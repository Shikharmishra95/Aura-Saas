import re
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, date, time
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.appointment import (
    Doctor, Department, DoctorSchedule, DoctorLeave, DoctorSpecialization,
    HospitalHoliday, WorkingHour
)
from app.engines.scheduling import SchedulingEngine

logger = logging.getLogger("aura.tools.doctor")

class DoctorTools:
    """
    HMS Doctor Operational Tools:
    - Search doctors by name, department, specialization
    - Get safe professional doctor details
    - Check real-time doctor availability (shifts, leaves, holidays)
    - Calculate live available appointment time slots
    """

    @staticmethod
    def _build_name_filter(name_query: str):
        """Builds multi-clause case-insensitive search for doctor names."""
        stopwords = {
            "dr", "dr.", "doctor", "ya", "aur", "and", "rhe", "rahe", "hai", "hain", "kya", "ko", "par", "pe",
            "aaj", "kal", "parso", "baith", "baithe", "baithte", "chutti", "leave", "duty", "off", "on",
            "the", "is", "of", "in", "status", "check", "batao", "dikhao", "please", "sir", "mam", "what",
            "about", "ka", "ki", "ke", "se", "summary", "record", "performance", "details"
        }
        raw_clean = name_query.lower().replace("dr.", "").replace("dr ", "").replace("doctor", "").strip()
        tokens = [t.strip() for t in raw_clean.split() if t.strip() not in stopwords and len(t.strip()) >= 2]
        clean = " ".join(tokens) if tokens else raw_clean

        conds = [
            func.concat(Doctor.first_name, " ", Doctor.last_name).ilike(f"%{clean}%"),
            Doctor.first_name.ilike(f"%{clean}%"),
            Doctor.last_name.ilike(f"%{clean}%")
        ]
        for t in tokens:
            conds.append(Doctor.first_name.ilike(f"%{t}%"))
            conds.append(Doctor.last_name.ilike(f"%{t}%"))
        return or_(*conds)

    @classmethod
    async def search_doctors(
        cls,
        hospital_id: Optional[str],
        name: Optional[str] = None,
        department: Optional[str] = None,
        specialization: Optional[str] = None,
        availability_date: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Searches active doctors in the hospital tenant by name, department, or specialization.
        """
        if not db or not hospital_id:
            return {"error": "Hospital tenant ID and active DB session required."}

        stmt = (
            select(Doctor, Department)
            .join(Department, Doctor.department_id == Department.id)
            .where(
                Doctor.hospital_id == hospital_id,
                Doctor.is_active == True
            )
        )

        if name and name.strip():
            stmt = stmt.where(cls._build_name_filter(name.strip()))

        if department and department.strip():
            stmt = stmt.where(Department.name.ilike(f"%{department.strip()}%"))

        results = (await db.execute(stmt)).all()
        if not results:
            return {
                "doctors": [],
                "count": 0,
                "message": f"No active doctors found matching criteria in this hospital."
            }

        doctor_list = []
        day_map = {1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu", 5: "Fri", 6: "Sat", 7: "Sun"}

        for doctor, dept in results:
            # Fetch specializations
            spec_stmt = select(DoctorSpecialization.specialization).where(DoctorSpecialization.doctor_id == doctor.id)
            specs = (await db.execute(spec_stmt)).scalars().all()

            # If specialization filter was requested
            if specialization and specialization.strip():
                if not any(specialization.strip().lower() in s.lower() for s in specs) and specialization.strip().lower() not in dept.name.lower():
                    continue

            # Fetch schedules
            sched_stmt = select(DoctorSchedule).where(DoctorSchedule.doctor_id == doctor.id).order_by(DoctorSchedule.day_of_week.asc())
            schedules = (await db.execute(sched_stmt)).scalars().all()
            timing_strs = []
            for s in schedules:
                day_name = day_map.get(s.day_of_week, f"Day {s.day_of_week}")
                st = s.start_time.strftime("%I:%M %p") if s.start_time else "N/A"
                et = s.end_time.strftime("%I:%M %p") if s.end_time else "N/A"
                timing_strs.append(f"{day_name} ({st}-{et})")

            doctor_list.append({
                "doctor_id": doctor.id,
                "doctor_name": f"Dr. {doctor.first_name} {doctor.last_name}".strip(),
                "name": f"Dr. {doctor.first_name} {doctor.last_name}".strip(),
                "department": dept.name,
                "specializations": list(specs) if specs else [dept.name],
                "opd_fee": doctor.opd_fees or 500,
                "schedule_timings": ", ".join(timing_strs) if timing_strs else "Standard OPD Hours",
                "phone_extension": dept.phone_extension
            })

        return {
            "doctors": doctor_list,
            "total_count": len(doctor_list),
            "count": len(doctor_list),
            "hospital_id": hospital_id
        }

    @classmethod
    async def get_doctor_details(
        cls,
        hospital_id: Optional[str],
        doctor_id: Optional[str] = None,
        doctor_name: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Returns safe, professional details of a doctor (name, department, specializations, fee, timings).
        Never exposes password hashes, internal keys, or personal private details.
        """
        if not db or not hospital_id:
            return {"error": "Hospital tenant ID and active DB session required."}

        stmt = (
            select(Doctor, Department)
            .join(Department, Doctor.department_id == Department.id)
            .where(
                Doctor.hospital_id == hospital_id,
                Doctor.is_active == True
            )
        )

        if doctor_id:
            stmt = stmt.where(Doctor.id == doctor_id)
        elif doctor_name:
            stmt = stmt.where(cls._build_name_filter(doctor_name))
        else:
            return {"error": "Either doctor_id or doctor_name must be provided."}

        res = (await db.execute(stmt)).first()
        if not res:
            return {"error": f"Doctor not found in this hospital."}

        doctor, dept = res

        # Specializations
        spec_stmt = select(DoctorSpecialization.specialization).where(DoctorSpecialization.doctor_id == doctor.id)
        specs = (await db.execute(spec_stmt)).scalars().all()

        # Weekly Schedule
        day_map = {1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu", 5: "Fri", 6: "Sat", 7: "Sun"}
        sched_stmt = select(DoctorSchedule).where(DoctorSchedule.doctor_id == doctor.id).order_by(DoctorSchedule.day_of_week.asc())
        schedules = (await db.execute(sched_stmt)).scalars().all()

        timing_list = []
        for s in schedules:
            timing_list.append({
                "day": day_map.get(s.day_of_week, f"Day {s.day_of_week}"),
                "start_time": s.start_time.strftime("%I:%M %p"),
                "end_time": s.end_time.strftime("%I:%M %p"),
                "slot_duration_minutes": s.slot_duration_minutes
            })

        return {
            "doctor_id": doctor.id,
            "doctor_name": f"Dr. {doctor.first_name} {doctor.last_name}".strip(),
            "name": f"Dr. {doctor.first_name} {doctor.last_name}".strip(),
            "department": dept.name,
            "specializations": list(specs) if specs else [dept.name],
            "opd_fee": doctor.opd_fees or 500,
            "license_number": doctor.license_number,
            "schedules": timing_list,
            "hospital_id": hospital_id
        }

    @classmethod
    async def check_doctor_availability(
        cls,
        hospital_id: Optional[str],
        doctor_id: Optional[str] = None,
        doctor_name: Optional[str] = None,
        date_str: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Checks real-time availability of a doctor on a specific date against:
        - Hospital working hours
        - Hospital holidays
        - Doctor weekly shifts
        - Doctor approved leaves
        """
        if not db or not hospital_id:
            return {"error": "Hospital tenant ID and active DB session required."}

        target_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else datetime.now().date()

        # 1. Lookup Doctor
        stmt = (
            select(Doctor, Department)
            .join(Department, Doctor.department_id == Department.id)
            .where(
                Doctor.hospital_id == hospital_id,
                Doctor.is_active == True
            )
        )
        if doctor_id:
            stmt = stmt.where(Doctor.id == doctor_id)
        elif doctor_name:
            stmt = stmt.where(cls._build_name_filter(doctor_name))
        else:
            return {"error": "Doctor name or ID is required."}

        res = (await db.execute(stmt)).first()
        if not res:
            return {"error": f"Doctor '{doctor_name or doctor_id}' not found in this hospital."}

        doctor, dept = res

        # 2. Check Hospital Holiday
        holiday_stmt = select(HospitalHoliday).where(
            HospitalHoliday.hospital_id == hospital_id,
            HospitalHoliday.holiday_date == target_date
        )
        holiday = (await db.execute(holiday_stmt)).scalar_one_or_none()
        if holiday:
            return {
                "doctor_name": f"Dr. {doctor.first_name} {doctor.last_name}",
                "department": dept.name,
                "date": target_date.strftime("%Y-%m-%d"),
                "is_available": False,
                "status": "HOSPITAL_HOLIDAY",
                "reason": f"Hospital closed for {holiday.name}"
            }

        # 3. Check Approved Leave
        leave_stmt = select(DoctorLeave).where(
            DoctorLeave.doctor_id == doctor.id,
            DoctorLeave.status == "APPROVED",
            DoctorLeave.start_date <= target_date,
            DoctorLeave.end_date >= target_date
        )
        leave = (await db.execute(leave_stmt)).scalar_one_or_none()
        if leave:
            return {
                "doctor_name": f"Dr. {doctor.first_name} {doctor.last_name}",
                "department": dept.name,
                "date": target_date.strftime("%Y-%m-%d"),
                "is_available": False,
                "is_on_leave": True,
                "status": "ON_LEAVE",
                "leave_reason": leave.reason or "Approved Leave",
                "leave_period": f"{leave.start_date} to {leave.end_date}"
            }

        # 4. Check Doctor's Shift on this weekday
        day_of_week = target_date.isoweekday()
        sched_stmt = select(DoctorSchedule).where(
            DoctorSchedule.doctor_id == doctor.id,
            DoctorSchedule.day_of_week == day_of_week
        )
        schedules = (await db.execute(sched_stmt)).scalars().all()

        if not schedules and day_of_week == 7:
            return {
                "doctor_name": f"Dr. {doctor.first_name} {doctor.last_name}",
                "department": dept.name,
                "date": target_date.strftime("%Y-%m-%d"),
                "is_available": False,
                "is_off_duty": True,
                "status": "WEEKLY_OFF",
                "note": "Doctor is off duty on Sundays."
            }

        timings_str = "Standard OPD Hours"
        if schedules:
            t_items = [f"{s.start_time.strftime('%I:%M %p')} - {s.end_time.strftime('%I:%M %p')}" for s in schedules]
            timings_str = ", ".join(t_items)

        return {
            "doctor_id": doctor.id,
            "doctor_name": f"Dr. {doctor.first_name} {doctor.last_name}",
            "department": dept.name,
            "date": target_date.strftime("%Y-%m-%d"),
            "is_available": True,
            "is_on_leave": False,
            "status": "ON_DUTY",
            "opd_fee": doctor.opd_fees or 500,
            "timings": timings_str
        }

    @classmethod
    async def get_available_slots(
        cls,
        hospital_id: Optional[str],
        doctor_id: Optional[str] = None,
        doctor_name: Optional[str] = None,
        date_str: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Calculates and returns real live open booking slots for a doctor on a given date.
        Uses SchedulingEngine to verify against working hours, leaves, holidays, and booked appointments.
        """
        if not db or not hospital_id:
            return {"error": "Hospital tenant ID and active DB session required."}

        target_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else datetime.now().date()

        # 1. Resolve Doctor
        stmt = (
            select(Doctor, Department)
            .join(Department, Doctor.department_id == Department.id)
            .where(
                Doctor.hospital_id == hospital_id,
                Doctor.is_active == True
            )
        )
        if doctor_id:
            stmt = stmt.where(Doctor.id == doctor_id)
        elif doctor_name:
            stmt = stmt.where(cls._build_name_filter(doctor_name))
        else:
            return {"error": "Doctor name or doctor_id must be provided."}

        res = (await db.execute(stmt)).first()
        if not res:
            return {"error": f"Doctor '{doctor_name or doctor_id}' not found in this hospital."}

        doctor, dept = res

        # 2. Calculate Real Slots via SchedulingEngine
        scheduling = SchedulingEngine(db)
        slots = await scheduling.get_available_slots(doctor.id, target_date)
        slot_strings = [s.start_time.strftime("%I:%M %p") for s in slots]

        return {
            "doctor_id": doctor.id,
            "doctor_name": f"Dr. {doctor.first_name} {doctor.last_name}".strip(),
            "department": dept.name,
            "date": target_date.strftime("%Y-%m-%d"),
            "opd_fee": doctor.opd_fees or 500,
            "available_slots": slot_strings,
            "total_slots": len(slot_strings),
            "is_fully_booked": len(slot_strings) == 0
        }
