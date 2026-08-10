import asyncio
import sys
sys.stdout.reconfigure(encoding='utf-8')
from datetime import datetime, date, time
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.engines.appointment import AppointmentEngine

# Import all models to ensure SQLAlchemy mapper resolves names correctly
import app.database.models.appointment
import app.database.models.conversation
import app.database.models.call_log

from app.database.models.appointment import Appointment, Patient

async def test():
    engine = create_async_engine(settings.ASYNC_DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        # Get active doctor CP Tiwari
        doctor_id = "53224cae-13cf-42ac-8e4b-04ead468bef7"
        
        # Create a dummy patient
        p_stmt = select(Patient).where(Patient.hospital_id == "HOSP-BALA-7282")
        patient = (await db.execute(p_stmt)).scalars().first()
        if not patient:
            print("No patient found to test with.")
            return

        # Target date: tomorrow to bypass SAME_DAY_NOT_ALLOWED
        test_date = date(2026, 7, 31)
        appt_time1 = datetime.combine(test_date, time(10, 0)) # 10:00 AM
        appt_time2 = datetime.combine(test_date, time(10, 30)) # 10:30 AM
        appt_time3 = datetime.combine(test_date, time(11, 0)) # 11:00 AM
        
        print(f"Creating mock booked appointments on {test_date} at 10:00 AM, 10:30 AM and 11:00 AM to fill slots...")
        
        # Clean any existing test appointments and patients first
        await db.execute(text("DELETE FROM appointments WHERE id LIKE 'test-appt-%'"))
        await db.execute(text("DELETE FROM patients WHERE id = 'test-temp-patient-2'"))
        await db.flush()
        
        # Create a valid temporary patient
        temp_pat = Patient(
            id="test-temp-patient-2",
            hospital_id="HOSP-BALA-7282",
            first_name="Temp2",
            last_name="Patient2",
            phone="+919999999990",
            gender="Male",
            date_of_birth=date(1990, 1, 1)
        )
        db.add(temp_pat)
        await db.flush()
        
        # Add temporary appointments directly under the valid temporary patient
        a1 = Appointment(
            id="test-appt-1",
            hospital_id="HOSP-BALA-7282",
            patient_id="test-temp-patient-2",
            doctor_id=doctor_id,
            appointment_datetime=appt_time1,
            duration_minutes=30,
            status="SCHEDULED",
            reason="Test booked 1",
            source="VOICE"
        )
        a2 = Appointment(
            id="test-appt-2",
            hospital_id="HOSP-BALA-7282",
            patient_id="test-temp-patient-2",
            doctor_id=doctor_id,
            appointment_datetime=appt_time2,
            duration_minutes=30,
            status="SCHEDULED",
            reason="Test booked 2",
            source="VOICE"
        )
        a3 = Appointment(
            id="test-appt-3",
            hospital_id="HOSP-BALA-7282",
            patient_id="test-temp-patient-2",
            doctor_id=doctor_id,
            appointment_datetime=appt_time3,
            duration_minutes=30,
            status="SCHEDULED",
            reason="Test booked 3",
            source="VOICE"
        )
        
        db.add_all([a1, a2, a3])
        await db.flush()
        
        # Now try to book an appointment at 10:00 AM (which is booked!)
        # This should trigger SLOT_FULL and return up to 3 nearest slots.
        # Doctor has morning slots: 10:00, 10:30, 11:00, 11:30, 12:00, 12:30.
        # Since 10:00, 10:30, 11:00 are booked:
        # Later slots: [11:30, 12:00, 12:30]
        # Earlier slots: []
        # So we should get 11:30 AM, 12:00 PM, and 12:30 PM!
        engine = AppointmentEngine(db)
        
        print("\nTrying to book slot at 10:00 AM (expecting SLOT_FULL)...")
        res = await engine.book_appointment(
            hospital_id="HOSP-BALA-7282",
            patient_id=patient.id,
            doctor_id=doctor_id,
            appointment_datetime=appt_time1,
            reason="Test booking"
        )
        
        print("\nResult Code:", res.get("code"))
        print("Message:", res.get("message"))
        print("Nearest Slots string:", res.get("nearest_slot"))
        
        # Rollback so we don't save mock bookings permanently
        await db.rollback()
        print("\nDatabase rolled back.")

asyncio.run(test())
