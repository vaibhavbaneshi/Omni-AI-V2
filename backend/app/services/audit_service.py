"""Audit center aggregations for admin dashboards."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.models.agent_trace import AgentTrace
from app.models.rbac import UserRole
from app.models.research_report import ResearchReport
from app.models.user import User


def get_audit_overview(db: Session, *, days: int = 30) -> dict[str, Any]:
    since = datetime.utcnow() - timedelta(days=days)

    agent_traces = (
        db.query(AgentTrace)
        .filter(AgentTrace.created_at >= since)
        .order_by(AgentTrace.created_at.desc())
        .limit(50)
        .all()
    )
    research_reports = (
        db.query(ResearchReport)
        .filter(ResearchReport.created_at >= since)
        .order_by(ResearchReport.created_at.desc())
        .limit(50)
        .all()
    )
    role_assignments = db.query(UserRole).order_by(UserRole.updated_at.desc()).limit(100).all()

    return {
        "period_days": days,
        "agent_traces": {
            "total": len(agent_traces),
            "complete": sum(1 for trace in agent_traces if trace.status == "complete"),
            "recent": [_serialize_trace(trace) for trace in agent_traces[:10]],
        },
        "research_reports": {
            "total": len(research_reports),
            "ready": sum(1 for report in research_reports if report.status == "ready"),
            "recent": [_serialize_research(report) for report in research_reports[:10]],
        },
        "rbac": {
            "assignments": len(role_assignments),
            "roles": [_serialize_role(db, row) for row in role_assignments[:20]],
        },
    }


def _serialize_trace(trace: AgentTrace) -> dict[str, Any]:
    return {
        "id": trace.id,
        "user_id": trace.user_id,
        "session_id": trace.session_id,
        "query": trace.query[:200],
        "status": trace.status,
        "latency_ms": trace.latency_ms,
        "created_at": trace.created_at.isoformat() if trace.created_at else None,
    }


def _serialize_research(report: ResearchReport) -> dict[str, Any]:
    return {
        "id": report.id,
        "user_id": report.user_id,
        "query": report.query[:200],
        "status": report.status,
        "created_at": report.created_at.isoformat() if report.created_at else None,
    }


def _serialize_role(db: Session, row: UserRole) -> dict[str, Any]:
    user = db.query(User).filter(User.id == row.user_id).first()
    return {
        "user_id": row.user_id,
        "email": user.email if user else None,
        "role": row.role,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }
