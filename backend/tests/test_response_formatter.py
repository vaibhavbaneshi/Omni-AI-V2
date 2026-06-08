from app.services.response_formatter import format_assistant_response, is_simple_response


def test_simple_query_not_wrapped_with_summary():
    text = format_assistant_response("Hello! How can I help?", query="hi")
    assert text == "Hello! How can I help?"
    assert "# Summary" not in text


def test_structured_response_gets_summary_heading():
    text = format_assistant_response(
        "## Key Points\n- One\n- Two",
        query="Explain machine learning in detail",
    )
    assert text.startswith("# Summary")
    assert "## Key Points" in text


def test_internal_labels_stripped():
    text = format_assistant_response(
        "# ROUTING PLAN\n\n# Summary\n\nAnswer body.",
        query="What is RAG?",
    )
    assert "ROUTING PLAN" not in text
    assert "# Summary" in text


def test_is_simple_response_short_reply():
    assert is_simple_response("Thanks!")
    assert not is_simple_response("# Summary\n\nLong " + ("text " * 80))
