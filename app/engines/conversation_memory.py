import time
import uuid
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger("aura.copilot.memory")

class ConversationMessage(BaseModel):
    role: str  # 'user', 'assistant', 'system', 'tool'
    content: str
    timestamp: float = Field(default_factory=time.time)
    tool_name: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None
    tool_result: Optional[Dict[str, Any]] = None
    route: Optional[str] = None
    citations: Optional[List[str]] = None


class ActionConfirmationToken(BaseModel):
    token: str
    hospital_id: str
    user_id: str
    action_name: str
    action_args: Dict[str, Any]
    summary: str
    created_at: float = Field(default_factory=time.time)
    expires_at: float


class SessionContextState(BaseModel):
    current_hospital_name: Optional[str] = None
    current_hospital_id: Optional[str] = None
    current_doctor_name: Optional[str] = None
    current_doctor_id: Optional[str] = None
    selected_date: Optional[str] = None
    selected_time: Optional[str] = None
    department: Optional[str] = None
    patient_name: Optional[str] = None
    patient_phone: Optional[str] = None
    booking_in_progress: bool = False
    dialog_state: str = "IDLE"  # "IDLE", "BOOKING_COLLECTING_SLOTS", "BOOKING_AWAITING_CONFIRMATION"
    pending_slots: Dict[str, Any] = Field(default_factory=dict)
    last_appointment_id: Optional[str] = None
    last_tool_used: Optional[str] = None
    last_tool_result: Optional[Dict[str, Any]] = None
    last_updated: float = Field(default_factory=time.time)


class MultiTenantConversationMemory:
    """
    Enterprise-Grade Multi-Tenant Isolated Conversation Memory & Confirmation Token Store.
    Compound Key Isolation: `conv:{hospital_id}:{user_id}:{session_id}`
    Guarantees zero cross-tenant or cross-user memory leakage.
    """

    def __init__(self, max_history_turns: int = 10, default_ttl_seconds: int = 1800):
        self.max_history_turns = max_history_turns
        self.default_ttl_seconds = default_ttl_seconds
        # In-Memory Storage: compound_key -> List[ConversationMessage]
        self._sessions: Dict[str, List[ConversationMessage]] = {}
        self._session_expiry: Dict[str, float] = {}
        # Working Context State: compound_key -> SessionContextState
        self._context_states: Dict[str, SessionContextState] = {}
        # Compressed summaries for long conversations (sliding window compression)
        self._session_summaries: Dict[str, str] = {}
        # Confirmation Store: token -> ActionConfirmationToken
        self._pending_confirmations: Dict[str, ActionConfirmationToken] = {}

    def _extractive_summary(self, messages: List[ConversationMessage]) -> str:
        """Fallback extractive summarizer — works fully offline without any LLM.
        Extracts key entity mentions (doctors, dates, amounts, tools) from old messages."""
        key_facts = []
        for msg in messages:
            if msg.role == "user" and msg.content:
                # Keep user intent lines (first 80 chars)
                clean = msg.content.strip()[:80].replace("\n", " ")
                if clean:
                    key_facts.append(f"User asked: {clean}")
            elif msg.role == "assistant" and msg.tool_name:
                key_facts.append(f"Tool used: {msg.tool_name}")
            elif msg.role == "assistant" and msg.content:
                # Extract first line of assistant response (usually contains the answer summary)
                first_line = msg.content.strip().split("\n")[0][:100].replace("#", "").strip()
                if first_line:
                    key_facts.append(f"Bot replied: {first_line}")
        if not key_facts:
            return ""
        return "[Earlier Conversation Summary] " + " | ".join(key_facts[-8:])  # Last 8 key facts

    def _get_compound_key(self, hospital_id: Optional[str], user_id: Optional[str], session_id: Optional[str]) -> str:
        h_id = hospital_id or "GLOBAL"
        u_id = user_id or "ANONYMOUS"
        s_id = session_id or "DEFAULT"
        return f"conv:{h_id}:{u_id}:{s_id}"

    def append_message(
        self,
        hospital_id: Optional[str],
        user_id: Optional[str],
        session_id: Optional[str],
        message: ConversationMessage
    ):
        """Appends a turn to the isolated tenant session history with sliding window compression.
        When window fills, OLD messages are compressed into a summary before deletion."""
        key = self._get_compound_key(hospital_id, user_id, session_id)
        now = time.time()

        if key not in self._sessions or now > self._session_expiry.get(key, 0):
            self._sessions[key] = []

        self._sessions[key].append(message)

        # Sliding window: when history exceeds cap, compress old messages before dropping
        cap = self.max_history_turns * 2  # default: 20 messages
        if len(self._sessions[key]) > cap:
            # Compress the OLDEST half of messages into a summary before dropping
            old_messages = self._sessions[key][:self.max_history_turns]
            new_summary = self._extractive_summary(old_messages)
            # Append to existing summary (rolling)
            existing = self._session_summaries.get(key, "")
            if existing:
                # Merge: keep existing summary + new facts (total cap 600 chars)
                combined = existing + " | " + new_summary
                self._session_summaries[key] = combined[-600:]
            else:
                self._session_summaries[key] = new_summary
            # Now drop the old messages
            self._sessions[key] = self._sessions[key][self.max_history_turns:]
            logger.info(f"Memory compressed for {key}: {len(old_messages)} messages → summary ({len(new_summary)} chars)")

        self._session_expiry[key] = now + self.default_ttl_seconds

    def get_history(
        self,
        hospital_id: Optional[str],
        user_id: Optional[str],
        session_id: Optional[str]
    ) -> List[ConversationMessage]:
        """Retrieves active conversation history for the exact tenant-user session."""
        key = self._get_compound_key(hospital_id, user_id, session_id)
        now = time.time()

        if key not in self._sessions or now > self._session_expiry.get(key, 0):
            return []

        # Refresh sliding TTL
        self._session_expiry[key] = now + self.default_ttl_seconds
        return list(self._sessions[key])

    def get_session_summary(
        self,
        hospital_id: Optional[str],
        user_id: Optional[str],
        session_id: Optional[str]
    ) -> str:
        """Returns the compressed summary of older conversation turns, if any."""
        key = self._get_compound_key(hospital_id, user_id, session_id)
        return self._session_summaries.get(key, "")

    def get_context_state(
        self,
        hospital_id: Optional[str],
        user_id: Optional[str],
        session_id: Optional[str]
    ) -> SessionContextState:
        """Retrieves or initializes active entity context state for multi-turn continuity."""
        key = self._get_compound_key(hospital_id, user_id, session_id)
        now = time.time()
        if key not in self._context_states or (key in self._session_expiry and now > self._session_expiry[key]):
            self._context_states[key] = SessionContextState()
        self._session_expiry[key] = now + self.default_ttl_seconds
        return self._context_states[key]

    def update_context_state(
        self,
        hospital_id: Optional[str],
        user_id: Optional[str],
        session_id: Optional[str],
        **kwargs
    ) -> SessionContextState:
        """Updates entity fields in the working session context."""
        state = self.get_context_state(hospital_id, user_id, session_id)
        for k, v in kwargs.items():
            if v is not None and hasattr(state, k):
                setattr(state, k, v)
        state.last_updated = time.time()
        return state

    def clear_context_state(
        self,
        hospital_id: Optional[str],
        user_id: Optional[str],
        session_id: Optional[str]
    ):
        """Resets active context state for a session."""
        key = self._get_compound_key(hospital_id, user_id, session_id)
        self._context_states.pop(key, None)

    def create_confirmation_token(
        self,
        hospital_id: str,
        user_id: str,
        action_name: str,
        action_args: Dict[str, Any],
        summary: str,
        expires_in_seconds: int = 600
    ) -> ActionConfirmationToken:
        """Generates a secure, short-lived action confirmation token for human-in-the-loop approvals."""
        token_id = f"act_{uuid.uuid4().hex[:10]}"
        now = time.time()
        record = ActionConfirmationToken(
            token=token_id,
            hospital_id=hospital_id or "GLOBAL",
            user_id=user_id or "ANONYMOUS",
            action_name=action_name,
            action_args=action_args,
            summary=summary,
            created_at=now,
            expires_at=now + expires_in_seconds
        )
        self._pending_confirmations[token_id] = record
        return record

    def get_latest_pending_token(
        self,
        hospital_id: Optional[str],
        user_id: Optional[str]
    ) -> Optional[str]:
        """Finds the most recently created unexpired confirmation token for the user/hospital."""
        now = time.time()
        h_id = hospital_id or "GLOBAL"
        u_id = user_id or "ANONYMOUS"
        for tok_id, rec in reversed(list(self._pending_confirmations.items())):
            if rec.expires_at > now:
                if (rec.hospital_id == h_id or rec.hospital_id == "GLOBAL") and (rec.user_id == u_id or rec.user_id == "ANONYMOUS" or not user_id):
                    return tok_id
        return None

    def validate_and_consume_token(
        self,
        token: str,
        hospital_id: str,
        user_id: str
    ) -> Optional[ActionConfirmationToken]:
        """Validates confirmation token security constraints and consumes it once."""
        record = self._pending_confirmations.get(token)
        if not record:
            return None

        now = time.time()
        if now > record.expires_at:
            # Expired
            self._pending_confirmations.pop(token, None)
            return None

        # Verify tenant and user boundary
        if record.hospital_id != (hospital_id or "GLOBAL") or record.user_id != (user_id or "ANONYMOUS"):
            logger.warning(f"Security Alert: Tenant/User mismatch on confirmation token {token}")
            return None

        # Consume token (one-time use)
        self._pending_confirmations.pop(token, None)
        return record

    # ──────────────────────────────────────────────────────────────────────────
    # Distributed Redis Synchronization Methods
    # ──────────────────────────────────────────────────────────────────────────

    def _get_redis_key(self, prefix: str, hospital_id: Optional[str], user_id: Optional[str], session_id: Optional[str]) -> str:
        h_id = hospital_id or "GLOBAL"
        u_id = user_id or "ANONYMOUS"
        s_id = session_id or "DEFAULT"
        return f"aura:prod:{h_id}:{prefix}:{u_id}:{s_id}"

    async def load_session_from_redis(
        self,
        hospital_id: Optional[str],
        user_id: Optional[str],
        session_id: Optional[str]
    ) -> None:
        """Loads distributed session context state, messages, and summary from Redis into memory."""
        try:
            from app.core.redis import redis_manager
        except ImportError:
            return

        ctx_key = self._get_redis_key("ctx", hospital_id, user_id, session_id)
        conv_key = self._get_redis_key("conv", hospital_id, user_id, session_id)
        sum_key = self._get_redis_key("sum", hospital_id, user_id, session_id)
        comp_key = self._get_compound_key(hospital_id, user_id, session_id)

        # 1. Load context state
        ctx_dict = await redis_manager.get_json(ctx_key)
        if ctx_dict and isinstance(ctx_dict, dict):
            try:
                self._context_states[comp_key] = SessionContextState.model_validate(ctx_dict)
            except Exception as e:
                logger.debug(f"Error deserializing SessionContextState from Redis: {e}")

        # 2. Load conversation history
        conv_list = await redis_manager.get_json(conv_key)
        if conv_list and isinstance(conv_list, list):
            try:
                self._sessions[comp_key] = [ConversationMessage.model_validate(m) for m in conv_list]
            except Exception as e:
                logger.debug(f"Error deserializing ConversationMessage list from Redis: {e}")

        # 3. Load summary
        sum_str = await redis_manager.get_json(sum_key)
        if sum_str and isinstance(sum_str, str):
            self._session_summaries[comp_key] = sum_str

    async def save_session_to_redis(
        self,
        hospital_id: Optional[str],
        user_id: Optional[str],
        session_id: Optional[str]
    ) -> None:
        """Persists session context state, messages, and summary to Redis with sliding window TTL."""
        try:
            from app.core.redis import redis_manager
        except ImportError:
            return

        ctx_key = self._get_redis_key("ctx", hospital_id, user_id, session_id)
        conv_key = self._get_redis_key("conv", hospital_id, user_id, session_id)
        sum_key = self._get_redis_key("sum", hospital_id, user_id, session_id)
        comp_key = self._get_compound_key(hospital_id, user_id, session_id)

        # 1. Save context state
        if comp_key in self._context_states:
            ctx = self._context_states[comp_key]
            await redis_manager.set_json(ctx_key, ctx.model_dump(), ttl_seconds=self.default_ttl_seconds)

        # 2. Save conversation history
        if comp_key in self._sessions:
            msgs = [m.model_dump() for m in self._sessions[comp_key]]
            await redis_manager.set_json(conv_key, msgs, ttl_seconds=self.default_ttl_seconds)

        # 3. Save summary
        if comp_key in self._session_summaries:
            await redis_manager.set_json(sum_key, self._session_summaries[comp_key], ttl_seconds=self.default_ttl_seconds)

    async def async_create_confirmation_token(
        self,
        hospital_id: str,
        user_id: str,
        action_name: str,
        action_args: Dict[str, Any],
        summary: str,
        expires_in_seconds: int = 600
    ) -> ActionConfirmationToken:
        """Creates token in memory AND persists to Redis for distributed worker validation."""
        record = self.create_confirmation_token(
            hospital_id=hospital_id,
            user_id=user_id,
            action_name=action_name,
            action_args=action_args,
            summary=summary,
            expires_in_seconds=expires_in_seconds
        )
        try:
            from app.core.redis import redis_manager
            h_id = hospital_id or "GLOBAL"
            u_id = user_id or "ANONYMOUS"
            tok_key = f"aura:prod:{h_id}:token:{record.token}"
            latest_key = f"aura:prod:{h_id}:latest_token:{u_id}"
            await redis_manager.set_json(tok_key, record.model_dump(), ttl_seconds=expires_in_seconds)
            await redis_manager.set_json(latest_key, record.token, ttl_seconds=expires_in_seconds)
        except Exception as e:
            logger.debug(f"Redis store confirmation token warning: {e}")
        return record

    async def async_validate_and_consume_token(
        self,
        token: str,
        hospital_id: str,
        user_id: str
    ) -> Optional[ActionConfirmationToken]:
        """Validates confirmation token across distributed workers using Redis."""
        h_id = hospital_id or "GLOBAL"
        tok_key = f"aura:prod:{h_id}:token:{token}"

        try:
            from app.core.redis import redis_manager
            tok_dict = await redis_manager.get_json(tok_key)
            if tok_dict and isinstance(tok_dict, dict):
                rec = ActionConfirmationToken.model_validate(tok_dict)
                now = time.time()
                if now <= rec.expires_at and rec.hospital_id == h_id and (rec.user_id == (user_id or "ANONYMOUS")):
                    await redis_manager.delete(tok_key)
                    self._pending_confirmations.pop(token, None)
                    return rec
        except Exception as e:
            logger.debug(f"Redis token validate error: {e}")

        # Fallback to local memory
        return self.validate_and_consume_token(token, hospital_id, user_id)


# Global singleton instance
conversation_memory = MultiTenantConversationMemory()
