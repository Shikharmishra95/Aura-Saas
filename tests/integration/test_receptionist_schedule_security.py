import uuid
import pytest
from datetime import date, datetime, timedelta
from app.database.models.call_log import User, UserRole
from app.database.models.appointment import Appointment
from app.core.dependencies import hash_password, create_access_token


@pytest.fixture
async def today_appointments(db_session, hospital_a, hospital_b, doctor_a, doctor_b, patient_a, patient_b):
    """Creates appointments scheduled for today in Hospital A and Hospital B."""
    today_noon = datetime.combine(date.today(), datetime.min.time()) + timedelta(hours=11)

    appt_a = Appointment(
        id="APPT-SCHED-A-1",
        hospital_id=hospital_a.id,
        doctor_id=doctor_a.id,
        patient_id=patient_a.id,
        appointment_datetime=today_noon,
        status="SCHEDULED",
        payment_status="PAID",
        reason="Alpha Patient Cardiac Consultation",
        source="PHONE"
    )
    appt_b = Appointment(
        id="APPT-SCHED-B-1",
        hospital_id=hospital_b.id,
        doctor_id=doctor_b.id,
        patient_id=patient_b.id,
        appointment_datetime=today_noon,
        status="SCHEDULED",
        payment_status="PAID",
        reason="Beta Patient Pediatric Fever",
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
        id="USER-PATIENT-SCHED",
        hospital_id=hospital_a.id,
        username="patient_sched_user",
        email="patient_sched@example.com",
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
async def test_receptionist_schedule_unauthenticated_returns_401(client, today_appointments):
    """Verifies that unauthenticated requests to the receptionist schedule are rejected with 401."""
    response = await client.get("/api/v1/receptionist/schedule")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_receptionist_schedule_patient_role_returns_403(client, today_appointments, patient_user_token):
    """Verifies that non-staff roles (e.g. PATIENT) cannot view the receptionist schedule (403 Forbidden)."""
    headers = {"Authorization": f"Bearer {patient_user_token}"}
    response = await client.get("/api/v1/receptionist/schedule", headers=headers)
    assert response.status_code == 403
    assert "Unauthorized" in response.json()["detail"]


@pytest.mark.asyncio
async def test_receptionist_schedule_receptionist_own_hospital_succeeds(
    client, today_appointments, receptionist_token_a
):
    """Verifies that a receptionist can view the daily schedule for their own hospital (200 OK HTML)."""
    headers = {"Authorization": f"Bearer {receptionist_token_a}"}
    response = await client.get("/api/v1/receptionist/schedule", headers=headers)
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")

    html_content = response.text
    # Should contain Hospital A details
    assert "Alpha Patient Cardiac Consultation" in html_content
    assert "Aarav" in html_content


@pytest.mark.asyncio
async def test_receptionist_schedule_doctor_own_hospital_succeeds(
    client, today_appointments, doctor_token_a
):
    """Verifies that a doctor can view the daily schedule for their own hospital (200 OK HTML)."""
    headers = {"Authorization": f"Bearer {doctor_token_a}"}
    response = await client.get("/api/v1/receptionist/schedule", headers=headers)
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "Alpha Patient Cardiac Consultation" in response.text


@pytest.mark.asyncio
async def test_receptionist_schedule_admin_own_hospital_succeeds(
    client, today_appointments, auth_token_headers
):
    """Verifies that a hospital admin can view the daily schedule for their own hospital (200 OK HTML)."""
    response = await client.get("/api/v1/receptionist/schedule", headers=auth_token_headers)
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "Alpha Patient Cardiac Consultation" in response.text


@pytest.mark.asyncio
async def test_receptionist_schedule_cross_tenant_receptionist_returns_403(
    client, today_appointments, receptionist_token_a, hospital_b
):
    """Verifies that a receptionist cannot view the schedule of another hospital (cross-tenant 403)."""
    headers = {"Authorization": f"Bearer {receptionist_token_a}"}
    response = await client.get(f"/api/v1/receptionist/schedule?hospital_id={hospital_b.id}", headers=headers)
    assert response.status_code == 403
    assert "Forbidden: Cannot view schedule of another hospital." in response.json()["detail"]


@pytest.mark.asyncio
async def test_receptionist_schedule_cross_tenant_admin_returns_403(
    client, today_appointments, auth_token_headers, hospital_b
):
    """Verifies that an admin cannot view the schedule of another hospital (cross-tenant 403)."""
    response = await client.get(f"/api/v1/receptionist/schedule?hospital_id={hospital_b.id}", headers=auth_token_headers)
    assert response.status_code == 403
    assert "Forbidden: Cannot view schedule of another hospital." in response.json()["detail"]


@pytest.mark.asyncio
async def test_receptionist_schedule_super_admin_allowed_cross_tenant(
    client, today_appointments, superadmin_token_headers, hospital_a, hospital_b
):
    """Verifies that a Super Admin can view the schedule of any hospital."""
    res_a = await client.get(f"/api/v1/receptionist/schedule?hospital_id={hospital_a.id}", headers=superadmin_token_headers)
    res_b = await client.get(f"/api/v1/receptionist/schedule?hospital_id={hospital_b.id}", headers=superadmin_token_headers)

    assert res_a.status_code == 200
    assert res_b.status_code == 200

    assert "Alpha Patient Cardiac Consultation" in res_a.text
    assert "Beta Patient Pediatric Fever" in res_b.text


@pytest.mark.asyncio
async def test_receptionist_schedule_data_isolation_between_tenants(
    client, today_appointments, receptionist_token_a
):
    """Verifies that Hospital A schedule contains NO data or doctors from Hospital B."""
    headers = {"Authorization": f"Bearer {receptionist_token_a}"}
    response = await client.get("/api/v1/receptionist/schedule", headers=headers)
    assert response.status_code == 200
    content = response.text

    # Hospital A data should be present
    assert "Alpha Patient Cardiac Consultation" in content
    # Hospital B data should NOT be present
    assert "Beta Patient Pediatric Fever" not in content
    assert "Bob Smith" not in content


@pytest.mark.asyncio
async def test_receptionist_schedule_invalid_date_format_returns_400(
    client, receptionist_token_a
):
    """Verifies that an invalid date string returns a 400 Bad Request."""
    headers = {"Authorization": f"Bearer {receptionist_token_a}"}
    response = await client.get("/api/v1/receptionist/schedule?date_str=not-a-date", headers=headers)
    assert response.status_code == 400
    assert "Invalid date format" in response.json()["detail"]
