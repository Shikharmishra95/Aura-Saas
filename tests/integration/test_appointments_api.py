import pytest
from datetime import datetime, date, time, timedelta, timezone

def get_future_date(days_ahead=1):
    ist_now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
    target = ist_now.date() + timedelta(days=days_ahead)
    while target.isoweekday() > 5:
        target += timedelta(days=1)
    return target

@pytest.mark.asyncio
async def test_get_doctors_requires_authentication(client):
    response = await client.get("/api/v1/doctors")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_get_doctors_returns_hospital_doctors(client, doctor_a, receptionist_token_a):
    headers = {"Authorization": f"Bearer {receptionist_token_a}"}
    response = await client.get("/api/v1/doctors", headers=headers)
    assert response.status_code == 200
    doctors = response.json()
    assert len(doctors) >= 1
    doc_ids = [d["id"] for d in doctors]
    assert doctor_a.id in doc_ids

@pytest.mark.asyncio
async def test_get_departments_returns_hospital_departments(client, department_a, receptionist_token_a):
    headers = {"Authorization": f"Bearer {receptionist_token_a}"}
    response = await client.get("/api/v1/hospital/departments", headers=headers)
    assert response.status_code == 200
    deps = response.json()
    assert len(deps) >= 1
    assert deps[0]["name"] == "General Medicine"

@pytest.mark.asyncio
async def test_receptionist_book_appointment_creates_record(
    client, hospital_a, doctor_a, doctor_schedule_a, receptionist_token_a
):
    headers = {"Authorization": f"Bearer {receptionist_token_a}"}
    target_date = get_future_date(1)
    appt_time = f"{target_date.isoformat()}T10:00:00"

    payload = {
        "hospital_id": hospital_a.id,
        "patient_name": "Suresh Raina",
        "patient_phone": "+919876500001",
        "patient_gender": "Male",
        "patient_dob": "1986-11-27",
        "doctor_id": doctor_a.id,
        "appointment_datetime": appt_time,
        "reason": "Knee Checkup",
        "payment_mode": "CASH"
    }

    response = await client.post("/api/v1/receptionist/book-appointment", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "appointment_id" in data

@pytest.mark.asyncio
async def test_finish_consultation_updates_status(
    client, hospital_a, doctor_a, patient_a, doctor_token_a, db_session
):
    from app.database.models.appointment import Appointment
    appt = Appointment(
        id="APPT-CONSULT-1",
        hospital_id=hospital_a.id,
        patient_id=patient_a.id,
        doctor_id=doctor_a.id,
        appointment_datetime=datetime.now(),
        duration_minutes=30,
        status="SCHEDULED",
        source="WEB"
    )
    db_session.add(appt)
    await db_session.commit()

    headers = {"Authorization": f"Bearer {doctor_token_a}"}
    response = await client.post(f"/api/v1/appointments/{appt.id}/finish-consultation", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    await db_session.refresh(appt)
    assert appt.status == "CONSULTATION_FINISHED"
