
import vosk
import sounddevice as sd
import queue
import json
import os
from pydub import AudioSegment
import numpy as np
from vosk_grammar import generate_vosk_grammar

class TranscriptionEngine:
    """
    Handles live audio transcription using the Vosk STT library.
    """
    def __init__(self, model_path):
        """
        Initializes the TranscriptionEngine.

        :param model_path: Path to the Vosk model directory.
        """
        self.model_path = model_path
        self.model = None
        self.recognizer = None
        self.is_listening = False
        self.audio_queue = queue.Queue()
        self.model_loaded = False
        self.is_recording = False
        self.recorded_frames = []
        self._load_model()

    def _load_model(self):
        """Loads the Vosk model and sets the model_loaded flag."""
        try:
            if not os.path.exists(self.model_path) or not os.listdir(self.model_path):
                print(f"Vosk model not found or directory is empty at: {self.model_path}")
                self.model_loaded = False
                return
            self.model = vosk.Model(self.model_path)
            self.model_loaded = True
            print("Vosk model loaded successfully.")
        except Exception as e:
            print(f"Error loading Vosk model: {e}")
            self.model_loaded = False

    @staticmethod
    def list_audio_devices():
        """
        Lists available audio input devices and identifies the default input device.
        :return: A tuple containing (dictionary of input devices {index: name}, default_device_index).
        """
        try:
            devices = sd.query_devices()
            hostapis = sd.query_hostapis()

            default_api = next((api for api in hostapis if api['name'] == sd.default.hostapi), None)
            default_device_index = -1
            if default_api:
                default_device_index = default_api['default_input_device']

            input_devices = {i: d['name'] for i, d in enumerate(devices) if d['max_input_channels'] > 0}

            return input_devices, default_device_index

        except Exception as e:
            print(f"Could not retrieve audio devices: {e}")
            return {}, -1

    def _audio_callback(self, indata, frames, time, status):
        """This is called (from a separate thread) for each audio block."""
        if status:
            self.status_callback(f"Audio callback status: {status}")

        # The data from sounddevice is a numpy array, which is what we need for wav saving
        if self.is_recording:
            self.recorded_frames.append(indata.copy())

        self.audio_queue.put(bytes(indata))

    def start_listening(self, on_transcription_update, on_status_update, device_index=None, record_audio=False):
        """
        Starts the audio stream and transcription process.

        :param on_transcription_update: A callback for transcription results.
        :param on_status_update: A callback for status messages.
        :param device_index: The index of the audio device to use.
        """
        self.status_callback = on_status_update
        if not self.model_loaded:
            self.status_callback("ERROR: Vosk model is not loaded. Cannot start listening.")
            return

        if self.is_listening:
            self.status_callback("Already listening.")
            return

        try:
            device_info = sd.query_devices(device_index, 'input')
            self.samplerate = int(device_info['default_samplerate'])

            # Start recording if requested
            self.is_recording = record_audio
            if self.is_recording:
                self.recorded_frames = [] # Clear previous recording
                self.status_callback("Recording audio...")

            self.stream = sd.InputStream(
                samplerate=self.samplerate, blocksize=8000, device=device_index,
                dtype='int16', channels=1, callback=self._audio_callback
            )

            # Generate and apply the custom grammar
            grammar = generate_vosk_grammar()
            self.recognizer = vosk.KaldiRecognizer(self.model, self.samplerate, grammar)

            self.is_listening = True
            self.stream.start()
            self.status_callback(f"Listening on: {device_info['name']}")

            while self.is_listening:
                data = self.audio_queue.get()
                if self.recognizer.AcceptWaveform(data):
                    result = json.loads(self.recognizer.Result())
                    on_transcription_update(result.get('text', ''), is_final=True)
                else:
                    partial_result = json.loads(self.recognizer.PartialResult())
                    on_transcription_update(partial_result.get('partial', ''), is_final=False)

        except Exception as e:
            error_message = f"ERROR: Failed to start listening. Check audio device. Details: {e}"
            self.status_callback(error_message)
            self.is_listening = False
            if hasattr(self, 'stream') and self.stream:
                self.stream.stop()
                self.stream.close()

    def stop_listening(self):
        """
        Stops the audio stream and transcription process.
        """
        if not self.is_listening:
            self.status_callback("Not currently listening.")
            return

        self.is_listening = False
        if hasattr(self, 'stream') and self.stream:
            self.stream.stop()
            self.stream.close()

        self.is_recording = False
        self.status_callback("Stopped listening.")

    def save_audio_stream(self, output_path):
        """
        Saves the captured audio stream to a MP3 file.
        :param output_path: The path to save the MP3 file.
        """
        if not self.recorded_frames:
            self.status_callback("No audio recorded to save.")
            return

        try:
            # Ensure the output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # Combine the recorded frames into a single numpy array
            audio_data = np.concatenate(self.recorded_frames, axis=0)

            # Create an AudioSegment from the raw audio data
            audio_segment = AudioSegment(
                audio_data.tobytes(),
                frame_rate=self.samplerate,
                sample_width=audio_data.dtype.itemsize,
                channels=1
            )

            # Export the audio to MP3 format
            audio_segment.export(output_path, format="mp3")

            self.status_callback(f"Audio saved to {output_path}")
        except Exception as e:
            self.status_callback(f"Error saving audio: {e}")


if __name__ == '__main__':
    # Example Usage:
    VOSK_MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'vosk-model')

    def handle_transcription(text, is_final):
        """A simple callback to print the transcription results."""
        if is_final:
            print(f"Final: {text}")
        else:
            print(f"Partial: {text}")

    def handle_status(message):
        """A simple callback to print status messages."""
        print(f"STATUS: {message}")

    if not os.path.exists(VOSK_MODEL_PATH) or not os.listdir(VOSK_MODEL_PATH):
        print("Vosk model not found or directory is empty.")
        print(f"Please download a model from https://alphacephei.com/vosk/models and unzip it to: {VOSK_MODEL_PATH}")
    else:
        try:
            engine = TranscriptionEngine(VOSK_MODEL_PATH)

            # 1. List available audio devices
            print("Available audio input devices:")
            devices, default_index = engine.list_audio_devices()
            for index, name in devices.items():
                default_marker = "(Default)" if index == default_index else ""
                print(f"  [{index}] {name} {default_marker}")
            
            SELECTED_DEVICE_INDEX = default_index
            
            print(f"\nStarting transcription in 3 seconds on device {SELECTED_DEVICE_INDEX}...")
            import time
            time.sleep(3)

            # 2. Start listening on the selected device
            import threading
            transcription_thread = threading.Thread(
                target=engine.start_listening, 
                args=(handle_transcription, handle_status, SELECTED_DEVICE_INDEX, True) # Record audio
            )
            transcription_thread.daemon = True
            transcription_thread.start()

            # Let it run for 10 seconds
            time.sleep(10)
            engine.stop_listening()

            # Save the recorded audio
            output_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'recordings', 'test_recording.mp3')
            engine.save_audio_stream(output_path)

            print("Demonstration finished.")

        except Exception as e:
            print(f"An error occurred during the demonstration: {e}")
            print("Please ensure you have 'sounddevice' and 'vosk' installed: pip install sounddevice vosk")
