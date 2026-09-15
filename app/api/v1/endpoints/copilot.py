from typing import Optional, List
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.core.dependencies import get_current_user
from app.database.models.call_log import User, Role, UserRole
from app.database.models.appointment import Hospital
from app.database.models.copilot import CopilotConversation, CopilotMessage
from app.engines.copilot_engine import CopilotEngine

router = APIRouter(prefix="/copilot", tags=["copilot"])

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    active_tab: Optional[str] = "overview"
    selected_date: Optional[str] = None

class MessageDTO(BaseModel):
    role: str
    content: str
    created_at: Optional[str] = None

class ChatResponse(BaseModel):
    conversation_id: str
    reply: str
    tool_used: Optional[str] = None

import logging
from datetime import datetime, date

logger = logging.getLogger("aura.copilot")

def make_json_serializable(val):
    if isinstance(val, (datetime, date)):
        return val.isoformat()
    if isinstance(val, dict):
        return {k: make_json_serializable(v) for k, v in val.items()}
    if isinstance(val, list):
        return [make_json_serializable(item) for item in val]
    return val

@router.post("/chat", response_model=ChatResponse)
async def chat_with_copilot(
    req: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticated, tenant-isolated endpoint for AURA AI Copilot.
    """
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    try:
        # 1. Resolve User Role
        role_stmt = select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == current_user.id)
        roles = (await db.execute(role_stmt)).scalars().all()
        primary_role = roles[0] if roles else ("SUPER_ADMIN" if current_user.hospital_id == "super_admin" or not current_user.hospital_id else "RECEPTIONIST")

        # 2. Resolve Hospital Name & Detailed Actor Profile
        hospital_name = "AURA SaaS Platform"
        if current_user.hospital_id:
            h_stmt = select(Hospital).where(Hospital.id == current_user.hospital_id)
            hosp = (await db.execute(h_stmt)).scalar_one_or_none()
            if hosp:
                hospital_name = hosp.name

        actor_profile: Dict[str, Any] = {
            "role": primary_role,
            "user_id": current_user.id,
            "username": current_user.username,
            "hospital_id": current_user.hospital_id,
            "hospital_name": hospital_name
        }

        # Detailed Actor Hydration for Doctor / Patient
        role_upper = (primary_role or "").upper().replace(" ", "_")
        if role_upper == "DOCTOR":
            from app.database.models.appointment import Doctor, Department, DoctorSchedule
            from sqlalchemy import or_
            doc_stmt = (
                select(Doctor, Department)
                .outerjoin(Department, Doctor.department_id == Department.id)
                .where(
                    Doctor.hospital_id == current_user.hospital_id,
                    or_(
                        Doctor.id == current_user.id,
                        Doctor.email == current_user.email,
                        Doctor.first_name.ilike(f"%{current_user.username}%"),
                        Doctor.last_name.ilike(f"%{current_user.username}%")
                    )
                )
            )
            doc_row = (await db.execute(doc_stmt)).first()
            if not doc_row:
                doc_stmt = (
                    select(Doctor, Department)
                    .outerjoin(Department, Doctor.department_id == Department.id)
                    .where(Doctor.hospital_id == current_user.hospital_id, Doctor.is_active == True)
                )
                doc_row = (await db.execute(doc_stmt)).first()

            if doc_row:
                doc_obj, dept_obj = doc_row
                actor_profile["doctor_id"] = doc_obj.id
                actor_profile["doctor_name"] = f"Dr. {doc_obj.first_name} {doc_obj.last_name}".strip()
                actor_profile["department"] = dept_obj.name if dept_obj else "General OPD"
                actor_profile["opd_fees"] = doc_obj.opd_fees or 500

                sched_stmt = select(DoctorSchedule).where(DoctorSchedule.doctor_id == doc_obj.id).order_by(DoctorSchedule.day_of_week.asc())
                schedules = (await db.execute(sched_stmt)).scalars().all()
                day_map = {1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu", 5: "Fri", 6: "Sat", 7: "Sun"}
                timing_items = [f"{day_map.get(s.day_of_week, 'Day')}: {s.start_time.strftime('%I:%M %p')} - {s.end_time.strftime('%I:%M %p')}" for s in schedules]
                actor_profile["timings"] = ", ".join(timing_items) if timing_items else "Standard OPD Hours"
        elif role_upper == "PATIENT":
            from app.database.models.appointment import Patient
            pat_stmt = select(Patient).where(
                Patient.hospital_id == current_user.hospital_id,
                or_(
                    Patient.id == current_user.id,
                    Patient.phone == current_user.username
                )
            )
            pat_obj = (await db.execute(pat_stmt)).scalar_one_or_none()
            if pat_obj:
                actor_profile["patient_id"] = pat_obj.id
                actor_profile["patient_name"] = f"{pat_obj.first_name} {pat_obj.last_name}".strip()
                actor_profile["patient_phone"] = pat_obj.phone

        # 3. Retrieve or create conversation session
        conv = None
        if req.conversation_id:
            conv_stmt = select(CopilotConversation).where(
                CopilotConversation.id == req.conversation_id,
                CopilotConversation.user_id == current_user.id
            )
            conv = (await db.execute(conv_stmt)).scalar_one_or_none()

        if not conv:
            conv = CopilotConversation(
                hospital_id=current_user.hospital_id,
                user_id=current_user.id,
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
            user_id=current_user.id,
            hospital_id=current_user.hospital_id,
            role=primary_role,
            hospital_name=hospital_name,
            active_tab=req.active_tab or "overview",
            selected_date=req.selected_date or "",
            chat_history=chat_history,
            db=db,
            actor_profile=actor_profile
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

        return ChatResponse(
            conversation_id=conv.id,
            reply=reply_text,
            tool_used=result.get("tool_used")
        )
    except Exception as e:
        logger.exception("Copilot chat endpoint error")
        await db.rollback()
        return ChatResponse(
            conversation_id=req.conversation_id or "default",
            reply="Aapke request ko process karne me takleef hui. Kripya doctor ka naam ya date dobara check karein.",
            tool_used=None
        )


@router.get("/history/{conversation_id}")
async def get_conversation_history(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Fetches chat thread history for a session."""
    conv_stmt = select(CopilotConversation).where(
        CopilotConversation.id == conversation_id,
        CopilotConversation.user_id == current_user.id
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
