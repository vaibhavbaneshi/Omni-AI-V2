from unittest.mock import MagicMock, patch

from app.core.telemetry import LLMCallMetrics, estimate_tokens
from app.services.llm_invoke import invoke_generate


def test_estimate_tokens():
    assert estimate_tokens("") == 0
    assert estimate_tokens("abcd") == 1
    assert estimate_tokens("a" * 100) == 25


def test_invoke_generate_records_metrics():
    provider = MagicMock()
    provider.name = "groq"
    provider.model_name = "test-model"
    provider.generate.return_value = "Hello"
    provider.last_usage = {
        "prompt_tokens": 10,
        "completion_tokens": 5,
        "total_tokens": 15,
    }

    with patch("app.services.llm_invoke.record_llm_usage") as record:
        result = invoke_generate(
            "prompt text",
            provider=provider,
            endpoint="test.generate",
            user_id=1,
            session_id=2,
        )

    assert result == "Hello"
    record.assert_called_once()
    metrics = record.call_args[0][0]
    assert isinstance(metrics, LLMCallMetrics)
    assert metrics.provider == "groq"
    assert metrics.prompt_tokens == 10
    assert metrics.completion_tokens == 5
    assert metrics.success is True


def test_usage_tracking_disabled_skips_db():
    from app.services.usage_tracking_service import record_api_usage

    with patch("app.services.usage_tracking_service._tracking_enabled", return_value=False):
        with patch("app.services.usage_tracking_service.SessionLocal") as session_local:
            record_api_usage(
                method="GET",
                path="/health",
                status_code=200,
                duration_ms=1.0,
            )
            session_local.assert_not_called()
