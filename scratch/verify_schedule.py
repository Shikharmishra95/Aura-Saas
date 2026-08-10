import asyncio
import uuid
from datetime import time
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text, select
from sqlalchemy.orm import sessionmaker

from app.database.models.appointment import Doctor, DoctorSchedule

logging.basicConfig(level=logging.INFO)

async def main():
    engine = create_async_engine(
        'mysql+aiomysql://root:ZvNIsPJkPHVgYApdcNoIUPxXHrTMmSKL@tokaido.proxy.rlwy.net:11118/railway',
        echo=True  # This will print the exact SQL executed
    )
    
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        # Find a doctor
        doc_stmt = select(Doctor).limit(1)
        doctor = (await db.execute(doc_stmt)).scalar_one_or_none()
        if not doctor:
            print("No doctor found")
            return
            
        print(f"Testing with Doctor: {doctor.first_name} (ID: {doctor.id})")
        
        # User payload
        slot_duration_minutes = 30
        schedule_days = "1,3,5,6" # Mon=1, Wed=3, Fri=5, Sat=6
        t_start = time(10, 0)
        t_end = time(13, 0)
        t_start_2 = None
        t_end_2 = None
        
        # EXACT CODE from update_doctor_profile
        # Clear old schedules
        del_stmt = select(DoctorSchedule).where(DoctorSchedule.doctor_id == doctor.id)
        old_scheds = (await db.execute(del_stmt)).scalars().all()
        for osc in old_scheds:
            await db.delete(osc)
        
        await db.flush()
        
        days = [int(d.strip()) for d in schedule_days.split(',') if d.strip().isdigit()]
        for day in days:
            s1 = DoctorSchedule(
                id=str(uuid.uuid4()),
                doctor_id=doctor.id,
                day_of_week=day,
                start_time=t_start,
                end_time=t_end,
                slot_duration_minutes=slot_duration_minutes
            )
            db.add(s1)
            
        await db.flush()
        await db.commit()
        
        # Fetch DB rows after commit
        print("\n--- DB Rows After Commit ---")
        final_scheds = (await db.execute(select(DoctorSchedule).where(DoctorSchedule.doctor_id == doctor.id))).scalars().all()
        print(f"Count of schedules inserted: {len(final_scheds)}")
        for s in final_scheds:
            print(f"- Day {s.day_of_week}: {s.start_time} to {s.end_time} ({s.slot_duration_minutes} mins)")
            
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
