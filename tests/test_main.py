import pytest
import json
import os
from unittest.mock import patch, MagicMock, ANY
from fastapi.testclient import TestClient
import sqlite3 # For type checking in DB test
from datetime import datetime # For type checking in DB test

# Add project root to sys.path to allow imports from 'app'
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the FastAPI app and other necessary components from main.py
# We need to set up environment variables BEFORE importing main
os.environ["VERIFY_TOKEN"] = "test_verify_token"
os.environ["FACEBOOK_PAGE_ACCESS_TOKEN"] = "test_fb_access_token"
os.environ["OPENAI_API_KEY"] = "test_openai_api_key" # Required by ResponseGenerator
os.environ["MCP_API_KEY"] = "test_mcp_api_key" # Required by MCPHandler

from app.main import app, summarize_conversation_and_store, DATABASE_FILE
from app.response_generator import ResponseGenerator
from app.mcp_handler import MCPHandler


# TestClient for FastAPI
client = TestClient(app)

# Sample webhook data
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


@pytest.fixture(autouse=True)
def cleanup_db_after_tests():
    """Ensure the DB is clean after tests that might create/modify it."""
    yield
    if os.path.exists(DATABASE_FILE):
        try:
            os.remove(DATABASE_FILE)
            print(f"\nCleaned up test database: {DATABASE_FILE}")
        except PermissionError:
            print(f"\nWarning: Could not remove test database {DATABASE_FILE} due to PermissionError.")
        except Exception as e:
            print(f"\nWarning: Error removing test database {DATABASE_FILE}: {e}")


@patch('app.main.requests.post')
@patch('app.main.summarize_conversation_and_store', return_value=None) # Disable summarization for this test
@patch('app.main.response_generator_instance.generate') # Mock the generate function
def test_dm_sending(mock_rg_generate, mock_summarize, mock_requests_post):
    """Test that a DM is sent correctly via requests.post."""
    mock_rg_generate.return_value = {"reply": "Test reply from RG", "booking_details": None}
    mock_requests_post.return_value = MagicMock(status_code=200) # Mock successful post

    response = client.post("/webhook", json=SAMPLE_WEBHOOK_DATA)
    assert response.status_code == 200
    assert response.json() == {"status": "done"}

    expected_url = "https://graph.facebook.com/v18.0/me/messages"
    expected_headers = {
        "Authorization": f"Bearer test_fb_access_token",
        "Content-Type": "application/json"
    }
    expected_payload = {
        "recipient": {"id": "user123"},
        "message": {"text": "Test reply from RG"},
        "messaging_type": "RESPONSE"
    }

    mock_requests_post.assert_called_once_with(
        expected_url,
        headers=expected_headers,
        json=expected_payload
    )
    mock_summarize.assert_called_once() # Check if it was called


@patch('app.main.response_generator_instance.summarize')
@patch('app.main.sqlite3.connect')
@patch('app.main.requests.post') # Mock requests.post to prevent actual DM sending
@patch('app.main.response_generator_instance.generate') # Mock generate for this test
def test_summarization_and_db_storage(mock_rg_generate, mock_requests_post, mock_sqlite_connect, mock_rg_summarize):
    """Test conversation summarization and database storage."""
    # Setup mocks
    mock_rg_generate.return_value = {"reply": "DB test reply", "booking_details": None}
    mock_rg_summarize.return_value = "This is a test summary."
    
    # Mock the DB connection and cursor
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_sqlite_connect.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor

    # Simulate webhook event by calling the function directly, or using TestClient
    # For this specific test, directly calling summarize_conversation_and_store might be easier
    # after mocking the history.
    # However, to test the flow through the webhook:
    
    # Manually set up memory for the user as if a conversation happened
    # This is a bit of a deeper mock, normally ConversationChain would handle this.
    # For simplicity, we'll assume the memory is populated correctly by ResponseGenerator.
    # The summarization function in main.py retrieves history from response_generator_instance.memories
    with patch.dict(app.main.response_generator_instance.memories, {}, clear=True): # Ensure clean state
        app.main.response_generator_instance.memories['user123'] = MagicMock()
        app.main.response_generator_instance.memories['user123'].chat_memory.messages = [
            MagicMock(content="Hello there!"), # Mocking HumanMessage
            MagicMock(content="DB test reply")  # Mocking AIMessage
        ]

        client.post("/webhook", json=SAMPLE_WEBHOOK_DATA) # Trigger the webhook

    mock_sqlite_connect.assert_called_once_with(DATABASE_FILE)
    mock_conn.commit.assert_called_once()
    mock_cursor.execute.assert_called_once()

    # Check the SQL INSERT query (args[0] of the call)
    args, _ = mock_cursor.execute.call_args
    sql_query = args[0]
    sql_params = args[1]

    assert "INSERT INTO conversations (customer_id, conversation_time, summary)" in sql_query
    assert sql_params[0] == "user123"
    assert isinstance(sql_params[1], datetime) # Check if it's a datetime object
    assert sql_params[2] == "This is a test summary."
    mock_rg_summarize.assert_called_once()


@patch('app.main.requests.post') # Mock for DM sending
@patch('app.main.mcp_handler_instance.make_reservation')
@patch('app.main.response_generator_instance.generate')
@patch('app.main.summarize_conversation_and_store', return_value=None) # Disable summarization for this test
def test_mcp_integration_flow_success(mock_summarize, mock_rg_generate, mock_mcp_make_reservation, mock_dm_requests_post):
    """Test the MCP integration flow for a successful reservation."""
    
    booking_params = {'date': '2023-10-10', 'time': '14:00', 'people': 1, 'service': 'Tire Change'}
    mock_rg_generate.return_value = {
        "reply": "Okay, let me check that for you.",
        "booking_details": booking_params
    }
    
    mcp_success_response = {
        "success": True,
        "booking_id": "MCP12345",
        "message": "Reservation confirmed for Tire Change on 2023-10-10 at 14:00."
    }
    mock_mcp_make_reservation.return_value = mcp_success_response
    mock_dm_requests_post.return_value = MagicMock(status_code=200)

    response = client.post("/webhook", json=SAMPLE_BOOKING_WEBHOOK_DATA)
    assert response.status_code == 200

    mock_mcp_make_reservation.assert_called_once_with(booking_params)
    
    # Assert that the final DM sent to the user includes MCP response
    dm_call_args = mock_dm_requests_post.call_args
    dm_payload = dm_call_args.kwargs['json']
    
    expected_final_reply = "Okay, let me check that for you."
    expected_final_reply += f"\n\n🎉 예약 성공! {mcp_success_response['message']} (ID: {mcp_success_response['booking_id']})"
    
    assert dm_payload['message']['text'] == expected_final_reply
    mock_summarize.assert_called_once()


@patch('app.main.requests.post') # Mock for DM sending
@patch('app.main.mcp_handler_instance.make_reservation')
@patch('app.main.response_generator_instance.generate')
@patch('app.main.summarize_conversation_and_store', return_value=None) # Disable summarization
def test_mcp_integration_flow_failure(mock_summarize, mock_rg_generate, mock_mcp_make_reservation, mock_dm_requests_post):
    """Test the MCP integration flow for a failed reservation."""
    booking_params = {'date': '2023-10-11', 'time': '10:00', 'people': 2, 'service': 'Oil Change'}
    mock_rg_generate.return_value = {
        "reply": "Checking for oil change availability...",
        "booking_details": booking_params
    }
    
    mcp_failure_response = {
        "success": False,
        "message": "Sorry, no slots available for Oil Change on that day."
    }
    mock_mcp_make_reservation.return_value = mcp_failure_response
    mock_dm_requests_post.return_value = MagicMock(status_code=200)

    response = client.post("/webhook", json=SAMPLE_BOOKING_WEBHOOK_DATA) # Use appropriate data
    assert response.status_code == 200

    mock_mcp_make_reservation.assert_called_once_with(booking_params)
    
    dm_call_args = mock_dm_requests_post.call_args
    dm_payload = dm_call_args.kwargs['json']
    
    expected_final_reply = "Checking for oil change availability..."
    expected_final_reply += f"\n\n⚠️ 예약 실패: {mcp_failure_response['message']}"
    
    assert dm_payload['message']['text'] == expected_final_reply
    mock_summarize.assert_called_once()

# Basic test for webhook verification (GET request)
def test_webhook_verification():
    """Test the webhook verification GET request."""
    params = {
        "hub.mode": "subscribe",
        "hub.verify_token": "test_verify_token",
        "hub.challenge": "12345"
    }
    response = client.get("/webhook", params=params)
    assert response.status_code == 200
    assert response.text == "12345"

def test_webhook_verification_invalid_token():
    """Test webhook verification with an invalid token."""
    params = {
        "hub.mode": "subscribe",
        "hub.verify_token": "wrong_token",
        "hub.challenge": "12345"
    }
    response = client.get("/webhook", params=params)
    assert response.status_code == 403
    assert response.json() == {"error": "Invalid token"}

if __name__ == "__main__":
    pytest.main()
