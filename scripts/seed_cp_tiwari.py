import asyncio
from datetime import date, time, datetime, timedelta
from sqlalchemy import select, delete
from app.database.session import async_session_factory
from app.database.base import Base
from app.database.models.appointment import Hospital, Department, Doctor, DoctorSchedule, WorkingHour
from app.database.models.conversation import FAQ, DoctorAvailabilityCache
from app.core.config import settings

async def seed_cp_tiwari():
    print("Starting CP Tiwari Hospital database seeding...")
    
    twilio_number = settings.TWILIO_PHONE_NUMBER or "+919532399202"
    
    async with async_session_factory() as db:
        # 1. Seed Hospital
        hospital_stmt = select(Hospital).where(Hospital.id == "hosp_default")
        hospital = (await db.execute(hospital_stmt)).scalar_one_or_none()
        
        if not hospital:
            hospital = Hospital(
                id="hosp_default",
                name="CP Tiwari Hospital",
                slug="cp-tiwari-hospital",
                phone=twilio_number,
                email="contact@cptiwarihospital.com",
                timezone="Asia/Kolkata",
                is_active=True
            )
            db.add(hospital)
            await db.flush()
            print(f"Hospital 'CP Tiwari Hospital' seeded with phone {twilio_number}.")
        else:
            hospital.name = "CP Tiwari Hospital"
            hospital.slug = "cp-tiwari-hospital"
            hospital.phone = twilio_number
            await db.flush()
            print(f"Updated existing hospital name to 'CP Tiwari Hospital' with phone {twilio_number}.")

        # 2. Seed Working Hours (Monday to Friday, 10 AM to 5 PM)
        for day in range(1, 6):
            wh_stmt = select(WorkingHour).where(WorkingHour.hospital_id == hospital.id, WorkingHour.day_of_week == day)
            wh = (await db.execute(wh_stmt)).scalar_one_or_none()
            if not wh:
                wh = WorkingHour(
                    id=f"wh_cp_{day}",
                    hospital_id=hospital.id,
                    day_of_week=day,
                    open_time=time(10, 0),
                    close_time=time(17, 0),
                    is_closed=False
                )
                db.add(wh)
        await db.flush()
        print("Hospital Working Hours (Mon-Fri) seeded.")

        # 3. Seed Departments
        depts_data = {
            "dept_ortho": ("Orthopedics (Haddi)", "Bone, Joint, and Fracture Care"),
            "dept_cardio": ("Cardiology (Heart)", "Heart and Cardiovascular Specialist Care"),
            "dept_eye": ("Ophthalmology (Eye)", "Eye Clinic and Vision Care Specialist")
        }
        
        seeded_depts = {}
        for dept_id, (name, desc) in depts_data.items():
            dept_stmt = select(Department).where(Department.id == dept_id)
            dept = (await db.execute(dept_stmt)).scalar_one_or_none()
            if not dept:
                dept = Department(
                    id=dept_id,
                    hospital_id=hospital.id,
                    name=name,
                    description=desc,
                    is_active=True
                )
                db.add(dept)
            else:
                dept.name = name
                dept.description = desc
            seeded_depts[dept_id] = dept
        await db.flush()
        print("Departments seeded.")

        await db.commit()
        print("CP Tiwari Hospital database seeding completed successfully!")

if __name__ == "__main__":
    asyncio.run(seed_cp_tiwari())
