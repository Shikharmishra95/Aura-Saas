import json
import traceback
import uuid
from datetime import datetime, date, timedelta, time
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
import google.generativeai as genai
from app.core.config import settings
from app.core.logging import logger
from app.database.models.conversation import VoiceSession, CallLog
from app.database.models.appointment import Hospital, Doctor, Patient, Department, Appointment
from app.engines.scheduling import SchedulingEngine
from app.engines.appointment import AppointmentEngine

# Initialize Gemini for Entity Extraction
genai.configure(api_key=settings.GEMINI_API_KEY)


def get_nearest_slots(requested_time: time, available_slots: list, limit: int = 3) -> list:
    """
    Returns up to `limit` nearest AvailableSlot objects sorted by absolute distance 
    (in minutes) from the requested_time.
    """
    if not available_slots:
        return []
    
    req_minutes = requested_time.hour * 60 + requested_time.minute
    
    def slot_distance(slot):
        slot_t = slot.start_time
        slot_minutes = slot_t.hour * 60 + slot_t.minute
        diff = abs(slot_minutes - req_minutes)
        return (diff, slot_t)

    sorted_slots = sorted(available_slots, key=slot_distance)
    return sorted_slots[:limit]


class VoiceStateMachine:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.scheduling = SchedulingEngine(db)
        self.appointment = AppointmentEngine(db)
        self.model = genai.GenerativeModel(
            model_name=settings.GEMINI_MODEL,
            system_instruction="You are a JSON parser for an enterprise hospital receptionist system. Extract entities from user speech. Return ONLY valid JSON.",
            generation_config={"response_mime_type": "application/json"}
        )

    async def _get_doctor_shifts_formatted(self, doctor_id: str, search_date: date) -> str:
        day_of_week = search_date.isoweekday()
        from app.database.models.appointment import DoctorSchedule
        from sqlalchemy import select, and_
        sched_stmt = select(DoctorSchedule).where(
            and_(
                DoctorSchedule.doctor_id == doctor_id,
                DoctorSchedule.day_of_week == day_of_week
            )
        )
        schedules = (await self.db.execute(sched_stmt)).scalars().all()
        if not schedules:
            if day_of_week <= 6:
                return "सुबह 9:00 बजे से दोपहर 1:00 बजे तक और शाम 5:00 बजे से रात 8:00 बजे तक"
            else:
                return "रविवार को उपलब्ध नहीं हैं"
        shifts = []
        for s in schedules:
            start_str = s.start_time.strftime("%I:%M %p").replace("AM", "सुबह").replace("PM", "शाम")
            end_str = s.end_time.strftime("%I:%M %p").replace("AM", "सुबह").replace("PM", "शाम")
            if "सुबह" in start_str:
                start_str = "सुबह " + start_str.replace(" सुबह", "").replace(" AM", "").lstrip("0")
            else:
                start_str = "शाम " + start_str.replace(" शाम", "").replace(" PM", "").replace("12:", "दोपहर 12:").replace("01:", "दोपहर 1:").replace("02:", "दोपहर 2:").replace("03:", "दोपहर 3:").replace("04:", "दोपहर 4:").replace("05:", "शाम 5:").replace("06:", "शाम 6:").replace("07:", "शाम 7:").replace("08:", "रात 8:").replace("09:", "रात 9:").replace("10:", "रात 10:").replace("11:", "रात 11:").lstrip("0")
            if "सुबह" in end_str:
                end_str = "सुबह " + end_str.replace(" सुबह", "").replace(" AM", "").lstrip("0")
            else:
                end_str = "शाम " + end_str.replace(" शाम", "").replace(" PM", "").replace("12:", "दोपहर 12:").replace("01:", "दोपहर 1:").replace("02:", "दोपहर 2:").replace("03:", "दोपहर 3:").replace("04:", "दोपहर 4:").replace("05:", "शाम 5:").replace("06:", "शाम 6:").replace("07:", "शाम 7:").replace("08:", "रात 8:").replace("09:", "रात 9:").replace("10:", "रात 10:").replace("11:", "रात 11:").lstrip("0")
            shifts.append(f"{start_str} से {end_str}")
        return " और ".join(shifts)

    async def _extract_entity(self, prompt: str, schema: dict) -> dict:
        """Helper to force Gemini to return structured JSON based on a schema with rate-limiting backoff."""
        full_prompt = f"Extract information into this JSON schema:\n{json.dumps(schema, indent=2)}\n\nSpeech:\n{prompt}"
        import asyncio
        import google.api_core.exceptions
        for attempt in range(2):
            try:
                response = self.model.generate_content(full_prompt)
                if response and response.text:
                    return json.loads(response.text)
                return {}
            except google.api_core.exceptions.ResourceExhausted:
                logger.warning(f"Gemini API rate limit (429) hit. Backing off for 1 second... (Attempt {attempt+1}/2)")
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Failed to extract entity: {str(e)}\nTraceback: {traceback.format_exc()}")
                break
        return {}

    async def _transition_state(self, session: VoiceSession, new_state: str, ctx: dict):
        """Helper to update state and write structured state transition logs."""
        old_state = session.current_state
        session.current_state = new_state
        session.booking_context = json.loads(json.dumps(ctx))
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(session, "booking_context")
        self.db.add(session)
        await self.db.commit()

        from app.core.logging import request_id_context
        log_data = {
            "event": "voice_state_transition",
            "session_id": session.id,
            "from_state": old_state,
            "to_state": new_state,
            "context": ctx
        }
        req_id = request_id_context.get()
        if req_id:
            log_data["request_id"] = req_id
        logger.info(json.dumps(log_data))

    async def process_turn(self, session_id: str, user_speech: str, hospital_id: str = None) -> str:
        """
        Advances the backend-driven voice state machine:
        GREETING → NAME → PROBLEM → DOCTOR_SELECTION → DATE → SLOT → CONFIRM → BOOKED
        """
        stmt = select(VoiceSession).where(VoiceSession.id == session_id)
        session = (await self.db.execute(stmt)).scalar_one_or_none()
        if not session:
            return "क्षमा करें, मुझे आपकी कॉल का डेटा नहीं मिल रहा है। कृपया दोबारा कॉल करें।"

        state = session.current_state or "GREETING"
        ctx = session.booking_context or {}

        try:
            if state == "GREETING":
                return await self._handle_greeting_state(session, user_speech, ctx, hospital_id)
            elif state == "NAME":
                return await self._handle_name_state(session, user_speech, ctx, hospital_id)
            elif state == "AGE":
                return await self._handle_age_state(session, user_speech, ctx, hospital_id)
            elif state == "PROBLEM":
                return await self._handle_problem_state(session, user_speech, ctx, hospital_id)
            elif state == "DOCTOR_SELECTION":
                return await self._handle_doctor_selection_state(session, user_speech, ctx, hospital_id)
            elif state == "DATE":
                return await self._handle_date_state(session, user_speech, ctx, hospital_id)
            elif state == "SLOT":
                return await self._handle_slot_state(session, user_speech, ctx, hospital_id)
            elif state == "CONFIRM":
                return await self._handle_confirm_state(session, user_speech, ctx, hospital_id)
            else:
                return "आपकी बुकिंग प्रक्रिया पूरी हो चुकी है। धन्यवाद।"
                
        except Exception as e:
            logger.error(f"State Machine Error in state {state}: {str(e)}\n{traceback.format_exc()}")
            return "क्षमा करें, कुछ तकनीकी समस्या आ गई है। कृपया अस्पताल के नंबर पर संपर्क करें।"

    async def _handle_greeting_state(self, session: VoiceSession, speech: str, ctx: dict, h_id: str) -> str:
        # Check if the user introduced themselves with their name
        schema = {"patient_name": "string (full name if mentioned, else null)"}
        res = await self._extract_entity(speech, schema)
        name = res.get("patient_name")
        if name and name.strip().lower() not in ["null", "none", ""]:
            ctx["patient_name"] = name
            await self._transition_state(session, "AGE", ctx)
            return f"धन्यवाद {name}। आपकी उम्र (age) कितने वर्ष है?"
            
        await self._transition_state(session, "NAME", ctx)
        return "कृपया अपना पूरा नाम बताइए।"

    async def _handle_name_state(self, session: VoiceSession, speech: str, ctx: dict, h_id: str) -> str:
        schema = {"patient_name": "string (full name extracted from text)"}
        res = await self._extract_entity(speech, schema)
        name = res.get("patient_name", speech.strip()[:50])
        
        ctx["patient_name"] = name
        await self._transition_state(session, "AGE", ctx)
        
        return f"धन्यवाद {name}। आपकी उम्र (age) कितने वर्ष है?"

    async def _handle_age_state(self, session: VoiceSession, speech: str, ctx: dict, h_id: str) -> str:
        schema = {"age": "integer (extracted age in years, or null if not found)"}
        res = await self._extract_entity(speech, schema)
        age = res.get("age")
        
        # Fallback regex check if Gemini rate limits or returns null
        if not age:
            import re
            match = re.search(r'\d+', speech)
            if match:
                try:
                    age = int(match.group())
                except ValueError:
                    pass
                    
        if not age:
            hindi_numbers = {
                "एक": 1, "दो": 2, "तीन": 3, "चार": 4, "पाँच": 5, "छह": 6, "सात": 7, "आठ": 8, "नौ": 9, "दस": 10,
                "बीस": 20, "पच्चीस": 25, "तीस": 30, "पैंतीस": 35, "चालीस": 40, "पैंतालीस": 45, "पचास": 50,
                "साठ": 60, "साढ़े": 30, "सत्तर": 70, "अस्सी": 80, "नब्बे": 90
            }
            for word, num in hindi_numbers.items():
                if word in speech:
                    age = num
                    break

        if not age or age <= 0 or age > 120:
            return "क्षमा करें, मैं आपकी उम्र समझ नहीं पाई। कृपया अपनी उम्र अंकों में बताएं, जैसे पच्चीस या तीस वर्ष?"

        ctx["patient_age"] = age
        from datetime import date as date_type
        birth_year = date_type.today().year - age
        ctx["date_of_birth"] = f"{birth_year}-01-01"
        
        await self._transition_state(session, "PROBLEM", ctx)
        return "धन्यवाद। आपको किस विभाग के डॉक्टर से मिलना है, या आपकी क्या स्वास्थ्य समस्या है?"

    async def _handle_problem_state(self, session: VoiceSession, speech: str, ctx: dict, h_id: str) -> str:
        # 1. Fetch departments
        dept_stmt = select(Department).where(Department.hospital_id == h_id)
        departments = (await self.db.execute(dept_stmt)).scalars().all()
        
        # Fetch active doctors
        doc_stmt = select(Doctor).options(selectinload(Doctor.department)).where(Doctor.hospital_id == h_id, Doctor.is_active == True)
        all_doctors = (await self.db.execute(doc_stmt)).scalars().all()
        
        if not all_doctors:
            return "क्षमा करें, हमारे अस्पताल में अभी कोई डॉक्टर उपलब्ध नहीं हैं। कृपया बाद में संपर्क करें।"

        # Local keyword pre-matching for department
        matched_dept_id = None
        lower_speech = speech.lower()
        for dept in departments:
            if dept.name.lower() in lower_speech:
                matched_dept_id = dept.id
                break
        if not matched_dept_id:
            for dept in departments:
                dept_name_lower = dept.name.lower()
                if "cardiology" in dept_name_lower and any(w in lower_speech for w in ["heart", "दिल", "हार्ट", "हृदय", "छाती"]):
                    matched_dept_id = dept.id
                    break
                elif "ortho" in dept_name_lower and any(w in lower_speech for w in ["haddi", "हड्डी", "bone", "joint"]):
                    matched_dept_id = dept.id
                    break
                elif ("eye" in dept_name_lower or "ophthalmology" in dept_name_lower) and any(w in lower_speech for w in ["eye", "आँख", "चश्मा", "vision"]):
                    matched_dept_id = dept.id
                    break
                elif ("pedia" in dept_name_lower or "child" in dept_name_lower) and any(w in lower_speech for w in ["child", "बच्चा", "pedia"]):
                    matched_dept_id = dept.id
                    break

        if not matched_dept_id:
            dept_info = [{"id": d.id, "name": d.name} for d in departments]
            schema = {
                "department_id": f"string (Best matching department ID from: {json.dumps(dept_info)}. If no exact match, return null)",
                "reason": "string (Short summary of medical issue)"
            }
            res = await self._extract_entity(speech, schema)
            matched_dept_id = res.get("department_id")
            reason = res.get("reason", speech.strip()[:100])
        else:
            reason = speech.strip()[:100]
        
        selected_dept = next((d for d in departments if d.id == matched_dept_id), None)
        if not selected_dept:
            # Fallback: Infer department from first doctor
            selected_dept = all_doctors[0].department if all_doctors[0].department else Department(id="gen", name="सामान्य चिकित्सा (General Medicine)")

        dept_name = selected_dept.name
        dept_doctors = [d for d in all_doctors if d.department_id == selected_dept.id]
        
        if not dept_doctors:
            return f"क्षमा करें, हमारे अस्पताल में {dept_name} विभाग में अभी कोई डॉक्टर उपलब्ध नहीं हैं। क्या आप किसी अन्य समस्या के लिए दिखाना चाहते हैं?"

        # If multiple doctors exist -> DOCTOR_SELECTION state
        if len(dept_doctors) > 1:
            doc_names = [f"डॉ. {d.first_name} {d.last_name}" for d in dept_doctors]
            if len(doc_names) == 2:
                docs_str = f"{doc_names[0]} और {doc_names[1]}"
            else:
                docs_str = ", ".join(doc_names[:-1]) + f" और {doc_names[-1]}"

            ctx["department_id"] = selected_dept.id
            ctx["department_name"] = dept_name
            ctx["reason"] = reason
            ctx["candidate_doctor_ids"] = [d.id for d in dept_doctors]
            await self._transition_state(session, "DOCTOR_SELECTION", ctx)

            return f"त्वचा रोग के लिए हमारे पास {docs_str} उपलब्ध हैं। आप किसके साथ अपॉइंटमेंट बुक करना चाहेंगे?" if "dermatology" in dept_name.lower() or "त्वचा" in dept_name else f"{dept_name} के लिए हमारे पास {docs_str} उपलब्ध हैं। आप किसके साथ अपॉइंटमेंट बुक करना चाहेंगे?"

        # If exactly 1 doctor -> DATE state
        single_doc = dept_doctors[0]
        doc_name = f"डॉ. {single_doc.first_name} {single_doc.last_name}"
        
        from datetime import timezone
        ist_now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
        ist_today = ist_now.date()
        tomorrow = ist_today + timedelta(days=1)
        day_after = ist_today + timedelta(days=2)

        # Check leaves and slots
        leave_t = await self.scheduling.get_doctor_leave_info(single_doc.id, tomorrow)
        leave_da = await self.scheduling.get_doctor_leave_info(single_doc.id, day_after)
        slots_t = await self.scheduling.get_available_slots(single_doc.id, tomorrow)
        slots_da = await self.scheduling.get_available_slots(single_doc.id, day_after)

        if leave_t and leave_da:
            return f"डॉ. {doc_name} {leave_t.start_date.strftime('%d-%m-%Y')} से {leave_t.end_date.strftime('%d-%m-%Y')} तक छुट्टी पर हैं। कृपया बाद में कॉल करके इन्हें बुक कराएं, अन्यथा अपना डॉक्टर या विभाग बताएं जिससे बुकिंग करानी हो।"

        if leave_t and not slots_da:
            return f"डॉ. {doc_name} कल छुट्टी पर हैं और परसों के सभी स्लॉट भर चुके हैं। कृपया बाद में कॉल करें या कोई अन्य विभाग बताएं।"
        if leave_da and not slots_t:
            return f"डॉ. {doc_name} परसों छुट्टी पर हैं और कल के सभी स्लॉट भर चुके हैं। कृपया बाद में कॉल करें या कोई अन्य विभाग बताएं।"

        if not slots_t and not slots_da:
            return f"माफ़ करें, डॉ. {doc_name} के लिए अगले 2 दिनों के सभी स्लॉट भर चुके हैं। कृपया कोई अन्य डॉक्टर या विभाग बताएं।"

        available_days = []
        if slots_t and not leave_t:
            available_days.append("कल")
        if slots_da and not leave_da:
            available_days.append("परसों")

        ctx["doctor_id"] = single_doc.id
        ctx["doctor_name"] = doc_name
        ctx["department_id"] = selected_dept.id
        ctx["department_name"] = dept_name
        ctx["reason"] = reason
        ctx["available_days"] = [("kal" if d == "कल" else "parso") for d in available_days]

        if len(available_days) == 1:
            day_avail = available_days[0]
            day_blocked = "कल" if day_avail == "परसों" else "परसों"
            await self._transition_state(session, "DATE", ctx)
            return f"जी, आपने {doc_name} को चुना है। वे {day_blocked} छुट्टी पर हैं, लेकिन वे {day_avail} उपलब्ध हैं। क्या आप {day_avail} आना चाहेंगे?"

        await self._transition_state(session, "DATE", ctx)
        days_str = " या ".join(available_days)
        return f"जी, {dept_name} के लिए हमारे पास {doc_name} उपलब्ध हैं। आप किस दिन आना चाहेंगे? {days_str}?"

    async def _handle_doctor_selection_state(self, session: VoiceSession, speech: str, ctx: dict, h_id: str) -> str:
        candidate_ids = ctx.get("candidate_doctor_ids", [])
        doc_stmt = select(Doctor).where(Doctor.id.in_(candidate_ids))
        cand_doctors = (await self.db.execute(doc_stmt)).scalars().all()
        
        if not cand_doctors:
            return "क्षमा करें, डॉक्टर का विवरण नहीं मिला। कृपया दोबारा प्रयास करें।"

        # Local keyword pre-matching for doctor
        chosen_id = None
        lower_speech = speech.lower()
        for doc in cand_doctors:
            doc_name_lower = f"{doc.first_name} {doc.last_name}".lower()
            first_lower = doc.first_name.lower()
            last_lower = doc.last_name.lower() if doc.last_name else ""
            if first_lower in lower_speech or (last_lower and last_lower in lower_speech) or doc_name_lower in lower_speech:
                chosen_id = doc.id
                break

        if not chosen_id:
            doc_info = [{"id": d.id, "name": f"{d.first_name} {d.last_name}"} for d in cand_doctors]
            schema = {
                "doctor_id": f"string (Best matching doctor ID chosen by user from: {json.dumps(doc_info)})"
            }
            res = await self._extract_entity(speech, schema)
            chosen_id = res.get("doctor_id")

        chosen_doc = next((d for d in cand_doctors if d.id == chosen_id), cand_doctors[0])
        doc_name = f"डॉ. {chosen_doc.first_name} {chosen_doc.last_name}"

        # Pre-check schedule
        from datetime import timezone
        ist_now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
        ist_today = ist_now.date()
        tomorrow = ist_today + timedelta(days=1)
        day_after = ist_today + timedelta(days=2)

        # Check leaves and slots
        leave_t = await self.scheduling.get_doctor_leave_info(chosen_doc.id, tomorrow)
        leave_da = await self.scheduling.get_doctor_leave_info(chosen_doc.id, day_after)
        slots_t = await self.scheduling.get_available_slots(chosen_doc.id, tomorrow)
        slots_da = await self.scheduling.get_available_slots(chosen_doc.id, day_after)

        if leave_t and leave_da:
            return f"डॉ. {doc_name} {leave_t.start_date.strftime('%d-%m-%Y')} से {leave_t.end_date.strftime('%d-%m-%Y')} तक छुट्टी पर हैं। कृपया बाद में कॉल करके इन्हें बुक कराएं, अन्यथा अपना डॉक्टर या विभाग बताएं जिससे बुकिंग करानी हो।"

        if leave_t and not slots_da:
            return f"डॉ. {doc_name} कल छुट्टी पर हैं और परसों के सभी स्लॉट भर चुके हैं। कृपया बाद में कॉल करें या कोई अन्य डॉक्टर चुनें।"
        if leave_da and not slots_t:
            return f"डॉ. {doc_name} परसों छुट्टी पर हैं और कल के सभी स्लॉट भर चुके हैं। कृपया बाद में कॉल करें या कोई अन्य डॉक्टर चुनें।"

        if not slots_t and not slots_da:
            return f"माफ़ करें, डॉ. {doc_name} के लिए अगले 2 दिनों के सभी स्लॉट भर चुके हैं। कृपया कोई अन्य डॉक्टर चुनें।"

        available_days = []
        if slots_t and not leave_t:
            available_days.append("कल")
        if slots_da and not leave_da:
            available_days.append("परसों")

        ctx["doctor_id"] = chosen_doc.id
        ctx["doctor_name"] = doc_name
        ctx["available_days"] = [("kal" if d == "कल" else "parso") for d in available_days]

        if len(available_days) == 1:
            day_avail = available_days[0]
            day_blocked = "कल" if day_avail == "परसों" else "परसों"
            await self._transition_state(session, "DATE", ctx)
            return f"जी, आपने {doc_name} को चुना है। वे {day_blocked} छुट्टी पर हैं, लेकिन वे {day_avail} उपलब्ध हैं। क्या आप {day_avail} आना चाहेंगे?"

        await self._transition_state(session, "DATE", ctx)
        days_str = " या ".join(available_days)
        return f"जी, आपने {doc_name} को चुना है। आप किस दिन आना चाहेंगे? {days_str}?"

    async def _handle_date_state(self, session: VoiceSession, speech: str, ctx: dict, h_id: str) -> str:
        from datetime import timezone
        ist_now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
        today_str = ist_now.strftime("%Y-%m-%d")
        tomorrow_str = (ist_now + timedelta(days=1)).strftime("%Y-%m-%d")
        day_after_str = (ist_now + timedelta(days=2)).strftime("%Y-%m-%d")
        
        schema = {
            "iso_date": f"string (YYYY-MM-DD format). 'aaj' = {today_str}. 'kal' = {tomorrow_str}. 'parso' = {day_after_str}. Return YYYY-MM-DD string."
        }
        res = await self._extract_entity(speech, schema)
        target_date_str = res.get("iso_date")
        
        # Keyword Fallback
        if not target_date_str:
            lower_speech = speech.lower()
            if "परसों" in lower_speech or "parso" in lower_speech:
                target_date_str = day_after_str
            elif "कल" in lower_speech or "kal" in lower_speech:
                target_date_str = tomorrow_str
            elif "आज" in lower_speech or "aaj" in lower_speech:
                target_date_str = today_str
                
        if not target_date_str:
            return "क्षमा करें, मैं तारीख समझ नहीं पाई। क्या आप कल या परसों आना चाहेंगे?"
            
        try:
            target_date = date.fromisoformat(target_date_str)
        except ValueError:
            return "क्षमा करें, तारीख स्पष्ट नहीं है। कृपया 'कल' या 'परसों' कहें।"

        ist_today = ist_now.date()
        days_ahead = (target_date - ist_today).days
        doc_name = ctx.get("doctor_name", "डॉक्टर")
        allowed_days = ctx.get("available_days", ["kal", "parso"])
        
        if days_ahead == 1 and "kal" not in allowed_days:
            return f"माफ़ करें, {doc_name} कल छुट्टी पर हैं, वे परसों ही उपलब्ध होंगे। क्या आप परसों आना चाहेंगे?"
        if days_ahead == 2 and "parso" not in allowed_days:
            return f"माफ़ करें, {doc_name} परसों छुट्टी पर हैं, वे कल ही उपलब्ध होंगे। क्या आप कल आना चाहेंगे?"

        if days_ahead < 0:
            return "आप बीती हुई तारीख नहीं बता सकते। कृपया आगे की कोई तारीख बताएँ।"
        if days_ahead == 0:
            return "माफ़ करें, आज की अपॉइंटमेंट कॉल पर बुक नहीं हो सकती। कृपया कल या परसों की तारीख बताएँ।"
        if days_ahead > 2:
            return "माफ़ करें, हम सिर्फ 2 दिन आगे तक की बुकिंग लेते हैं। कृपया कल या परसों की तारीख बताएँ।"

        # Check slots on requested date
        slots = await self.scheduling.get_available_slots(ctx["doctor_id"], target_date)
        if not slots:
            leave_info = await self.scheduling.get_doctor_leave_info(ctx["doctor_id"], target_date)
            if leave_info:
                return_date = leave_info.end_date + timedelta(days=1)
                return f"माफ़ करें, डॉ. {ctx.get('doctor_name', 'डॉक्टर')} {target_date_str} को छुट्टी पर हैं। वे {return_date.strftime('%d-%m-%Y')} को वापस आएंगे। कृपया कल या परसों की कोई और तारीख चुनें।"
            else:
                return f"माफ़ करें, {target_date_str} को डॉ. {ctx.get('doctor_name', 'डॉक्टर')} के सभी स्लॉट भर चुके हैं। कृपया कोई और तारीख बताएँ।"

        ctx["appointment_date"] = target_date_str
        await self._transition_state(session, "SLOT", ctx)

        shifts_str = await self._get_doctor_shifts_formatted(ctx["doctor_id"], target_date)
        return f"धन्यवाद। {target_date.strftime('%d %B')} को डॉक्टर {shifts_str} उपलब्ध हैं। आप किस समय आना चाहेंगे?"

    async def _handle_slot_state(self, session: VoiceSession, speech: str, ctx: dict, h_id: str) -> str:
        # Local keyword pre-matching for slot time
        pref_time_str = None
        lower_speech = speech.lower()
        
        # 1. Match time format like "12:50" or "4:00" or "4.00"
        import re
        time_match = re.search(r'\b(\d{1,2})[:\.](\d{2})\b', lower_speech)
        if time_match:
            h = int(time_match.group(1))
            m = int(time_match.group(2))
            if h < 9 or (h >= 1 and h <= 8 and any(w in lower_speech for w in ["shaam", "shama", "shamb", "शाम", "रात", "pm", "evening"])):
                h += 12
            pref_time_str = f"{h:02d}:{m:02d}:00"
        else:
            # 2. Hindi word number parsing
            hindi_hours = {
                "ग्यारह": 11, "barah": 12, "बारह": 12, "ek": 13, "एक": 13, "do": 14, "दो": 14, 
                "teen": 15, "तीन": 15, "chaar": 16, "चार": 16, "paanch": 17, "five": 17,
                "पांच": 17, "पाँच": 17, "cheh": 18, "छह": 18, "saat": 19, "सात": 19, "aath": 20, "आठ": 20, 
                "nau": 9, "nine": 9, "नौ": 9, "das": 10, "ten": 10, "दस": 10
            }
            matched_hw = False
            for hw, hr in hindi_hours.items():
                if hw in lower_speech:
                    m = 30 if any(w in lower_speech for w in ["sade", "साढ़े", "साढ़े"]) else 0
                    pref_time_str = f"{hr:02d}:{m:02d}:00"
                    matched_hw = True
                    break
            
            # 3. Match single hour like "11 baje", "12 baje", "4 baje", "5 baje"
            if not matched_hw:
                hour_match = re.search(r'\b(\d{1,2})\s*(?:baje|बजे|pm|am|o|hr)?\b', lower_speech)
                if hour_match:
                    h = int(hour_match.group(1))
                    m = 0
                    if h < 9 or (h >= 1 and h <= 8 and any(w in lower_speech for w in ["shaam", "shama", "shamb", "शाम", "रात", "pm", "evening"])):
                        h += 12
                    pref_time_str = f"{h:02d}:{m:02d}:00"

        # 4. Fallback to Gemini if still not parsed
        if not pref_time_str:
            schema = {
                "preferred_time": "string (HH:MM:SS format, e.g., '11:00:00' for 11 AM or '17:00:00' for 5 PM. If 'morning', pick '11:00:00'. If 'evening', pick '17:00:00'.)"
            }
            res = await self._extract_entity(speech, schema)
            pref_time_str = res.get("preferred_time")
            
        # 5. Standard generic fallbacks if Gemini also returns None
        if not pref_time_str:
            if "11" in lower_speech or "११" in lower_speech or "morning" in lower_speech or "सुबह" in lower_speech:
                pref_time_str = "11:00:00"
            elif "5" in lower_speech or "५" in lower_speech or "evening" in lower_speech or "शाम" in lower_speech:
                pref_time_str = "17:00:00"

        if not pref_time_str:
            target_date = date.fromisoformat(ctx["appointment_date"])
            shifts_str = await self._get_doctor_shifts_formatted(ctx["doctor_id"], target_date)
            return f"क्षमा करें, मैं समय समझ नहीं पाई। डॉक्टर {shifts_str} उपलब्ध हैं। कृपया इस दौरान का कोई समय बताएँ।"
            
        try:
            pref_time = time.fromisoformat(pref_time_str)
        except ValueError:
            target_date = date.fromisoformat(ctx["appointment_date"])
            shifts_str = await self._get_doctor_shifts_formatted(ctx["doctor_id"], target_date)
            return f"समय स्पष्ट नहीं है। डॉक्टर {shifts_str} उपलब्ध हैं। कृपया इस दौरान का कोई समय बताएँ।"

        target_date = date.fromisoformat(ctx["appointment_date"])
        slots = await self.scheduling.get_available_slots(ctx["doctor_id"], target_date)
        if not slots:
            return f"माफ़ करें, {ctx['appointment_date']} को कोई स्लॉट उपलब्ध नहीं है। कृपया कोई दूसरी तारीख बताएँ।"

        exact_slot = next((s for s in slots if s.start_time == pref_time), None)
        if exact_slot:
            pref_display = pref_time.strftime("%I:%M %p").lstrip("0")
            ctx["pending_time"] = pref_time.isoformat()
            ctx["pending_datetime"] = datetime.combine(target_date, pref_time).isoformat()
            await self._transition_state(session, "CONFIRM", ctx)
            
            return f"जी, {pref_display} का स्लॉट उपलब्ध है। क्या मैं {ctx['doctor_name']} के साथ {target_date.strftime('%d %B')} को {pref_display} की अपॉइंटमेंट कन्फर्म कर दूँ?"

        # Suggest 3 nearest slots
        nearest_slots = get_nearest_slots(pref_time, slots, limit=3)
        if not nearest_slots:
            return "क्षमा करें, इस तारीख को कोई नज़दीकी स्लॉट नहीं मिला। कृपया कोई अन्य समय या तारीख बताएँ।"

        nearest_times_str = [s.start_time.strftime("%I:%M %p").lstrip("0") for s in nearest_slots]
        if len(nearest_times_str) == 1:
            times_formatted = nearest_times_str[0]
        elif len(nearest_times_str) == 2:
            times_formatted = f"{nearest_times_str[0]} या {nearest_times_str[1]}"
        else:
            times_formatted = f"{nearest_times_str[0]}, {nearest_times_str[1]} या {nearest_times_str[2]}"

        pref_display = pref_time.strftime("%I:%M %p").lstrip("0")
        
        # Remain in SLOT state for retry
        session.booking_context = json.loads(json.dumps(ctx))
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(session, "booking_context")
        self.db.add(session)
        await self.db.commit()

        return f"{pref_display} का स्लॉट उपलब्ध नहीं है। सबसे नज़दीकी खाली समय {times_formatted} हैं। इनमें से कौन सा समय आपके लिए ठीक रहेगा?"

    async def _handle_confirm_state(self, session: VoiceSession, speech: str, ctx: dict, h_id: str) -> str:
        schema = {
            "confirmed": "boolean (true if the user says 'yes', 'haan', 'ok', 'theek hai', 'confirm', 'कर दो', false otherwise)"
        }
        res = await self._extract_entity(speech, schema)
        confirmed = res.get("confirmed")
        
        # Keyword Fallback
        if confirmed is None:
            lower_speech = speech.lower()
            negative_words = ["नहीं", "नही", "nahi", "no", "cancel", "कैंसिल", "रद्द", "मत", "stop", "rehne"]
            positive_words = ["हाँ", "ha", "haa", "yes", "confirm", "theek", "कर दो", "ok", "okay"]
            if any(w in lower_speech for w in negative_words):
                confirmed = False
            elif any(w in lower_speech for w in positive_words):
                confirmed = True
            else:
                confirmed = False
        
        if not confirmed:
            return "ठीक है, आपकी अपॉइंटमेंट बुक नहीं की गई है। कॉल करने के लिए धन्यवाद।"
            
        call_stmt = select(CallLog).where(CallLog.id == session.call_log_id)
        call_log = (await self.db.execute(call_stmt)).scalar_one_or_none()
        caller_phone = call_log.caller_number if call_log else "0000000000"
        
        name_parts = ctx.get("patient_name", "Patient").split(" ", 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""
        
        from datetime import date as date_type
        dob_str = ctx.get("date_of_birth")
        if dob_str:
            dob_val = date.fromisoformat(dob_str)
        else:
            dob_val = date(1990, 1, 1)

        # 1. Fetch patient matching phone, first_name, and DOB
        pt_stmt = select(Patient).where(
            Patient.hospital_id == h_id,
            Patient.phone == caller_phone,
            Patient.first_name == first_name,
            Patient.date_of_birth == dob_val
        )
        patient = (await self.db.execute(pt_stmt)).scalars().first()
        
        if not patient:
            patient = Patient(
                id=str(uuid.uuid4()),
                hospital_id=h_id,
                first_name=first_name,
                last_name=last_name,
                phone=caller_phone,
                date_of_birth=dob_val,
                gender="Unknown"
            )
            self.db.add(patient)
            await self.db.flush()
            
        target_dt = datetime.fromisoformat(ctx["pending_datetime"])
        ctx["appointment_time"] = ctx["pending_time"]
        ctx["appointment_datetime"] = ctx["pending_datetime"]
        
        # 2. Check duplicate appointment for this patient, doctor, and date
        from sqlalchemy import cast, Date
        booking_date = target_dt.date()
        dup_stmt = select(Appointment).where(
            Appointment.hospital_id == h_id,
            Appointment.patient_id == patient.id,
            Appointment.doctor_id == ctx["doctor_id"],
            cast(Appointment.appointment_datetime, Date) == booking_date,
            Appointment.status != "CANCELLED"
        )
        existing_appt = (await self.db.execute(dup_stmt)).scalars().first()
        if existing_appt:
            return f"माफ़ करें, इस तारीख को डॉ. {ctx.get('doctor_name', 'डॉक्टर')} के साथ {ctx.get('patient_name')} की अपॉइंटमेंट पहले से ही बुक है।"

        result = await self.appointment.book_appointment(
            hospital_id=h_id,
            patient_id=patient.id,
            doctor_id=ctx["doctor_id"],
            appointment_datetime=target_dt,
            reason=ctx.get("reason", "Voice Call")
        )
        
        if result["code"] == "BOOKING_SUCCESS":
            await self._transition_state(session, "BOOKED", ctx)
            
            # Dispatch WhatsApp confirmation
            try:
                import asyncio
                from app.services.whatsapp import WhatsAppNotificationService
                wa_service = WhatsAppNotificationService()
                wa_details = {
                    "hospital_id": h_id,
                    "appointment_id": result["appointment_id"],
                    "patient_name": result["patient_name"],
                    "patient_phone": patient.phone,
                    "doctor_name": ctx["doctor_name"],
                    "appointment_datetime": target_dt,
                    "reason": ctx.get("reason", "")
                }
                asyncio.create_task(wa_service.send_patient_confirmation(wa_details))
            except Exception as wa_err:
                logger.error(f"WhatsApp Error: {wa_err}")
                
            return f"जी, आपकी अपॉइंटमेंट {ctx['doctor_name']} के साथ सफलतापूर्वक बुक हो गई है। व्हाट्सएप पर कन्फर्मेशन भेज दिया गया है। धन्यवाद!"
        else:
            await self.db.rollback()
            return f"क्षमा करें, अपॉइंटमेंट बुक नहीं हो पाई। कारण: {result.get('message', 'तकनीकी समस्या')}।"
