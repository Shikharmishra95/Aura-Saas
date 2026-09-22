import uuid
import asyncio
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy import select, and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.core.dependencies import get_current_user
from app.core.logging import logger
from app.database.models.call_log import User, Role, UserRole
from app.database.models.appointment import Appointment, Patient, Doctor, Hospital, AppointmentStatusHistory, ConsultationNote
from app.services.whatsapp import WhatsAppNotificationService

router = APIRouter(tags=["doctor"])


@router.post("/appointments/{appointment_id}/status", tags=["receptionist"])
async def update_appointment_status(
    appointment_id: str,
    new_status: str = Form(..., description="COMPLETED, CANCELLED, MISSED, or RESCHEDULED"),
    new_datetime: Optional[str] = Form(None, description="ISO datetime for RESCHEDULED status"),
    cutoff_note: Optional[str] = Form(None, description="Arrival cutoff instruction for patient"),
    cancellation_reason: Optional[str] = Form(None, description="Reason for cancellation (for refund WhatsApp)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Hospital staff action endpoint to update appointment status.
    Protected: Requires authenticated staff (RECEPTIONIST, ADMIN, DOCTOR) or SUPER_ADMIN.
    Enforces strict tenant isolation: non-superadmin callers cannot modify appointments of other hospitals.
    On RESCHEDULED, updates time and sends WhatsApp to patient.
    """
    # 1. Enforce RBAC: staff or superadmin
    role_stmt = select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == current_user.id)
    roles = set((await db.execute(role_stmt)).scalars().all())

    is_super_admin = "SUPER_ADMIN" in roles or current_user.hospital_id == "super_admin"
    is_staff = bool(roles.intersection({"RECEPTIONIST", "ADMIN", "DOCTOR"}))

    if not is_super_admin and not is_staff:
        raise HTTPException(
            status_code=403,
            detail="Unauthorized: Only hospital staff (Doctor, Receptionist, Admin) or SuperAdmin can update appointment status."
        )

    # 2. Lookup appointment
    stmt = select(Appointment).where(Appointment.id == appointment_id)
    appointment = (await db.execute(stmt)).scalar_one_or_none()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found.")

    # 3. Enforce tenant isolation
    if not is_super_admin and appointment.hospital_id != current_user.hospital_id:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Cannot modify appointment belonging to another hospital."
        )

    old_status = appointment.status

    # Validate reschedule rules
    if new_status == "RESCHEDULED":
        is_paid = appointment.payment_status in ["PAID", "COMPLETED", "SUCCESS", "PAID_RECEPTION", "captured"]
        if not is_paid:
            raise HTTPException(status_code=400, detail="Reschedule is strictly allowed only for paid appointments.")
        
        if (appointment.reschedule_count or 0) >= 1:
            raise HTTPException(status_code=400, detail="This appointment has already reached the maximum limit of 1 reschedule.")
        
        now = datetime.now()
        if old_status == "MISSED" or appointment.appointment_datetime < now:
            if now > appointment.appointment_datetime + timedelta(hours=48):
                raise HTTPException(status_code=400, detail="Reschedule window expired. Rescheduling is only allowed within 48 hours of missed appointment.")

        if not new_datetime:
            raise HTTPException(status_code=400, detail="New datetime required for rescheduling.")

        try:
            target_dt = datetime.fromisoformat(new_datetime)
            max_allowed_date = now.date() + timedelta(days=2)
            if target_dt.date() < now.date() or target_dt.date() > max_allowed_date:
                raise HTTPException(status_code=400, detail="Rescheduling is strictly restricted to dates within the next 2 days.")
            appointment.appointment_datetime = target_dt
            appointment.reschedule_count = (appointment.reschedule_count or 0) + 1
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid datetime format. Use ISO format.")

    appointment.status = new_status
    appointment.updated_at = datetime.now()

    history = AppointmentStatusHistory(
        id=str(uuid.uuid4()),
        appointment_id=appointment.id,
        previous_status=old_status,
        new_status=new_status,
        changed_by_user_id=current_user.id,
        change_reason=f"Status updated to {new_status} by {current_user.username}"
    )
    db.add(history)
    try:
        await db.flush()
        patient_stmt = select(Patient).where(Patient.id == appointment.patient_id)
        patient = (await db.execute(patient_stmt)).scalar_one_or_none()
        doctor_stmt = select(Doctor).where(Doctor.id == appointment.doctor_id)
        doctor = (await db.execute(doctor_stmt)).scalar_one_or_none()
        await db.commit()
    except IntegrityError as ie:
        await db.rollback()
        logger.warning(f"Reschedule conflict prevented by unique constraint in doctor_queue: {ie}")
        raise HTTPException(
            status_code=400,
            detail="The selected time slot is already booked for this doctor. Please choose another slot."
        )

    if new_status == "RESCHEDULED" and patient and new_datetime:
        wa_service = WhatsAppNotificationService()
        wa_details = {
            "patient_name": f"{patient.first_name} {patient.last_name}".strip(),
            "patient_phone": patient.phone,
            "doctor_name": f"Dr. {doctor.first_name} {doctor.last_name}" if doctor else "Doctor",
            "new_datetime": new_datetime,
            "cutoff_note": cutoff_note or ""
        }
        asyncio.create_task(wa_service.send_reschedule_notification(wa_details))

    elif new_status == "MISSED" and patient:
        wa_service = WhatsAppNotificationService()
        wa_details = {
            "patient_name": f"{patient.first_name} {patient.last_name}".strip(),
            "patient_phone": patient.phone,
            "doctor_name": f"Dr. {doctor.first_name} {doctor.last_name}" if doctor else "Doctor",
            "appointment_datetime": appointment.appointment_datetime.isoformat(),
            "reason": appointment.reason or "General consultation"
        }
        asyncio.create_task(wa_service.send_missed_notification(wa_details))

    elif new_status == "CANCELLED" and patient:
        wa_service = WhatsAppNotificationService()
        wa_details = {
            "patient_name": f"{patient.first_name} {patient.last_name}".strip(),
            "patient_phone": patient.phone,
            "doctor_name": f"Dr. {doctor.first_name} {doctor.last_name}" if doctor else "Doctor",
            "appointment_datetime": appointment.appointment_datetime.isoformat(),
            "reason": cancellation_reason or "Hospital cancellation request",
            "is_paid": old_status == "SCHEDULED"
        }
        asyncio.create_task(wa_service.send_cancellation_refund_notification(wa_details))

    return {"success": True, "appointment_id": appointment_id, "new_status": new_status}


@router.post("/appointments/{appointment_id}/finish-consultation", tags=["doctor"])
async def finish_doctor_consultation(
    appointment_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Doctor finishes physical consultation for a patient.
    Transitions status to CONSULTATION_FINISHED so receptionist can digitize prescription & complete appointment.
    """
    appt_stmt = select(Appointment).where(
        and_(
            Appointment.id == appointment_id,
            Appointment.hospital_id == current_user.hospital_id
        )
    )
    appt = (await db.execute(appt_stmt)).scalar_one_or_none()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found.")

    appt.status = "CONSULTATION_FINISHED"
    appt.consultation_status = "FINISHED"
    appt.updated_at = datetime.now()
    await db.commit()
    await db.refresh(appt)
    return {"status": "success", "message": "Doctor finished consultation! Sent to Receptionist desk."}


@router.post("/appointments/{appointment_id}/complete", tags=["doctor"])
async def complete_consultation(
    appointment_id: str,
    clinical_notes: str = Form("", description="Doctor's clinical summary/notes"),
    prescription: str = Form("", description="Prescription medicines details"),
    follow_up_date: Optional[str] = Form(None, description="Follow-up date in YYYY-MM-DD format"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Saves consultation summary, writes prescription,
    transitions status to COMPLETED, and sends prescription details via WhatsApp.
    """
    role_stmt = select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == current_user.id)
    roles = (await db.execute(role_stmt)).scalars().all()
    if "DOCTOR" not in roles and "ADMIN" not in roles and "RECEPTIONIST" not in roles and "SUPER_ADMIN" not in roles:
        raise HTTPException(status_code=403, detail="Only Doctors, Receptionists, or Admins can complete a consultation.")

    try:
        appt_stmt = select(Appointment).where(
            and_(
                Appointment.id == appointment_id,
                Appointment.hospital_id == current_user.hospital_id
            )
        )
        appt = (await db.execute(appt_stmt)).scalar_one_or_none()
        if not appt:
            raise HTTPException(status_code=404, detail="Appointment not found in this hospital.")

        old_status = appt.status
        if old_status == "COMPLETED":
            raise HTTPException(status_code=400, detail="Consultation already completed.")

        appt.status = "COMPLETED"
        appt.consultation_status = "DONE"
        appt.updated_at = datetime.now()

        history = AppointmentStatusHistory(
            id=str(uuid.uuid4()),
            appointment_id=appt.id,
            previous_status=old_status,
            new_status="COMPLETED",
            changed_by_user_id=current_user.id,
            change_reason="Consultation completed by doctor."
        )
        db.add(history)

        f_up_date = None
        if follow_up_date and follow_up_date.strip() and follow_up_date.strip().lower() not in ["", "null", "undefined"]:
            try:
                f_up_date = datetime.strptime(follow_up_date.strip(), "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format for follow_up_date. Use YYYY-MM-DD.")

        note_stmt = select(ConsultationNote).where(ConsultationNote.appointment_id == appointment_id)
        note = (await db.execute(note_stmt)).scalar_one_or_none()
        if not note:
            note = ConsultationNote(
                id=str(uuid.uuid4()),
                appointment_id=appointment_id,
                patient_id=appt.patient_id,
                doctor_id=appt.doctor_id,
                clinical_notes=clinical_notes,
                prescription=prescription,
                follow_up_date=f_up_date
            )
            db.add(note)
        else:
            note.clinical_notes = clinical_notes
            note.prescription = prescription
            note.follow_up_date = f_up_date

        patient_stmt = select(Patient).where(Patient.id == appt.patient_id)
        patient = (await db.execute(patient_stmt)).scalar_one_or_none()
        
        doctor_stmt = select(Doctor).where(Doctor.id == appt.doctor_id)
        doctor = (await db.execute(doctor_stmt)).scalar_one_or_none()
        doc_name = f"Dr. {doctor.first_name} {doctor.last_name}" if doctor else "Doctor"

        hosp_stmt = select(Hospital).where(Hospital.id == appt.hospital_id)
        hospital = (await db.execute(hosp_stmt)).scalar_one_or_none()
        hosp_name = hospital.name if hospital else "Hospital"

        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.error(f"Error completing consultation transaction: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail="Failed to complete consultation.")

    if patient and patient.phone:
        wa_service = WhatsAppNotificationService()
        wa_details = {
            "phone": patient.phone,
            "patient_name": f"{patient.first_name} {patient.last_name}".strip(),
            "doctor_name": doc_name,
            "hospital_name": hosp_name,
            "clinical_notes": clinical_notes,
            "prescription": prescription,
            "follow_up_date": follow_up_date or "N/A"
        }
        try:
            await wa_service.send_prescription_notification(wa_details)
        except Exception as wa_err:
            logger.error(f"WhatsApp prescription notification failed: {str(wa_err)}")

    return {
        "success": True,
        "message": "Consultation completed and prescription sent to patient.",
        "appointment_id": appointment_id
    }
