import asyncio
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Dial, Stream
from app.core.config import settings
from app.core.logging import twilio_logger
from app.core.exceptions import ThirdPartyException

class TwilioService:
    def __init__(self):
        # Initialize Twilio Client
        self.client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        self.phone_number = settings.TWILIO_PHONE_NUMBER

    def generate_gather_twiml(self, voice_session_id: str, prompt_text: str, hospital_id: str = "hosp_default") -> str:
        """Generates TwiML using Gather speech recognition for turn-by-turn AI voice conversation."""
        response = VoiceResponse()
        clean_webhook_url = settings.TWILIO_WEBHOOK_URL.strip().rstrip("/")
        action_url = f"{clean_webhook_url}/api/v1/voice/gather/{voice_session_id}?hospital_id={hospital_id}"
        
        gather = response.gather(
            input="speech",
            action=action_url,
            method="POST",
            language="hi-IN",
            speech_timeout="2",
            timeout=8,
            profanity_filter=False
        )
        gather.say(prompt_text, voice="Polly.Kajal-Neural", language="hi-IN")
        
        # If user stays silent, re-prompt
        response.say("माफ़ कीजिये, मुझे आपकी आवाज़ नहीं सुनाई दी। क्या आप पुनः बोल सकते हैं?", voice="Polly.Kajal-Neural", language="hi-IN")
        response.redirect(action_url)
        return str(response)

    def generate_hangup_twiml(self, message: str) -> str:
        """Generates TwiML to speak a final closing message and hang up."""
        response = VoiceResponse()
        response.say(message, voice="Polly.Kajal-Neural", language="hi-IN")
        response.hangup()
        return str(response)

    def generate_transfer_twiml(self, transfer_number: str, message: str) -> str:
        """Generates TwiML to speak a transfer notice and dial an external phone number."""
        twilio_logger.info(f"Generating call transfer TwiML to destination: {transfer_number}")
        response = VoiceResponse()
        response.say(message, voice="Polly.Kajal-Neural", language="hi-IN")
        
        dial = Dial()
        dial.number(transfer_number)
        response.append(dial)
        return str(response)

    async def send_sms_async(self, to_number: str, body: str) -> str:
        """Sends an SMS message asynchronously using asyncio.to_thread to prevent event loop blocking."""
        twilio_logger.info(f"Sending SMS alert to {to_number}")
        
        def _send():
            message = self.client.messages.create(
                body=body,
                from_=self.phone_number,
                to=to_number
            )
            return message.sid

        try:
            message_sid = await asyncio.to_thread(_send)
            twilio_logger.info(f"SMS successfully sent. Message SID: {message_sid}")
            return message_sid
        except Exception as e:
            twilio_logger.error(f"Failed to dispatch SMS notification via Twilio: {str(e)}")
            raise ThirdPartyException(f"Twilio SMS gateway failed: {str(e)}")

    async def initiate_outbound_call_async(
        self,
        to_number: str,
        webhook_domain: str,
        from_number: Optional[str] = None,
        hospital_id: Optional[str] = None,
        account_sid: Optional[str] = None,
        auth_token: Optional[str] = None
    ) -> str:
        """Initiates an outbound call asynchronously using Twilio Calls API with custom hospital settings support."""
        clean_domain = webhook_domain.strip().rstrip("/")
        domain = clean_domain.replace("https://", "").replace("http://", "")
        voice_url = f"https://{domain}/api/v1/voice/inbound"
        if hospital_id:
            voice_url += f"?hospital_id={hospital_id}"

        # Fix Account SID prefix if missing
        if account_sid and not account_sid.startswith("AC"):
            account_sid = "AC" + account_sid

        active_client = Client(account_sid, auth_token) if (account_sid and auth_token) else self.client
        active_from = from_number if from_number else self.phone_number

        # Format recipient phone number for Indian (+91) numbers
        clean_to = to_number.replace("whatsapp:", "").strip()
        if clean_to.startswith("+1") and len(clean_to) == 12 and clean_to[2] in "6789":
            clean_to = "+91" + clean_to[2:]
        elif not clean_to.startswith("+"):
            if len(clean_to) == 10 and clean_to[0] in "6789":
                clean_to = "+91" + clean_to
            else:
                clean_to = "+" + clean_to

        twilio_logger.info(f"Initiating outbound call from {active_from} to {clean_to} targeting Webhook: {voice_url}")

        def _call(client_to_use, from_to_use):
            call = client_to_use.calls.create(
                to=clean_to,
                from_=from_to_use,
                url=voice_url
            )
            return call.sid

        is_custom = bool(account_sid and auth_token)
        try:
            call_sid = await asyncio.to_thread(_call, active_client, active_from)
            twilio_logger.info(f"Outbound call successfully initiated from {active_from}. Call SID: {call_sid} (Custom Creds: {is_custom})")
            return call_sid, active_from, is_custom
        except Exception as e:
            if "401" in str(e) or "20003" in str(e):
                twilio_logger.warning(f"Custom hospital Twilio credentials invalid ({str(e)}). Falling back to global system Twilio account.")
                try:
                    call_sid = await asyncio.to_thread(_call, self.client, self.phone_number)
                    twilio_logger.info(f"Outbound call successfully initiated via fallback client from {self.phone_number}. Call SID: {call_sid}")
                    return call_sid, self.phone_number, False
                except Exception as fallback_err:
                    twilio_logger.error(f"Fallback outbound call also failed: {str(fallback_err)}")
                    raise ThirdPartyException(f"Twilio Calls gateway failed: {str(fallback_err)}")
            twilio_logger.error(f"Failed to initiate outbound call via Twilio: {str(e)}")
            raise ThirdPartyException(f"Twilio Calls gateway failed: {str(e)}")

    async def terminate_call_async(self, call_sid: str) -> None:
        """Terminates an active Twilio call using the REST API."""
        twilio_logger.info(f"Terminating active call SID: {call_sid}")
        def _terminate():
            self.client.calls(call_sid).update(status="completed")
        try:
            await asyncio.to_thread(_terminate)
            twilio_logger.info(f"Call SID {call_sid} terminated successfully.")
        except Exception as e:
            twilio_logger.error(f"Failed to terminate call SID {call_sid}: {str(e)}")

    async def redirect_call_to_fallback_async(self, call_sid: str, fallback_url: str, account_sid: Optional[str] = None, auth_token: Optional[str] = None) -> None:
        """Redirects an active call to a fallback TwiML URL for graceful error announcement."""
        twilio_logger.info(f"Redirecting active call SID: {call_sid} to fallback URL: {fallback_url}")
        def _redirect():
            active_client = Client(account_sid, auth_token) if (account_sid and auth_token) else self.client
            active_client.calls(call_sid).update(url=fallback_url)
        try:
            await asyncio.to_thread(_redirect)
            twilio_logger.info(f"Call SID {call_sid} redirected successfully to fallback.")
        except Exception as e:
            twilio_logger.error(f"Failed to redirect call SID {call_sid} to fallback: {str(e)}")

    def generate_hangup_twiml(self, message: str) -> str:
        """Generates TwiML to play a message and hang up the call."""
        response = VoiceResponse()
        response.say(message, voice="Polly.Joanna-Neural")
        response.hangup()
        return str(response)
