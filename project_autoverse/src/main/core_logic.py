
import re
import time

BIBLE_BOOKS = [
    "genesis", "exodus", "leviticus", "numbers", "deuteronomy", "joshua",
    "judges", "ruth", "first samuel", "second samuel", "first kings",
    "second kings", "first chronicles", "second chronicles", "ezra",
    "nehemiah", "esther", "job", "psalms", "proverbs", "ecclesiastes",
    "song of solomon", "isaiah", "jeremiah", "lamentations", "ezekiel",
    "daniel", "hosea", "joel", "amos", "obadiah", "jonah", "micah",
    "nahum", "habakkuk", "zephaniah", "haggai", "zechariah", "malachi",
    "matthew", "mark", "luke", "john", "acts", "romans",
    "first corinthians", "second corinthians", "galatians", "ephesians",
    "philippians", "colossians", "first thessalonians", "second thessalonians",
    "first timothy", "second timothy", "titus", "philemon", "hebrews",
    "james", "first peter", "second peter", "first john", "second john",
    "third john", "jude", "revelation"
]

def normalize_text_to_digits(text):
    """Converts written numbers and ordinals in text to their digit equivalents."""
    num_map = {
        'zero': '0', 'one': '1', 'two': '2', 'three': '3', 'four': '4', 'five': '5',
        'six': '6', 'seven': '7', 'eight': '8', 'nine': '9', 'ten': '10',
        'eleven': '11', 'twelve': '12', 'thirteen': '13', 'fourteen': '14', 'fifteen': '15',
        'sixteen': '16', 'seventeen': '17', 'eighteen': '18', 'nineteen': '19', 'twenty': '20',
        'thirty': '30', 'forty': '40', 'fifty': '50', 'sixty': '60', 'seventy': '70',
        'eighty': '80', 'ninety': '90', 'hundred': '100',
        'first': '1', 'second': '2', 'third': '3'
    }

    # Handle special cases for numbered book names
    text = re.sub(r'first(?=\s(samuel|kings|chronicles|corinthians|thessalonians|timothy|peter|john))', '1', text, flags=re.IGNORECASE)
    text = re.sub(r'second(?=\s(samuel|kings|chronicles|corinthians|thessalonians|timothy|peter|john))', '2', text, flags=re.IGNORECASE)
    text = re.sub(r'third(?=\s(john))', '3', text, flags=re.IGNORECASE)

    # General number conversion
    for word, digit in num_map.items():
        text = re.sub(r'\b' + word + r'\b', digit, text, flags=re.IGNORECASE)

    return text

def extract_citation(normalized_text, book_names):
    """
    Extracts a Bible citation (book, chapter, verse) from normalized text.
    Returns a dictionary with citation info or None.
    """
    # Create a version of the book names with numbers for regex matching
    numbered_book_names = [b.replace('first', '1').replace('second', '2').replace('third', '3') for b in book_names]
    all_book_names = sorted(list(set(book_names + numbered_book_names)), key=len, reverse=True)
    book_pattern = '|'.join(all_book_names)

    # Regex to find citations like "John 3 16" or "1 Corinthians 13 4 through 7"
    pattern = re.compile(
        rf'({book_pattern})\s+(\d+)\s+(\d+)(?:\s+(?:through|to)\s+(\d+))?',
        re.IGNORECASE
    )
    match = pattern.search(normalized_text)

    if not match:
        return None

    book, chapter_start, verse_start, verse_end = match.groups()

    return {
        'book': book,
        'chapter_start': chapter_start,
        'verse_start': verse_start,
        'chapter_end': chapter_start, # Assume same chapter if not specified
        'verse_end': verse_end if verse_end else verse_start
    }

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

    def parse_and_find_verse(self, text, translation='KJV'):
        """
        Parses text to find a Bible citation and retrieves the verse.
        
        :param text: The transcribed text from the STT engine.
        :param translation: The Bible translation to use (e.g., 'KJV').
        :return: A dictionary with verse info or None.
        """
        normalized_text = normalize_text_to_digits(text)
        citation = extract_citation(normalized_text, BIBLE_BOOKS)
        
        if not citation:
            return None

        # For simplicity, we'll retrieve the starting verse of the citation
        book = citation['book']
        chapter = citation['chapter_start']
        verse = citation['verse_start']
        
        verse_text = self.data_engine.get_verse(translation, book, chapter, verse)
        
        if verse_text:
            return {
                'translation': translation,
                'book': self.data_engine.spoken_word_map.get(book, book).title(),
                'chapter': chapter,
                'verse_num': verse,
                'text': verse_text,
                'timestamp': time.time()
            }
        
        return None

    def get_ui_text(self, verse_data):
        """
        Formats the verse data into an HTML string for UI display.

        :param verse_data: A dictionary with verse info.
        :return: An HTML-formatted string for the UI.
        """
        if not verse_data:
            return ""

        verse_text = f'"...{verse_data["text"]}"'
        citation_text = f"{verse_data['book']} {verse_data['chapter']}:{verse_data['verse_num']} ({verse_data['translation']})"

        return f"""
            <p>{verse_text}</p>
            <p style='color: #AAAAAA; font-size: 10pt;'>{citation_text}</p>
        """


if __name__ == '__main__':
    # --- Test Cases for the new functions ---

    # Test normalize_text_to_digits
    assert normalize_text_to_digits("first samuel one two") == "1 samuel 1 2"
    assert normalize_text_to_digits("Let's read from second Corinthians chapter five") == "Let's read from 2 Corinthians chapter 5"
    assert normalize_text_to_digits("Third John verse one") == "3 John verse 1"
    print("normalize_text_to_digits tests passed!")

    # Test extract_citation
    citation = extract_citation("a reading from genesis 1 1 and it says", BIBLE_BOOKS)
    assert citation['book'] == 'genesis' and citation['verse_start'] == '1'

    citation_range = extract_citation("in exodus 20 1 through 17 we find", BIBLE_BOOKS)
    assert citation_range['book'] == 'exodus' and citation_range['verse_start'] == '1' and citation_range['verse_end'] == '17'

    citation_numbered = extract_citation("1 timothy 2 5 is a good verse", BIBLE_BOOKS)
    assert citation_numbered['book'] == '1 timothy' and citation_numbered['chapter_start'] == '2'
    print("extract_citation tests passed!")

    # This is a mock DataEngine for testing purposes.
    class MockDataEngine:
        def __init__(self):
            self.spoken_word_map = {
                "john": "John",
                "1 corinthians": "1 Corinthians"
            }
        def get_verse(self, translation, book, chapter, verse_num):
            book_key = self.spoken_word_map.get(book.lower())
            if book_key == "John" and chapter == "3" and verse_num == "16":
                return "For God so loved the world..."
            return None

    # --- Test CoreLogic with new parsing ---
    engine = CoreLogic(MockDataEngine())
    
    test_phrase_1 = "Testing testing and now for a reading from john three sixteen and it says..."
    result = engine.parse_and_find_verse(test_phrase_1)
    assert result is not None
    assert result['book'] == "John" and result['chapter'] == "3" and result['verse_num'] == "16"
    print(f"Successfully parsed complex phrase: '{test_phrase_1}'")

    print("\nAll CoreLogic tests passed!")
