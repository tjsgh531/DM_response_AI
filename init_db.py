import sqlite3
import os

# Define the database file path - this will create the DB in the current working directory
DATABASE_FILE = 'chat_history.db'

def initialize_database():
    """
    Initializes the SQLite database and creates the 'conversations' table
    if it doesn't already exist.
    """
    conn = None  # Initialize conn to None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                customer_id TEXT NOT NULL,
                conversation_time TIMESTAMP NOT NULL,
                summary TEXT NOT NULL
            )
        ''')

        conn.commit()
        # Get absolute path for clarity in the print message
        db_abs_path = os.path.abspath(DATABASE_FILE)
        print(f"Database initialized and 'conversations' table created successfully at {db_abs_path}.")

    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    initialize_database()
