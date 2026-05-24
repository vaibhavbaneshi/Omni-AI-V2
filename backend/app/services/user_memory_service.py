from sqlalchemy.orm import Session

from app.models.memory import UserMemory


def list_memories(
    db: Session,
    user_id: int,
    workspace_id: str = "default"
):

    return (
        db.query(UserMemory)
        .filter(
            UserMemory.user_id == user_id,
            UserMemory.workspace_id == workspace_id
        )
        .order_by(UserMemory.importance.desc(), UserMemory.updated_at.desc())
        .all()
    )


def create_memory(
    db: Session,
    user_id: int,
    content: str,
    category: str = "preference",
    importance: float = 0.5,
    workspace_id: str = "default"
):

    memory = UserMemory(
        user_id=user_id,
        workspace_id=workspace_id,
        category=category,
        content=content,
        importance=importance
    )

    db.add(memory)
    db.commit()
    db.refresh(memory)

    return memory


def delete_memory(
    db: Session,
    user_id: int,
    memory_id: int
):

    memory = (
        db.query(UserMemory)
        .filter(
            UserMemory.id == memory_id,
            UserMemory.user_id == user_id
        )
        .first()
    )

    if not memory:
        return False

    db.delete(memory)
    db.commit()

    return True


def retrieve_memory_context(
    db: Session,
    user_id: int,
    query: str,
    workspace_id: str = "default",
    limit: int = 5
):

    query_terms = {
        term.lower()
        for term in query.split()
        if len(term) > 2
    }

    memories = list_memories(
        db=db,
        user_id=user_id,
        workspace_id=workspace_id
    )

    ranked = sorted(
        memories,
        key=lambda memory: (
            len(query_terms.intersection(set(memory.content.lower().split()))),
            memory.importance
        ),
        reverse=True
    )

    selected = ranked[:limit]

    context = "\n".join(
        [
            f"[Memory {memory.id}] {memory.category}: {memory.content}"
            for memory in selected
        ]
    )

    sources = [
        {
            "title": f"Memory: {memory.category}",
            "source": "Omni memory",
            "chunk": memory.content,
            "score": memory.importance,
            "strategy": "memory",
            "type": "memory"
        }
        for memory in selected
    ]

    return {
        "context": context,
        "sources": sources
    }
