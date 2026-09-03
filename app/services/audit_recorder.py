from typing import Optional, Dict, Any
from app.core.logging import logger, request_id_context, correlation_id_context, hospital_id_context
from app.core.redaction import redact_sensitive_data
from app.database.session import async_session_factory
from app.database.models.control_tower import PlatformAuditLog

async def record_audit_event(
    actor_id: str,
    actor_username: str,
    actor_role: str,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    hospital_id: Optional[str] = None,
    old_state: Optional[Dict[str, Any]] = None,
    new_state: Optional[Dict[str, Any]] = None,
    status: str = "SUCCESS",
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    request_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
) -> Optional[str]:
    """
    Records an immutable audit event for administrative operations, state mutations, and security violations.
    """
    try:
        resolved_hosp_id = hospital_id or hospital_id_context.get()
        resolved_req_id = request_id or request_id_context.get()
        resolved_corr_id = correlation_id or correlation_id_context.get() or resolved_req_id

        sanitized_old = redact_sensitive_data(old_state) if old_state else None
        sanitized_new = redact_sensitive_data(new_state) if new_state else None

        async with async_session_factory() as session:
            audit_entry = PlatformAuditLog(
                actor_id=actor_id,
                actor_username=actor_username,
                actor_role=actor_role,
                hospital_id=resolved_hosp_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                old_state=sanitized_old,
                new_state=sanitized_new,
                status=status,
                ip_address=ip_address,
                user_agent=user_agent,
                request_id=resolved_req_id,
                correlation_id=resolved_corr_id,
            )
            session.add(audit_entry)
            await session.commit()
            await session.refresh(audit_entry)
            return audit_entry.id

    except Exception as ex:
        logger.error(f"[AuditRecorder] Failed to persist audit log: {str(ex)}")
        return None
