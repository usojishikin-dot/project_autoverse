
import re

class CoreLogic:
    """
    Parses transcription text to find and retrieve Bible verses.
    """
    def __init__(self, data_engine):
        """
        Initializes the CoreLogic engine.
        :param data_engine: An instance of the DataEngine.
        """
        self.data_engine = data_engine
        self.book_pattern = self._build_book_pattern()

    def _build_book_pattern(self):
        """Builds a regex pattern to match all known Bible books."""
        # The keys from the spoken word map are perfect for this
        books = list(self.data_engine.spoken_word_map.keys())
        # Add books that might be spoken differently, e.g., with numbers
        books.extend(['1 corinthians', '2 corinthians', '1 timothy', '2 timothy', '1 peter', '2 peter', '1 john', '2 john', '3 john'])
        # Create a regex pattern: (first corinthians|genesis|...)
        return f"({'|'.join(sorted(books, key=len, reverse=True))})"

    def parse_and_find_verse(self, text, translation='KJV'):
        """
        Parses text to find a Bible citation and retrieves the verse.
        
        :param text: The transcribed text from the STT engine.
        :param translation: The Bible translation to use (e.g., 'KJV').
        :return: A dictionary with verse info or None.
        """
        text = text.lower()
        
        pattern = re.compile(f"{self.book_pattern}\s+(\d+)\s+(\d+)")
        match = pattern.search(text)

        if not match:
            return None

        book, chapter, verse = match.groups()
        
        verse_text = self.data_engine.get_verse(translation, book, chapter, verse)
        
        if verse_text:
            return {
                'translation': translation,
                'book': self.data_engine.spoken_word_map.get(book, book).title(),
                'chapter': chapter,
                'verse_num': verse,
                'text': verse_text
            }
        
        return None

    def get_ui_text(self, verse_data):
        """
        Formats the verse data into a string for UI display.

        :param verse_data: A dictionary with verse info.
        :return: A formatted string for the UI.
        """
        if not verse_data:
            return ""
        return f'"...{verse_data["text"]}"\n\n{verse_data["book"]} {verse_data["chapter"]}:{verse_data["verse_num"]} ({verse_data["translation"]})'


if __name__ == '__main__':
    # This is a mock DataEngine for testing purposes.
    class MockDataEngine:
        def __init__(self):
            self.spoken_word_map = {
                "john": "John",
                "first corinthians": "1 Corinthians"
            }
        def get_verse(self, translation, book, chapter, verse_num):
            book_key = self.spoken_word_map.get(book.lower())
            if book_key == "John" and chapter == "3" and verse_num == "16":
                return "For God so loved the world..."
            return None

    # --- Test Cases ---
    engine = CoreLogic(MockDataEngine())
    
    test_phrase_1 = "Testing testing and now for a reading from john 3 16 and it says..."
    result = engine.parse_and_find_verse(test_phrase_1)
    assert result is not None
    assert result['book'] == "John"
    assert result['chapter'] == "3"
    assert result['verse_num'] == "16"
    print(f"Successfully parsed: '{test_phrase_1}'")

    # Test the new get_ui_text function
    ui_text = engine.get_ui_text(result)
    expected_text = '"...For God so loved the world..."\n\nJohn 3:16 (KJV)'
    assert ui_text == expected_text
    print(f"Successfully formatted UI text: '{ui_text}'")

    test_phrase_2 = "This is a test with no verse"
    result = engine.parse_and_find_verse(test_phrase_2)
    assert result is None
    print(f"Successfully ignored: '{test_phrase_2}'")

    # Test get_ui_text with no result
    ui_text_none = engine.get_ui_text(result)
    assert ui_text_none == ""
    print("Successfully handled None input for UI text.")

    print("\nCoreLogic tests passed!")
