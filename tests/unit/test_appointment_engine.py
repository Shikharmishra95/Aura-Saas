import pytest
from datetime import date, time, datetime, timedelta, timezone
from app.engines.appointment import AppointmentEngine
from app.database.models.appointment import Appointment, AppointmentStatusHistory

def get_future_date(days_ahead=1):
    ist_now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
    target = ist_now.date() + timedelta(days=days_ahead)
    while target.isoweekday() > 6:
        target += timedelta(days=1)
    return target

@pytest.mark.asyncio
async def test_book_appointment_success(db_session, hospital_a, doctor_a, patient_a, doctor_schedule_a):
    engine = AppointmentEngine(db_session)
    target_date = get_future_date(1)
    appt_dt = datetime.combine(target_date, time(10, 0))

    result = await engine.book_appointment(
        hospital_id=hospital_a.id,
        patient_id=patient_a.id,
        doctor_id=doctor_a.id,
        appointment_datetime=appt_dt,
        reason="General Health Consultation",
        source="WEB"
    )

    assert result["code"] == "BOOKING_SUCCESS"
    assert "appointment_id" in result
    assert result["patient_name"] == "Rohan Verma"

@pytest.mark.asyncio
async def test_book_appointment_invalid_patient_fails(db_session, hospital_a, doctor_a, doctor_schedule_a):
    engine = AppointmentEngine(db_session)
    target_date = get_future_date(1)
    appt_dt = datetime.combine(target_date, time(10, 0))

    result = await engine.book_appointment(
        hospital_id=hospital_a.id,
        patient_id="NON-EXISTENT-PATIENT",
        doctor_id=doctor_a.id,
        appointment_datetime=appt_dt
    )

    assert result["code"] == "PATIENT_NOT_FOUND"

@pytest.mark.asyncio
async def test_book_appointment_invalid_doctor_fails(db_session, hospital_a, patient_a):
    engine = AppointmentEngine(db_session)
    target_date = get_future_date(1)
    appt_dt = datetime.combine(target_date, time(10, 0))

    result = await engine.book_appointment(
        hospital_id=hospital_a.id,
        patient_id=patient_a.id,
        doctor_id="NON-EXISTENT-DOCTOR",
        appointment_datetime=appt_dt
    )

    assert result["code"] == "DOCTOR_NOT_FOUND"

@pytest.mark.asyncio
async def test_book_appointment_past_date_fails(db_session, hospital_a, doctor_a, patient_a):
    engine = AppointmentEngine(db_session)
    past_dt = datetime(2020, 1, 1, 10, 0)

    result = await engine.book_appointment(
        hospital_id=hospital_a.id,
        patient_id=patient_a.id,
        doctor_id=doctor_a.id,
        appointment_datetime=past_dt
    )

    assert result["code"] == "SAME_DAY_NOT_ALLOWED"

@pytest.mark.asyncio
async def test_book_appointment_same_day_voice_rejected(db_session, hospital_a, doctor_a, patient_a, doctor_schedule_a):
    engine = AppointmentEngine(db_session)
    ist_now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
    same_day_dt = datetime.combine(ist_now.date(), time(23, 59))

    result = await engine.book_appointment(
        hospital_id=hospital_a.id,
        patient_id=patient_a.id,
        doctor_id=doctor_a.id,
        appointment_datetime=same_day_dt,
        source="VOICE"
    )

    assert result["code"] == "SAME_DAY_NOT_ALLOWED"

@pytest.mark.asyncio
async def test_book_appointment_too_far_ahead_rejected(db_session, hospital_a, doctor_a, patient_a, doctor_schedule_a):
    engine = AppointmentEngine(db_session)
    far_dt = datetime.now(timezone.utc) + timedelta(days=10)

    result = await engine.book_appointment(
        hospital_id=hospital_a.id,
        patient_id=patient_a.id,
        doctor_id=doctor_a.id,
        appointment_datetime=far_dt,
        source="WEB"
    )

    assert result["code"] == "DATE_TOO_FAR"

@pytest.mark.asyncio
async def test_book_appointment_duplicate_booking_rejected(db_session, hospital_a, doctor_a, patient_a, doctor_schedule_a):
    engine = AppointmentEngine(db_session)
    target_date = get_future_date(1)
    appt_dt1 = datetime.combine(target_date, time(10, 0))
    appt_dt2 = datetime.combine(target_date, time(11, 0))

    res1 = await engine.book_appointment(
        hospital_id=hospital_a.id,
        patient_id=patient_a.id,
        doctor_id=doctor_a.id,
        appointment_datetime=appt_dt1,
        source="WEB"
    )
    assert res1["code"] == "BOOKING_SUCCESS"

    res2 = await engine.book_appointment(
        hospital_id=hospital_a.id,
        patient_id=patient_a.id,
        doctor_id=doctor_a.id,
        appointment_datetime=appt_dt2,
        source="WEB"
    )
    assert res2["code"] == "DUPLICATE_BOOKING"

@pytest.mark.asyncio
async def test_cancel_appointment_success(db_session, hospital_a, doctor_a, patient_a, doctor_schedule_a):
    engine = AppointmentEngine(db_session)
    target_date = get_future_date(1)
    appt_dt = datetime.combine(target_date, time(10, 0))

    res = await engine.book_appointment(
        hospital_id=hospital_a.id,
        patient_id=patient_a.id,
        doctor_id=doctor_a.id,
        appointment_datetime=appt_dt,
        source="WEB"
    )
    appt_id = res["appointment_id"]

    cancel_res = await engine.cancel_appointment(appt_id, reason="Patient had emergency")
    assert cancel_res["code"] == "CANCELLED"

    cancel_again = await engine.cancel_appointment(appt_id)
    assert cancel_again["code"] == "ALREADY_CANCELLED"
