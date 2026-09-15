import json
import uuid
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, date, time, timedelta
from sqlalchemy import select, func, case, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.appointment import (
    Hospital, Department, Doctor, DoctorSchedule, DoctorLeave, Appointment, Patient,
    ConsultationNote, PatientIntake, AppointmentStatusHistory
)
from app.database.models.call_log import User, PaymentLink, Payment
from app.engines.scheduling import SchedulingEngine
from app.engines.appointment import AppointmentEngine

logger = logging.getLogger("aura.copilot.tools")

class CopilotTools:
    """
    Enterprise-Grade, Role-Scoped, Multi-Tenant Isolated Tools Suite for AURA AI Copilot.
    Every query strictly enforces `hospital_id` tenancy unless executing a designated SuperAdmin global tool.
    """

    @staticmethod
    def _build_doctor_search_conditions(clean_name: str):
        """Constructs full-name, single-name, and token-split search clauses for Doctor records."""
        conds = [
            func.concat(Doctor.first_name, " ", Doctor.last_name).ilike(f"%{clean_name}%"),
            Doctor.first_name.ilike(f"%{clean_name}%"),
            Doctor.last_name.ilike(f"%{clean_name}%")
        ]
        stopwords = {
            "dr", "dr.", "doctor", "ya", "aur", "rhe", "rahe", "hai", "hain", "kya", "ko", "par", "pe",
            "aaj", "kal", "parso", "baith", "baithe", "baithte", "chutti", "leave", "duty", "off", "on",
            "the", "is", "of", "in", "status", "check", "batao", "dikhao", "please", "sir", "mam"
        }
        tokens = [t.strip() for t in clean_name.split() if t.strip() not in stopwords and len(t.strip()) >= 2]
        for tok in tokens:
            conds.append(Doctor.first_name.ilike(f"%{tok}%"))
            conds.append(Doctor.last_name.ilike(f"%{tok}%"))
        if len(tokens) >= 2:
            conds.append(and_(
                Doctor.first_name.ilike(f"%{tokens[0]}%"),
                Doctor.last_name.ilike(f"%{tokens[-1]}%")
            ))
        return or_(*conds)

    @staticmethod
    async def resolve_hospital_by_name(hospital_name: str, db: AsyncSession) -> Optional[str]:
        """Resolves hospital_id from a hospital name or slug for SuperAdmin cross-hospital lookups."""
        if not hospital_name or not db:
            return None
        clean_h = hospital_name.lower().replace("hospital", "").strip()
        stmt = select(Hospital.id).where(
            or_(
                Hospital.name.ilike(f"%{hospital_name.strip()}%"),
                Hospital.name.ilike(f"%{clean_h}%"),
                Hospital.slug.ilike(f"%{clean_h}%"),
                Hospital.id.ilike(f"%{hospital_name.strip()}%")
            ),
            Hospital.is_active == True
        )
        return (await db.execute(stmt)).scalar_one_or_none()

    # ==========================================
    # DOMAIN 1: DOCTOR LEAVES, SHIFTS & SCHEDULES
    # ==========================================

    @staticmethod
    async def check_doctor_leave_status(
        hospital_id: str,
        doctor_name: str,
        date_str: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """Checks if a doctor is on approved leave or off-duty for a given date."""
        if not db or not hospital_id:
            return {"error": "Invalid session or tenant context"}

        target_date_obj = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else datetime.now().date()
        clean_name = doctor_name.lower().replace("dr.", "").replace("dr ", "").replace("doctor", "").strip()

        # 1. Lookup Doctor
        doc_stmt = select(Doctor, Department).join(Department, Doctor.department_id == Department.id).where(
            Doctor.hospital_id == hospital_id,
            Doctor.is_active == True,
            CopilotTools._build_doctor_search_conditions(clean_name)
        )
        res = (await db.execute(doc_stmt)).first()
        if not res:
            return {"error": f"No active doctor found matching '{doctor_name}' in this hospital."}

        doctor, department = res

        # 2. Check DoctorLeave table
        leave_stmt = select(DoctorLeave).where(
            DoctorLeave.doctor_id == doctor.id,
            DoctorLeave.status == "APPROVED",
            DoctorLeave.start_date <= target_date_obj,
            DoctorLeave.end_date >= target_date_obj
        )
        leave_row = (await db.execute(leave_stmt)).scalar_one_or_none()

        if leave_row:
            return {
                "doctor_name": f"Dr. {doctor.first_name} {doctor.last_name}",
                "department": department.name,
                "date": str(target_date_obj),
                "is_on_leave": True,
                "is_off_duty": False,
                "status": "ON_LEAVE",
                "opd_fee": doctor.opd_fees or 500,
                "leave_reason": leave_row.reason or "Approved Leave",
                "leave_period": f"{leave_row.start_date} to {leave_row.end_date}"
            }

        # 3. Check weekly shift schedule for that day of week (1=Mon, 7=Sun)
        day_of_week = target_date_obj.isoweekday()
        sched_stmt = select(DoctorSchedule).where(
            DoctorSchedule.doctor_id == doctor.id,
            DoctorSchedule.day_of_week == day_of_week
        )
        schedules = (await db.execute(sched_stmt)).scalars().all()

        if not schedules:
            return {
                "doctor_name": f"Dr. {doctor.first_name} {doctor.last_name}",
                "department": department.name,
                "date": str(target_date_obj),
                "is_on_leave": False,
                "is_off_duty": True,
                "status": "WEEKLY_OFF",
                "opd_fee": doctor.opd_fees or 500,
                "note": f"Doctor has no scheduled shifts on {target_date_obj.strftime('%A')} (Weekly Off)."
            }

        shift_timings = [f"{s.start_time.strftime('%I:%M %p')} - {s.end_time.strftime('%I:%M %p')}" for s in schedules]
        return {
            "doctor_name": f"Dr. {doctor.first_name} {doctor.last_name}",
            "department": department.name,
            "date": str(target_date_obj),
            "is_on_leave": False,
            "is_off_duty": False,
            "status": "ON_DUTY",
            "opd_fee": doctor.opd_fees or 500,
            "timings": ", ".join(shift_timings)
        }

    @staticmethod
    async def get_available_doctors_for_day(
        hospital_id: str,
        date_str: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """Finds all doctors who are scheduled and ON DUTY (not on leave) on a given date."""
        if not db or not hospital_id:
            return {"error": "Invalid session or tenant context"}

        target_date_obj = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else datetime.now().date()
        day_of_week = target_date_obj.isoweekday()

        doc_stmt = select(Doctor, Department).join(Department, Doctor.department_id == Department.id).where(
            Doctor.hospital_id == hospital_id,
            Doctor.is_active == True
        )
        all_docs = (await db.execute(doc_stmt)).all()

        available_list = []
        on_leave_list = []
        off_duty_list = []

        for doctor, department in all_docs:
            # Check leave
            leave_stmt = select(DoctorLeave).where(
                DoctorLeave.doctor_id == doctor.id,
                DoctorLeave.status == "APPROVED",
                DoctorLeave.start_date <= target_date_obj,
                DoctorLeave.end_date >= target_date_obj
            )
            is_leave = (await db.execute(leave_stmt)).scalar_one_or_none()
            if is_leave:
                on_leave_list.append(f"Dr. {doctor.first_name} {doctor.last_name} ({department.name} - On Leave)")
                continue

            # Check shifts
            sched_stmt = select(DoctorSchedule).where(
                DoctorSchedule.doctor_id == doctor.id,
                DoctorSchedule.day_of_week == day_of_week
            )
            schedules = (await db.execute(sched_stmt)).scalars().all()
            if not schedules:
                off_duty_list.append(f"Dr. {doctor.first_name} {doctor.last_name} ({department.name} - Day Off)")
                continue

            shift_strs = [f"{s.start_time.strftime('%I:%M %p')} - {s.end_time.strftime('%I:%M %p')}" for s in schedules]
            available_list.append({
                "doctor_name": f"Dr. {doctor.first_name} {doctor.last_name}",
                "department": department.name,
                "opd_fee": doctor.opd_fees or 500,
                "timings": ", ".join(shift_strs)
            })

        return {
            "date": str(target_date_obj),
            "day_name": target_date_obj.strftime("%A"),
            "total_available_doctors": len(available_list),
            "available_doctors": available_list,
            "on_leave_doctors": on_leave_list,
            "off_duty_doctors": off_duty_list
        }

    @staticmethod
    async def get_single_doctor_slots(
        hospital_id: str,
        doctor_name_or_dept: str,
        date_str: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """Generates real-time slot availability for one doctor on a target date."""
        if not db or not hospital_id:
            return {"error": "Invalid session or tenant context"}

        clean_name = doctor_name_or_dept.lower().replace("dr.", "").replace("dr ", "").replace("doctor", "").strip()

        stmt = select(Doctor, Department).join(Department, Doctor.department_id == Department.id).where(
            Doctor.hospital_id == hospital_id,
            Doctor.is_active == True,
            CopilotTools._build_doctor_search_conditions(clean_name)
        )
        res = (await db.execute(stmt)).first()
        if not res:
            return {"error": f"No active doctor found matching '{doctor_name_or_dept}' in your hospital."}

        doctor, department = res
        target_date = date_str or datetime.now().strftime("%Y-%m-%d")

        sched_engine = SchedulingEngine(db)
        slots = await sched_engine.get_available_slots(doctor.id, target_date)
        formatted_slots = [
            s.start_time.strftime("%I:%M %p") if hasattr(s, "start_time") else str(s)
            for s in slots
        ]

        return {
            "doctor_name": f"Dr. {doctor.first_name} {doctor.last_name}",
            "department": department.name,
            "opd_fee": doctor.opd_fees or 500,
            "date": target_date,
            "total_open_slots": len(formatted_slots),
            "available_slots": formatted_slots[:15],
            "status": "SLOTS_AVAILABLE" if formatted_slots else "NO_SLOTS_AVAILABLE"
        }

    @staticmethod
    async def get_doctor_leave_history(
        hospital_id: str,
        doctor_name: Optional[str] = None,
        user_id: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """Retrieves past, approved, and pending leave history for a doctor."""
        if not db or not hospital_id:
            return {"error": "Invalid session or tenant context"}

        doc_stmt = select(Doctor).where(Doctor.hospital_id == hospital_id, Doctor.is_active == True)
        if doctor_name:
            clean_name = doctor_name.lower().replace("dr.", "").replace("dr ", "").replace("doctor", "").strip()
            doc_stmt = doc_stmt.where(CopilotTools._build_doctor_search_conditions(clean_name))

        doc = (await db.execute(doc_stmt)).scalars().first()
        if not doc:
            return {"error": f"Doctor '{doctor_name or 'current user'}' not found in this hospital."}

        leave_stmt = select(DoctorLeave).where(DoctorLeave.doctor_id == doc.id).order_by(DoctorLeave.start_date.desc())
        leaves = (await db.execute(leave_stmt)).scalars().all()

        return {
            "doctor_name": f"Dr. {doc.first_name} {doc.last_name}",
            "total_leave_records": len(leaves),
            "leaves": [
                {
                    "leave_id": l.id,
                    "start_date": str(l.start_date),
                    "end_date": str(l.end_date),
                    "reason": l.reason or "Personal",
                    "status": l.status
                }
                for l in leaves
            ]
        }

    @staticmethod
    async def update_doctor_leave_status(
        hospital_id: str,
        leave_id: str,
        action: str,  # "APPROVE" or "REJECT"
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """Hospital Admin action to approve or reject a pending doctor leave request."""
        if not db or not hospital_id:
            return {"error": "Invalid session or tenant context"}

        stmt = select(DoctorLeave, Doctor).join(Doctor, DoctorLeave.doctor_id == Doctor.id).where(
            DoctorLeave.id == leave_id,
            Doctor.hospital_id == hospital_id
        )
        res = (await db.execute(stmt)).first()
        if not res:
            return {"error": f"Leave request with ID '{leave_id}' not found in this hospital."}

        leave, doc = res
        new_status = "APPROVED" if action.upper() == "APPROVE" else "REJECTED"
        leave.status = new_status
        await db.commit()

        return {
            "success": True,
            "leave_id": leave_id,
            "doctor_name": f"Dr. {doc.first_name} {doc.last_name}",
            "period": f"{leave.start_date} to {leave.end_date}",
            "new_status": new_status,
            "message": f"Doctor leave request has been marked as {new_status}."
        }

    # ==========================================
    # DOMAIN 2: APPOINTMENTS, QUEUE & PATIENTS
    # ==========================================

    @staticmethod
    async def get_queue_statistics(
        hospital_id: str,
        date_str: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """Returns full appointment breakdown (Total, Completed, Waiting, Missed) for any date."""
        if not db or not hospital_id:
            return {"error": "Invalid session or tenant context"}

        target_date = date_str or datetime.now().strftime("%Y-%m-%d")

        stmt = select(
            func.count(Appointment.id).label("total"),
            func.sum(case((Appointment.status.in_(["COMPLETED", "CONSULTATION_FINISHED"]), 1), else_=0)).label("completed"),
            func.sum(case((Appointment.status.in_(["WAITING", "CONFIRMED", "SCHEDULED"]), 1), else_=0)).label("waiting"),
            func.sum(case((Appointment.status.in_(["MISSED", "CANCELLED"]), 1), else_=0)).label("missed")
        ).where(
            Appointment.hospital_id == hospital_id,
            func.date(Appointment.appointment_datetime) == target_date
        )
        row = (await db.execute(stmt)).first()

        # Doctor breakdown
        doc_stmt = select(
            Doctor.first_name, Doctor.last_name, Department.name.label("dept"),
            func.count(Appointment.id).label("cnt")
        ).join(Department, Doctor.department_id == Department.id)\
         .outerjoin(Appointment, (Appointment.doctor_id == Doctor.id) & (func.date(Appointment.appointment_datetime) == target_date))\
         .where(Doctor.hospital_id == hospital_id, Doctor.is_active == True)\
         .group_by(Doctor.id, Doctor.first_name, Doctor.last_name, Department.name)

        doc_rows = (await db.execute(doc_stmt)).all()
        breakdown = [
            {"doctor": f"Dr. {r.first_name} {r.last_name}", "department": r.dept, "booked_count": r.cnt or 0}
            for r in doc_rows
        ]

        return {
            "date": target_date,
            "total_appointments": row.total or 0 if row else 0,
            "completed": int(row.completed or 0) if row else 0,
            "waiting": int(row.waiting or 0) if row else 0,
            "missed_or_cancelled": int(row.missed or 0) if row else 0,
            "doctor_breakdown": breakdown
        }

    @staticmethod
    async def get_doctor_live_queue(
        hospital_id: str,
        doctor_name: Optional[str] = None,
        date_str: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """Provides Doctor with today's live waiting queue, patient tokens, and intake chief complaints."""
        if not db or not hospital_id:
            return {"error": "Invalid session or tenant context"}

        target_date = date_str or datetime.now().strftime("%Y-%m-%d")

        stmt = select(Appointment, Patient, Doctor, PatientIntake).join(
            Patient, Appointment.patient_id == Patient.id
        ).join(
            Doctor, Appointment.doctor_id == Doctor.id
        ).outerjoin(
            PatientIntake, PatientIntake.appointment_id == Appointment.id
        ).where(
            Appointment.hospital_id == hospital_id,
            func.date(Appointment.appointment_datetime) == target_date
        )

        if doctor_name:
            clean_name = doctor_name.lower().replace("dr.", "").replace("dr ", "").replace("doctor", "").strip()
            stmt = stmt.where(CopilotTools._build_doctor_search_conditions(clean_name))

        stmt = stmt.order_by(Appointment.appointment_datetime.asc())
        rows = (await db.execute(stmt)).all()

        queue_list = []
        for idx, (appt, pat, doc, intake) in enumerate(rows, start=1):
            queue_list.append({
                "token_number": idx,
                "appointment_id": appt.id,
                "patient_name": f"{pat.first_name} {pat.last_name}".strip(),
                "mobile": pat.phone,
                "doctor_name": f"Dr. {doc.first_name} {doc.last_name}",
                "time": appt.appointment_datetime.strftime("%I:%M %p") if appt.appointment_datetime else "N/A",
                "status": appt.status,
                "chief_complaint": appt.reason or (intake.report_details if intake else "General Checkup"),
                "current_medicines": intake.current_medicines if intake else None
            })

        return {
            "date": target_date,
            "total_in_queue": len(queue_list),
            "waiting_count": sum(1 for q in queue_list if q["status"] in ["WAITING", "SCHEDULED", "CONFIRMED"]),
            "completed_count": sum(1 for q in queue_list if q["status"] in ["COMPLETED", "CONSULTATION_FINISHED"]),
            "patients": queue_list
        }

    @staticmethod
    async def search_patient_appointment_status(
        hospital_id: str,
        query: str,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """Searches patient records and active appointment status by name, phone, or appointment ID."""
        if not db or not hospital_id:
            return {"error": "Invalid session or tenant context"}

        clean_q = query.strip()
        patient_conds = [
            Patient.phone.ilike(f"%{clean_q}%"),
            Patient.first_name.ilike(f"%{clean_q}%"),
            Patient.last_name.ilike(f"%{clean_q}%"),
            func.concat(Patient.first_name, " ", Patient.last_name).ilike(f"%{clean_q}%"),
            Appointment.id.ilike(f"%{clean_q}%")
        ]
        tokens = [t.strip() for t in clean_q.split() if len(t.strip()) >= 1]
        for tok in tokens:
            patient_conds.append(Patient.first_name.ilike(f"%{tok}%"))
            patient_conds.append(Patient.last_name.ilike(f"%{tok}%"))

        stmt = select(Appointment, Patient, Doctor, Department).join(
            Patient, Appointment.patient_id == Patient.id
        ).join(
            Doctor, Appointment.doctor_id == Doctor.id
        ).join(
            Department, Doctor.department_id == Department.id
        ).where(
            Appointment.hospital_id == hospital_id,
            or_(*patient_conds)
        ).order_by(Appointment.appointment_datetime.desc()).limit(5)

        rows = (await db.execute(stmt)).all()
        if not rows:
            return {"message": f"No patient records found matching '{query}' in your hospital."}

        results = []
        for appt, pat, doc, dept in rows:
            results.append({
                "appointment_id": appt.id,
                "patient_name": f"{pat.first_name} {pat.last_name}".strip(),
                "mobile": pat.phone,
                "doctor_name": f"Dr. {doc.first_name} {doc.last_name}",
                "department": dept.name,
                "appointment_time": appt.appointment_datetime.strftime("%Y-%m-%d %I:%M %p") if appt.appointment_datetime else "N/A",
                "status": appt.status,
                "payment_status": appt.payment_status,
                "reason": appt.reason or "General Consultation"
            })

        return {"matches_found": len(results), "patients": results}

    @staticmethod
    async def get_missed_and_cancelled_list(
        hospital_id: str,
        date_str: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """Fetches list of patients who missed or cancelled their visits with reasons."""
        if not db or not hospital_id:
            return {"error": "Invalid session or tenant context"}

        target_date = date_str or datetime.now().strftime("%Y-%m-%d")
        stmt = select(Appointment, Patient, Doctor).join(
            Patient, Appointment.patient_id == Patient.id
        ).join(
            Doctor, Appointment.doctor_id == Doctor.id
        ).where(
            Appointment.hospital_id == hospital_id,
            func.date(Appointment.appointment_datetime) == target_date,
            Appointment.status.in_(["MISSED", "CANCELLED"])
        )
        rows = (await db.execute(stmt)).all()
        missed_list = [
            {
                "patient_name": f"{p.first_name} {p.last_name}".strip(),
                "phone": p.phone,
                "doctor": f"Dr. {d.first_name} {d.last_name}",
                "time": a.appointment_datetime.strftime("%I:%M %p") if a.appointment_datetime else "N/A",
                "status": a.status,
                "problem_reason": a.reason or "General Consultation"
            }
            for a, p, d in rows
        ]
        return {"date": target_date, "total_missed_or_cancelled": len(missed_list), "records": missed_list}

    @staticmethod
    async def book_walkin_appointment(
        hospital_id: str,
        doctor_name_or_dept: str,
        patient_name: str,
        phone: str,
        time_slot: str,
        date_str: Optional[str] = None,
        reason: Optional[str] = "Consultation",
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """Directly books an OPD appointment for a patient with a doctor."""
        if not db or not hospital_id:
            return {"error": "Invalid session or tenant context"}

        # 1. Lookup Doctor
        clean_name = doctor_name_or_dept.lower().replace("dr.", "").replace("dr ", "").replace("doctor", "").strip()

        stmt = select(Doctor, Department).join(Department, Doctor.department_id == Department.id).where(
            Doctor.hospital_id == hospital_id,
            Doctor.is_active == True,
            CopilotTools._build_doctor_search_conditions(clean_name)
        )
        res = (await db.execute(stmt)).first()
        if not res:
            return {"error": f"No active doctor found matching '{doctor_name_or_dept}' in this hospital."}

        doctor, department = res

        # 2. Lookup or Create Patient
        clean_phone = phone.strip().replace(" ", "").replace("-", "")
        if not clean_phone.startswith("+"):
            clean_phone = "+91" + clean_phone.lstrip("0")

        pat_stmt = select(Patient).where(Patient.hospital_id == hospital_id, Patient.phone == clean_phone)
        patient = (await db.execute(pat_stmt)).scalar_one_or_none()
        if not patient:
            name_parts = patient_name.strip().split(" ", 1)
            first_n = name_parts[0]
            last_n = name_parts[1] if len(name_parts) > 1 else ""
            patient = Patient(
                id=str(uuid.uuid4()),
                hospital_id=hospital_id,
                first_name=first_n,
                last_name=last_n,
                phone=clean_phone,
                date_of_birth=date(1990, 1, 1)
            )
            db.add(patient)
            await db.flush()

        # 3. Parse DateTime
        target_date = date_str or datetime.now().strftime("%Y-%m-%d")
        
        try:
            time_obj = None
            for fmt in ["%I:%M %p", "%I:%M%p", "%H:%M", "%I %p"]:
                try:
                    time_obj = datetime.strptime(time_slot.strip(), fmt).time()
                    break
                except ValueError:
                    pass
            if not time_obj:
                time_obj = time(10, 0)
        except Exception:
            time_obj = time(10, 0)

        appt_dt = datetime.combine(datetime.strptime(target_date, "%Y-%m-%d").date(), time_obj)

        # 4. Book appointment using existing AppointmentEngine
        engine = AppointmentEngine(db)
        booking_res = await engine.book_appointment(
            hospital_id=hospital_id,
            patient_id=patient.id,
            doctor_id=doctor.id,
            appointment_datetime=appt_dt,
            reason=reason or "OPD Consultation",
            source="COPILOT"
        )
        
        if booking_res.get("code") == "BOOKING_SUCCESS":
            return {
                "success": True,
                "message": f"Appointment successfully booked for {patient_name} with Dr. {doctor.first_name} {doctor.last_name} on {target_date} at {time_slot}.",
                "appointment_id": booking_res.get("appointment_id"),
                "doctor_name": f"Dr. {doctor.first_name} {doctor.last_name}",
                "department": department.name,
                "opd_fee": doctor.opd_fees or 500,
                "date": target_date,
                "time": time_slot
            }
        else:
            return {
                "success": False,
                "code": booking_res.get("code"),
                "error": booking_res.get("message", "Booking failed due to slot conflict or rules.")
            }

    @staticmethod
    async def reschedule_existing_appointment(
        hospital_id: str,
        query: str,  # patient phone or appointment_id
        new_date_str: str,
        new_time_slot: str,
        reason: Optional[str] = "Patient requested reschedule",
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """Reschedules an existing active appointment to a new date and time."""
        if not db or not hospital_id:
            return {"error": "Invalid session or tenant context"}

        clean_q = query.strip()
        stmt = select(Appointment, Patient, Doctor).join(
            Patient, Appointment.patient_id == Patient.id
        ).join(
            Doctor, Appointment.doctor_id == Doctor.id
        ).where(
            Appointment.hospital_id == hospital_id,
            or_(Appointment.id == clean_q, Patient.phone.ilike(f"%{clean_q}%")),
            Appointment.status.notin_(["CANCELLED", "COMPLETED"])
        ).order_by(Appointment.appointment_datetime.desc())

        res = (await db.execute(stmt)).first()
        if not res:
            return {"error": f"No active appointment found for '{query}' to reschedule."}

        appt, pat, doc = res

        time_obj = None
        for fmt in ["%I:%M %p", "%I:%M%p", "%H:%M", "%I %p"]:
            try:
                time_obj = datetime.strptime(new_time_slot.strip(), fmt).time()
                break
            except ValueError:
                pass
        if not time_obj:
            time_obj = time(10, 0)

        new_dt = datetime.combine(datetime.strptime(new_date_str, "%Y-%m-%d").date(), time_obj)

        engine = AppointmentEngine(db)
        r_res = await engine.reschedule_appointment(
            appointment_id=appt.id,
            new_datetime=new_dt,
            hospital_id=hospital_id,
            reason=reason
        )

        if r_res.get("code") == "RESCHEDULE_SUCCESS":
            return {
                "success": True,
                "message": f"Appointment for {pat.first_name} {pat.last_name} with Dr. {doc.first_name} {doc.last_name} rescheduled to {new_date_str} at {new_time_slot}.",
                "appointment_id": appt.id,
                "new_date": new_date_str,
                "new_time": new_time_slot
            }
        return {"success": False, "error": r_res.get("message", "Reschedule failed.")}

    @staticmethod
    async def cancel_existing_appointment(
        hospital_id: str,
        query: str,  # appointment_id or patient phone
        reason: Optional[str] = "Cancelled via Copilot",
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """Cancels an active appointment and frees the doctor's calendar slot."""
        if not db or not hospital_id:
            return {"error": "Invalid session or tenant context"}

        clean_q = query.strip()
        stmt = select(Appointment, Patient, Doctor).join(
            Patient, Appointment.patient_id == Patient.id
        ).join(
            Doctor, Appointment.doctor_id == Doctor.id
        ).where(
            Appointment.hospital_id == hospital_id,
            or_(Appointment.id == clean_q, Patient.phone.ilike(f"%{clean_q}%")),
            Appointment.status.notin_(["CANCELLED", "COMPLETED"])
        ).order_by(Appointment.appointment_datetime.desc())

        res = (await db.execute(stmt)).first()
        if not res:
            return {"error": f"No active appointment found for '{query}' to cancel."}

        appt, pat, doc = res
        engine = AppointmentEngine(db)
        c_res = await engine.cancel_appointment(appointment_id=appt.id, hospital_id=hospital_id, reason=reason)

        if c_res.get("code") == "CANCEL_SUCCESS":
            return {
                "success": True,
                "message": f"Appointment for {pat.first_name} {pat.last_name} with Dr. {doc.first_name} {doc.last_name} has been cancelled successfully.",
                "appointment_id": appt.id,
                "cancelled_time": str(appt.appointment_datetime)
            }
        return {"success": False, "error": c_res.get("message", "Cancellation failed.")}

    # ==========================================
    # DOMAIN 3: CLINICAL EMR, PRESCRIPTIONS & INTAKE
    # ==========================================

    @staticmethod
    async def search_clinical_emr_records(
        hospital_id: str,
        query: Optional[str] = None,
        date_str: Optional[str] = None,
        patient_name: Optional[str] = None,
        doctor_name: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """Searches past clinical records, prescriptions, symptoms, and intake details."""
        if not db or not hospital_id:
            return {"error": "Invalid session or tenant context"}

        stmt = select(
            Appointment, Patient, Doctor, Department, ConsultationNote, PatientIntake
        ).join(
            Patient, Appointment.patient_id == Patient.id
        ).join(
            Doctor, Appointment.doctor_id == Doctor.id
        ).join(
            Department, Doctor.department_id == Department.id
        ).outerjoin(
            ConsultationNote, ConsultationNote.appointment_id == Appointment.id
        ).outerjoin(
            PatientIntake, PatientIntake.appointment_id == Appointment.id
        ).where(
            Appointment.hospital_id == hospital_id
        )

        conditions = []
        if query:
            clean_q = query.strip()
            conditions.append(or_(
                Appointment.reason.ilike(f"%{clean_q}%"),
                ConsultationNote.clinical_notes.ilike(f"%{clean_q}%"),
                ConsultationNote.prescription.ilike(f"%{clean_q}%"),
                PatientIntake.report_details.ilike(f"%{clean_q}%"),
                PatientIntake.current_medicines.ilike(f"%{clean_q}%")
            ))

        if date_str:
            target_d = datetime.strptime(date_str, "%Y-%m-%d").date()
            conditions.append(func.date(Appointment.appointment_datetime) == target_d)

        if patient_name:
            pn = patient_name.strip()
            conditions.append(or_(
                Patient.first_name.ilike(f"%{pn}%"),
                Patient.last_name.ilike(f"%{pn}%"),
                func.concat(Patient.first_name, " ", Patient.last_name).ilike(f"%{pn}%")
            ))

        if doctor_name:
            dn = doctor_name.lower().replace("dr.", "").replace("dr ", "").replace("doctor", "").strip()
            conditions.append(CopilotTools._build_doctor_search_conditions(dn))

        if conditions:
            stmt = stmt.where(and_(*conditions))

        stmt = stmt.order_by(Appointment.appointment_datetime.desc()).limit(8)
        rows = (await db.execute(stmt)).all()

        if not rows:
            return {
                "records_found": 0,
                "message": f"No clinical or prescription records found matching your query."
            }

        results = []
        for appt, pat, doc, dept, note, intake in rows:
            results.append({
                "appointment_id": appt.id,
                "patient_name": f"{pat.first_name} {pat.last_name}".strip(),
                "mobile": pat.phone,
                "doctor_name": f"Dr. {doc.first_name} {doc.last_name}",
                "department": dept.name,
                "visit_date": appt.appointment_datetime.strftime("%Y-%m-%d %I:%M %p") if appt.appointment_datetime else "N/A",
                "chief_complaint": appt.reason or "General Consultation",
                "clinical_diagnosis": note.clinical_notes if note and note.clinical_notes else "Not documented",
                "prescription": note.prescription if note and note.prescription else "No digital prescription attached",
                "past_medicines": intake.current_medicines if intake and intake.current_medicines else None,
                "reports_summary": intake.report_details if intake and intake.report_details else None
            })

        return {"records_found": len(results), "records": results}

    @staticmethod
    async def record_clinical_consultation(
        hospital_id: str,
        appointment_id: str,
        clinical_notes: str,
        prescription: str,
        follow_up_date_str: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """Doctor action to write clinical notes, digital Rx prescription, and mark appointment COMPLETED."""
        if not db or not hospital_id:
            return {"error": "Invalid session or tenant context"}

        stmt = select(Appointment, Patient, Doctor).join(
            Patient, Appointment.patient_id == Patient.id
        ).join(
            Doctor, Appointment.doctor_id == Doctor.id
        ).where(
            Appointment.id == appointment_id,
            Appointment.hospital_id == hospital_id
        )
        res = (await db.execute(stmt)).first()
        if not res:
            return {"error": f"Appointment with ID '{appointment_id}' not found."}

        appt, pat, doc = res

        note_stmt = select(ConsultationNote).where(ConsultationNote.appointment_id == appt.id)
        note = (await db.execute(note_stmt)).scalar_one_or_none()

        fu_date = datetime.strptime(follow_up_date_str, "%Y-%m-%d").date() if follow_up_date_str else None

        if note:
            note.clinical_notes = clinical_notes
            note.prescription = prescription
            note.follow_up_date = fu_date
        else:
            note = ConsultationNote(
                id=str(uuid.uuid4()),
                appointment_id=appt.id,
                patient_id=pat.id,
                doctor_id=doc.id,
                clinical_notes=clinical_notes,
                prescription=prescription,
                follow_up_date=fu_date
            )
            db.add(note)

        appt.status = "COMPLETED"
        appt.consultation_status = "COMPLETED"
        await db.commit()

        return {
            "success": True,
            "message": f"Consultation notes and digital prescription saved for patient {pat.first_name} {pat.last_name}.",
            "appointment_id": appt.id,
            "patient_name": f"{pat.first_name} {pat.last_name}",
            "doctor_name": f"Dr. {doc.first_name} {doc.last_name}",
            "status": "COMPLETED",
            "prescription": prescription
        }

    # ==========================================
    # DOMAIN 4: FINANCIALS, BILLING & DIRECTORY
    # ==========================================

    @staticmethod
    async def get_revenue_and_dues(
        hospital_id: str,
        time_range: str = "today",
        role: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """Calculates revenue collected, cash vs online, and pending dues for today, week, month, or all time."""
        if not db:
            return {"error": "Invalid session or tenant context"}

        is_super_admin = (role and role.upper() in ["SUPER_ADMIN", "SUPERADMIN"]) or hospital_id in ["super_admin", "GLOBAL", "", None]

        now = datetime.now()
        stmt = select(
            func.count(Appointment.id).label("total_bookings"),
            func.sum(case((Appointment.payment_status == "PAID", 1), else_=0)).label("paid_count"),
            func.sum(case((Appointment.payment_status == "PENDING", 1), else_=0)).label("pending_count")
        )
        amt_stmt = select(
            func.sum(case((Appointment.payment_status == "PAID", Doctor.opd_fees), else_=0)).label("paid_amount"),
            func.sum(case((Appointment.payment_status == "PENDING", Doctor.opd_fees), else_=0)).label("pending_amount")
        ).select_from(Appointment).join(Doctor, Appointment.doctor_id == Doctor.id)

        if not is_super_admin and hospital_id:
            stmt = stmt.where(Appointment.hospital_id == hospital_id)
            amt_stmt = amt_stmt.where(Appointment.hospital_id == hospital_id)

        t_range_norm = (time_range or "today").lower().strip()
        if any(w in t_range_norm for w in ["all", "lifetime", "overall", "total"]):
            period_label = "All Time"
        elif any(w in t_range_norm for w in ["month", "mahine"]):
            stmt = stmt.where(
                func.extract("year", Appointment.appointment_datetime) == now.year,
                func.extract("month", Appointment.appointment_datetime) == now.month
            )
            amt_stmt = amt_stmt.where(
                func.extract("year", Appointment.appointment_datetime) == now.year,
                func.extract("month", Appointment.appointment_datetime) == now.month
            )
            period_label = "This Month"
        elif any(w in t_range_norm for w in ["week", "hafte"]):
            start_week = now.date() - timedelta(days=now.weekday())
            stmt = stmt.where(func.date(Appointment.appointment_datetime) >= start_week)
            amt_stmt = amt_stmt.where(func.date(Appointment.appointment_datetime) >= start_week)
            period_label = "This Week"
        else:
            stmt = stmt.where(func.date(Appointment.appointment_datetime) == now.strftime("%Y-%m-%d"))
            amt_stmt = amt_stmt.where(func.date(Appointment.appointment_datetime) == now.strftime("%Y-%m-%d"))
            period_label = "Today"

        row = (await db.execute(stmt)).first()
        amt_row = (await db.execute(amt_stmt)).first()

        paid_amt = int(amt_row.paid_amount or 0) if amt_row else 0
        pending_amt = int(amt_row.pending_amount or 0) if amt_row else 0

        return {
            "hospital_id": hospital_id,
            "period": period_label,
            "total_appointments": row.total_bookings or 0 if row else 0,
            "paid_transactions": int(row.paid_count or 0) if row else 0,
            "pending_collection_count": int(row.pending_count or 0) if row else 0,
            "total_collected_formatted": f"₹{paid_amt:,}",
            "pending_dues_formatted": f"₹{pending_amt:,}"
        }

    @staticmethod
    async def get_comprehensive_doctor_analytics(
        hospital_id: str,
        time_range: str = "all",
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """Provides a comprehensive chart/matrix of all doctors: bookings, cancellations, working days, and revenue."""
        if not db or not hospital_id:
            return {"error": "Invalid session or tenant context"}

        doc_stmt = select(Doctor, Department).join(Department, Doctor.department_id == Department.id).where(
            Doctor.hospital_id == hospital_id,
            Doctor.is_active == True
        )
        doctors = (await db.execute(doc_stmt)).all()

        analytics = []
        for doc, dept in doctors:
            sched_stmt = select(func.count(func.distinct(DoctorSchedule.day_of_week))).where(
                DoctorSchedule.doctor_id == doc.id
            )
            working_days_cnt = (await db.execute(sched_stmt)).scalar() or 0

            appt_stmt = select(
                func.count(Appointment.id).label("total_booked"),
                func.sum(case((Appointment.status.in_(["COMPLETED", "CONSULTATION_FINISHED"]), 1), else_=0)).label("completed"),
                func.sum(case((Appointment.status.in_(["CANCELLED", "MISSED"]), 1), else_=0)).label("cancelled"),
                func.sum(case((Appointment.payment_status == "PAID", 1), else_=0)).label("paid")
            ).where(Appointment.doctor_id == doc.id)

            if time_range == "month":
                now = datetime.now()
                appt_stmt = appt_stmt.where(
                    func.extract("year", Appointment.appointment_datetime) == now.year,
                    func.extract("month", Appointment.appointment_datetime) == now.month
                )

            row = (await db.execute(appt_stmt)).first()
            total_b = row.total_booked or 0 if row else 0
            comp = int(row.completed or 0) if row else 0
            canc = int(row.cancelled or 0) if row else 0
            paid_cnt = int(row.paid or 0) if row else 0
            fee = doc.opd_fees or 500
            rev = paid_cnt * fee

            analytics.append({
                "doctor_name": f"Dr. {doc.first_name} {doc.last_name}",
                "department": dept.name,
                "opd_fee": fee,
                "weekly_working_days": working_days_cnt or 6,
                "total_appointments": total_b,
                "completed": comp,
                "cancelled_or_missed": canc,
                "paid_appointments": paid_cnt,
                "total_revenue_generated": f"₹{rev:,}"
            })

        return {
            "hospital_id": hospital_id,
            "period": time_range.capitalize(),
            "total_active_doctors": len(analytics),
            "doctor_matrix": analytics
        }

    @staticmethod
    async def get_hospital_department_directory(
        hospital_id: str,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """Returns all active departments, doctor counts, and specialist names."""
        if not db or not hospital_id:
            return {"error": "Invalid session or tenant context"}

        stmt = select(Department.name, func.count(Doctor.id).label("doc_count")).join(
            Doctor, Doctor.department_id == Department.id
        ).where(
            Department.hospital_id == hospital_id,
            Doctor.is_active == True
        ).group_by(Department.name)

        rows = (await db.execute(stmt)).all()
        return {
            "hospital_id": hospital_id,
            "total_departments": len(rows),
            "departments": [{"department": r[0], "active_doctors": r[1]} for r in rows]
        }

    @staticmethod
    async def get_hospital_subscription_info(
        hospital_id: str,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """Retrieves hospital SaaS plan status, expiry date, and doctor capacity."""
        if not db or not hospital_id:
            return {"error": "Invalid session or tenant context"}

        stmt = select(Hospital).where(Hospital.id == hospital_id)
        h = (await db.execute(stmt)).scalar_one_or_none()
        if not h:
            return {"error": "Hospital not found"}

        doc_cnt = (await db.execute(select(func.count(Doctor.id)).where(Doctor.hospital_id == hospital_id, Doctor.is_active == True))).scalar() or 0

        days_left = None
        if h.plan_expires_at:
            days_left = (h.plan_expires_at.date() - datetime.now().date()).days

        return {
            "hospital_name": h.name,
            "subscription_plan": h.subscription_plan or "ENTERPRISE",
            "plan_status": h.plan_status or "ACTIVE",
            "expires_at": str(h.plan_expires_at.date()) if h.plan_expires_at else "No expiration configured",
            "days_remaining": days_left if days_left is not None else 365,
            "active_doctors": doc_cnt,
            "max_doctor_quota": h.max_doctors or 10,
            "ai_voice_enabled": h.ai_voice_enabled
        }

    # ==========================================
    # DOMAIN 5: SUPERADMIN PLATFORM CONTROL TOWER
    # ==========================================

    @staticmethod
    async def get_platform_control_tower_overview(
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """SuperAdmin platform overview: active hospitals, subscriptions, expiry timeline, and total platform revenue."""
        if not db:
            return {"error": "Invalid session"}

        from app.database.models.conversation import CallLog
        from app.database.models.control_tower import HospitalSubscriptionHistory

        hosp_stmt = select(Hospital).order_by(Hospital.created_at.desc())
        hospitals = (await db.execute(hosp_stmt)).scalars().all()

        fleet = []
        now = datetime.now().date()
        expiring_30_days = []
        total_saas_rev = 0.0
        total_calls_all = 0

        for h in hospitals:
            doc_cnt = (await db.execute(select(func.count(Doctor.id)).where(Doctor.hospital_id == h.id, Doctor.is_active == True))).scalar() or 0
            appt_cnt = (await db.execute(select(func.count(Appointment.id)).where(Appointment.hospital_id == h.id))).scalar() or 0

            # SaaS revenue from subscriptions
            sub_rev = (await db.execute(
                select(func.coalesce(func.sum(HospitalSubscriptionHistory.amount_paid), 0.0))
                .where(HospitalSubscriptionHistory.hospital_id == h.id)
            )).scalar() or 0.0
            sub_rev = float(sub_rev)
            total_saas_rev += sub_rev

            # Calls count
            calls_cnt = (await db.execute(
                select(func.count(CallLog.id)).where(CallLog.hospital_id == h.id)
            )).scalar() or 0
            total_calls_all += calls_cnt

            days_left = None
            if h.plan_expires_at:
                days_left = (h.plan_expires_at.date() - now).days
                if 0 <= days_left <= 30:
                    expiring_30_days.append({
                        "hospital_name": h.name.strip(),
                        "hospital_id": h.id,
                        "plan": h.subscription_plan or "STARTER",
                        "days_left": days_left,
                        "expires_at": str(h.plan_expires_at.date())
                    })

            fleet.append({
                "hospital_name": h.name.strip(),
                "hospital_id": h.id,
                "subscription_plan": h.subscription_plan or "ENTERPRISE",
                "active_doctors": doc_cnt,
                "total_appointments": appt_cnt,
                "saas_revenue": sub_rev,
                "saas_revenue_formatted": f"₹{sub_rev:,.0f}",
                "voice_calls_count": calls_cnt,
                "days_remaining": days_left if days_left is not None else "Active",
                "status": "ACTIVE" if h.is_active else "SUSPENDED"
            })

        sorted_by_rev = sorted(fleet, key=lambda x: x["saas_revenue"], reverse=True)
        top_hosp = sorted_by_rev[0] if sorted_by_rev else None

        return {
            "total_active_hospitals": len(fleet),
            "total_platform_saas_revenue": total_saas_rev,
            "total_platform_saas_revenue_formatted": f"₹{total_saas_rev:,.0f}",
            "total_platform_voice_calls": total_calls_all,
            "top_revenue_hospital": top_hosp["hospital_name"] if top_hosp else "N/A",
            "top_revenue_amount": top_hosp["saas_revenue_formatted"] if top_hosp else "₹0",
            "hospitals_fleet": fleet,
            "expiring_soon_count": len(expiring_30_days),
            "expiring_hospitals": expiring_30_days
        }

    @staticmethod
    async def get_specific_hospital_metrics(
        hospital_name_or_id: str,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """SuperAdmin cross-hospital drilldown for metrics, doctor counts, and bookings."""
        if not db or not hospital_name_or_id:
            return {"error": "Please provide a hospital name or ID."}

        h_id = await CopilotTools.resolve_hospital_by_name(hospital_name_or_id, db)
        if not h_id:
            return {"error": f"No hospital found matching '{hospital_name_or_id}'."}

        stmt = select(Hospital).where(Hospital.id == h_id)
        h = (await db.execute(stmt)).scalar_one()

        rev_data = await CopilotTools.get_revenue_and_dues(hospital_id=h_id, time_range="month", db=db)
        doc_data = await CopilotTools.get_comprehensive_doctor_analytics(hospital_id=h_id, time_range="all", db=db)

        return {
            "hospital_name": h.name,
            "hospital_id": h.id,
            "slug": h.slug,
            "subscription_plan": h.subscription_plan,
            "total_doctors": doc_data.get("total_active_doctors", 0),
            "monthly_revenue": rev_data.get("total_collected_formatted", "₹0"),
            "monthly_appointments": rev_data.get("total_appointments", 0),
            "doctor_roster": doc_data.get("doctor_matrix", [])
        }

    # ==========================================
    # DOMAIN 6: PATIENT PORTAL
    # ==========================================

    @staticmethod
    async def get_my_patient_appointments(
        phone: str,
        hospital_id: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """Retrieves upcoming and past appointments for a patient by phone number."""
        if not db or not phone:
            return {"error": "Patient phone number required."}

        clean_p = phone.strip().replace(" ", "").replace("-", "")
        if not clean_p.startswith("+"):
            clean_p = "+91" + clean_p.lstrip("0")

        stmt = select(Appointment, Patient, Doctor, Department).join(
            Patient, Appointment.patient_id == Patient.id
        ).join(
            Doctor, Appointment.doctor_id == Doctor.id
        ).join(
            Department, Doctor.department_id == Department.id
        ).where(
            Patient.phone == clean_p
        )

        if hospital_id:
            stmt = stmt.where(Appointment.hospital_id == hospital_id)

        stmt = stmt.order_by(Appointment.appointment_datetime.desc()).limit(5)
        rows = (await db.execute(stmt)).all()

        if not rows:
            return {"message": f"No appointments found for phone number '{phone}'."}

        results = []
        for appt, pat, doc, dept in rows:
            results.append({
                "appointment_id": appt.id,
                "doctor_name": f"Dr. {doc.first_name} {doc.last_name}",
                "department": dept.name,
                "date_time": appt.appointment_datetime.strftime("%Y-%m-%d %I:%M %p") if appt.appointment_datetime else "N/A",
                "status": appt.status,
                "payment_status": appt.payment_status,
                "opd_fee": doc.opd_fees or 500
            })

        return {
            "patient_name": f"{rows[0][1].first_name} {rows[0][1].last_name}".strip(),
            "phone": clean_p,
            "total_bookings": len(results),
            "appointments": results
        }

    # ==========================================
    # DOMAIN 7: SUPERADMIN OBSERVABILITY & AUDIT
    # ==========================================

    @staticmethod
    async def get_platform_revenue_analytics(
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """SuperAdmin platform MRR, SaaS subscription revenue, and plan distribution."""
        if not db:
            return {"error": "Invalid session"}
        from app.database.models.control_tower import HospitalSubscriptionHistory

        hist_stmt = select(HospitalSubscriptionHistory)
        records = (await db.execute(hist_stmt)).scalars().all()

        plan_counts = {}
        total_saas = 0.0
        for r in records:
            p = r.plan_name or "STARTER"
            plan_counts[p] = plan_counts.get(p, 0) + 1
            total_saas += float(r.amount_paid or 0.0)

        overview = await CopilotTools.get_platform_control_tower_overview(db=db)
        return {
            "total_platform_saas_revenue": f"₹{total_saas:,.0f}",
            "top_revenue_hospital": overview.get("top_revenue_hospital", "N/A"),
            "top_revenue_amount": overview.get("top_revenue_amount", "₹0"),
            "total_transactions": len(records),
            "plan_distribution": plan_counts,
            "hospitals_breakdown": overview.get("hospitals_fleet", [])
        }

    @staticmethod
    async def get_platform_voice_telemetry(
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """SuperAdmin platform AI voice call telemetry, volume, and hospital breakdown."""
        if not db:
            return {"error": "Invalid session"}
        from app.database.models.conversation import CallLog

        total_calls = (await db.execute(select(func.count(CallLog.id)))).scalar() or 0
        now_date = datetime.now().date()
        today_calls = (await db.execute(select(func.count(CallLog.id)).where(func.date(CallLog.created_at) == now_date))).scalar() or 0

        overview = await CopilotTools.get_platform_control_tower_overview(db=db)
        hosp_breakdown = [
            {"hospital_name": h.get("hospital_name"), "calls_count": h.get("voice_calls_count", 0)}
            for h in overview.get("hospitals_fleet", [])
        ]
        return {
            "total_calls_today": today_calls,
            "total_calls_all_time": total_calls,
            "hospital_breakdown": hosp_breakdown
        }

    @staticmethod
    async def get_platform_error_telemetry(
        severity: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """SuperAdmin platform error streams and failure logs by service."""
        if not db:
            return {"error": "Invalid session"}
        from app.database.models.control_tower import TenantErrorLog

        stmt = select(TenantErrorLog).order_by(TenantErrorLog.occurred_at.desc()).limit(15)
        if severity:
            stmt = stmt.where(TenantErrorLog.severity == severity.upper())

        errors = (await db.execute(stmt)).scalars().all()
        err_list = []
        for e in errors:
            err_list.append({
                "service": e.service_name,
                "severity": e.severity,
                "error_code": e.error_code,
                "error_message": e.error_message,
                "occurred_at": e.occurred_at.strftime("%Y-%m-%d %I:%M %p") if e.occurred_at else "N/A"
            })
        return {
            "total_errors_reported": len(err_list),
            "errors": err_list
        }

    @staticmethod
    async def get_platform_audit_trail(
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """SuperAdmin platform security and configuration audit trail."""
        if not db:
            return {"error": "Invalid session"}
        from app.database.models.control_tower import PlatformAuditLog

        stmt = select(PlatformAuditLog).order_by(PlatformAuditLog.created_at.desc()).limit(15)
        audits = (await db.execute(stmt)).scalars().all()
        audit_list = []
        for a in audits:
            audit_list.append({
                "actor": a.actor_username,
                "role": a.actor_role,
                "action": a.action,
                "resource": a.resource_type,
                "status": a.status,
                "timestamp": a.created_at.strftime("%Y-%m-%d %I:%M %p") if a.created_at else "N/A"
            })
        return {
            "total_audits": len(audit_list),
            "audits": audit_list
        }

    # ==========================================
    # DOMAIN 8: EXTENDED OPD, CLINICAL & DESK
    # ==========================================

    @staticmethod
    async def apply_doctor_leave(
        hospital_id: str,
        user_id: Optional[str] = None,
        doctor_name: Optional[str] = None,
        start_date_str: str = "",
        end_date_str: str = "",
        reason: str = "Personal Leave",
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """Doctor applies for personal leave."""
        if not db or not hospital_id:
            return {"error": "Invalid session"}

        doctor = None
        if doctor_name:
            clean_name = doctor_name.lower().replace("dr.", "").replace("dr ", "").replace("doctor", "").strip()
            doctor = (await db.execute(select(Doctor).where(Doctor.hospital_id == hospital_id, CopilotTools._build_doctor_search_conditions(clean_name)))).scalars().first()
        elif user_id:
            doctor = (await db.execute(select(Doctor).where(Doctor.hospital_id == hospital_id, or_(Doctor.id == user_id, Doctor.email == user_id)))).scalars().first()

        if not doctor:
            doctor = (await db.execute(select(Doctor).where(Doctor.hospital_id == hospital_id, Doctor.is_active == True))).scalars().first()

        if not doctor:
            return {"error": "Could not identify doctor to apply leave."}

        try:
            s_date = datetime.strptime(start_date_str, "%Y-%m-%d").date() if start_date_str else datetime.now().date()
            e_date = datetime.strptime(end_date_str, "%Y-%m-%d").date() if end_date_str else s_date
        except Exception:
            return {"error": "Invalid date format. Use YYYY-MM-DD."}

        leave_id = str(uuid.uuid4())
        new_leave = DoctorLeave(
            id=leave_id,
            doctor_id=doctor.id,
            start_date=s_date,
            end_date=e_date,
            reason=reason,
            status="PENDING"
        )
        db.add(new_leave)
        await db.commit()

        return {
            "success": True,
            "leave_id": leave_id,
            "doctor_name": f"Dr. {doctor.first_name} {doctor.last_name}",
            "period": f"{s_date} to {e_date}",
            "reason": reason,
            "status": "PENDING"
        }

    @staticmethod
    async def update_patient_queue_status(
        hospital_id: str,
        appointment_id: str,
        new_status: str,
        changed_by: Optional[str] = "Receptionist",
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """Updates appointment status in live queue (e.g. IN_PROGRESS, COMPLETED, MISSED)."""
        if not db or not hospital_id or not appointment_id:
            return {"error": "Appointment ID required."}

        clean_status = new_status.upper().strip()
        valid_statuses = ["BOOKED", "CONFIRMED", "IN_PROGRESS", "COMPLETED", "CANCELLED", "MISSED"]
        if clean_status not in valid_statuses:
            return {"error": f"Invalid status '{new_status}'. Valid options: {', '.join(valid_statuses)}"}

        stmt = select(Appointment, Patient, Doctor).join(
            Patient, Appointment.patient_id == Patient.id
        ).join(
            Doctor, Appointment.doctor_id == Doctor.id
        ).where(
            Appointment.id == appointment_id,
            Appointment.hospital_id == hospital_id
        )
        row = (await db.execute(stmt)).first()
        if not row:
            return {"error": f"Appointment '{appointment_id}' not found."}

        appt, pat, doc = row
        old_status = appt.status
        appt.status = clean_status

        hist = AppointmentStatusHistory(
            id=str(uuid.uuid4()),
            appointment_id=appt.id,
            old_status=old_status,
            new_status=clean_status,
            changed_by=changed_by or "Copilot",
            change_reason=f"Status updated via Copilot to {clean_status}"
        )
        db.add(hist)
        await db.commit()

        return {
            "success": True,
            "appointment_id": appt.id,
            "patient_name": f"{pat.first_name} {pat.last_name}".strip(),
            "doctor_name": f"Dr. {doc.first_name} {doc.last_name}",
            "old_status": old_status,
            "new_status": clean_status,
            "token_number": appt.token_number
        }

    @staticmethod
    async def get_patient_profile_history(
        hospital_id: str,
        query: str,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """Fetches complete patient profile, contact info, and visit history by phone or name."""
        if not db or not hospital_id or not query:
            return {"error": "Patient name or phone query required."}

        clean_q = query.strip()
        stmt = select(Patient).where(
            Patient.hospital_id == hospital_id,
            or_(
                Patient.phone.ilike(f"%{clean_q}%"),
                func.concat(Patient.first_name, " ", Patient.last_name).ilike(f"%{clean_q}%"),
                Patient.id == clean_q
            )
        )
        pat = (await db.execute(stmt)).scalar_one_or_none()
        if not pat:
            return {"error": f"No patient found matching '{query}' in this hospital."}

        appts_stmt = select(Appointment, Doctor, Department).join(
            Doctor, Appointment.doctor_id == Doctor.id
        ).join(
            Department, Doctor.department_id == Department.id
        ).where(
            Appointment.patient_id == pat.id
        ).order_by(Appointment.appointment_datetime.desc()).limit(10)
        appts = (await db.execute(appts_stmt)).all()

        visits = []
        for a, d, dept in appts:
            visits.append({
                "date": a.appointment_datetime.strftime("%Y-%m-%d %I:%M %p") if a.appointment_datetime else "N/A",
                "doctor": f"Dr. {d.first_name} {d.last_name}",
                "department": dept.name,
                "status": a.status,
                "payment_status": a.payment_status
            })

        return {
            "patient_id": pat.id,
            "patient_name": f"{pat.first_name} {pat.last_name}".strip(),
            "phone": pat.phone,
            "gender": pat.gender or "N/A",
            "blood_group": pat.blood_group or "N/A",
            "emergency_contact": pat.emergency_contact or "N/A",
            "total_visits": len(visits),
            "visit_history": visits
        }

    @staticmethod
    async def get_daily_cash_register(
        hospital_id: str,
        date_str: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """Front desk daily cash collection, UPI split, and pending dues reconciliation."""
        if not db or not hospital_id:
            return {"error": "Invalid session"}

        t_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else datetime.now().date()

        stmt = select(Appointment, Doctor).join(
            Doctor, Appointment.doctor_id == Doctor.id
        ).where(
            Appointment.hospital_id == hospital_id,
            func.date(Appointment.appointment_datetime) == t_date
        )
        rows = (await db.execute(stmt)).all()

        cash_total = 0.0
        online_total = 0.0
        pending_total = 0.0
        paid_count = 0
        pending_count = 0

        for a, d in rows:
            fee = float(a.amount_paid or d.opd_fees or 500)
            if a.payment_status == "PAID":
                paid_count += 1
                if (a.payment_method or "").upper() == "CASH":
                    cash_total += fee
                else:
                    online_total += fee
            else:
                pending_count += 1
                pending_total += fee

        return {
            "date": str(t_date),
            "total_appointments": len(rows),
            "cash_collected": f"₹{cash_total:,.0f}",
            "online_collected": f"₹{online_total:,.0f}",
            "total_collected": f"₹{(cash_total + online_total):,.0f}",
            "pending_dues": f"₹{pending_total:,.0f}",
            "paid_transactions": paid_count,
            "pending_transactions": pending_count
        }

    @staticmethod
    async def mark_appointment_payment_paid(
        hospital_id: str,
        appointment_id: str,
        payment_method: str = "CASH",
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """Marks an appointment consultation fee as paid."""
        if not db or not hospital_id or not appointment_id:
            return {"error": "Appointment ID required."}

        stmt = select(Appointment, Doctor, Patient).join(
            Doctor, Appointment.doctor_id == Doctor.id
        ).join(
            Patient, Appointment.patient_id == Patient.id
        ).where(
            Appointment.id == appointment_id,
            Appointment.hospital_id == hospital_id
        )
        row = (await db.execute(stmt)).first()
        if not row:
            return {"error": f"Appointment '{appointment_id}' not found."}

        appt, doc, pat = row
        method_upper = payment_method.upper()
        if method_upper not in ["CASH", "ONLINE", "UPI", "CARD"]:
            method_upper = "CASH"

        fee = float(appt.amount_paid or doc.opd_fees or 500)
        appt.payment_status = "PAID"
        appt.payment_method = method_upper
        appt.amount_paid = fee

        pmt = Payment(
            id=str(uuid.uuid4()),
            appointment_id=appt.id,
            amount=fee,
            currency="INR",
            status="SUCCESS",
            method=method_upper
        )
        db.add(pmt)
        await db.commit()

        return {
            "success": True,
            "appointment_id": appt.id,
            "patient_name": f"{pat.first_name} {pat.last_name}".strip(),
            "doctor_name": f"Dr. {doc.first_name} {doc.last_name}",
            "amount_paid": f"₹{fee:,.0f}",
            "payment_method": method_upper,
            "status": "PAID"
        }

    @staticmethod
    async def get_doctor_daily_earnings(
        hospital_id: str,
        user_id: Optional[str] = None,
        doctor_name: Optional[str] = None,
        date_str: Optional[str] = None,
        time_range: str = "today",
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """Doctor personal OPD consultation earnings and patient load for a date or all time."""
        if not db or not hospital_id:
            return {"error": "Invalid session"}

        doctor = None
        if doctor_name:
            clean_name = doctor_name.lower().replace("dr.", "").replace("dr ", "").replace("doctor", "").strip()
            doctor = (await db.execute(select(Doctor).where(Doctor.hospital_id == hospital_id, CopilotTools._build_doctor_search_conditions(clean_name)))).scalars().first()
        elif user_id:
            doctor = (await db.execute(select(Doctor).where(Doctor.hospital_id == hospital_id, or_(Doctor.id == user_id, Doctor.email == user_id)))).scalars().first()

        if not doctor:
            doctor = (await db.execute(select(Doctor).where(Doctor.hospital_id == hospital_id, Doctor.is_active == True))).scalars().first()

        if not doctor:
            return {"error": "Doctor context not found."}

        stmt = select(Appointment).where(
            Appointment.doctor_id == doctor.id,
            Appointment.hospital_id == hospital_id
        )

        now = datetime.now()
        t_range_norm = (time_range or "today").lower().strip()

        if t_range_norm in ["all", "all_time", "lifetime", "total", "overall", "all time"]:
            period_label = "All Time"
        elif t_range_norm in ["month", "this_month", "monthly", "this month"]:
            stmt = stmt.where(
                func.extract("year", Appointment.appointment_datetime) == now.year,
                func.extract("month", Appointment.appointment_datetime) == now.month
            )
            period_label = "This Month"
        elif t_range_norm in ["week", "this_week", "weekly", "this week"]:
            start_week = now.date() - timedelta(days=now.weekday())
            stmt = stmt.where(func.date(Appointment.appointment_datetime) >= start_week)
            period_label = "This Week"
        elif date_str:
            target_date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            stmt = stmt.where(func.date(Appointment.appointment_datetime) == target_date_obj)
            period_label = str(target_date_obj)
        else:
            target_date_obj = now.date()
            stmt = stmt.where(func.date(Appointment.appointment_datetime) == target_date_obj)
            period_label = str(target_date_obj)

        appts = (await db.execute(stmt)).scalars().all()

        total_booked = len(appts)
        completed = sum(1 for a in appts if a.status in ["COMPLETED", "CONSULTATION_FINISHED"])
        fee = float(doctor.opd_fees or 500)
        earned = completed * fee

        return {
            "doctor_name": f"Dr. {doctor.first_name} {doctor.last_name}",
            "period": period_label,
            "date": period_label,
            "opd_fee": fee,
            "total_booked": total_booked,
            "completed_consultations": completed,
            "total_earned": f"₹{earned:,.0f}"
        }

    @staticmethod
    async def apply_leave_for_doctor(
        hospital_id: str,
        user_id: Optional[str] = None,
        doctor_name: Optional[str] = None,
        leave_date: Optional[str] = None,
        start_date_str: Optional[str] = None,
        end_date_str: Optional[str] = None,
        reason: str = "Personal Leave",
        confirmation_token: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """Submits and approves/records a planned leave application for a doctor in MySQL."""
        if not db or not hospital_id:
            return {"error": "Invalid session or tenant context"}

        doctor = None
        if doctor_name:
            clean_name = doctor_name.lower().replace("dr.", "").replace("dr ", "").replace("doctor", "").strip()
            doctor = (await db.execute(select(Doctor).where(Doctor.hospital_id == hospital_id, CopilotTools._build_doctor_search_conditions(clean_name)))).scalars().first()
        elif user_id:
            doctor = (await db.execute(select(Doctor).where(Doctor.hospital_id == hospital_id, or_(Doctor.id == user_id, Doctor.email == user_id)))).scalars().first()

        if not doctor:
            doctor = (await db.execute(select(Doctor).where(Doctor.hospital_id == hospital_id, Doctor.is_active == True))).scalars().first()

        if not doctor:
            return {"error": "Doctor record not found for leave application."}

        s_date_str = start_date_str or leave_date or datetime.now().strftime("%Y-%m-%d")
        e_date_str = end_date_str or s_date_str

        try:
            s_date = datetime.strptime(s_date_str, "%Y-%m-%d").date()
            e_date = datetime.strptime(e_date_str, "%Y-%m-%d").date()
        except Exception:
            s_date = datetime.now().date()
            e_date = s_date

        leave_rec = DoctorLeave(
            id=str(uuid.uuid4()),
            doctor_id=doctor.id,
            start_date=s_date,
            end_date=e_date,
            reason=reason or "Personal Leave",
            status="APPROVED"
        )
        db.add(leave_rec)
        await db.commit()

        return {
            "success": True,
            "leave_id": leave_rec.id,
            "doctor_name": f"Dr. {doctor.first_name} {doctor.last_name}",
            "start_date": str(s_date),
            "end_date": str(e_date),
            "reason": reason or "Personal Leave",
            "status": "APPROVED",
            "message": f"Leave application for Dr. {doctor.first_name} {doctor.last_name} ({s_date} to {e_date}) has been successfully recorded and approved."
        }

    @staticmethod
    async def record_patient_intake_vitals(
        hospital_id: str,
        appointment_id: str,
        chief_complaint: str,
        bp: Optional[str] = None,
        pulse: Optional[int] = None,
        temperature: Optional[float] = None,
        spo2: Optional[int] = None,
        weight: Optional[float] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """Nurse / Receptionist records patient intake vitals and chief complaint."""
        if not db or not hospital_id or not appointment_id:
            return {"error": "Appointment ID required."}

        stmt = select(Appointment, Patient).join(Patient, Appointment.patient_id == Patient.id).where(
            Appointment.id == appointment_id,
            Appointment.hospital_id == hospital_id
        )
        row = (await db.execute(stmt)).first()
        if not row:
            return {"error": f"Appointment '{appointment_id}' not found."}

        appt, pat = row
        intake_id = str(uuid.uuid4())
        intake = PatientIntake(
            id=intake_id,
            appointment_id=appt.id,
            chief_complaint=chief_complaint,
            bp=bp,
            pulse=pulse,
            temperature=temperature,
            spo2=spo2,
            weight=weight
        )
        db.add(intake)
        await db.commit()

        return {
            "success": True,
            "intake_id": intake_id,
            "patient_name": f"{pat.first_name} {pat.last_name}".strip(),
            "chief_complaint": chief_complaint,
            "vitals": {
                "bp": bp or "N/A",
                "pulse": f"{pulse} bpm" if pulse else "N/A",
                "temp": f"{temperature} °F" if temperature else "N/A",
                "spo2": f"{spo2}%" if spo2 else "N/A",
                "weight": f"{weight} kg" if weight else "N/A"
            }
        }

    @staticmethod
    async def get_patient_prescription_receipt(
        phone: str,
        hospital_id: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """Retrieves latest prescription and payment invoice details for a patient."""
        if not db or not phone:
            return {"error": "Phone number required."}

        clean_p = phone.strip().replace(" ", "").replace("-", "")
        if not clean_p.startswith("+"):
            clean_p = "+91" + clean_p.lstrip("0")

        stmt = select(ConsultationNote, Appointment, Patient, Doctor, Department).join(
            Appointment, ConsultationNote.appointment_id == Appointment.id
        ).join(
            Patient, Appointment.patient_id == Patient.id
        ).join(
            Doctor, Appointment.doctor_id == Doctor.id
        ).join(
            Department, Doctor.department_id == Department.id
        ).where(
            Patient.phone == clean_p
        )
        if hospital_id:
            stmt = stmt.where(Appointment.hospital_id == hospital_id)

        stmt = stmt.order_by(ConsultationNote.created_at.desc()).limit(1)
        res = (await db.execute(stmt)).first()

        if not res:
            return {"message": f"No prescription records found for phone '{phone}'."}

        note, appt, pat, doc, dept = res
        fee = appt.amount_paid or doc.opd_fees or 500
        return {
            "patient_name": f"{pat.first_name} {pat.last_name}".strip(),
            "doctor_name": f"Dr. {doc.first_name} {doc.last_name}",
            "department": dept.name,
            "visit_date": appt.appointment_datetime.strftime("%Y-%m-%d %I:%M %p") if appt.appointment_datetime else "N/A",
            "diagnosis": note.diagnosis or "Clinical Consultation",
            "prescription": note.prescription or "Prescribed medications as advised",
            "follow_up_date": str(note.follow_up_date) if note.follow_up_date else "As needed",
            "amount_paid": f"₹{fee}",
            "payment_status": appt.payment_status
        }


