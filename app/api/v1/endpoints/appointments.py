import uuid
import os
import asyncio
from datetime import date, datetime, timedelta
from typing import Optional
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException, Query, Form
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.core.dependencies import get_current_user
from app.core.config import settings
from app.core.logging import logger
from app.database.models.call_log import User, Role, UserRole
from app.database.models.appointment import Doctor, Patient, Hospital, Department, Appointment, ConsultationNote
from app.engines.appointment import AppointmentEngine
from app.engines.scheduling import SchedulingEngine
from app.schemas.appointment import (
    AppointmentCreate, AppointmentRead, AvailableSlotsResponse
)
from app.services.whatsapp import WhatsAppNotificationService

router = APIRouter(tags=["appointments"])

# ─── Missed Appointment Sweeper Throttle ───────────────────────────────────
# Prevents expensive full-table scan from running on every API request.
# Sweeper runs at most once per hour per server process.
_last_sweep_run: Optional[datetime] = None
SWEEP_INTERVAL_SECONDS = 3600  # 1 hour
# ───────────────────────────────────────────────────────────────────────────


async def auto_update_missed_appointments(db: AsyncSession):
    """
    Sweeper that auto-marks expired appointments as MISSED and dispatches WhatsApp notifications.
    Throttled: runs at most once per hour to avoid full-table scan on every request.
    - Any appointment whose appointment_datetime has passed is marked MISSED.
    - Sends WhatsApp missed notification for each newly marked missed appointment.
    """
    global _last_sweep_run
    now = datetime.now()

    # Skip if sweeper ran recently (within last hour)
    if _last_sweep_run and (now - _last_sweep_run).total_seconds() < SWEEP_INTERVAL_SECONDS:
        return
    _last_sweep_run = now

    try:
        now = datetime.now()
        start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        stmt = (
            select(Appointment)
            .options(
                selectinload(Appointment.patient),
                selectinload(Appointment.doctor),
                selectinload(Appointment.hospital)
            )
            .where(
                and_(
                    Appointment.appointment_datetime < start_of_today,
                    Appointment.status.in_(["SCHEDULED", "CONFIRMED", "PENDING_PAYMENT", "RESCHEDULED"])
                )
            )
        )
        expired_appts = (await db.execute(stmt)).scalars().all()
        
        if not expired_appts:
            return

        wa_service = WhatsAppNotificationService()
        
        for appt in expired_appts:
            appt.status = "MISSED"
            appt.consultation_status = "MISSED"
            appt.updated_at = now
            
            try:
                patient = appt.patient
                doctor = appt.doctor
                hospital = appt.hospital
                
                if patient and doctor and hospital:
                    details = {
                        "patient_phone": patient.phone,
                        "patient_name": f"{patient.first_name} {patient.last_name}".strip(),
                        "doctor_name": f"Dr. {doctor.first_name} {doctor.last_name}",
                        "date": appt.appointment_datetime.strftime("%Y-%m-%d"),
                        "time": appt.appointment_datetime.strftime("%I:%M %p"),
                        "hospital_name": hospital.name,
                        "hospital_id": hospital.id
                    }
                    asyncio.create_task(wa_service.send_missed_notification(details))
            except Exception as wa_err:
                logger.error(f"Failed to send missed WA msg for {appt.id}: {wa_err}")

        await db.commit()
    except Exception as e:
        logger.error(f"Error running auto-missed sweep: {str(e)}", exc_info=True)


@router.get("/appointments", tags=["appointments"])
async def list_all_appointments(
    doctor_id: Optional[str] = None,
    status: Optional[str] = Query(None, description="Filter by status: SCHEDULED, PENDING_PAYMENT, ARRIVED, MISSED, COMPLETED, CANCELLED"),
    search: Optional[str] = Query(None, description="Search by patient name or phone"),
    date_from: Optional[str] = Query(None, description="Filter from date YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="Filter to date YYYY-MM-DD"),
    limit: int = Query(100, ge=1, le=500, description="Max records to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieves appointments with pagination, filtering, and search support."""
    await auto_update_missed_appointments(db)

    stmt = (
        select(Appointment, Patient, Doctor, Department, ConsultationNote)
        .join(Patient, Appointment.patient_id == Patient.id)
        .join(Doctor, Appointment.doctor_id == Doctor.id)
        .join(Department, Doctor.department_id == Department.id)
        .outerjoin(ConsultationNote, Appointment.id == ConsultationNote.appointment_id)
    )

    if current_user.hospital_id and current_user.hospital_id != "super_admin":
        stmt = stmt.where(Appointment.hospital_id == current_user.hospital_id)

    if doctor_id:
        target_doc_id = doctor_id
        doc_stmt = select(Doctor).where(or_(Doctor.id == doctor_id, Doctor.first_name.ilike(f"%{doctor_id}%")))
        matched_doc = (await db.execute(doc_stmt)).scalars().first()
        if matched_doc:
            target_doc_id = matched_doc.id
        stmt = stmt.where(Appointment.doctor_id == target_doc_id)

    if status:
        stmt = stmt.where(Appointment.status == status.upper())

    if date_from:
        try:
            df = datetime.strptime(date_from, "%Y-%m-%d")
            stmt = stmt.where(Appointment.appointment_datetime >= df)
        except ValueError:
            pass
    if date_to:
        try:
            dt = datetime.strptime(date_to, "%Y-%m-%d")
            stmt = stmt.where(Appointment.appointment_datetime <= dt)
        except ValueError:
            pass

    if search:
        search_term = f"%{search}%"
        stmt = stmt.where(
            or_(
                Patient.first_name.ilike(search_term),
                Patient.last_name.ilike(search_term),
                Patient.phone.ilike(search_term)
            )
        )

    stmt = stmt.order_by(Appointment.appointment_datetime.desc()).limit(limit).offset(offset)
    results = (await db.execute(stmt)).all()

    appts = []
    for appt, patient, doctor, dept, note in results:
        patient_age = None
        if patient.date_of_birth:
            from datetime import date as date_type
            today = date_type.today()
            dob = patient.date_of_birth
            patient_age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            if dob.year == 1990 and dob.month == 1 and dob.day == 1:
                patient_age = None

        resolved_patient_name = None
        if hasattr(appt, 'patient_name_override') and appt.patient_name_override:
            resolved_patient_name = appt.patient_name_override
        elif appt.reason and appt.reason.startswith("For:"):
            try:
                for_part = appt.reason.split("|")[0].strip()
                extracted = for_part.replace("For:", "").split("(")[0].strip()
                if extracted:
                    resolved_patient_name = extracted
            except Exception:
                pass

        if not resolved_patient_name:
            resolved_patient_name = f"{patient.first_name} {patient.last_name}".strip()

        resolved_booker_name = appt.booked_by_name if (hasattr(appt, 'booked_by_name') and appt.booked_by_name) else None
        if not resolved_booker_name and resolved_patient_name != f"{patient.first_name} {patient.last_name}".strip():
            resolved_booker_name = f"{patient.first_name} {patient.last_name}".strip()

        appts.append({
            "id": appt.id,
            "patient_id": patient.id,
            "patient_name": resolved_patient_name,
            "patient_phone": patient.phone,
            "patient_age": patient_age,
            "booked_by_name": resolved_booker_name,
            "doctor_id": doctor.id,
            "doctor_name": f"Dr. {doctor.first_name} {doctor.last_name}",
            "department_name": dept.name,
            "appointment_datetime": appt.appointment_datetime.isoformat(),
            "reason": appt.reason,
            "payment_status": appt.payment_status,
            "consultation_status": appt.consultation_status,
            "status": appt.status,
            "reschedule_count": appt.reschedule_count if hasattr(appt, 'reschedule_count') and appt.reschedule_count is not None else 0,
            "source": appt.source if hasattr(appt, 'source') else "MANUAL",
            "clinical_notes": note.clinical_notes if note else None,
            "prescription": note.prescription if note else None,
            "follow_up_date": note.follow_up_date.isoformat() if note and note.follow_up_date else None,
            "consultation_completed_at": note.created_at.isoformat() if note and note.created_at else None,
            "created_at": appt.created_at.isoformat() if appt.created_at else None
        })
    return appts


@router.post("/appointments", response_model=AppointmentRead)
async def create_appointment(
    payload: AppointmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Creates a new patient booking, verifying slots availability."""
    try:
        existing_stmt = select(Appointment).where(
            Appointment.patient_id == payload.patient_id,
            Appointment.doctor_id == payload.doctor_id,
            Appointment.appointment_datetime == payload.appointment_datetime,
            Appointment.status.in_(["SCHEDULED", "PENDING_PAYMENT"])
        )
        existing = (await db.execute(existing_stmt)).scalar_one_or_none()
        if existing:
            logger.info(f"Idempotent booking triggered: Appointment already exists for patient={payload.patient_id}, doctor={payload.doctor_id}, time={payload.appointment_datetime}. Returning cached record.")
            return existing
    except Exception as ie:
        logger.error(f"Error during idempotency lookup: {str(ie)}")
        
    try:
        target_hospital_id = payload.hospital_id
        if current_user.hospital_id and current_user.hospital_id != "super_admin":
            target_hospital_id = current_user.hospital_id

        engine = AppointmentEngine(db)
        res = await engine.book_appointment(
            hospital_id=target_hospital_id,
            patient_id=payload.patient_id,
            doctor_id=payload.doctor_id,
            appointment_datetime=payload.appointment_datetime,
            reason=payload.reason or "General Consultation",
            source="PORTAL"
        )
        if res.get("code") != "BOOKING_SUCCESS":
            raise HTTPException(status_code=400, detail=res.get("message", "Booking failed"))
        
        appt_stmt = select(Appointment).where(Appointment.id == res["appointment_id"])
        appt = (await db.execute(appt_stmt)).scalar_one_or_none()
        if not appt:
            raise HTTPException(status_code=500, detail="Appointment created but could not be retrieved")
            
        await db.commit()
        logger.info(f"Booking successfully committed to DB. Appointment ID: {appt.id}")
    except Exception as ex:
        await db.rollback()
        logger.error(f"Error during appointment creation database transaction: {str(ex)}")
        if isinstance(ex, HTTPException):
            raise ex
        raise HTTPException(status_code=500, detail=f"Booking failed due to internal error: {str(ex)}")
        
    warning_code = None
    try:
        from twilio.rest import Client
        from twilio.base.exceptions import TwilioRestException
        
        logger.info(f"Twilio Config: ACCOUNT_SID={settings.TWILIO_ACCOUNT_SID}, SENDER={settings.TWILIO_WHATSAPP_FROM}")
        
        h_stmt = select(Hospital).where(Hospital.id == appt.hospital_id)
        hospital = (await db.execute(h_stmt)).scalar_one_or_none()
        h_name = hospital.name if hospital else "Hospital"
        
        p_stmt = select(Patient).where(Patient.id == appt.patient_id)
        patient = (await db.execute(p_stmt)).scalar_one_or_none()
        p_name = f"{patient.first_name} {patient.last_name}".strip() if patient else "Patient"
        p_phone = patient.phone if patient else ""
        
        d_stmt = select(Doctor).where(Doctor.id == appt.doctor_id)
        doctor = (await db.execute(d_stmt)).scalar_one_or_none()
        d_name = f"Dr. {doctor.first_name} {doctor.last_name}" if doctor else "Doctor"

        raw_to = p_phone.strip()
        if raw_to:
            if not raw_to.startswith("+"):
                if len(raw_to) == 10:
                    raw_to = "+91" + raw_to
                else:
                    raw_to = "+" + raw_to
            final_to = f"whatsapp:{raw_to}"
        else:
            final_to = ""
            
        final_from = settings.TWILIO_WHATSAPP_FROM
        if final_from and not final_from.startswith("whatsapp:"):
            final_from = f"whatsapp:{final_from}"
            
        logger.info(f"Sending WhatsApp message: from_={final_from}, to={final_to}")
        
        if final_to and final_from:
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            appt_display = appt.appointment_datetime.strftime("%d %b %Y, %I:%M %p")
            appt_id_short = appt.id[-8:]
            
            railway_domain = os.environ.get("RAILWAY_STATIC_URL") or os.environ.get("RAILWAY_PUBLIC_DOMAIN")
            if railway_domain:
                base_url = f"https://{railway_domain}" if not railway_domain.startswith("http") else railway_domain.rstrip('/')
            else:
                base_url = settings.TWILIO_WEBHOOK_URL.rstrip('/') if settings.TWILIO_WEBHOOK_URL else settings.PAYMENT_BASE_URL.rstrip('/')
            
            payment_link = f"{base_url}/payment/checkout?appt={appt_id_short}"
            
            message_body = (
                f"🏥 *{h_name}*\n"
                f"✅ *आपकी अपॉइंटमेंट बुक हो गई!*\n\n"
                f"👤 *नाम:* {p_name}\n"
                f"👨‍⚕️ *डॉक्टर:* {d_name}\n"
                f"📅 *तारीख व समय:* {appt_display}\n"
                f"🩺 *समस्या:* {appt.reason}\n"
                f"🆔 *Appointment ID:* {appt_id_short}\n\n"
                f"💳 *Payment करें और अपॉइंटमेंट Confirm करें:*\n"
                f"{payment_link}\n\n"
                f"_Payment के बाद आपकी अपॉइंटमेंट confirmed हो जाएगी।_\n"
                f"_किसी सहायता के लिए हमें call करें।_"
            )
            
            try:
                message = client.messages.create(
                    body=message_body,
                    from_=final_from,
                    to=final_to
                )
                logger.info(f"Twilio response message sent successfully. SID: {message.sid}")
            except TwilioRestException as tre:
                logger.error(f"TwilioRestException caught during synchronous send: code={tre.code}, status={tre.status}, msg={tre.msg}")
                if tre.code == 63012 or "sandbox" in str(tre.msg).lower() or "not opted in" in str(tre.msg).lower():
                    warning_code = "BOOKED_BUT_WHATSAPP_NOT_DELIVERED_SANDBOX"
                else:
                    warning_code = f"TWILIO_ERROR_{tre.code}"
            except Exception as inner_err:
                logger.error(f"Unexpected inner exception in Twilio client send: {str(inner_err)}")
                warning_code = "WHATSAPP_SEND_FAILED"
    except Exception as wa_err:
        logger.error(f"Twilio client initialization or formatting error: {str(wa_err)}")
        warning_code = "WHATSAPP_CONFIG_ERROR"

    if warning_code:
        appt.warning = warning_code
        logger.warning(f"Appointment warning set: {warning_code}")
        
    return appt


@router.delete("/appointments/{appointment_id}", response_model=AppointmentRead)
async def cancel_appointment(
    appointment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cancels an existing appointment."""
    engine = AppointmentEngine(db)
    res = await engine.cancel_appointment(appointment_id)
    if res.get("code") not in ["CANCELLED", "ALREADY_CANCELLED"]:
        raise HTTPException(status_code=400, detail=res.get("message", "Cancellation failed"))
    
    appt_stmt = select(Appointment).where(Appointment.id == appointment_id)
    appt = (await db.execute(appt_stmt)).scalar_one_or_none()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return appt


@router.get("/appointments/availability", response_model=AvailableSlotsResponse)
async def get_doctor_availability(
    doctor_id: str,
    target_date: date,
    db: AsyncSession = Depends(get_db)
):
    """Public query endpoint to fetch free booking slots for a specific doctor."""
    scheduler = SchedulingEngine(db)
    slots = await scheduler.get_available_slots(doctor_id, target_date)
    return AvailableSlotsResponse(doctor_id=doctor_id, slots=slots)


@router.get("/receptionist/booked-slots", tags=["receptionist"])
async def get_booked_slots(
    doctor_id: str = Query(...),
    date_str: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns a list of start times for all booked appointments of a doctor on a specific date.
    Used by the dashboard to show busy slots in RED inside the reschedule modal.
    """
    try:
        from datetime import date as date_type
        target_date = date_type.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    start_dt = datetime.combine(target_date, datetime.min.time())
    end_dt = datetime.combine(target_date, datetime.max.time())

    stmt = (
        select(Appointment)
        .where(
            and_(
                Appointment.doctor_id == doctor_id,
                Appointment.appointment_datetime >= start_dt,
                Appointment.appointment_datetime <= end_dt,
                Appointment.status.in_(["SCHEDULED", "PENDING_PAYMENT", "RESCHEDULED"])
            )
        )
    )
    appointments = (await db.execute(stmt)).scalars().all()
    booked_times = [appt.appointment_datetime.strftime("%I:%M %p") for appt in appointments]
    
    all_slots = []
    from app.database.models.appointment import DoctorSchedule, DoctorLeave
    doc_stmt = select(Doctor).where(Doctor.id == doctor_id, Doctor.is_active == True)
    doctor = (await db.execute(doc_stmt)).scalar_one_or_none()
    
    if doctor:
        day_of_week = target_date.isoweekday()
        
        leave_stmt = select(DoctorLeave).where(
            and_(
                DoctorLeave.doctor_id == doctor_id,
                DoctorLeave.start_date <= target_date,
                DoctorLeave.end_date >= target_date,
                DoctorLeave.status == "APPROVED"
            )
        )
        leave = (await db.execute(leave_stmt)).scalar_one_or_none()
        
        if not leave:
            sched_stmt = select(DoctorSchedule).where(
                and_(
                    DoctorSchedule.doctor_id == doctor_id,
                    DoctorSchedule.day_of_week == day_of_week
                )
            )
            schedules = (await db.execute(sched_stmt)).scalars().all()
            for sched in schedules:
                if sched.slot_duration_minutes and sched.slot_duration_minutes > 0:
                    current_time = datetime.combine(target_date, sched.start_time)
                    end_time_limit = datetime.combine(target_date, sched.end_time)
                    dur = timedelta(minutes=sched.slot_duration_minutes)
                    
                    while current_time + dur <= end_time_limit:
                        all_slots.append(current_time.strftime("%I:%M %p"))
                        current_time += dur
                        
    def sort_key(time_str):
        return datetime.strptime(time_str, "%I:%M %p")
    all_slots = sorted(list(set(all_slots)), key=sort_key)
    
    return {"booked_slots": booked_times, "all_slots": all_slots}


@router.post("/appointments/mark-missed", tags=["hospital"])
async def mark_past_appointments_missed(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Marks all CONFIRMED or SCHEDULED appointments that are in the past as MISSED."""
    hosp_id = current_user.hospital_id if current_user.hospital_id else "hosp_default"
    now = datetime.now()
    
    stmt = select(Appointment).where(
        Appointment.hospital_id == hosp_id,
        Appointment.appointment_datetime < now,
        Appointment.status.in_(["SCHEDULED", "CONFIRMED"])
    )
    past_appts = (await db.execute(stmt)).scalars().all()
    
    count = 0
    wa_service = WhatsAppNotificationService()
    
    for appt in past_appts:
        appt.status = "MISSED"
        appt.consultation_status = "MISSED"
        count += 1
        
        try:
            pat_stmt = select(Patient).where(Patient.id == appt.patient_id)
            patient = (await db.execute(pat_stmt)).scalar_one_or_none()
            doc_stmt = select(Doctor).where(Doctor.id == appt.doctor_id)
            doctor = (await db.execute(doc_stmt)).scalar_one_or_none()
            hosp_stmt = select(Hospital).where(Hospital.id == appt.hospital_id)
            hospital = (await db.execute(hosp_stmt)).scalar_one_or_none()
            
            if patient and doctor and hospital:
                details = {
                    "patient_phone": patient.phone,
                    "patient_name": f"{patient.first_name} {patient.last_name}".strip(),
                    "doctor_name": doctor.first_name + " " + doctor.last_name,
                    "date": appt.appointment_datetime.strftime("%Y-%m-%d"),
                    "time": appt.appointment_datetime.strftime("%I:%M %p"),
                    "hospital_name": hospital.name,
                    "hospital_id": hospital.id
                }
                asyncio.create_task(wa_service.send_missed_notification(details))
        except Exception as wa_err:
            logger.error(f"Failed to send missed WA msg for {appt.id}: {wa_err}")
            
    if count > 0:
        await db.commit()
        
    return {"success": True, "marked_count": count}


class BulkCancelRequest(BaseModel):
    doctor_id: str
    target_date: date
    reason: str


@router.post("/appointments/bulk-cancel", tags=["hospital"])
async def bulk_cancel_appointments(
    payload: BulkCancelRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Cancels all pending/scheduled appointments for a doctor on a specific date."""
    hosp_id = current_user.hospital_id if current_user.hospital_id else "hosp_default"
    
    start_dt = datetime.combine(payload.target_date, datetime.min.time())
    end_dt = datetime.combine(payload.target_date, datetime.max.time())
    
    stmt = select(Appointment).where(
        Appointment.hospital_id == hosp_id,
        Appointment.doctor_id == payload.doctor_id,
        Appointment.appointment_datetime >= start_dt,
        Appointment.appointment_datetime <= end_dt,
        Appointment.status.in_(["SCHEDULED", "CONFIRMED", "PENDING_PAYMENT"])
    )
    appts_to_cancel = (await db.execute(stmt)).scalars().all()
    
    engine = AppointmentEngine(db)
    
    count = 0
    for appt in appts_to_cancel:
        res = await engine.cancel_appointment(appt.id, reason=payload.reason)
        if res.get("code") == "CANCELLED":
            count += 1
            
    if count > 0:
        await db.commit()
        
    return {"success": True, "cancelled_count": count}


class ReceptionistBookRequest(BaseModel):
    patient_name: str
    patient_phone: str
    patient_gender: Optional[str] = "Male"
    patient_dob: Optional[str] = None
    doctor_id: str
    appointment_datetime: datetime
    reason: Optional[str] = None
    payment_mode: Optional[str] = "CASH"
    hospital_id: Optional[str] = None


@router.post("/receptionist/book-appointment", tags=["receptionist"])
async def book_receptionist_appointment(
    req: ReceptionistBookRequest,
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Receptionist Manual Booking Endpoint.
    - Cash Mode: Marks status SCHEDULED, payment_status PAID, sends WhatsApp confirmation without payment link.
    - Online Mode: Marks status PENDING_PAYMENT, payment_status PENDING, sends WhatsApp with checkout link.
    """
    hosp_id = req.hospital_id or (current_user.hospital_id if current_user and current_user.hospital_id else None)
    if not hosp_id:
        h_stmt = select(Hospital.id).limit(1)
        hosp_id = (await db.execute(h_stmt)).scalar_one_or_none() or "hosp_default"

    clean_phone = req.patient_phone.strip()
    if clean_phone.startswith("whatsapp:"):
        clean_phone = clean_phone.replace("whatsapp:", "").strip()

    name_parts = req.patient_name.strip().split(" ", 1)
    p_first = name_parts[0]
    p_last = name_parts[1] if len(name_parts) > 1 else ""

    p_stmt = select(Patient).where(Patient.hospital_id == hosp_id, Patient.phone == clean_phone, Patient.first_name == p_first)
    patient = (await db.execute(p_stmt)).scalars().first()

    payment_mode = (req.payment_mode or "CASH").upper()

    if patient:
        existing_stmt = select(Appointment).where(
            Appointment.patient_id == patient.id,
            Appointment.doctor_id == req.doctor_id,
            Appointment.appointment_datetime == req.appointment_datetime,
            Appointment.status.in_(["SCHEDULED", "PENDING_PAYMENT", "RESCHEDULED"])
        )
        existing = (await db.execute(existing_stmt)).scalar_one_or_none()
        if existing:
            return {"success": True, "appointment_id": existing.id, "payment_mode": payment_mode, "idempotent": True}

    # Verify doctor slot availability to prevent double-booking
    slot_conflict_stmt = select(Appointment).where(
        Appointment.doctor_id == req.doctor_id,
        Appointment.appointment_datetime == req.appointment_datetime,
        Appointment.status.in_(["SCHEDULED", "CONFIRMED", "PENDING_PAYMENT", "RESCHEDULED", "IN_CONSULTATION"])
    )
    existing_slot = (await db.execute(slot_conflict_stmt)).scalars().first()
    if existing_slot:
        raise HTTPException(
            status_code=400,
            detail="The selected time slot for this doctor is already booked. Please choose another slot."
        )

    try:
        if not patient:
            dob = None
            if req.patient_dob:
                try:
                    dob = datetime.strptime(req.patient_dob, "%Y-%m-%d").date()
                except Exception:
                    dob = datetime.now().date()
            else:
                dob = datetime.now().date()

            patient = Patient(
                id=str(uuid.uuid4()),
                hospital_id=hosp_id,
                first_name=p_first,
                last_name=p_last,
                phone=clean_phone,
                gender=req.patient_gender,
                date_of_birth=dob,
                is_active=True
            )
            db.add(patient)
            await db.flush()

        if payment_mode == "CASH":
            appt_status = "SCHEDULED"
            pay_status = "PAID"
        else:
            appt_status = "PENDING_PAYMENT"
            pay_status = "PENDING"

        appt = Appointment(
            id=str(uuid.uuid4()),
            hospital_id=hosp_id,
            patient_id=patient.id,
            doctor_id=req.doctor_id,
            appointment_datetime=req.appointment_datetime,
            duration_minutes=30,
            status=appt_status,
            payment_status=pay_status,
            payment_method=payment_mode,
            consultation_status="SCHEDULED",
            reason=req.reason or "Walk-in Booking",
            source="RECEPTIONIST_PORTAL",
            booked_by_name=f"{current_user.first_name} {current_user.last_name}".strip() if current_user and hasattr(current_user, 'first_name') and current_user.first_name else None
        )
        db.add(appt)
        await db.flush()
        await db.commit()
    except IntegrityError as ie:
        await db.rollback()
        logger.warning(f"Double-booking prevented by unique constraint in receptionist booking: {ie}")
        raise HTTPException(
            status_code=400,
            detail="The selected time slot for this doctor is already booked. Please choose another slot."
        )
    except Exception as e:
        await db.rollback()
        logger.error(f"Error during receptionist booking database transaction: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Booking failed due to database transaction error: {str(e)}")

    try:
        wa_service = WhatsAppNotificationService()
        doc_stmt = select(Doctor).where(Doctor.id == req.doctor_id)
        doctor = (await db.execute(doc_stmt)).scalar_one_or_none()
        hosp_stmt = select(Hospital).where(Hospital.id == hosp_id)
        hospital = (await db.execute(hosp_stmt)).scalar_one_or_none()

        if doctor and hospital:
            wa_details = {
                "hospital_id": hospital.id,
                "hospital_name": hospital.name,
                "appointment_id": appt.id,
                "patient_name": f"{patient.first_name} {patient.last_name}".strip(),
                "patient_phone": patient.phone,
                "doctor_name": f"{doctor.first_name} {doctor.last_name}".strip(),
                "appointment_datetime": appt.appointment_datetime.isoformat(),
                "reason": appt.reason or "",
                "fees": doctor.opd_fees or 500
            }
            if payment_mode == "CASH":
                asyncio.create_task(wa_service.send_cash_booking_confirmation(wa_details))
            else:
                asyncio.create_task(wa_service.send_patient_confirmation(wa_details))
    except Exception as wa_err:
        logger.error(f"WhatsApp notification failed in receptionist booking: {wa_err}")

    return {
        "success": True,
        "appointment_id": appt.id,
        "payment_status": pay_status,
        "payment_mode": payment_mode,
        "message": f"Appointment booked successfully with {payment_mode} payment."
    }


@router.get("/receptionist/schedule", response_class=HTMLResponse, tags=["receptionist"])
async def receptionist_today_schedule(
    date_str: Optional[str] = Query(None, description="Date in YYYY-MM-DD format. Defaults to today."),
    hospital_id: Optional[str] = Query(None, description="Hospital ID (defaults to authenticated user's hospital)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Human receptionist dashboard — shows all appointments for a given date organized by doctor.
    Protected: Requires authenticated staff (RECEPTIONIST, ADMIN, DOCTOR) or SUPER_ADMIN.
    Enforces tenant isolation: staff cannot view appointments of other hospitals.
    """
    # 1. Enforce RBAC
    role_stmt = select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == current_user.id)
    roles = set((await db.execute(role_stmt)).scalars().all())

    is_super_admin = "SUPER_ADMIN" in roles or current_user.hospital_id == "super_admin"
    is_staff = bool(roles.intersection({"RECEPTIONIST", "ADMIN", "DOCTOR"}))

    if not is_super_admin and not is_staff:
        raise HTTPException(
            status_code=403,
            detail="Unauthorized: Only hospital staff (Receptionist, Admin, Doctor) or SuperAdmin can view schedule."
        )

    # 2. Resolve target hospital with tenant boundary check
    target_hospital_id = hospital_id or current_user.hospital_id or "hosp_default"

    if not is_super_admin and target_hospital_id != current_user.hospital_id:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Cannot view schedule of another hospital."
        )

    hospital_id = target_hospital_id

    await auto_update_missed_appointments(db)

    if date_str:
        try:
            target_date = date.fromisoformat(date_str)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
    else:
        target_date = date.today()

    start_dt = datetime.combine(target_date, datetime.min.time())
    end_dt = datetime.combine(target_date, datetime.max.time())

    appt_stmt = (
        select(Appointment, Patient, Doctor, Department)
        .join(Patient, Appointment.patient_id == Patient.id)
        .join(Doctor, Appointment.doctor_id == Doctor.id)
        .join(Department, Doctor.department_id == Department.id)
        .where(
            and_(
                Appointment.hospital_id == hospital_id,
                Appointment.appointment_datetime >= start_dt,
                Appointment.appointment_datetime <= end_dt,
                Appointment.status.in_(["SCHEDULED", "PENDING_PAYMENT", "COMPLETED", "CANCELLED", "MISSED", "RESCHEDULED"])
            )
        )
        .order_by(Doctor.first_name, Appointment.appointment_datetime)
    )
    results = (await db.execute(appt_stmt)).all()

    hosp_stmt = select(Hospital).where(Hospital.id == hospital_id)
    hospital_obj = (await db.execute(hosp_stmt)).scalar_one_or_none()
    hosp_name = hospital_obj.name if hospital_obj else "CP Tiwari Hospital"

    docs_stmt = (
        select(Doctor, Department)
        .join(Department, Doctor.department_id == Department.id)
        .where(Doctor.hospital_id == hospital_id, Doctor.is_active == True)
    )
    doctors_db = (await db.execute(docs_stmt)).all()
    
    scheduler = SchedulingEngine(db)
    doctors_info = []
    
    for doc, dept in doctors_db:
        free_slots = await scheduler.get_available_slots(doc.id, target_date)
        fees = f"₹{doc.opd_fees}" if (doc.opd_fees is not None) else "₹500"
        
        from app.database.models.appointment import DoctorSchedule
        sched_stmt = select(DoctorSchedule).where(DoctorSchedule.doctor_id == doc.id)
        doc_schedules = (await db.execute(sched_stmt)).scalars().all()
        if doc_schedules:
            day_to_ranges = defaultdict(list)
            for s in doc_schedules:
                tr = f"{s.start_time.strftime('%I:%M %p').lstrip('0')} - {s.end_time.strftime('%I:%M %p').lstrip('0')}"
                if tr not in day_to_ranges[s.day_of_week]:
                    day_to_ranges[s.day_of_week].append(tr)
            
            times_tuple_to_days = defaultdict(list)
            for day, ranges in day_to_ranges.items():
                times_tuple = tuple(ranges)
                times_tuple_to_days[times_tuple].append(day)
            
            parts = []
            day_names_map = {1: "सोम", 2: "मंगल", 3: "बुध", 4: "गुरु", 5: "शुक्र", 6: "शनि", 7: "रवि"}
            for times_tuple, days_list in times_tuple_to_days.items():
                days_list.sort()
                if len(days_list) >= 5 and days_list == list(range(days_list[0], days_list[0] + len(days_list))):
                    days_str = f"{day_names_map.get(days_list[0])}–{day_names_map.get(days_list[-1])}"
                else:
                    days_str = ", ".join([day_names_map.get(d, str(d)) for d in days_list])
                time_slots_str = ", ".join(times_tuple)
                parts.append(f"{days_str} ({time_slots_str})")
            
            timing_str = " | ".join(parts)
        else:
            timing_str = "सोम–शुक्र (10:00 AM - 1:00 PM, 2:00 PM - 5:00 PM)"
        
        doctors_info.append({
            "name": f"Dr. {doc.first_name} {doc.last_name}",
            "dept": dept.name,
            "fees": fees,
            "timings": timing_str,
            "free_slots_count": len(free_slots)
        })

    by_doctor: dict = defaultdict(list)
    for appt, patient, doctor, dept in results:
        from app.database.models.appointment import PatientIntake
        intake_stmt = select(PatientIntake).where(PatientIntake.appointment_id == appt.id)
        intake_obj = (await db.execute(intake_stmt)).scalar_one_or_none()
        intake_html_parts = []
        if intake_obj:
            if intake_obj.has_visited_before is not None:
                intake_html_parts.append(f"🔁 पहले दिखाया: {'हाँ — ' + (intake_obj.previous_doctor or '') if intake_obj.has_visited_before else 'नहीं'}")
            if intake_obj.has_reports is not None:
                intake_html_parts.append(f"📄 Reports: {'हाँ — ' + (intake_obj.report_details or '') if intake_obj.has_reports else 'नहीं'}")
            if intake_obj.current_medicines:
                intake_html_parts.append(f"💊 दवाइयाँ: {intake_obj.current_medicines}")
            if intake_obj.additional_notes:
                intake_html_parts.append(f"📝 नोट: {intake_obj.additional_notes}")

        key = (f"Dr. {doctor.first_name} {doctor.last_name}", dept.name)
        by_doctor[key].append({
            "appointment_id": appt.id,
            "doctor_id": doctor.id,
            "time": appt.appointment_datetime.strftime("%I:%M %p"),
            "time_24": appt.appointment_datetime.strftime("%H:%M"),
            "appointment_datetime_iso": appt.appointment_datetime.isoformat(),
            "patient_name": f"{patient.first_name} {patient.last_name}".strip(),
            "patient_phone": patient.phone,
            "reason": appt.reason or "—",
            "status": appt.status,
            "intake_html": "<br>".join(intake_html_parts) if intake_html_parts else "",
        })

    day_display = target_date.strftime("%d %B %Y")
    day_name = target_date.strftime("%A")
    prev_date = (target_date - timedelta(days=1)).isoformat()
    next_date = (target_date + timedelta(days=1)).isoformat()
    total = len(results)
    confirmed = sum(1 for appt, *_ in results if appt.status == "SCHEDULED")
    pending = total - confirmed
    is_today = (target_date == date.today())
    now_str = datetime.now().strftime("%I:%M:%S %p")

    from app.templates.receptionist_schedule_template import render_receptionist_schedule_html

    html = render_receptionist_schedule_html(
        target_date=target_date,
        day_display=day_display,
        day_name=day_name,
        prev_date=prev_date,
        next_date=next_date,
        total=total,
        confirmed=confirmed,
        pending=pending,
        is_today=is_today,
        now_str=now_str,
        hosp_name=hosp_name,
        hospital_id=hospital_id,
        doctors_info=doctors_info,
        by_doctor=by_doctor
    )
    return HTMLResponse(content=html)
