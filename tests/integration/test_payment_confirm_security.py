import uuid
import pytest
from datetime import datetime, timedelta
from sqlalchemy import select
from app.database.models.call_log import User, UserRole
from app.database.models.appointment import Appointment, AppointmentStatusHistory
from app.core.dependencies import hash_password, create_access_token

@pytest.fixture
async def pending_appointments(db_session, hospital_a, hospital_b, doctor_a, doctor_b, patient_a, patient_b):
    """Creates pending payment appointments for Hospital A and Hospital B."""
    future_time = datetime.now() + timedelta(days=1)
    
    appt_a = Appointment(
        id="APPT-PAY-A-1",
        hospital_id=hospital_a.id,
        doctor_id=doctor_a.id,
        patient_id=patient_a.id,
        appointment_datetime=future_time,
        status="PENDING_PAYMENT",
        payment_status="PENDING",
        source="ONLINE"
    )
    appt_b = Appointment(
        id="APPT-PAY-B-1",
        hospital_id=hospital_b.id,
        doctor_id=doctor_b.id,
        patient_id=patient_b.id,
        appointment_datetime=future_time,
        status="PENDING_PAYMENT",
        payment_status="PENDING",
        source="ONLINE"
    )
    db_session.add(appt_a)
    db_session.add(appt_b)
    await db_session.commit()
    await db_session.refresh(appt_a)
    await db_session.refresh(appt_b)
    return {"appt_a": appt_a, "appt_b": appt_b}


@pytest.fixture
async def patient_user_token(db_session, hospital_a, patient_a, seed_roles):
    """Creates an authenticated patient user."""
    user = User(
        id="USER-PATIENT-PAY",
        hospital_id=hospital_a.id,
        username="patient_pay_user",
        email="patient_pay@example.com",
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
async def test_payment_confirm_unauthenticated_returns_401(client, db_session, pending_appointments):
    """Verifies unauthenticated payment confirmation is rejected with 401."""
    appt_a = pending_appointments["appt_a"]
    response = await client.post(f"/api/v1/payment/confirm/{appt_a.id}")
    assert response.status_code == 401

    # Verify DB unchanged
    await db_session.refresh(appt_a)
    assert appt_a.payment_status == "PENDING"
    assert appt_a.status == "PENDING_PAYMENT"


@pytest.mark.asyncio
async def test_payment_confirm_patient_role_returns_403(client, db_session, pending_appointments, patient_user_token):
    """Verifies patient role is forbidden from manually confirming payments."""
    appt_a = pending_appointments["appt_a"]
    headers = {"Authorization": f"Bearer {patient_user_token}"}
    response = await client.post(f"/api/v1/payment/confirm/{appt_a.id}", headers=headers)
    assert response.status_code == 403
    assert "Unauthorized" in response.json()["detail"]

    # Verify DB unchanged
    await db_session.refresh(appt_a)
    assert appt_a.payment_status == "PENDING"
    assert appt_a.status == "PENDING_PAYMENT"


@pytest.mark.asyncio
async def test_payment_confirm_receptionist_own_hospital_succeeds(
    client, db_session, pending_appointments, receptionist_token_a, receptionist_user_a
):
    """Verifies Receptionist A can confirm counter payment for Hospital A appointment."""
    appt_a = pending_appointments["appt_a"]
    headers = {"Authorization": f"Bearer {receptionist_token_a}"}
    response = await client.post(f"/api/v1/payment/confirm/{appt_a.id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

    # Verify DB updated
    await db_session.refresh(appt_a)
    assert appt_a.payment_status == "PAID"
    assert appt_a.status == "SCHEDULED"

    # Verify status history
    stmt = select(AppointmentStatusHistory).where(AppointmentStatusHistory.appointment_id == appt_a.id)
    history = (await db_session.execute(stmt)).scalars().all()
    assert len(history) >= 1
    assert history[-1].changed_by_user_id == receptionist_user_a.id


@pytest.mark.asyncio
async def test_payment_confirm_admin_own_hospital_succeeds(
    client, db_session, pending_appointments, auth_token_headers
):
    """Verifies Hospital Admin A can confirm payment for Hospital A appointment."""
    appt_a = pending_appointments["appt_a"]
    response = await client.post(f"/api/v1/payment/confirm/{appt_a.id}", headers=auth_token_headers)
    assert response.status_code == 200

    await db_session.refresh(appt_a)
    assert appt_a.payment_status == "PAID"
    assert appt_a.status == "SCHEDULED"


@pytest.mark.asyncio
async def test_payment_confirm_cross_tenant_receptionist_returns_403(
    client, db_session, pending_appointments, receptionist_token_a
):
    """Verifies Receptionist from Hospital A is forbidden from confirming Hospital B appointment."""
    appt_b = pending_appointments["appt_b"]
    headers = {"Authorization": f"Bearer {receptionist_token_a}"}
    response = await client.post(f"/api/v1/payment/confirm/{appt_b.id}", headers=headers)
    assert response.status_code == 403
    assert "Forbidden" in response.json()["detail"]
    assert "another hospital" in response.json()["detail"]

    # Verify Hospital B appointment in DB was NOT modified
    await db_session.refresh(appt_b)
    assert appt_b.payment_status == "PENDING"
    assert appt_b.status == "PENDING_PAYMENT"


@pytest.mark.asyncio
async def test_payment_confirm_cross_tenant_admin_returns_403(
    client, db_session, pending_appointments, auth_token_headers
):
    """Verifies Admin from Hospital A is forbidden from confirming Hospital B appointment."""
    appt_b = pending_appointments["appt_b"]
    response = await client.post(f"/api/v1/payment/confirm/{appt_b.id}", headers=auth_token_headers)
    assert response.status_code == 403
    assert "Forbidden" in response.json()["detail"]

    # Verify Hospital B appointment in DB was NOT modified
    await db_session.refresh(appt_b)
    assert appt_b.payment_status == "PENDING"
    assert appt_b.status == "PENDING_PAYMENT"


@pytest.mark.asyncio
async def test_payment_confirm_super_admin_allowed_cross_tenant(
    client, db_session, pending_appointments, superadmin_token_headers
):
    """Verifies SuperAdmin can confirm payments across any hospital tenant."""
    appt_a = pending_appointments["appt_a"]
    appt_b = pending_appointments["appt_b"]

    res_a = await client.post(f"/api/v1/payment/confirm/{appt_a.id}", headers=superadmin_token_headers)
    res_b = await client.post(f"/api/v1/payment/confirm/{appt_b.id}", headers=superadmin_token_headers)
    assert res_a.status_code == 200
    assert res_b.status_code == 200

    await db_session.refresh(appt_a)
    await db_session.refresh(appt_b)
    assert appt_a.payment_status == "PAID"
    assert appt_b.payment_status == "PAID"


@pytest.mark.asyncio
async def test_payment_confirm_nonexistent_appointment_returns_404(
    client, receptionist_token_a
):
    """Verifies non-existent appointment ID returns 404."""
    headers = {"Authorization": f"Bearer {receptionist_token_a}"}
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = await client.post(f"/api/v1/payment/confirm/{fake_id}", headers=headers)
    assert response.status_code == 404
    assert "Appointment not found." in response.json()["detail"]
