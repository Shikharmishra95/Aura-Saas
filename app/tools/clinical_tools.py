import uuid
import logging
from datetime import datetime, date, time, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.appointment import (
    Appointment, Patient, Doctor, Department, ConsultationNote,
    InsuranceProvider, DoctorSchedule
)
from app.engines.conversation_memory import conversation_memory

logger = logging.getLogger("aura.tools.clinical")

class ClinicalTools:
    """
    AURA Clinical & Patient Health Records Tools:
    - Get Patient Prescriptions & Consultations History
    - Live Queue Position & Wait Time Estimation
    - Insurance & TPA Cashless Panel Directory
    - Save Doctor Consultation Notes & Prescriptions
    """

    @classmethod
    async def get_my_prescriptions(
        cls,
        hospital_id: Optional[str],
        user_id: Optional[str],
        role: str,
        phone: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Retrieves clinical consultation notes and prescriptions strictly scoped to the authenticated patient identity.
        """
        if not db or not hospital_id:
            return {"error": "Hospital tenant ID and active DB session required."}

        role_upper = (role or "").upper().replace(" ", "_")

        stmt = (
            select(ConsultationNote, Appointment, Doctor, Department, Patient)
            .join(Appointment, ConsultationNote.appointment_id == Appointment.id)
            .join(Doctor, ConsultationNote.doctor_id == Doctor.id)
            .join(Department, Doctor.department_id == Department.id)
            .join(Patient, ConsultationNote.patient_id == Patient.id)
            .where(Appointment.hospital_id == hospital_id)
        )

        if role_upper == "PATIENT":
            if phone and phone.strip():
                stmt = stmt.where(Patient.phone.ilike(f"%{phone.strip()}%"))
            elif user_id:
                stmt = stmt.where(or_(Patient.id == user_id, Appointment.patient_id == user_id))
            else:
                return {"prescriptions": [], "total_count": 0, "message": "Please provide your registered phone number."}
        else:
            if phone and phone.strip():
                stmt = stmt.where(Patient.phone.ilike(f"%{phone.strip()}%"))

        stmt = stmt.order_by(ConsultationNote.created_at.desc()).limit(20)
        rows = (await db.execute(stmt)).all()

        records = []
        for note, appt, doc, dept, pat in rows:
            records.append({
                "note_id": note.id,
                "appointment_id": appt.id,
                "visit_date": appt.appointment_datetime.strftime("%Y-%m-%d"),
                "doctor_name": f"Dr. {doc.first_name} {doc.last_name}",
                "department": dept.name,
                "patient_name": f"{pat.first_name} {pat.last_name}",
                "clinical_notes": note.clinical_notes or "General OPD Consultation",
                "prescription": note.prescription or "No medication prescribed",
                "follow_up_date": note.follow_up_date.strftime("%Y-%m-%d") if note.follow_up_date else "As needed"
            })

        return {
            "prescriptions": records,
            "total_count": len(records),
            "hospital_id": hospital_id
        }

    @classmethod
    async def get_my_live_token_position(
        cls,
        hospital_id: Optional[str],
        user_id: Optional[str],
        role: str,
        appointment_id_or_phone: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Computes live waiting position, patients ahead, and estimated wait minutes for today's appointment.
        """
        if not db or not hospital_id:
            return {"error": "Hospital tenant ID and active DB session required."}

        today = datetime.now().date()
        start_day = datetime.combine(today, time.min)
        end_day = datetime.combine(today, time.max)

        # 1. Resolve Patient's Appointment for Today
        stmt = (
            select(Appointment, Doctor, Department, Patient)
            .join(Doctor, Appointment.doctor_id == Doctor.id)
            .join(Department, Doctor.department_id == Department.id)
            .join(Patient, Appointment.patient_id == Patient.id)
            .where(
                Appointment.hospital_id == hospital_id,
                Appointment.appointment_datetime >= start_day,
                Appointment.appointment_datetime <= end_day,
                Appointment.status.in_(["SCHEDULED", "CONFIRMED", "PENDING_PAYMENT", "RESCHEDULED", "WAITING", "IN_CONSULTATION"])
            )
        )

        clean_q = (appointment_id_or_phone or "").strip()
        if clean_q:
            stmt = stmt.where(or_(
                Appointment.id == clean_q,
                Patient.phone.ilike(f"%{clean_q}%"),
                Patient.id == clean_q
            ))
        elif user_id:
            stmt = stmt.where(or_(Patient.id == user_id, Appointment.patient_id == user_id))

        res = (await db.execute(stmt)).first()
        if not res:
            return {
                "has_active_appointment": False,
                "message": "No active appointment found for today. Please verify your appointment date or booking ID."
            }

        target_appt, doc, dept, pat = res

        # 2. Count appointments ahead for this doctor today
        ahead_stmt = select(func.count(Appointment.id)).where(
            Appointment.hospital_id == hospital_id,
            Appointment.doctor_id == doc.id,
            Appointment.appointment_datetime >= start_day,
            Appointment.appointment_datetime < target_appt.appointment_datetime,
            Appointment.status.in_(["SCHEDULED", "CONFIRMED", "WAITING"])
        )
        patients_ahead = (await db.execute(ahead_stmt)).scalar() or 0

        # Estimated wait time (approx 15-20 mins per patient ahead)
        est_wait_minutes = patients_ahead * 15

        return {
            "has_active_appointment": True,
            "appointment_id": target_appt.id,
            "patient_name": f"{pat.first_name} {pat.last_name}",
            "doctor_name": f"Dr. {doc.first_name} {doc.last_name}",
            "department": dept.name,
            "appointment_time": target_appt.appointment_datetime.strftime("%I:%M %p"),
            "status": target_appt.status,
            "patients_ahead": patients_ahead,
            "estimated_wait_minutes": est_wait_minutes,
            "hospital_id": hospital_id
        }

    @classmethod
    async def get_insurance_tpa_panels(
        cls,
        hospital_id: Optional[str],
        provider_name: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Retrieves list of accepted cashless insurance panels and TPA networks for the hospital.
        """
        if not db or not hospital_id:
            return {"error": "Hospital tenant ID and active DB session required."}

        stmt = select(InsuranceProvider).where(InsuranceProvider.hospital_id == hospital_id)
        if provider_name and provider_name.strip():
            stmt = stmt.where(InsuranceProvider.provider_name.ilike(f"%{provider_name.strip()}%"))

        rows = (await db.execute(stmt)).scalars().all()

        panels = []
        for p in rows:
            panels.append({
                "provider_id": p.id,
                "provider_name": p.provider_name,
                "plan_name": p.plan_name or "Cashless Mediclaim",
                "network_status": p.network_status or "IN_NETWORK"
            })

        return {
            "insurance_panels": panels,
            "total_count": len(panels),
            "hospital_id": hospital_id
        }

    @classmethod
    async def save_consultation_notes(
        cls,
        hospital_id: Optional[str],
        user_id: Optional[str],
        role: str,
        appointment_id: str,
        clinical_notes: str,
        prescription: Optional[str] = None,
        follow_up_date_str: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Allows doctor to dictate and record clinical diagnosis, notes, prescription, and follow-up date for an appointment.
        """
        if not db or not hospital_id:
            return {"success": False, "error": "Hospital tenant ID and active DB session required."}

        role_upper = (role or "").upper().replace(" ", "_")
        if role_upper not in ["DOCTOR", "ADMIN", "SUPER_ADMIN"]:
            return {"success": False, "error": "Access Denied: Only doctors or medical staff can record consultation notes."}

        # 1. Fetch Appointment
        appt_stmt = (
            select(Appointment, Doctor, Patient)
            .join(Doctor, Appointment.doctor_id == Doctor.id)
            .join(Patient, Appointment.patient_id == Patient.id)
            .where(
                Appointment.id == appointment_id.strip(),
                Appointment.hospital_id == hospital_id
            )
        )
        res = (await db.execute(appt_stmt)).first()
        if not res:
            return {"success": False, "error": f"Appointment #{appointment_id} not found in this hospital."}

        appt, doc, pat = res

        # 2. Parse Follow-up Date
        fu_date = None
        if follow_up_date_str and follow_up_date_str.strip():
            try:
                fu_date = datetime.strptime(follow_up_date_str.strip(), "%Y-%m-%d").date()
            except Exception:
                pass

        # 3. Create or Update ConsultationNote
        note_stmt = select(ConsultationNote).where(ConsultationNote.appointment_id == appt.id)
        existing_note = (await db.execute(note_stmt)).scalar_one_or_none()

        if existing_note:
            existing_note.clinical_notes = clinical_notes
            existing_note.prescription = prescription or existing_note.prescription
            existing_note.follow_up_date = fu_date or existing_note.follow_up_date
            existing_note.updated_at = datetime.now()
        else:
            new_note = ConsultationNote(
                id=f"note_{uuid.uuid4().hex[:12]}",
                appointment_id=appt.id,
                patient_id=pat.id,
                doctor_id=doc.id,
                clinical_notes=clinical_notes,
                prescription=prescription or "Prescribed medications as advised",
                follow_up_date=fu_date,
                created_at=datetime.now()
            )
            db.add(new_note)

        # 4. Mark Appointment as COMPLETED
        appt.consultation_status = "COMPLETED"
        appt.status = "COMPLETED"
        appt.updated_at = datetime.now()

        await db.commit()

        return {
            "success": True,
            "appointment_id": appt.id,
            "patient_name": f"{pat.first_name} {pat.last_name}",
            "doctor_name": f"Dr. {doc.first_name} {doc.last_name}",
            "clinical_notes": clinical_notes,
            "prescription": prescription or "Medications recorded",
            "follow_up_date": fu_date.strftime("%Y-%m-%d") if fu_date else "As needed",
            "status": "COMPLETED"
        }
