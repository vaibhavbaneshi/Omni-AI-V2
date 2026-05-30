from datetime import datetime

from sqlalchemy.orm import Session

from app.models.memory import UserMemory


def list_memories(
    db: Session,
    user_id: int,
    workspace_id: str = "default",
):
    return (
        db.query(UserMemory)
        .filter(
            UserMemory.user_id == user_id,
            UserMemory.workspace_id == workspace_id,
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
    workspace_id: str = "default",
):
    memory = UserMemory(
        user_id=user_id,
        workspace_id=workspace_id,
        category=category,
        content=content,
        importance=importance,
    )

    db.add(memory)
    db.commit()
    db.refresh(memory)

    return memory


def delete_memory(
    db: Session,
    user_id: int,
    memory_id: int,
):
    memory = (
        db.query(UserMemory)
        .filter(
            UserMemory.id == memory_id,
            UserMemory.user_id == user_id,
        )
        .first()
    )

    if not memory:
        return False

    db.delete(memory)
    db.commit()

    return True


def _memory_tokens(text: str) -> set[str]:
    return {term.lower() for term in text.split() if len(term) > 2}


def _recency_score(updated_at: datetime | None) -> float:
    if not updated_at:
        return 0.0
    age_days = max((datetime.utcnow() - updated_at).total_seconds() / 86400, 0.0)
    return 1.0 / (1.0 + age_days / 14.0)


def retrieve_memory_context(
    db: Session,
    user_id: int,
    query: str,
    workspace_id: str = "default",
    limit: int = 6,
):
    query_terms = _memory_tokens(query)
    memories = list_memories(db=db, user_id=user_id, workspace_id=workspace_id)

    scored: list[tuple[float, UserMemory]] = []
    seen_content: set[str] = set()

    for memory in memories:
        content_key = memory.content.strip().lower()
        if content_key in seen_content:
            continue

        overlap = len(query_terms.intersection(_memory_tokens(memory.content)))
        overlap_ratio = overlap / max(len(query_terms), 1)
        semantic_proxy = overlap_ratio * 0.55 + memory.importance * 0.35 + _recency_score(memory.updated_at) * 0.10
        if overlap == 0 and memory.importance < 0.75:
            continue

        scored.append((semantic_proxy, memory))
        seen_content.add(content_key)

    if not scored and memories:
        scored = [(memory.importance, memory) for memory in memories[:limit]]

    ranked = sorted(scored, key=lambda item: item[0], reverse=True)
    selected = [memory for _, memory in ranked[:limit]]

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
            "score": round(score, 3),
            "strategy": "memory",
            "type": "memory",
        }
        for score, memory in ranked[:limit]
    ]

    return {
        "context": context,
        "sources": sources,
    }
