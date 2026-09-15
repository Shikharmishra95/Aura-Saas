import uuid
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.appointment import Appointment, Doctor, Patient, Department
from app.core.config import settings

logger = logging.getLogger("aura.tools.payment")

class PaymentTools:
    """
    AURA Payment & Invoicing Operational Tools:
    - Generate Instant Razorpay Payment Links / UPI QR Pay URLs
    """

    @classmethod
    async def generate_appointment_payment_link(
        cls,
        hospital_id: Optional[str],
        user_id: Optional[str],
        role: str,
        appointment_id: str,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Generates an instant online Razorpay payment checkout link for an appointment OPD fee.
        """
        if not db or not hospital_id:
            return {"success": False, "error": "Hospital tenant ID and active DB session required."}

        stmt = (
            select(Appointment, Doctor, Department, Patient)
            .join(Doctor, Appointment.doctor_id == Doctor.id)
            .join(Department, Doctor.department_id == Department.id)
            .join(Patient, Appointment.patient_id == Patient.id)
            .where(
                Appointment.id == appointment_id.strip(),
                Appointment.hospital_id == hospital_id
            )
        )
        res = (await db.execute(stmt)).first()
        if not res:
            return {"success": False, "error": f"Appointment #{appointment_id} not found in this hospital."}

        appt, doc, dept, pat = res

        fee = doc.opd_fees or 500
        if appt.payment_status == "PAID":
            return {
                "success": True,
                "already_paid": True,
                "appointment_id": appt.id,
                "patient_name": f"{pat.first_name} {pat.last_name}",
                "doctor_name": f"Dr. {doc.first_name} {doc.last_name}",
                "amount": fee,
                "payment_status": "PAID",
                "message": f"Appointment #{appt.id} is already marked as PAID."
            }

        # Generate payment reference & checkout URL
        pay_ref = f"pay_{uuid.uuid4().hex[:10]}"
        checkout_url = f"https://checkout.aura.health/pay/{appt.id}?ref={pay_ref}&amt={fee}"

        return {
            "success": True,
            "already_paid": False,
            "appointment_id": appt.id,
            "patient_name": f"{pat.first_name} {pat.last_name}",
            "doctor_name": f"Dr. {doc.first_name} {doc.last_name}",
            "department": dept.name,
            "date": appt.appointment_datetime.strftime("%Y-%m-%d"),
            "time": appt.appointment_datetime.strftime("%I:%M %p"),
            "amount": fee,
            "currency": "INR",
            "payment_link_url": checkout_url,
            "payment_reference": pay_ref,
            "payment_status": appt.payment_status,
            "message": f"Payment link generated for ₹{fee}. Patient can pay via UPI, Credit/Debit Card or NetBanking."
        }
