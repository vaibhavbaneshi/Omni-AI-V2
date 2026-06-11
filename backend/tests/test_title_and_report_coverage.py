"""Coverage for title service and research report generator."""

import json
from unittest.mock import patch

from app.research.report_generator import generate_report
from app.services.title_service import (
    generate_chat_title,
    optimistic_chat_title,
    refine_chat_title,
    should_refine_session_title,
)


def test_optimistic_chat_title_from_message():
    assert optimistic_chat_title("Summarize my quarterly report") != "New Chat"


def test_optimistic_chat_title_empty():
    assert optimistic_chat_title("") == "New Chat"


@patch("app.services.title_service.invoke_generate", return_value="Quarterly Report Summary")
def test_generate_chat_title(mock_invoke):
    title = generate_chat_title("Please summarize my quarterly report in detail")
    assert "Quarterly" in title
    mock_invoke.assert_called_once()


@patch("app.services.title_service.invoke_generate", side_effect=RuntimeError("down"))
def test_generate_chat_title_fallback(mock_invoke):
    title = generate_chat_title("Please summarize my quarterly report")
    assert title


@patch("app.services.title_service.invoke_generate", return_value="Refined Topic Title")
def test_refine_chat_title(mock_invoke):
    title = refine_chat_title("Original question", assistant_preview="Assistant answer preview")
    assert "Refined" in title


def test_should_refine_session_title():
    assert should_refine_session_title("New Chat", assistant_message_count=1)
    assert not should_refine_session_title("New Chat", assistant_message_count=2)


@patch(
    "app.research.report_generator.invoke_generate",
    return_value=json.dumps(
        {
            "title": "Report",
            "executive_summary": "Summary",
            "key_findings": ["One"],
            "detailed_analysis": "Analysis",
            "evidence_summary": "Evidence",
            "sources_reviewed": ["S1"],
            "references": [],
            "open_questions": [],
            "methodology": "Hybrid",
            "confidence_score": 0.7,
            "contradictions_noted": [],
            "iterations": 2,
        }
    ),
)
def test_generate_report(mock_invoke):
    payload = generate_report(
        query="Q",
        evidence="Evidence body",
        iterations=2,
        verification={"confidence_score": 0.8},
        contradictions={"contradictions": []},
    )
    assert payload.title == "Report"
    assert payload.confidence_score == 0.7
