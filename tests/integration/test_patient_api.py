import pytest
from datetime import datetime, date, time, timedelta, timezone

def get_future_date(days_ahead=1):
    ist_now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
    target = ist_now.date() + timedelta(days=days_ahead)
    while target.isoweekday() > 5:
        target += timedelta(days=1)
    return target

@pytest.mark.asyncio
async def test_patient_send_otp_success(client, hospital_a):
    payload = {
        "hospital_id": hospital_a.id,
        "phone": "+919888877777"
    }
    response = await client.post("/api/v1/patient/send-otp", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["message"] == "OTP sent successfully."

@pytest.mark.asyncio
async def test_patient_verify_otp_returns_patient_jwt(client, hospital_a):
    send_payload = {
        "hospital_id": hospital_a.id,
        "phone": "+919888866666"
    }
    await client.post("/api/v1/patient/send-otp", json=send_payload)

    verify_payload = {
        "hospital_id": hospital_a.id,
        "phone": "+919888866666",
        "otp": "1234",
        "name": "Kavita Roy",
        "age": 28
    }
    response = await client.post("/api/v1/patient/verify-otp", json=verify_payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["patient"]["name"] == "Kavita Roy"
    assert data["patient"]["hospital_id"] == hospital_a.id

@pytest.mark.asyncio
async def test_patient_verify_otp_with_invalid_otp_fails(client, hospital_a):
    send_payload = {
        "hospital_id": hospital_a.id,
        "phone": "+919888855555"
    }
    await client.post("/api/v1/patient/send-otp", json=send_payload)

    verify_payload = {
        "hospital_id": hospital_a.id,
        "phone": "+919888855555",
        "otp": "9999"
    }
    response = await client.post("/api/v1/patient/verify-otp", json=verify_payload)
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid OTP."

@pytest.mark.asyncio
async def test_patient_portal_get_hospital_by_slug(client, hospital_a, department_a, doctor_a):
    response = await client.get(f"/api/v1/patient/hospital/{hospital_a.slug}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == hospital_a.name
    assert len(data["departments"]) >= 1
    assert data["departments"][0]["name"] == "General Medicine"

@pytest.mark.asyncio
async def test_patient_portal_get_doctors(client, hospital_a, doctor_a):
    response = await client.get(f"/api/v1/patient/doctors?hospital_id={hospital_a.id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["id"] == doctor_a.id

@pytest.mark.asyncio
async def test_patient_self_booking_with_jwt(
    client, hospital_a, doctor_a, doctor_schedule_a, patient_a, patient_token_a
):
    headers = {"Authorization": f"Bearer {patient_token_a}"}
    target_date = get_future_date(1)
    appt_time = f"{target_date.isoformat()}T10:30:00"

    payload = {
        "hospital_id": hospital_a.id,
        "doctor_id": doctor_a.id,
        "patient_id": patient_a.id,
        "patient_name": "Rohan Verma",
        "patient_age": 30,
        "appointment_datetime": appt_time,
        "reason": "Headache consultation",
        "payment_mode": "ONLINE"
    }

    response = await client.post("/api/v1/patient/appointments", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "appointment_id" in data
