"""Evaluation API — admin-gated RAG quality runs."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.admin_access import user_has_admin_access
from app.core.security import get_current_user
from app.models.user import User
from evaluation.runner import run_evaluation

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


class EvaluationRunRequest(BaseModel):
    dataset_path: str | None = Field(
        default=None,
        description="Optional path to a JSON evaluation dataset.",
    )
    run_rag: bool = True
    run_orchestration: bool = True
    generate_answers: bool = Field(
        default=False,
        description="When true, generates answers via live RAG pipeline (requires LLM).",
    )
    engine_preference: str = Field(
        default="auto",
        description="auto | heuristic | ragas | deepeval",
    )


def _user_can_run_evaluation(user: User) -> bool:
    return user_has_admin_access(user)


def require_evaluation_admin(current_user: User = Depends(get_current_user)) -> User:
    if not _user_can_run_evaluation(current_user):
        raise HTTPException(
            status_code=403,
            detail="Evaluation runs are restricted to configured admin accounts.",
        )
    return current_user


@router.post("/run")
def run_evaluation_endpoint(
    payload: EvaluationRunRequest,
    _: User = Depends(require_evaluation_admin),
):
    dataset = Path(payload.dataset_path) if payload.dataset_path else None
    if dataset and not dataset.exists():
        raise HTTPException(status_code=404, detail=f"Dataset not found: {dataset}")

    if payload.engine_preference not in {"auto", "heuristic", "ragas", "deepeval"}:
        raise HTTPException(status_code=400, detail="Invalid engine_preference.")

    try:
        report = run_evaluation(
            dataset_path=dataset,
            run_rag=payload.run_rag,
            run_orchestration=payload.run_orchestration,
            generate_answers=payload.generate_answers,
            engine_preference=payload.engine_preference,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {exc}") from exc

    return report


@router.get("/datasets/sample")
def get_sample_dataset(_: User = Depends(get_current_user)):
    sample_path = Path(__file__).resolve().parents[2] / "evaluation" / "datasets" / "sample_rag_eval.json"
    if not sample_path.exists():
        raise HTTPException(status_code=404, detail="Sample dataset not found.")
    return {
        "path": str(sample_path),
        "name": "sample_rag_eval.json",
        "description": "Default RAG + orchestration benchmark cases for OmniAI.",
    }
