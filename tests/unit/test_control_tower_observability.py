import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from app.core.redaction import redact_sensitive_data, mask_string
from app.core.logging import request_id_context, correlation_id_context, hospital_id_context
from app.database.models.control_tower import (
    HospitalSubscriptionHistory,
    TenantErrorLog,
    PlatformAuditLog,
    PlatformIncident,
    PlatformAlert
)
from app.services.error_recorder import record_tenant_error
from app.services.audit_recorder import record_audit_event

def test_redaction_utility_masks_secrets():
    raw_text = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.doNotLeakThis"
    masked = mask_string(raw_text)
    assert "[REDACTED_JWT]" in masked or "[REDACTED_TOKEN]" in masked

    data = {
        "user_id": "u123",
        "password": "supersecretpassword123",
        "api_key": "sk-1234567890abcdef",
        "patient": {
            "name": "John Doe",
            "medical_notes": "Patient has acute bronchitis",
            "phone": "+919876543210"
        }
    }
    cleaned = redact_sensitive_data(data)
    assert cleaned["password"] == "[REDACTED]"
    assert cleaned["api_key"] == "[REDACTED]"
    assert cleaned["patient"]["medical_notes"] == "[REDACTED]"
    assert cleaned["patient"]["name"] == "John Doe"

@pytest.mark.asyncio
async def test_subscription_history_model_creation(db_session):
    now = datetime.now(timezone.utc)
    entry = HospitalSubscriptionHistory(
        hospital_id="HOSP-TEST-001",
        event_type="INITIAL_JOIN",
        plan_name="PRO",
        amount_paid=2999.00,
        currency="INR",
        payment_ref="pay_test_12345",
        duration_days_added=30,
        plan_started_at=now,
        plan_expires_at=now + timedelta(days=30),
        triggered_by="admin_apolo",
        notes="Automated monthly registration"
    )
    db_session.add(entry)
    await db_session.commit()

    stmt = select(HospitalSubscriptionHistory).where(HospitalSubscriptionHistory.hospital_id == "HOSP-TEST-001")
    res = (await db_session.execute(stmt)).scalars().first()
    assert res is not None
    assert res.plan_name == "PRO"
    assert float(res.amount_paid) == 2999.00
    assert res.duration_days_added == 30

@pytest.mark.asyncio
async def test_incident_lifecycle_model(db_session):
    incident = PlatformIncident(
        title="Twilio Voice Call Latency Spike",
        severity="P2_HIGH",
        status="DETECTED",
        hospital_id="HOSP-TEST-001",
        affected_service="TWILIO_VOICE",
        detected_by="AUTOMATED_RULE",
        related_error_count=5
    )
    db_session.add(incident)
    await db_session.commit()

    assert incident.id is not None
    assert incident.status == "DETECTED"

    # Transition to ACKNOWLEDGED -> INVESTIGATING -> RESOLVED
    incident.status = "ACKNOWLEDGED"
    incident.assigned_to = "sre_lead"
    await db_session.commit()
    assert incident.status == "ACKNOWLEDGED"

    incident.status = "RESOLVED"
    incident.resolution_summary = "Twilio upstream provider resolved regional network route congestion."
    await db_session.commit()
    assert incident.status == "RESOLVED"

@pytest.mark.asyncio
async def test_error_recorder_safe_execution():
    # Set context vars
    req_token = request_id_context.set("req_test_123")
    corr_token = correlation_id_context.set("corr_test_456")
    hosp_token = hospital_id_context.set("HOSP-TEST-999")

    try:
        log_id = await record_tenant_error(
            service_name="GEMINI_AI",
            error_code="GEMINI_LIVE_TIMEOUT",
            error_message="Gemini connection dropped with secret api_key=sk-12345678",
            severity="CRITICAL",
            hospital_id="HOSP-TEST-999",
            details={"patient_token": "Bearer secret_jwt_token_123"}
        )
        # Even in async testing environment, recording should not raise an unhandled exception
        assert log_id is None or isinstance(log_id, str)
    finally:
        request_id_context.reset(req_token)
        correlation_id_context.reset(corr_token)
        hospital_id_context.reset(hosp_token)

@pytest.mark.asyncio
async def test_audit_recorder_safe_execution():
    audit_id = await record_audit_event(
        actor_id="u_admin_1",
        actor_username="shiva9532",
        actor_role="SUPER_ADMIN",
        action="PLAN_UPGRADE",
        resource_type="HOSPITAL",
        resource_id="HOSP-TEST-999",
        hospital_id="HOSP-TEST-999",
        old_state={"plan": "PRO"},
        new_state={"plan": "ENTERPRISE"}
    )
    assert audit_id is None or isinstance(audit_id, str)
