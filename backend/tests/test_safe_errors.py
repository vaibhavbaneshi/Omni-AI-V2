from sqlalchemy.exc import ProgrammingError

from app.core.llm import LLMProviderError
from app.core.safe_errors import chat_facing_message, user_facing_message


def test_user_facing_message_hides_sqlalchemy_details():
    exc = ProgrammingError(
        "SELECT users",
        {},
        Exception('relation "users" does not exist'),
    )
    message = user_facing_message(exc, context="test")
    assert "psycopg2" not in message.lower()
    assert "sqlalchemy" not in message.lower()
    assert "users" not in message.lower() or "set up" in message.lower()
    assert "try again" in message.lower()


def test_user_facing_message_keeps_short_value_errors():
    message = user_facing_message(ValueError("Invalid OAuth state"), context="test")
    assert message == "Invalid OAuth state"


def test_chat_facing_message_hides_groq_stream_details():
    exc = LLMProviderError(
        "Groq streaming failed: Completions.create() got an unexpected keyword argument 'stream_options'"
    )
    message = chat_facing_message(exc, context="chat stream")
    assert "stream_options" not in message
    assert "groq" not in message.lower()
    assert "generate a response" in message.lower()
