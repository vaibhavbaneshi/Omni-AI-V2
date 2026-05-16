from fastapi import APIRouter
from fastapi import Depends

from sqlalchemy.orm import Session

from app.db.session import get_db

from app.models.user import User

from app.services.auth_service import (
    hash_password,
    verify_password,
    create_access_token
)

from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter()

# -----------------------------------
# REGISTER
# -----------------------------------
@router.post("/register")
def register(
    username: str,
    email: str,
    password: str,
    db: Session = Depends(get_db)
):

    hashed_password = hash_password(password)

    new_user = User(
        username=username,
        email=email,
        password=hashed_password
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "message": "User created successfully"
    }

# -----------------------------------
# LOGIN
# -----------------------------------

@router.post("/login")

def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):

    user = (
        db.query(User)
        .filter(
            User.username == form_data.username
        )
        .first()
    )

    if not user:
        return {
            "error": "Invalid username"
        }

    if not verify_password(
        form_data.password,
        user.password
    ):
        return {
            "error": "Invalid password"
        }

    access_token = create_access_token(
        data={
            "sub": user.username
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }