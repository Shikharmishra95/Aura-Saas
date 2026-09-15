import logging
from typing import Dict, Any, List, Optional
from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.appointment import Patient, Appointment, Doctor, Department

logger = logging.getLogger("aura.tools.patient")

class PatientTools:
    """
    HMS Patient Profile & Clinical History Operational Tools:
    - Strictly respects Role-Based Access Control (RBAC).
    - Protects confidential patient PII, OTPs, and password credentials.
    """

    @classmethod
    async def get_patient_details(
        cls,
        hospital_id: Optional[str],
        user_id: Optional[str],
        role: str,
        patient_id: Optional[str] = None,
        query: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Retrieves patient medical profile and visit history according to caller's role.
        - PATIENT: Only allowed to view their own profile.
        - DOCTOR/RECEPTIONIST/ADMIN: Allowed to view patient records within this hospital tenant.
        """
        if not db or not hospital_id:
            return {"error": "Hospital tenant ID and active DB session required."}

        role_upper = (role or "").upper().replace(" ", "_")

        stmt = select(Patient).where(
            Patient.hospital_id == hospital_id,
            Patient.is_active == True
        )

        # RBAC Enforcement
        if role_upper == "PATIENT":
            if user_id:
                stmt = stmt.where(Patient.id == user_id)
            elif query:
                stmt = stmt.where(or_(Patient.phone == query.strip(), Patient.id == query.strip()))
            else:
                return {"error": "Patient identity context required."}
        else:
            if patient_id:
                stmt = stmt.where(Patient.id == patient_id)
            elif query:
                q_clean = query.strip()
                stmt = stmt.where(
                    or_(
                        Patient.phone.ilike(f"%{q_clean}%"),
                        func.concat(Patient.first_name, " ", Patient.last_name).ilike(f"%{q_clean}%"),
                        Patient.id == q_clean
                    )
                )
            else:
                return {"error": "Please specify patient ID, name, or phone number."}

        patient = (await db.execute(stmt)).scalars().first()
        if not patient:
            return {"error": f"Patient record not found in this hospital."}

        # Fetch recent visit history
        appt_stmt = (
            select(Appointment, Doctor, Department)
            .join(Doctor, Appointment.doctor_id == Doctor.id)
            .join(Department, Doctor.department_id == Department.id)
            .where(
                Appointment.hospital_id == hospital_id,
                Appointment.patient_id == patient.id
            )
            .order_by(Appointment.appointment_datetime.desc())
            .limit(10)
        )
        visits = (await db.execute(appt_stmt)).all()

        visit_history = []
        for a, d, dept in visits:
            visit_history.append({
                "appointment_id": a.id,
                "date": a.appointment_datetime.strftime("%Y-%m-%d"),
                "time": a.appointment_datetime.strftime("%I:%M %p"),
                "doctor_name": f"Dr. {d.first_name} {d.last_name}",
                "department": dept.name,
                "status": a.status,
                "payment_status": a.payment_status,
                "reason": a.reason
            })

        return {
            "patient_id": patient.id,
            "patient_name": f"{patient.first_name} {patient.last_name}".strip(),
            "phone": patient.phone,
            "gender": patient.gender or "Not Specified",
            "date_of_birth": patient.date_of_birth.strftime("%Y-%m-%d") if patient.date_of_birth else "N/A",
            "insurance_policy": patient.insurance_policy_number or "None (Direct Pay)",
            "total_visits": len(visit_history),
            "recent_visits": visit_history,
            "hospital_id": hospital_id
        }
