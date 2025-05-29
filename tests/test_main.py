import pytest
import json
import os
from unittest.mock import patch, MagicMock, ANY
from fastapi.testclient import TestClient
# No longer need sqlite3, import psycopg2 for error types if needed for side_effects
# import psycopg2
from datetime import datetime

# Add project root to sys.path
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set up environment variables BEFORE importing main and its components
MOCK_ENV_VARS = {
    "VERIFY_TOKEN": "test_verify_token",
    "FACEBOOK_PAGE_ACCESS_TOKEN": "test_fb_access_token",
    "OPENAI_API_KEY": "test_openai_api_key",
    "MCP_API_KEY": "test_mcp_api_key",
    # Add mock DB env vars for PostgreSQL, used by summarize_conversation_and_store
    "DB_HOST": "mock_db_host",
    "DB_PORT": "5432",
    "DB_USER": "mock_db_user",
    "DB_PASSWORD": "mock_db_password",
    "DB_NAME": "mock_db_name"
}

# It's crucial to patch os.environ BEFORE app.main is imported if it reads env vars at module level
# For FastAPI, TestClient handles app loading, but direct imports from main might happen sooner.
# The `app.main.summarize_conversation_and_store` directly calls os.getenv.
# So, patching os.environ globally or specifically where needed is important.
# Using @patch.dict(os.environ, MOCK_ENV_VARS) in relevant test functions is safer.

# Patch load_dotenv globally for all tests in this file, or selectively.
# If app.main.load_dotenv() is called at module level, it might be too early.
# The current app.main.py calls load_dotenv() at the top.
# We can mock it to prevent it from overriding our test environment variables.
global_load_dotenv_patch = patch('app.main.load_dotenv', MagicMock())
global_load_dotenv_patch.start() # Start it before app.main is imported by TestClient or direct imports

from app.main import app #, summarize_conversation_and_store # summarize_conversation_and_store is tested via webhook
# from app.response_generator import ResponseGenerator # Not directly used in these tests
# from app.mcp_handler import MCPHandler # Not directly used in these tests

# Stop the global patch if you only want it for imports.
# global_load_dotenv_patch.stop()
# However, for this structure, keeping it active for the duration of tests is fine,
# as each test function can further refine os.environ using @patch.dict.


client = TestClient(app)

SAMPLE_WEBHOOK_DATA = {
    "entry": [{
        "changes": [{
            "value": {
                "message": {"text": "Hello there!"},
                "sender": {"id": "user123"}
            }
        }]
    }]
}

SAMPLE_BOOKING_WEBHOOK_DATA = {
    "entry": [{
        "changes": [{
            "value": {
                "message": {"text": "I want to book a tire change for tomorrow at 2 PM for 1 person."},
                "sender": {"id": "user789"}
            }
        }]
    }]
}

# Removed SQLite specific db_cleanup fixture
# PostgreSQL tests will mock the connection, no actual DB file created by tests.

@patch.dict(os.environ, MOCK_ENV_VARS, clear=True)
@patch('app.main.requests.post')
@patch('app.main.summarize_conversation_and_store', return_value=None) # Keep this mocked if not testing its DB part here
@patch('app.main.response_generator_instance.generate')
def test_dm_sending(mock_rg_generate, mock_summarize, mock_requests_post):
    mock_rg_generate.return_value = {"reply": "Test reply from RG", "booking_details": None}
    mock_requests_post.return_value = MagicMock(status_code=200)

    response = client.post("/webhook", json=SAMPLE_WEBHOOK_DATA)
    assert response.status_code == 200
    assert response.json() == {"status": "done"}

    expected_url = "https://graph.facebook.com/v18.0/me/messages"
    expected_headers = {
        "Authorization": f"Bearer {MOCK_ENV_VARS['FACEBOOK_PAGE_ACCESS_TOKEN']}",
        "Content-Type": "application/json"
    }
    expected_payload = {
        "recipient": {"id": "user123"},
        "message": {"text": "Test reply from RG"},
        "messaging_type": "RESPONSE"
    }
    mock_requests_post.assert_called_once_with(expected_url, headers=expected_headers, json=expected_payload)
    mock_summarize.assert_called_once()


@patch.dict(os.environ, MOCK_ENV_VARS, clear=True) # Ensure DB env vars are set
@patch('app.main.response_generator_instance.summarize') # Mock the LLM call for summary
@patch('app.main.psycopg2.connect') # Mock PostgreSQL connect
@patch('app.main.requests.post') # Mock DM sending
@patch('app.main.response_generator_instance.generate') # Mock main response generation
def test_summarization_and_db_storage_postgresql(mock_rg_generate, mock_dm_post, mock_psycopg2_connect, mock_rg_summarize):
    """Test conversation summarization and PostgreSQL database storage."""
    sender_id = "user_db_test"
    test_summary_text = "This is a PostgreSQL test summary."
    
    # Configure mocks
    mock_rg_generate.return_value = {"reply": "DB test reply", "booking_details": None}
    mock_rg_summarize.return_value = test_summary_text # Output from summarize method
    
    # Mock the DB connection and cursor for psycopg2
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_psycopg2_connect.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor
    # Ensure the cursor can be used in a 'with' statement
    mock_cursor.__enter__.return_value = mock_cursor
    mock_cursor.__exit__.return_value = None # Important for context manager

    # Simulate memory state for summarization
    # This needs to point to where app.main accesses memories, which is response_generator_instance.memories
    with patch.dict(app.main.response_generator_instance.memories, {}, clear=True):
        # Ensure response_generator_instance exists; it's created globally in app.main
        app.main.response_generator_instance.memories[sender_id] = MagicMock()
        # Mocking HumanMessage and AIMessage content for history string generation
        app.main.response_generator_instance.memories[sender_id].chat_memory.messages = [
            MagicMock(content="Hello for DB!"), 
            MagicMock(content="DB test reply") 
        ]
        
        # Trigger the webhook which will call summarize_conversation_and_store
        webhook_data_for_db_test = {
            "entry": [{"changes": [{"value": {"message": {"text": "Hello for DB!"}, "sender": {"id": sender_id}}}]}]
        }
        client.post("/webhook", json=webhook_data_for_db_test)

    # Verify psycopg2.connect was called with correct parameters from MOCK_ENV_VARS
    mock_psycopg2_connect.assert_called_once_with(
        dbname=MOCK_ENV_VARS["DB_NAME"],
        user=MOCK_ENV_VARS["DB_USER"],
        password=MOCK_ENV_VARS["DB_PASSWORD"],
        host=MOCK_ENV_VARS["DB_HOST"],
        port=MOCK_ENV_VARS["DB_PORT"]
    )
    
    # Verify commit was called
    mock_conn.commit.assert_called_once()
    mock_cursor.execute.assert_called_once()

    # Check the SQL INSERT query and parameters
    args, _ = mock_cursor.execute.call_args
    sql_query = args[0]
    sql_params = args[1]

    assert "INSERT INTO conversations (customer_id, conversation_time, summary)" in sql_query
    assert sql_params[0] == sender_id
    assert isinstance(sql_params[1], datetime) # Check if it's a datetime object
    assert sql_params[2] == test_summary_text
    
    mock_rg_summarize.assert_called_once() # Ensure ResponseGenerator.summarize was called


@patch.dict(os.environ, MOCK_ENV_VARS, clear=True)
@patch('app.main.requests.post')
@patch('app.main.mcp_handler_instance.make_reservation')
@patch('app.main.response_generator_instance.generate')
@patch('app.main.summarize_conversation_and_store', return_value=None) # Mock out summarization
def test_mcp_integration_flow_success(mock_summarize, mock_rg_generate, mock_mcp_make_reservation, mock_dm_requests_post):
    booking_params = {'date': '2023-10-10', 'time': '14:00', 'people': 1, 'service': 'Tire Change'}
    mock_rg_generate.return_value = {"reply": "Okay, let me check.", "booking_details": booking_params}
    mcp_success_response = {"success": True, "booking_id": "MCP12345", "message": "Booked."}
    mock_mcp_make_reservation.return_value = mcp_success_response
    mock_dm_requests_post.return_value = MagicMock(status_code=200)

    response = client.post("/webhook", json=SAMPLE_BOOKING_WEBHOOK_DATA)
    assert response.status_code == 200
    mock_mcp_make_reservation.assert_called_once_with(booking_params)
    
    dm_payload = mock_dm_requests_post.call_args.kwargs['json']
    expected_reply = f"Okay, let me check.\n\n🎉 예약 성공! {mcp_success_response['message']} (ID: {mcp_success_response['booking_id']})"
    assert dm_payload['message']['text'] == expected_reply
    mock_summarize.assert_called_once()


@patch.dict(os.environ, MOCK_ENV_VARS, clear=True)
@patch('app.main.requests.post')
@patch('app.main.mcp_handler_instance.make_reservation')
@patch('app.main.response_generator_instance.generate')
@patch('app.main.summarize_conversation_and_store', return_value=None) # Mock out summarization
def test_mcp_integration_flow_failure(mock_summarize, mock_rg_generate, mock_mcp_make_reservation, mock_dm_requests_post):
    booking_params = {'date': '2023-10-11', 'time': '10:00', 'people': 2, 'service': 'Oil Change'}
    mock_rg_generate.return_value = {"reply": "Checking...", "booking_details": booking_params}
    mcp_failure_response = {"success": False, "message": "Slot unavailable."}
    mock_mcp_make_reservation.return_value = mcp_failure_response
    mock_dm_requests_post.return_value = MagicMock(status_code=200)

    # Use a different sender ID for this test to avoid memory collision if tests run in parallel
    # or if memory isn't cleared perfectly between tests.
    # However, with patch.dict for memories, it should be fine.
    # Using SAMPLE_BOOKING_WEBHOOK_DATA which has sender_id "user789"
    response = client.post("/webhook", json=SAMPLE_BOOKING_WEBHOOK_DATA) 
    assert response.status_code == 200
    mock_mcp_make_reservation.assert_called_once_with(booking_params)
    
    dm_payload = mock_dm_requests_post.call_args.kwargs['json']
    expected_reply = f"Checking...\n\n⚠️ 예약 실패: {mcp_failure_response['message']}"
    assert dm_payload['message']['text'] == expected_reply
    mock_summarize.assert_called_once()


@patch.dict(os.environ, MOCK_ENV_VARS, clear=True)
def test_webhook_verification():
    params = {
        "hub.mode": "subscribe",
        "hub.verify_token": MOCK_ENV_VARS["VERIFY_TOKEN"],
        "hub.challenge": "12345"
    }
    response = client.get("/webhook", params=params)
    assert response.status_code == 200
    assert response.text == "12345"

@patch.dict(os.environ, MOCK_ENV_VARS, clear=True)
def test_webhook_verification_invalid_token():
    params = {
        "hub.mode": "subscribe",
        "hub.verify_token": "wrong_token", # Different from MOCK_ENV_VARS["VERIFY_TOKEN"]
        "hub.challenge": "12345"
    }
    response = client.get("/webhook", params=params)
    assert response.status_code == 403
    assert response.json() == {"error": "Invalid token"}

# Teardown for the global patch if started
# This ensures that other test files are not affected if pytest runs them in the same session.
# However, pytest typically isolates test files. For safety:
def teardown_module(module):
    global_load_dotenv_patch.stop()

if __name__ == "__main__":
    pytest.main()
