import re
import uuid
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy import select, and_, or_, func
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

    @classmethod
    async def search_platform_hospital(
        cls,
        query: str,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Global platform hospital lookup for SuperAdmin across all tenant hospitals.
        Returns hospital contact details, phone, email, address, subscription plan, and active doctor count.
        """
        if not db:
            return {"error": "Active database session required."}

        raw_query = (query or "").strip()
        clean_q = raw_query.lower()
        stopwords = [
            "hospital", "hospitals", "hospita", "hosp", "total", "revenue", "all", "time", 
            "earnings", "earning", "collection", "collections", "dues", "status", "overview",
            "ka", "ki", "ke", "number", "contact", "phone", "details", "batao", "do", "mujhe", 
            "info", "search", "find", "lookup", "show", "get", "please", "kaha", "hai"
        ]
        for sw in stopwords:
            clean_q = re.sub(rf'\b{sw}\b', '', clean_q, flags=re.IGNORECASE)
        clean_q = re.sub(r'[^\w\s]', ' ', clean_q).strip()
        search_term = f"%{clean_q}%" if clean_q else "%"

        stmt = select(Hospital).where(
            Hospital.is_active == True,
            or_(
                Hospital.name.ilike(search_term),
                Hospital.slug.ilike(search_term),
                Hospital.id.ilike(search_term),
                Hospital.address.ilike(search_term)
            )
        ).limit(10)
        hospitals = (await db.execute(stmt)).scalars().all()

        # Token-based fallback if multiple words remain or typo exists
        if not hospitals and clean_q:
            tokens = [w for w in clean_q.split() if len(w) >= 3]
            for tok in tokens:
                tok_term = f"%{tok}%"
                tok_stmt = select(Hospital).where(
                    Hospital.is_active == True,
                    or_(
                        Hospital.name.ilike(tok_term),
                        Hospital.slug.ilike(tok_term),
                        Hospital.id.ilike(tok_term)
                    )
                ).limit(10)
                tok_hospitals = (await db.execute(tok_stmt)).scalars().all()
                if tok_hospitals:
                    hospitals = tok_hospitals
                    break

        if not hospitals and clean_q != raw_query.lower():
            # Fallback search with raw query
            fallback_term = f"%{raw_query}%"
            fb_stmt = select(Hospital).where(
                Hospital.is_active == True,
                or_(
                    Hospital.name.ilike(fallback_term),
                    Hospital.slug.ilike(fallback_term),
                    Hospital.address.ilike(fallback_term)
                )
            ).limit(10)
            hospitals = (await db.execute(fb_stmt)).scalars().all()

        results = []
        for h in hospitals:
            doc_stmt = select(func.count(Doctor.id)).where(Doctor.hospital_id == h.id, Doctor.is_active == True)
            doc_count = (await db.execute(doc_stmt)).scalar() or 0
            results.append({
                "hospital_id": h.id,
                "name": h.name.strip() if h.name else "Hospital",
                "phone": h.phone or "N/A",
                "email": h.email or "N/A",
                "address": h.address or "N/A",
                "slug": h.slug,
                "subscription_plan": h.subscription_plan,
                "plan_status": h.plan_status,
                "plan_expires_at": h.plan_expires_at.strftime("%Y-%m-%d") if h.plan_expires_at else "N/A",
                "ai_voice_enabled": h.ai_voice_enabled,
                "active_doctors": doc_count
            })

        return {
            "query": raw_query,
            "total_found": len(results),
            "hospitals": results
        }

