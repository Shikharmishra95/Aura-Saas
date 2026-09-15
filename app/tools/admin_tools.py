import uuid
import logging
from datetime import datetime, date, time
from typing import Dict, Any, List, Optional
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.appointment import (
    Doctor, Department, DoctorSchedule, DoctorLeave, Appointment
)
from app.engines.conversation_memory import conversation_memory

logger = logging.getLogger("aura.tools.admin")

class AdminTools:
    """
    AURA Hospital Operations & Administration Tools:
    - Multi-Department Live OPD Queues Overview
    - Approve / Reject Doctor Planned Leave (with Action Token)
    - Update Doctor OPD Timetable Schedule (with Action Token)
    """

    @classmethod
    async def get_all_opd_queues(
        cls,
        hospital_id: Optional[str],
        date_str: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Aggregates live OPD patient queue status across all hospital wings and departments.
        """
        if not db or not hospital_id:
            return {"error": "Hospital tenant ID and active DB session required."}

        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else datetime.now().date()
        except Exception:
            target_date = datetime.now().date()

        start_day = datetime.combine(target_date, time.min)
        end_day = datetime.combine(target_date, time.max)

        # 1. Fetch active departments
        dept_stmt = select(Department).where(Department.hospital_id == hospital_id, Department.is_active == True)
        departments = (await db.execute(dept_stmt)).scalars().all()

        dept_matrix = []
        total_waiting = 0
        total_in_consult = 0
        total_completed = 0
        total_appointments = 0

        for dept in departments:
            # Query appointments in this dept today
            stmt = (
                select(Appointment.status, Appointment.consultation_status, func.count(Appointment.id))
                .join(Doctor, Appointment.doctor_id == Doctor.id)
                .where(
                    Appointment.hospital_id == hospital_id,
                    Doctor.department_id == dept.id,
                    Appointment.appointment_datetime >= start_day,
                    Appointment.appointment_datetime <= end_day
                )
                .group_by(Appointment.status, Appointment.consultation_status)
            )
            rows = (await db.execute(stmt)).all()

            dept_wait = 0
            dept_consult = 0
            dept_done = 0
            dept_total = 0

            for status, consult_status, count in rows:
                dept_total += count
                if consult_status == "COMPLETED" or status == "COMPLETED":
                    dept_done += count
                elif consult_status == "IN_CONSULTATION" or status == "IN_CONSULTATION":
                    dept_consult += count
                elif status in ["SCHEDULED", "CONFIRMED", "WAITING", "PENDING_PAYMENT"]:
                    dept_wait += count

            total_waiting += dept_wait
            total_in_consult += dept_consult
            total_completed += dept_done
            total_appointments += dept_total

            dept_matrix.append({
                "department_id": dept.id,
                "department_name": dept.name,
                "waiting_count": dept_wait,
                "in_consultation_count": dept_consult,
                "completed_count": dept_done,
                "total_booked": dept_total
            })

        return {
            "date": target_date.strftime("%Y-%m-%d"),
            "total_departments": len(departments),
            "total_appointments": total_appointments,
            "total_waiting": total_waiting,
            "total_in_consultation": total_in_consult,
            "total_completed": total_completed,
            "department_queues": dept_matrix,
            "hospital_id": hospital_id
        }

    @classmethod
    async def approve_or_reject_doctor_leave(
        cls,
        hospital_id: Optional[str],
        user_id: Optional[str],
        role: str,
        leave_id: str,
        action: str = "APPROVE", # 'APPROVE' or 'REJECT'
        rejection_reason: Optional[str] = None,
        confirmation_token: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Approves or rejects a doctor leave request with two-phase Human-in-the-Loop Confirmation.
        """
        if not db or not hospital_id:
            return {"success": False, "error": "Hospital tenant ID and active DB session required."}

        role_upper = (role or "").upper().replace(" ", "_")
        if role_upper not in ["ADMIN", "SUPER_ADMIN"]:
            return {"success": False, "error": "Access Denied: Only hospital administrators can approve or reject leaves."}

        # 1. Fetch Leave Record
        stmt = (
            select(DoctorLeave, Doctor, Department)
            .join(Doctor, DoctorLeave.doctor_id == Doctor.id)
            .join(Department, Doctor.department_id == Department.id)
            .where(
                DoctorLeave.id == leave_id.strip(),
                Doctor.hospital_id == hospital_id
            )
        )
        res = (await db.execute(stmt)).first()
        if not res:
            return {"success": False, "error": f"Leave application #{leave_id} not found."}

        leave, doc, dept = res
        act_upper = action.upper().strip()

        # 2. Confirmation Check
        if not confirmation_token:
            summary = f"{act_upper} leave for Dr. {doc.first_name} {doc.last_name} ({dept.name}) from {leave.start_date} to {leave.end_date}"
            token_rec = conversation_memory.create_confirmation_token(
                hospital_id=hospital_id,
                user_id=user_id or "ADMIN",
                action_name="approve_or_reject_doctor_leave",
                action_args={"leave_id": leave.id, "action": act_upper, "rejection_reason": rejection_reason},
                summary=summary,
                expires_in_seconds=120
            )
            return {
                "status": "CONFIRMATION_REQUIRED",
                "confirmation_token": token_rec.token,
                "summary": summary,
                "leave_id": leave.id,
                "doctor_name": f"Dr. {doc.first_name} {doc.last_name}",
                "department": dept.name,
                "period": f"{leave.start_date} to {leave.end_date}",
                "requested_action": act_upper,
                "message": f"⚠️ Please confirm {act_upper} for Dr. {doc.first_name}'s leave. Reply with: CONFIRM {token_rec.token}"
            }

        # 3. Validate Token
        consumed = conversation_memory.validate_and_consume_token(
            token=confirmation_token,
            hospital_id=hospital_id,
            user_id=user_id or "ADMIN"
        )
        if not consumed:
            return {"success": False, "error": "Confirmation token is invalid or has expired."}

        # 4. Execute Update
        if act_upper == "APPROVE":
            leave.status = "APPROVED"
        else:
            leave.status = "REJECTED"
            leave.rejection_reason = rejection_reason or "Declined by Admin"

        leave.updated_at = datetime.now()
        await db.commit()

        return {
            "success": True,
            "leave_id": leave.id,
            "doctor_name": f"Dr. {doc.first_name} {doc.last_name}",
            "status": leave.status,
            "period": f"{leave.start_date} to {leave.end_date}",
            "message": f"Leave application #{leave.id} has been {leave.status} successfully."
        }

    @classmethod
    async def update_doctor_schedule(
        cls,
        hospital_id: Optional[str],
        user_id: Optional[str],
        role: str,
        doctor_id_or_name: str,
        day_of_week: int,
        start_time_str: str,
        end_time_str: str,
        slot_duration_minutes: int = 20,
        confirmation_token: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Modifies a doctor's weekly shift start/end times and slot duration with Action Confirmation.
        """
        if not db or not hospital_id:
            return {"success": False, "error": "Hospital tenant ID and active DB session required."}

        role_upper = (role or "").upper().replace(" ", "_")
        if role_upper not in ["ADMIN", "SUPER_ADMIN"]:
            return {"success": False, "error": "Access Denied: Only administrators can update doctor schedules."}

        # 1. Resolve Doctor
        clean_d = doctor_id_or_name.lower().replace("dr.", "").replace("dr ", "").strip()
        doc_stmt = select(Doctor).where(
            Doctor.hospital_id == hospital_id,
            or_(
                Doctor.id == doctor_id_or_name.strip(),
                func.concat(Doctor.first_name, " ", Doctor.last_name).ilike(f"%{clean_d}%"),
                Doctor.first_name.ilike(f"%{clean_d}%"),
                Doctor.last_name.ilike(f"%{clean_d}%")
            )
        )
        doctor = (await db.execute(doc_stmt)).scalars().first()
        if not doctor:
            return {"success": False, "error": f"Doctor '{doctor_id_or_name}' not found."}

        # 2. Parse Times
        st = None
        et = None
        for fmt in ("%I:%M %p", "%I:%M%p", "%H:%M", "%I %p"):
            try:
                if not st:
                    st = datetime.strptime(start_time_str.strip(), fmt).time()
            except Exception:
                pass
            try:
                if not et:
                    et = datetime.strptime(end_time_str.strip(), fmt).time()
            except Exception:
                pass

        if not st or not et:
            return {"success": False, "error": f"Invalid time format. Please use '09:00 AM' or '05:00 PM'."}

        day_map = {1: "Monday", 2: "Tuesday", 3: "Wednesday", 4: "Thursday", 5: "Friday", 6: "Saturday", 7: "Sunday"}
        day_name = day_map.get(day_of_week, f"Day {day_of_week}")

        # 3. Confirmation Check
        if not confirmation_token:
            summary = f"Update Dr. {doctor.first_name} {doctor.last_name}'s {day_name} shift to {st.strftime('%I:%M %p')} - {et.strftime('%I:%M %p')} (Slot: {slot_duration_minutes}m)"
            token_rec = conversation_memory.create_confirmation_token(
                hospital_id=hospital_id,
                user_id=user_id or "ADMIN",
                action_name="update_doctor_schedule",
                action_args={
                    "doctor_id_or_name": doctor.id,
                    "day_of_week": day_of_week,
                    "start_time_str": start_time_str,
                    "end_time_str": end_time_str,
                    "slot_duration_minutes": slot_duration_minutes
                },
                summary=summary,
                expires_in_seconds=120
            )
            return {
                "status": "CONFIRMATION_REQUIRED",
                "confirmation_token": token_rec.token,
                "summary": summary,
                "doctor_name": f"Dr. {doctor.first_name} {doctor.last_name}",
                "day": day_name,
                "new_timings": f"{st.strftime('%I:%M %p')} - {et.strftime('%I:%M %p')}",
                "slot_duration": f"{slot_duration_minutes} minutes",
                "message": f"⚠️ Please confirm updating Dr. {doctor.first_name}'s schedule. Reply with: CONFIRM {token_rec.token}"
            }

        # 4. Validate Token
        consumed = conversation_memory.validate_and_consume_token(
            token=confirmation_token,
            hospital_id=hospital_id,
            user_id=user_id or "ADMIN"
        )
        if not consumed:
            return {"success": False, "error": "Confirmation token is invalid or has expired."}

        # 5. Create or Update Schedule
        sched_stmt = select(DoctorSchedule).where(
            DoctorSchedule.doctor_id == doctor.id,
            DoctorSchedule.day_of_week == day_of_week
        )
        sched = (await db.execute(sched_stmt)).scalar_one_or_none()
        if sched:
            sched.start_time = st
            sched.end_time = et
            sched.slot_duration_minutes = slot_duration_minutes
            sched.updated_at = datetime.now()
        else:
            new_sched = DoctorSchedule(
                id=f"sch_{uuid.uuid4().hex[:12]}",
                doctor_id=doctor.id,
                day_of_week=day_of_week,
                start_time=st,
                end_time=et,
                slot_duration_minutes=slot_duration_minutes,
                created_at=datetime.now()
            )
            db.add(new_sched)

        await db.commit()

        return {
            "success": True,
            "doctor_name": f"Dr. {doctor.first_name} {doctor.last_name}",
            "day": day_name,
            "start_time": st.strftime("%I:%M %p"),
            "end_time": et.strftime("%I:%M %p"),
            "slot_duration_minutes": slot_duration_minutes,
            "message": f"Schedule for Dr. {doctor.first_name} on {day_name} updated to {st.strftime('%I:%M %p')} - {et.strftime('%I:%M %p')}."
        }
