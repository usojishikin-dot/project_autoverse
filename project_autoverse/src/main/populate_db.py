
import csv
import os
from data_engine import DataEngine

def populate_from_csv(db_engine, csv_path, translation_name):
    """
    Populates the database from a CSV file.

    :param db_engine: An instance of the DataEngine.
    :param csv_path: The path to the CSV file.
    :param translation_name: The name of the translation (e.g., 'KJV').
    """
    if not os.path.exists(csv_path):
        print(f"Error: CSV file not found at {csv_path}")
        print("Please ensure you have downloaded the file and placed it in the correct directory.")
        return

    print(f"Populating database with {translation_name} translation from {csv_path}...")

    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            # Skipping header row if it exists. Adjust if your CSV doesn't have a header.
            next(reader, None)  

            cursor = db_engine.connection.cursor()
            verses_to_insert = []
            for row in reader:
                                try:
                                    # Corrected indices: Book Name=1, Chapter=3, Verse=4, Text=5
                                    book_name = row[1]
                                    chapter = int(row[3])
                                    verse_num = int(row[4])
                                    text = row[5]
                                    verses_to_insert.append((translation_name, book_name, chapter, verse_num, text))
                                except (IndexError, ValueError) as e:                    print(f"Skipping malformed row: {row} - Error: {e}")

            # Use executemany for efficient bulk insertion
            cursor.executemany("""
                INSERT INTO scriptures (translation, book, chapter, verse_num, text)
                VALUES (?, ?, ?, ?, ?)
            """, verses_to_insert)

            db_engine.connection.commit()
            print(f"Successfully inserted {len(verses_to_insert)} verses.")

    except Exception as e:
        print(f"An error occurred during database population: {e}")
    finally:
        if cursor:
            cursor.close()

if __name__ == '__main__':
    # --- Configuration ---
    DB_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'bible.db')
    KJV_CSV_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 't_kjv.csv')
    
    # --- Execution ---
    # Initialize the data engine
    engine = DataEngine(DB_FILE)
    engine.connect()
    # Ensure the table is created
    engine.setup_database() 

    # Populate with KJV data
    populate_from_csv(engine, KJV_CSV_PATH, 'KJV')

    # You would add calls for other translations here, e.g.:
    # NIV_CSV_PATH = os.path.join('..', 'data', 't_niv.csv')
    # populate_from_csv(engine, NIV_CSV_PATH, 'NIV')

    # Close the connection
    engine.close_connection()
    print("Database population process finished.")
