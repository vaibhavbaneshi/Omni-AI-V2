from datetime import datetime
from datetime import timedelta
import hashlib
import hmac
import secrets
import uuid

from jose import jwt

from passlib.context import CryptContext

from app.core.app_settings import get_settings

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


def get_jwt_secret() -> str:
    return get_settings().JWT_SECRET_KEY


def get_jwt_algorithm() -> str:
    return get_settings().JWT_ALGORITHM


# Backward-compatible module constants
SECRET_KEY = get_jwt_secret()
ALGORITHM = get_jwt_algorithm()
ACCESS_TOKEN_EXPIRE_MINUTES = get_settings().JWT_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = 7


def hash_password(password: str):
    return pwd_context.hash(password)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, *, expires_delta: timedelta | None = None):
    settings = get_settings()
    to_encode = data.copy()
    to_encode.setdefault("jti", str(uuid.uuid4()))
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> dict:
    settings = get_settings()
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


def create_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def refresh_token_expires_at() -> datetime:
    return datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)


def hash_refresh_token(token: str) -> str:
    key = get_settings().JWT_SECRET_KEY.encode("utf-8")
    digest = hmac.new(key, token.encode("utf-8"), hashlib.sha256).hexdigest()
    return digest


def verify_refresh_token(token: str, token_hash: str | None) -> bool:
    if not token or not token_hash:
        return False
    return hmac.compare_digest(hash_refresh_token(token), token_hash)
