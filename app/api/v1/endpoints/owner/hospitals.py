from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.api.v1.endpoints.owner.dependencies import require_super_admin
from app.database.models.appointment import Hospital, Doctor, Appointment, Patient
from app.database.models.conversation import CallLog
from app.database.models.control_tower import (
    HospitalSubscriptionHistory,
    TenantErrorLog,
    PlatformAuditLog
)

router = APIRouter()

@router.get("/hospitals")
async def list_all_hospitals_overview(
    db: AsyncSession = Depends(get_db),
    admin=Depends(require_super_admin),
    search: Optional[str] = None,
    plan: Optional[str] = None,
    status: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Returns master control tower list of all hospital tenants with real-time operational & billing posture.
    """
    stmt = select(Hospital).order_by(Hospital.created_at.desc())
    if search:
        stmt = stmt.where(Hospital.name.ilike(f"%{search}%") | Hospital.phone.ilike(f"%{search}%") | Hospital.id.ilike(f"%{search}%"))
    if plan:
        stmt = stmt.where(Hospital.subscription_plan == plan)
    if status:
        stmt = stmt.where(Hospital.plan_status == status)

    hospitals = (await db.execute(stmt)).scalars().all()
    results = []
    now = datetime.now(timezone.utc)

    for h in hospitals:
        # Calculate days left
        days_left = 0
        if h.plan_expires_at:
            exp = h.plan_expires_at if h.plan_expires_at.tzinfo else h.plan_expires_at.replace(tzinfo=timezone.utc)
            delta = exp - now
            days_left = max(0, delta.days)

        # Doctor count vs quota
        doc_count = (await db.execute(select(func.count(Doctor.id)).where(Doctor.hospital_id == h.id, Doctor.is_active == True))).scalar() or 0
        
        # Appointment & Patient counts
        appt_count = (await db.execute(select(func.count(Appointment.id)).where(Appointment.hospital_id == h.id))).scalar() or 0
        patient_count = (await db.execute(select(func.count(Patient.id)).where(Patient.hospital_id == h.id))).scalar() or 0

        # Total SaaS revenue collected from this hospital
        saas_paid = (await db.execute(select(func.sum(HospitalSubscriptionHistory.amount_paid)).where(HospitalSubscriptionHistory.hospital_id == h.id))).scalar() or 0.0

        # Recent error count (last 7 days)
        err_count = (await db.execute(select(func.count(TenantErrorLog.id)).where(TenantErrorLog.hospital_id == h.id))).scalar() or 0

        results.append({
            "id": h.id,
            "name": h.name,
            "slug": h.slug,
            "phone": h.phone,
            "email": h.email,
            "is_active": h.is_active,
            "subscription_plan": h.subscription_plan,
            "max_doctors": h.max_doctors,
            "active_doctors": doc_count,
            "doctor_quota_used_pct": round((doc_count / max(1, h.max_doctors)) * 100, 1),
            "ai_voice_enabled": h.ai_voice_enabled,
            "plan_status": h.plan_status,
            "plan_expires_at": h.plan_expires_at.isoformat() if h.plan_expires_at else None,
            "days_left": days_left,
            "is_expiring_soon": days_left <= 7 and h.plan_status == "ACTIVE",
            "total_patients": patient_count,
            "total_appointments": appt_count,
            "total_saas_revenue_inr": float(saas_paid),
            "error_count": err_count,
            "health_status": "HEALTHY" if err_count == 0 else ("WARNING" if err_count < 5 else "DEGRADED"),
            "created_at": h.created_at.isoformat() if h.created_at else None
        })

    return results

@router.get("/hospitals/{hospital_id}/360")
async def get_hospital_360_deep_audit(
    hospital_id: str,
    db: AsyncSession = Depends(get_db),
    admin=Depends(require_super_admin)
) -> Dict[str, Any]:
    """
    Returns complete 360-degree operational, clinical, AI voice, and financial audit for a single hospital.
    """
    hospital = (await db.execute(select(Hospital).where(Hospital.id == hospital_id))).scalar_one_or_none()
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital not found")

    now = datetime.now(timezone.utc)
    days_left = 0
    if hospital.plan_expires_at:
        exp = hospital.plan_expires_at if hospital.plan_expires_at.tzinfo else hospital.plan_expires_at.replace(tzinfo=timezone.utc)
        days_left = max(0, (exp - now).days)

    # 1. Subscription Ledger History
    sub_hist_stmt = select(HospitalSubscriptionHistory).where(HospitalSubscriptionHistory.hospital_id == hospital_id).order_by(HospitalSubscriptionHistory.created_at.desc())
    sub_history = (await db.execute(sub_hist_stmt)).scalars().all()

    # 2. Doctors Roster
    doctors_stmt = select(Doctor).where(Doctor.hospital_id == hospital_id, Doctor.is_active == True)
    doctors = (await db.execute(doctors_stmt)).scalars().all()

    # 3. Appointment Funnel
    appts_stmt = select(Appointment).where(Appointment.hospital_id == hospital_id)
    appts = (await db.execute(appts_stmt)).scalars().all()
    
    total_appts = len(appts)
    completed_appts = sum(1 for a in appts if a.status == "COMPLETED")
    cancelled_appts = sum(1 for a in appts if a.status == "CANCELLED")
    missed_appts = sum(1 for a in appts if a.status == "MISSED")
    paid_appts = sum(1 for a in appts if a.payment_status == "PAID")
    pending_pay_appts = sum(1 for a in appts if a.payment_status != "PAID")

    # 4. Recent Voice Calls
    calls_stmt = select(CallLog).where(CallLog.hospital_id == hospital_id).order_by(CallLog.created_at.desc()).limit(15)
    calls = (await db.execute(calls_stmt)).scalars().all()
    total_calls_count = (await db.execute(select(func.count(CallLog.id)).where(CallLog.hospital_id == hospital_id))).scalar() or 0

    # 5. Tenant Error Telemetry
    errors_stmt = select(TenantErrorLog).where(TenantErrorLog.hospital_id == hospital_id).order_by(TenantErrorLog.occurred_at.desc()).limit(20)
    errors = (await db.execute(errors_stmt)).scalars().all()

    return {
        "profile": {
            "id": hospital.id,
            "name": hospital.name,
            "slug": hospital.slug,
            "phone": hospital.phone,
            "email": hospital.email,
            "timezone": hospital.timezone,
            "is_active": hospital.is_active,
            "subscription_plan": hospital.subscription_plan,
            "max_doctors": hospital.max_doctors,
            "active_doctors": len(doctors),
            "ai_voice_enabled": hospital.ai_voice_enabled,
            "plan_status": hospital.plan_status,
            "plan_expires_at": hospital.plan_expires_at.isoformat() if hospital.plan_expires_at else None,
            "days_left": days_left,
            "joined_date": hospital.created_at.isoformat() if hospital.created_at else None
        },
        "subscription_history": [
            {
                "id": s.id,
                "event_type": s.event_type,
                "plan_name": s.plan_name,
                "amount_paid": float(s.amount_paid),
                "currency": s.currency,
                "payment_ref": s.payment_ref,
                "duration_days_added": s.duration_days_added,
                "plan_started_at": s.plan_started_at.isoformat() if s.plan_started_at else None,
                "plan_expires_at": s.plan_expires_at.isoformat() if s.plan_expires_at else None,
                "triggered_by": s.triggered_by,
                "notes": s.notes,
                "created_at": s.created_at.isoformat() if s.created_at else None
            }
            for s in sub_history
        ],
        "doctors": [
            {
                "id": d.id,
                "name": f"Dr. {d.first_name} {d.last_name}",
                "email": d.email,
                "phone": d.phone,
                "opd_fees": d.opd_fees or 500,
                "license_number": d.license_number
            }
            for d in doctors
        ],
        "operations_funnel": {
            "total_appointments": total_appts,
            "completed": completed_appts,
            "cancelled": cancelled_appts,
            "missed": missed_appts,
            "paid_payments": paid_appts,
            "pending_payments": pending_pay_appts,
            "completion_rate_pct": round((completed_appts / total_appts * 100), 1) if total_appts > 0 else 100.0
        },
        "ai_voice_telemetry": {
            "total_calls_handled": total_calls_count,
            "recent_calls": [
                {
                    "id": c.id,
                    "caller_number": c.caller_number,
                    "call_duration": c.call_duration or 0,
                    "intent": c.intent or "General Inquiry",
                    "status": c.status or "COMPLETED",
                    "created_at": c.created_at.isoformat() if c.created_at else None
                }
                for c in calls
            ]
        },
        "recent_errors": [
            {
                "id": e.id,
                "service_name": e.service_name,
                "severity": e.severity,
                "error_code": e.error_code,
                "error_message": e.error_message,
                "occurred_at": e.occurred_at.isoformat() if e.occurred_at else None,
                "resolution_status": e.resolution_status
            }
            for e in errors
        ]
    }
