
import sqlite3
import os

class DataEngine:
    """
    Manages the SQLite database for storing and retrieving Bible verses.
    """
    def __init__(self, db_path):
        """
        Initializes the DataEngine and connects to the database.

        :param db_path: Path to the SQLite database file.
        """
        self.db_path = db_path
        self.connection = None
        self._create_spoken_word_map()

    def connect(self):
        """Establishes a connection to the SQLite database."""
        try:
            self.connection = sqlite3.connect(self.db_path)
            print("Successfully connected to the database.")
        except sqlite3.Error as e:
            print(f"Error connecting to database: {e}")
            # In a real app, this should be logged and handled gracefully.
            raise

    def setup_database(self):
        """
        Creates the necessary tables if they don't already exist.
        """
        if not self.connection:
            self.connect()

        cursor = self.connection.cursor()
        try:
            # Table optimized for fast lookups
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scriptures (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    translation TEXT NOT NULL,
                    book TEXT NOT NULL,
                    chapter INTEGER NOT NULL,
                    verse_num INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    UNIQUE(translation, book, chapter, verse_num)
                );
            """)
            self.connection.commit()
            print("Database setup complete. 'scriptures' table is ready.")
        except sqlite3.Error as e:
            print(f"Error setting up database table: {e}")
        finally:
            cursor.close()

    def get_verse(self, translation, book, chapter, verse_num):
        """
        Retrieves a specific verse from the database.

        :param translation: Bible translation (e.g., 'KJV').
        :param book: The book of the Bible (e.g., 'John').
        :param chapter: The chapter number.
        :param verse_num: The verse number.
        :return: The text of the verse, or None if not found.
        """
        if not self.connection:
            return None

        # Normalize book name using the spoken word map
        book_key = self.spoken_word_map.get(book.lower(), book)

        cursor = self.connection.cursor()
        try:
            cursor.execute("""
                SELECT text FROM scriptures
                WHERE translation = ? AND book = ? AND chapter = ? AND verse_num = ?
            """, (translation, book_key, chapter, verse_num))
            result = cursor.fetchone()
            return result[0] if result else None
        except sqlite3.Error as e:
            print(f"Error retrieving verse: {e}")
            return None
        finally:
            cursor.close()

    def get_all_book_names(self):
        """Retrieves a sorted list of unique book names from the database."""
        if not self.connection:
            return []

        cursor = self.connection.cursor()
        try:
            cursor.execute("SELECT DISTINCT book FROM scriptures ORDER BY book")
            results = cursor.fetchall()
            return [row[0] for row in results]
        except sqlite3.Error as e:
            print(f"Error retrieving book names: {e}")
            return []
        finally:
            cursor.close()

    def get_chapters_for_book(self, translation, book):
        """Retrieves a sorted list of unique chapter numbers for a given book."""
        if not self.connection:
            return []

        cursor = self.connection.cursor()
        try:
            cursor.execute("""
                SELECT DISTINCT chapter FROM scriptures 
                WHERE translation = ? AND book = ? ORDER BY chapter
            """, (translation, book))
            results = cursor.fetchall()
            return [str(row[0]) for row in results] # Return as strings for completer
        except sqlite3.Error as e:
            print(f"Error retrieving chapter numbers: {e}")
            return []
        finally:
            cursor.close()

    def get_verses_for_chapter(self, translation, book, chapter):
        """Retrieves a sorted list of unique verse numbers for a given book and chapter."""
        if not self.connection:
            return []

        cursor = self.connection.cursor()
        try:
            cursor.execute("""
                SELECT DISTINCT verse_num FROM scriptures 
                WHERE translation = ? AND book = ? AND chapter = ? ORDER BY verse_num
            """, (translation, book, chapter))
            results = cursor.fetchall()
            return [str(row[0]) for row in results] # Return as strings for completer
        except sqlite3.Error as e:
            print(f"Error retrieving verse numbers: {e}")
            return []
        finally:
            cursor.close()

    def close_connection(self):
        """Closes the database connection."""
        if self.connection:
            self.connection.close()
            print("Database connection closed.")

    def _create_spoken_word_map(self):
        """
        Creates an internal dictionary to map spoken variations of book names.
        This is a foundational implementation. A more robust solution might
        use fuzzy matching or a more extensive list.
        """
        self.spoken_word_map = {
            "first corinthians": "1 Corinthians",
            "second corinthians": "2 Corinthians",
            "one corinthians": "1 Corinthians",
            "two corinthians": "2 Corinthians",
            "genesis": "Genesis",
            "exodus": "Exodus",
            "leviticus": "Leviticus",
            "numbers": "Numbers",
            "deuteronomy": "Deuteronomy",
            "joshua": "Joshua",
            "judges": "Judges",
            "ruth": "Ruth",
            "first samuel": "1 Samuel",
            "second samuel": "2 Samuel",
            "first kings": "1 Kings",
            "second kings": "2 Kings",
            "first chronicles": "1 Chronicles",
            "second chronicles": "2 Chronicles",
            "ezra": "Ezra",
            "nehemiah": "Nehemiah",
            "esther": "Esther",
            "job": "Job",
            "psalms": "Psalm",
            "proverbs": "Proverbs",
            "ecclesiastes": "Ecclesiastes",
            "song of solomon": "Song of Solomon",
            "isaiah": "Isaiah",
            "jeremiah": "Jeremiah",
            "lamentations": "Lamentations",
            "ezekiel": "Ezekiel",
            "daniel": "Daniel",
            "hosea": "Hosea",
            "joel": "Joel",
            "amos": "Amos",
            "obadiah": "Obadiah",
            "jonah": "Jonah",
            "micah": "Micah",
            "nahum": "Nahum",
            "habakkuk": "Habakkuk",
            "zephaniah": "Zephaniah",
            "haggai": "Haggai",
            "zechariah": "Zechariah",
            "malachi": "Malachi",
            "matthew": "Matthew",
            "mark": "Mark",
            "luke": "Luke",
            "john": "John",
            "acts": "Acts",
            "romans": "Romans",
            "first timothy": "1 Timothy",
            "second timothy": "2 Timothy",
            "titus": "Titus",
            "philemon": "Philemon",
            "hebrews": "Hebrews",
            "james": "James",
            "first peter": "1 Peter",
            "second peter": "2 Peter",
            "first john": "1 John",
            "second john": "2 John",
            "third john": "3 John",
            "jude": "Jude",
            "revelation": "Revelation"
        }

if __name__ == '__main__':
    # Example Usage:
    # This demonstrates how to set up and use the DataEngine.
    # In the main application, the db_path would be configured more robustly.
    
    db_file = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'bible.db')
    
    # Ensure the data directory exists
    os.makedirs(os.path.dirname(db_file), exist_ok=True)

    engine = DataEngine(db_file)
    engine.setup_database()

    # In a real scenario, you would have a separate process to populate the DB
    # with KJV, NIV, and Amplified scriptures.

    # --- Test Cases ---
    def run_tests():
        print("\nRunning DataEngine tests...")
        # 1. Test with an empty database
        verse = engine.get_verse('KJV', 'John', 3, 16)
        assert verse is None
        print("Test passed: Verse not found in empty DB.")

        # 2. Test inserting and retrieving a verse
        cursor = engine.connection.cursor()
        try:
            cursor.execute("""
                INSERT INTO scriptures (translation, book, chapter, verse_num, text)
                VALUES ('KJV', 'Genesis', 1, 1, 'In the beginning God created the heaven and the earth.')
            """)
            engine.connection.commit()
            print("Test data inserted.")

            verse = engine.get_verse('KJV', 'genesis', 1, 1) # Test with lowercase book
            assert verse == 'In the beginning God created the heaven and the earth.'
            print("Test passed: Successfully retrieved inserted verse.")

            # 3. Test retrieving book names, chapters, and verses
            books = engine.get_all_book_names()
            assert "Genesis" in books
            print(f"Test passed: get_all_book_names() -> {books}")

            chapters = engine.get_chapters_for_book('KJV', 'Genesis')
            assert "1" in chapters
            print(f"Test passed: get_chapters_for_book() -> {chapters}")

            verses = engine.get_verses_for_chapter('KJV', 'Genesis', 1)
            assert "1" in verses
            print(f"Test passed: get_verses_for_chapter() -> {verses}")

        except sqlite3.Error as e:
            print(f"An error occurred during tests: {e}")
        finally:
            # Clean up the test entry
            cursor.execute("DELETE FROM scriptures WHERE book = 'Genesis'")
            engine.connection.commit()
            cursor.close()
            print("Test data cleaned up.")

    run_tests()
    engine.close_connection()
