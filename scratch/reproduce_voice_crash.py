import asyncio
import sys
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.database.models.conversation import VoiceSession, CallLog
from app.engines.voice_state_machine import VoiceStateMachine

# Monkey patch _extract_entity to simulate a successful entity extraction
async def mock_extract_entity(self, prompt: str, schema: dict) -> dict:
    print(f"[Mock Gemini] Extracting from prompt: '{prompt}'")
    return {"patient_name": "Shiva"}

VoiceStateMachine._extract_entity = mock_extract_entity

async def reproduce():
    sys.stdout.reconfigure(encoding='utf-8')
    engine = create_async_engine(settings.ASYNC_DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        h_id = "HOSP-BALA-7282"
        
        # Create a mock call log
        import uuid
        call_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())
        
        call_log = CallLog(
            id=call_id,
            hospital_id=h_id,
            caller_number="+919532399202",
            receiver_number="+919532399202",
            twilio_call_sid=f"CA_mock_{uuid.uuid4().hex[:8]}",
            call_status="ringing"
        )
        db.add(call_log)
        
        session = VoiceSession(
            id=session_id,
            call_log_id=call_id,
            current_state="GREETING",
            booking_context={}
        )
        db.add(session)
        await db.commit()
        
        print(f"Created mock VoiceSession: {session_id} in GREETING state")
        
        # 2. Instantiate state machine and process the turn
        sm = VoiceStateMachine(db)
        print("Processing turn: 'मेरा naam shiva hai'...")
        try:
            response = await sm.process_turn(session_id, "मेरा naam shiva hai", h_id)
            print(f"SM Response: {response}")
            
            # Fetch updated session state
            stmt = select(VoiceSession).where(VoiceSession.id == session_id)
            updated_session = (await db.execute(stmt)).scalar_one_or_none()
            print(f"State after turn: {updated_session.current_state}")
            print(f"Booking context after turn: {updated_session.booking_context}")
            
        except Exception as e:
            import traceback
            print("CRASH DETECTED:")
            print(f"Exception Type: {type(e).__name__}")
            print(f"Exception Message: {str(e)}")
            traceback.print_exc()

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(reproduce())
