import logging

from jose import jwt
from jose import JWTError

from fastapi import Depends
from fastapi import HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.services.auth_service import (
    SECRET_KEY,
    ALGORITHM,
    decode_access_token,
)
from app.db.session import get_db
from app.models.user import User
from app.models.user_settings import UserSessionRecord

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="login"
)

# -----------------------------------
# VERIFY JWT TOKEN
# -----------------------------------

def get_current_username(
    token: str = Depends(oauth2_scheme)
):

    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials"
    )

    try:
        payload = decode_access_token(token)
        username = payload.get("sub")

        if username is None:
            raise credentials_exception

        return username

    except JWTError as exc:
        logger.info("Authentication token rejected: %s", exc)
        raise credentials_exception


def get_current_token_payload(
    token: str = Depends(oauth2_scheme),
) -> dict:
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
    )
    try:
        return decode_access_token(token)
    except JWTError as exc:
        logger.info("Authentication token payload rejected: %s", exc)
        raise credentials_exception from exc


def get_current_user(
    username: str = Depends(get_current_username),
    token_payload: dict = Depends(get_current_token_payload),
    db: Session = Depends(get_db)
):

    user = (
        db.query(User)
        .filter(User.username == username)
        .first()
    )

    if not user:
        logger.info("Authentication token subject not found: username=%s", username)
        raise HTTPException(
            status_code=401,
            detail="Could not validate credentials"
        )

    from app.services.settings_service import touch_user_session

    session_jti = token_payload.get("jti")
    if session_jti:
        session_record = (
            db.query(UserSessionRecord)
            .filter(
                UserSessionRecord.user_id == user.id,
                UserSessionRecord.session_jti == session_jti,
            )
            .first()
        )
        if session_record and session_record.revoked_at is not None:
            logger.info("Authentication token belongs to revoked session user_id=%s", user.id)
            raise HTTPException(
                status_code=401,
                detail="Could not validate credentials",
            )

    touch_user_session(
        db,
        user_id=user.id,
        session_jti=session_jti,
    )

    return user
