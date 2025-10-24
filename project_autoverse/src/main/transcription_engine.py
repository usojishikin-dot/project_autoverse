
import vosk
import sounddevice as sd
import queue
import json
import os

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

        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Vosk model not found at path: {self.model_path}")

        self.model = vosk.Model(self.model_path)

    @staticmethod
    def list_audio_devices():
        """
        Lists available audio input devices.
        :return: A dictionary of input devices {index: name}.
        """
        devices = sd.query_devices()
        input_devices = {}
        for i, device in enumerate(devices):
            # Check if the device is an input device
            if device['max_input_channels'] > 0:
                input_devices[i] = device['name']
        return input_devices

    def _audio_callback(self, indata, frames, time, status):
        """This is called (from a separate thread) for each audio block."""
        if status:
            print(status, flush=True)
        self.audio_queue.put(bytes(indata))

    def start_listening(self, on_transcription_update, device_index=None):
        """
        Starts the audio stream and transcription process.

        :param on_transcription_update: A callback function to be called with new transcription results.
        :param device_index: The index of the audio device to use. Defaults to the system's default input device.
        """
        if self.is_listening:
            print("Already listening.")
            return

        try:
            if device_index is None:
                device_info = sd.query_devices(kind='input')
            else:
                device_info = sd.query_devices(device=device_index)
            
            samplerate = int(device_info['default_samplerate'])

            self.stream = sd.RawInputStream(
                samplerate=samplerate,
                blocksize=8000,
                device=device_index,
                dtype='int16',
                channels=1,
                callback=self._audio_callback
            )

            self.recognizer = vosk.KaldiRecognizer(self.model, samplerate)
            self.is_listening = True
            self.stream.start()
            print(f"Started listening on device: {device_info['name']}...")

            # Main transcription loop
            while self.is_listening:
                data = self.audio_queue.get()
                if self.recognizer.AcceptWaveform(data):
                    result = json.loads(self.recognizer.Result())
                    on_transcription_update(result.get('text', ''), is_final=True)
                else:
                    partial_result = json.loads(self.recognizer.PartialResult())
                    on_transcription_update(partial_result.get('partial', ''), is_final=False)

        except Exception as e:
            print(f"An error occurred while starting to listen: {e}")
            self.is_listening = False

    def stop_listening(self):
        """
        Stops the audio stream and transcription process.
        """
        if not self.is_listening:
            print("Not currently listening.")
            return

        self.is_listening = False
        if hasattr(self, 'stream') and self.stream:
            self.stream.stop()
            self.stream.close()
        print("Stopped listening.")

    def save_audio_stream(self, output_path):
        """
        Placeholder for functionality to save the captured audio stream.
        """
        print(f"[INFO] Audio stream saving to {output_path} is not yet implemented.")


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
