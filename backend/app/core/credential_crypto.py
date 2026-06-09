"""Encrypt connector credentials at rest using Fernet derived from JWT secret."""

from __future__ import annotations

import base64
import hashlib
import json
from typing import Any

from cryptography.fernet import Fernet

from app.core.app_settings import get_settings


def _fernet_key() -> bytes:
    settings = get_settings()
    raw = (settings.JWT_SECRET_KEY or "dev-only-change-me-before-production").encode()
    digest = hashlib.sha256(raw).digest()
    return base64.urlsafe_b64encode(digest)


def encrypt_credentials(payload: dict[str, Any]) -> str:
    token = Fernet(_fernet_key()).encrypt(json.dumps(payload).encode("utf-8"))
    return token.decode("utf-8")


def decrypt_credentials(token: str) -> dict[str, Any]:
    raw = Fernet(_fernet_key()).decrypt(token.encode("utf-8"))
    return json.loads(raw.decode("utf-8"))
