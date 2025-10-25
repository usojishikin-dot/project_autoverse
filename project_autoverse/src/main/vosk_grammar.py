
# vosk_grammar.py

"""
This file contains the custom vocabulary for the Vosk speech recognizer.
A well-defined grammar significantly improves the accuracy of recognizing
domain-specific terms, such as Bible book names and church terminology.
"""

import json

# --- Static Vocabulary List ---

BIBLE_BOOKS = [
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy", "Joshua", "Judges", "Ruth",
    "First Samuel", "Second Samuel", "First Kings", "Second Kings", "First Chronicles", "Second Chronicles",
    "Ezra", "Nehemiah", "Esther", "Job", "Psalms", "Proverbs", "Ecclesiastes", "Song of Solomon",
    "Isaiah", "Jeremiah", "Lamentations", "Ezekiel", "Daniel", "Hosea", "Joel", "Amos", "Obadiah",
    "Jonah", "Micah", "Nahum", "Habakkuk", "Zephaniah", "Haggai", "Zechariah", "Malachi",
    "Matthew", "Mark", "Luke", "John", "Acts", "Romans", "First Corinthians", "Second Corinthians",
    "Galatians", "Ephesians", "Philippians", "Colossians", "First Thessalonians", "Second Thessalonians",
    "First Timothy", "Second Timothy", "Titus", "Philemon", "Hebrews", "James", "First Peter", "Second Peter",
    "First John", "Second John", "Third John", "Jude", "Revelation"
]

ORDINAL_NUMBERS = [
    "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
    "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen", "twenty",
    "first", "second", "third"
]

CITATION_CONNECTORS = [
    "chapter", "verse", "to", "through", "let's read", "turn to", "referencing"
]

CHURCH_TERMS = [
    "Apostle", "Elder", "Deacon", "Doxology", "Eucharist", "Trinity", "Baptism"
]

# --- Grammar Generation ---

def generate_vosk_grammar():
    """
    Generates a JSON grammar string for the Vosk KaldiRecognizer.
    This function combines all the vocabulary lists into a single,
    properly formatted string that biases the recognizer towards
    these specific terms.

    :return: A JSON-formatted string containing the custom vocabulary.
    """
    # Combine all vocabulary lists
    full_vocabulary = BIBLE_BOOKS + ORDINAL_NUMBERS + CITATION_CONNECTORS + CHURCH_TERMS

    # Remove duplicates and convert to lowercase
    unique_vocabulary = sorted(list(set([word.lower() for word in full_vocabulary])))

    # Create the grammar structure expected by Vosk
    grammar = {
        "text": "[unk]",
        "words": unique_vocabulary
    }

    # Return as a JSON string
    return json.dumps(grammar)

if __name__ == '__main__':
    # Example of how to generate and view the grammar
    generated_grammar = generate_vosk_grammar()
    print("Generated Vosk Grammar:")
    print(json.dumps(json.loads(generated_grammar), indent=2))
