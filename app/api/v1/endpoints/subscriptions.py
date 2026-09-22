import json
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.core.dependencies import get_current_user
from app.database.models.call_log import User, Role, UserRole
from app.database.models.appointment import Hospital
from app.database.models.control_tower import SubscriptionPlanConfig, HospitalSubscriptionHistory

router = APIRouter(tags=["subscription"])


@router.get("/plans", tags=["subscription"])
async def get_subscription_plans(db: AsyncSession = Depends(get_db)):
    """Fetches all active SaaS subscription plans with live pricing, doctor quotas, and feature lists."""
    stmt = select(SubscriptionPlanConfig).where(SubscriptionPlanConfig.is_active == 1).order_by(SubscriptionPlanConfig.price_inr.asc())
    rows = (await db.execute(stmt)).scalars().all()

    # Fallback to defaults if table is empty
    if not rows:
        return [
            {
                "plan_code": "STARTER",
                "display_name": "Starter (15-Day Free Trial)",
                "description": "15-Day Free Trial for clinics and small hospitals. Renews at ₹1,500/month after trial.",
                "price_inr": 1500.0,
                "billing_cycle": "MONTHLY",
                "duration_days": 15,
                "max_doctors": 1,
                "ai_voice_enabled": False,
                "whatsapp_enabled": True,
                "online_opd_enabled": True,
                "features": [
                    "15-Day Full Access Free Trial",
                    "1 Active Doctor Profile",
                    "Basic OPD Schedule & Patient Queue",
                    "Manual Appointment Management",
                    "Post-Trial Renewal: ₹1,500 / month"
                ]
            },
            {
                "plan_code": "PRO",
                "display_name": "Pro AI Plan",
                "description": "Full-scale Voice AI receptionist and automated patient operations for growing hospitals.",
                "price_inr": 2999.0,
                "billing_cycle": "MONTHLY",
                "duration_days": 30,
                "max_doctors": 5,
                "ai_voice_enabled": True,
                "whatsapp_enabled": True,
                "online_opd_enabled": True,
                "features": [
                    "24/7 Live AI Voice Call Receptionist",
                    "Up to 5 Active Doctor Profiles",
                    "Automated WhatsApp Confirmations",
                    "Online OPD Payments (Razorpay)",
                    "30-Day Monthly Billing Cycle"
                ]
            },
            {
                "plan_code": "ENTERPRISE",
                "display_name": "Enterprise 360",
                "description": "Unlimited enterprise scale with priority AI voice lines, custom branding, and annual SLA.",
                "price_inr": 29999.0,
                "billing_cycle": "YEARLY",
                "duration_days": 365,
                "max_doctors": 999,
                "ai_voice_enabled": True,
                "whatsapp_enabled": True,
                "online_opd_enabled": True,
                "features": [
                    "Unlimited Doctor Profiles",
                    "Dedicated Low-Latency Voice LLM",
                    "Custom Domain & White-Label Branding",
                    "Multi-Branch & Priority SRE Support",
                    "365-Day Annual Billing (Best Value)"
                ]
            }
        ]

    plans = []
    for r in rows:
        feat_list = []
        if r.features_json:
            try:
                feat_list = json.loads(r.features_json) if isinstance(r.features_json, str) else r.features_json
            except Exception:
                feat_list = []
        plans.append({
            "id": r.id,
            "plan_code": r.plan_code,
            "display_name": r.display_name,
            "description": r.description or "",
            "price_inr": float(r.price_inr),
            "billing_cycle": r.billing_cycle,
            "duration_days": r.duration_days,
            "max_doctors": r.max_doctors,
            "ai_voice_enabled": bool(r.ai_voice_enabled),
            "whatsapp_enabled": bool(r.whatsapp_enabled),
            "online_opd_enabled": bool(r.online_opd_enabled),
            "features": feat_list
        })
    return plans


@router.put("/admin/plans/{plan_code}", tags=["admin"])
async def update_subscription_plan_config(
    plan_code: str,
    price_inr: float = Form(..., description="Plan Price in INR"),
    max_doctors: int = Form(..., description="Max doctors allowed for this tier"),
    duration_days: int = Form(..., description="Duration in days added on purchase"),
    ai_voice_enabled: int = Form(1, description="1 if AI Voice is enabled, 0 if disabled"),
    features_json: Optional[str] = Form(None, description="JSON array of features"),
    description: Optional[str] = Form(None, description="Plan description"),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_user)
):
    """Super Admin: Dynamically updates plan pricing, quotas, and capabilities."""
    role_stmt = select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == current_admin.id)
    roles = (await db.execute(role_stmt)).scalars().all()
    is_super_admin = (
        "SUPER_ADMIN" in roles 
        or current_admin.hospital_id == "super_admin"
    )
    if not is_super_admin:
        raise HTTPException(status_code=403, detail="Only Platform Owners (SUPER_ADMIN) can configure plans.")

    plan_stmt = select(SubscriptionPlanConfig).where(SubscriptionPlanConfig.plan_code == plan_code.upper().strip())
    plan_cfg = (await db.execute(plan_stmt)).scalar_one_or_none()
    if not plan_cfg:
        raise HTTPException(status_code=404, detail=f"Plan {plan_code} not found.")

    plan_cfg.price_inr = price_inr
    plan_cfg.max_doctors = max_doctors
    plan_cfg.duration_days = duration_days
    plan_cfg.ai_voice_enabled = ai_voice_enabled
    if features_json is not None:
        plan_cfg.features_json = features_json
    elif plan_cfg.plan_code == "STARTER":
        plan_cfg.features_json = json.dumps([
            "15-Day Full Access Free Trial",
            f"{max_doctors} Active Doctor Profile" if max_doctors == 1 else f"Up to {max_doctors} Active Doctor Profiles",
            "Basic OPD Schedule & Patient Queue",
            "Manual Appointment Management",
            f"Post-Trial Renewal: ₹{int(price_inr):,} / month"
        ])
    if description is not None:
        plan_cfg.description = description

    await db.commit()
    await db.refresh(plan_cfg)

    return {
        "success": True,
        "message": f"Plan {plan_cfg.plan_code} updated successfully.",
        "plan": {
            "plan_code": plan_cfg.plan_code,
            "display_name": plan_cfg.display_name,
            "price_inr": float(plan_cfg.price_inr),
            "max_doctors": plan_cfg.max_doctors,
            "duration_days": plan_cfg.duration_days,
            "ai_voice_enabled": bool(plan_cfg.ai_voice_enabled)
        }
    }


@router.post("/hospitals/{hospital_id}/upgrade-plan", tags=["admin"])
async def upgrade_hospital_plan(
    hospital_id: str,
    plan_name: str = Form(..., description="Plan Name: STARTER, PRO, ENTERPRISE"),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_user)
):
    """Upgrades hospital subscription tier, extending validity and dynamically applying quotas from DB.
    Protected: Requires SuperAdmin or matching Hospital Admin. Enforces strict tenant isolation.
    """
    # 1. Enforce RBAC & Tenant Isolation (IDOR-02 protection)
    role_stmt = select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == current_admin.id)
    roles = set((await db.execute(role_stmt)).scalars().all())

    is_super_admin = "SUPER_ADMIN" in roles or current_admin.hospital_id == "super_admin"
    is_hospital_admin = bool(roles.intersection({"ADMIN", "HOSPITAL_ADMIN"}))

    if not is_super_admin:
        if not is_hospital_admin or current_admin.hospital_id != hospital_id:
            raise HTTPException(
                status_code=403,
                detail="Forbidden: You can only upgrade subscriptions for your own hospital."
            )

    hosp_stmt = select(Hospital).where(Hospital.id == hospital_id)
    hospital = (await db.execute(hosp_stmt)).scalar_one_or_none()
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital not found")

    plan_upper = plan_name.upper().strip()

    # Query dynamic plan configuration
    plan_cfg_stmt = select(SubscriptionPlanConfig).where(SubscriptionPlanConfig.plan_code == plan_upper)
    plan_cfg = (await db.execute(plan_cfg_stmt)).scalar_one_or_none()

    if plan_cfg:
        amount = float(plan_cfg.price_inr)
        days_added = plan_cfg.duration_days
        max_docs = plan_cfg.max_doctors
        ai_enabled = bool(plan_cfg.ai_voice_enabled)
    else:
        if plan_upper == "STARTER":
            amount, days_added, max_docs, ai_enabled = 1000.0, 15, 1, False
        elif plan_upper == "PRO":
            amount, days_added, max_docs, ai_enabled = 2999.0, 30, 5, True
        elif plan_upper == "ENTERPRISE":
            amount, days_added, max_docs, ai_enabled = 29999.0, 365, 999, True
        else:
            raise HTTPException(status_code=400, detail="Invalid plan name specified.")

    base_time = datetime.now()
    if hospital.plan_expires_at and hospital.plan_expires_at > base_time:
        base_time = hospital.plan_expires_at

    hospital.subscription_plan = plan_upper
    hospital.max_doctors = max_docs
    hospital.ai_voice_enabled = ai_enabled
    hospital.plan_expires_at = base_time + timedelta(days=days_added)
    hospital.plan_status = "ACTIVE"
    hospital.is_active = True

    sub_entry = HospitalSubscriptionHistory(
        hospital_id=hospital.id,
        event_type="UPGRADE",
        plan_name=hospital.subscription_plan,
        amount_paid=amount,
        currency="INR",
        duration_days_added=days_added,
        plan_started_at=datetime.now(),
        plan_expires_at=hospital.plan_expires_at,
        triggered_by=current_admin.username if current_admin else "SYSTEM"
    )
    db.add(sub_entry)
    await db.commit()
    await db.refresh(hospital)

    diff_sec = (hospital.plan_expires_at - datetime.now()).total_seconds()
    days_left = max(0, int(diff_sec / 86400))

    return {
        "success": True,
        "subscription_plan": hospital.subscription_plan,
        "max_doctors": hospital.max_doctors,
        "ai_voice_enabled": hospital.ai_voice_enabled,
        "plan_expires_at": str(hospital.plan_expires_at),
        "days_left": days_left,
        "message": f"🎉 Subscription Plan successfully upgraded to {hospital.subscription_plan}!"
    }


@router.post("/hospitals/{hospital_id}/renew-plan", tags=["admin"])
async def renew_hospital_plan(
    hospital_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_user)
):
    """Renews the current active subscription plan adding 30 days (for PRO) or 365 days (for Enterprise)."""
    hosp_stmt = select(Hospital).where(Hospital.id == hospital_id)
    hospital = (await db.execute(hosp_stmt)).scalar_one_or_none()
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital not found")

    plan = hospital.subscription_plan or "STARTER"

    plan_cfg_stmt = select(SubscriptionPlanConfig).where(SubscriptionPlanConfig.plan_code == plan)
    plan_cfg = (await db.execute(plan_cfg_stmt)).scalar_one_or_none()

    if plan_cfg:
        amount = float(plan_cfg.price_inr)
        days_to_add = plan_cfg.duration_days
        max_docs = plan_cfg.max_doctors
        ai_enabled = bool(plan_cfg.ai_voice_enabled)
    else:
        if plan == "PRO":
            amount, days_to_add, max_docs, ai_enabled = 2999.0, 30, 5, True
        elif plan == "ENTERPRISE":
            amount, days_to_add, max_docs, ai_enabled = 29999.0, 365, 999, True
        else:
            amount, days_to_add, max_docs, ai_enabled = 1000.0, 30, 1, False

    base_time = datetime.now()
    if hospital.plan_expires_at and hospital.plan_expires_at > base_time:
        base_time = hospital.plan_expires_at

    hospital.plan_expires_at = base_time + timedelta(days=days_to_add)
    hospital.max_doctors = max_docs
    hospital.ai_voice_enabled = ai_enabled
    hospital.plan_status = "ACTIVE"
    hospital.is_active = True

    sub_entry = HospitalSubscriptionHistory(
        hospital_id=hospital.id,
        event_type="RENEWAL",
        plan_name=hospital.subscription_plan,
        amount_paid=amount,
        currency="INR",
        duration_days_added=days_to_add,
        plan_started_at=datetime.now(),
        plan_expires_at=hospital.plan_expires_at,
        triggered_by=current_admin.username if current_admin else "SYSTEM"
    )
    db.add(sub_entry)
    await db.commit()
    await db.refresh(hospital)

    diff_sec = (hospital.plan_expires_at - datetime.now()).total_seconds()
    days_left = max(0, int(diff_sec / 86400))

    return {
        "success": True,
        "subscription_plan": hospital.subscription_plan,
        "max_doctors": hospital.max_doctors,
        "ai_voice_enabled": hospital.ai_voice_enabled,
        "plan_expires_at": str(hospital.plan_expires_at),
        "days_left": days_left,
        "message": f"🎉 Subscription {hospital.subscription_plan} Plan renewed successfully! Added {days_to_add} days."
    }
