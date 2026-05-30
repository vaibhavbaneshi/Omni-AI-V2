from unittest.mock import MagicMock, patch

from app.services.memory_summary_service import generate_summary


def test_generate_summary_uses_llm_for_long_threads():
    messages = [
        MagicMock(role="user", content=f"Question {index}?")
        for index in range(8)
    ]

    db = MagicMock()
    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = messages
    db.query.return_value.filter.return_value.first.return_value = None

    with patch("app.services.memory_summary_service.SessionLocal", return_value=db):
        with patch(
            "app.services.memory_summary_service.summarize_conversation",
            return_value="Condensed thread summary",
        ) as summarize:
            generate_summary(session_id=42)

    summarize.assert_called_once()
    db.add.assert_called_once()
    db.commit.assert_called_once()
