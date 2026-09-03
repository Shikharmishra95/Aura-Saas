from datetime import datetime, timezone, timedelta
from typing import Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.api.v1.endpoints.owner.dependencies import require_super_admin
from app.database.models.appointment import Hospital, Doctor, Appointment
from app.database.models.control_tower import (
    HospitalSubscriptionHistory,
    TenantErrorLog,
    PlatformIncident,
    PlatformAuditLog
)

router = APIRouter()

@router.get("/overview")
async def get_control_tower_overview(
    db: AsyncSession = Depends(get_db),
    admin=Depends(require_super_admin)
) -> Dict[str, Any]:
    """
    Returns global executive metrics for the Control Tower single pane of glass.
    """
    now = datetime.now(timezone.utc)
    seven_days_later = now + timedelta(days=7)
    past_24h = now - timedelta(hours=24)

    # 1. Hospitals counts
    hosp_total = (await db.execute(select(func.count(Hospital.id)))).scalar() or 0
    hosp_active = (await db.execute(select(func.count(Hospital.id)).where(Hospital.is_active == True, Hospital.plan_status == "ACTIVE"))).scalar() or 0
    hosp_expiring = (await db.execute(
        select(func.count(Hospital.id)).where(
            Hospital.is_active == True,
            Hospital.plan_expires_at != None,
            Hospital.plan_expires_at <= seven_days_later
        )
    )).scalar() or 0

    # 2. Doctors & Appointments
    doc_count = (await db.execute(select(func.count(Doctor.id)).where(Doctor.is_active == True))).scalar() or 0
    appt_total = (await db.execute(select(func.count(Appointment.id)))).scalar() or 0
    appt_completed = (await db.execute(select(func.count(Appointment.id)).where(Appointment.status == "COMPLETED"))).scalar() or 0

    # 3. SaaS Collections vs Hospital OPD Revenue
    saas_revenue_res = (await db.execute(select(func.sum(HospitalSubscriptionHistory.amount_paid)))).scalar() or 0.0
    
    # Hospital OPD collections from paid appointments
    paid_appts_stmt = select(Doctor.opd_fees).join(Appointment, Appointment.doctor_id == Doctor.id).where(Appointment.payment_status == "PAID")
    paid_appts_fees = (await db.execute(paid_appts_stmt)).scalars().all()
    hospital_opd_revenue = sum(fee or 500 for fee in paid_appts_fees)

    # 4. Active Incidents & 24h Error counts
    active_incidents = (await db.execute(
        select(func.count(PlatformIncident.id)).where(PlatformIncident.status.in_(["DETECTED", "ACKNOWLEDGED", "INVESTIGATING"]))
    )).scalar() or 0

    errors_24h = (await db.execute(
        select(func.count(TenantErrorLog.id)).where(TenantErrorLog.occurred_at >= past_24h)
    )).scalar() or 0

    # 5. Recent Audit Activity
    recent_audits_stmt = select(PlatformAuditLog).order_by(PlatformAuditLog.created_at.desc()).limit(8)
    recent_audits = (await db.execute(recent_audits_stmt)).scalars().all()

    return {
        "hospitals": {
            "total": hosp_total,
            "active": hosp_active,
            "expiring_soon": hosp_expiring
        },
        "operations": {
            "total_doctors": doc_count,
            "total_appointments": appt_total,
            "completed_appointments": appt_completed,
            "completion_rate_pct": round((appt_completed / appt_total * 100), 1) if appt_total > 0 else 100.0
        },
        "financials": {
            "total_saas_revenue_inr": float(saas_revenue_res),
            "total_hospital_opd_revenue_inr": float(hospital_opd_revenue)
        },
        "observability": {
            "active_incidents": active_incidents,
            "errors_last_24h": errors_24h,
            "platform_health_status": "DEGRADED" if active_incidents > 0 else ("HEALTHY" if errors_24h < 20 else "WARNING")
        },
        "recent_audit_events": [
            {
                "id": a.id,
                "actor": a.actor_username,
                "role": a.actor_role,
                "action": a.action,
                "resource_type": a.resource_type,
                "hospital_id": a.hospital_id,
                "status": a.status,
                "created_at": a.created_at.isoformat() if a.created_at else None
            }
            for a in recent_audits
        ]
    }
