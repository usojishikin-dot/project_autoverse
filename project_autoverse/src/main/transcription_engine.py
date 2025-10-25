
import vosk
import sounddevice as sd
import queue
import json
import os
from pydub import AudioSegment
import numpy as np

# --- 1. The Vocabulary Generator Class ---

class VoskGrammarGenerator:
    """
    Generates the custom JSON grammar for Vosk based on church and Bible terminology.
    This helps Vosk prioritize domain-specific words, reducing recognition errors.
    """

    # 66 Books of the Bible (Canonical Names for the Grammar)
    BIBLE_BOOKS = [
        # Old Testament
        "genesis", "exodus", "leviticus", "numbers", "deuteronomy", "joshua",
        "judges", "ruth", "first samuel", "second samuel", "first kings",
        "second kings", "first chronicles", "second chronicles", "ezra",
        "nehemiah", "esther", "job", "psalms", "proverbs", "ecclesiastes",
        "song of solomon", "isaiah", "jeremiah", "lamentations", "ezekiel",
        "daniel", "hosea", "joel", "amos", "obadiah", "jonah", "micah",
        "nahum", "habakkuk", "zephaniah", "haggai", "zechariah", "malachi",
        # New Testament
        "matthew", "mark", "luke", "john", "acts", "romans",
        "first corinthians", "second corinthians", "galatians", "ephesians",
        "philippians", "colossians", "first thessalonians", "second thessalonians",
        "first timothy", "second timothy", "titus", "philemon", "hebrews",
        "james", "first peter", "second peter", "first john", "second john",
        "third john", "jude", "revelation"
    ]

    # Numbers for Chapters/Verses (0 to 100 for redundancy)
    NUMBERS = [str(i) for i in range(101)] + [
        "zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
        "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
        "twenty", "thirty", "forty", "fifty", "hundred",
        # Ordinals for 1/2/3 John/Peter/Corinthians
        "first", "second", "third"
    ]

    # Citation & Church-Specific Keywords
    KEYWORDS = [
        "chapter", "verse", "to", "through", "and", "in", "let us read",
        "turn to", "referencing", "elder", "deacon", "pastor", "reverend",
        "trinity", "baptism", "eucharist", "doxology", "amen", "hallelujah"
    ]

    @classmethod
    def generate_grammar_list(cls):
        """Generates a complete list of all words for the Vosk grammar."""
        # Combine all lists, convert to lowercase, and ensure unique words
        full_vocabulary = set()

        # Add book names and their components (e.g., 'first' and 'corinthians' separately)
        for book in cls.BIBLE_BOOKS:
            for word in book.split():
                full_vocabulary.add(word)

        # Add numbers and keywords
        full_vocabulary.update(cls.NUMBERS)
        full_vocabulary.update(cls.KEYWORDS)

        # Vosk expects the grammar to be a list of words, plus the out-of-vocabulary token [unk]
        return list(full_vocabulary)

    @classmethod
    def generate_vosk_json(cls):
        """Creates the JSON string required by Vosk for grammar biasing."""
        # The structure is a simple list of strings
        grammar_list = cls.generate_grammar_list()

        # For simple vocabulary biasing, we can simply stringify the list
        return json.dumps(grammar_list)

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
            grammar = VoskGrammarGenerator.generate_vosk_json()
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
