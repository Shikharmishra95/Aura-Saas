import asyncio
import uuid
import requests
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.database.models.conversation import VoiceSession, CallLog

async def test_gather():
    engine = create_async_engine(settings.ASYNC_DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    h_id = "HOSP-BALA-7282"
    call_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())

    async with async_session() as db:
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
        print(f"Seeded session {session_id} in GREETING state")

    await engine.dispose()

    # Make the HTTP request to the running local server
    url = f"http://localhost:8000/api/v1/voice/gather/{session_id}"
    data = {
        "SpeechResult": "मेरा naam shiva hai",
        "From": "+919532399202",
        "To": "+919532399202",
        "hospital_id": h_id
    }
    
    print(f"Sending POST to {url}...")
    try:
        response = requests.post(url, data=data, timeout=180)
        print(f"HTTP Status Code: {response.status_code}")
        print("Response headers:")
        for k, v in response.headers.items():
            print(f"  {k}: {v}")
        print("Response Body:")
        print(response.text)
    except Exception as e:
        print(f"HTTP request failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_gather())
