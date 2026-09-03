from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import and_, or_
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date

import app.database.models
from app.database.session import get_db
from app.database.models.appointment import Hospital, Doctor, Appointment, Department, Patient, ConsultationNote
from app.core.dependencies import get_current_user, oauth2_scheme

router = APIRouter()

# Dependency to ensure current user is a patient
async def get_current_patient(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        from app.core.config import settings
        import jwt
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        role = payload.get("role")
        if role != "PATIENT":
            raise credentials_exception
        return payload
    except Exception as e:
        raise credentials_exception


@router.get("/hospital/{slug}")
async def get_hospital_by_slug(slug: str, db: AsyncSession = Depends(get_db)):
    from urllib.parse import unquote
    clean_slug = unquote(slug).strip()
    hyphen_slug = clean_slug.replace(" ", "-").lower()

    stmt = select(Hospital).where(
        or_(
            Hospital.id == clean_slug,
            Hospital.slug == slug,
            Hospital.slug == clean_slug,
            Hospital.slug == hyphen_slug,
            Hospital.name.ilike(f"%{clean_slug}%")
        ),
        Hospital.is_active == True
    )
    hospital = (await db.execute(stmt)).scalars().first()
    if not hospital:
        # Fallback to default hospital if not found
        fallback_stmt = select(Hospital).where(Hospital.is_active == True).order_by(Hospital.created_at.asc())
        hospital = (await db.execute(fallback_stmt)).scalars().first()

    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital not found")
        
    # Get active departments
    dept_stmt = select(Department).where(Department.hospital_id == hospital.id, Department.is_active == True)
    departments = (await db.execute(dept_stmt)).scalars().all()
    
    return {
        "id": hospital.id,
        "name": hospital.name,
        "slug": hospital.slug,
        "address": hospital.address,
        "phone": hospital.phone,
        "departments": [{"id": d.id, "name": d.name} for d in departments]
    }

@router.get("/doctors")
async def get_doctors(hospital_id: str, department_id: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    stmt = select(Doctor).options(selectinload(Doctor.department), selectinload(Doctor.schedules)).where(Doctor.hospital_id == hospital_id, Doctor.is_active == True)
    if department_id:
        stmt = stmt.where(Doctor.department_id == department_id)
        
    doctors = (await db.execute(stmt)).scalars().all()
    
    results = []
    for d in doctors:
        # Get first schedule or default
        schedule_str = "Mon-Sat: 10:00 AM - 5:00 PM"
        if d.schedules:
            sch = d.schedules[0]
            start = sch.start_time.strftime("%I:%M %p") if sch.start_time else "10:00 AM"
            end = sch.end_time.strftime("%I:%M %p") if sch.end_time else "05:00 PM"
            schedule_str = f"Days: {sch.day_of_week} | {start} - {end}"
            
        # Hardcoded Hindi translations for standard departments
        dept_name = d.department.name if d.department else "General"
        hindi_map = {
            "Cardiology": "हृदय रोग (Cardiology)",
            "Neurology": "स्नायुतंत्र (Neurology)",
            "Orthopedics": "हड्डी रोग (Orthopedics)",
            "Pediatrics": "बाल रोग (Pediatrics)",
            "Gynecology": "स्त्री रोग (Gynecology)",
            "Dermatology": "त्वचा रोग (Dermatology)",
            "ENT": "कान, नाक, गला (ENT)",
            "Ophthalmology": "नेत्र रोग (Ophthalmology)",
            "General Medicine": "सामान्य चिकित्सा (General Medicine)",
            "Dental": "दंत चिकित्सा (Dental)"
        }
        dept_display = hindi_map.get(dept_name, f"{dept_name} (Department)")
        
        results.append({
            "id": d.id, 
            "name": f"{d.first_name} {d.last_name}", 
            "department_id": d.department_id,
            "department_name": dept_display,
            "schedule": schedule_str,
            "opd_fees": d.opd_fees
        })
        
    return results

@router.get("/doctors/{doctor_id}/slots")
async def get_doctor_slots(doctor_id: str, date_param: date = Query(..., alias="date"), db: AsyncSession = Depends(get_db)):
    # 1. Fetch Doctor and their schedule for this day
    from app.database.models.appointment import DoctorSchedule
    day_of_week = date_param.isoweekday()
    sched_stmt = select(DoctorSchedule).where(
        DoctorSchedule.doctor_id == doctor_id,
        DoctorSchedule.day_of_week == day_of_week
    )
    schedules = (await db.execute(sched_stmt)).scalars().all()
    
    if not schedules:
        return {"date": date_param, "slots": []}

    # 2. Fetch booked appointments for the day
    stmt = select(Appointment).where(
        Appointment.doctor_id == doctor_id, 
        Appointment.appointment_datetime >= datetime.combine(date_param, datetime.min.time()),
        Appointment.appointment_datetime <= datetime.combine(date_param, datetime.max.time()),
        Appointment.status != "CANCELLED"
    )
    booked_appts = (await db.execute(stmt)).scalars().all()
    
    # Store booked times in %H:%M format
    booked_times = [a.appointment_datetime.strftime("%H:%M") for a in booked_appts]
    
    # 3. Check if requested date is today to block past slots
    from datetime import datetime as dt, timedelta
    now = dt.now()
    is_today = date_param == now.date()
    current_time_str = now.strftime("%H:%M")
    
    slots = []
    
    # 4. Generate slots based on schedule
    for schedule in schedules:
        if not schedule.slot_duration_minutes or schedule.slot_duration_minutes <= 0:
            continue
            
        slot_duration = timedelta(minutes=schedule.slot_duration_minutes)
        current_dt = datetime.combine(date_param, schedule.start_time)
        end_dt = datetime.combine(date_param, schedule.end_time)
        
        while current_dt + slot_duration <= end_dt:
            time_str_24h = current_dt.strftime("%H:%M")
            time_str_12h = current_dt.strftime("%I:%M %p")
            
            is_past = is_today and time_str_24h <= current_time_str
            is_booked = (time_str_24h in booked_times) or is_past
            
            slots.append({
                "time": time_str_12h,
                "value": time_str_24h, # Actual value sent to backend
                "is_booked": is_booked
            })
            
            current_dt += slot_duration
            
    return {"date": date_param, "slots": slots}


@router.get("/doctors/{doctor_id}/next-working-days")
async def get_doctor_next_working_days(
    doctor_id: str,
    count: int = Query(3, ge=1, le=7),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns the doctor's next N active working days, skipping off-days, leaves, and hospital holidays.
    """
    from datetime import datetime as dt, timedelta
    from app.database.models.appointment import DoctorSchedule, DoctorLeave, HospitalHoliday, Doctor

    start_date = dt.now().date()

    # 1. Fetch Doctor
    doc_stmt = select(Doctor).where(Doctor.id == doctor_id)
    doctor = (await db.execute(doc_stmt)).scalar_one_or_none()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    # 2. Fetch all weekly schedules for this doctor
    sched_stmt = select(DoctorSchedule).where(DoctorSchedule.doctor_id == doctor_id)
    schedules = (await db.execute(sched_stmt)).scalars().all()
    working_dow_set = {s.day_of_week for s in schedules if s.slot_duration_minutes and s.slot_duration_minutes > 0}

    # 3. Fetch doctor leaves (APPROVED or PENDING)
    leave_stmt = select(DoctorLeave).where(
        DoctorLeave.doctor_id == doctor_id,
        DoctorLeave.end_date >= start_date,
        DoctorLeave.status.in_(["APPROVED", "PENDING"])
    )
    doctor_leaves = (await db.execute(leave_stmt)).scalars().all()

    # 4. Fetch hospital holidays
    holiday_stmt = select(HospitalHoliday.holiday_date).where(
        HospitalHoliday.hospital_id == doctor.hospital_id,
        HospitalHoliday.holiday_date >= start_date
    )
    holiday_dates = set((await db.execute(holiday_stmt)).scalars().all())

    working_days = []
    curr = start_date
    max_lookahead = 21 # Search up to 3 weeks ahead for active working days

    for _ in range(max_lookahead):
        dow = curr.isoweekday()
        is_on_leave = any(l.start_date <= curr <= l.end_date for l in doctor_leaves)
        is_holiday = curr in holiday_dates

        if dow in working_dow_set and not is_on_leave and not is_holiday:
            label = "Today" if curr == start_date else ("Tomorrow" if curr == start_date + timedelta(days=1) else curr.strftime("%a"))
            working_days.append({
                "date": curr.isoformat(),
                "day_name": curr.strftime("%A"),
                "display_label": label,
                "display_date": curr.strftime("%b %d"),
                "is_today": curr == start_date
            })
            if len(working_days) >= count:
                break
        curr += timedelta(days=1)

    return {"doctor_id": doctor_id, "working_days": working_days}




class BookAppointmentRequest(BaseModel):
    hospital_id: str
    doctor_id: str
    appointment_datetime: datetime
    reason: Optional[str] = None
    patient_id: Optional[str] = None
    patient_name: Optional[str] = None
    patient_age: Optional[int] = None
    payment_mode: Optional[str] = "ONLINE"  # "ONLINE" or "COUNTER"

@router.post("/appointments")
async def book_appointment(request: BookAppointmentRequest, current_patient=Depends(get_current_patient), db: AsyncSession = Depends(get_db)):
    import uuid
    from app.core.logging import logger
    
    phone = current_patient.get("sub") if isinstance(current_patient, dict) else getattr(current_patient, "phone", None)
    logged_in_patient_id = current_patient.get("user_id") if isinstance(current_patient, dict) else getattr(current_patient, "id", None)

    # Fetch logged in account holder (booker)
    booker = None
    if logged_in_patient_id:
        booker_stmt = select(Patient).where(Patient.id == logged_in_patient_id)
        booker = (await db.execute(booker_stmt)).scalars().first()
    elif phone:
        booker_stmt = select(Patient).where(Patient.phone == phone).order_by(Patient.created_at.asc())
        booker = (await db.execute(booker_stmt)).scalars().first()
        if booker:
            logged_in_patient_id = booker.id

    booker_name = f"{booker.first_name} {booker.last_name}".strip() if booker else "Account Holder"

    # Resolve target patient_id (Handle booking for self vs family member)
    target_patient_id = None
    is_self_booking = True

    if request.patient_name and request.patient_name.strip() and booker and request.patient_name.strip().lower() != booker_name.lower():
        # Booking for someone else (family member)
        is_self_booking = False
        p_name = request.patient_name.strip()
        name_parts = p_name.split(" ", 1)
        f_name = name_parts[0]
        l_name = name_parts[1] if len(name_parts) > 1 else ""

        # Check if family patient record already exists for this phone number
        p_stmt = select(Patient).where(
            Patient.hospital_id == request.hospital_id,
            Patient.phone == phone,
            Patient.first_name.ilike(f_name)
        )
        existing_family_p = (await db.execute(p_stmt)).scalars().first()
        if existing_family_p:
            target_patient_id = existing_family_p.id
        else:
            # Create new family member Patient record linked to hospital & phone
            from datetime import date as date_type
            new_p = Patient(
                id=str(uuid.uuid4()),
                hospital_id=request.hospital_id,
                first_name=f_name,
                last_name=l_name,
                phone=phone,
                date_of_birth=date_type(1990, 1, 1),
                is_active=True
            )
            db.add(new_p)
            await db.flush()
            target_patient_id = new_p.id
    elif request.patient_id:
        p_stmt = select(Patient).where(Patient.id == request.patient_id, Patient.phone == phone)
        target_p = (await db.execute(p_stmt)).scalars().first()
        target_patient_id = target_p.id if target_p else logged_in_patient_id
        is_self_booking = (target_patient_id == logged_in_patient_id)
    else:
        target_patient_id = logged_in_patient_id
        is_self_booking = True

    if not target_patient_id and phone:
        p_stmt = select(Patient).where(Patient.phone == phone).order_by(Patient.created_at.asc())
        target_p = (await db.execute(p_stmt)).scalars().first()
        if target_p:
            target_patient_id = target_p.id

    if not target_patient_id:
        raise HTTPException(status_code=400, detail="Could not identify patient. Please log out and log in again.")

    payment_mode = (request.payment_mode or "ONLINE").upper()
    
    # Idempotency check: if active appointment already exists with same patient, doctor, and time, return it immediately.
    existing_stmt = select(Appointment).where(
        Appointment.patient_id == target_patient_id,
        Appointment.doctor_id == request.doctor_id,
        Appointment.appointment_datetime == request.appointment_datetime,
        Appointment.status.in_(["SCHEDULED", "PENDING_PAYMENT", "RESCHEDULED"])
    )
    existing = (await db.execute(existing_stmt)).scalar_one_or_none()
    if existing:
        import json
        from app.core.logging import request_id_context
        log_data = {
            "event": "idempotent_patient_portal_booking_triggered",
            "patient_id": target_patient_id,
            "doctor_id": request.doctor_id,
            "time": request.appointment_datetime.isoformat()
        }
        req_id = request_id_context.get()
        if req_id:
            log_data["request_id"] = req_id
        logger.info(json.dumps(log_data))
        return {"success": True, "appointment_id": existing.id, "payment_mode": payment_mode, "idempotent": True}

    try:
        appt = Appointment(
            id=str(uuid.uuid4()),
            hospital_id=request.hospital_id,
            patient_id=target_patient_id,
            doctor_id=request.doctor_id,
            appointment_datetime=request.appointment_datetime,
            duration_minutes=30,
            status="PENDING_PAYMENT",
            payment_status="PENDING",
            payment_method=payment_mode,
            consultation_status="SCHEDULED",
            reason=request.reason,
            source="PATIENT_PORTAL",
            booked_by_name=None if is_self_booking else booker_name,
            patient_name_override=request.patient_name
        )
        db.add(appt)
        await db.flush()
        await db.commit()
        
        import json
        from app.core.logging import request_id_context
        log_data = {
            "event": "patient_portal_appointment_booked",
            "appointment_id": appt.id,
            "doctor_id": request.doctor_id,
            "patient_id": target_patient_id
        }
        req_id = request_id_context.get()
        if req_id:
            log_data["request_id"] = req_id
        logger.info(json.dumps(log_data))
    except Exception as e:
        await db.rollback()
        logger.error(f"Error during patient portal booking database transaction: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Booking failed due to database transaction error: {str(e)}")

    # Trigger WhatsApp notification based on payment mode
    try:
        from app.services.whatsapp import WhatsAppNotificationService
        import asyncio
        wa_service = WhatsAppNotificationService()

        pat_stmt = select(Patient).where(Patient.id == target_patient_id)
        patient = (await db.execute(pat_stmt)).scalar_one_or_none()
        doc_stmt = select(Doctor).where(Doctor.id == request.doctor_id)
        doctor = (await db.execute(doc_stmt)).scalar_one_or_none()
        hosp_stmt = select(Hospital).where(Hospital.id == request.hospital_id)
        hospital = (await db.execute(hosp_stmt)).scalar_one_or_none()

        if patient and doctor and hospital:
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
            if payment_mode == "COUNTER":
                asyncio.create_task(wa_service.send_counter_booking_confirmation(wa_details))
            else:
                asyncio.create_task(wa_service.send_patient_confirmation(wa_details))
    except Exception as wa_err:
        logger.error(f"WhatsApp booking dispatch failed: {wa_err}")

    return {"success": True, "appointment_id": appt.id, "payment_mode": payment_mode}

@router.get("/appointments")
async def get_patient_appointments(
    patient_id: Optional[str] = Query(None),
    current_patient=Depends(get_current_patient),
    db: AsyncSession = Depends(get_db)
):
    from app.api.v1.endpoints.appointments import auto_update_missed_appointments
    from datetime import datetime, timedelta
    
    # Auto-sweep missed appointments
    await auto_update_missed_appointments(db)
    
    default_patient_id = current_patient.get("user_id") if isinstance(current_patient, dict) else current_patient.id
    phone = current_patient.get("sub") if isinstance(current_patient, dict) else getattr(current_patient, "phone", None)
    hospital_id = current_patient.get("hospital_id") if isinstance(current_patient, dict) else None
    
    # Normalize phone matching (both +91 and 10-digit)
    phone_clean = phone.replace("+91", "").strip() if phone else ""
    
    p_stmt = select(Patient.id).where(or_(Patient.phone == phone, Patient.phone == f"+91{phone_clean}", Patient.phone.contains(phone_clean)))
    if hospital_id:
        p_stmt = p_stmt.where(Patient.hospital_id == hospital_id)
        
    valid_patient_ids = (await db.execute(p_stmt)).scalars().all() or [default_patient_id]

    if patient_id and patient_id in valid_patient_ids:
        target_patient_ids = [patient_id]
    else:
        target_patient_ids = valid_patient_ids

    stmt = select(Appointment).options(selectinload(Appointment.doctor), selectinload(Appointment.patient)).where(Appointment.patient_id.in_(target_patient_ids))
    if hospital_id:
        stmt = stmt.where(Appointment.hospital_id == hospital_id)
        
    stmt = stmt.order_by(Appointment.appointment_datetime.desc())
    appts = (await db.execute(stmt)).scalars().all()
    
    now = datetime.now()
    results = []
    for a in appts:
        can_reschedule = False
        reschedule_count = getattr(a, "reschedule_count", 0) or 0
        is_paid = a.payment_status in ["PAID", "COMPLETED"]
        
        if is_paid and reschedule_count < 1:
            if a.status in ["SCHEDULED", "CONFIRMED", "RESCHEDULED"]:
                can_reschedule = True
            elif a.status == "MISSED":
                if now <= a.appointment_datetime + timedelta(hours=48):
                    can_reschedule = True

        patient_name = f"{a.patient.first_name} {a.patient.last_name}".strip() if a.patient else "Patient"

        results.append({
            "id": a.id,
            "datetime": a.appointment_datetime,
            "status": a.status,
            "payment_status": a.payment_status,
            "payment_method": getattr(a, "payment_method", "ONLINE") or "ONLINE",
            "reason": a.reason,
            "patient_id": a.patient_id,
            "patient_name": patient_name,
            "doctor_name": f"Dr. {a.doctor.first_name} {a.doctor.last_name}" if a.doctor else "Unknown",
            "doctor_id": a.doctor_id,
            "reschedule_count": reschedule_count,
            "can_reschedule": can_reschedule
        })
    return results

@router.get("/appointments/{appointment_id}/prescription")
async def get_prescription(appointment_id: str, current_patient=Depends(get_current_patient), db: AsyncSession = Depends(get_db)):
    phone = current_patient.get("sub") if isinstance(current_patient, dict) else getattr(current_patient, "phone", None)
    
    # Verify appointment belongs to patient phone
    p_stmt = select(Patient.id).where(Patient.phone == phone)
    all_patient_ids = (await db.execute(p_stmt)).scalars().all()
    
    stmt = select(Appointment).where(Appointment.id == appointment_id, Appointment.patient_id.in_(all_patient_ids))
    appt = (await db.execute(stmt)).scalars().first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
        
    note_stmt = select(ConsultationNote).where(ConsultationNote.appointment_id == appointment_id)
    note = (await db.execute(note_stmt)).scalars().first()
    
    pat_stmt = select(Patient).where(Patient.id == appt.patient_id)
    patient = (await db.execute(pat_stmt)).scalar_one_or_none()
    doc_stmt = select(Doctor).where(Doctor.id == appt.doctor_id)
    doctor = (await db.execute(doc_stmt)).scalar_one_or_none()
    hosp_stmt = select(Hospital).where(Hospital.id == appt.hospital_id)
    hospital = (await db.execute(hosp_stmt)).scalar_one_or_none()

    if not note:
        return {
            "has_prescription": False,
            "patient_name": f"{patient.first_name} {patient.last_name}".strip() if patient else "Patient",
            "doctor_name": f"Dr. {doctor.first_name} {doctor.last_name}".strip() if doctor else "Doctor",
            "doctor_specialty": getattr(doctor, "specialization", "General") if doctor else "General",
            "hospital_name": hospital.name if hospital else "Hospital",
            "hospital_address": getattr(hospital, "address", "") if hospital else "",
            "appointment_date": appt.appointment_datetime.strftime("%d %B %Y") if appt.appointment_datetime else "N/A"
        }
        
    return {
        "has_prescription": True,
        "clinical_notes": note.clinical_notes,
        "prescription": note.prescription,
        "follow_up_date": str(note.follow_up_date) if note.follow_up_date else None,
        "patient_name": f"{patient.first_name} {patient.last_name}".strip() if patient else "Patient",
        "doctor_name": f"Dr. {doctor.first_name} {doctor.last_name}".strip() if doctor else "Doctor",
        "doctor_specialty": getattr(doctor, "specialization", "General") if doctor else "General",
        "hospital_name": hospital.name if hospital else "Hospital",
        "hospital_address": getattr(hospital, "address", "") if hospital else "",
        "appointment_date": appt.appointment_datetime.strftime("%d %B %Y") if appt.appointment_datetime else "N/A"
    }


class PatientRescheduleRequest(BaseModel):
    new_datetime: str


@router.post("/appointments/{appointment_id}/reschedule")
async def patient_reschedule_appointment(
    appointment_id: str,
    request: PatientRescheduleRequest,
    current_patient=Depends(get_current_patient),
    db: AsyncSession = Depends(get_db)
):
    """
    Patient self-service 1-time reschedule within 48h and next 2 days only.
    """
    phone = current_patient.get("sub") if isinstance(current_patient, dict) else getattr(current_patient, "phone", None)
    p_stmt = select(Patient.id).where(Patient.phone == phone)
    all_patient_ids = (await db.execute(p_stmt)).scalars().all()

    stmt = select(Appointment).where(Appointment.id == appointment_id, Appointment.patient_id.in_(all_patient_ids))
    appt = (await db.execute(stmt)).scalars().first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found.")

    if appt.payment_status not in ["PAID", "COMPLETED", "SUCCESS", "PAID_RECEPTION", "captured"]:
        raise HTTPException(status_code=400, detail="Rescheduling is allowed only for paid appointments.")

    if (appt.reschedule_count or 0) >= 1:
        raise HTTPException(status_code=400, detail="This appointment has already reached the maximum limit of 1 reschedule.")

    now = datetime.now()
    if appt.status == "MISSED" or appt.appointment_datetime < now:
        if now > appt.appointment_datetime + timedelta(hours=48):
            raise HTTPException(status_code=400, detail="Reschedule window expired. Rescheduling is strictly allowed only within 48 hours of missed appointment.")

    try:
        target_dt = datetime.fromisoformat(request.new_datetime)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid datetime format. Use ISO format.")

    max_allowed_date = now.date() + timedelta(days=2)
    if target_dt.date() < now.date() or target_dt.date() > max_allowed_date:
        raise HTTPException(status_code=400, detail="Rescheduling is strictly restricted to dates within the next 2 days.")

    appt.appointment_datetime = target_dt
    appt.status = "RESCHEDULED"
    appt.reschedule_count = (appt.reschedule_count or 0) + 1
    appt.updated_at = now

    await db.commit()
    await db.refresh(appt)

    # WhatsApp notification
    try:
        from app.services.whatsapp import WhatsAppNotificationService
        import asyncio
        wa_service = WhatsAppNotificationService()
        pat_stmt = select(Patient).where(Patient.id == appt.patient_id)
        patient = (await db.execute(pat_stmt)).scalar_one_or_none()
        doc_stmt = select(Doctor).where(Doctor.id == appt.doctor_id)
        doctor = (await db.execute(doc_stmt)).scalar_one_or_none()
        hosp_stmt = select(Hospital).where(Hospital.id == appt.hospital_id)
        hospital = (await db.execute(hosp_stmt)).scalar_one_or_none()

        if patient and doctor and hospital:
            wa_details = {
                "hospital_id": hospital.id,
                "hospital_name": hospital.name,
                "appointment_id": appt.id,
                "patient_name": f"{patient.first_name} {patient.last_name}".strip(),
                "patient_phone": patient.phone,
                "doctor_name": f"{doctor.first_name} {doctor.last_name}".strip(),
                "appointment_datetime": appt.appointment_datetime.isoformat(),
                "reason": appt.reason or ""
            }
            asyncio.create_task(wa_service.send_appointment_confirmation(wa_details))
    except Exception:
        pass

    return {
        "success": True,
        "message": "Appointment successfully rescheduled.",
        "appointment_id": appt.id,
        "new_datetime": appt.appointment_datetime.isoformat()
    }

class ConfirmPaymentRequest(BaseModel):
    payment_mode: str # "CASH" or "ONLINE"

@router.post("/appointments/{appointment_id}/confirm-payment")
async def confirm_payment(appointment_id: str, request: ConfirmPaymentRequest, current_patient=Depends(get_current_patient), db: AsyncSession = Depends(get_db)):
    from app.core.logging import logger
    phone = current_patient.get("sub") if isinstance(current_patient, dict) else getattr(current_patient, "phone", None)
    
    p_stmt = select(Patient.id).where(Patient.phone == phone)
    all_patient_ids = (await db.execute(p_stmt)).scalars().all()

    stmt = select(Appointment).where(Appointment.id == appointment_id, Appointment.patient_id.in_(all_patient_ids))
    appt = (await db.execute(stmt)).scalars().first()
    
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
        
    if request.payment_mode == "ONLINE":
        appt.payment_status = "PAID"
        if appt.status == "PENDING_PAYMENT":
            appt.status = "SCHEDULED"
    
    db.add(appt)
    await db.commit()

    # Trigger WhatsApp confirmation message to patient
    try:
        from app.services.whatsapp import WhatsAppNotificationService
        import asyncio
        wa_service = WhatsAppNotificationService()

        pat_stmt = select(Patient).where(Patient.id == appt.patient_id)
        patient = (await db.execute(pat_stmt)).scalar_one_or_none()
        doc_stmt = select(Doctor).where(Doctor.id == appt.doctor_id)
        doctor = (await db.execute(doc_stmt)).scalar_one_or_none()
        hosp_stmt = select(Hospital).where(Hospital.id == appt.hospital_id)
        hospital = (await db.execute(hosp_stmt)).scalar_one_or_none()

        if patient and doctor and hospital:
            wa_details = {
                "hospital_id": hospital.id,
                "hospital_name": hospital.name,
                "appointment_id": appt.id,
                "patient_name": f"{patient.first_name} {patient.last_name}".strip(),
                "patient_phone": patient.phone,
                "doctor_name": f"{doctor.first_name} {doctor.last_name}".strip(),
                "appointment_datetime": appt.appointment_datetime.isoformat(),
                "reason": appt.reason or ""
            }
            asyncio.create_task(wa_service.send_payment_confirmation(wa_details))
    except Exception as wa_err:
        logger.error(f"WhatsApp booking confirmation failed: {wa_err}")
    
    return {"success": True, "message": "Payment confirmed and WhatsApp notification sent."}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Profile & Family Management Endpoints
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class UpdateProfileRequest(BaseModel):
    name: str
    gender: Optional[str] = None
    date_of_birth: Optional[date] = None

@router.get("/profile")
async def get_patient_profile(current_patient=Depends(get_current_patient), db: AsyncSession = Depends(get_db)):
    phone = current_patient.get("sub") if isinstance(current_patient, dict) else getattr(current_patient, "phone", None)
    hospital_id = current_patient.get("hospital_id") if isinstance(current_patient, dict) else None
    
    stmt = select(Patient).where(Patient.phone == phone)
    if hospital_id:
        stmt = stmt.where(Patient.hospital_id == hospital_id)
    stmt = stmt.order_by(Patient.created_at.asc())
    
    patients = (await db.execute(stmt)).scalars().all()
    
    if not patients:
        raise HTTPException(status_code=404, detail="Patient profile not found.")
        
    primary = patients[0]
    
    return {
        "id": primary.id,
        "name": f"{primary.first_name} {primary.last_name}".strip(),
        "first_name": primary.first_name,
        "last_name": primary.last_name,
        "phone": primary.phone,
        "gender": primary.gender or "Not Specified",
        "date_of_birth": str(primary.date_of_birth) if primary.date_of_birth else None
    }

@router.put("/profile")
async def update_patient_profile(request: UpdateProfileRequest, current_patient=Depends(get_current_patient), db: AsyncSession = Depends(get_db)):
    phone = current_patient.get("sub") if isinstance(current_patient, dict) else getattr(current_patient, "phone", None)
    hospital_id = current_patient.get("hospital_id") if isinstance(current_patient, dict) else None
    
    stmt = select(Patient).where(Patient.phone == phone)
    if hospital_id:
        stmt = stmt.where(Patient.hospital_id == hospital_id)
    stmt = stmt.order_by(Patient.created_at.asc())
    
    primary = (await db.execute(stmt)).scalars().first()
    
    if not primary:
        raise HTTPException(status_code=404, detail="Patient profile not found.")
        
    parts = request.name.strip().split(" ", 1)
    primary.first_name = parts[0]
    primary.last_name = parts[1] if len(parts) > 1 else ""
    
    if request.gender:
        primary.gender = request.gender
    if request.date_of_birth:
        primary.date_of_birth = request.date_of_birth
        
    db.add(primary)
    await db.commit()
    return {"success": True, "message": "Profile updated successfully."}


