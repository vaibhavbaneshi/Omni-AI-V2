from fastapi import APIRouter
from fastapi import Depends

from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.services.auth_service import hash_password

router = APIRouter()

# -----------------------------------
# CREATE USER
# -----------------------------------

@router.post("/users")

def create_user(
    username: str,
    email: str,
    password: str,
    db: Session = Depends(get_db)
):

    user = User(
        username=username,
        email=email,
        password=hash_password(password)
    )

    db.add(user)

    db.commit()

    db.refresh(user)

    return {
        "message": "User created",
        "user_id": user.id
    }

# -----------------------------------
# GET USERS
# -----------------------------------

@router.get("/users")

def get_users(
    db: Session = Depends(get_db)
):

    users = db.query(User).all()

    return users
