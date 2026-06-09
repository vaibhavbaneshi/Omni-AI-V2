"""Tests for cross-origin cookie settings and rate-limit browser redirects."""

from unittest.mock import patch

from starlette.requests import Request

from app.core.cookie_auth import _cookie_samesite, _cookie_secure, _is_cross_origin_auth
from app.services.rate_limit_service import (
    browser_rate_limit_redirect_url,
    is_browser_navigation,
    is_rate_limit_exempt_path,
)


def test_oauth_paths_are_rate_limit_exempt():
    assert is_rate_limit_exempt_path("/auth/github")
    assert is_rate_limit_exempt_path("/auth/github/callback")
    assert is_rate_limit_exempt_path("/auth/google")
    assert is_rate_limit_exempt_path("/auth/google/callback")
    assert not is_rate_limit_exempt_path("/auth/session")


def test_browser_navigation_detects_html_accept():
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/auth/session",
        "headers": [(b"accept", b"text/html,application/xhtml+xml")],
    }
    request = Request(scope)
    assert is_browser_navigation(request) is True


def test_browser_rate_limit_redirect_url_points_to_frontend():
    with patch("app.services.rate_limit_service.get_settings") as mock_settings:
        mock_settings.return_value.FRONTEND_URL = "https://app.example.com"
        url = browser_rate_limit_redirect_url(retry_after=45, scope="auth")
    assert url.startswith("https://app.example.com/rate-limited?")
    assert "retry_after=45" in url
    assert "scope=auth" in url


def test_cross_origin_auth_uses_none_samesite(monkeypatch):
    monkeypatch.setenv("FRONTEND_URL", "https://app.example.com")
    monkeypatch.setenv("API_PUBLIC_URL", "https://api.example.com")
    monkeypatch.setenv("ENVIRONMENT", "staging")
    from app.core.app_settings import get_settings

    get_settings.cache_clear()

    assert _is_cross_origin_auth() is True
    assert _cookie_secure() is True
    assert _cookie_samesite() == "none"

    get_settings.cache_clear()
