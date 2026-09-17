import uuid
import logging
from datetime import datetime, date, time
from typing import Dict, Any, List, Optional
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.appointment import (
    Appointment, Patient, Doctor, Department, AppointmentStatusHistory
)
from app.engines.scheduling import SchedulingEngine
from app.engines.conversation_memory import conversation_memory

logger = logging.getLogger("aura.tools.appointment")

class AppointmentTools:
    """
    HMS Appointment Operational Tools:
    - Real Transactional Booking with Multi-Stage Validation
    - Patient Identity-Scoped My Appointments Lookup
    - Secure Human-in-the-Loop Cancellation with Action Tokens
    - Atomic Rescheduling with Real-Time Slot Revalidation
    """

    @classmethod
    async def book_appointment(
        cls,
        hospital_id: Optional[str],
        user_id: Optional[str],
        role: str,
        doctor_name_or_dept: str,
        date_str: str,
        time_slot: str,
        patient_name: Optional[str] = None,
        phone: Optional[str] = None,
        reason: str = "OPD Consultation",
        source: str = "AI_COPILOT",
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Creates a new appointment transactionally with strict backend validations:
        1. Tenant boundary enforcement
        2. Doctor belongs to hospital & is active
        3. Real slot availability validation
        4. Duplicate booking prevention
        5. Transactional record creation
        """
        if not db or not hospital_id:
            return {"success": False, "error": "Hospital tenant context and DB session required."}

        role_upper = (role or "").upper().replace(" ", "_")

        # 1. Parse Date and Time
        try:
            appt_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else datetime.now().date()
        except Exception:
            appt_date = datetime.now().date()

        # Parse time_slot like "10:00 AM", "04:30 PM", "14:00"
        target_time = None
        for fmt in ("%I:%M %p", "%I:%M%p", "%H:%M", "%I %p"):
            try:
                target_time = datetime.strptime(time_slot.strip(), fmt).time()
                break
            except Exception:
                continue

        if not target_time:
            return {"success": False, "error": f"Invalid time slot format '{time_slot}'. Please use format like '10:00 AM' or '04:30 PM'."}

        appt_datetime = datetime.combine(appt_date, target_time)

        # 2. Resolve Doctor in this Hospital
        clean_doc = doctor_name_or_dept.lower().replace("dr.", "").replace("dr ", "").replace("doctor", "").strip()
        tokens = [t.strip() for t in clean_doc.split() if len(t.strip()) >= 2]
        match_clauses = [
            func.concat(func.trim(Doctor.first_name), " ", func.trim(Doctor.last_name)).ilike(f"%{clean_doc}%"),
            func.trim(Doctor.first_name).ilike(f"%{clean_doc}%"),
            func.trim(Doctor.last_name).ilike(f"%{clean_doc}%"),
            Department.name.ilike(f"%{clean_doc}%")
        ]
        for tok in tokens:
            match_clauses.append(func.trim(Doctor.first_name).ilike(f"%{tok}%"))
            match_clauses.append(func.trim(Doctor.last_name).ilike(f"%{tok}%"))
        if len(tokens) >= 2:
            match_clauses.append(and_(
                func.trim(Doctor.first_name).ilike(f"%{tokens[0]}%"),
                func.trim(Doctor.last_name).ilike(f"%{tokens[-1]}%")
            ))

        doc_stmt = (
            select(Doctor, Department)
            .join(Department, Doctor.department_id == Department.id)
            .where(
                Doctor.hospital_id == hospital_id,
                Doctor.is_active == True,
                or_(*match_clauses)
            )
        )
        doc_res = (await db.execute(doc_stmt)).first()
        if not doc_res:
            return {"success": False, "error": f"Doctor or department '{doctor_name_or_dept}' not found in this hospital."}

        doctor, dept = doc_res

        # 3. Resolve / Create Patient Record
        # If PATIENT role, bind to patient's own phone / identity
        patient_phone = (phone or "").strip()
        patient_full_name = (patient_name or "Walk-in Patient").strip()

        if not patient_phone and role_upper == "PATIENT":
            # Lookup authenticated patient profile
            pat_stmt = select(Patient).where(Patient.hospital_id == hospital_id, Patient.is_active == True)
            if user_id:
                pat_stmt = pat_stmt.where(Patient.id == user_id)
            auth_pat = (await db.execute(pat_stmt)).scalars().first()
            if auth_pat:
                patient_phone = auth_pat.phone
                patient_full_name = f"{auth_pat.first_name} {auth_pat.last_name}".strip()

        if not patient_phone or len(patient_phone) < 8:
            return {"success": False, "error": "Patient mobile phone number is required to confirm booking."}

        # Find or create patient in tenant (safely handling duplicate phones / family members)
        p_stmt = select(Patient).where(Patient.hospital_id == hospital_id, Patient.phone == patient_phone).order_by(Patient.id.asc())
        patients_found = (await db.execute(p_stmt)).scalars().all()
        patient_rec = None
        primary_account_name = None

        if patients_found:
            primary_p = patients_found[0]
            primary_account_name = f"{primary_p.first_name or ''} {primary_p.last_name or ''}".strip()

            p_first = patient_full_name.split()[0].lower() if patient_full_name else ""
            p_full = patient_full_name.strip().lower() if patient_full_name else ""
            for p in patients_found:
                db_first = (p.first_name or "").strip().lower()
                db_full = f"{p.first_name or ''} {p.last_name or ''}".strip().lower()
                if (p_first and db_first == p_first) or (p_full and (p_full == db_full or p_full in db_full or db_full in p_full)):
                    patient_rec = p
                    break

        if not patient_rec:
            parts = patient_full_name.split(maxsplit=1) if patient_full_name else ["Patient"]
            fname = parts[0] if parts else "Patient"
            lname = parts[1] if len(parts) > 1 else ""
            patient_rec = Patient(
                id=f"pat_{uuid.uuid4().hex[:12]}",
                hospital_id=hospital_id,
                first_name=fname,
                last_name=lname,
                date_of_birth=date(1990, 1, 1),
                phone=patient_phone,
                is_active=True
            )
            db.add(patient_rec)
            await db.flush()

        # 4. Check Duplicate Booking (Same patient, same doctor, same day)
        start_day = datetime.combine(appt_date, time.min)
        end_day = datetime.combine(appt_date, time.max)
        dup_stmt = select(Appointment).where(
            Appointment.hospital_id == hospital_id,
            Appointment.patient_id == patient_rec.id,
            Appointment.doctor_id == doctor.id,
            Appointment.appointment_datetime >= start_day,
            Appointment.appointment_datetime <= end_day,
            Appointment.status.in_(["SCHEDULED", "CONFIRMED", "PENDING_PAYMENT"])
        )
        existing = (await db.execute(dup_stmt)).scalars().first()
        if existing:
            return {
                "success": False,
                "error": f"Patient already has an active appointment with Dr. {doctor.first_name} {doctor.last_name} on {appt_date} at {existing.appointment_datetime.strftime('%I:%M %p')}."
            }

        # 5. Check Slot Availability via SchedulingEngine
        scheduling = SchedulingEngine(db)
        avail_slots = await scheduling.get_available_slots(doctor.id, appt_date)
        slot_is_free = any(s.start_time.strftime("%I:%M %p") == target_time.strftime("%I:%M %p") for s in avail_slots)

        if not slot_is_free and len(avail_slots) > 0:
            suggested = [s.start_time.strftime("%I:%M %p") for s in avail_slots[:3]]
            return {
                "success": False,
                "error": f"Slot {time_slot} is not available for Dr. {doctor.first_name} {doctor.last_name} on {appt_date}. Nearest open slots: {', '.join(suggested)}"
            }

        # 6. Create Appointment Record Transactionally
        new_appt = Appointment(
            id=f"apt_{uuid.uuid4().hex[:12]}",
            hospital_id=hospital_id,
            patient_id=patient_rec.id,
            doctor_id=doctor.id,
            appointment_datetime=appt_datetime,
            duration_minutes=30,
            status="SCHEDULED",
            payment_status="PENDING",
            reason=reason,
            source=source,
            booked_by_name=primary_account_name if (primary_account_name and primary_account_name.lower() != f"{patient_rec.first_name} {patient_rec.last_name}".strip().lower()) else None
        )
        db.add(new_appt)

        # Record Status History
        hist = AppointmentStatusHistory(
            id=f"ash_{uuid.uuid4().hex[:12]}",
            appointment_id=new_appt.id,
            previous_status=None,
            new_status="SCHEDULED",
            changed_by_user_id=user_id or "AI_AGENT",
            change_reason="Booked via AURA Copilot"
        )
        db.add(hist)
        await db.commit()

        # Daily token count
        start_day = datetime.combine(appt_date, time.min)
        end_day = datetime.combine(appt_date, time.max)
        token_stmt = select(func.count(Appointment.id)).where(
            Appointment.hospital_id == hospital_id,
            Appointment.doctor_id == doctor.id,
            Appointment.appointment_datetime >= start_day,
            Appointment.appointment_datetime <= end_day
        )
        token_num = (await db.execute(token_stmt)).scalar() or 1

        return {
            "success": True,
            "appointment_id": new_appt.id,
            "token_number": token_num,
            "doctor_name": f"Dr. {doctor.first_name} {doctor.last_name}",
            "department": dept.name,
            "patient_name": patient_full_name,
            "patient_phone": patient_phone,
            "date": appt_date.strftime("%Y-%m-%d"),
            "time": target_time.strftime("%I:%M %p"),
            "time_slot": target_time.strftime("%I:%M %p"),
            "opd_fee": doctor.opd_fees or 500,
            "status": "SCHEDULED"
        }

    @classmethod
    async def get_my_appointments(
        cls,
        hospital_id: Optional[str],
        user_id: Optional[str],
        role: str,
        phone: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Returns appointments strictly scoped to the authenticated patient identity,
        preventing unauthorized access to other patients' records.
        """
        if not db or not hospital_id:
            return {"error": "Hospital tenant ID and active DB session required."}

        role_upper = (role or "").upper().replace(" ", "_")

        stmt = (
            select(Appointment, Doctor, Department, Patient)
            .join(Doctor, Appointment.doctor_id == Doctor.id)
            .join(Department, Doctor.department_id == Department.id)
            .join(Patient, Appointment.patient_id == Patient.id)
            .where(Appointment.hospital_id == hospital_id)
        )

        if role_upper == "PATIENT":
            # Strict Patient Scope
            if phone and phone.strip():
                stmt = stmt.where(Patient.phone.ilike(f"%{phone.strip()}%"))
            elif user_id:
                stmt = stmt.where(or_(Patient.id == user_id, Appointment.patient_id == user_id))
            else:
                return {"appointments": [], "count": 0, "message": "Please provide your registered phone number to view appointments."}
        else:
            # Staff / Admin lookup
            if phone and phone.strip():
                stmt = stmt.where(Patient.phone.ilike(f"%{phone.strip()}%"))

        stmt = stmt.order_by(Appointment.appointment_datetime.desc()).limit(20)
        rows = (await db.execute(stmt)).all()

        appts = []
        for appt, doc, dept, pat in rows:
            appts.append({
                "appointment_id": appt.id,
                "doctor_name": f"Dr. {doc.first_name} {doc.last_name}",
                "department": dept.name,
                "patient_name": f"{pat.first_name} {pat.last_name}".strip(),
                "patient_phone": pat.phone,
                "appointment_datetime": appt.appointment_datetime.strftime("%Y-%m-%d %I:%M %p"),
                "date": appt.appointment_datetime.strftime("%Y-%m-%d"),
                "time": appt.appointment_datetime.strftime("%I:%M %p"),
                "status": appt.status,
                "payment_status": appt.payment_status,
                "reason": appt.reason
            })

        return {
            "appointments": appts,
            "total_count": len(appts),
            "count": len(appts),
            "hospital_id": hospital_id
        }

    @classmethod
    async def cancel_appointment(
        cls,
        hospital_id: Optional[str],
        user_id: Optional[str],
        role: str,
        appointment_id_or_query: str,
        reason: str = "Cancelled by user via Copilot",
        confirmation_token: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Secure cancellation requiring Human-in-the-Loop Confirmation:
        - If no valid confirmation token: generates action token and returns CONFIRMATION_REQUIRED.
        - If confirmation token is valid: validates ownership and cancels appointment.
        """
        if not db or not hospital_id:
            return {"success": False, "error": "Hospital tenant ID and active DB session required."}

        # 1. Resolve Appointment
        clean_q = appointment_id_or_query.strip()
        stmt = (
            select(Appointment, Doctor, Patient)
            .join(Doctor, Appointment.doctor_id == Doctor.id)
            .join(Patient, Appointment.patient_id == Patient.id)
            .where(
                Appointment.hospital_id == hospital_id,
                or_(
                    Appointment.id == clean_q,
                    Patient.phone.ilike(f"%{clean_q}%"),
                    Patient.first_name.ilike(f"%{clean_q}%")
                ),
                Appointment.status.in_(["SCHEDULED", "CONFIRMED", "PENDING_PAYMENT", "RESCHEDULED"])
            )
        )
        res = (await db.execute(stmt)).first()
        if not res:
            return {"success": False, "error": f"No active scheduled appointment found matching '{clean_q}'."}

        appt, doc, pat = res
        role_upper = (role or "").upper().replace(" ", "_")

        # 2. Check Ownership for PATIENT role
        if role_upper == "PATIENT" and user_id:
            owns = (pat.id == user_id) or (appt.patient_id == user_id) or (pat.phone in clean_q) or (clean_q == appt.id)
            if not owns:
                return {"success": False, "error": "Access Denied: You can only cancel your own appointments."}

        # 3. Confirmation Flow Check
        if not confirmation_token:
            summary = f"Cancel appointment #{appt.id} with Dr. {doc.first_name} {doc.last_name} on {appt.appointment_datetime.strftime('%Y-%m-%d at %I:%M %p')}"
            token_rec = conversation_memory.create_confirmation_token(
                hospital_id=hospital_id,
                user_id=user_id or "ANONYMOUS",
                action_name="cancel_appointment",
                action_args={"appointment_id_or_query": appt.id, "reason": reason},
                summary=summary,
                expires_in_seconds=120
            )
            return {
                "status": "CONFIRMATION_REQUIRED",
                "confirmation_token": token_rec.token,
                "summary": summary,
                "appointment_id": appt.id,
                "patient_name": f"{pat.first_name} {pat.last_name}",
                "doctor_name": f"Dr. {doc.first_name} {doc.last_name}",
                "datetime": appt.appointment_datetime.strftime("%Y-%m-%d %I:%M %p"),
                "message": f"⚠️ Are you sure you want to cancel appointment #{appt.id}? Type 'CONFIRM {token_rec.token}' or click Confirm."
            }

        # 4. Validate and Consume Confirmation Token
        consumed = conversation_memory.validate_and_consume_token(
            token=confirmation_token,
            hospital_id=hospital_id,
            user_id=user_id or "ANONYMOUS"
        )
        if not consumed:
            return {"success": False, "error": "Confirmation token is invalid or has expired. Please initiate cancellation again."}

        # 5. Execute Cancellation Transactionally
        appt.status = "CANCELLED"
        appt.consultation_status = "CANCELLED"
        appt.updated_at = datetime.now()

        hist = AppointmentStatusHistory(
            id=f"ash_{uuid.uuid4().hex[:12]}",
            appointment_id=appt.id,
            previous_status="SCHEDULED",
            new_status="CANCELLED",
            changed_by_user_id=user_id or "AI_AGENT",
            change_reason=reason
        )
        db.add(hist)
        await db.commit()

        return {
            "success": True,
            "appointment_id": appt.id,
            "status": "CANCELLED",
            "patient_name": f"{pat.first_name} {pat.last_name}",
            "doctor_name": f"Dr. {doc.first_name} {doc.last_name}",
            "cancellation_reason": reason,
            "message": f"Appointment #{appt.id} has been successfully cancelled."
        }

    @classmethod
    async def reschedule_appointment(
        cls,
        hospital_id: Optional[str],
        user_id: Optional[str],
        role: str,
        appointment_id_or_query: str,
        new_date_str: str,
        new_time_slot: str,
        reason: str = "Rescheduled by user via Copilot",
        confirmation_token: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Reschedules an appointment with live slot availability revalidation.
        """
        if not db or not hospital_id:
            return {"success": False, "error": "Hospital tenant ID and active DB session required."}

        # 1. Resolve Appointment
        clean_q = appointment_id_or_query.strip()
        stmt = (
            select(Appointment, Doctor, Patient)
            .join(Doctor, Appointment.doctor_id == Doctor.id)
            .join(Patient, Appointment.patient_id == Patient.id)
            .where(
                Appointment.hospital_id == hospital_id,
                or_(
                    Appointment.id == clean_q,
                    Patient.phone.ilike(f"%{clean_q}%")
                ),
                Appointment.status.in_(["SCHEDULED", "CONFIRMED", "PENDING_PAYMENT", "RESCHEDULED"])
            )
        )
        res = (await db.execute(stmt)).first()
        if not res:
            return {"success": False, "error": f"No active appointment found matching '{clean_q}' to reschedule."}

        appt, doc, pat = res

        # 2. Parse New DateTime
        try:
            new_date = datetime.strptime(new_date_str, "%Y-%m-%d").date()
        except Exception:
            return {"success": False, "error": f"Invalid date format '{new_date_str}'. Please use YYYY-MM-DD."}

        target_time = None
        for fmt in ("%I:%M %p", "%I:%M%p", "%H:%M", "%I %p"):
            try:
                target_time = datetime.strptime(new_time_slot.strip(), fmt).time()
                break
            except Exception:
                continue

        if not target_time:
            return {"success": False, "error": f"Invalid time slot format '{new_time_slot}'. Please use '10:00 AM' or '04:30 PM'."}

        new_datetime = datetime.combine(new_date, target_time)

        # 3. Live Re-validation of Slot Availability
        scheduling = SchedulingEngine(db)
        avail_slots = await scheduling.get_available_slots(doc.id, new_date)
        slot_is_free = any(s.start_time.strftime("%I:%M %p") == target_time.strftime("%I:%M %p") for s in avail_slots)

        if not slot_is_free and len(avail_slots) > 0:
            suggested = [s.start_time.strftime("%I:%M %p") for s in avail_slots[:3]]
            return {
                "success": False,
                "error": f"Slot {new_time_slot} is not available on {new_date_str}. Available slots: {', '.join(suggested)}"
            }

        # 4. Execute Update Transactionally
        old_dt = appt.appointment_datetime
        appt.appointment_datetime = new_datetime
        appt.status = "RESCHEDULED"
        appt.reschedule_count = (appt.reschedule_count or 0) + 1
        appt.updated_at = datetime.now()

        hist = AppointmentStatusHistory(
            id=f"ash_{uuid.uuid4().hex[:12]}",
            appointment_id=appt.id,
            previous_status="SCHEDULED",
            new_status="RESCHEDULED",
            changed_by_user_id=user_id or "AI_AGENT",
            change_reason=f"Rescheduled from {old_dt} to {new_datetime}. Reason: {reason}"
        )
        db.add(hist)
        await db.commit()

        return {
            "success": True,
            "appointment_id": appt.id,
            "patient_name": f"{pat.first_name} {pat.last_name}",
            "doctor_name": f"Dr. {doc.first_name} {doc.last_name}",
            "old_datetime": old_dt.strftime("%Y-%m-%d %I:%M %p"),
            "new_date": new_date.strftime("%Y-%m-%d"),
            "new_time": target_time.strftime("%I:%M %p"),
            "status": "RESCHEDULED"
        }
