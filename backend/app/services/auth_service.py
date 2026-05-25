from datetime import datetime
from datetime import timedelta

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


def hash_password(password: str):
    return pwd_context.hash(password)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict):
    settings = get_settings()
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
