import time
import traceback
from typing import Optional, Dict, Any
from sqlalchemy import select
from app.core.logging import logger, request_id_context, correlation_id_context, hospital_id_context
from app.core.redaction import redact_sensitive_data
from app.database.session import async_session_factory
from app.database.models.control_tower import TenantErrorLog

# In-memory deduplication cache: (hospital_id, service_name, error_code) -> last_logged_timestamp
_error_dedup_cache: Dict[tuple, float] = {}
DEDUP_WINDOW_SECONDS = 30.0

async def record_tenant_error(
    service_name: str,
    error_code: str,
    error_message: str,
    severity: str = "WARNING",
    hospital_id: Optional[str] = None,
    stack_trace: Optional[str] = None,
    endpoint: Optional[str] = None,
    http_method: Optional[str] = None,
    http_status: Optional[int] = None,
    user_id: Optional[str] = None,
    voice_session_id: Optional[str] = None,
    call_id: Optional[str] = None,
    appointment_id: Optional[str] = None,
    payment_id: Optional[str] = None,
    external_provider: Optional[str] = None,
    provider_error_code: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    correlation_id: Optional[str] = None,
    request_id: Optional[str] = None,
) -> Optional[str]:
    """
    Safely captures and persists error telemetry without ever propagating exceptions.
    Applies PII/secret scrubbing and deduplication.
    """
    try:
        # ContextVar fallbacks
        resolved_hosp_id = hospital_id or hospital_id_context.get()
        resolved_req_id = request_id or request_id_context.get()
        resolved_corr_id = correlation_id or correlation_id_context.get() or resolved_req_id

        # Deduplication check
        cache_key = (resolved_hosp_id, service_name, error_code)
        now = time.time()
        last_logged = _error_dedup_cache.get(cache_key, 0)
        if now - last_logged < DEDUP_WINDOW_SECONDS and severity != "CRITICAL":
            logger.debug(f"[ErrorRecorder] Deduplicating repeated error: {error_code} for {resolved_hosp_id}")
            return None
        _error_dedup_cache[cache_key] = now

        # Redact sensitive data
        sanitized_msg = redact_sensitive_data(error_message)
        sanitized_stack = redact_sensitive_data(stack_trace) if stack_trace else None
        sanitized_details = redact_sensitive_data(details) if details else None

        async with async_session_factory() as session:
            error_log = TenantErrorLog(
                hospital_id=resolved_hosp_id,
                service_name=service_name,
                severity=severity,
                error_code=error_code,
                error_message=str(sanitized_msg)[:2000],
                stack_trace=str(sanitized_stack)[:4000] if sanitized_stack else None,
                endpoint=endpoint,
                http_method=http_method,
                http_status=http_status,
                request_id=resolved_req_id,
                correlation_id=resolved_corr_id,
                user_id=user_id,
                voice_session_id=voice_session_id,
                call_id=call_id,
                appointment_id=appointment_id,
                payment_id=payment_id,
                external_provider=external_provider,
                provider_error_code=provider_error_code,
                details=sanitized_details,
            )
            session.add(error_log)
            await session.commit()
            await session.refresh(error_log)
            return error_log.id

    except Exception as ex:
        # Crucial safeguard: logging errors must never disrupt the primary application execution
        logger.error(f"[ErrorRecorder] Failed to persist tenant error log: {str(ex)}")
        return None
