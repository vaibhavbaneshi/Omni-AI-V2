import base64
import hashlib
import hmac
import json
import secrets
from typing import Any
from urllib.parse import urlencode

import requests

from app.services.auth_service import SECRET_KEY, hash_password

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"
GITHUB_EMAILS_URL = "https://api.github.com/user/emails"

GOOGLE_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


def _sign_payload(payload: str) -> str:
    return hmac.new(
        SECRET_KEY.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def encode_oauth_state(provider: str, next_path: str) -> str:
    payload = {
        "provider": provider,
        "next": next_path,
        "nonce": secrets.token_urlsafe(16),
    }
    encoded = base64.urlsafe_b64encode(
        json.dumps(payload).encode("utf-8")
    ).decode("utf-8")
    signature = _sign_payload(encoded)
    return f"{encoded}.{signature}"


def decode_oauth_state(state: str) -> dict[str, str]:
    try:
        encoded, signature = state.rsplit(".", 1)
    except ValueError as exc:
        raise ValueError("Invalid OAuth state") from exc

    if not hmac.compare_digest(_sign_payload(encoded), signature):
        raise ValueError("Invalid OAuth state signature")

    payload = json.loads(
        base64.urlsafe_b64decode(encoded.encode("utf-8")).decode("utf-8")
    )
    return payload


def build_github_authorize_url(
    *,
    client_id: str,
    redirect_uri: str,
    state: str,
) -> str:
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": "read:user user:email",
        "state": state,
    }
    return f"{GITHUB_AUTHORIZE_URL}?{urlencode(params)}"


def build_google_authorize_url(
    *,
    client_id: str,
    redirect_uri: str,
    state: str,
) -> str:
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "online",
        "include_granted_scopes": "true",
        "state": state,
    }
    return f"{GOOGLE_AUTHORIZE_URL}?{urlencode(params)}"


def exchange_github_code(
    *,
    client_id: str,
    client_secret: str,
    code: str,
    redirect_uri: str,
) -> str:
    response = requests.post(
        GITHUB_TOKEN_URL,
        headers={"Accept": "application/json"},
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
        },
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    access_token = payload.get("access_token")
    if not access_token:
        raise ValueError(payload.get("error_description", "GitHub token exchange failed"))
    return access_token


def exchange_google_code(
    *,
    client_id: str,
    client_secret: str,
    code: str,
    redirect_uri: str,
) -> str:
    response = requests.post(
        GOOGLE_TOKEN_URL,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        },
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    access_token = payload.get("access_token")
    if not access_token:
        raise ValueError(payload.get("error_description", "Google token exchange failed"))
    return access_token


def fetch_github_profile(access_token: str) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github+json",
    }
    user_response = requests.get(GITHUB_USER_URL, headers=headers, timeout=20)
    user_response.raise_for_status()
    user = user_response.json()

    email = user.get("email")
    if not email:
        emails_response = requests.get(GITHUB_EMAILS_URL, headers=headers, timeout=20)
        emails_response.raise_for_status()
        emails = emails_response.json()
        primary = next((item for item in emails if item.get("primary")), None)
        fallback = emails[0] if emails else None
        chosen = primary or fallback
        email = chosen.get("email") if chosen else None

    if not email:
        raise ValueError("GitHub account must have a visible primary email")

    login = user.get("login") or email.split("@")[0]
    name = user.get("name") or login

    return {
        "email": email,
        "username": email,
        "name": name,
    }


def fetch_google_profile(access_token: str) -> dict[str, str]:
    response = requests.get(
        GOOGLE_USERINFO_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=20,
    )
    response.raise_for_status()
    user = response.json()

    email = user.get("email")
    if not email:
        raise ValueError("Google account must provide an email address")

    name = user.get("name") or email.split("@")[0]

    return {
        "email": email,
        "username": email,
        "name": name,
    }


def get_or_create_oauth_user(db, profile: dict[str, str], *, provider: str):
    from app.models.user import User

    email = profile["email"]
    username = profile["username"]

    user = (
        db.query(User)
        .filter((User.email == email) | (User.username == username))
        .first()
    )

    if user:
        if not user.oauth_provider:
            user.oauth_provider = provider
            db.commit()
        return user

    user = User(
        username=username,
        email=email,
        password=hash_password(secrets.token_urlsafe(32)),
        oauth_provider=provider,
        has_password=False,
        first_name=(profile.get("name") or "").split(" ")[0] or None,
        last_name=" ".join((profile.get("name") or "").split(" ")[1:]) or None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
