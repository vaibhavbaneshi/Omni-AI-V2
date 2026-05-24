from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services.user_memory_service import (
    create_memory,
    delete_memory,
    list_memories
)

router = APIRouter()


@router.get("/memory")
def get_memory(
    workspace_id: str = "default",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    memories = list_memories(
        db=db,
        user_id=current_user.id,
        workspace_id=workspace_id
    )

    return {
        "memories": [
            {
                "id": memory.id,
                "category": memory.category,
                "content": memory.content,
                "importance": memory.importance,
                "created_at": memory.created_at.isoformat() if memory.created_at else None,
                "updated_at": memory.updated_at.isoformat() if memory.updated_at else None
            }
            for memory in memories
        ]
    }


@router.post("/memory")
def add_memory(
    content: str,
    category: str = "preference",
    importance: float = 0.5,
    workspace_id: str = "default",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    memory = create_memory(
        db=db,
        user_id=current_user.id,
        content=content,
        category=category,
        importance=importance,
        workspace_id=workspace_id
    )

    return {
        "id": memory.id,
        "category": memory.category,
        "content": memory.content,
        "importance": memory.importance
    }


@router.delete("/memory/{memory_id}")
def remove_memory(
    memory_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    deleted = delete_memory(
        db=db,
        user_id=current_user.id,
        memory_id=memory_id
    )

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Memory not found"
        )

    return {
        "message": "Memory deleted"
    }
