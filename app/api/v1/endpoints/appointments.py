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
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.core.dependencies import get_current_user
from app.core.config import settings
from app.core.logging import logger
from app.database.models.call_log import User
from app.database.models.appointment import Doctor, Patient, Hospital, Department, Appointment, ConsultationNote
from app.engines.appointment import AppointmentEngine
from app.engines.scheduling import SchedulingEngine
from app.schemas.appointment import (
    AppointmentCreate, AppointmentRead, AvailableSlotsResponse
)
from app.services.whatsapp import WhatsAppNotificationService

router = APIRouter(tags=["appointments"])


async def auto_update_missed_appointments(db: AsyncSession):
    """
    Sweeper that auto-marks expired appointments as MISSED and dispatches WhatsApp notifications:
    - Any appointment (Paid or Unpaid) whose appointment_datetime has passed and is not COMPLETED/CANCELLED/MISSED is marked MISSED.
    - Sends WhatsApp missed notification for each newly marked missed appointment.
    """
    try:
        now = datetime.now()
        start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        stmt = select(Appointment).where(
            and_(
                Appointment.appointment_datetime < start_of_today,
                Appointment.status.in_(["SCHEDULED", "CONFIRMED", "PENDING_PAYMENT", "RESCHEDULED"])
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
    hospital_id: str = Query("hosp_default"),
    db: AsyncSession = Depends(get_db)
):
    """
    Human receptionist dashboard — shows all appointments for a given date organized by doctor.
    No authentication required. Auto-refreshes every 30 seconds.
    """
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
        .where(Doctor.is_active == True)
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

    dept_icons = {
        "Orthopedics": "🦴", "Cardiology": "❤️", "Ophthalmology": "👁️",
        "Heart": "❤️", "Eye": "👁️", "Haddi": "🦴",
    }

    doctor_sections = ""
    if not by_doctor:
        doctor_sections = """
        <div class="empty-card">
            <div class="empty-icon">📅</div>
            <h3>इस दिन कोई अपॉइंटमेंट नहीं है</h3>
            <p>अभी तक कोई बुकिंग नहीं आई है। जैसे ही AI Receptionist call लेगी, यहाँ दिखेगी।</p>
        </div>"""
    else:
        for (doc_name, dept_name), appts in by_doctor.items():
            icon = next((v for k, v in dept_icons.items() if k.lower() in dept_name.lower()), "👨‍⚕️")
            rows = ""
            for i, a in enumerate(appts, 1):
                appt_id = a['appointment_id']
                status = a['status']
                badge_map = {
                    'SCHEDULED': '<span class="badge confirmed">✅ Confirmed</span>',
                    'PENDING_PAYMENT': '<span class="badge pending-pay">⏳ Payment Pending</span>',
                    'COMPLETED': '<span class="badge completed">🎉 Completed</span>',
                    'CANCELLED': '<span class="badge cancelled">❌ Cancelled</span>',
                    'MISSED': '<span class="badge missed">🚫 Missed</span>',
                    'RESCHEDULED': '<span class="badge rescheduled">📅 Rescheduled</span>',
                }
                badge = badge_map.get(status, f'<span class="badge">{status}</span>')

                action_btns = ""
                if status in ["SCHEDULED", "PENDING_PAYMENT", "RESCHEDULED"]:
                    reschedule_btn = f"""<button class="act-btn blue" onclick="openReschedule('{appt_id}', '{a["doctor_id"]}', '{status}')">📅 Reschedule</button>""" if status != "PENDING_PAYMENT" else ""
                    
                    action_btns = f"""
                    <div class="action-btns" id="actions-{appt_id}">
                        <button class="act-btn green" onclick="updateStatus('{appt_id}', 'COMPLETED', '{status}')">✅ Completed</button>
                        <button class="act-btn red" onclick="updateStatus('{appt_id}', 'CANCELLED', '{status}')">❌ Cancel</button>
                        <button class="act-btn orange" onclick="updateStatus('{appt_id}', 'MISSED', '{status}')">🚫 Missed</button>
                        {reschedule_btn}
                    </div>"""

                intake_panel = ""
                if a.get('intake_html'):
                    intake_panel = f"""<div class="intake-panel"><span class="intake-label">🩺 AI Intake:</span> {a['intake_html']}</div>"""

                rows += f"""
                <tr class="appt-row" id="row-{appt_id}">
                    <td class="td-sno">{i}</td>
                    <td class="td-time">
                        <span class="time-pill">{a["time"]}</span>
                    </td>
                    <td class="td-patient">
                        <div class="patient-name">{a["patient_name"]}</div>
                        {intake_panel}
                    </td>
                    <td class="td-phone">
                        <a href="tel:{a["patient_phone"]}" class="phone-link">📞 {a["patient_phone"]}</a>
                    </td>
                    <td class="td-reason">{a["reason"]}</td>
                    <td class="td-status">
                        <div id="badge-{appt_id}">{badge}</div>
                        {action_btns}
                    </td>
                </tr>"""
            doctor_sections += f"""
            <div class="doctor-card">
                <div class="doctor-header">
                    <div class="doctor-left">
                        <div class="doc-icon">{icon}</div>
                        <div class="doc-details">
                            <div class="doc-name">{doc_name}</div>
                            <div class="doc-dept">{dept_name}</div>
                        </div>
                    </div>
                    <div class="doc-right">
                        <div class="doc-count">{len(appts)}</div>
                        <div class="doc-count-label">अपॉइंटमेंट</div>
                    </div>
                </div>
                <div class="table-wrap">
                    <table>
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>⏰ समय</th>
                                <th>👤 मरीज़ का नाम</th>
                                <th>📞 मोबाइल</th>
                                <th>🩺 समस्या</th>
                                <th>स्थिति / कार्रवाई</th>
                            </tr>
                        </thead>
                        <tbody>{rows}</tbody>
                    </table>
                </div>
            </div>"""

    sidebar_html = ""
    for d in doctors_info:
        badge_class = "slots-badge" if d["free_slots_count"] > 0 else "slots-badge empty"
        badge_text = f"{d['free_slots_count']} slots free" if d["free_slots_count"] > 0 else "Full / Closed"
        sidebar_html += f"""
        <div class="sidebar-doc-item">
            <div class="sidebar-doc-name">{d["name"]}</div>
            <div class="sidebar-doc-dept">{d["dept"]}</div>
            <div class="sidebar-doc-detail">
                <span>⏰ Timing:</span>
                <span>{d["timings"].replace("Timing:", "").strip()}</span>
            </div>
            <div class="sidebar-doc-detail">
                <span>💰 OPD Fees:</span>
                <span>{d["fees"]}</span>
            </div>
            <div class="sidebar-doc-detail" style="margin-top: 8px;">
                <span>📅 Slots status:</span>
                <span class="{badge_class}">{badge_text}</span>
            </div>
        </div>"""

    today_flag = '<span class="today-badge">आज</span>' if is_today else ""

    html = f"""<!DOCTYPE html>
<html lang="hi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{hosp_name} — रिसेप्शनिस्ट डैशबोर्ड</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {{
            --primary: #1a4fa0;
            --primary-dark: #0f3276;
            --primary-light: #dbeafe;
            --accent: #0ea5e9;
            --green: #16a34a;
            --green-bg: #dcfce7;
            --yellow: #b45309;
            --yellow-bg: #fef9c3;
            --bg: #f0f5fc;
            --card-bg: #ffffff;
            --text: #0f172a;
            --text-muted: #64748b;
            --border: #e2e8f0;
            --shadow: 0 4px 20px rgba(26,79,160,0.10);
            --radius: 16px;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Inter', system-ui, sans-serif;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
        }}
        .header {{
            background: linear-gradient(135deg, #0f3276 0%, #1a4fa0 50%, #1e6cc4 100%);
            padding: 0;
            box-shadow: 0 4px 24px rgba(15,50,118,0.35);
        }}
        .header-inner {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 18px 28px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
            flex-wrap: wrap;
        }}
        .header-brand {{
            display: flex;
            align-items: center;
            gap: 14px;
        }}
        .header-logo {{
            width: 52px;
            height: 52px;
            background: rgba(255,255,255,0.15);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 26px;
            border: 1px solid rgba(255,255,255,0.25);
        }}
        .header-title {{ color: white; }}
        .header-title h1 {{ font-size: 20px; font-weight: 800; letter-spacing: -0.3px; }}
        .header-title p {{ font-size: 12px; color: rgba(255,255,255,0.75); margin-top: 2px; }}
        .header-right {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .live-clock {{
            background: rgba(255,255,255,0.12);
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 10px;
            padding: 8px 16px;
            color: white;
            font-size: 15px;
            font-weight: 600;
            font-variant-numeric: tabular-nums;
            min-width: 100px;
            text-align: center;
        }}
        .refresh-btn {{
            background: rgba(255,255,255,0.15);
            border: 1px solid rgba(255,255,255,0.3);
            color: white;
            padding: 8px 16px;
            border-radius: 10px;
            font-size: 13px;
            font-weight: 600;
            text-decoration: none;
            cursor: pointer;
            transition: background 0.2s;
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        .refresh-btn:hover {{ background: rgba(255,255,255,0.28); }}
        .date-bar {{
            background: white;
            border-bottom: 1px solid var(--border);
        }}
        .date-bar-inner {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 14px 28px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 12px;
        }}
        .date-info {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .date-text {{
            font-size: 17px;
            font-weight: 700;
            color: var(--primary-dark);
        }}
        .day-text {{
            font-size: 13px;
            color: var(--text-muted);
            font-weight: 500;
        }}
        .today-badge {{
            background: var(--primary);
            color: white;
            padding: 3px 10px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 700;
        }}
        .date-nav {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .date-nav a {{
            padding: 7px 14px;
            border: 1.5px solid var(--border);
            border-radius: 8px;
            text-decoration: none;
            color: var(--text-muted);
            font-size: 13px;
            font-weight: 600;
            transition: all 0.15s;
        }}
        .date-nav a:hover {{ background: var(--primary-light); border-color: var(--accent); color: var(--primary); }}
        .date-nav a.today-btn {{ background: var(--primary); color: white; border-color: var(--primary); }}
        .date-nav a.today-btn:hover {{ background: var(--primary-dark); }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 24px 28px;
        }}
        .dashboard-layout {{
            display: grid;
            grid-template-columns: 2.2fr 1fr;
            gap: 24px;
            align-items: start;
        }}
        @media (max-width: 950px) {{
            .dashboard-layout {{
                grid-template-columns: 1fr;
            }}
        }}
        .stats-row {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 16px;
            margin-bottom: 24px;
        }}
        .stat-card {{
            background: white;
            border-radius: var(--radius);
            padding: 20px 24px;
            box-shadow: var(--shadow);
            display: flex;
            align-items: center;
            gap: 16px;
        }}
        .stat-icon {{
            width: 48px;
            height: 48px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 22px;
            flex-shrink: 0;
        }}
        .stat-icon.blue {{ background: var(--primary-light); }}
        .stat-icon.green {{ background: var(--green-bg); }}
        .stat-icon.yellow {{ background: var(--yellow-bg); }}
        .stat-value {{ font-size: 28px; font-weight: 800; color: var(--text); line-height: 1; }}
        .stat-label {{ font-size: 12px; color: var(--text-muted); font-weight: 500; margin-top: 4px; }}
        .doctor-card {{
            background: var(--card-bg);
            border-radius: var(--radius);
            margin-bottom: 20px;
            box-shadow: var(--shadow);
            overflow: hidden;
            border: 1px solid var(--border);
        }}
        .doctor-header {{
            padding: 18px 24px;
            background: linear-gradient(135deg, #eff6ff 0%, #e0f2fe 100%);
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #bfdbfe;
        }}
        .doctor-left {{
            display: flex;
            align-items: center;
            gap: 14px;
        }}
        .doc-icon {{
            width: 44px;
            height: 44px;
            background: white;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 22px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }}
        .doc-name {{ font-size: 17px; font-weight: 700; color: var(--primary-dark); }}
        .doc-dept {{
            display: inline-block;
            margin-top: 4px;
            background: var(--primary);
            color: white;
            padding: 2px 10px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 600;
        }}
        .doc-right {{ text-align: center; }}
        .doc-count {{ font-size: 28px; font-weight: 800; color: var(--primary); }}
        .doc-count-label {{ font-size: 11px; color: var(--text-muted); font-weight: 500; }}
        .sidebar-card {{
            background: white;
            border-radius: var(--radius);
            padding: 24px;
            box-shadow: var(--shadow);
            border: 1px solid var(--border);
            position: sticky;
            top: 24px;
        }}
        .sidebar-title {{
            font-size: 16px;
            font-weight: 800;
            color: var(--primary-dark);
            margin-bottom: 18px;
            display: flex;
            align-items: center;
            gap: 8px;
            border-bottom: 2px solid var(--primary-light);
            padding-bottom: 10px;
        }}
        .sidebar-doc-item {{
            padding: 16px 0;
            border-bottom: 1px dashed var(--border);
        }}
        .sidebar-doc-item:last-child {{
            border-bottom: none;
            padding-bottom: 0;
        }}
        .sidebar-doc-item:first-child {{
            padding-top: 0;
        }}
        .sidebar-doc-name {{
            font-size: 15px;
            font-weight: 700;
            color: var(--text);
        }}
        .sidebar-doc-dept {{
            font-size: 10px;
            font-weight: 700;
            background: var(--primary-light);
            color: var(--primary-dark);
            padding: 2px 8px;
            border-radius: 12px;
            display: inline-block;
            margin-top: 4px;
            text-transform: uppercase;
        }}
        .sidebar-doc-detail {{
            font-size: 12px;
            color: var(--text-muted);
            margin-top: 8px;
            display: flex;
            justify-content: space-between;
            font-weight: 500;
        }}
        .slots-badge {{
            background: var(--green-bg);
            color: var(--green);
            padding: 2px 8px;
            border-radius: 6px;
            font-weight: 700;
            font-size: 11px;
        }}
        .slots-badge.empty {{
            background: #fee2e2;
            color: #ef4444;
        }}
        .table-wrap {{ overflow-x: auto; }}
        table {{ width: 100%; border-collapse: collapse; }}
        thead tr {{ background: #f8fafc; }}
        th {{
            padding: 11px 16px;
            text-align: left;
            font-size: 11px;
            font-weight: 700;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.06em;
            border-bottom: 1.5px solid var(--border);
            white-space: nowrap;
        }}
        td {{
            padding: 13px 16px;
            border-bottom: 1px solid #f1f5f9;
            font-size: 14px;
            vertical-align: middle;
        }}
        .appt-row:last-child td {{ border-bottom: none; }}
        .appt-row:hover {{ background: #f8fafc; }}
        .td-sno {{ color: #cbd5e1; font-weight: 700; font-size: 13px; width: 36px; }}
        .time-pill {{
            background: var(--primary-light);
            color: var(--primary-dark);
            padding: 5px 12px;
            border-radius: 20px;
            font-weight: 700;
            font-size: 13px;
            white-space: nowrap;
            display: inline-block;
        }}
        .patient-name {{ font-weight: 600; color: var(--text); font-size: 14px; }}
        .phone-link {{ color: var(--text-muted); text-decoration: none; font-size: 13px; white-space: nowrap; }}
        .phone-link:hover {{ color: var(--primary); }}
        .td-reason {{ color: var(--text-muted); font-size: 13px; max-width: 180px; }}
        .badge {{
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 700;
            white-space: nowrap;
            display: inline-block;
        }}
        .badge.confirmed {{ background: var(--green-bg); color: var(--green); }}
        .badge.pending-pay {{ background: var(--yellow-bg); color: var(--yellow); }}
        .empty-card {{
            background: white;
            border-radius: var(--radius);
            padding: 60px 20px;
            text-align: center;
            box-shadow: var(--shadow);
            border: 1px solid var(--border);
        }}
        .empty-icon {{ font-size: 52px; margin-bottom: 16px; }}
        .empty-card h3 {{ font-size: 18px; font-weight: 700; color: var(--text); margin-bottom: 8px; }}
        .empty-card p {{ font-size: 14px; color: var(--text-muted); max-width: 360px; margin: 0 auto; }}
        .footer {{
            text-align: center;
            color: #94a3b8;
            font-size: 12px;
            padding: 20px;
        }}
        @media (max-width: 700px) {{
            .header-inner, .date-bar-inner, .container {{ padding: 14px 16px; }}
            .stats-row {{ grid-template-columns: 1fr; }}
            th, td {{ padding: 10px 12px; }}
            .header-title h1 {{ font-size: 16px; }}
            .date-text {{ font-size: 14px; }}
        }}
        @media (max-width: 480px) {{
            .stats-row {{ grid-template-columns: 1fr 1fr; }}
            .stat-card:first-child {{ grid-column: span 2; }}
        }}
        .action-btns {{
            display: flex;
            flex-wrap: wrap;
            gap: 5px;
            margin-top: 8px;
        }}
        .act-btn {{
            padding: 4px 9px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 700;
            border: none;
            cursor: pointer;
            transition: all 0.15s;
            white-space: nowrap;
        }}
        .act-btn.green {{ background: #dcfce7; color: #15803d; }}
        .act-btn.green:hover {{ background: #bbf7d0; }}
        .act-btn.red {{ background: #fee2e2; color: #b91c1c; }}
        .act-btn.red:hover {{ background: #fecaca; }}
        .act-btn.orange {{ background: #fff7ed; color: #c2410c; }}
        .act-btn.orange:hover {{ background: #fed7aa; }}
        .act-btn.blue {{ background: #dbeafe; color: #1d4ed8; }}
        .act-btn.blue:hover {{ background: #bfdbfe; }}
        .badge.completed {{ background: #dcfce7; color: #15803d; }}
        .badge.cancelled {{ background: #fee2e2; color: #b91c1c; }}
        .badge.missed {{ background: #fef3c7; color: #92400e; }}
        .badge.rescheduled {{ background: #ede9fe; color: #6d28d9; }}
        .intake-panel {{
            margin-top: 6px;
            background: #f0f9ff;
            border: 1px solid #bae6fd;
            border-radius: 7px;
            padding: 6px 10px;
            font-size: 11.5px;
            color: #0369a1;
            line-height: 1.6;
        }}
        .intake-label {{
            font-weight: 700;
            display: block;
            margin-bottom: 2px;
        }}
        .modal-overlay {{
            display: none;
            position: fixed;
            inset: 0;
            background: rgba(15,50,118,0.45);
            z-index: 9000;
            align-items: center;
            justify-content: center;
        }}
        .modal-overlay.open {{ display: flex; }}
        .modal-box {{
            background: white;
            border-radius: 18px;
            padding: 32px;
            max-width: 460px;
            width: 95%;
            box-shadow: 0 20px 60px rgba(15,50,118,0.25);
        }}
        .modal-title {{ font-size: 18px; font-weight: 800; color: var(--primary-dark); margin-bottom: 20px; }}
        .modal-label {{ font-size: 13px; font-weight: 600; color: var(--text-muted); margin-bottom: 6px; }}
        .modal-input {{
            width: 100%;
            padding: 10px 14px;
            border: 1.5px solid var(--border);
            border-radius: 9px;
            font-size: 14px;
            margin-bottom: 16px;
            font-family: inherit;
        }}
        .modal-input:focus {{ outline: none; border-color: var(--primary); }}
        .modal-actions {{ display: flex; gap: 10px; justify-content: flex-end; margin-top: 8px; }}
        .modal-btn {{
            padding: 10px 20px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 700;
            border: none;
            cursor: pointer;
            transition: background 0.15s;
        }}
        .modal-btn.confirm {{ background: var(--primary); color: white; }}
        .modal-btn.confirm:hover {{ background: var(--primary-dark); }}
        .modal-btn.cancel {{ background: #f1f5f9; color: var(--text-muted); }}
        .modal-btn.cancel:hover {{ background: #e2e8f0; }}
    </style>
</head>
<body>

    <div class="header">
        <div class="header-inner">
            <div class="header-brand">
                <div class="header-logo">🏥</div>
                <div class="header-title">
                    <h1>{hosp_name}</h1>
                    <p>रिसेप्शनिस्ट डैशबोर्ड — AI Voice Booking System</p>
                </div>
            </div>
            <div class="header-right">
                <div class="live-clock" id="clock">{now_str}</div>
                <a class="refresh-btn" href="/receptionist/schedule?hospital_id={hospital_id}">
                    🔄 Refresh
                </a>
            </div>
        </div>
    </div>

    <div class="date-bar">
        <div class="date-bar-inner">
            <div class="date-info">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <div class="header-logo" style="width: 40px; height: 40px; font-size: 20px; background: var(--primary-light); color: var(--primary); cursor: pointer; border: 1.5px solid var(--border); display: flex; align-items: center; justify-content: center; border-radius: 10px;" onclick="document.getElementById('date-select').showPicker()">📅</div>
                    <div>
                        <div class="date-text" style="display: flex; align-items: center; gap: 6px; cursor: pointer; color: var(--primary-dark); font-weight: 700; font-size: 17px;" onclick="document.getElementById('date-select').showPicker()">
                            {day_display} {today_flag}
                            <span style="font-size: 11px; color: var(--accent); vertical-align: middle;">▼</span>
                        </div>
                        <div class="day-text">{day_name}</div>
                    </div>
                    <input type="date" id="date-select" value="{target_date.isoformat()}" 
                           style="opacity: 0; width: 0; height: 0; position: absolute;"
                           onchange="window.location.href='/receptionist/schedule?hospital_id={hospital_id}&date_str=' + this.value">
                </div>
            </div>
            <div class="date-nav">
                <a href="/receptionist/schedule?date_str={prev_date}&hospital_id={hospital_id}">◀ पिछला</a>
                <a href="/receptionist/schedule?hospital_id={hospital_id}" class="today-btn">आज</a>
                <a href="/receptionist/schedule?date_str={next_date}&hospital_id={hospital_id}">अगला ▶</a>
            </div>
        </div>
    </div>

    <div class="container">

        <div class="stats-row">
            <div class="stat-card">
                <div class="stat-icon blue">📋</div>
                <div>
                    <div class="stat-value">{total}</div>
                    <div class="stat-label">कुल अपॉइंटमेंट</div>
                </div>
            </div>
            <div class="stat-card">
                <div class="stat-icon green">✅</div>
                <div>
                    <div class="stat-value">{confirmed}</div>
                    <div class="stat-label">Confirmed</div>
                </div>
            </div>
            <div class="stat-card">
                <div class="stat-icon yellow">⏳</div>
                <div>
                    <div class="stat-value">{pending}</div>
                    <div class="stat-label">Payment Pending</div>
                </div>
            </div>
        </div>

        <div class="dashboard-layout">
            <div class="main-content">
                {doctor_sections}
            </div>

            <div class="sidebar-content">
                <div class="sidebar-card">
                    <div class="sidebar-title">
                        <span>👨‍⚕️</span> डॉक्टर, समय एवं फीस सूची
                    </div>
                    <div class="sidebar-list">
                        {sidebar_html}
                    </div>
                </div>
            </div>
        </div>

        <div class="footer">
            अंतिम अपडेट: {datetime.now().strftime("%d %b %Y, %I:%M:%S %p")}
        </div>
    </div>

    <div class="modal-overlay" id="rescheduleModal">
        <div class="modal-box">
            <div class="modal-title">📅 Appointment Reschedule करें</div>
            <input type="hidden" id="modal-appt-id">
            <input type="hidden" id="modal-doctor-id">
            <label class="modal-label">नई Date और Time:</label>
            <input type="datetime-local" class="modal-input" id="modal-new-datetime" onchange="fetchBusySlots()">
            
            <div id="busy-slots-container" style="display:none; margin-bottom: 16px;">
                <label class="modal-label" style="color: #b91c1c; display: flex; align-items: center; gap: 4px;">
                    🚫 व्यस्त स्लॉट्स (Already Booked Times):
                </label>
                <div id="busy-slots-list" style="display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px;"></div>
            </div>

            <label class="modal-label">मरीज़ के लिए पहुँचने की Cutoff Note (optional):</label>
            <input type="text" class="modal-input" id="modal-cutoff" placeholder="जैसे: कृपया 10 बजे तक पहुँचें">
            <div class="modal-actions">
                <button class="modal-btn cancel" onclick="closeReschedule()">रद्द करें</button>
                <button class="modal-btn confirm" onclick="confirmReschedule()">📅 Reschedule करें</button>
            </div>
        </div>
    </div>

    <script>
        function updateClock() {{
            const now = new Date();
            const h = String(now.getHours() % 12 || 12).padStart(2, '0');
            const m = String(now.getMinutes()).padStart(2, '0');
            const s = String(now.getSeconds()).padStart(2, '0');
            const ampm = now.getHours() >= 12 ? 'PM' : 'AM';
            document.getElementById('clock').textContent = h + ':' + m + ':' + s + ' ' + ampm;
        }}
        setInterval(updateClock, 1000);
        updateClock();

        async function updateStatus(apptId, newStatus, currentStatus) {{
            const label = {{COMPLETED: 'Completed ✅', CANCELLED: 'Cancelled ❌', MISSED: 'Missed 🚫'}}[newStatus] || newStatus;
            
            let cancelReason = null;
            if (newStatus === 'CANCELLED' && currentStatus === 'SCHEDULED') {{
                cancelReason = prompt("इस Paid Appointment को निरस्त करने का कारण (Reason) दर्ज करें (यह मरीज़ को WhatsApp रिफंड सूचना के साथ भेजा जाएगा):");
                if (cancelReason === null) return;
                if (!cancelReason.trim()) cancelReason = "अस्पताल के अनुरोध पर";
            }}

            if (!confirm(`क्या आप इस appointment को "${{label}}" mark करना चाहते हैं?`)) return;

            const formData = new FormData();
            formData.append('new_status', newStatus);
            if (cancelReason) {{
                formData.append('cancellation_reason', cancelReason);
            }}

            try {{
                const res = await fetch(`/appointments/${{apptId}}/status`, {{
                    method: 'POST',
                    body: formData
                }});
                const data = await res.json();
                if (data.success) {{
                    const badgeMap = {{
                        COMPLETED: '<span class="badge completed">🎉 Completed</span>',
                        CANCELLED: '<span class="badge cancelled">❌ Cancelled</span>',
                        MISSED: '<span class="badge missed">🚫 Missed</span>',
                    }};
                    document.getElementById(`badge-${{apptId}}`).innerHTML = badgeMap[newStatus] || newStatus;
                    const actionsDiv = document.getElementById(`actions-${{apptId}}`);
                    if (actionsDiv) actionsDiv.remove();
                    if (newStatus === 'CANCELLED' && currentStatus === 'SCHEDULED') {{
                        alert('✅ Appointment निरस्त कर दी गई है और मरीज़ को रिफंड की सूचना WhatsApp कर दी गई है।');
                    }}
                }} else {{
                    alert('कुछ गड़बड़ हो गई। दोबारा कोशिश करें।');
                }}
            }} catch (e) {{
                alert('Network error. Please try again.');
            }}
        }}

        function openReschedule(apptId, doctorId, currentStatus) {{
            if (currentStatus === 'PENDING_PAYMENT') {{
                alert('❌ भुगतान अपूर्ण है (Payment Pending)। रीशेड्यूल केवल भुगतान पूरा होने के बाद ही संभव है।');
                return;
            }}

            document.getElementById('modal-appt-id').value = apptId;
            document.getElementById('modal-doctor-id').value = doctorId;
            
            const dtInput = document.getElementById('modal-new-datetime');
            dtInput.value = '';
            
            const now = new Date();
            const tzOffset = now.getTimezoneOffset() * 60000;
            const minDt = new Date(now.getTime() - tzOffset).toISOString().slice(0, 16);
            const maxDate = new Date(now.getTime() + 2 * 24 * 60 * 60 * 1000);
            const maxDt = new Date(maxDate.getTime() - tzOffset).toISOString().slice(0, 16);
            
            dtInput.min = minDt;
            dtInput.max = maxDt;
            
            document.getElementById('modal-cutoff').value = '';
            document.getElementById('busy-slots-container').style.display = 'none';
            document.getElementById('busy-slots-list').innerHTML = '';

            document.getElementById('rescheduleModal').classList.add('open');
        }}

        function closeReschedule() {{
            document.getElementById('rescheduleModal').classList.remove('open');
        }}

        async function fetchBusySlots() {{
            const docId = document.getElementById('modal-doctor-id').value;
            const newDtVal = document.getElementById('modal-new-datetime').value;
            if (!newDtVal) return;

            const dateStr = newDtVal.split('T')[0];

            try {{
                const res = await fetch(`/receptionist/booked-slots?doctor_id=${{docId}}&date_str=${{dateStr}}`);
                const data = await res.json();
                const container = document.getElementById('busy-slots-container');
                const list = document.getElementById('busy-slots-list');
                
                list.innerHTML = '';
                if (data.booked_slots && data.booked_slots.length > 0) {{
                    data.booked_slots.forEach(slot => {{
                        const badge = document.createElement('span');
                        badge.className = 'badge cancelled';
                        badge.style.fontSize = '11px';
                        badge.style.padding = '3px 8px';
                        badge.style.background = '#fee2e2';
                        badge.style.color = '#b91c1c';
                        badge.textContent = slot;
                        list.appendChild(badge);
                    }});
                    container.style.display = 'block';
                }} else {{
                    list.innerHTML = '<span style="font-size:11px;color:#16a34a">💡 इस दिन कोई अन्य बुकिंग नहीं है। सारे स्लॉट्स खाली हैं।</span>';
                    container.style.display = 'block';
                }}
            }} catch (e) {{
                console.error("Failed to fetch busy slots", e);
            }}
        }}

        async function confirmReschedule() {{
            const apptId = document.getElementById('modal-appt-id').value;
            const newDt = document.getElementById('modal-new-datetime').value;
            const cutoff = document.getElementById('modal-cutoff').value;

            if (!newDt) {{
                alert('कृपया नई Date और Time चुनें।');
                return;
            }}

            const formData = new FormData();
            formData.append('new_status', 'RESCHEDULED');
            formData.append('new_datetime', newDt);
            formData.append('cutoff_note', cutoff);

            try {{
                const res = await fetch(`/appointments/${{apptId}}/status`, {{
                    method: 'POST',
                    body: formData
                }});
                
                if (res.status === 400) {{
                    const errData = await res.json();
                    if (errData.detail === 'appointment already rescheduled once') {{
                        alert('⚠️ यह अपॉइंटमेंट पहले ही 1 बार reschedule की जा चुकी है। इसे दोबारा reschedule नहीं किया जा सकता।');
                        closeReschedule();
                        return;
                    }}
                }}

                const data = await res.json();
                if (data.success) {{
                    closeReschedule();
                    document.getElementById(`badge-${{apptId}}`).innerHTML = '<span class="badge rescheduled">📅 Rescheduled</span>';
                    const actionsDiv = document.getElementById(`actions-${{apptId}}`);
                    if (actionsDiv) actionsDiv.remove();
                    alert('✅ Reschedule हो गया! मरीज़ के WhatsApp पर नया समय भेज दिया गया है।');
                }} else {{
                    alert('कुछ गड़बड़ हो गई।');
                }}
            }} catch (e) {{
                alert('Network error. Please try again.');
            }}
        }}

        document.getElementById('rescheduleModal').addEventListener('click', function(e) {{
            if (e.target === this) closeReschedule();
        }});
    </script>

</body>
</html>"""
    return HTMLResponse(content=html)