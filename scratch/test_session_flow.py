import asyncio
import uuid
import json
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.database.models.conversation import VoiceSession, CallLog

async def test():
    engine = create_async_engine(settings.ASYNC_DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        # Create call log and session
        call_id = str(uuid.uuid4())
        call = CallLog(
            id=call_id, hospital_id="HOSP-BALA-7282",
            twilio_call_sid=f"test_{uuid.uuid4().hex[:6]}",
            caller_number="+919999999999", receiver_number="+14174733994",
            call_status="ringing"
        )
        db.add(call)
        sess_id = str(uuid.uuid4())
        sess = VoiceSession(
            id=sess_id, call_log_id=call_id,
            session_status="ACTIVE", current_state="GREETING"
        )
        db.add(sess)
        await db.commit()

        # Turn 1: GREETING -> PROBLEM
        print("--- Turn 1 ---")
        sess_stmt = select(VoiceSession).where(VoiceSession.id == sess_id)
        s1 = (await db.execute(sess_stmt)).scalar_one()
        print(f"Loaded s1: state={s1.current_state}, ctx={s1.booking_context}")
        
        ctx = s1.booking_context or {}
        ctx["patient_name"] = "Shiv Kumar"
        s1.current_state = "PROBLEM"
        s1.booking_context = json.loads(json.dumps(ctx))
        db.add(s1)
        await db.commit()
        print(f"Committed Turn 1.")

        # Turn 2: PROBLEM -> DOCTOR_SELECTION
        print("\n--- Turn 2 ---")
        s2 = (await db.execute(sess_stmt)).scalar_one()
        print(f"Loaded s2: state={s2.current_state}, ctx={s2.booking_context}")
        
        ctx2 = s2.booking_context or {}
        ctx2["department_id"] = "cardio"
        ctx2["candidate_doctor_ids"] = ["doc1", "doc2"]
        s2.current_state = "DOCTOR_SELECTION"
        s2.booking_context = json.loads(json.dumps(ctx2))
        db.add(s2)
        await db.commit()
        print(f"Committed Turn 2.")

        # Turn 3: DOCTOR_SELECTION -> DATE
        print("\n--- Turn 3 ---")
        s3 = (await db.execute(sess_stmt)).scalar_one()
        print(f"Loaded s3: state={s3.current_state}, ctx={s3.booking_context}")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test())
