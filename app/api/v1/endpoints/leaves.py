import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.core.dependencies import get_current_user
from app.database.models.call_log import User, Role, UserRole
from app.database.models.appointment import Doctor, DoctorLeave
from app.schemas.appointment import DoctorLeaveCreate, DoctorLeaveRead

router = APIRouter(tags=["hospital"])


@router.post("/hospital/leaves", response_model=DoctorLeaveRead, tags=["hospital"])
async def create_doctor_leave(
    payload: DoctorLeaveCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Allows Doctor or Admin to register a date/range of leave."""
    hosp_id = current_user.hospital_id if current_user.hospital_id else "hosp_default"
    
    # Auto-detect doctor if current user is a DOCTOR
    role_stmt = select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == current_user.id)
    roles = (await db.execute(role_stmt)).scalars().all()
    if "DOCTOR" in roles:
        doc_stmt_curr = select(Doctor).where(Doctor.id == current_user.id)
        curr_doc = (await db.execute(doc_stmt_curr)).scalar_one_or_none()
        if curr_doc:
            payload.doctor_id = curr_doc.id

    doc_stmt = select(Doctor).where(Doctor.id == payload.doctor_id)
    doctor = (await db.execute(doc_stmt)).scalar_one_or_none()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    
    if doctor.hospital_id != hosp_id and current_user.username != "super_admin":
        raise HTTPException(status_code=403, detail="Unauthorized hospital access")
    
    leave_id = str(uuid.uuid4())
    new_leave = DoctorLeave(
        id=leave_id,
        doctor_id=payload.doctor_id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        reason=payload.reason,
        status=payload.status or "PENDING"
    )
    db.add(new_leave)
    await db.commit()
    await db.refresh(new_leave)
    return new_leave


@router.get("/hospital/leaves", tags=["hospital"])
async def list_doctor_leaves(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetches all registered doctor leaves for the hospital."""
    hosp_id = current_user.hospital_id if current_user.hospital_id else "hosp_default"
    stmt = select(DoctorLeave, Doctor).join(Doctor, DoctorLeave.doctor_id == Doctor.id).where(Doctor.hospital_id == hosp_id)
    results = (await db.execute(stmt)).all()
    
    leaves_info = []
    for leave, doc in results:
        leaves_info.append({
            "id": leave.id,
            "doctor_id": doc.id,
            "doctor_name": f"Dr. {doc.first_name} {doc.last_name}",
            "start_date": leave.start_date.isoformat(),
            "end_date": leave.end_date.isoformat(),
            "reason": leave.reason,
            "status": leave.status,
            "created_at": leave.created_at.isoformat()
        })
    return leaves_info


@router.delete("/hospital/leaves/{leave_id}", tags=["hospital"])
async def delete_doctor_leave(
    leave_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cancels/deletes a doctor leave record."""
    hosp_id = current_user.hospital_id if current_user.hospital_id else "hosp_default"
    stmt = select(DoctorLeave).join(Doctor, DoctorLeave.doctor_id == Doctor.id).where(
        (DoctorLeave.id == leave_id) & (Doctor.hospital_id == hosp_id)
    )
    leave = (await db.execute(stmt)).scalar_one_or_none()
    if not leave:
        raise HTTPException(status_code=404, detail="Leave record not found or unauthorized")
    
    await db.delete(leave)
    await db.commit()
    return {"status": "success", "message": "Leave deleted successfully"}


@router.post("/hospital/leaves/{leave_id}/approve", tags=["hospital"])
async def approve_doctor_leave(
    leave_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Approves a pending doctor leave request (Admin or Receptionist only)."""
    role_stmt = select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == current_user.id)
    roles = (await db.execute(role_stmt)).scalars().all()
    if "ADMIN" not in roles and "RECEPTIONIST" not in roles:
        raise HTTPException(status_code=403, detail="Only Hospital Admins and Receptionists can approve leaves.")

    hosp_id = current_user.hospital_id if current_user.hospital_id else "hosp_default"
    stmt = select(DoctorLeave).join(Doctor, DoctorLeave.doctor_id == Doctor.id).where(
        (DoctorLeave.id == leave_id) & (Doctor.hospital_id == hosp_id)
    )
    leave = (await db.execute(stmt)).scalar_one_or_none()
    if not leave:
        raise HTTPException(status_code=404, detail="Leave record not found or unauthorized")

    leave.status = "APPROVED"
    await db.commit()
    return {"status": "success", "message": "Leave request approved successfully"}


@router.post("/hospital/leaves/{leave_id}/reject", tags=["hospital"])
async def reject_doctor_leave(
    leave_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Rejects a pending doctor leave request (Admin or Receptionist only)."""
    role_stmt = select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == current_user.id)
    roles = (await db.execute(role_stmt)).scalars().all()
    if "ADMIN" not in roles and "RECEPTIONIST" not in roles:
        raise HTTPException(status_code=403, detail="Only Hospital Admins and Receptionists can reject leaves.")

    hosp_id = current_user.hospital_id if current_user.hospital_id else "hosp_default"
    stmt = select(DoctorLeave).join(Doctor, DoctorLeave.doctor_id == Doctor.id).where(
        (DoctorLeave.id == leave_id) & (Doctor.hospital_id == hosp_id)
    )
    leave = (await db.execute(stmt)).scalar_one_or_none()
    if not leave:
        raise HTTPException(status_code=404, detail="Leave record not found or unauthorized")

    leave.status = "REJECTED"
    await db.commit()
    return {"status": "success", "message": "Leave request rejected successfully"}


@router.post("/hospital/leaves/{leave_id}/cancel", tags=["hospital"])
async def cancel_doctor_leave(
    leave_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cancels an already-approved doctor leave request (Admin or Receptionist only). Keeps the leave record."""
    role_stmt = select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == current_user.id)
    roles = (await db.execute(role_stmt)).scalars().all()
    if "ADMIN" not in roles and "RECEPTIONIST" not in roles:
        raise HTTPException(status_code=403, detail="Only Hospital Admins and Receptionists can cancel leaves.")

    hosp_id = current_user.hospital_id if current_user.hospital_id else "hosp_default"
    stmt = select(DoctorLeave).join(Doctor, DoctorLeave.doctor_id == Doctor.id).where(
        (DoctorLeave.id == leave_id) & (Doctor.hospital_id == hosp_id)
    )
    leave = (await db.execute(stmt)).scalar_one_or_none()
    if not leave:
        raise HTTPException(status_code=404, detail="Leave record not found or unauthorized")

    leave.status = "CANCELLED"
    await db.commit()
    return {"status": "success", "message": "Leave has been cancelled successfully"}
