import pytest
import os

# Add project root to sys.path
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.mcp_handler import MCPHandler

# Test with a dummy API key, as the actual calls are mocked.
# In a real scenario with actual API calls, this might need to be a valid test key.
TEST_API_KEY = "test_mcp_api_key_for_handler"

@pytest.fixture
def mcp_handler_instance():
    """Fixture to create an MCPHandler instance."""
    # Temporarily set the environment variable if MCPHandler relies on it at import/init
    # os.environ["MCP_API_KEY"] = TEST_API_KEY 
    # The MCPHandler provided takes api_key as __init__ arg, so direct pass is fine.
    return MCPHandler(api_key=TEST_API_KEY)

def test_check_availability_placeholder(mcp_handler_instance):
    """
    Test the placeholder check_availability method.
    Ensures it can be called and returns a dictionary with expected keys.
    """
    sample_details = {'date': '2024-01-01', 'time': '10:00', 'people': 1, 'service': 'Tire Check'}
    response = mcp_handler_instance.check_availability(sample_details)

    assert isinstance(response, dict), "Response should be a dictionary."
    # Check for expected keys based on the placeholder logic
    assert "available" in response, "Response should contain 'available' key."
    # Depending on the mock logic, other keys like 'message' or 'slots' might be present.
    assert "message" in response, "Response should contain 'message' key."

    # Example specific to current mock logic in mcp_handler.py
    if sample_details['date'] == "2023-12-25":
        assert response['available'] is False
    else:
        assert response['available'] is True
        if "tire" in sample_details['service'].lower():
            assert "slots" in response

def test_make_reservation_placeholder_success(mcp_handler_instance):
    """
    Test the placeholder make_reservation method for a successful scenario.
    Ensures it can be called and returns a dictionary indicating success.
    """
    sample_details = {'date': '2024-01-02', 'time': '11:00', 'people': 1, 'service': 'Oil Change'}
    response = mcp_handler_instance.make_reservation(sample_details)

    assert isinstance(response, dict), "Response should be a dictionary."
    assert "success" in response, "Response should contain 'success' key."
    assert "message" in response, "Response should contain 'message' key."
    
    if response['success']:
        assert "booking_id" in response, "Successful response should contain 'booking_id'."
        assert response['booking_id'] is not None
    
    # Based on current mock logic
    assert response['success'] is True 
    assert "Reservation confirmed" in response['message']


def test_make_reservation_placeholder_failure_missing_info(mcp_handler_instance):
    """
    Test placeholder make_reservation for failure due to missing information.
    """
    sample_details_missing_time = {'date': '2024-01-03', 'service': 'Inspection'} # Missing time
    response = mcp_handler_instance.make_reservation(sample_details_missing_time)

    assert isinstance(response, dict)
    assert response.get('success') is False
    assert "Reservation failed: Date and time are required." in response.get('message', "")


def test_make_reservation_placeholder_failure_specific_slot(mcp_handler_instance):
    """
    Test placeholder make_reservation for failure on a specific problematic slot.
    """
    sample_details_problem_slot = {'date': '2024-01-04', 'time': '17:00', 'service': 'Full Check'}
    response = mcp_handler_instance.make_reservation(sample_details_problem_slot)

    assert isinstance(response, dict)
    assert response.get('success') is False
    assert "Sorry, the 5 PM slot just became unavailable." in response.get('message', "")


def test_mcp_handler_initialization_with_key(mcp_handler_instance):
    """Test that the MCPHandler initializes with the provided API key."""
    assert mcp_handler_instance.api_key == TEST_API_KEY


def test_mcp_handler_initialization_without_key():
    """Test MCPHandler initialization when API key is None or empty."""
    # Capture print output to check for warning
    with patch('builtins.print') as mock_print:
        handler_no_key = MCPHandler(api_key=None)
    assert handler_no_key.api_key is None
    mock_print.assert_called_with("⚠️ MCP_API_KEY is not set. MCPHandler may not function correctly.")

    with patch('builtins.print') as mock_print:
        handler_empty_key = MCPHandler(api_key="")
    assert handler_empty_key.api_key == ""
    mock_print.assert_called_with("⚠️ MCP_API_KEY is not set. MCPHandler may not function correctly.")


if __name__ == "__main__":
    pytest.main()
