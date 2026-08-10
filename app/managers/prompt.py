from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models.appointment import Hospital
from app.core.logging import logger


class PromptManager:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def compile_receptionist_prompt(
        self,
        hospital_id: str,
        caller_phone: Optional[str] = None,
        patient_name: Optional[str] = None,
        running_summary: Optional[str] = None,
        active_faq_context: Optional[str] = None
    ) -> str:
        """Assembles and returns a dynamic system instruction prompt for the Gemini receptionist model."""

        # 1. Fetch Hospital Info
        stmt = select(Hospital).where(Hospital.id == hospital_id)
        hospital = (await self.db.execute(stmt)).scalar_one_or_none()
        hospital_name = hospital.name if hospital else "हॉस्पिटल"

        # Fetch custom settings
        from app.database.models.appointment import HospitalSetting
        
        greeting_stmt = select(HospitalSetting.setting_value).where(
            HospitalSetting.hospital_id == hospital_id,
            HospitalSetting.setting_key == "greeting_prompt"
        )
        custom_greeting = (await self.db.execute(greeting_stmt)).scalar_one_or_none()

        full_prompt_stmt = select(HospitalSetting.setting_value).where(
            HospitalSetting.hospital_id == hospital_id,
            HospitalSetting.setting_key == "full_custom_prompt"
        )
        full_custom_prompt = (await self.db.execute(full_prompt_stmt)).scalar_one_or_none()

        # 2. Get tomorrow and day after tomorrow dates in Indian Standard Time (IST)
        from datetime import timezone, timedelta as td_type
        now = datetime.now(timezone.utc) + td_type(hours=5, minutes=30)
        today = now.date()
        tomorrow = today + timedelta(days=1)
        day_after = today + timedelta(days=2)
        tomorrow_str = tomorrow.strftime("%Y-%m-%d")    # for tool calls
        day_after_str = day_after.strftime("%Y-%m-%d")  # for tool calls
        today_display = today.strftime("%d %B %Y")
        tomorrow_display = tomorrow.strftime("%d %B %Y")
        day_after_display = day_after.strftime("%d %B %Y")
        current_time_str = now.strftime("%I:%M %p")
        day_name = today.strftime("%A")

        phone_line = (
            f"मरीज़ का मोबाइल नंबर: {caller_phone} (यह उनके Twilio caller ID से automatically मिला है — दोबारा मत पूछो)"
            if caller_phone else
            "मरीज़ का मोबाइल नंबर उपलब्ध नहीं है। अपॉइंटमेंट बुक करते समय phone field में '0000000000' use करो।"
        )

        if full_custom_prompt and full_custom_prompt.strip():
            system_instruction = f"""{full_custom_prompt}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CALLER INFORMATION (Already Known - DO NOT ASK FOR THIS INFO):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{phone_line}
आज की तारीख: {today_display} ({day_name}), समय: {current_time_str}
कल का ISO date (tool calls के लिए): {tomorrow_str} ({tomorrow_display})
परसों का ISO date (tool calls के लिए): {day_after_str} ({day_after_display})
"""
            return system_instruction

        greeting_msg = custom_greeting if (custom_greeting and custom_greeting.strip()) else f"नमस्ते! {hospital_name} में आपका स्वागत है। मैं आपकी अपॉइंटमेंट असिस्टेंट हूँ। कृपया अपना पूरा नाम बताइए।"

        system_instruction = f"""तुम {hospital_name} की AI वर्चुअल रिसेप्शनिस्ट हो।
तुम्हारा काम सिर्फ backend से आये हुए response को बोलना है।
Backend जो जवाब देगा, तुम्हें उसे प्राकृतिक रूप से (naturally) बोलना है।"""
        return system_instruction
    async def compile_intake_prompt(
        self,
        appointment_id: str,
        patient_name: str,
        doctor_name: str,
        appointment_datetime: str,
        hospital_name: str = "हॉस्पिटल"
    ) -> str:
        """Assembles the AI system prompt for post-payment medical intake outbound calls."""

        now = datetime.now()
        current_time_str = now.strftime("%I:%M %p")

        return f"""तुम {hospital_name} की AI Medical Assistant हो।
तुम्हें अभी एक patient को outbound call करके उनकी appointment से पहले कुछ medical जानकारी लेनी है।

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
APPOINTMENT INFO (Already Known):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Patient का नाम: {patient_name}
Appointment ID: {appointment_id}
Doctor: {doctor_name}
Appointment Date/Time: {appointment_datetime}
अभी का समय: {current_time_str}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
भाषा और आवाज़:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- हमेशा हिंदी में बात करो।
- आवाज़ शांत, दोस्ताना और मददगार हो।
- एक बार में एक ही सवाल पूछो।
- जवाब सुनने के बाद आगे बढ़ो।

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
बातचीत का क्रम:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Step 1] शुरुआत:
\"नमस्ते! मैं {hospital_name} से बोल रही हूँ। आपकी अपॉइंटमेंट confirm हो गई है। Doctor से मिलने से पहले हम आपसे कुछ जानकारी लेना चाहते हैं ताकि Doctor आपको बेहतर तरीके से देख सकें। क्या आप अभी बात कर सकते हैं?\"

[Step 2] पहले कहीं दिखाया:
\"क्या आपने इस समस्या के लिए पहले कहीं किसी Doctor को दिखाया है?\"
- अगर हाँ: \"कहाँ दिखाया था? किस Doctor को?\"
- अगर नहीं: अगले सवाल पर जाओ।

[Step 3] Reports:
\"क्या आपके पास कोई पुरानी जाँच रिपोर्ट, X-ray, या Blood Test है?\"
- अगर हाँ: \"कौन सी रिपोर्ट है? (जैसे Blood Report, X-Ray, MRI)\"
- अगर नहीं: अगले सवाल पर जाओ।

[Step 4] दवाइयाँ:
\"क्या आप अभी कोई दवाई ले रहे हैं?\"
- अगर हाँ: \"कौन सी दवाई? (नाम याद हो तो बताएँ)\"
- अगर नहीं: अगले step पर।

[Step 5] SAVE करो:
जब सारी जानकारी मिल जाए, save_patient_intake tool call करो इन parameters के साथ:
- appointment_id: \"{appointment_id}\"
- has_visited_before: true/false
- previous_doctor: (जो बताया)
- has_reports: true/false
- report_details: (report का विवरण)
- current_medicines: (दवाइयों के नाम)
- additional_notes: (कोई और ज़रूरी बात)

[Step 6] अलविदा:
Save successful होने के बाद बोलो:
\"बहुत अच्छा! जानकारी save हो गई है। Doctor साहब आपके appointment पर इसे देखेंगे। समय पर आइएगा। धन्यवाद!\"
(इसके बाद call समाप्त हो जाएगी।)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STRICT RULES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. कोई diagnosis या treatment मत बताओ।
2. एक बार में एक ही सवाल।
3. save_patient_intake tool call करने के बाद result का इंतज़ार करो।
4. tool result मिलने पर ही goodbye बोलो।
"""
