import jwt
import uuid
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.database.session import get_db
from app.database.models.call_log import User, Role, UserRole
from app.database.models.appointment import Hospital, Patient
from app.database.models.copilot import CopilotConversation, CopilotMessage
from app.engines.copilot_engine import CopilotEngine

router = APIRouter(prefix="/copilot", tags=["copilot"])

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    active_tab: Optional[str] = "overview"
    selected_date: Optional[str] = None
    hospital_id: Optional[str] = None
    slug: Optional[str] = None
    patient_name: Optional[str] = None
    patient_phone: Optional[str] = None
    patient_data: Optional[Dict[str, Any]] = None

class MessageDTO(BaseModel):
    role: str
    content: str
    created_at: Optional[str] = None

class ChatResponse(BaseModel):
    conversation_id: str
    reply: str
    tool_used: Optional[str] = None
    suggestions: Optional[List[str]] = None

logger = logging.getLogger("aura.copilot")

def make_json_serializable(val):
    if isinstance(val, (datetime, date)):
        return val.isoformat()
    if isinstance(val, dict):
        return {k: make_json_serializable(v) for k, v in val.items()}
    if isinstance(val, list):
        return [make_json_serializable(item) for item in val]
    return val

async def get_copilot_actor(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Flexible actor resolver for AURA AI Copilot:
    Supports Staff JWTs, Patient Portal JWTs, and Unauthenticated/Guest Patient browsing.
    """
    auth_header = request.headers.get("Authorization")
    token = None
    if auth_header and auth_header.startswith("Bearer "):
        raw_token = auth_header.split(" ")[1].strip()
        if raw_token not in ("null", "undefined", "", "None"):
            token = raw_token

    if token:
        try:
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            token_role = (payload.get("role") or "").upper()
            
            if token_role == "PATIENT":
                patient_id = payload.get("user_id")
                phone = payload.get("sub")
                pat = None
                if patient_id:
                    pat = await db.get(Patient, patient_id)
                if not pat and phone:
                    p_stmt = select(Patient).where(Patient.phone == phone)
                    pat = (await db.execute(p_stmt)).scalar_one_or_none()

                hosp_id = payload.get("hospital_id") or (pat.hospital_id if pat else None)
                hosp_name = "Hospital"
                if hosp_id:
                    h = (await db.execute(select(Hospital).where(Hospital.id == hosp_id))).scalar_one_or_none()
                    if h:
                        hosp_name = h.name

                pname = f"{pat.first_name} {pat.last_name}".strip() if pat else "Patient"
                pphone = pat.phone if pat else phone
                return {
                    "role": "PATIENT",
                    "user_id": pat.id if pat else (patient_id or "ANONYMOUS_PATIENT"),
                    "username": pname,
                    "hospital_id": hosp_id,
                    "hospital_name": hosp_name,
                    "patient_id": pat.id if pat else patient_id,
                    "patient_name": pname,
                    "patient_phone": pphone
                }
            else:
                # Staff User
                username = payload.get("sub")
                user = (await db.execute(select(User).where(User.username == username, User.is_active == True))).scalar_one_or_none()
                if user:
                    role_stmt = select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == user.id)
                    roles = (await db.execute(role_stmt)).scalars().all()
                    primary_role = roles[0] if roles else ("SUPER_ADMIN" if user.hospital_id == "super_admin" or not user.hospital_id else "RECEPTIONIST")
                    
                    hosp_name = "AURA SaaS Platform"
                    if user.hospital_id:
                        h_stmt = select(Hospital).where(Hospital.id == user.hospital_id)
                        hosp = (await db.execute(h_stmt)).scalar_one_or_none()
                        if hosp:
                            hosp_name = hosp.name

                    actor = {
                        "role": primary_role,
                        "user_id": user.id,
                        "username": user.username,
                        "hospital_id": user.hospital_id,
                        "hospital_name": hosp_name
                    }

                    role_upper = (primary_role or "").upper().replace(" ", "_")
                    if role_upper == "DOCTOR":
                        from app.database.models.appointment import Doctor, Department, DoctorSchedule
                        from sqlalchemy import or_
                        doc_stmt = (
                            select(Doctor, Department)
                            .outerjoin(Department, Doctor.department_id == Department.id)
                            .where(
                                Doctor.hospital_id == user.hospital_id,
                                or_(
                                    Doctor.id == user.id,
                                    Doctor.email == user.email,
                                    Doctor.first_name.ilike(f"%{user.username}%"),
                                    Doctor.last_name.ilike(f"%{user.username}%")
                                )
                            )
                        )
                        doc_row = (await db.execute(doc_stmt)).first()
                        if not doc_row:
                            doc_stmt = (
                                select(Doctor, Department)
                                .outerjoin(Department, Doctor.department_id == Department.id)
                                .where(Doctor.hospital_id == user.hospital_id, Doctor.is_active == True)
                            )
                            doc_row = (await db.execute(doc_stmt)).first()

                        if doc_row:
                            doc_obj, dept_obj = doc_row
                            actor["doctor_id"] = doc_obj.id
                            actor["doctor_name"] = f"Dr. {doc_obj.first_name} {doc_obj.last_name}".strip()
                            actor["department"] = dept_obj.name if dept_obj else "General OPD"
                            actor["opd_fees"] = doc_obj.opd_fees or 500

                            sched_stmt = select(DoctorSchedule).where(DoctorSchedule.doctor_id == doc_obj.id).order_by(DoctorSchedule.day_of_week.asc())
                            schedules = (await db.execute(sched_stmt)).scalars().all()
                            day_map = {1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu", 5: "Fri", 6: "Sat", 7: "Sun"}
                            timing_items = [f"{day_map.get(s.day_of_week, 'Day')}: {s.start_time.strftime('%I:%M %p')} - {s.end_time.strftime('%I:%M %p')}" for s in schedules]
                            actor["timings"] = ", ".join(timing_items) if timing_items else "Standard OPD Hours"

                    return actor
        except Exception as e:
            logger.debug(f"JWT decode in get_copilot_actor fallback: {e}")

    # Fallback: Guest Patient / Portal Visitor
    return {
        "role": "PATIENT",
        "user_id": "GUEST_PATIENT",
        "username": "Guest Patient",
        "hospital_id": None,
        "hospital_name": "Hospital"
    }

@router.post("/chat", response_model=ChatResponse)
async def chat_with_copilot(
    req: ChatRequest,
    actor: Dict[str, Any] = Depends(get_copilot_actor),
    db: AsyncSession = Depends(get_db)
):
    """
    Unified Copilot endpoint for Staff, Authenticated Patients, and Portal Visitors.
    """
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    if actor.get("user_id") == "GUEST_PATIENT" and not (req.slug or req.hospital_id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token or hospital context required.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    try:
        # Resolve tenant hospital if not known from user token
        hospital_id = actor.get("hospital_id")
        hospital_name = actor.get("hospital_name", "Hospital")

        if not hospital_id:
            if req.slug:
                h_stmt = select(Hospital).where(Hospital.slug == req.slug, Hospital.is_active == True)
                hosp = (await db.execute(h_stmt)).scalar_one_or_none()
                if hosp:
                    hospital_id = hosp.id
                    hospital_name = hosp.name
            elif req.hospital_id:
                h_stmt = select(Hospital).where(Hospital.id == req.hospital_id, Hospital.is_active == True)
                hosp = (await db.execute(h_stmt)).scalar_one_or_none()
                if hosp:
                    hospital_id = hosp.id
                    hospital_name = hosp.name
            actor["hospital_id"] = hospital_id
            actor["hospital_name"] = hospital_name

        # Check Hospital Subscription Expiry (Except for SuperAdmin)
        if hospital_id and actor.get("role") != "SUPER_ADMIN":
            h_chk_stmt = select(Hospital).where(Hospital.id == hospital_id)
            h_chk = (await db.execute(h_chk_stmt)).scalar_one_or_none()
            if h_chk and h_chk.plan_expires_at:
                now_dt = datetime.now()
                if h_chk.plan_expires_at < now_dt:
                    exp_date_str = h_chk.plan_expires_at.strftime('%d %b %Y')
                    return ChatResponse(
                        conversation_id=req.conversation_id or f"conv_{uuid.uuid4().hex[:8]}",
                        reply=f"🔒 **{h_chk.name} का सब्सक्रिप्शन प्लान समाप्त (Expired) हो चुका है।**\n\n* **प्लान:** {h_chk.subscription_plan or 'STARTER'}\n* **समाप्ति तिथि:** {exp_date_str}\n\nAI Copilot, ऑटोमेटेड अपॉइंटमेंट्स और हॉस्पिटल ऑटोमेशन दोबारा सक्रिय करने के लिए कृपया **Settings / Plans** से प्लान रिन्यू करें।",
                        tool_used="subscription_paywall",
                        suggestions=["Renew Subscription Plan", "View Available Plans"]
                    )

        # Hydrate logged-in patient details from request body if available
        if req.patient_phone and not actor.get("patient_phone"):
            actor["patient_phone"] = req.patient_phone
        if req.patient_name and not actor.get("patient_name"):
            actor["patient_name"] = req.patient_name
        if req.patient_data:
            if not actor.get("patient_phone") and req.patient_data.get("phone"):
                actor["patient_phone"] = req.patient_data.get("phone")
            if not actor.get("patient_name") and req.patient_data.get("name"):
                actor["patient_name"] = req.patient_data.get("name")
            if not actor.get("patient_id") and req.patient_data.get("id"):
                actor["patient_id"] = req.patient_data.get("id")

        user_id = actor.get("user_id") or "GUEST_PATIENT"

        # 3. Retrieve or create conversation session
        conv = None
        if req.conversation_id:
            conv_stmt = select(CopilotConversation).where(
                CopilotConversation.id == req.conversation_id
            )
            conv = (await db.execute(conv_stmt)).scalar_one_or_none()

        if not conv:
            conv = CopilotConversation(
                hospital_id=hospital_id,
                user_id=user_id,
                portal_context=req.active_tab or "overview"
            )
            db.add(conv)
            await db.flush()

        # 4. Fetch past messages for memory
        msg_stmt = select(CopilotMessage).where(CopilotMessage.conversation_id == conv.id).order_by(CopilotMessage.created_at.asc())
        past_messages = (await db.execute(msg_stmt)).scalars().all()
        chat_history = [{"role": m.role, "content": m.content} for m in past_messages]

        # Save incoming user message
        user_msg = CopilotMessage(
            conversation_id=conv.id,
            role="user",
            content=req.message.strip()
        )
        db.add(user_msg)
        await db.flush()

        # 5. Execute Copilot Engine Turn with Hydrated Actor Profile
        result = await CopilotEngine.chat(
            user_message=req.message.strip(),
            user_id=user_id,
            hospital_id=hospital_id,
            role=actor.get("role", "PATIENT"),
            hospital_name=hospital_name,
            active_tab=req.active_tab or "overview",
            selected_date=req.selected_date or "",
            chat_history=chat_history,
            db=db,
            actor_profile=actor
        )

        reply_text = result.get("reply", "I am here to help.")

        # Save assistant response
        assistant_msg = CopilotMessage(
            conversation_id=conv.id,
            role="assistant",
            content=reply_text,
            tool_name=result.get("tool_used"),
            tool_call_data=make_json_serializable(result.get("tool_result"))
        )
        db.add(assistant_msg)
        await db.commit()

        suggestions = result.get("suggestions")
        if not suggestions:
            suggestions = CopilotEngine._build_contextual_suggestions(
                role=actor.get("role", "PATIENT"),
                tool_used=result.get("tool_used"),
                query=req.message.strip(),
                reply=reply_text
            )

        return ChatResponse(
            conversation_id=conv.id,
            reply=reply_text,
            tool_used=result.get("tool_used"),
            suggestions=suggestions
        )
    except Exception as e:
        logger.exception("Copilot chat endpoint error")
        await db.rollback()
        return ChatResponse(
            conversation_id=req.conversation_id or "default",
            reply="Aapke request ko process karne me takleef hui. Kripya doctor ka naam ya date dobara check karein.",
            tool_used=None,
            suggestions=None
        )


@router.get("/history/{conversation_id}")
async def get_conversation_history(
    conversation_id: str,
    actor: Dict[str, Any] = Depends(get_copilot_actor),
    db: AsyncSession = Depends(get_db)
):
    """Fetches chat thread history for a session."""
    conv_stmt = select(CopilotConversation).where(
        CopilotConversation.id == conversation_id
    )
    conv = (await db.execute(conv_stmt)).scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    msg_stmt = select(CopilotMessage).where(CopilotMessage.conversation_id == conv.id).order_by(CopilotMessage.created_at.asc())
    messages = (await db.execute(msg_stmt)).scalars().all()

    return {
        "conversation_id": conv.id,
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "tool_used": m.tool_name,
                "created_at": m.created_at.isoformat() if m.created_at else None
            }
            for m in messages
        ]
    }
