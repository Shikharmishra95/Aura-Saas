import logging
from typing import Dict, Any, List, Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.appointment import (
    Hospital, Department, Doctor, WorkingHour
)

logger = logging.getLogger("aura.tools.hospital")

class HospitalTools:
    """
    HMS Hospital Information Operational Tools:
    - Returns structured, live hospital metadata (Departments, Doctors fleet, Working Hours, Emergency Contacts).
    """

    @classmethod
    async def get_hospital_information(
        cls,
        hospital_id: Optional[str],
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Retrieves real-time structured hospital directory information from the database.
        """
        if not db or not hospital_id:
            return {"error": "Hospital tenant ID and active DB session required."}

        # 1. Fetch Hospital
        hosp_stmt = select(Hospital).where(Hospital.id == hospital_id, Hospital.is_active == True)
        hospital = (await db.execute(hosp_stmt)).scalar_one_or_none()
        if not hospital:
            return {"error": f"Hospital '{hospital_id}' not found or inactive."}

        # 2. Fetch Departments & Doctor Counts
        dept_stmt = select(Department).where(Department.hospital_id == hospital_id, Department.is_active == True)
        departments = (await db.execute(dept_stmt)).scalars().all()

        dept_list = []
        for d in departments:
            doc_cnt_stmt = select(func.count(Doctor.id)).where(
                Doctor.department_id == d.id,
                Doctor.is_active == True
            )
            doc_count = (await db.execute(doc_cnt_stmt)).scalar() or 0
            dept_list.append({
                "department_id": d.id,
                "name": d.name,
                "description": d.description or "General Medical Wing",
                "active_doctors": doc_count,
                "phone_extension": d.phone_extension
            })

        # 3. Fetch Working Hours
        day_map = {1: "Monday", 2: "Tuesday", 3: "Wednesday", 4: "Thursday", 5: "Friday", 6: "Saturday", 7: "Sunday"}
        wh_stmt = select(WorkingHour).where(WorkingHour.hospital_id == hospital_id).order_by(WorkingHour.day_of_week.asc())
        working_hours = (await db.execute(wh_stmt)).scalars().all()

        hours_list = []
        for wh in working_hours:
            hours_list.append({
                "day": day_map.get(wh.day_of_week, f"Day {wh.day_of_week}"),
                "open_time": wh.open_time.strftime("%I:%M %p") if wh.open_time else "09:00 AM",
                "close_time": wh.close_time.strftime("%I:%M %p") if wh.close_time else "09:00 PM",
                "is_closed": wh.is_closed
            })

        # Total Active Doctors
        total_docs_stmt = select(func.count(Doctor.id)).where(Doctor.hospital_id == hospital_id, Doctor.is_active == True)
        total_docs = (await db.execute(total_docs_stmt)).scalar() or 0

        return {
            "hospital_id": hospital.id,
            "hospital_name": hospital.name.strip() if hospital.name else "Hospital",
            "address": hospital.address or "Main Campus",
            "contact_phone": hospital.phone,
            "email": hospital.email or "support@hospital.com",
            "subscription_tier": hospital.subscription_plan,
            "total_departments": len(dept_list),
            "total_doctors": total_docs,
            "total_active_doctors": total_docs,
            "departments": dept_list,
            "working_hours": hours_list if hours_list else [{"general": "Monday-Saturday 09:00 AM - 08:00 PM, Emergency 24x7"}],
            "emergency_services": "24x7 Casualty & Trauma Unit Active"
        }
