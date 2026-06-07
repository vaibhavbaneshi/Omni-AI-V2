"""Tests for Phase C formal agent workflows."""

import json
from unittest.mock import MagicMock, patch

from tests.factories import ChatSessionFactory, UserFactory


SAMPLE_REPORT = {
    "title": "Vector Database Landscape",
    "executive_summary": "Vector databases power semantic retrieval for RAG systems.",
    "key_findings": ["Embeddings enable similarity search", "Hybrid retrieval improves recall"],
    "evidence_summary": "Internal docs and web snippets support these findings.",
    "sources_reviewed": ["document-chunk-1", "web-source-1"],
    "open_questions": ["Which vendor fits low-memory deploys?"],
    "methodology": "Iterative hybrid retrieval plus web search",
    "iterations": 3,
}


@patch("app.agent.research_agent.invoke_generate")
@patch("app.agent.research_agent.web_search")
@patch("app.agent.research_agent.hybrid_search")
def test_research_agent_persists_report(
    mock_hybrid,
    mock_web_search,
    mock_invoke,
    db_session,
):
    from app.agent.research_agent import ResearchAgent
    from app.models.research_report import ResearchReport

    user = UserFactory()
    session = ChatSessionFactory(user=user)

    mock_hybrid.return_value = ["Vector databases store embeddings."]
    web_result = MagicMock()
    web_result.context = "Recent articles discuss pgvector and Chroma."
    web_result.sources = []
    mock_web_search.return_value = web_result
    mock_invoke.return_value = json.dumps(SAMPLE_REPORT)

    result = ResearchAgent().run(
        query="Compare vector databases for RAG",
        user_id=user.id,
        db=db_session,
        session_id=session.id,
    )

    assert result["agent"] == "research"
    assert result["report_id"]
    record = db_session.query(ResearchReport).filter(ResearchReport.id == result["report_id"]).first()
    assert record is not None
    assert record.status == "ready"
    assert record.report["title"] == "Vector Database Landscape"
    assert "Executive Summary" in result["context"]


@patch("app.agent.document_analysis_agent.generate_document_insights")
def test_document_analysis_agent_formats_context(
    mock_generate,
    db_session,
):
    from app.agent.document_analysis_agent import DocumentAnalysisAgent, is_document_analysis_request
    from app.models.document import DocumentCollection, DocumentRecord
    from app.models.document_insight import DocumentInsight

    assert is_document_analysis_request("Generate FAQs from the uploaded document")

    user = UserFactory()
    chat_session = ChatSessionFactory(user=user)
    collection = DocumentCollection(user_id=user.id, workspace_id="default", name="Default")
    db_session.add(collection)
    db_session.commit()

    document = DocumentRecord(
        user_id=user.id,
        workspace_id="default",
        collection_id=collection.id,
        session_id=chat_session.id,
        filename="policy.pdf",
        storage_path="/tmp/policy.pdf",
        file_size=256,
        chunks_created=3,
        indexing_stage="ready",
    )
    db_session.add(document)
    db_session.commit()

    insight = DocumentInsight(
        document_id=document.id,
        user_id=user.id,
        status="ready",
        payload={
            "executive_summary": {
                "overview": "The policy covers refunds within 14 days.",
                "key_findings": ["14-day refund window"],
                "important_points": [],
                "risks": [],
                "recommendations": ["Review annually"],
            },
            "faqs": [{"question": "How long?", "answer": "14 days."}],
            "action_items": [],
            "metadata_insights": {
                "keywords": ["refund"],
                "topics": ["Policy"],
                "entities": [],
                "important_dates": [],
                "statistics": [],
            },
        },
    )
    mock_generate.return_value = insight

    result = DocumentAnalysisAgent().run(
        query="Generate insights from the uploaded document",
        user_id=user.id,
        db=db_session,
        session_id=chat_session.id,
    )

    assert result["agent"] == "document-analysis"
    assert "policy.pdf" in result["context"]
    assert result["document_analysis"][0]["document_id"] == document.id


def test_orchestrator_routes_document_analysis_agent(db_session):
    from app.agent.orchestrator import AgentOrchestrator
    from app.models.document import DocumentCollection, DocumentRecord

    user = UserFactory()
    session = ChatSessionFactory(user=user)
    collection = DocumentCollection(user_id=user.id, workspace_id="default", name="Default")
    db_session.add(collection)
    db_session.commit()

    db_session.add(
        DocumentRecord(
            user_id=user.id,
            workspace_id="default",
            collection_id=collection.id,
            session_id=session.id,
            filename="notes.pdf",
            storage_path="/tmp/notes.pdf",
            file_size=64,
            chunks_created=1,
            indexing_stage="ready",
        )
    )
    db_session.commit()

    route = AgentOrchestrator().plan(
        "Generate FAQs from the uploaded document",
        mode="analyst",
        db=db_session,
        user_id=user.id,
        session_id=session.id,
    )

    assert route.strategy == "document-analysis-agent"


@patch("app.api.agent_routes.run_document_analysis_agent")
def test_document_analysis_api(mock_run, auth_client):
    mock_run.return_value = {
        "context": "Overview: Sample",
        "route": {"status": "ready"},
        "document_analysis": [
            {
                "document_id": 1,
                "filename": "notes.pdf",
                "status": "ready",
                "insight_id": 10,
            }
        ],
    }

    response = auth_client.post(
        "/agents/document-analysis",
        json={"session_id": 1, "force": False},
        headers=auth_client.auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["documents"][0]["filename"] == "notes.pdf"
