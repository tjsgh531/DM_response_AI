import pytest
import os
import sqlite3

# Add project root to sys.path to allow import of init_db
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the function to be tested
from init_db import initialize_database, DATABASE_FILE # DATABASE_FILE is 'chat_history.db'

@pytest.fixture(scope="function") # Use function scope for cleaner state between tests if this file had more
def db_cleanup():
    """Fixture to ensure the database file is removed before and after the test."""
    # Remove DB if it exists from a previous failed run
    if os.path.exists(DATABASE_FILE):
        os.remove(DATABASE_FILE)
    
    yield # This is where the test runs

    # Cleanup after the test
    if os.path.exists(DATABASE_FILE):
        try:
            os.remove(DATABASE_FILE)
            print(f"\nCleaned up test database: {DATABASE_FILE}")
        except Exception as e:
            print(f"\nError during cleanup: {e}")


def test_initialize_database_creates_table(db_cleanup):
    """
    Tests that initialize_database creates the 'conversations' table
    in the specified database file.
    """
    # Ensure the DB file does not exist before the test
    assert not os.path.exists(DATABASE_FILE), "Database file should not exist at the start of this test."

    # Call the function to initialize the database
    # Capture print output to check success message (optional)
    with patch('builtins.print') as mock_print:
        initialize_database()
    
    # Assert that the success message was printed
    db_abs_path = os.path.abspath(DATABASE_FILE)
    mock_print.assert_any_call(f"Database initialized and 'conversations' table created successfully at {db_abs_path}.")

    # Assert that the database file was created
    assert os.path.exists(DATABASE_FILE), "Database file was not created."

    conn = None
    try:
        # Connect to the newly created database
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        # Query the sqlite_master table to check for the 'conversations' table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='conversations';")
        table_exists = cursor.fetchone()

        assert table_exists is not None, "'conversations' table was not found in the database."
        assert table_exists[0] == "conversations", "Table found but name doesn't match 'conversations'."

        # Optionally, check table schema (column names)
        cursor.execute("PRAGMA table_info(conversations);")
        columns_info = cursor.fetchall()
        # Expected columns: (column_id, name, type, notnull, default_value, primary_key)
        expected_columns = {
            "customer_id": "TEXT",
            "conversation_time": "TIMESTAMP", # SQLite stores this as TEXT, NUMERIC, INTEGER, REAL, or BLOB. Often NUMERIC or TEXT.
            "summary": "TEXT"
        }
        
        actual_columns = {info[1]: info[2] for info in columns_info}

        for col_name, col_type in expected_columns.items():
            assert col_name in actual_columns, f"Column '{col_name}' not found."
            # SQLite type affinity can be tricky. TEXT is generally safe. TIMESTAMP might become NUMERIC.
            # This check is simplified; more robust checks might consider type affinity.
            assert actual_columns[col_name] == col_type, \
                f"Column '{col_name}' has type '{actual_columns[col_name]}' but expected '{col_type}'."
            # Check for NOT NULL constraints if important
            if col_name in ["customer_id", "conversation_time", "summary"]: # All are NOT NULL
                 column_details = next(c for c in columns_info if c[1] == col_name)
                 assert column_details[3] == 1, f"Column '{col_name}' should be NOT NULL."


    except sqlite3.Error as e:
        pytest.fail(f"SQLite error occurred: {e}")
    finally:
        if conn:
            conn.close()
    
    # db_cleanup fixture handles removal

def test_initialize_database_idempotency(db_cleanup):
    """
    Tests that calling initialize_database multiple times does not cause errors
    (e.g., trying to create a table that already exists).
    """
    assert not os.path.exists(DATABASE_FILE), "Database file should not exist at the start."

    # Call initialize_database the first time
    initialize_database()
    assert os.path.exists(DATABASE_FILE), "Database file should have been created after first call."

    # Call initialize_database a second time
    try:
        with patch('builtins.print') as mock_print_again:
            initialize_database()
        # Should not raise an error, and print success message
        db_abs_path = os.path.abspath(DATABASE_FILE)
        mock_print_again.assert_any_call(f"Database initialized and 'conversations' table created successfully at {db_abs_path}.")

    except Exception as e:
        pytest.fail(f"Calling initialize_database a second time raised an error: {e}")

    # Verify table still exists and is correctly structured (optional, covered by first test)
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='conversations';")
        table_exists = cursor.fetchone()
        assert table_exists is not None, "'conversations' table should still exist."
    except sqlite3.Error as e:
        pytest.fail(f"SQLite error occurred on second check: {e}")
    finally:
        if conn:
            conn.close()
    
    # db_cleanup fixture handles removal

if __name__ == "__main__":
    pytest.main()
