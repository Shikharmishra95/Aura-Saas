import pytest
from datetime import datetime, timezone, timedelta
from app.database.models.appointment import Hospital, Doctor, Appointment
from app.database.models.control_tower import HospitalSubscriptionHistory, TenantErrorLog, PlatformIncident

@pytest.mark.asyncio
async def test_owner_overview_superadmin_access(client, hospital_a, superadmin_token_headers):
    response = await client.get("/api/v1/owner/overview", headers=superadmin_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert "hospitals" in data
    assert "operations" in data
    assert "financials" in data
    assert "observability" in data
    assert data["hospitals"]["total"] >= 1

@pytest.mark.asyncio
async def test_owner_overview_regular_admin_blocked(client, hospital_a, auth_token_headers):
    response = await client.get("/api/v1/owner/overview", headers=auth_token_headers)
    assert response.status_code == 403
    assert "Access denied" in response.json()["detail"]

@pytest.mark.asyncio
async def test_owner_hospitals_master_list(client, hospital_a, superadmin_token_headers):
    response = await client.get("/api/v1/owner/hospitals", headers=superadmin_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    hosp = data[0]
    assert "id" in hosp
    assert "subscription_plan" in hosp
    assert "doctor_quota_used_pct" in hosp
    assert "health_status" in hosp

@pytest.mark.asyncio
async def test_owner_hospital_360_deep_audit(client, db_session, hospital_a, superadmin_token_headers):
    now = datetime.now(timezone.utc)
    sub = HospitalSubscriptionHistory(
        hospital_id=hospital_a.id,
        event_type="INITIAL_JOIN",
        plan_name="PRO",
        amount_paid=2999.00,
        currency="INR",
        duration_days_added=30,
        plan_started_at=now,
        plan_expires_at=now + timedelta(days=30),
        triggered_by="admin"
    )
    db_session.add(sub)
    await db_session.commit()

    response = await client.get(f"/api/v1/owner/hospitals/{hospital_a.id}/360", headers=superadmin_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert "profile" in data
    assert "subscription_history" in data
    assert "operations_funnel" in data
    assert "ai_voice_telemetry" in data
    assert len(data["subscription_history"]) >= 1

@pytest.mark.asyncio
async def test_owner_health_radar(client, superadmin_token_headers):
    response = await client.get("/api/v1/owner/health-radar", headers=superadmin_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert "overall_platform_status" in data
    assert "components" in data
    assert "database" in data["components"]
    assert "gemini_live_ai" in data["components"]
    assert "twilio_voice" in data["components"]

@pytest.mark.asyncio
async def test_owner_errors_and_traces(client, db_session, hospital_a, superadmin_token_headers):
    err = TenantErrorLog(
        hospital_id=hospital_a.id,
        service_name="TWILIO_VOICE",
        severity="CRITICAL",
        error_code="CALL_DROPPED_TEST",
        error_message="Simulated call drop for trace",
        correlation_id="corr-unique-999"
    )
    db_session.add(err)
    await db_session.commit()

    # 1. Test errors list
    err_res = await client.get(f"/api/v1/owner/errors?hospital_id={hospital_a.id}", headers=superadmin_token_headers)
    assert err_res.status_code == 200
    assert err_res.json()["count"] >= 1

    # 2. Test trace lookup
    trace_res = await client.get("/api/v1/owner/traces/corr-unique-999", headers=superadmin_token_headers)
    assert trace_res.status_code == 200
    trace_data = trace_res.json()
    assert trace_data["correlation_id"] == "corr-unique-999"
    assert len(trace_data["error_events"]) >= 1
