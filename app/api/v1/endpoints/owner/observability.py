from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.api.v1.endpoints.owner.dependencies import require_super_admin
from app.database.models.control_tower import TenantErrorLog, PlatformAuditLog, PlatformIncident, PlatformAlert

router = APIRouter()

@router.get("/errors")
async def list_tenant_errors(
    db: AsyncSession = Depends(get_db),
    admin=Depends(require_super_admin),
    hospital_id: Optional[str] = None,
    service_name: Optional[str] = None,
    severity: Optional[str] = None,
    error_code: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
) -> Dict[str, Any]:
    """
    Returns filterable, paginated error telemetry stream across all hospitals or for a specific tenant.
    """
    stmt = select(TenantErrorLog).order_by(TenantErrorLog.occurred_at.desc())
    if hospital_id:
        stmt = stmt.where(TenantErrorLog.hospital_id == hospital_id)
    if service_name:
        stmt = stmt.where(TenantErrorLog.service_name == service_name)
    if severity:
        stmt = stmt.where(TenantErrorLog.severity == severity)
    if error_code:
        stmt = stmt.where(TenantErrorLog.error_code == error_code)

    stmt = stmt.limit(limit).offset(offset)
    errors = (await db.execute(stmt)).scalars().all()

    return {
        "count": len(errors),
        "errors": [
            {
                "id": e.id,
                "hospital_id": e.hospital_id,
                "service_name": e.service_name,
                "severity": e.severity,
                "error_code": e.error_code,
                "error_message": e.error_message,
                "stack_trace": e.stack_trace,
                "endpoint": e.endpoint,
                "http_method": e.http_method,
                "http_status": e.http_status,
                "request_id": e.request_id,
                "correlation_id": e.correlation_id,
                "occurred_at": e.occurred_at.isoformat() if e.occurred_at else None,
                "resolution_status": e.resolution_status
            }
            for e in errors
        ]
    }

@router.get("/traces/{correlation_id}")
async def get_correlation_trace(
    correlation_id: str,
    db: AsyncSession = Depends(get_db),
    admin=Depends(require_super_admin)
) -> Dict[str, Any]:
    """
    Looks up all telemetry and audit records associated with a single correlation ID.
    """
    err_stmt = select(TenantErrorLog).where(TenantErrorLog.correlation_id == correlation_id).order_by(TenantErrorLog.occurred_at.asc())
    errors = (await db.execute(err_stmt)).scalars().all()

    audit_stmt = select(PlatformAuditLog).where(PlatformAuditLog.correlation_id == correlation_id).order_by(PlatformAuditLog.created_at.asc())
    audits = (await db.execute(audit_stmt)).scalars().all()

    return {
        "correlation_id": correlation_id,
        "error_logs_count": len(errors),
        "audit_logs_count": len(audits),
        "error_events": [
            {
                "id": e.id,
                "hospital_id": e.hospital_id,
                "service_name": e.service_name,
                "severity": e.severity,
                "error_code": e.error_code,
                "error_message": e.error_message,
                "occurred_at": e.occurred_at.isoformat() if e.occurred_at else None
            }
            for e in errors
        ],
        "audit_events": [
            {
                "id": a.id,
                "actor": a.actor_username,
                "action": a.action,
                "resource_type": a.resource_type,
                "status": a.status,
                "created_at": a.created_at.isoformat() if a.created_at else None
            }
            for a in audits
        ]
    }

@router.get("/incidents")
async def list_platform_incidents(
    db: AsyncSession = Depends(get_db),
    admin=Depends(require_super_admin),
    status: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Lists all platform incidents.
    """
    stmt = select(PlatformIncident).order_by(PlatformIncident.started_at.desc())
    if status:
        stmt = stmt.where(PlatformIncident.status == status)
    
    incidents = (await db.execute(stmt)).scalars().all()
    return [
        {
            "id": i.id,
            "title": i.title,
            "severity": i.severity,
            "status": i.status,
            "hospital_id": i.hospital_id,
            "affected_service": i.affected_service,
            "detected_by": i.detected_by,
            "assigned_to": i.assigned_to,
            "root_cause": i.root_cause,
            "resolution_summary": i.resolution_summary,
            "related_error_count": i.related_error_count,
            "started_at": i.started_at.isoformat() if i.started_at else None,
            "resolved_at": i.resolved_at.isoformat() if i.resolved_at else None
        }
        for i in incidents
    ]

@router.patch("/incidents/{incident_id}")
async def update_incident_status(
    incident_id: str,
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    admin=Depends(require_super_admin)
) -> Dict[str, Any]:
    """
    Transitions incident status (ACKNOWLEDGED -> INVESTIGATING -> MITIGATED -> RESOLVED).
    """
    incident = (await db.execute(select(PlatformIncident).where(PlatformIncident.id == incident_id))).scalar_one_or_none()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    new_status = payload.get("status")
    if new_status:
        incident.status = new_status
        if new_status == "ACKNOWLEDGED" and not incident.acknowledged_at:
            incident.acknowledged_at = datetime.now(timezone.utc)
        elif new_status == "RESOLVED":
            incident.resolved_at = datetime.now(timezone.utc)

    if "assigned_to" in payload:
        incident.assigned_to = payload["assigned_to"]
    if "root_cause" in payload:
        incident.root_cause = payload["root_cause"]
    if "resolution_summary" in payload:
        incident.resolution_summary = payload["resolution_summary"]

    await db.commit()
    await db.refresh(incident)
    return {"message": "Incident updated successfully", "incident_id": incident.id, "status": incident.status}
