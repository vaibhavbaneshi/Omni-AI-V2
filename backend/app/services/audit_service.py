"""Audit center aggregations for admin dashboards."""

from __future__ import annotations

import csv
import io
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.models.agent_trace import AgentTrace
from app.models.document import DocumentRecord
from app.models.rbac import UserRole
from app.models.research_report import ResearchReport
from app.models.user import User
from app.models.user_settings import SecurityAuditLog


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
    uploads = (
        db.query(DocumentRecord)
        .filter(DocumentRecord.created_at >= since)
        .order_by(DocumentRecord.created_at.desc())
        .limit(50)
        .all()
    )
    security_events = (
        db.query(SecurityAuditLog)
        .filter(SecurityAuditLog.created_at >= since)
        .order_by(SecurityAuditLog.created_at.desc())
        .limit(50)
        .all()
    )

    return {
        "period_days": days,
        "uploads": {
            "total": len(uploads),
            "recent": [_serialize_upload(row) for row in uploads[:10]],
        },
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
        "security_events": {
            "total": len(security_events),
            "recent": [_serialize_security(row) for row in security_events[:20]],
        },
    }


def list_audit_events(
    db: Session,
    *,
    days: int = 30,
    action_prefix: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    since = datetime.utcnow() - timedelta(days=days)
    query = db.query(SecurityAuditLog).filter(SecurityAuditLog.created_at >= since)
    if action_prefix:
        query = query.filter(SecurityAuditLog.action.like(f"{action_prefix}%"))
    total = query.count()
    rows = query.order_by(SecurityAuditLog.created_at.desc()).offset(offset).limit(limit).all()
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "events": [_serialize_security(row) for row in rows],
    }


def export_audit_events_csv(db: Session, *, days: int = 30) -> str:
    payload = list_audit_events(db, days=days, limit=1000, offset=0)
    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=["id", "action", "user_id", "ip_address", "detail", "created_at"],
    )
    writer.writeheader()
    for event in payload["events"]:
        writer.writerow(event)
    return buffer.getvalue()


def list_users_with_roles(db: Session, *, limit: int = 100, offset: int = 0) -> dict[str, Any]:
    total = db.query(User).count()
    users = db.query(User).order_by(User.id.asc()).offset(offset).limit(limit).all()
    roles = {row.user_id: row.role for row in db.query(UserRole).all()}
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "users": [
            {
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "role": roles.get(user.id, "viewer"),
                "oauth_provider": user.oauth_provider,
            }
            for user in users
        ],
    }


def _serialize_upload(document: DocumentRecord) -> dict[str, Any]:
    return {
        "document_id": document.id,
        "user_id": document.user_id,
        "filename": document.filename,
        "security_status": getattr(document, "security_status", "approved"),
        "indexing_stage": document.indexing_stage,
        "created_at": document.created_at.isoformat() if document.created_at else None,
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


def _serialize_security(row: SecurityAuditLog) -> dict[str, Any]:
    return {
        "id": row.id,
        "action": row.action,
        "user_id": row.user_id,
        "ip_address": row.ip_address,
        "detail": row.detail,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }
