import sys
import os
import threading
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QComboBox, QTextEdit, QLabel, QLineEdit, QFontComboBox, 
    QSpinBox, QColorDialog, QFrame, QCompleter
)
from PyQt6.QtCore import pyqtSignal, QObject, Qt, QStringListModel

# Adjust the path to import from the 'main' subdirectory
sys.path.append(os.path.join(os.path.dirname(__file__), 'main'))
from transcription_engine import TranscriptionEngine
from data_engine import DataEngine
from core_logic import CoreLogic

# --- Configuration ---
VOSK_MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'vosk-model')
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'bible.db')

# --- Stylesheet for Dark Theme ---
DARK_STYLESHEET = """
    QMainWindow, QWidget {
        background-color: #1E1E1E;
        color: #FFFFFF;
        font-family: Segoe UI;
    }
    QTextEdit {
        background-color: #2D2D2D;
        border: 1px solid #444444;
        font-size: 11pt;
    }
    QLabel {
        font-size: 9pt;
        font-weight: bold;
        color: #CCCCCC;
    }
    QLabel#VersePreviewText {
        font-size: 14pt;
        font-family: "Times New Roman";
    }
    QPushButton {
        background-color: #0078D7;
        color: #FFFFFF;
        border: none;
        padding: 8px 16px;
        font-size: 10pt;
        font-weight: bold;
        border-radius: 4px;
    }
    QPushButton:hover {
        background-color: #005A9E;
    }
    QPushButton:pressed {
        background-color: #003C6A;
    }
    QPushButton#StartListenButton {
        background-color: #107C10; /* Green */
        font-size: 12pt;
    }
    QPushButton#StartListenButton:hover {
        background-color: #0E6B0E;
    }
    QPushButton#StartListenButton:checked {
        background-color: #C50F1F; /* Red */
    }
    QComboBox, QLineEdit, QSpinBox, QFontComboBox {
        background-color: #2D2D2D;
        border: 1px solid #444444;
        padding: 5px;
        border-radius: 4px;
    }
    QComboBox::drop-down {
        border: none;
    }
    QFrame#OutputPreview {
        background-color: black;
        border: 2px solid #444444;
        border-radius: 5px;
    }
"""

class SelectAllLineEdit(QLineEdit):
    """A QLineEdit that selects all text when it receives focus."""
    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.selectAll()

class WorkerSignals(QObject):
    update_transcript = pyqtSignal(str, bool)
    update_status = pyqtSignal(str)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AutoVerse Control Panel")
        self.resize(1200, 700)
        self.setStyleSheet(DARK_STYLESHEET)

        # --- Initialize Engines ---
        self.data_engine = DataEngine(DB_PATH)
        self.data_engine.connect()
        self.book_list = self.data_engine.get_all_book_names()
        self.core_logic = CoreLogic(self.data_engine)
        self.transcription_engine = TranscriptionEngine(VOSK_MODEL_PATH)
        self.signals = WorkerSignals()

        self.initUI()
        self.post_init_checks()

    def initUI(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # === TOP ROW: LISTENING & TRANSCRIPT ===
        top_layout = QHBoxLayout()
        
        self.listen_button = QPushButton("START LISTENING")
        self.listen_button.setObjectName("StartListenButton")
        self.listen_button.setCheckable(True)
        self.listen_button.clicked.connect(self.toggle_listening)
        self.listen_button.setMinimumHeight(50)
        top_layout.addWidget(self.listen_button, 1)

        transcript_v_layout = QVBoxLayout()
        transcript_v_layout.addWidget(QLabel("PRIVATE TRANSCRIPT"))
        self.transcript_text = QTextEdit()
        self.transcript_text.setReadOnly(True)
        transcript_v_layout.addWidget(self.transcript_text)
        top_layout.addLayout(transcript_v_layout, 3)

        main_layout.addLayout(top_layout)

        # === MIDDLE ROW: CONTROLS ===
        controls_layout = QHBoxLayout()
        controls_layout.addWidget(self.create_manual_override_group())
        controls_layout.addWidget(self.create_customize_display_group())
        main_layout.addLayout(controls_layout)

        # === BOTTOM ROW: AUDIO & CLEAR ===
        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(QLabel("Audio Record")) # Placeholder for switch
        bottom_layout.addStretch()
        
        bottom_layout.addWidget(QLabel("Audio Source:"))
        self.audio_device_combo = QComboBox()
        self.audio_device_combo.setMinimumWidth(200)
        bottom_layout.addWidget(self.audio_device_combo)

        self.clear_button = QPushButton("CLEAR SCREEN")
        self.clear_button.clicked.connect(self.clear_displays)
        bottom_layout.addWidget(self.clear_button)
        main_layout.addLayout(bottom_layout)

        # === STATUS BAR ===
        self.statusBar = self.statusBar()
        self.status_label = QLabel("Welcome to AutoVerse.")
        self.statusBar.addWidget(self.status_label)

        self.signals.update_transcript.connect(self.update_transcript_display)
        self.signals.update_status.connect(self.update_status_bar)

    def post_init_checks(self):
        """Checks to run after the UI is initialized."""
        self.populate_audio_devices()
        if not self.transcription_engine.model_loaded:
            self.update_status_bar("ERROR: Vosk model not found. Please download and place it in the data/vosk-model folder.")
            self.listen_button.setEnabled(False)
            self.listen_button.setText("MODEL NOT FOUND")

    def create_manual_override_group(self):
        group_widget = QWidget()
        layout = QVBoxLayout(group_widget)
        layout.addWidget(QLabel("MANUAL OVERRIDE"))
        
        grid = QGridLayout()
        # --- Book Input ---
        grid.addWidget(QLabel("Book"), 0, 0)
        self.book_input = SelectAllLineEdit()
        book_completer = QCompleter(self.book_list)
        book_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        book_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.book_input.setCompleter(book_completer)
        self.book_input.returnPressed.connect(self.on_book_entered)
        self.book_input.editingFinished.connect(self.update_chapter_suggestions)
        grid.addWidget(self.book_input, 0, 1)
        
        # --- Chapter Input ---
        grid.addWidget(QLabel("Chapter"), 1, 0)
        self.chapter_input = SelectAllLineEdit()
        self.chapter_completer_model = QStringListModel()
        chapter_completer = QCompleter()
        chapter_completer.setModel(self.chapter_completer_model)
        self.chapter_input.setCompleter(chapter_completer)
        self.chapter_input.returnPressed.connect(self.on_chapter_entered)
        self.chapter_input.editingFinished.connect(self.update_verse_suggestions)
        grid.addWidget(self.chapter_input, 1, 1)

        # --- Verse Input ---
        grid.addWidget(QLabel("Verse"), 2, 0)
        self.verse_input = SelectAllLineEdit()
        self.verse_completer_model = QStringListModel()
        verse_completer = QCompleter()
        verse_completer.setModel(self.verse_completer_model)
        self.verse_input.setCompleter(verse_completer)
        self.verse_input.returnPressed.connect(self.manual_lookup)
        grid.addWidget(self.verse_input, 2, 1)
        
        self.go_button = QPushButton("GO")
        self.go_button.clicked.connect(self.manual_lookup)
        grid.addWidget(self.go_button, 3, 1)

        layout.addLayout(grid)
        layout.addStretch()
        return group_widget

    def on_book_entered(self):
        """If completer is visible, confirms selection. Then moves focus."""
        completer = self.book_input.completer()
        if completer.popup().isVisible():
            self.book_input.setText(completer.currentCompletion())
            completer.popup().hide()
        self.update_chapter_suggestions()
        self.chapter_input.setFocus()

    def on_chapter_entered(self):
        """If completer is visible, confirms selection. Then moves focus."""
        completer = self.chapter_input.completer()
        if completer.popup().isVisible():
            self.chapter_input.setText(completer.currentCompletion())
            completer.popup().hide()
        self.update_verse_suggestions()
        self.verse_input.setFocus()

    def update_chapter_suggestions(self):
        book = self.book_input.text()
        translation = self.translation_combo.currentText()
        if book in self.book_list:
            chapters = self.data_engine.get_chapters_for_book(translation, book)
            self.chapter_completer_model.setStringList(chapters)

    def update_verse_suggestions(self):
        book = self.book_input.text()
        chapter = self.chapter_input.text()
        translation = self.translation_combo.currentText()
        if book in self.book_list and chapter.isdigit():
            verses = self.data_engine.get_verses_for_chapter(translation, book, chapter)
            self.verse_completer_model.setStringList(verses)

    def create_customize_display_group(self):
        group_widget = QWidget()
        layout = QGridLayout(group_widget)
        layout.addWidget(QLabel("CUSTOMIZE DISPLAY"), 0, 0, 1, 2)

        layout.addWidget(QLabel("Translation"), 1, 0)
        self.translation_combo = QComboBox()
        self.translation_combo.addItems(["KJV", "NIV", "AMP"])
        layout.addWidget(self.translation_combo, 1, 1)
        
        layout.addWidget(QLabel("Font"), 2, 0)
        layout.addWidget(QFontComboBox(), 2, 1)
        layout.addWidget(QLabel("Font Size"), 3, 0)
        layout.addWidget(QSpinBox(), 3, 1)
        layout.addWidget(QLabel("Text Color"), 4, 0)
        layout.addWidget(QPushButton("Choose Color"), 4, 1)
        layout.addWidget(QLabel("Background"), 5, 0)
        layout.addWidget(QPushButton("Choose Color"), 5, 1)

        # Output Preview
        preview_label = QLabel("CUSTOMIZE OUTPUT")
        layout.addWidget(preview_label, 0, 2, 1, 2)
        output_preview = QFrame()
        output_preview.setObjectName("OutputPreview")
        output_preview.setMinimumSize(200, 100)
        preview_layout = QVBoxLayout(output_preview)
        self.preview_text = QLabel("Output will appear here.")
        self.preview_text.setObjectName("VersePreviewText")
        self.preview_text.setWordWrap(True)
        self.preview_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_layout.addWidget(self.preview_text)
        layout.addWidget(output_preview, 1, 2, 5, 2)

        return group_widget

    def populate_audio_devices(self):
        self.audio_devices = self.transcription_engine.list_audio_devices()
        for index, name in self.audio_devices.items():
            self.audio_device_combo.addItem(name, userData=index)

    def manual_lookup(self):
        """Looks up a verse based on manual input fields."""
        book = self.book_input.text()
        chapter = self.chapter_input.text()
        verse = self.verse_input.text()
        translation = self.translation_combo.currentText()

        if not all([book, chapter, verse]):
            self.preview_text.setText("Error: Book, Chapter, and Verse must all be filled in.")
            return

        verse_text = self.data_engine.get_verse(translation, book, chapter, verse)
        if verse_text:
            verse_data = {
                'translation': translation,
                'book': book.title(),
                'chapter': chapter,
                'verse_num': verse,
                'text': verse_text
            }
            self.display_verse(verse_data)
        else:
            self.preview_text.setText(f"Verse not found:\n{translation} {book} {chapter}:{verse}")

    def toggle_listening(self):
        if self.listen_button.isChecked():
            self.listen_button.setText("STOP LISTENING")
            selected_index = self.audio_device_combo.currentData()

            self.transcription_thread = threading.Thread(
                target=self.transcription_engine.start_listening,
                args=(self.on_transcription_update, self.on_status_update, selected_index)
            )
            self.transcription_thread.daemon = True
            self.transcription_thread.start()
        else:
            self.listen_button.setText("START LISTENING")
            self.transcription_engine.stop_listening()
            self.update_status_bar("Stopped listening.")

    def on_transcription_update(self, text, is_final):
        self.signals.update_transcript.emit(text, is_final)

    def on_status_update(self, message):
        self.signals.update_status.emit(message)

    def update_transcript_display(self, text, is_final):
        if is_final and text.strip():
            self.transcript_text.append(text)
            translation = self.translation_combo.currentText()
            verse_data = self.core_logic.parse_and_find_verse(text, translation)
            if verse_data:
                self.display_verse(verse_data)

    def update_status_bar(self, message):
        """Updates the status bar with a message."""
        print(f"UI Status: {message}") # Debugging print
        self.status_label.setText(message)

    def display_verse(self, verse_data):
        """Updates the preview panel with the found verse."""
        formatted_text = self.core_logic.get_ui_text(verse_data)
        self.preview_text.setText(formatted_text)
        self.update_status_bar(f"Displayed: {verse_data['book']} {verse_data['chapter']}:{verse_data['verse_num']}")

    def clear_displays(self):
        """Clears the transcript and preview displays."""
        self.transcript_text.clear()
        self.preview_text.setText("Output will appear here.")
        self.update_status_bar("Displays cleared.")

    def closeEvent(self, event):
        if self.transcription_engine.is_listening:
            self.transcription_engine.stop_listening()
        self.data_engine.close_connection()
        event.accept()

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
