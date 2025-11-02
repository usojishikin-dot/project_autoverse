
import csv
import os
import logging
from data_engine import DataEngine

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def populate_from_csv(db_engine, csv_path, translation_name):
    """
    Populates the database from a CSV file after validating its structure.

    Args:
        db_engine (DataEngine): An instance of the DataEngine.
        csv_path (str): The path to the CSV file.
        translation_name (str): The name of the translation (e.g., 'KJV').
    """
    # --- 1. File Existence Check ---
    # Moved from the original code for early exit.
    if not os.path.exists(csv_path):
        logging.error(f"CSV file not found at {csv_path}")
        logging.warning("Please ensure you have downloaded the file and placed it in the correct directory.")
        return

    logging.info(f"Starting population for '{translation_name}' from {csv_path}...")

    # --- 2. Define required columns for validation ---
    required_columns = {'book', 'chapter', 'verse', 'text'}

    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)

            # --- 3. Header Validation ---
            # Reads the first row to check for required column names.
            try:
                header = next(reader)
                # Create a mapping from column name to index
                column_indices = {name.strip(): i for i, name in enumerate(header)}

                # Check if all required columns are present in the header
                if not required_columns.issubset(column_indices.keys()):
                    missing = required_columns - column_indices.keys()
                    logging.error(f"CSV file is missing required columns: {', '.join(missing)}")
                    return
            except StopIteration:
                logging.error("CSV file is empty.")
                return

            # --- 4. Database Insertion Logic ---
            # Correctly get a cursor from the connection object.
            cursor = db_engine.connection.cursor()

            verses_to_insert = []
            malformed_rows = 0

            for i, row in enumerate(reader, 1):
                try:
                    # Use the dynamically found indices for robust data extraction
                    book_name = row[column_indices['book']]
                    chapter = int(row[column_indices['chapter']])
                    verse_num = int(row[column_indices['verse']])
                    text = row[column_indices['text']]

                    verses_to_insert.append((translation_name, book_name, chapter, verse_num, text))
                except (IndexError, ValueError) as e:
                    # Log parsing errors for specific rows
                    logging.warning(f"Skipping malformed row #{i+1}: {row} - Error: {e}")
                    malformed_rows += 1

            # --- 5. Efficient Bulk Insertion ---
            # Use executemany for much faster inserts.
            if verses_to_insert:
                cursor.executemany("""
                    INSERT INTO scriptures (translation, book, chapter, verse_num, text)
                    VALUES (?, ?, ?, ?, ?)
                """, verses_to_insert)

                # Commit the transaction to save changes.
                db_engine.connection.commit()
                logging.info(f"Successfully inserted {len(verses_to_insert)} verses.")
            else:
                logging.warning("No valid verses found to insert.")

            if malformed_rows > 0:
                logging.warning(f"Skipped {malformed_rows} malformed rows.")

    except IOError as e:
        # --- 6. Improved Exception Handling ---
        # Catches file-related errors (e.g., permissions).
        logging.error(f"Could not read the file at {csv_path}: {e}")
    except Exception as e:
        # General exception for any other unexpected errors.
        logging.error(f"An unexpected error occurred: {e}")
        # In a transactional database, you might want to rollback here.
        # db_engine.connection.rollback()
    finally:
        # --- 7. Graceful Cleanup ---
        # Ensure the cursor is closed if it was created.
        if 'cursor' in locals() and cursor:
            cursor.close()

if __name__ == '__main__':
    # --- Configuration ---
    # Use absolute paths for reliability.
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DB_FILE = os.path.join(BASE_DIR, '..', '..', 'data', 'bible.db')
    KJV_CSV_PATH = os.path.join(BASE_DIR, '..', '..', 'data', 't_kjv.csv')
    
    # --- Execution ---
    # Initialize the data engine
    engine = DataEngine(DB_FILE)

    try:
        engine.connect()
        # Ensure the table is created before population
        engine.setup_database()

        # Populate with KJV data
        populate_from_csv(engine, KJV_CSV_PATH, 'KJV')

    except Exception as e:
        # Catch connection or setup errors
        logging.critical(f"A critical error occurred during initialization: {e}")
    finally:
        # Always close the connection
        engine.close_connection()
        logging.info("Database population process finished.")
