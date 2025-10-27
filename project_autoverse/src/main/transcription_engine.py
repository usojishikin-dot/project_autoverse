
import vosk
import sounddevice as sd
import queue
import json
import os
import wave
import numpy as np

class TranscriptionEngine:
    """
    Handles live audio transcription using the Vosk STT library and optional audio recording.
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
        self.recorded_frames = []
        self.should_record = False
        self.samplerate = None
        self.model_loaded = False

        try:
            if os.path.exists(self.model_path):
                self.model = vosk.Model(self.model_path)
                self.model_loaded = True
            else:
                print(f"Warning: Vosk model not found at path: {self.model_path}")
        except Exception as e:
            print(f"Error loading Vosk model: {e}")

    @staticmethod
    def list_audio_devices():
        """
        Lists available audio input devices.
        :return: A tuple containing a dictionary of input devices {index: name} and the index of the default device.
        """
        devices = sd.query_devices()
        input_devices = {}
        default_device_index = -1
        for i, device in enumerate(devices):
            is_input = device['max_input_channels'] > 0
            is_default = sd.query_hostapis()[device['hostapi']]['name'] in sd.query_devices(kind='input')['name']
            if is_input:
                input_devices[i] = device['name']
                if is_default:
                    default_device_index = i
        return input_devices, default_device_index

    def _audio_callback(self, indata, frames, time, status):
        """This is called (from a separate thread) for each audio block."""
        if status:
            print(status, flush=True)
        self.audio_queue.put(bytes(indata))
        if self.should_record:
            self.recorded_frames.append(indata.copy())

    def start_listening(self, on_transcription_update, on_status_update, device_index=None, should_record=False):
        """
        Starts the audio stream and transcription process.

        :param on_transcription_update: Callback for transcription results.
        :param on_status_update: Callback for status messages.
        :param device_index: Index of the audio device.
        :param should_record: Boolean flag to enable recording.
        """
        if self.is_listening:
            on_status_update("Already listening.")
            return
        if not self.model_loaded:
            on_status_update("Vosk model not loaded. Cannot start listening.")
            return

        self.should_record = should_record
        if self.should_record:
            self.recorded_frames = [] # Clear previous recording

        try:
            device_info = sd.query_devices(device=device_index, kind='input')
            self.samplerate = int(device_info['default_samplerate'])
            
            self.stream = sd.RawInputStream(
                samplerate=self.samplerate,
                blocksize=4000, # Increased for more stable performance
                device=device_index,
                dtype='int16',
                channels=1,
                callback=self._audio_callback
            )

            self.recognizer = vosk.KaldiRecognizer(self.model, self.samplerate)
            self.is_listening = True
            self.stream.start()
            on_status_update(f"Listening on: {device_info['name']}...")

            while self.is_listening:
                data = self.audio_queue.get()
                if self.recognizer.AcceptWaveform(data):
                    result = json.loads(self.recognizer.Result())
                    on_transcription_update(result.get('text', ''), is_final=True)
                else:
                    partial_result = json.loads(self.recognizer.PartialResult())
                    on_transcription_update(partial_result.get('partial', ''), is_final=False)

        except Exception as e:
            on_status_update(f"Error: {e}")
            self.is_listening = False

    def stop_listening(self):
        """
        Stops the audio stream and transcription process.
        """
        if not self.is_listening:
            return

        self.is_listening = False
        # The loop in start_listening will exit
        if hasattr(self, 'stream') and self.stream:
            self.stream.stop()
            self.stream.close()
            print("Stream stopped and closed.")
        
        # The transcription thread will terminate naturally after the loop ends.

    def save_audio_stream(self, output_path):
        """
        Saves the recorded audio frames to a WAV file.
        :param output_path: The path to save the WAV file.
        """
        if not self.should_record or not self.recorded_frames:
            print("[INFO] No audio was recorded or recording was not enabled.")
            return

        print(f"[INFO] Saving audio to {output_path}...")
        try:
            # Ensure the directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            wave_file = wave.open(output_path, 'wb')
            wave_file.setnchannels(1)
            wave_file.setsampwidth(2)  # 2 bytes for int16
            wave_file.setframerate(self.samplerate)
            
            # Concatenate all frames and write to the file
            wave_file.writeframes(b''.join(self.recorded_frames))
            wave_file.close()
            
            print(f"[INFO] Audio successfully saved to {output_psth}")
            self.recorded_frames = [] # Clear frames after saving
        except Exception as e:
            print(f"[ERROR] Failed to save audio stream: {e}")



if __name__ == '__main__':
    # Example Usage:
    VOSK_MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'vosk-model')

    def handle_transcription(text, is_final):
        """A simple callback to print the transcription results."""
        if is_final:
            print(f"Final: {text}")
        else:
            print(f"Partial: {text}")

    if not os.path.exists(VOSK_MODEL_PATH) or not os.listdir(VOSK_MODEL_PATH):
        print("Vosk model not found or directory is empty.")
        print(f"Please download a model from https://alphacephei.com/vosk/models and unzip it to: {VOSK_MODEL_PATH}")
    else:
        try:
            engine = TranscriptionEngine(VOSK_MODEL_PATH)

            # 1. List available audio devices
            print("Available audio input devices:")
            devices = engine.list_audio_devices()
            for index, name in devices.items():
                print(f"  [{index}] {name}")

            # In a real UI, you would present this list in a dropdown.
            # For this demo, we will use the default device (None).
            # To test a specific device, change SELECTED_DEVICE_INDEX to the desired index.
            SELECTED_DEVICE_INDEX = None

            print("\nStarting transcription in 3 seconds... Speak into your microphone.")
            import time
            time.sleep(3)

            # 2. Start listening on the selected device
            import threading
            transcription_thread = threading.Thread(
                target=engine.start_listening,
                args=(handle_transcription, SELECTED_DEVICE_INDEX)
            )
            transcription_thread.daemon = True
            transcription_thread.start()

            # Let it run for 10 seconds
            time.sleep(10)
            engine.stop_listening()
            print("Demonstration finished.")

        except Exception as e:
            print(f"An error occurred during the demonstration: {e}")
            print("Please ensure you have 'sounddevice' and 'vosk' installed: pip install sounddevice vosk")
