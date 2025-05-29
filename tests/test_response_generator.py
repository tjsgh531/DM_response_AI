import pytest
import json
import os
from unittest.mock import patch, MagicMock, ANY

# Add project root to sys.path
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.response_generator import ResponseGenerator
from langchain.memory import ConversationBufferMemory
from langchain.schema import HumanMessage, AIMessage # For checking prompt contents

# Mock OPENAI_API_KEY before importing ResponseGenerator if it's accessed at import time
# However, it's passed in __init__, so direct instantiation is fine.

@pytest.fixture
def rg_instance():
    """Fixture to create a ResponseGenerator instance."""
    return ResponseGenerator(api_key="test_openai_api_key_for_rg")

def test_conversation_memory_initialization(rg_instance):
    """Test that memory is initialized for a new sender_id."""
    assert len(rg_instance.memories) == 0
    
    # Mock the ConversationChain.predict to avoid actual LLM calls
    with patch.object(rg_instance.llm, 'invoke', return_value=MagicMock(content="Hello back!")) as mock_llm_invoke:
      with patch('langchain.chains.ConversationChain.predict', return_value="Hello back!") as mock_predict:
        rg_instance.generate(message_text="Hello", sender_id="user1")
    
    assert "user1" in rg_instance.memories
    assert isinstance(rg_instance.memories["user1"], ConversationBufferMemory)
    assert len(rg_instance.memories) == 1

@patch('langchain.chains.ConversationChain.predict')
def test_conversation_memory_context_maintenance(mock_predict, rg_instance):
    """Test that conversation context is maintained for the same sender_id."""
    sender_id = "user_context_test"

    # First interaction
    mock_predict.return_value = "Response 1"
    rg_instance.generate(message_text="First message", sender_id=sender_id)
    
    # Check that the memory for sender_id was created
    assert sender_id in rg_instance.memories
    memory_for_sender = rg_instance.memories[sender_id]
    
    # We expect ConversationChain's memory to have the first message and response
    # The prompt passed to predict will contain this history.
    # The actual prompt formatting is handled by ConversationChain.
    # We can check that memory.chat_memory.messages contains the expected sequence.
    
    assert len(memory_for_sender.chat_memory.messages) == 2 # Human: First message, AI: Response 1
    assert memory_for_sender.chat_memory.messages[0].content == "First message" # Input to chain, effectively
    assert memory_for_sender.chat_memory.messages[1].content == "Response 1" # Output from chain

    # Second interaction
    mock_predict.return_value = "Response 2"
    rg_instance.generate(message_text="Second message", sender_id=sender_id)
    
    # Check memory again
    assert len(memory_for_sender.chat_memory.messages) == 4 # Human, AI, Human, AI
    assert memory_for_sender.chat_memory.messages[2].content == "Second message"
    assert memory_for_sender.chat_memory.messages[3].content == "Response 2"

    # Verify that when predict is called the second time, the prompt includes history.
    # The contextual_message passed to predict includes the current message AND the history from memory.
    # The mock_predict.call_args will show what `input` was given to `conversation.predict()`
    # The prompt construction inside `generate` includes `memory.chat_memory.messages`
    
    # Last call to predict
    last_call_args = mock_predict.call_args_list[-1]
    prompt_input_to_chain = last_call_args.kwargs['input'] # or last_call_args[0][0] if positional

    # The prompt includes the new message AND the history from memory.
    assert "Second message" in prompt_input_to_chain
    assert "Response 1" in prompt_input_to_chain # History from previous interaction


@patch('langchain.chains.ConversationChain.predict')
def test_separate_conversations_for_different_senders(mock_predict, rg_instance):
    """Test that different sender_ids have separate conversations."""
    # User A
    mock_predict.return_value = "Response A1"
    rg_instance.generate(message_text="Hello from A", sender_id="userA")
    assert "userA" in rg_instance.memories
    assert len(rg_instance.memories["userA"].chat_memory.messages) == 2

    # User B
    mock_predict.return_value = "Response B1"
    rg_instance.generate(message_text="Hello from B", sender_id="userB")
    assert "userB" in rg_instance.memories
    assert len(rg_instance.memories["userB"].chat_memory.messages) == 2
    assert rg_instance.memories["userB"].chat_memory.messages[0].content == "Hello from B"

    # Ensure User A's memory is distinct and unchanged by User B's interaction
    assert len(rg_instance.memories["userA"].chat_memory.messages) == 2 
    assert rg_instance.memories["userA"].chat_memory.messages[0].content == "Hello from A"


@patch('langchain.chains.ConversationChain.predict')
def test_booking_intent_parsing_with_intent(mock_predict, rg_instance):
    """Test parsing of booking intent when the marker is present."""
    raw_llm_response_with_intent = (
        "Okay, I can help you book that. What date and time?\n"
        "BOOKING_INTENT_DETECTED: {'date': '2023-12-01', 'time': '14:00', 'people': '2', 'service': 'Tire Repair'}"
    )
    mock_predict.return_value = raw_llm_response_with_intent

    result = rg_instance.generate(message_text="Book a tire repair for 2 on Dec 1st 2pm", sender_id="user_book_test1")

    expected_reply = "Okay, I can help you book that. What date and time?"
    expected_details = {'date': '2023-12-01', 'time': '14:00', 'people': '2', 'service': 'Tire Repair'}
    
    assert result['reply'] == expected_reply
    assert result['booking_details'] == expected_details


@patch('langchain.chains.ConversationChain.predict')
def test_booking_intent_parsing_with_none_values(mock_predict, rg_instance):
    """Test parsing when BOOKING_INTENT_DETECTED contains 'None' (as string from LLM) or actual null after parsing."""
    # LLM might output 'None' as a string, or the prompt might instruct it to use "None"
    # The parsing logic converts "None" or null to Python None.
    raw_llm_response_with_none = (
        "Sure, I can assist with that. For which service?\n"
        "BOOKING_INTENT_DETECTED: {'date': '2024-01-15', 'time': 'None', 'people': '1', 'service': 'None'}"
    )
    mock_predict.return_value = raw_llm_response_with_none
    
    result = rg_instance.generate(message_text="I need a booking for Jan 15th for myself.", sender_id="user_book_test_none")
    
    expected_reply = "Sure, I can assist with that. For which service?"
    # After json.loads and custom None conversion:
    expected_details = {'date': '2024-01-15', 'time': None, 'people': '1', 'service': None}

    assert result['reply'] == expected_reply
    assert result['booking_details'] == expected_details


@patch('langchain.chains.ConversationChain.predict')
def test_booking_intent_parsing_without_intent(mock_predict, rg_instance):
    """Test behavior when the booking intent marker is not present."""
    raw_llm_response_no_intent = "Hello! How can I help you today?"
    mock_predict.return_value = raw_llm_response_no_intent

    result = rg_instance.generate(message_text="Just saying hi", sender_id="user_book_test2")

    assert result['reply'] == raw_llm_response_no_intent
    assert result['booking_details'] is None


@patch('langchain.chains.ConversationChain.predict')
def test_booking_intent_parsing_malformed_json(mock_predict, rg_instance):
    """Test parsing with malformed JSON in booking intent string."""
    # Missing closing brace for the dict
    raw_llm_response_malformed = (
        "I think you want to book. \n"
        "BOOKING_INTENT_DETECTED: {'date': '2023-11-20', 'time': '10:00', 'people': '1', 'service': 'Checkup'" 
    ) # Malformed JSON part
    mock_predict.return_value = raw_llm_response_malformed

    with patch('builtins.print') as mock_print: # To capture error prints
        result = rg_instance.generate(message_text="Book checkup Nov 20 10am 1 person", sender_id="user_book_test_malformed")
    
    expected_reply = "I think you want to book." # Should strip the marker line
    assert result['reply'] == expected_reply
    assert result['booking_details'] is None # Parsing should fail gracefully
    
    # Check if error was printed (optional, but good to know our error handling works)
    # mock_print.assert_any_call(f"⚠️ 예약 정보 문자열에서 유효한 딕셔너리 패턴을 찾지 못했습니다: {{'date': '2023-11-20', 'time': '10:00', 'people': '1', 'service': 'Checkup'")
    # or
    # mock_print.assert_any_call(f"❌ 예약 정보 JSON 파싱 오류: Expecting '}}' delimiter: line 1 column 70 (char 69). 문자열: {{'date': '2023-11-20', 'time': '10:00', 'people': '1', 'service': 'Checkup'")
    # The exact error message depends on the regex matching and json.loads behavior for the specific malformed string.
    # For this test, ensuring booking_details is None is the main goal.
    assert any("예약 정보" in call_args[0][0] and ("오류" in call_args[0][0] or "패턴을 찾지 못했습니다" in call_args[0][0]) for call_args in mock_print.call_args_list)


@patch.object(ResponseGenerator, 'llm', new_callable=MagicMock) # Mock the LLM instance itself
def test_summarization_prompt(mock_llm_instance, rg_instance):
    """Test that the summarization prompt is constructed as expected."""
    # The mock_llm_instance will be the MagicMock replacing rg_instance.llm
    # We need to make sure its return value when called (as if it's a function, due to __call__)
    # has a 'content' attribute.
    mock_llm_instance.return_value = MagicMock(content="Mocked summary") # For rg_instance.llm([...])
    # If Langchain's LLM objects are directly callable, then mock_llm_instance needs to be callable
    # and return an object with a .content attribute.
    # If it's llm.invoke or llm.generate that's called, that specific method on the mock needs configuring.
    # Current code uses: response_generator_instance.llm([HumanMessage(content=summary_prompt)]).content
    # So, the mock_llm_instance itself should be callable.

    conversation_history = "Human: Hi\nAI: Hello\nHuman: How are you?\nAI: I am fine."
    rg_instance.summarize(conversation_history)

    # Assert that the LLM was called (or its 'invoke' or similar method)
    mock_llm_instance.assert_called_once()
    
    # Get the actual prompt passed to the LLM
    # The call is `self.llm([HumanMessage(content=summary_prompt_text)])`
    # So, call_args[0][0] is the list of messages.
    # call_args[0][0][0] is the HumanMessage object.
    # call_args[0][0][0].content is the actual prompt string.
    actual_prompt_message_list = mock_llm_instance.call_args[0][0]
    actual_prompt_content = actual_prompt_message_list[0].content
    
    expected_prompt_structure = f"""
        다음 대화 내용을 간결하게 요약해주세요:

        {conversation_history}

        요약:
        """
    assert actual_prompt_content.strip() == expected_prompt_structure.strip()

if __name__ == "__main__":
    pytest.main()
