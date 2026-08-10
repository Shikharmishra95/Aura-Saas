import asyncio
import uuid
from datetime import datetime, date, timedelta, time, timezone
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.database.models.conversation import VoiceSession, CallLog
from app.database.models.appointment import Hospital, Doctor, Patient, Department, DoctorLeave
from app.engines.voice_state_machine import VoiceStateMachine

async def run_simulation():
    engine = create_async_engine(settings.ASYNC_DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        # Resolve hospital ID
        h_stmt = select(Hospital).where(Hospital.id == "HOSP-BALA-7282")
        hosp = (await db.execute(h_stmt)).scalar_one_or_none()
        if not hosp:
            print("Hospital HOSP-BALA-7282 not found.")
            return

        h_id = hosp.id
        print("=== SIMULATION 1: SUCCESSFUL CALL FLOW ===")
        
        call_log_id = str(uuid.uuid4())
        call_log = CallLog(
            id=call_log_id,
            hospital_id=h_id,
            twilio_call_sid=f"sim_call_{uuid.uuid4().hex[:8]}",
            caller_number="+919999999999",
            receiver_number="+14174733994",
            call_status="ringing",
            start_time=datetime.now(timezone.utc)
        )
        db.add(call_log)
        
        session_id = str(uuid.uuid4())
        session = VoiceSession(
            id=session_id,
            call_log_id=call_log_id,
            session_status="ACTIVE",
            current_state="GREETING"
        )
        db.add(session)
        await db.commit()

        sm = VoiceStateMachine(db)
        
        # Inbound played greeting:
        print("AI (Initial Greeting): नमस्ते! BALAJI HOSPITAL में आपका स्वागत है। मैं यहाँ की अपॉइंटमेंट असिस्टेंट हूँ। क्या मैं आपकी कोई मदद कर सकती हूँ?")
        
        # Turn 1: User says Hello
        print("User: नमस्ते")
        r1 = await sm.process_turn(session_id, "नमस्ते", h_id)
        print(f"AI: {r1}")
        await asyncio.sleep(12)
        
        # Turn 2: User says name
        print("User: मेरा नाम शिवा शर्मा है")
        r2 = await sm.process_turn(session_id, "मेरा नाम शिवा शर्मा है", h_id)
        print(f"AI: {r2}")
        await asyncio.sleep(12)
        
        # Turn 3: User says Cardiology/Heart problem (2 doctors exist in Cardiology)
        print("User: मुझे दिल की बीमारी की जांच करानी है")
        r3 = await sm.process_turn(session_id, "मुझे दिल की बीमारी की जांच करानी है", h_id)
        print(f"AI: {r3}")
        await asyncio.sleep(12)
        
        # Turn 4: User selects doctor
        print("User: डॉक्टर तिवारी")
        r4 = await sm.process_turn(session_id, "डॉक्टर तिवारी", h_id)
        print(f"AI: {r4}")
        await asyncio.sleep(12)
        
        # Turn 5: User chooses date
        print("User: कल आना है")
        r5 = await sm.process_turn(session_id, "कल आना है", h_id)
        print(f"AI: {r5}")
        await asyncio.sleep(12)
        
        # Turn 6: User chooses slot
        print("User: सुबह 11 बजे का समय")
        r6 = await sm.process_turn(session_id, "सुबह 11 बजे का समय", h_id)
        print(f"AI: {r6}")
        await asyncio.sleep(12)
        
        # Turn 7: User confirms booking
        print("User: हाँ, कन्फर्म कर दो")
        r7 = await sm.process_turn(session_id, "हाँ, कन्फर्म कर दो", h_id)
        print(f"AI: {r7}")
        await asyncio.sleep(12)

        print("\n\n=== SIMULATION 2: DOCTOR ON LEAVE FLOW ===")
        # Register a temporary leave for Dr. kamlesh kumar for tomorrow
        # End date of leave is tomorrow, meaning return date is day after tomorrow
        today = date.today()
        tomorrow = today + timedelta(days=1)
        
        # Delete existing leaves for Dr. kamlesh to avoid conflicts
        await db.execute(text("DELETE FROM doctor_leaves WHERE doctor_id = '6e568e8b-03c3-4966-bd35-67da6645e03f'"))
        await db.commit()
        
        leave_id = str(uuid.uuid4())
        leave = DoctorLeave(
            id=leave_id,
            doctor_id="6e568e8b-03c3-4966-bd35-67da6645e03f",
            start_date=tomorrow,
            end_date=tomorrow,
            status="APPROVED",
            reason="Medical Seminar"
        )
        db.add(leave)
        
        call_log_id2 = str(uuid.uuid4())
        call_log2 = CallLog(
            id=call_log_id2,
            hospital_id=h_id,
            twilio_call_sid=f"sim_call_{uuid.uuid4().hex[:8]}",
            caller_number="+918888888888",
            receiver_number="+14174733994",
            call_status="ringing",
            start_time=datetime.now(timezone.utc)
        )
        db.add(call_log2)
        
        session_id2 = str(uuid.uuid4())
        session2 = VoiceSession(
            id=session_id2,
            call_log_id=call_log_id2,
            session_status="ACTIVE",
            current_state="GREETING"
        )
        db.add(session2)
        await db.commit()

        # Turn 1: Inbound plays greeting, user says hello
        print("AI (Initial Greeting): नमस्ते! BALAJI HOSPITAL में आपका स्वागत है।...")
        print("User: हैलो")
        r1_2 = await sm.process_turn(session_id2, "हैलो", h_id)
        print(f"AI: {r1_2}")
        await asyncio.sleep(12)
        
        # Turn 2: User says name
        print("User: मेरा नाम अमन वर्मा है")
        r2_2 = await sm.process_turn(session_id2, "मेरा नाम अमन वर्मा है", h_id)
        print(f"AI: {r2_2}")
        await asyncio.sleep(12)
        
        # Turn 3: User says bones/orthopedics (Orthopedics has 1 doctor: kamlesh kumar)
        print("User: मुझे हड्डियों की समस्या है")
        r3_2 = await sm.process_turn(session_id2, "मुझे हड्डियों की समस्या है", h_id)
        print(f"AI: {r3_2}")
        await asyncio.sleep(12)
        
        # Turn 4: User chooses date (tomorrow, where doctor is on leave)
        print("User: कल आना है")
        r4_2 = await sm.process_turn(session_id2, "कल आना है", h_id)
        print(f"AI: {r4_2}")
        await asyncio.sleep(12)
        
        # Cleanup leave
        await db.execute(text("DELETE FROM doctor_leaves WHERE id = :id"), {"id": leave_id})
        await db.commit()

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(run_simulation())
