"""Additional unit tests to improve coverage on core modules."""

from app.services.attachment_service import is_document_query, NO_DOCUMENT_MESSAGE
from app.services.prompt_builder import build_stream_prompt
from app.services.user_memory_service import create_memory, list_memories


def test_is_document_query_detects_upload_intent():
    assert is_document_query("summarize the attached PDF file")
    assert is_document_query("what is in the uploaded document")
    assert not is_document_query("what is 2 + 2")


def test_no_document_message_is_user_friendly():
    assert "upload" in NO_DOCUMENT_MESSAGE.lower()


def test_build_stream_prompt_includes_context():
    prompt = build_stream_prompt(
        query="Explain refunds",
        context="Refunds within 14 days.",
        history="user: hello\n",
        summary="Prior discussion about billing.",
        mode="research",
    )
    assert "Explain refunds" in prompt
    assert "Refunds within 14 days" in prompt
    assert len(prompt) > 50


def test_build_stream_prompt_requires_professional_answer_structure():
    prompt = build_stream_prompt(
        query="Review our vector database architecture",
        context="Vector databases store embeddings for semantic search.",
        mode="research",
    )

    assert "# Summary" in prompt
    assert "## Key Points" in prompt
    assert "## Details" in prompt
    assert "## Recommendations" in prompt
    assert "Synthesize retrieved content" in prompt
    assert "Never dump raw retrieved chunks" in prompt
    assert "NEVER reply as one large unbroken text block" in prompt


def test_build_stream_prompt_uses_document_analysis_format():
    prompt = build_stream_prompt(
        query="Summarize this uploaded report",
        context="Revenue grew 12% year over year.",
        mode="research",
        document_summary=True,
    )

    assert "# Executive Summary" in prompt
    assert "## Key Findings" in prompt
    assert "## Risks" in prompt
    assert "## Recommendations" in prompt


def test_build_stream_prompt_uses_step_format_for_how_to_requests():
    prompt = build_stream_prompt(
        query="How do I build a RAG system?",
        context="Use chunking, embeddings, retrieval, and answer generation.",
        mode="research",
    )

    assert "ANSWER FORMAT (mandatory for process/how-to requests)" in prompt
    assert "## Details" in prompt
    assert "## Recommendations" in prompt


def test_build_stream_prompt_uses_comparison_format():
    prompt = build_stream_prompt(
        query="Compare LangChain vs LangGraph",
        context="LangChain is a framework. LangGraph models stateful workflows.",
        mode="research",
    )

    assert "ANSWER FORMAT (mandatory for multi-document comparison)" in prompt
    assert "## Feature Comparison" in prompt
    assert "Markdown table" in prompt
    assert "## Recommendations" in prompt


def test_user_memory_service_crud(db_session):
    from tests.factories import UserFactory

    user = UserFactory()
    created = create_memory(
        db_session,
        user_id=user.id,
        content="Prefers concise answers",
        category="preference",
        importance=0.7,
    )
    assert created.id is not None

    memories = list_memories(db_session, user_id=user.id)
    assert any(item.content == "Prefers concise answers" for item in memories)
