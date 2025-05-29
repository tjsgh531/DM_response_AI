import pytest
import os
from unittest.mock import patch, MagicMock

# Add project root to sys.path to allow import of init_db
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the function to be tested
# Assuming init_db.py is now in the project root and uses psycopg2
from init_db import initialize_database

# Mock environment variables for database connection
MOCK_DB_ENV_VARS = {
    "DB_HOST": "test_host",
    "DB_PORT": "1234",
    "DB_USER": "test_user",
    "DB_PASSWORD": "test_password",
    "DB_NAME": "test_db"
}

@patch.dict(os.environ, MOCK_DB_ENV_VARS, clear=True) # Ensure clean env for each test
@patch('init_db.psycopg2.connect') # Mock the actual connect call
@patch('init_db.load_dotenv') # Mock load_dotenv as we are setting env vars directly
def test_initialize_database_success(mock_load_dotenv, mock_psycopg2_connect):
    """
    Tests successful database initialization and table creation for PostgreSQL.
    """
    # Configure the mock connection and cursor
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_psycopg2_connect.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor
    # Ensure the cursor can be used in a 'with' statement
    mock_cursor.__enter__.return_value = mock_cursor
    mock_cursor.__exit__.return_value = None

    # Call the function to initialize the database
    with patch('builtins.print') as mock_print: # To check print statements
        initialize_database()

    # Verify psycopg2.connect was called correctly
    mock_psycopg2_connect.assert_called_once_with(
        dbname=MOCK_DB_ENV_VARS["DB_NAME"],
        user=MOCK_DB_ENV_VARS["DB_USER"],
        password=MOCK_DB_ENV_VARS["DB_PASSWORD"],
        host=MOCK_DB_ENV_VARS["DB_HOST"],
        port=MOCK_DB_ENV_VARS["DB_PORT"]
    )

    # Verify the CREATE TABLE SQL statement
    executed_sql = mock_cursor.execute.call_args[0][0]
    assert "CREATE TABLE IF NOT EXISTS conversations" in executed_sql
    assert "id SERIAL PRIMARY KEY" in executed_sql
    assert "customer_id TEXT NOT NULL" in executed_sql
    assert "conversation_time TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP" in executed_sql
    assert "summary TEXT NOT NULL" in executed_sql
    
    # Verify commit was called
    mock_conn.commit.assert_called_once()
    
    # Verify print statements for success (optional, but good for confirming flow)
    mock_print.assert_any_call(f"Attempting to connect to PostgreSQL: User={MOCK_DB_ENV_VARS['DB_USER']}, DB={MOCK_DB_ENV_VARS['DB_NAME']}, Host={MOCK_DB_ENV_VARS['DB_HOST']}, Port={MOCK_DB_ENV_VARS['DB_PORT']}")
    mock_print.assert_any_call(f"✅ Database '{MOCK_DB_ENV_VARS['DB_NAME']}' initialized and 'conversations' table ensured successfully on host '{MOCK_DB_ENV_VARS['DB_HOST']}'.")
    mock_print.assert_any_call("🔌 PostgreSQL connection closed.")


@patch.dict(os.environ, {"DB_HOST": "test"}, clear=True) # Missing some variables
@patch('init_db.load_dotenv')
@patch('init_db.psycopg2.connect') # Should not be called if env vars are missing
def test_initialize_database_missing_env_vars(mock_psycopg2_connect, mock_load_dotenv):
    """
    Tests that initialization handles missing environment variables gracefully.
    (This assumes init_db.py checks for all required variables)
    """
    with patch('builtins.print') as mock_print:
        initialize_database()

    mock_psycopg2_connect.assert_not_called()
    mock_print.assert_any_call("❌ Error: Missing one or more database environment variables (DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, DB_PORT).")


@patch.dict(os.environ, MOCK_DB_ENV_VARS, clear=True)
@patch('init_db.psycopg2.connect', side_effect=psycopg2.OperationalError("Test connection error"))
@patch('init_db.load_dotenv')
def test_initialize_database_connection_error(mock_load_dotenv, mock_psycopg2_connect_op_error):
    """
    Tests error handling for psycopg2.OperationalError during connection.
    """
    # Import psycopg2 directly here ONLY for accessing the Error class, not for connect
    # This is needed because the module 'init_db' might not have 'psycopg2' in its global scope
    # if the import fails or is conditional. However, for side_effect, we need the type.
    # A better way might be to ensure 'psycopg2' is importable in the test file.
    import psycopg2 # Ensure psycopg2.OperationalError is defined for the side_effect

    with patch('builtins.print') as mock_print:
        initialize_database()

    mock_psycopg2_connect_op_error.assert_called_once()
    mock_print.assert_any_call("❌ PostgreSQL Operational Error: Test connection error")


@patch.dict(os.environ, MOCK_DB_ENV_VARS, clear=True)
@patch('init_db.psycopg2.connect')
@patch('init_db.load_dotenv')
def test_initialize_database_idempotency(mock_load_dotenv, mock_psycopg2_connect_idem):
    """
    Tests that calling initialize_database multiple times (if it were to run again)
    uses 'CREATE TABLE IF NOT EXISTS', which is inherently idempotent.
    The test structure is similar to the success case.
    """
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_psycopg2_connect_idem.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.__enter__.return_value = mock_cursor
    mock_cursor.__exit__.return_value = None

    # First call
    initialize_database()
    
    # Assertions for the first call (as in test_initialize_database_success)
    assert "CREATE TABLE IF NOT EXISTS conversations" in mock_cursor.execute.call_args[0][0]
    mock_conn.commit.assert_called_once()

    # Reset mocks for a hypothetical second call if needed, or simply assert
    # that the SQL itself is idempotent.
    # If the script were called twice, the mocks would need resetting for the second call.
    # Here, we are testing one execution of initialize_database, which should use "IF NOT EXISTS".
    
    # (No actual second call in this test, as the SQL handles idempotency)
    # This test mainly verifies the SQL contains "IF NOT EXISTS".
    # The previous success test already covers this.
    # If we wanted to test calling the Python function twice:
    # initialize_database() # Second call
    # mock_psycopg2_connect_idem.assert_called_with(...) # Check calls
    # mock_cursor.execute.assert_any_call(...) # Check SQL again for the second call
    # mock_conn.commit.call_count == 2

    # For this test, confirming "IF NOT EXISTS" is sufficient as that ensures SQL-level idempotency.
    # The test_initialize_database_success already verifies this.
    # This test can be simplified or merged if it doesn't add much beyond that.
    # Keeping it to emphasize the idempotency aspect of the SQL.
    pass # The core check is already in test_initialize_database_success


if __name__ == "__main__":
    # This is needed if you want to run this test file directly using `python tests/test_init_db.py`
    # It also allows importing psycopg2 for the side_effect in test_initialize_database_connection_error
    import psycopg2 
    pytest.main()
