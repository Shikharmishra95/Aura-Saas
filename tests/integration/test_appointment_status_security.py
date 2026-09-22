import uuid
import pytest
from datetime import datetime, timedelta
from sqlalchemy import select
from app.database.models.call_log import User, UserRole
from app.database.models.appointment import Appointment, AppointmentStatusHistory
from app.core.dependencies import hash_password, create_access_token

@pytest.fixture
async def sample_appointments(db_session, hospital_a, hospital_b, doctor_a, doctor_b, patient_a, patient_b):
    """Creates sample appointments for Hospital A and Hospital B."""
    future_time = datetime.now() + timedelta(days=1)
    
    appt_a = Appointment(
        id="APPT-AUTH-A-1",
        hospital_id=hospital_a.id,
        doctor_id=doctor_a.id,
        patient_id=patient_a.id,
        appointment_datetime=future_time,
        status="SCHEDULED",
        payment_status="PAID",
        reschedule_count=0,
        source="PHONE"
    )
    appt_b = Appointment(
        id="APPT-AUTH-B-1",
        hospital_id=hospital_b.id,
        doctor_id=doctor_b.id,
        patient_id=patient_b.id,
        appointment_datetime=future_time,
        status="SCHEDULED",
        payment_status="PAID",
        reschedule_count=0,
        source="PHONE"
    )
    db_session.add(appt_a)
    db_session.add(appt_b)
    await db_session.commit()
    await db_session.refresh(appt_a)
    await db_session.refresh(appt_b)
    return {"appt_a": appt_a, "appt_b": appt_b}


@pytest.fixture
async def patient_user_token(db_session, hospital_a, patient_a, seed_roles):
    """Creates an authenticated patient user with PATIENT role."""
    user = User(
        id="USER-PATIENT-AUTH",
        hospital_id=hospital_a.id,
        username="patient_user_auth",
        email="patient_auth@example.com",
        password_hash=hash_password("patpass123"),
        first_name="Rohan",
        last_name="Patient",
        is_active=True
    )
    db_session.add(user)
    await db_session.flush()
    ur = UserRole(
        id=str(uuid.uuid4()),
        user_id=user.id,
        role_id=seed_roles["PATIENT"].id
    )
    db_session.add(ur)
    await db_session.commit()

    token = create_access_token({
        "sub": user.username,
        "role": "PATIENT",
        "hospital_id": user.hospital_id,
        "user_id": user.id
    })
    return token


@pytest.mark.asyncio
async def test_status_update_unauthenticated_returns_401(client, db_session, sample_appointments):
    """Test A: Unauthenticated request must return 401 and not modify DB."""
    appt_a = sample_appointments["appt_a"]
    response = await client.post(
        f"/api/v1/appointments/{appt_a.id}/status",
        data={"new_status": "CANCELLED"}
    )
    assert response.status_code == 401

    # Verify DB unchanged (Test H)
    await db_session.refresh(appt_a)
    assert appt_a.status == "SCHEDULED"


@pytest.mark.asyncio
async def test_status_update_patient_returns_403(client, db_session, sample_appointments, patient_user_token):
    """Test B: Authenticated patient role must be rejected with 403."""
    appt_a = sample_appointments["appt_a"]
    headers = {"Authorization": f"Bearer {patient_user_token}"}
    response = await client.post(
        f"/api/v1/appointments/{appt_a.id}/status",
        data={"new_status": "CANCELLED"},
        headers=headers
    )
    assert response.status_code == 403
    assert "Unauthorized" in response.json()["detail"]

    # Verify DB unchanged (Test H)
    await db_session.refresh(appt_a)
    assert appt_a.status == "SCHEDULED"


@pytest.mark.asyncio
async def test_status_update_authorized_doctor_succeeds(client, db_session, sample_appointments, doctor_token_a, doctor_user_a):
    """Test C: Authenticated doctor modifying own hospital's appointment succeeds."""
    appt_a = sample_appointments["appt_a"]
    headers = {"Authorization": f"Bearer {doctor_token_a}"}
    response = await client.post(
        f"/api/v1/appointments/{appt_a.id}/status",
        data={"new_status": "CANCELLED", "cancellation_reason": "Doctor leave"},
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["new_status"] == "CANCELLED"

    # Verify DB updated
    await db_session.refresh(appt_a)
    assert appt_a.status == "CANCELLED"

    # Verify audit history
    stmt = select(AppointmentStatusHistory).where(AppointmentStatusHistory.appointment_id == appt_a.id)
    history = (await db_session.execute(stmt)).scalars().all()
    assert len(history) >= 1
    assert history[-1].changed_by_user_id == doctor_user_a.id


@pytest.mark.asyncio
async def test_status_update_cross_tenant_doctor_blocked(client, db_session, sample_appointments, doctor_token_a):
    """Test D: Doctor from Hospital A attempting to modify Hospital B appointment must return 403."""
    appt_b = sample_appointments["appt_b"]
    headers = {"Authorization": f"Bearer {doctor_token_a}"}
    response = await client.post(
        f"/api/v1/appointments/{appt_b.id}/status",
        data={"new_status": "CANCELLED"},
        headers=headers
    )
    assert response.status_code == 403
    assert "Forbidden" in response.json()["detail"]
    assert "another hospital" in response.json()["detail"]

    # Verify Hospital B appointment in DB was NOT modified (Test H)
    await db_session.refresh(appt_b)
    assert appt_b.status == "SCHEDULED"


@pytest.mark.asyncio
async def test_status_update_receptionist_rbac_and_tenant_isolation(
    client, db_session, sample_appointments, receptionist_token_a
):
    """Test E1: Receptionist can modify Hospital A appointment, but blocked from Hospital B."""
    appt_a = sample_appointments["appt_a"]
    appt_b = sample_appointments["appt_b"]
    headers = {"Authorization": f"Bearer {receptionist_token_a}"}

    # 1. Allowed on own hospital appointment
    res_a = await client.post(
        f"/api/v1/appointments/{appt_a.id}/status",
        data={"new_status": "MISSED"},
        headers=headers
    )
    assert res_a.status_code == 200
    await db_session.refresh(appt_a)
    assert appt_a.status == "MISSED"

    # 2. Blocked from Hospital B appointment
    res_b = await client.post(
        f"/api/v1/appointments/{appt_b.id}/status",
        data={"new_status": "CANCELLED"},
        headers=headers
    )
    assert res_b.status_code == 403
    await db_session.refresh(appt_b)
    assert appt_b.status == "SCHEDULED"


@pytest.mark.asyncio
async def test_status_update_admin_rbac_and_tenant_isolation(
    client, db_session, sample_appointments, auth_token_headers
):
    """Test E2: Hospital Admin can modify Hospital A appointment, but blocked from Hospital B."""
    appt_a = sample_appointments["appt_a"]
    appt_b = sample_appointments["appt_b"]

    # 1. Allowed on own hospital appointment
    res_a = await client.post(
        f"/api/v1/appointments/{appt_a.id}/status",
        data={"new_status": "COMPLETED"},
        headers=auth_token_headers
    )
    assert res_a.status_code == 200
    await db_session.refresh(appt_a)
    assert appt_a.status == "COMPLETED"

    # 2. Blocked from Hospital B appointment
    res_b = await client.post(
        f"/api/v1/appointments/{appt_b.id}/status",
        data={"new_status": "CANCELLED"},
        headers=auth_token_headers
    )
    assert res_b.status_code == 403
    await db_session.refresh(appt_b)
    assert appt_b.status == "SCHEDULED"


@pytest.mark.asyncio
async def test_status_update_super_admin_allowed_cross_tenant(
    client, db_session, sample_appointments, superadmin_token_headers
):
    """Test F: SuperAdmin can update appointments across all hospital tenants."""
    appt_a = sample_appointments["appt_a"]
    appt_b = sample_appointments["appt_b"]

    # SuperAdmin updates Hospital A appointment
    res_a = await client.post(
        f"/api/v1/appointments/{appt_a.id}/status",
        data={"new_status": "CANCELLED", "cancellation_reason": "SuperAdmin system override"},
        headers=superadmin_token_headers
    )
    assert res_a.status_code == 200

    # SuperAdmin updates Hospital B appointment
    res_b = await client.post(
        f"/api/v1/appointments/{appt_b.id}/status",
        data={"new_status": "CANCELLED", "cancellation_reason": "SuperAdmin system override"},
        headers=superadmin_token_headers
    )
    assert res_b.status_code == 200

    await db_session.refresh(appt_a)
    await db_session.refresh(appt_b)
    assert appt_a.status == "CANCELLED"
    assert appt_b.status == "CANCELLED"


@pytest.mark.asyncio
async def test_status_update_nonexistent_appointment_returns_404(
    client, receptionist_token_a
):
    """Test G: Non-existent appointment ID returns 404."""
    headers = {"Authorization": f"Bearer {receptionist_token_a}"}
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = await client.post(
        f"/api/v1/appointments/{fake_id}/status",
        data={"new_status": "CANCELLED"},
        headers=headers
    )
    assert response.status_code == 404
    assert "Appointment not found." in response.json()["detail"]


@pytest.mark.asyncio
async def test_status_reschedule_business_rules_preserved(
    client, db_session, sample_appointments, receptionist_token_a
):
    """Preserves business logic: rescheduling requires valid future ISO datetime within 2 days."""
    appt_a = sample_appointments["appt_a"]
    headers = {"Authorization": f"Bearer {receptionist_token_a}"}

    # Missing new_datetime for reschedule -> 400
    res_missing = await client.post(
        f"/api/v1/appointments/{appt_a.id}/status",
        data={"new_status": "RESCHEDULED"},
        headers=headers
    )
    assert res_missing.status_code == 400
    assert "New datetime required" in res_missing.json()["detail"]

    # Valid new_datetime within 2 days -> 200
    valid_reschedule = (datetime.now() + timedelta(days=1)).replace(microsecond=0).isoformat()
    res_valid = await client.post(
        f"/api/v1/appointments/{appt_a.id}/status",
        data={"new_status": "RESCHEDULED", "new_datetime": valid_reschedule},
        headers=headers
    )
    assert res_valid.status_code == 200
    assert res_valid.json()["new_status"] == "RESCHEDULED"

    # Second reschedule attempt -> 400 (max 1 reschedule limit)
    res_second = await client.post(
        f"/api/v1/appointments/{appt_a.id}/status",
        data={"new_status": "RESCHEDULED", "new_datetime": valid_reschedule},
        headers=headers
    )
    assert res_second.status_code == 400
    assert "maximum limit" in res_second.json()["detail"]
