import asyncio
import base64
import json
import uuid
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, Form, WebSocket, WebSocketDisconnect, Response, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_
from app.database.session import get_db
from app.database.models.conversation import CallLog, VoiceSession
from app.database.models.appointment import Hospital, Patient, Doctor
from app.services.twilio_service import TwilioService
from app.services.gemini_live import GeminiLiveClient
from app.utils.audio import ulaw_to_pcm, pcm_to_ulaw, resample_pcm, calculate_amplitude
from app.engines.scheduling import SchedulingEngine
from app.engines.appointment import AppointmentEngine
from app.managers.prompt import PromptManager
from app.core.logging import twilio_logger
from app.core.config import settings

router = APIRouter()
twilio_service = TwilioService()

@router.post("/inbound")
async def handle_inbound_call(
    From: str = Form(...),
    To: str = Form(...),
    CallSid: str = Form(...),
    CallStatus: str = Form(...),
    hospital_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Twilio incoming voice webhook endpoint. Initiates logs, creates session, and returns streaming TwiML response."""
    twilio_logger.info(f"Incoming call webhook received from caller: {From} to line: {To} (target hospital: {hospital_id})")
    
    try:
        hospital = None
        if hospital_id:
            h_stmt = select(Hospital).where(Hospital.id == hospital_id)
            hospital = (await db.execute(h_stmt)).scalar_one_or_none()

        if not hospital:
            hospital_stmt = select(Hospital).where(Hospital.phone == To)
            hospital = (await db.execute(hospital_stmt)).scalar_one_or_none()

        if not hospital:
            # Try matching by Twilio helpline number stored in HospitalSetting
            from app.database.models.appointment import HospitalSetting
            hs_stmt = select(HospitalSetting).where(
                HospitalSetting.setting_key == "twilio_helpline",
                HospitalSetting.setting_value == To
            )
            hs = (await db.execute(hs_stmt)).scalar_one_or_none()
            if hs:
                h_stmt2 = select(Hospital).where(Hospital.id == hs.hospital_id)
                hospital = (await db.execute(h_stmt2)).scalar_one_or_none()

        if not hospital:
            twilio_logger.error(f"No hospital found for Twilio number: {To}. Rejecting call.")
            fallback_twiml = twilio_service.generate_hangup_twiml(
                "क्षमा करें, इस नंबर पर अभी सेवा उपलब्ध नहीं है। कृपया हेल्पलाइन पर कॉल करें।"
            )
            return Response(content=fallback_twiml, media_type="text/xml")

        # Subscription & active status verification
        now_dt = datetime.now()
        is_plan_expired = bool(hospital.plan_expires_at and hospital.plan_expires_at < now_dt)
        if not hospital.is_active or is_plan_expired or not hospital.ai_voice_enabled:
            twilio_logger.warning(f"Hospital {hospital.name} ({hospital.id}) cannot receive voice calls (active={hospital.is_active}, expired={is_plan_expired}, voice_enabled={hospital.ai_voice_enabled}). Rejecting call.")
            if is_plan_expired:
                msg = f"नमस्कार। {hospital.name} की टेलीफोन बुकिंग सेवा वर्तमान में अस्थायी रूप से स्थगित है। कृपया अस्पताल फ्रंट डेस्क पर सीधे संपर्क करें।"
            else:
                msg = "क्षमा करें, यह अस्पताल खाता वर्तमान में निष्क्रिय है। कृपया बाद में प्रयास करें।"
            suspension_twiml = twilio_service.generate_hangup_twiml(msg)
            return Response(content=suspension_twiml, media_type="text/xml")

        hospital_id = hospital.id

        # 3. Create Call Log Record
        call_log_id = str(uuid.uuid4())
        call_log = CallLog(
            id=call_log_id,
            hospital_id=hospital_id,
            twilio_call_sid=CallSid,
            caller_number=From,
            receiver_number=To,
            call_status=CallStatus,
            start_time=datetime.now(timezone.utc)
        )
        db.add(call_log)

        # 4. Create Voice Session Record
        voice_session_id = str(uuid.uuid4())
        voice_session = VoiceSession(
            id=voice_session_id,
            call_log_id=call_log_id,
            session_status="ACTIVE",
            current_state="GREETING"
        )
        db.add(voice_session)
        await db.commit()

        # Log transition into GREETING state
        import json
        from app.core.logging import request_id_context
        log_data = {
            "event": "voice_state_transition",
            "session_id": voice_session_id,
            "from_state": None,
            "to_state": "GREETING",
            "context": {}
        }
        req_id = request_id_context.get()
        if req_id:
            log_data["request_id"] = req_id
        twilio_logger.info(json.dumps(log_data))

        # Fetch hospital object for dynamic greeting
        h_name = hospital.name if hospital else "हॉस्पिटल"

        greeting = f"नमस्ते! {h_name} में आपका स्वागत है। मैं यहाँ की अपॉइंटमेंट असिस्टेंट हूँ। कृपया अपना पूरा नाम बताइए।"
        twiml = twilio_service.generate_gather_twiml(voice_session_id, greeting, hospital_id=hospital_id)
        return Response(content=twiml, media_type="text/xml")
    except Exception as e:
        twilio_logger.error(f"Error handling inbound call webhook: {str(e)}")
        fallback_twiml = twilio_service.generate_hangup_twiml("क्षमा करें, हमारे सर्वर में तकनीकी समस्या है। कृपया कुछ समय बाद पुनः प्रयास करें।")
        return Response(content=fallback_twiml, media_type="text/xml")

@router.post("/gather/{voice_session_id}")
async def handle_speech_gather(
    voice_session_id: str,
    SpeechResult: Optional[str] = Form(None),
    From: Optional[str] = Form(None),
    To: Optional[str] = Form(None),
    hospital_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Processes speech input from Twilio Gather, routes to Gemini LLM, and returns TwiML audio response."""
    twilio_logger.info(f"Speech gather received for session {voice_session_id}. User said: '{SpeechResult}'")
    
    h_id = hospital_id

    # FIRST resolve hospital_id from session/call_log before anything else
    session_stmt = select(VoiceSession).where(VoiceSession.id == voice_session_id)
    session = (await db.execute(session_stmt)).scalar_one_or_none()
    
    call_log = None
    if session:
        call_stmt = select(CallLog).where(CallLog.id == session.call_log_id)
        call_log = (await db.execute(call_stmt)).scalar_one_or_none()

    if call_log:
        h_id = call_log.hospital_id
    elif not h_id:
        twilio_logger.error(f"Cannot determine hospital for session {voice_session_id}. Aborting.")
        error_twiml = twilio_service.generate_hangup_twiml("तकनीकी समस्या। कृपया पुनः प्रयास करें।")
        return Response(content=error_twiml, media_type="text/xml")
    caller_phone = call_log.caller_number if call_log else (From or "")

    # Save user speech log and check silence/empty speech
    from app.database.models.conversation import ConversationLog
    import uuid as _log_uuid

    if not SpeechResult or not SpeechResult.strip():
        twilio_logger.warning(f"Empty SpeechResult for session {voice_session_id}, h_id={h_id}")
        if session:
            session.retry_count = (session.retry_count or 0) + 1
            await db.commit()

            # Retrieve previous prompt from ConversationLog
            log_stmt = select(ConversationLog).where(
                ConversationLog.voice_session_id == voice_session_id,
                ConversationLog.speaker == "AI_RECEPTIONIST"
            ).order_by(ConversationLog.created_at.desc()).limit(1)
            last_log = (await db.execute(log_stmt)).scalar_one_or_none()
            last_prompt = last_log.transcript if last_log else "नमस्ते! कृपया अपना नाम बताइए।"

            if session.retry_count == 1:
                reply_text = f"माफ़ कीजिये, मुझे आपकी आवाज़ नहीं सुनाई दी। {last_prompt}"
                ai_log = ConversationLog(
                    id=str(_log_uuid.uuid4()),
                    voice_session_id=voice_session_id,
                    speaker="AI_RECEPTIONIST",
                    transcript=reply_text
                )
                db.add(ai_log)
                await db.commit()

                twiml = twilio_service.generate_gather_twiml(voice_session_id, reply_text, hospital_id=h_id)
                return Response(content=twiml, media_type="text/xml")
                
            elif session.retry_count == 2:
                reply_text = f"क्षमा करें, मुझे अभी भी आपकी आवाज़ नहीं सुनाई दे रही है। {last_prompt}"
                ai_log = ConversationLog(
                    id=str(_log_uuid.uuid4()),
                    voice_session_id=voice_session_id,
                    speaker="AI_RECEPTIONIST",
                    transcript=reply_text
                )
                db.add(ai_log)
                await db.commit()

                twiml = twilio_service.generate_gather_twiml(voice_session_id, reply_text, hospital_id=h_id)
                return Response(content=twiml, media_type="text/xml")
                
            else:
                transfer_msg = "माफ़ कीजिये, मैं आपकी आवाज़ नहीं सुन पा रही हूँ। मैं आपकी कॉल अस्पताल के रिसेप्शन पर ट्रांसफर कर रही हूँ। कृपया लाइन पर बने रहें।"
                ai_log = ConversationLog(
                    id=str(_log_uuid.uuid4()),
                    voice_session_id=voice_session_id,
                    speaker="AI_RECEPTIONIST",
                    transcript=transfer_msg
                )
                db.add(ai_log)
                
                h_stmt = select(Hospital).where(Hospital.id == h_id)
                hospital = (await db.execute(h_stmt)).scalar_one_or_none()
                transfer_number = hospital.phone if hospital and hospital.phone else settings.TWILIO_PHONE_NUMBER
                
                session.session_status = "TRANSFERRED"
                await db.commit()

                twiml = twilio_service.generate_transfer_twiml(transfer_number, transfer_msg)
                return Response(content=twiml, media_type="text/xml")
        else:
            twiml = twilio_service.generate_hangup_twiml("तकनीकी समस्या। कृपया पुनः प्रयास करें।")
            return Response(content=twiml, media_type="text/xml")

    # Reset retry count since user spoke
    if session:
        session.retry_count = 0
        user_log = ConversationLog(
            id=str(_log_uuid.uuid4()),
            voice_session_id=voice_session_id,
            speaker="CALLER",
            transcript=SpeechResult
        )
        db.add(user_log)
        await db.commit()

    # Pass control to strict VoiceStateMachine
    from app.engines.voice_state_machine import VoiceStateMachine
    import traceback
    
    state_machine = VoiceStateMachine(db)
    
    try:
        reply_text = await state_machine.process_turn(voice_session_id, SpeechResult, h_id)
        # Check if booking is completed based on current state
        fresh_stmt = select(VoiceSession).where(VoiceSession.id == voice_session_id)
        fresh_session = (await db.execute(fresh_stmt)).scalar_one_or_none()
        booking_completed = fresh_session and fresh_session.current_state == "BOOKED"
    except Exception as err:
        twilio_logger.error(f"State Machine Error in gather: {str(err)}\n{traceback.format_exc()}")
        reply_text = "क्षमा करें, कुछ तकनीकी समस्या आ गई है। कृपया अस्पताल के रिसेप्शन पर संपर्क करें।"
        booking_completed = False

    # Save AI response log
    if session:
        ai_log = ConversationLog(
            id=str(_log_uuid.uuid4()),
            voice_session_id=voice_session_id,
            speaker="AI_RECEPTIONIST",
            transcript=reply_text
        )
        db.add(ai_log)
        await db.commit()

    twilio_logger.info(f"AI response for session {voice_session_id}: '{reply_text}'")

    # Check if appointment booking flow completed
    if booking_completed or "तकनीकी समस्या" in reply_text or "अपॉइंटमेंट बुक नहीं" in reply_text or "रिसेप्शन पर संपर्क करें" in reply_text:
        twiml = twilio_service.generate_hangup_twiml(reply_text)
        return Response(content=twiml, media_type="text/xml")

    # Return next Gather step
    twiml = twilio_service.generate_gather_twiml(
        voice_session_id,
        reply_text,
        hospital_id=h_id
    )
    return Response(content=twiml, media_type="text/xml")


@router.post("/fallback")
async def voice_fallback():
    """Fallback TwiML returned to Twilio when a WebSocket exception or error occurs in handle_voice_stream."""
    from twilio.twiml.voice_response import VoiceResponse
    response = VoiceResponse()
    response.say(
        "क्षमा करें, कुछ तकनीकी समस्या आ गई है। कृपया थोड़ी देर बाद दोबारा प्रयास करें।",
        language="hi-IN",
        voice="Polly.Aditi"
    )
    response.hangup()
    return Response(content=str(response), media_type="text/xml")


@router.websocket("/stream/{voice_session_id}")
async def handle_voice_stream(websocket: WebSocket, voice_session_id: str, db: AsyncSession = Depends(get_db)):
    """Bidirectional WebSocket connection handling G.711 mu-law audio from Twilio and routing to Gemini Live WebSocket."""
    twilio_logger.info(f"WebSocket voice stream connection request for session: {voice_session_id}")
    await websocket.accept()

    # Resolve custom credentials variables early for use in exception handler
    custom_sid = None
    custom_token = None
    call_log = None
    hospital_id = None
    caller_phone = ""

    try:
        # 1. Fetch Voice Session & Hospital ID
        session_stmt = select(VoiceSession).where(VoiceSession.id == voice_session_id)
        session = (await db.execute(session_stmt)).scalar_one_or_none()
        if not session:
            twilio_logger.error(f"Voice session {voice_session_id} not found. Terminating WebSocket.")
            await websocket.close()
            return

        call_stmt = select(CallLog).where(CallLog.id == session.call_log_id)
        call_log = (await db.execute(call_stmt)).scalar_one_or_none()
        hospital_id = call_log.hospital_id if call_log else None
        if not hospital_id:
            twilio_logger.error(f"No hospital_id found for stream session {voice_session_id}. Closing WebSocket.")
            await websocket.close()
            return
        
        caller_number = call_log.caller_number if call_log else ""
        receiver_number = call_log.receiver_number if call_log else ""

        # Check hospital phone / Twilio helpline numbers
        hosp_obj = None
        if hospital_id:
            hosp_stmt = select(Hospital).where(Hospital.id == hospital_id)
            hosp_obj = (await db.execute(hosp_stmt)).scalar_one_or_none()

        is_caller_hospital = (
            caller_number == settings.TWILIO_PHONE_NUMBER or
            (hosp_obj and (caller_number == hosp_obj.phone or caller_number == hosp_obj.helpline))
        )
        
        # If caller is the hospital (outbound call), patient is the receiver; otherwise patient is the caller
        if is_caller_hospital and receiver_number:
            resolved_patient_phone = receiver_number
        else:
            resolved_patient_phone = caller_number or receiver_number
        caller_phone = resolved_patient_phone

        # Resolve custom credentials for Twilio redirects
        if hospital_id and hospital_id != "hosp_default":
            from app.database.models.appointment import HospitalSetting
            sid_stmt = select(HospitalSetting.setting_value).where(
                HospitalSetting.hospital_id == hospital_id,
                HospitalSetting.setting_key == "twilio_account_sid"
            )
            custom_sid = (await db.execute(sid_stmt)).scalar_one_or_none()

            tok_stmt = select(HospitalSetting.setting_value).where(
                HospitalSetting.hospital_id == hospital_id,
                HospitalSetting.setting_key == "twilio_auth_token"
            )
            custom_token = (await db.execute(tok_stmt)).scalar_one_or_none()

        # 2. Build default system instructions prompt for the voice model
        prompt_manager = PromptManager(db)
        system_instruction = await prompt_manager.compile_receptionist_prompt(
            hospital_id=hospital_id,
            caller_phone=resolved_patient_phone
        )

        # 3. Instantiate Gemini Live WebSocket Client
        gemini_client = GeminiLiveClient(system_instruction)
        try:
            await gemini_client.connect()
        except Exception as e:
            twilio_logger.error(f"Failed to connect to Gemini Live WebSocket: {str(e)}")
            await websocket.close()
            return

        stream_sid = None
        scheduling_engine = SchedulingEngine(db)
        appointment_engine = AppointmentEngine(db)

        # State tracking variables for turn detection and silence
        model_is_speaking = False
        user_is_speaking = False
        last_speech_time = None
        turn_complete_time = None
        silence_retry_stage = 0
        booking_completed = False

        async def heartbeat_loop():
            """Keep-alive task to prevent Gemini Multimodal Live API from timing out."""
            try:
                while True:
                    await asyncio.sleep(20)
                    if gemini_client.websocket:
                        try:
                            await gemini_client.websocket.ping()
                            twilio_logger.debug("Heartbeat ping sent to Gemini Live.")
                        except Exception as ping_err:
                            twilio_logger.warning(f"Failed to send heartbeat: {ping_err}")
            except asyncio.CancelledError:
                pass

        async def silence_monitor():
            """Monitors elapsed silence and triggers stages of Hindi prompts/retries."""
            nonlocal turn_complete_time, model_is_speaking, silence_retry_stage, user_is_speaking, booking_completed
            try:
                while True:
                    await asyncio.sleep(0.2)  # High resolution silence check
                    if booking_completed:
                        break
                    if not stream_sid:
                        continue
                    if model_is_speaking or user_is_speaking:
                        continue
                    if turn_complete_time is None:
                        continue

                    current_time = asyncio.get_event_loop().time()
                    elapsed = current_time - turn_complete_time

                    if elapsed > 8.0 and silence_retry_stage == 2:
                        silence_retry_stage = 3
                        twilio_logger.info(f"silence_retry: Stage 3 triggered ({elapsed:.1f}s silence). Saying Main aapki awaaz spasht nahi sun pa raha hoon.")
                        twilio_logger.info("gemini_request: Sending Stage 3 prompt to Gemini.")
                        await gemini_client.send_text_trigger(
                            "(मरीज़ शांत है, कृपया हिंदी में कहें: 'मैं आपकी आवाज़ स्पष्ट नहीं सुन पा रहा हूँ।')"
                        )
                    elif elapsed > 5.0 and silence_retry_stage == 1:
                        silence_retry_stage = 2
                        twilio_logger.info(f"silence_retry: Stage 2 triggered ({elapsed:.1f}s silence). Saying Mujhe awaaz nahi mili, kripya dobara batayein.")
                        twilio_logger.info("gemini_request: Sending Stage 2 prompt to Gemini.")
                        await gemini_client.send_text_trigger(
                            "(मरीज़ शांत है, कृपया हिंदी में कहें: 'मुझे आवाज़ नहीं मिली, कृपया दोबारा बताएं।')"
                        )
                    elif elapsed > 2.5 and silence_retry_stage == 0:
                        silence_retry_stage = 1
                        twilio_logger.info(f"silence_retry: Stage 1 triggered ({elapsed:.1f}s silence). Repeating question.")
                        twilio_logger.info("gemini_request: Sending Stage 1 prompt to Gemini.")
                        await gemini_client.send_text_trigger(
                            "(मरीज़ शांत है, कृपया अपना पिछला सवाल बिल्कुल उसी तरह हिंदी में दोबारा दोहराएं।)"
                        )
            except asyncio.CancelledError:
                pass
            except Exception as e:
                twilio_logger.error(f"Error in silence monitor task: {str(e)}")

        async def gemini_to_twilio_sender():
            """Listens for responses coming from Gemini Live API and relays them to Twilio."""
            nonlocal stream_sid, model_is_speaking, turn_complete_time, silence_retry_stage, booking_completed
            try:
                async for event in gemini_client.receive_stream():
                    if not stream_sid:
                        continue

                    # Log gemini response event
                    twilio_logger.debug(f"gemini_response: Received event of type {event['type']}")

                    if event["type"] == "audio":
                        model_is_speaking = True
                        # User got a response, reset silence retry tracking
                        silence_retry_stage = 0
                        # Decode and resample Gemini 24kHz PCM to Twilio 8kHz G.711 mu-law
                        raw_pcm_24k = base64.b64decode(event["data"])
                        raw_pcm_8k = resample_pcm(raw_pcm_24k, from_rate=24000, to_rate=8000)
                        mulaw_data = pcm_to_ulaw(raw_pcm_8k)
                        base64_mulaw = base64.b64encode(mulaw_data).decode("utf-8")

                        response_frame = {
                            "event": "media",
                            "streamSid": stream_sid,
                            "media": {
                                "payload": base64_mulaw
                            }
                        }
                        await websocket.send_text(json.dumps(response_frame))

                    elif event["type"] == "turn_complete":
                        model_is_speaking = False
                        turn_complete_time = asyncio.get_event_loop().time()
                        twilio_logger.info("turn_completed: Gemini finished speaking. Arming VAD silence detection.")

                        if booking_completed:
                            twilio_logger.info("Booking completed and model finished speaking. Scheduling call hangup in 4.5 seconds.")
                            async def hangup_after_delay():
                                await asyncio.sleep(4.5)
                                twilio_logger.info("Hanging up call after booking confirmation.")
                                if call_log and call_log.call_sid:
                                    try:
                                        await twilio_service.terminate_call_async(call_log.call_sid)
                                    except Exception as term_err:
                                        twilio_logger.error(f"Failed to terminate call SID {call_log.call_sid}: {str(term_err)}")
                                await websocket.close()
                            asyncio.create_task(hangup_after_delay())

                    elif event["type"] == "interrupted":
                        model_is_speaking = False
                        turn_complete_time = asyncio.get_event_loop().time()
                        twilio_logger.info("Caller interrupted AI speaker. Clearing Twilio buffer and resetting states.")
                        clear_frame = {
                            "event": "clear",
                            "streamSid": stream_sid
                        }
                        await websocket.send_text(json.dumps(clear_frame))

                    elif event["type"] == "tool_call" or event.get("type") == "function_call":
                        call_id = event["call_id"] if "call_id" in event else event.get("id")
                        tool_name = event["name"]
                        args = event["args"]
                        twilio_logger.info(f"gemini_response: Tool call requested: {tool_name} with arguments: {args}")
                        
                        result = {}
                        try:
                            if tool_name == "check_availability":
                                from datetime import date as date_type
                                raw_date = str(args["date"] if "date" in args else args.get("target_date")).strip()
                                if "T" in raw_date:
                                    raw_date = raw_date.split("T")[0]
                                elif " " in raw_date:
                                    raw_date = raw_date.split(" ")[0]
                                target_date = date_type.fromisoformat(raw_date)
                                slots = await scheduling_engine.get_available_slots(args["doctor_id"], target_date)
                                slot_times = [s.start_time.strftime("%I:%M %p") for s in slots]
                                result = {
                                    "available_slots": slot_times,
                                    "total_available": len(slots),
                                    "date": raw_date
                                }
                                twilio_logger.info(f"check_availability returned {len(slots)} slots for {args['doctor_id']} on {raw_date}")

                            elif tool_name == "book_appointment":
                                from datetime import date as date_type
                                import uuid as _uuid

                                try:
                                    appt_time = datetime.fromisoformat(args["appointment_datetime"])
                                except Exception:
                                    result = {"code": "ERROR", "message": "Invalid appointment_datetime format. Use YYYY-MM-DDTHH:MM:SS."}
                                    twilio_logger.info(f"gemini_request: Sending invalid date tool response to Gemini.")
                                    await gemini_client.send_tool_response(call_id, tool_name, result)
                                    continue

                                patient_name_raw = args.get("patient_name", "Patient")
                                doctor_id = args["doctor_id"]

                                patient = None
                                name_parts = patient_name_raw.strip().split(" ", 1)
                                first_name = name_parts[0]
                                last_name = name_parts[1] if len(name_parts) > 1 else ""

                                effective_phone = args.get("patient_phone") or args.get("phone") or caller_phone or "0000000000"
                                if effective_phone and effective_phone != "0000000000":
                                    phone_clean = effective_phone.replace("+91", "").strip()
                                    pt_stmt = select(Patient).where(
                                        Patient.hospital_id == hospital_id,
                                        or_(Patient.phone == effective_phone, Patient.phone == f"+91{phone_clean}", Patient.phone.contains(phone_clean))
                                    )
                                    patient = (await db.execute(pt_stmt)).scalars().first()

                                if not patient:
                                    new_patient = Patient(
                                        id=str(_uuid.uuid4()),
                                        hospital_id=hospital_id,
                                        first_name=first_name,
                                        last_name=last_name,
                                        phone=effective_phone,
                                        date_of_birth=date_type(1990, 1, 1),
                                        gender="Unknown"
                                    )
                                    db.add(new_patient)
                                    await db.flush()
                                    patient = new_patient
                                    twilio_logger.info(f"Created new patient for caller: {effective_phone}, name: {patient_name_raw}")
                                else:
                                    if first_name and patient.first_name != first_name:
                                        patient.first_name = first_name
                                        patient.last_name = last_name
                                    twilio_logger.info(f"Found existing patient: {patient.id}, caller: {caller_phone}")

                                booking_result = await appointment_engine.book_appointment(
                                    hospital_id=hospital_id,
                                    patient_id=patient.id,
                                    doctor_id=doctor_id,
                                    appointment_datetime=appt_time,
                                    reason=args.get("reason", "Voice Booking")
                                )

                                if booking_result["code"] == "BOOKING_SUCCESS":
                                    await db.commit()
                                    booking_completed = True
                                    twilio_logger.info(f"WebSocket: Appointment {booking_result['appointment_id']} COMMITTED to DB.")

                                    result = {
                                        "code": "BOOKING_SUCCESS",
                                        "appointment_id": booking_result["appointment_id"],
                                        "patient_name": booking_result["patient_name"],
                                        "appointment_datetime": booking_result["appointment_datetime"]
                                    }

                                    # Fire n8n webhook asynchronously
                                    try:
                                        from app.services.automation import AutomationService
                                        automation = AutomationService()
                                        doctor_stmt = select(Doctor).where(Doctor.id == doctor_id)
                                        doctor_obj = (await db.execute(doctor_stmt)).scalar_one_or_none()
                                        webhook_details = {
                                            "appointment_id": booking_result["appointment_id"],
                                            "patient_name": booking_result["patient_name"],
                                            "patient_phone": patient.phone,
                                            "doctor_id": doctor_id,
                                            "doctor_name": f"Dr. {doctor_obj.first_name} {doctor_obj.last_name}" if doctor_obj else "Doctor",
                                            "appointment_datetime": booking_result["appointment_datetime"],
                                            "reason": args.get("reason", "Voice Booking")
                                        }
                                        asyncio.create_task(automation.dispatch_appointment_booked_webhook(webhook_details))
                                    except Exception as auto_err:
                                        twilio_logger.error(f"n8n webhook dispatch failed (non-critical): {str(auto_err)}")

                                    # WhatsApp Notification
                                    try:
                                        from app.services.whatsapp import WhatsAppNotificationService
                                        wa_service = WhatsAppNotificationService()
                                        doctor_stmt2 = select(Doctor).where(Doctor.id == doctor_id)
                                        doctor2 = (await db.execute(doctor_stmt2)).scalar_one_or_none()
                                        wa_details = {
                                            "hospital_id": hospital_id,
                                            "appointment_id": booking_result["appointment_id"],
                                            "patient_name": booking_result["patient_name"],
                                            "patient_phone": patient.phone,
                                            "doctor_name": f"Dr. {doctor2.first_name} {doctor2.last_name}" if doctor2 else "Doctor",
                                            "appointment_datetime": booking_result["appointment_datetime"],
                                            "reason": args.get("reason", "Voice Booking")
                                        }
                                        asyncio.create_task(wa_service.send_patient_confirmation(wa_details))
                                        twilio_logger.info("WhatsApp confirmation task queued for patient.")
                                    except Exception as wa_err:
                                        twilio_logger.error(f"WhatsApp notification dispatch failed (non-critical): {str(wa_err)}")
                                else:
                                    await db.rollback()
                                    result = booking_result
                                    twilio_logger.info(f"Booking not completed. Code: {booking_result['code']}, Msg: {booking_result.get('message', '')}")

                            elif tool_name == "save_patient_intake":
                                from app.database.models.appointment import PatientIntake
                                intake_appt_id = args.get("appointment_id", "")
                                twilio_logger.info(f"Saving patient intake for appointment: {intake_appt_id}")

                                existing_intake_stmt = select(PatientIntake).where(
                                    PatientIntake.appointment_id == intake_appt_id
                                )
                                existing_intake = (await db.execute(existing_intake_stmt)).scalar_one_or_none()

                                if existing_intake:
                                    existing_intake.has_visited_before = args.get("has_visited_before")
                                    existing_intake.previous_doctor = args.get("previous_doctor")
                                    existing_intake.has_reports = args.get("has_reports")
                                    existing_intake.report_details = args.get("report_details")
                                    existing_intake.current_medicines = args.get("current_medicines")
                                    existing_intake.additional_notes = args.get("additional_notes")
                                else:
                                    import uuid as _uuid2
                                    new_intake = PatientIntake(
                                        id=str(_uuid2.uuid4()),
                                        appointment_id=intake_appt_id,
                                        has_visited_before=args.get("has_visited_before"),
                                        previous_doctor=args.get("previous_doctor"),
                                        has_reports=args.get("has_reports"),
                                        report_details=args.get("report_details"),
                                        current_medicines=args.get("current_medicines"),
                                        additional_notes=args.get("additional_notes")
                                    )
                                    db.add(new_intake)

                                await db.commit()
                                booking_completed = True
                                twilio_logger.info(f"Patient intake saved successfully for: {intake_appt_id}")
                                result = {"status": "SAVED", "appointment_id": intake_appt_id}

                            elif tool_name == "get_active_bookings":
                                from app.database.models.appointment import Appointment, Patient, Doctor, AppointmentStatusHistory
                                
                                twilio_logger.info(f"Fetching active bookings for caller phone: {resolved_patient_phone}")
                                stmt = (
                                    select(Appointment, Patient, Doctor)
                                    .join(Patient, Appointment.patient_id == Patient.id)
                                    .join(Doctor, Appointment.doctor_id == Doctor.id)
                                    .where(
                                        and_(
                                            Patient.phone == resolved_patient_phone,
                                            Appointment.status.in_(["SCHEDULED", "PENDING_PAYMENT", "RESCHEDULED"])
                                        )
                                    )
                                    .order_by(Appointment.appointment_datetime)
                                )
                                db_results = (await db.execute(stmt)).all()
                                
                                now = datetime.now()
                                bookings_list = []
                                for appt, patient, doctor in db_results:
                                    history_stmt = select(AppointmentStatusHistory).where(
                                        and_(
                                            AppointmentStatusHistory.appointment_id == appt.id,
                                            AppointmentStatusHistory.new_status == "RESCHEDULED"
                                        )
                                    )
                                    reschedules = (await db.execute(history_stmt)).all()
                                    reschedule_count = len(reschedules)
                                    
                                    created_at_dt = appt.created_at or appt.appointment_datetime
                                    hours_since_booking = (now - created_at_dt).total_seconds() / 3600.0
                                    is_within_2_days = hours_since_booking <= 48.0
                                    
                                    bookings_list.append({
                                        "appointment_id": appt.id,
                                        "patient_name": f"{patient.first_name} {patient.last_name}".strip(),
                                        "doctor_name": f"Dr. {doctor.first_name} {doctor.last_name}",
                                        "doctor_id": doctor.id,
                                        "appointment_datetime": appt.appointment_datetime.strftime("%Y-%m-%d %I:%M %p"),
                                        "payment_status": appt.status,
                                        "reschedule_count": reschedule_count,
                                        "is_within_2_days": is_within_2_days
                                    })
                                
                                result = {"bookings": bookings_list, "total_active": len(bookings_list)}
                                twilio_logger.info(f"get_active_bookings returned {len(bookings_list)} active bookings.")

                            elif tool_name == "reschedule_appointment_by_ai":
                                from app.database.models.appointment import Appointment, Patient, Doctor, AppointmentStatusHistory
                                from app.services.whatsapp import WhatsAppNotificationService
                                
                                appt_id = args["appointment_id"]
                                new_dt_str = args["new_datetime"]
                                
                                twilio_logger.info(f"AI Rescheduling appt: {appt_id} to {new_dt_str}")
                                
                                stmt = select(Appointment).where(Appointment.id == appt_id)
                                appt = (await db.execute(stmt)).scalar_one_or_none()
                                if not appt:
                                    result = {"status": "ERROR", "message": "Appointment not found"}
                                else:
                                    old_status = appt.status
                                    appt.status = "RESCHEDULED"
                                    appt.appointment_datetime = datetime.fromisoformat(new_dt_str)
                                    appt.updated_at = datetime.now()
                                    
                                    history = AppointmentStatusHistory(
                                        id=str(uuid.uuid4()),
                                        appointment_id=appt.id,
                                        previous_status=old_status,
                                        new_status="RESCHEDULED",
                                        change_reason="Helpline AI voice reschedule"
                                    )
                                    db.add(history)
                                    await db.flush()
                                    
                                    pt_stmt = select(Patient).where(Patient.id == appt.patient_id)
                                    patient = (await db.execute(pt_stmt)).scalar_one_or_none()
                                    doc_stmt = select(Doctor).where(Doctor.id == appt.doctor_id)
                                    doctor = (await db.execute(doc_stmt)).scalar_one_or_none()
                                    
                                    await db.commit()
                                    
                                    if patient and doctor:
                                        wa_service = WhatsAppNotificationService()
                                        wa_details = {
                                            "patient_name": f"{patient.first_name} {patient.last_name}".strip(),
                                            "patient_phone": patient.phone,
                                            "doctor_name": f"Dr. {doctor.first_name} {doctor.last_name}",
                                            "new_datetime": new_dt_str,
                                            "cutoff_note": "कृपया नए समय पर अस्पताल पहुँचे।"
                                        }
                                        asyncio.create_task(wa_service.send_reschedule_notification(wa_details))
                                    
                                    booking_completed = True
                                    result = {"status": "RESCHEDULED", "appointment_id": appt_id}
                                    twilio_logger.info(f"AI Rescheduled appointment {appt_id} successfully.")

                            else:
                                result = {"error": f"Tool '{tool_name}' not recognized."}

                        except Exception as err:
                            from app.core.exceptions import ValidationException
                            if isinstance(err, ValidationException):
                                friendly_msg = str(err)
                                err_lower = friendly_msg.lower()

                                if "already has an active appointment" in err_lower:
                                    result = {"error": "इस मरीज़ का इस डॉक्टर के साथ उस दिन के लिए पहले से एक अपॉइंटमेंट बुक है। कोई दूसरा दिन या डॉक्टर चुनें।"}

                                elif (
                                    "not available for booking" in err_lower
                                    or "aaj ki taareekh" in err_lower
                                    or "आज की तारीख" in friendly_msg
                                    or "aaj" in err_lower
                                    or "today" in err_lower
                                    or "कल या परसों" in friendly_msg
                                    or "संभव नहीं" in friendly_msg
                                ):
                                    try:
                                        from app.engines.scheduling import SchedulingEngine
                                        from datetime import date as _date, timedelta as _td
                                        sched_eng = SchedulingEngine(db)
                                        booked_doctor_id = args.get("doctor_id", "")
                                        alt_slots = []
                                        for days_ahead in [1, 2]:
                                            alt_date = _date.today() + _td(days=days_ahead)
                                            alt_slots = await sched_eng.get_available_slots(booked_doctor_id, alt_date)
                                            if alt_slots:
                                                alt_date_label = alt_date.strftime("%d %B %Y")
                                                slot_times = [s.start_time.strftime("%I:%M %p") for s in alt_slots]
                                                result = {
                                                    "error": "आज के लिए अपॉइंटमेंट बुक नहीं हो सकती।",
                                                    "suggestion": f"{alt_date_label} को ये स्लॉट उपलब्ध हैं: {', '.join(slot_times[:5])}. कृपया इनमें से कोई समय चुनें।",
                                                    "available_date": alt_date.isoformat(),
                                                    "available_slots": slot_times[:5]
                                                }
                                                break
                                        if not alt_slots:
                                            result = {"error": "अगले 2 दिनों में कोई भी स्लॉट उपलब्ध नहीं है। कृपया बाद में कॉल करें।"}
                                    except Exception as slot_err:
                                        twilio_logger.error(f"Failed to fetch alt slots: {slot_err}")
                                        result = {"error": "आज के लिए अपॉइंटमेंट बुक नहीं हो सकती। कल या परसों का समय चुनें।"}
                                else:
                                    result = {"error": friendly_msg}
                                twilio_logger.warning(f"Validation error in tool {tool_name}: {friendly_msg}")
                            else:
                                twilio_logger.error(f"Error executing tool {tool_name}: {str(err)}", exc_info=True)
                                result = {"error": str(err)}

                        twilio_logger.info("gemini_request: Sending tool execution response to Gemini.")
                        await gemini_client.send_tool_response(call_id, tool_name, result)
            except Exception as e:
                twilio_logger.error(f"Error in Gemini to Twilio sender loop: {str(e)}")
                raise e

        # Run the sender, silence monitor, and heartbeat loops as background tasks
        sender_task = asyncio.create_task(gemini_to_twilio_sender())
        silence_task = asyncio.create_task(silence_monitor())
        heartbeat_task = asyncio.create_task(heartbeat_loop())

        while True:
            message_text = await websocket.receive_text()
            data = json.loads(message_text)

            event = data.get("event")
            if event == "start":
                stream_sid = data["start"]["streamSid"]
                twilio_logger.info(f"Twilio stream connected. Stream SID: {stream_sid}")
                from app.database.models.appointment import Hospital
                hosp_stmt = select(Hospital).where(Hospital.id == hospital_id)
                hosp_obj = (await db.execute(hosp_stmt)).scalar_one_or_none()
                hosp_name_str = hosp_obj.name if hosp_obj else "हॉस्पिटल"

                twilio_logger.info("gemini_request: Triggering warmest initial opening greeting from Gemini.")
                await gemini_client.send_text_trigger(
                    f"[SYSTEM] The call has just connected. Start the conversation now. "
                    f"Greet the patient warmly as {hosp_name_str}'s appointment assistant: "
                    f"'नमस्ते! {hosp_name_str} में आपका स्वागत है। मैं यहाँ की अपॉइंटमेंट असिस्टेंट हूँ। कृपया अपना पूरा नाम बताइए।' "
                    f"Ask ONLY for their full name. Nothing else."
                )
            
            elif event == "media":
                if not stream_sid:
                    continue
                
                payload = data["media"]["payload"]
                raw_mulaw = base64.b64decode(payload)
                raw_pcm_8k = ulaw_to_pcm(raw_mulaw)

                raw_pcm_16k = resample_pcm(raw_pcm_8k, from_rate=8000, to_rate=16000)
                base64_pcm_16k = base64.b64encode(raw_pcm_16k).decode("utf-8")

                amplitude = calculate_amplitude(raw_pcm_8k)
                current_time = asyncio.get_event_loop().time()

                # VAD & Speech state detection (ignore non-speech noise below 350)
                if not model_is_speaking:
                    if amplitude > 350:
                        if not user_is_speaking:
                            user_is_speaking = True
                            twilio_logger.info(f"speech_detected: Speech activity detected. Amplitude: {amplitude}")
                        # Keep refreshing last speech timestamp
                        last_speech_time = current_time
                        turn_complete_time = None  # Reset silence monitor timer
                    else:
                        # If user was speaking but drops below threshold (silence gap)
                        if user_is_speaking and last_speech_time is not None:
                            silence_gap = current_time - last_speech_time
                            if silence_gap > 1.2:
                                # User finished speaking -> Trigger turn completion!
                                user_is_speaking = False
                                twilio_logger.info(f"turn_completed: User stopped speaking (silence gap {silence_gap:.1f}s). Triggering Gemini response.")
                                twilio_logger.info("gemini_request: Sending VAD turn completion trigger to Gemini.")
                                await gemini_client.send_text_trigger(
                                    "(मरीज़ ने बोलना समाप्त कर दिया है, कृपया आगे बढ़ें और उत्तर दें।)"
                                )

                # Forward base64 PCM chunk to Gemini only if model is not speaking
                if not model_is_speaking:
                    await gemini_client.send_audio_chunk(base64_pcm_16k)
            
            elif event == "stop":
                twilio_logger.info(f"Twilio stream stopped for session: {voice_session_id}")
                break

    except WebSocketDisconnect:
        twilio_logger.info(f"WebSocket disconnected for session: {voice_session_id}")
    except Exception as e:
        # Structured log: websocket error details
        twilio_logger.error(f"WebSocket error in session {voice_session_id}: {str(e)}", exc_info=True)
        
        # Trigger fallback redirect to return a polite TwiML message instead of Application Error
        if call_log and call_log.call_sid:
            try:
                # Log fallback message sent event
                twilio_logger.info(f"fallback_message_sent: Initiating call redirect for SID {call_log.call_sid} to fallback announcer.")
                clean_domain = settings.TWILIO_WEBHOOK_URL.strip().rstrip("/")
                domain = clean_domain.replace("https://", "").replace("http://", "")
                fallback_url = f"https://{domain}/api/v1/voice/fallback"
                
                await twilio_service.redirect_call_to_fallback_async(
                    call_sid=call_log.call_sid,
                    fallback_url=fallback_url,
                    account_sid=custom_sid,
                    auth_token=custom_token
                )
            except Exception as redirect_err:
                twilio_logger.error(f"Failed to redirect call to fallback: {redirect_err}")
    finally:
        # Cancel all background tasks safely
        sender_task.cancel()
        silence_task.cancel()
        heartbeat_task.cancel()
        await gemini_client.close()

        # Update voice session status
        await db.execute(
            update(VoiceSession)
            .where(VoiceSession.id == voice_session_id)
            .values(session_status="TERMINATED", updated_at=datetime.now(timezone.utc))
        )
        twilio_logger.info(f"Call session {voice_session_id} ended. Caller: {caller_phone}.")
        await db.commit()


class TestCallRequest(BaseModel):
    to_number: Optional[str] = Field(None, description="The target phone number to call. Falls back to TEST_PHONE_NUMBER from environment/env if omitted.")
    hospital_id: Optional[str] = Field(None, description="Optional hospital ID to use its custom Twilio credentials and helpline number.")


class TestCallResponse(BaseModel):
    success: bool
    call_sid: str
    from_number: str
    used_custom_credentials: bool
    message: str


@router.post("/test-call", response_model=TestCallResponse)
async def initiate_test_call(
    request: TestCallRequest,
    db: AsyncSession = Depends(get_db)
):
    """Initiates a test call using Twilio API to the specified phone number."""
    # Resolve recipient phone number
    to_number = request.to_number or settings.TEST_PHONE_NUMBER
    if not to_number:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Recipient phone number must be provided in the request body (to_number) or configured as TEST_PHONE_NUMBER in environment variables."
        )

    # Validate that webhook url is configured
    if not settings.TWILIO_WEBHOOK_URL:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="TWILIO_WEBHOOK_URL environment variable is missing or empty."
        )

    # Resolve custom hospital credentials if hospital_id is provided
    custom_sid = None
    custom_token = None
    custom_from = None
    target_hospital_id = request.hospital_id

    if target_hospital_id:
        from app.database.models.appointment import HospitalSetting, Hospital
        
        sid_stmt = select(HospitalSetting.setting_value).where(
            HospitalSetting.hospital_id == target_hospital_id,
            HospitalSetting.setting_key == "twilio_account_sid"
        )
        custom_sid = (await db.execute(sid_stmt)).scalar_one_or_none()

        tok_stmt = select(HospitalSetting.setting_value).where(
            HospitalSetting.hospital_id == target_hospital_id,
            HospitalSetting.setting_key == "twilio_auth_token"
        )
        custom_token = (await db.execute(tok_stmt)).scalar_one_or_none()

        hosp_stmt = select(Hospital).where(Hospital.id == target_hospital_id)
        hospital_rec = (await db.execute(hosp_stmt)).scalar_one_or_none()
        if hospital_rec and hospital_rec.phone:
            custom_from = hospital_rec.phone

    try:
        call_sid, from_num, is_custom = await twilio_service.initiate_outbound_call_async(
            to_number=to_number,
            webhook_domain=settings.TWILIO_WEBHOOK_URL,
            from_number=custom_from,
            hospital_id=target_hospital_id,
            account_sid=custom_sid,
            auth_token=custom_token
        )
        return TestCallResponse(
            success=True,
            call_sid=call_sid,
            from_number=from_num,
            used_custom_credentials=is_custom,
            message="Test call initiated successfully"
        )
    except Exception as e:
        twilio_logger.error(f"Failed to trigger test call: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger test call: {str(e)}"
        )

