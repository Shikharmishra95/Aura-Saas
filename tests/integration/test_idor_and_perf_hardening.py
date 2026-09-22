import uuid
import pytest
from datetime import datetime, timedelta
from sqlalchemy import select

from app.database.models.call_log import User, Role, UserRole
from app.database.models.appointment import Appointment, Hospital
from app.database.models.copilot import CopilotConversation, CopilotMessage
from app.core.dependencies import hash_password, create_access_token
from app.engines.tool_registry import DynamicToolRegistry, ToolMetadata
from app.api.v1.endpoints.appointments import auto_update_missed_appointments


@pytest.fixture
async def copilot_conversations(db_session, hospital_a, hospital_b, admin_user_a, doctor_user_a):
    """Seeds test Copilot conversations for Hospital A and Hospital B."""
    conv_a = CopilotConversation(
        id="CONV-HOSP-A-01",
        hospital_id=hospital_a.id,
        user_id=admin_user_a.id,
        portal_context="admin"
    )
    msg_a = CopilotMessage(
        id=str(uuid.uuid4()),
        conversation_id=conv_a.id,
        role="user",
        content="Show revenue for Hospital A"
    )
    conv_b = CopilotConversation(
        id="CONV-HOSP-B-01",
        hospital_id=hospital_b.id,
        user_id=doctor_user_a.id,
        portal_context="doctor"
    )
    msg_b = CopilotMessage(
        id=str(uuid.uuid4()),
        conversation_id=conv_b.id,
        role="user",
        content="What is my schedule for Hospital B"
    )
    db_session.add_all([conv_a, msg_a, conv_b, msg_b])
    await db_session.commit()
    return {"conv_a": conv_a, "conv_b": conv_b}


# ==============================================================================
# IDOR-01 Tests: /history/{conversation_id} Tenant Isolation
# ==============================================================================

@pytest.mark.asyncio
async def test_copilot_history_rejects_cross_hospital_staff(
    client, copilot_conversations, admin_token_a
):
    """
    IDOR-01: Verifies that an authenticated Hospital A admin CANNOT read
    the chat history of a Hospital B conversation (returns HTTP 403).
    """
    conv_b_id = copilot_conversations["conv_b"].id

    response = await client.get(
        f"/api/v1/copilot/history/{conv_b_id}",
        headers={"Authorization": f"Bearer {admin_token_a}"}
    )

    assert response.status_code == 403
    assert "Forbidden" in response.json()["detail"]


@pytest.mark.asyncio
async def test_copilot_history_allows_same_hospital_staff(
    client, copilot_conversations, admin_token_a
):
    """
    IDOR-01: Verifies that an authenticated Hospital A admin CAN read
    their own hospital's conversation history (returns HTTP 200).
    """
    conv_a_id = copilot_conversations["conv_a"].id

    response = await client.get(
        f"/api/v1/copilot/history/{conv_a_id}",
        headers={"Authorization": f"Bearer {admin_token_a}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["conversation_id"] == conv_a_id
    assert len(data["messages"]) >= 1
    assert data["messages"][0]["content"] == "Show revenue for Hospital A"


@pytest.mark.asyncio
async def test_copilot_history_allows_super_admin(
    client, copilot_conversations, superadmin_token_headers
):
    """
    IDOR-01: Verifies that SuperAdmin has platform-wide authority
    to view any hospital conversation for support / oversight.
    """
    conv_b_id = copilot_conversations["conv_b"].id

    response = await client.get(
        f"/api/v1/copilot/history/{conv_b_id}",
        headers=superadmin_token_headers
    )

    assert response.status_code == 200
    assert response.json()["conversation_id"] == conv_b_id


# ==============================================================================
# IDOR-02 Tests: /hospitals/{hospital_id}/upgrade-plan RBAC & Tenant Check
# ==============================================================================

@pytest.mark.asyncio
async def test_upgrade_plan_rejects_cross_hospital_admin(
    client, hospital_b, admin_token_a
):
    """
    IDOR-02: Verifies that Hospital A admin CANNOT upgrade or tamper with
    Hospital B's subscription tier (returns HTTP 403).
    """
    response = await client.post(
        f"/api/v1/hospitals/{hospital_b.id}/upgrade-plan",
        data={"plan_name": "ENTERPRISE"},
        headers={"Authorization": f"Bearer {admin_token_a}"}
    )

    assert response.status_code == 403
    assert "Forbidden" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upgrade_plan_rejects_non_admin_staff(
    client, hospital_a, receptionist_token_a
):
    """
    IDOR-02: Verifies that non-admin staff (e.g. Receptionist) CANNOT
    upgrade hospital subscriptions (returns HTTP 403).
    """
    response = await client.post(
        f"/api/v1/hospitals/{hospital_a.id}/upgrade-plan",
        data={"plan_name": "PRO"},
        headers={"Authorization": f"Bearer {receptionist_token_a}"}
    )

    assert response.status_code == 403
    assert "Forbidden" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upgrade_plan_allows_own_hospital_admin(
    client, hospital_a, admin_token_a, db_session
):
    """
    IDOR-02: Verifies that Hospital A admin CAN upgrade Hospital A's plan.
    """
    response = await client.post(
        f"/api/v1/hospitals/{hospital_a.id}/upgrade-plan",
        data={"plan_name": "PRO"},
        headers={"Authorization": f"Bearer {admin_token_a}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["subscription_plan"] == "PRO"

    # Verify DB update
    updated_hosp = await db_session.get(Hospital, hospital_a.id)
    assert updated_hosp.subscription_plan == "PRO"


@pytest.mark.asyncio
async def test_upgrade_plan_allows_super_admin(
    client, hospital_b, superadmin_token_headers, db_session
):
    """
    IDOR-02: Verifies that SuperAdmin can manage subscription for any hospital.
    """
    response = await client.post(
        f"/api/v1/hospitals/{hospital_b.id}/upgrade-plan",
        data={"plan_name": "ENTERPRISE"},
        headers=superadmin_token_headers
    )

    assert response.status_code == 200
    assert response.json()["subscription_plan"] == "ENTERPRISE"


# ==============================================================================
# AI Tool Registry Duplication Tests
# ==============================================================================

def test_tool_registry_has_exact_unique_tools_and_rejects_duplicates():
    """
    Tool Registry: Verifies that DynamicToolRegistry initializes with exactly 37
    unique tools and that duplicate tool registration attempts are safely ignored.
    """
    registry = DynamicToolRegistry()
    initial_count = len(registry._tools)
    assert initial_count == 37

    # Attempt to re-register an existing tool
    dummy_meta = ToolMetadata(
        tool_name="search_doctors",
        domain="doctor",
        description="Duplicate search doctor test",
        parameters={"type": "OBJECT", "properties": {}},
        required_roles=["ALL"]
    )
    registry.register(dummy_meta, handler=lambda **kw: None)

    # Tool count must NOT increase
    assert len(registry._tools) == 37


# ==============================================================================
# PERF-01 Tests: Missed Appointment Sweeper Eager Loading
# ==============================================================================

@pytest.mark.asyncio
async def test_sweeper_runs_with_eager_loaded_relations(
    db_session, hospital_a, doctor_a, patient_a
):
    """
    PERF-01: Verifies that auto_update_missed_appointments sweeps expired
    appointments and accesses eager-loaded patient, doctor, hospital without N+1 crashes.
    """
    past_time = datetime.now() - timedelta(days=2)
    appt = Appointment(
        id=f"APPT-SWEEP-{uuid.uuid4().hex[:8]}",
        hospital_id=hospital_a.id,
        doctor_id=doctor_a.id,
        patient_id=patient_a.id,
        appointment_datetime=past_time,
        status="SCHEDULED",
        payment_status="PENDING"
    )
    db_session.add(appt)
    await db_session.commit()

    # Run sweeper
    await auto_update_missed_appointments(db_session)

    # Verify status changed to MISSED
    await db_session.refresh(appt)
    assert appt.status == "MISSED"
    assert appt.consultation_status == "MISSED"
