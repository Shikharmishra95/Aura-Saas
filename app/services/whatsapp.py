"""
WhatsApp Notification Service — Twilio WhatsApp API se directly notification bhejo.
Shared sender used for all hospitals and all messages.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, Optional
from twilio.rest import Client
from app.core.config import settings
from app.core.logging import logger

# Thread pool for running synchronous Twilio calls without blocking async event loop
_whatsapp_executor = ThreadPoolExecutor(max_workers=20, thread_name_prefix="whatsapp")


class WhatsAppNotificationService:
    """Sends WhatsApp messages via Twilio WhatsApp API directly from Python code."""

    def __init__(self):
        self.client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        self.from_number = settings.TWILIO_WHATSAPP_FROM
        self.receptionist_number = settings.RECEPTIONIST_WHATSAPP_NUMBER

    def _is_configured(self) -> bool:
        """Check if WhatsApp notification is configured."""
        return bool(self.receptionist_number and self.receptionist_number != "whatsapp:+919999999999")

    async def _resolve_hospital_info(self, details: dict) -> tuple[str, str]:
        h_id = "hosp_default"
        if "hospital_id" in details and details["hospital_id"]:
            h_id = details["hospital_id"]
        else:
            appt_id = details.get("appointment_id")
            if appt_id:
                try:
                    from app.database.session import async_session_factory
                    from app.database.models.appointment import Appointment
                    from sqlalchemy import select
                    async with async_session_factory() as db:
                        stmt = select(Appointment.hospital_id).where(Appointment.id == appt_id)
                        res = (await db.execute(stmt)).scalar_one_or_none()
                        if res:
                            h_id = res
                except Exception as e:
                    logger.error(f"Error resolving hospital_id: {str(e)}")
        
        h_name = "Hospital"
        try:
            from app.database.session import async_session_factory
            from app.database.models.appointment import Hospital
            from sqlalchemy import select
            async with async_session_factory() as db:
                stmt = select(Hospital.name).where(Hospital.id == h_id)
                res = (await db.execute(stmt)).scalar_one_or_none()
                if res:
                    h_name = res
        except Exception:
            pass
            
        details["hospital_id"] = h_id
        details["hospital_name"] = h_name
        return h_id, h_name

    async def _get_client_for_hospital(self, hospital_id: Optional[str]) -> tuple:
        """Returns (TwilioClient, from_number) for a specific hospital or default config.
        Forced to use the shared Twilio account and from_number for all hospitals.
        """
        return self.client, self.from_number

    def _send_sync(self, to: str, body: str, client: Optional[Client] = None, from_number: Optional[str] = None) -> Optional[str]:
        """Synchronous Twilio API call — runs inside thread pool."""
        try:
            active_client = client if client else self.client
            active_from = from_number if from_number else self.from_number

            # Robust E.164 phone formatting for Indian (+91) numbers
            clean_to = to.replace("whatsapp:", "").strip()
            if clean_to.startswith("+1") and len(clean_to) == 12 and clean_to[2] in "6789":
                clean_to = "+91" + clean_to[2:]
            elif not clean_to.startswith("+"):
                if len(clean_to) == 10 and clean_to[0] in "6789":
                    clean_to = "+91" + clean_to
                else:
                    clean_to = "+" + clean_to

            final_to = f"whatsapp:{clean_to}"

            message = active_client.messages.create(
                from_=active_from,
                to=final_to,
                body=body
            )
            logger.info(f"SUCCESS: WhatsApp sent to {final_to}. SID: {message.sid}")
            return message.sid
        except Exception as e:
            logger.error(f"ERROR: WhatsApp send failed to {to}: {str(e)}")
            return None

    def _format_whatsapp_number(self, phone_raw: str) -> str:
        """Format raw phone number into Twilio E.164 whatsapp format (adds +91 if missing)."""
        if not phone_raw:
            return ""
        clean = str(phone_raw).strip().replace("whatsapp:", "").replace(" ", "").replace("-", "")
        if clean.isdigit() and len(clean) == 10:
            clean = "+91" + clean
        elif not clean.startswith("+") and clean.isdigit():
            clean = "+" + clean
        return f"whatsapp:{clean}"

    def _format_datetime(self, dt_str: str) -> str:
        """Convert ISO datetime string to human-readable Hindi-friendly format."""
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(dt_str)
            return dt.strftime("%d %b %Y, %I:%M %p")
        except Exception:
            return dt_str or "N/A"

    async def send_appointment_booked(self, details: dict) -> None:
        """Disabled: Only 5 core notification flows allowed."""
        pass

    async def send_patient_confirmation(self, details: dict) -> None:
        """
        Flow 4: Appointment confirm hone par PATIENT ke apne WhatsApp number par
        sari details + payment link bhejo.
        """
        patient_phone_raw = details.get("patient_phone", "")
        if not patient_phone_raw:
            logger.warning("Patient WhatsApp skipped: patient_phone not available.")
            return

        patient_to = self._format_whatsapp_number(patient_phone_raw)

        hosp_id, hosp_name = await self._resolve_hospital_info(details)
        client, from_number = await self._get_client_for_hospital(hosp_id)
        appt_display = self._format_datetime(details.get("appointment_datetime", ""))
        
        # Dynamically build payment checkout URL. Auto-detect if running on Railway.
        import os
        railway_domain = os.environ.get("RAILWAY_STATIC_URL") or os.environ.get("RAILWAY_PUBLIC_DOMAIN")
        if railway_domain:
            if not railway_domain.startswith("http"):
                base_url = f"https://{railway_domain}"
            else:
                base_url = railway_domain.rstrip('/')
        else:
            base_url = settings.TWILIO_WEBHOOK_URL.rstrip('/') if settings.TWILIO_WEBHOOK_URL else settings.PAYMENT_BASE_URL.rstrip('/')

        payment_link = f"{base_url}/payment/checkout"
        appt_id_short = details.get('appointment_id', 'N/A')[-8:]

        message_body = (
            f"🏥 *{details.get('hospital_name', 'Hospital')}*\n"
            f"✅ *आपकी अपॉइंटमेंट बुक हो गई!*\n\n"
            f"👤 *नाम:* {details.get('patient_name', 'N/A')}\n"
            f"👨‍⚕️ *डॉक्टर:* {details.get('doctor_name', 'N/A')}\n"
            f"📅 *तारीख व समय:* {appt_display}\n"
            f"🩺 *समस्या:* {details.get('reason', 'N/A')}\n"
            f"🆔 *Appointment ID:* {appt_id_short}\n\n"
            f"💳 *Payment करें और अपॉइंटमेंट Confirm करें:*\n"
            f"{payment_link}?appt={appt_id_short}\n\n"
            f"_Payment के बाद आपकी अपॉइंटमेंट confirmed हो जाएगी।_\n"
            f"_किसी सहायता के लिए हमें call करें।_"
        )

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            _whatsapp_executor,
            self._send_sync,
            patient_to,
            message_body,
            client,
            from_number
        )

    async def send_payment_confirmation(self, details: dict) -> None:
        """
        Flow 4 (alternative): Send a payment success and final appointment confirmation WhatsApp message to the patient.
        """
        patient_phone_raw = details.get("patient_phone", "")
        if not patient_phone_raw:
            logger.warning("Patient WhatsApp skipped: patient_phone not available.")
            return

        # Ensure whatsapp: prefix
        if not patient_phone_raw.startswith("whatsapp:"):
            patient_to = f"whatsapp:{patient_phone_raw}"
        else:
            patient_to = patient_phone_raw

        hosp_id, hosp_name = await self._resolve_hospital_info(details)
        client, from_number = await self._get_client_for_hospital(hosp_id)
        appt_display = self._format_datetime(details.get("appointment_datetime", ""))
        appt_id_short = details.get('appointment_id', 'N/A')[-8:]

        message_body = (
            f"🏥 *{details.get('hospital_name', 'Hospital')}*\n"
            f"🎉 *पेमेंट प्राप्त हुआ - अपॉइंटमेंट पक्की हो गई!*\n\n"
            f"नमस्ते {details.get('patient_name', 'N/A')} जी,\n"
            f"हमें आपका पेमेंट सफलतापूर्वक प्राप्त हो गया है।\n\n"
            f"👤 *मरीज़:* {details.get('patient_name', 'N/A')}\n"
            f"👨‍⚕️ *डॉक्टर:* {details.get('doctor_name', 'N/A')}\n"
            f"📅 *तारीख व समय:* {appt_display}\n"
            f"🩺 *समस्या:* {details.get('reason', 'N/A')}\n"
            f"🆔 *Appointment ID:* {appt_id_short}\n\n"
            f"✅ *आपकी अपॉइंटमेंट अब confirmed है।* आपको अस्पताल पहुंचने पर सीधे ओपीडी (OPD) में प्रवेश मिलेगा।\n\n"
            f"_— {details.get('hospital_name', 'Hospital')} पर विश्वास जताने के लिए धन्यवाद!_"
        )

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            _whatsapp_executor,
            self._send_sync,
            patient_to,
            message_body,
            client,
            from_number
        )

    async def send_reschedule_notification(self, details: dict) -> None:
        """
        Flow 5: Receptionist ke Reschedule action par PATIENT ke WhatsApp par nayi
        appointment details aur cutoff arrival time bhejo.
        """
        patient_phone_raw = details.get("patient_phone", "")
        if not patient_phone_raw:
            logger.warning("Reschedule WhatsApp skipped: patient_phone not available.")
            return

        if not patient_phone_raw.startswith("whatsapp:"):
            patient_to = f"whatsapp:{patient_phone_raw}"
        else:
            patient_to = patient_phone_raw

        hosp_id, hosp_name = await self._resolve_hospital_info(details)
        client, from_number = await self._get_client_for_hospital(hosp_id)
        appt_display = self._format_datetime(details.get("new_datetime", ""))

        message_body = (
            f"🏥 *{details.get('hospital_name', 'Hospital')}*\n"
            f"📅 *आपकी अपॉइंटमेंट Reschedule हो गई है*\n\n"
            f"नमस्ते {details.get('patient_name', '')} जी,\n"
            f"आपकी अपॉइंटमेंट का नया समय निर्धारित कर दिया गया है।\n\n"
            f"👨‍⚕️ *डॉक्टर:* {details.get('doctor_name', 'N/A')}\n"
            f"📅 *नया समय:* {appt_display}\n"
        )

        cutoff = details.get("cutoff_note", "")
        if cutoff:
            message_body += f"⚠️ *ज़रूरी सूचना:* {cutoff}\n"

        message_body += (
            f"\nकृपया समय पर पहुंचें। किसी सहायता के लिए हमें call करें।\n"
            f"_— {details.get('hospital_name', 'Hospital')} टीम_"
        )

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            _whatsapp_executor,
            self._send_sync,
            patient_to,
            message_body,
            client,
            from_number
        )

    async def send_cash_booking_confirmation(self, details: dict) -> None:
        """Send WhatsApp confirmation for Cash payments (No payment link)."""
        patient_phone_raw = details.get("patient_phone", "")
        if not patient_phone_raw:
            return
        patient_to = self._format_whatsapp_number(patient_phone_raw)
        hosp_id, hosp_name = await self._resolve_hospital_info(details)
        client, from_number = await self._get_client_for_hospital(hosp_id)
        appt_display = self._format_datetime(details.get("appointment_datetime", ""))

        message_body = (
            f"🏥 *{details.get('hospital_name', 'Hospital')}*\n"
            f"✅ *आपकी अपॉइंटमेंट की पुष्टि हो गई है!*\n\n"
            f"👤 *मरीज़:* {details.get('patient_name', 'N/A')}\n"
            f"👨‍⚕️ *डॉक्टर:* {details.get('doctor_name', 'N/A')}\n"
            f"📅 *तारीख व समय:* {appt_display}\n"
            f"🩺 *समस्या:* {details.get('reason', 'N/A')}\n"
            f"💰 *भुगतान स्थिति:* नकद प्राप्त (PAID — ₹{details.get('fees', '500')})\n\n"
            f"कृपया समय पर अस्पताल पहुँचें। धन्यवाद!\n"
            f"_— {details.get('hospital_name', 'Hospital')} टीम_"
        )

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(_whatsapp_executor, self._send_sync, patient_to, message_body, client, from_number)

    async def send_counter_booking_confirmation(self, details: dict) -> None:
        """Send WhatsApp confirmation for Pay at Hospital Counter (No payment link)."""
        patient_phone_raw = details.get("patient_phone", "")
        if not patient_phone_raw:
            return
        patient_to = self._format_whatsapp_number(patient_phone_raw)
        hosp_id, hosp_name = await self._resolve_hospital_info(details)
        client, from_number = await self._get_client_for_hospital(hosp_id)
        appt_display = self._format_datetime(details.get("appointment_datetime", ""))

        # Dynamically build payment checkout URL
        import os
        railway_domain = os.environ.get("RAILWAY_STATIC_URL") or os.environ.get("RAILWAY_PUBLIC_DOMAIN")
        if railway_domain:
            if not railway_domain.startswith("http"):
                base_url = f"https://{railway_domain}"
            else:
                base_url = railway_domain.rstrip('/')
        else:
            base_url = settings.TWILIO_WEBHOOK_URL.rstrip('/') if settings.TWILIO_WEBHOOK_URL else settings.PAYMENT_BASE_URL.rstrip('/')

        payment_link = f"{base_url}/payment/checkout"
        appt_id_short = details.get('appointment_id', 'N/A')[-8:]

        message_body = (
            f"🏥 *{details.get('hospital_name', 'Hospital')}*\n"
            f"✅ *आपकी अपॉइंटमेंट सफलतापूर्वक बुक हो गई है!*\n\n"
            f"👤 *मरीज़:* {details.get('patient_name', 'N/A')}\n"
            f"👨‍⚕️ *डॉक्टर:* {details.get('doctor_name', 'N/A')}\n"
            f"📅 *तारीख व समय:* {appt_display}\n"
            f"🩺 *समस्या:* {details.get('reason', 'N/A')}\n"
            f"💵 *देय राशि:* ₹{details.get('fees', '500')} (अस्पताल काउंटर पर देय)\n\n"
            f"⏳ *अस्पताल में समय बचाने के लिए ऑनलाइन पेमेंट करें:*\n"
            f"{payment_link}?appt={appt_id_short}\n\n"
            f"कृपया समय पर अस्पताल पहुँचें।\n"
            f"_— {details.get('hospital_name', 'Hospital')} टीम_"
        )

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(_whatsapp_executor, self._send_sync, patient_to, message_body, client, from_number)

    async def send_missed_notification(self, details: dict) -> None:
        """Send notification when appointment is marked as MISSED."""
        phone_raw = details.get("patient_phone", "")
        if not phone_raw:
            return
        
        staff_to = f"whatsapp:{phone_raw}" if not phone_raw.startswith("whatsapp:") else phone_raw
        hosp_id, hosp_name = await self._resolve_hospital_info(details)
        client, from_number = await self._get_client_for_hospital(hosp_id)
        
        date_str = details.get("date", "Today")
        time_str = details.get("time", "")
        doc_name = details.get("doctor_name", "Doctor")
        
        message_body = (
            f"🏥 *{details.get('hospital_name', 'Hospital')} — Appointment Missed*\n\n"
            f"नमस्ते {details.get('patient_name', '')} जी,\n"
            f"आपका अपॉइंटमेंट डॉ. {doc_name} के साथ {date_str} को {time_str} बजे का था, "
            f"लेकिन आप समय पर उपस्थित नहीं हो पाए। इसलिए इसे *MISSED* मार्क कर दिया गया है।\n\n"
            f"नया अपॉइंटमेंट बुक करने के लिए कृपया हमें संपर्क करें।\n"
            f"_— {details.get('hospital_name', 'Hospital')} टीम_"
        )
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(_whatsapp_executor, self._send_sync, staff_to, message_body, client, from_number)

    async def send_cancellation_refund_notification(self, details: dict) -> None:
        """Send cancellation notification with optional refund text."""
        phone_raw = details.get("patient_phone", "")
        if not phone_raw:
            return
            
        staff_to = f"whatsapp:{phone_raw}" if not phone_raw.startswith("whatsapp:") else phone_raw
        hosp_id, hosp_name = await self._resolve_hospital_info(details)
        client, from_number = await self._get_client_for_hospital(hosp_id)
        
        doc_name = details.get("doctor_name", "Doctor")
        reason = details.get("reason", "Hospital administrative reason")
        is_paid = details.get("payment_status", "PENDING") == "PAID"
        
        message_body = (
            f"🏥 *{details.get('hospital_name', 'Hospital')} — Appointment Cancelled*\n\n"
            f"नमस्ते {details.get('patient_name', '')} जी,\n"
            f"आपका डॉ. {doc_name} के साथ अपॉइंटमेंट कैंसिल कर दिया गया है।\n"
            f"*कारण:* {reason}\n"
        )
        
        if is_paid:
            message_body += f"\n💰 *Refund Info:* चूँकि आपने भुगतान (Payment) कर दिया था, आपका रिफंड (Refund) प्रोसेस कर दिया गया है। यह राशि **5 working days** के भीतर आपके बैंक खाते में वापस आ जाएगी।\n"
            
        message_body += f"\nअसुविधा के लिए हमें खेद है।\n_— {details.get('hospital_name', 'Hospital')} टीम_"
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(_whatsapp_executor, self._send_sync, staff_to, message_body, client, from_number)

    async def send_staff_credentials_notification(self, details: dict) -> None:
        """
        Flow 2 & 3: Admins ke naya staff (Doctor/Receptionist) add karne par credentials WhatsApp par bhejo.
        """
        phone_raw = details.get("phone", "")
        if not phone_raw:
            logger.warning("Staff credentials WhatsApp skipped: phone not available.")
            return

        if not phone_raw.startswith("whatsapp:"):
            staff_to = f"whatsapp:{phone_raw}"
        else:
            staff_to = phone_raw

        hosp_id, hosp_name = await self._resolve_hospital_info(details)
        client, from_number = await self._get_client_for_hospital(hosp_id)
        role_label = "डॉक्टर (Doctor)" if details.get("role") == "DOCTOR" else "रिसेप्शनिस्ट (Receptionist)"

        message_body = (
            f"🏥 *{details.get('hospital_name', 'CP Tiwari Hospital')} — Staff Registration Alert*\n\n"
            f"नमस्ते {details.get('staff_name', '')} जी,\n"
            f"आपको हमारे hospital में **{role_label}** के रूप में register कर दिया गया है।\n\n"
            f"🔑 *आपके लॉगिन क्रेडेंशियल्स (Credentials):*\n"
            f"• *Hospital ID:* `{details.get('hospital_id', 'hosp_default')}`\n"
            f"• *Username:* `{details.get('username')}`\n"
            f"• *Password:* `{details.get('password')}`\n"
            f"• *Portal Link:* {details.get('login_url', 'https://pay.cptiwari.com/login')}\n\n"
            f"कृपया सुरक्षा के लिए अपना पासवर्ड लॉगिन करने के बाद बदल लें।\n"
            f"_— {details.get('hospital_name', 'CP Tiwari Hospital')} टीम_"
        )

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            _whatsapp_executor,
            self._send_sync,
            staff_to,
            message_body,
            client,
            from_number
        )

    async def send_prescription_notification(self, details: dict) -> None:
        """Send prescription details to the patient's WhatsApp after consultation is complete."""
        phone_raw = details.get("phone", "")
        if not phone_raw:
            logger.warning("Prescription WhatsApp skipped: phone not available.")
            return

        # Ensure whatsapp: prefix
        if not phone_raw.startswith("whatsapp:"):
            patient_to = f"whatsapp:{phone_raw}"
        else:
            patient_to = phone_raw

        hosp_id, hosp_name = await self._resolve_hospital_info(details)
        client, from_number = await self._get_client_for_hospital(hosp_id)

        message_body = (
            f"🏥 *{details.get('hospital_name', 'Hospital')}*\n"
            f"✅ *डॉ. {details.get('doctor_name', '')} की सलाह (Prescription)*\n\n"
            f"नमस्ते {details.get('patient_name', '')} जी,\n"
            f"आपकी अपॉइंटमेंट सफलतापूर्वक पूरी हो गई है। डॉक्टर का पर्चा नीचे दिया गया है:\n\n"
            f"📝 *क्लिनिकल नोट्स:*\n{details.get('clinical_notes', 'N/A')}\n\n"
            f"💊 *दवाइयां:*\n{details.get('prescription', 'N/A')}\n\n"
            f"📅 *अगली जांच (Follow-up):* {details.get('follow_up_date', 'N/A')}\n\n"
            f"स्वस्थ रहें! 🙏"
        )

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            _whatsapp_executor,
            self._send_sync,
            patient_to,
            message_body,
            client,
            from_number
        )

    async def send_custom_notification(self, to_phone: str, message: str) -> None:
        """
        Flow 1: Used to send onboarding or generic notifications via shared number.
        """
        if not to_phone:
            logger.warning("WhatsApp skipped: phone not available.")
            return

        if not to_phone.startswith("whatsapp:"):
            target_to = f"whatsapp:{to_phone}"
        else:
            target_to = to_phone

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            _whatsapp_executor,
            self._send_sync,
            target_to,
            message
        )

    async def send_daily_summary(self, hospital_id: str = "hosp_default") -> None:
        """Disabled: Only 5 core notification flows allowed."""
        pass
