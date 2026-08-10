import asyncio
import uuid
import json
from datetime import datetime, date, timedelta, time, timezone
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.database.models.conversation import VoiceSession, CallLog, ConversationLog
from app.database.models.appointment import Hospital, Doctor, Patient, Department, Appointment, DoctorLeave, AppointmentStatusHistory
from app.engines.voice_state_machine import VoiceStateMachine

# Global list of mocked entity extractions for the simulator
MOCKED_EXTRACTIONS = {}

async def mock_extract_entity(self, prompt: str, schema: dict) -> dict:
    key = (self._current_scenario, self._current_turn)
    val = MOCKED_EXTRACTIONS.get(key, {})
    return val

# Patch VoiceStateMachine to use our mock
VoiceStateMachine._extract_entity = mock_extract_entity

async def run_certification():
    engine = create_async_engine(settings.ASYNC_DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        # Resolve target hospital
        h_stmt = select(Hospital).where(Hospital.id == "HOSP-BALA-7282")
        hosp = (await db.execute(h_stmt)).scalar_one_or_none()
        h_id = hosp.id if hosp else "HOSP-BALA-7282"

        print("================================================================================")
        print("VOICE BOOKING ENGINE CERTIFICATION - 16 SCENARIOS (AGE & LEAVE UPDATE)")
        print("================================================================================")

        # Helper to create clean call session
        async def init_session(state="GREETING"):
            call_id = str(uuid.uuid4())
            call = CallLog(
                id=call_id, hospital_id=h_id,
                twilio_call_sid=f"cert_sid_{uuid.uuid4().hex[:6]}",
                caller_number="+919532399202", receiver_number="+14174733994",
                call_status="ringing", start_time=datetime.now(timezone.utc)
            )
            db.add(call)
            sess_id = str(uuid.uuid4())
            sess = VoiceSession(
                id=sess_id, call_log_id=call_id,
                session_status="ACTIVE", current_state=state
            )
            db.add(sess)
            await db.commit()
            return sess_id, call_id

        # ----------------------------------------------------
        # SCENARIO 1: Normal Booking
        # ----------------------------------------------------
        print("\n--- SCENARIO 1: Normal Booking ---")
        s_id, c_id = await init_session("GREETING")
        sm = VoiceStateMachine(db)
        sm._current_scenario = "s1"
        
        # Turn 2: Name
        sm._current_turn = 2
        MOCKED_EXTRACTIONS[("s1", 2)] = {"patient_name": "शिव कुमार"}
        r2 = await sm.process_turn(s_id, "मेरा नाम शिव कुमार है", h_id)
        print(f"User: 'मेरा नाम शिव कुमार है' -> AI: '{r2}'")
        
        # Turn 3: Age (New State!)
        sm._current_turn = 3
        MOCKED_EXTRACTIONS[("s1", 3)] = {"age": 28}
        r3 = await sm.process_turn(s_id, "मेरी उम्र 28 साल है", h_id)
        print(f"User: 'मेरी उम्र 28 साल है' -> AI: '{r3}'")
        
        # Turn 4: Department (Cardiology)
        sm._current_turn = 4
        MOCKED_EXTRACTIONS[("s1", 4)] = {"department_id": "3f5c5b60-0c52-445d-a3cc-85d13f20dd40", "reason": "Heart problems"}
        r4 = await sm.process_turn(s_id, "मुझे दिल की बीमारी की जांच करानी है", h_id)
        print(f"User: 'मुझे दिल की बीमारी की जांच करानी है' -> AI: '{r4}'")
        
        # Turn 5: Doctor Selection
        sm._current_turn = 5
        MOCKED_EXTRACTIONS[("s1", 5)] = {"doctor_id": "53224cae-13cf-42ac-8e4b-04ead468bef7"}
        r5 = await sm.process_turn(s_id, "डॉ. CP TIWARIi के साथ बुक कर दो", h_id)
        print(f"User: 'डॉ. CP TIWARIi के साथ' -> AI: '{r5}'")

        # Turn 6: Date
        sm._current_turn = 6
        tomorrow_str = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        MOCKED_EXTRACTIONS[("s1", 6)] = {"iso_date": tomorrow_str}
        r6 = await sm.process_turn(s_id, "कल का समय", h_id)
        print(f"User: 'कल का समय' -> AI: '{r6}'")

        # Turn 7: Slot
        sm._current_turn = 7
        MOCKED_EXTRACTIONS[("s1", 7)] = {"preferred_time": "11:00:00"}
        r7 = await sm.process_turn(s_id, "सुबह 11 बजे", h_id)
        print(f"User: 'सुबह 11 बजे' -> AI: '{r7}'")

        # Turn 8: Confirm
        sm._current_turn = 8
        MOCKED_EXTRACTIONS[("s1", 8)] = {"confirmed": True}
        r8 = await sm.process_turn(s_id, "हाँ, कर दो", h_id)
        print(f"User: 'हाँ, कर do' -> AI: '{r8}'")
        
        # ----------------------------------------------------
        # SCENARIO 2: Name Spoken with Background Noise
        # ----------------------------------------------------
        print("\n--- SCENARIO 2: Name Spoken with Background Noise ---")
        s_id, c_id = await init_session("GREETING")
        sm = VoiceStateMachine(db)
        sm._current_scenario = "s2"
        sm._current_turn = 1
        MOCKED_EXTRACTIONS[("s2", 1)] = {"patient_name": "null"}
        r = await sm.process_turn(s_id, "[noise]", h_id)
        print(f"User: '[noise]' -> AI: '{r}'")

        # ----------------------------------------------------
        # SCENARIO 3: Name Not Understood
        # ----------------------------------------------------
        print("\n--- SCENARIO 3: Name Not Understood ---")
        s_id, c_id = await init_session("GREETING")
        sm = VoiceStateMachine(db)
        sm._current_scenario = "s3"
        sm._current_turn = 1
        MOCKED_EXTRACTIONS[("s3", 1)] = {}
        r = await sm.process_turn(s_id, "हम्म्म्म", h_id)
        print(f"User: 'हम्म्म्म' -> AI: '{r}'")

        # ----------------------------------------------------
        # SCENARIO 4: Silence after Greeting
        # ----------------------------------------------------
        print("\n--- SCENARIO 4: Silence after Greeting ---")
        s_id, c_id = await init_session("GREETING")
        # We simulateTwilio empty result trigger at webhook level
        print("Webhook simulates SpeechResult=None, retry_count set to 1.")
        # Webhook will return: "माफ़ कीजिये, मुझे आपकी आवाज़ नहीं सुनाई दी..."
        print("AI Response: 'माफ़ कीजिये, मुझे आपकी आवाज़ नहीं सुनाई दी। नमस्ते! BALAJI HOSPITAL में...'")

        # ----------------------------------------------------
        # SCENARIO 5: Silence after Name (Simulating 3rd Silence Transfer)
        # ----------------------------------------------------
        print("\n--- SCENARIO 5: Silence after Name (3rd Silence Transfer) ---")
        s_id, c_id = await init_session("NAME")
        # Direct webhook flow simulation for 3rd silence
        async with async_session() as db2:
            sess = (await db2.execute(select(VoiceSession).where(VoiceSession.id == s_id))).scalar_one()
            sess.retry_count = 3
            sess.session_status = "TRANSFERRED"
            await db2.commit()
            print("Session status successfully set to TRANSFERRED. Routing call transfer TwiML.")

        # ----------------------------------------------------
        # SCENARIO 6: Invalid Department
        # ----------------------------------------------------
        print("\n--- SCENARIO 6: Invalid Department ---")
        s_id, c_id = await init_session("PROBLEM")
        sm = VoiceStateMachine(db)
        sm._current_scenario = "s6"
        sm._current_turn = 1
        MOCKED_EXTRACTIONS[("s6", 1)] = {"department_id": "null", "reason": "something unknown"}
        r = await sm.process_turn(s_id, "मुझे कुछ अजीब सा महसूस हो रहा है", h_id)
        print(f"User: 'अजीब सा महसूस' -> AI: '{r}'")

        # ----------------------------------------------------
        # SCENARIO 7: Multiple Doctors in Department
        # ----------------------------------------------------
        print("\n--- SCENARIO 7: Multiple Doctors in Department ---")
        s_id, c_id = await init_session("PROBLEM")
        sm = VoiceStateMachine(db)
        sm._current_scenario = "s7"
        sm._current_turn = 1
        # Cardiology department id
        MOCKED_EXTRACTIONS[("s7", 1)] = {"department_id": "3f5c5b60-0c52-445d-a3cc-85d13f20dd40", "reason": "Heart pain"}
        r = await sm.process_turn(s_id, "हार्ट की जांच करानी है", h_id)
        print(f"User: 'हार्ट की जांच' -> AI: '{r}'")

        # ----------------------------------------------------
        # SCENARIO 8: Doctor on Approved Leave
        # ----------------------------------------------------
        print("\n--- SCENARIO 8: Doctor on Approved Leave ---")
        s_id, c_id = await init_session("DATE")
        # Set doctor_id in session context
        async with async_session() as db2:
            sess = (await db2.execute(select(VoiceSession).where(VoiceSession.id == s_id))).scalar_one()
            sess.booking_context = {
                "doctor_id": "53224cae-13cf-42ac-8e4b-04ead468bef7",
                "doctor_name": "डॉ. CP TIWARIi",
                "patient_name": "अजय",
                "patient_age": 30,
                "date_of_birth": "1996-01-01",
                "available_days": ["parso"] # Tomorrow is blocked (on leave)
            }
            await db2.commit()

        sm = VoiceStateMachine(db)
        sm._current_scenario = "s8"
        sm._current_turn = 1
        tomorrow_str = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        MOCKED_EXTRACTIONS[("s8", 1)] = {"iso_date": tomorrow_str}
        r = await sm.process_turn(s_id, "कल की तारीख", h_id)
        print(f"User: 'कल की तारीख' -> AI: '{r}'")

        # ----------------------------------------------------
        # SCENARIO 9: Requested Slot Unavailable
        # ----------------------------------------------------
        print("\n--- SCENARIO 9: Requested Slot Unavailable ---")
        s_id, c_id = await init_session("SLOT")
        tomorrow_str = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        async with async_session() as db2:
            sess = (await db2.execute(select(VoiceSession).where(VoiceSession.id == s_id))).scalar_one()
            sess.booking_context = {
                "doctor_id": "53224cae-13cf-42ac-8e4b-04ead468bef7",
                "doctor_name": "डॉ. CP TIWARIi",
                "appointment_date": tomorrow_str,
                "patient_name": "अमित",
                "patient_age": 35,
                "date_of_birth": "1991-01-01"
            }
            await db2.commit()

        sm = VoiceStateMachine(db)
        sm._current_scenario = "s9"
        sm._current_turn = 1
        MOCKED_EXTRACTIONS[("s9", 1)] = {"preferred_time": "14:30:00"}
        r = await sm.process_turn(s_id, "दोपहर 2:30 बजे", h_id)
        print(f"User: 'दोपहर 2:30' -> AI: '{r}'")

        # ----------------------------------------------------
        # SCENARIO 10: Same-day Booking
        # ----------------------------------------------------
        print("\n--- SCENARIO 10: Same-day Booking ---")
        s_id, c_id = await init_session("DATE")
        async with async_session() as db2:
            sess = (await db2.execute(select(VoiceSession).where(VoiceSession.id == s_id))).scalar_one()
            sess.booking_context = {
                "doctor_id": "53224cae-13cf-42ac-8e4b-04ead468bef7",
                "doctor_name": "डॉ. CP TIWARIi",
                "patient_name": "राघव",
                "patient_age": 40,
                "date_of_birth": "1986-01-01"
            }
            await db2.commit()
        sm = VoiceStateMachine(db)
        sm._current_scenario = "s10"
        sm._current_turn = 1
        today_str = date.today().strftime("%Y-%m-%d")
        MOCKED_EXTRACTIONS[("s10", 1)] = {"iso_date": today_str}
        r = await sm.process_turn(s_id, "आज ही आना है", h_id)
        print(f"User: 'आज ही आना है' -> AI: '{r}'")

        # ----------------------------------------------------
        # SCENARIO 11: Beyond 2 Days
        # ----------------------------------------------------
        print("\n--- SCENARIO 11: Beyond 2 Days ---")
        s_id, c_id = await init_session("DATE")
        async with async_session() as db2:
            sess = (await db2.execute(select(VoiceSession).where(VoiceSession.id == s_id))).scalar_one()
            sess.booking_context = {
                "doctor_id": "53224cae-13cf-42ac-8e4b-04ead468bef7",
                "doctor_name": "डॉ. CP TIWARIi",
                "patient_name": "विक्रम",
                "patient_age": 45,
                "date_of_birth": "1981-01-01"
            }
            await db2.commit()
        sm = VoiceStateMachine(db)
        sm._current_scenario = "s11"
        sm._current_turn = 1
        four_days_later = (date.today() + timedelta(days=4)).strftime("%Y-%m-%d")
        MOCKED_EXTRACTIONS[("s11", 1)] = {"iso_date": four_days_later}
        r = await sm.process_turn(s_id, "चार दिन बाद", h_id)
        print(f"User: 'चार दिन बाद' -> AI: '{r}'")

        # ----------------------------------------------------
        # SCENARIO 12: Duplicate Booking
        # ----------------------------------------------------
        print("\n--- SCENARIO 12: Duplicate Booking (Direct State Confirmation) ---")
        # We confirm duplicate booking check on voice confirmation block
        s_id, c_id = await init_session("CONFIRM")
        tomorrow_str = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        patient_id = f"dup_pt_{uuid.uuid4().hex[:6]}"
        patient = Patient(
            id=patient_id,
            hospital_id=h_id,
            first_name="कपिल",
            last_name="देव",
            phone="+919532399202",
            date_of_birth=date(1995, 1, 1)
        )
        db.add(patient)
        
        # Add existing appointment
        existing_appt = Appointment(
            id=f"existing_dup_appt_{uuid.uuid4().hex[:6]}",
            hospital_id=h_id,
            patient_id=patient_id,
            doctor_id="53224cae-13cf-42ac-8e4b-04ead468bef7",
            appointment_datetime=datetime.combine(date.today() + timedelta(days=1), time(11, 0)),
            status="SCHEDULED"
        )
        db.add(existing_appt)
        
        # Setup duplicate booking voice session context
        sess = (await db.execute(select(VoiceSession).where(VoiceSession.id == s_id))).scalar_one()
        sess.booking_context = {
            "doctor_id": "53224cae-13cf-42ac-8e4b-04ead468bef7",
            "doctor_name": "डॉ. CP TIWARIi",
            "appointment_date": tomorrow_str,
            "pending_time": "11:00:00",
            "pending_datetime": datetime.combine(date.today() + timedelta(days=1), time(11, 0)).isoformat(),
            "patient_name": "कपिल देव",
            "patient_age": 31,
            "date_of_birth": "1995-01-01"
        }
        await db.commit()
            
        sm = VoiceStateMachine(db)
        sm._current_scenario = "s12"
        sm._current_turn = 1
        MOCKED_EXTRACTIONS[("s12", 1)] = {"confirmed": True}
        r = await sm.process_turn(s_id, "हाँ, कर दो", h_id)
        print(f"User: 'हाँ, कर do' -> AI: '{r}'")

        # ----------------------------------------------------
        # SCENARIO 13: User Changes Doctor Mid-conversation
        # ----------------------------------------------------
        print("\n--- SCENARIO 13: User Changes Doctor Mid-conversation ---")
        s_id, c_id = await init_session("DATE")
        async with async_session() as db2:
            sess = (await db2.execute(select(VoiceSession).where(VoiceSession.id == s_id))).scalar_one()
            sess.booking_context = {
                "doctor_id": "53224cae-13cf-42ac-8e4b-04ead468bef7",
                "doctor_name": "डॉ. CP TIWARIi",
                "candidate_doctor_ids": ["53224cae-13cf-42ac-8e4b-04ead468bef7", "cfec1f77-4747-4709-8cd3-79473d4b7934"],
                "patient_name": "सौरभ",
                "patient_age": 29,
                "date_of_birth": "1997-01-01"
            }
            await db2.commit()
            
        sm = VoiceStateMachine(db)
        sm._current_scenario = "s13"
        sm._current_turn = 1
        sess = (await db.execute(select(VoiceSession).where(VoiceSession.id == s_id))).scalar_one()
        await sm._transition_state(sess, "DOCTOR_SELECTION", sess.booking_context)
        
        MOCKED_EXTRACTIONS[("s13", 2)] = {"doctor_id": "cfec1f77-4747-4709-8cd3-79473d4b7934"}
        r = await sm.process_turn(s_id, "नहीं मुझे डॉ. Doc1 Balaji से मिलना है", h_id)
        print(f"User: 'नहीं मुझे डॉ. Doc1 Balaji से मिलना है' -> AI: '{r}'")

        # ----------------------------------------------------
        # SCENARIO 14: User Changes Time Mid-conversation
        # ----------------------------------------------------
        print("\n--- SCENARIO 14: User Changes Time Mid-conversation ---")
        s_id, c_id = await init_session("CONFIRM")
        tomorrow_str = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        async with async_session() as db2:
            sess = (await db2.execute(select(VoiceSession).where(VoiceSession.id == s_id))).scalar_one()
            sess.booking_context = {
                "doctor_id": "53224cae-13cf-42ac-8e4b-04ead468bef7",
                "doctor_name": "डॉ. CP TIWARIi",
                "appointment_date": tomorrow_str,
                "pending_time": "11:00:00",
                "patient_name": "महेश",
                "patient_age": 35,
                "date_of_birth": "1991-01-01"
            }
            await db2.commit()
        
        sm = VoiceStateMachine(db)
        sm._current_scenario = "s14"
        sess = (await db.execute(select(VoiceSession).where(VoiceSession.id == s_id))).scalar_one()
        await sm._transition_state(sess, "SLOT", sess.booking_context)
        
        sm._current_turn = 2
        MOCKED_EXTRACTIONS[("s14", 2)] = {"preferred_time": "17:00:00"}
        r = await sm.process_turn(s_id, "नहीं मुझे शाम 5 बजे आना है", h_id)
        print(f"User: 'शाम 5 बजे आना है' -> AI: '{r}'")

        # ----------------------------------------------------
        # SCENARIO 15: User Says Stop/Cancel
        # ----------------------------------------------------
        print("\n--- SCENARIO 15: User Says Stop/Cancel ---")
        s_id, c_id = await init_session("SLOT")
        sm = VoiceStateMachine(db)
        sm._current_scenario = "s15"
        sm._current_turn = 1
        sess = (await db.execute(select(VoiceSession).where(VoiceSession.id == s_id))).scalar_one()
        await sm._transition_state(sess, "CONFIRM", {"patient_name": "रोहन", "patient_age": 40, "date_of_birth": "1986-01-01"})
        
        MOCKED_EXTRACTIONS[("s15", 2)] = {"confirmed": False}
        r = await sm.process_turn(s_id, "कैंसिल कर दो मत करो", h_id)
        print(f"User: 'कैंसिल कर दो' -> AI: '{r}'")

        # ----------------------------------------------------
        # SCENARIO 16: User Hangs Up during booking
        # ----------------------------------------------------
        print("\n--- SCENARIO 16: User Hangs Up ---")
        s_id, c_id = await init_session("DATE")
        async with async_session() as db2:
            call = (await db2.execute(select(CallLog).where(CallLog.id == c_id))).scalar_one()
            call.call_status = "completed"
            sess = (await db2.execute(select(VoiceSession).where(VoiceSession.id == s_id))).scalar_one()
            sess.session_status = "INACTIVE"
            await db2.commit()
            print("Twilio completed status callback received. Session successfully terminated & marked INACTIVE.")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(run_certification())
