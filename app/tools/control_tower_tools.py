import uuid
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.appointment import Hospital, Doctor
from app.database.models.control_tower import HospitalSubscriptionHistory
from app.engines.conversation_memory import conversation_memory

logger = logging.getLogger("aura.tools.control_tower")

class ControlTowerTools:
    """
    AURA SuperAdmin & Platform Control Tower Operations:
    - Upcoming Subscription Renewals & Expiration Monitoring
    - Extend / Renew Hospital SaaS Subscriptions (Immutable Ledger)
    - Toggle Tenant AI Telephony Voice Agent Status
    """

    @classmethod
    async def get_expiring_subscriptions_report(
        cls,
        days_threshold: int = 30,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Lists all tenant hospitals whose SaaS subscriptions are expiring within the specified threshold.
        """
        if not db:
            return {"error": "Active database session required."}

        now = datetime.now()
        target_limit = now + timedelta(days=days_threshold)

        stmt = (
            select(Hospital)
            .where(
                Hospital.is_active == True,
                Hospital.plan_expires_at != None,
                Hospital.plan_expires_at <= target_limit
            )
            .order_by(Hospital.plan_expires_at.asc())
        )
        hospitals = (await db.execute(stmt)).scalars().all()

        exp_list = []
        for h in hospitals:
            days_left = max((h.plan_expires_at - now).days, 0) if h.plan_expires_at else 0
            exp_list.append({
                "hospital_id": h.id,
                "hospital_name": h.name.strip() if h.name else "Hospital",
                "plan": h.subscription_plan,
                "expires_at": h.plan_expires_at.strftime("%Y-%m-%d"),
                "days_remaining": days_left,
                "contact_phone": h.phone,
                "contact_email": h.email or "N/A",
                "status": h.plan_status
            })

        return {
            "expiring_hospitals": exp_list,
            "total_expiring": len(exp_list),
            "threshold_days": days_threshold
        }

    @classmethod
    async def extend_hospital_subscription(
        cls,
        hospital_id: str,
        duration_days: int = 30,
        plan_name: Optional[str] = None,
        notes: Optional[str] = None,
        user_id: Optional[str] = None,
        confirmation_token: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Extends or renews a hospital SaaS subscription and records an immutable ledger entry.
        """
        if not db:
            return {"success": False, "error": "Active database session required."}

        # 1. Fetch Hospital
        hosp_stmt = select(Hospital).where(Hospital.id == hospital_id.strip())
        hospital = (await db.execute(hosp_stmt)).scalar_one_or_none()
        if not hospital:
            return {"success": False, "error": f"Hospital '{hospital_id}' not found."}

        now = datetime.now()
        base_date = hospital.plan_expires_at if (hospital.plan_expires_at and hospital.plan_expires_at > now) else now
        new_expiry = base_date + timedelta(days=duration_days)
        target_plan = plan_name or hospital.subscription_plan

        # 2. Confirmation Check
        if not confirmation_token:
            summary = f"Extend {hospital.name.strip()} ({target_plan}) by {duration_days} days until {new_expiry.strftime('%Y-%m-%d')}"
            token_rec = conversation_memory.create_confirmation_token(
                hospital_id=hospital.id,
                user_id=user_id or "SUPER_ADMIN",
                action_name="extend_hospital_subscription",
                action_args={
                    "hospital_id": hospital.id,
                    "duration_days": duration_days,
                    "plan_name": target_plan,
                    "notes": notes
                },
                summary=summary,
                expires_in_seconds=120
            )
            return {
                "status": "CONFIRMATION_REQUIRED",
                "confirmation_token": token_rec.token,
                "summary": summary,
                "hospital_id": hospital.id,
                "hospital_name": hospital.name.strip(),
                "duration_days": duration_days,
                "current_expiry": hospital.plan_expires_at.strftime("%Y-%m-%d") if hospital.plan_expires_at else "Expired",
                "new_expiry": new_expiry.strftime("%Y-%m-%d"),
                "plan": target_plan,
                "message": f"⚠️ Please confirm subscription extension for {hospital.name.strip()}. Reply with: CONFIRM {token_rec.token}"
            }

        # 3. Validate Token
        consumed = conversation_memory.validate_and_consume_token(
            token=confirmation_token,
            hospital_id=hospital.id,
            user_id=user_id or "SUPER_ADMIN"
        )
        if not consumed:
            return {"success": False, "error": "Confirmation token is invalid or has expired."}

        # 4. Update Hospital Expiry
        hospital.plan_expires_at = new_expiry
        hospital.subscription_plan = target_plan
        hospital.plan_status = "ACTIVE"
        hospital.updated_at = now

        # 5. Write Immutable Ledger Entry
        ledger_entry = HospitalSubscriptionHistory(
            id=str(uuid.uuid4()),
            hospital_id=hospital.id,
            event_type="RENEWAL",
            plan_name=target_plan,
            amount_paid=0.0,
            currency="INR",
            payment_ref="MANUAL_ADMIN_OVERRIDE",
            duration_days_added=duration_days,
            plan_started_at=base_date,
            plan_expires_at=new_expiry,
            triggered_by=user_id or "SUPER_ADMIN",
            notes=notes or f"Extended by {duration_days} days via AURA Copilot",
            created_at=now
        )
        db.add(ledger_entry)
        await db.commit()

        return {
            "success": True,
            "hospital_name": hospital.name.strip(),
            "new_expiry_date": new_expiry.strftime("%Y-%m-%d"),
            "plan": target_plan,
            "days_added": duration_days,
            "message": f"Subscription for {hospital.name.strip()} successfully extended by {duration_days} days until {new_expiry.strftime('%Y-%m-%d')}."
        }

    @classmethod
    async def toggle_hospital_ai_voice_service(
        cls,
        hospital_id: str,
        enabled: bool,
        user_id: Optional[str] = None,
        confirmation_token: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Toggles tenant AI Voice telephony integration with Action Confirmation.
        """
        if not db:
            return {"success": False, "error": "Active database session required."}

        hosp_stmt = select(Hospital).where(Hospital.id == hospital_id.strip())
        hospital = (await db.execute(hosp_stmt)).scalar_one_or_none()
        if not hospital:
            return {"success": False, "error": f"Hospital '{hospital_id}' not found."}

        state_str = "ENABLE" if enabled else "DISABLE"

        # 1. Confirmation Check
        if not confirmation_token:
            summary = f"{state_str} AI Voice Telephony for {hospital.name.strip()}"
            token_rec = conversation_memory.create_confirmation_token(
                hospital_id=hospital.id,
                user_id=user_id or "SUPER_ADMIN",
                action_name="toggle_hospital_ai_voice_service",
                action_args={"hospital_id": hospital.id, "enabled": enabled},
                summary=summary,
                expires_in_seconds=120
            )
            return {
                "status": "CONFIRMATION_REQUIRED",
                "confirmation_token": token_rec.token,
                "summary": summary,
                "hospital_name": hospital.name.strip(),
                "requested_state": state_str,
                "message": f"⚠️ Please confirm {state_str} AI Voice telephony for {hospital.name.strip()}. Reply with: CONFIRM {token_rec.token}"
            }

        # 2. Validate Token
        consumed = conversation_memory.validate_and_consume_token(
            token=confirmation_token,
            hospital_id=hospital.id,
            user_id=user_id or "SUPER_ADMIN"
        )
        if not consumed:
            return {"success": False, "error": "Confirmation token is invalid or has expired."}

        # 3. Update Status
        hospital.ai_voice_enabled = enabled
        hospital.updated_at = datetime.now()
        await db.commit()

        return {
            "success": True,
            "hospital_name": hospital.name.strip(),
            "ai_voice_enabled": hospital.ai_voice_enabled,
            "message": f"AI Voice telephony for {hospital.name.strip()} has been {'enabled' if enabled else 'disabled'} successfully."
        }
