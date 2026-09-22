import pytest
from datetime import datetime, date, time, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from app.database.models.appointment import Appointment
from app.engines.appointment import AppointmentEngine


@pytest.mark.asyncio
async def test_db_unique_constraint_rejects_duplicate_active_slot(
    db_session, hospital_a, doctor_a, patient_a, patient_b
):
    """
    Direct Database Engine Test:
    Verifies that the database-level unique constraint 'uq_doctor_appointment_slot'
    physically prevents two active appointments for the same doctor at the same datetime.
    """
    target_dt = datetime.combine(date.today() + timedelta(days=2), time(11, 0))

    appt1 = Appointment(
        id="APPT-DIRECT-1",
        hospital_id=hospital_a.id,
        patient_id=patient_a.id,
        doctor_id=doctor_a.id,
        appointment_datetime=target_dt,
        status="SCHEDULED",
        payment_status="PAID"
    )
    db_session.add(appt1)
    await db_session.commit()

    appt2 = Appointment(
        id="APPT-DIRECT-2",
        hospital_id=hospital_a.id,
        patient_id=patient_b.id,
        doctor_id=doctor_a.id,
        appointment_datetime=target_dt,
        status="SCHEDULED",
        payment_status="PAID"
    )
    db_session.add(appt2)

    with pytest.raises(IntegrityError):
        await db_session.flush()

    await db_session.rollback()


@pytest.mark.asyncio
async def test_cancelled_appointment_allows_rebooking_same_slot(
    db_session, hospital_a, doctor_a, patient_a, patient_b
):
    """
    Verifies that when an appointment is cancelled (active_slot_token=None),
    another patient can book the exact same slot without IntegrityError conflicts.
    """
    target_dt = datetime.combine(date.today() + timedelta(days=2), time(11, 30))

    cancelled_appt = Appointment(
        id="APPT-CAN-PREV-1",
        hospital_id=hospital_a.id,
        patient_id=patient_a.id,
        doctor_id=doctor_a.id,
        appointment_datetime=target_dt,
        status="CANCELLED",
        payment_status="REFUNDED"
    )
    db_session.add(cancelled_appt)
    await db_session.commit()

    # Verify cancelled appointment has active_slot_token = None
    await db_session.refresh(cancelled_appt)
    assert cancelled_appt.active_slot_token is None

    # New appointment booked for the exact same slot
    new_appt = Appointment(
        id="APPT-NEW-ACTIVE-1",
        hospital_id=hospital_a.id,
        patient_id=patient_b.id,
        doctor_id=doctor_a.id,
        appointment_datetime=target_dt,
        status="SCHEDULED",
        payment_status="PAID"
    )
    db_session.add(new_appt)
    await db_session.commit()

    # Both appointments must exist in database without conflict
    stmt = select(Appointment).where(
        Appointment.doctor_id == doctor_a.id,
        Appointment.appointment_datetime == target_dt
    )
    results = (await db_session.execute(stmt)).scalars().all()
    assert len(results) == 2
    statuses = {a.status for a in results}
    assert statuses == {"CANCELLED", "SCHEDULED"}


@pytest.mark.asyncio
async def test_duplicate_booking_rejected_via_api(
    client, db_session, hospital_a, doctor_a, doctor_schedule_a, receptionist_token_a
):
    """
    Verifies that booking requests to /api/v1/receptionist/book-appointment
    for the exact same slot result in the first succeeding (200) and the duplicate being rejected (400).
    """
    ist_now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
    target_date = ist_now.date() + timedelta(days=1)
    while target_date.isoweekday() > 5:
        target_date += timedelta(days=1)

    appt_time = f"{target_date.isoformat()}T10:30:00"
    headers = {"Authorization": f"Bearer {receptionist_token_a}"}

    payload_1 = {
        "hospital_id": hospital_a.id,
        "patient_name": "Sequential Patient 1",
        "patient_phone": "+919876543201",
        "patient_gender": "Male",
        "patient_dob": "1991-01-01",
        "doctor_id": doctor_a.id,
        "appointment_datetime": appt_time,
        "reason": "Chest checkup",
        "payment_mode": "CASH"
    }
    payload_2 = {
        "hospital_id": hospital_a.id,
        "patient_name": "Sequential Patient 2",
        "patient_phone": "+919876543202",
        "patient_gender": "Female",
        "patient_dob": "1992-02-02",
        "doctor_id": doctor_a.id,
        "appointment_datetime": appt_time,
        "reason": "Routine consultation",
        "payment_mode": "CASH"
    }

    # First booking request succeeds
    res1 = await client.post("/api/v1/receptionist/book-appointment", json=payload_1, headers=headers)
    assert res1.status_code == 200, f"Expected first booking to succeed: {res1.text}"

    # Second booking request for the exact same slot is rejected
    res2 = await client.post("/api/v1/receptionist/book-appointment", json=payload_2, headers=headers)
    assert res2.status_code == 400, f"Expected second booking to be rejected: {res2.text}"
    assert "already booked" in res2.json()["detail"].lower()

    # Confirm exactly 1 active record exists in DB
    target_dt = datetime.fromisoformat(appt_time)
    stmt = select(Appointment).where(
        Appointment.doctor_id == doctor_a.id,
        Appointment.appointment_datetime == target_dt,
        Appointment.status.in_(["SCHEDULED", "CONFIRMED", "PENDING_PAYMENT"])
    )
    records = (await db_session.execute(stmt)).scalars().all()
    assert len(records) == 1


@pytest.mark.asyncio
async def test_appointment_engine_catches_integrity_error(
    db_session, hospital_a, doctor_a, patient_a, patient_b, doctor_schedule_a
):
    """
    Verifies that AppointmentEngine.book_appointment catches IntegrityError gracefully
    and returns a structured SLOT_FULL response code.
    """
    ist_now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
    target_date = ist_now.date() + timedelta(days=1)
    while target_date.isoweekday() > 5:
        target_date += timedelta(days=1)

    target_dt = datetime.combine(target_date, time(10, 0))

    engine = AppointmentEngine(db_session)

    # First booking via engine
    res1 = await engine.book_appointment(
        hospital_id=hospital_a.id,
        patient_id=patient_a.id,
        doctor_id=doctor_a.id,
        appointment_datetime=target_dt,
        reason="Initial consultation",
        source="PORTAL"
    )
    assert res1["code"] == "BOOKING_SUCCESS"
    await db_session.commit()

    # Second booking via engine for exact same slot
    res2 = await engine.book_appointment(
        hospital_id=hospital_a.id,
        patient_id=patient_b.id,
        doctor_id=doctor_a.id,
        appointment_datetime=target_dt,
        reason="Conflicting consultation",
        source="PORTAL"
    )
    assert res2["code"] == "SLOT_FULL"
    assert "not available" in res2["message"] or "reserved" in res2["message"]


@pytest.mark.asyncio
async def test_reschedule_to_occupied_slot_prevented(
    db_session, hospital_a, doctor_a, patient_a, patient_b, doctor_schedule_a
):
    """
    Verifies that rescheduling an appointment to a slot already occupied by another patient
    is rejected and does not overwrite the existing booking.
    """
    ist_now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
    target_date = ist_now.date() + timedelta(days=1)
    while target_date.isoweekday() > 5:
        target_date += timedelta(days=1)

    dt_slot_1 = datetime.combine(target_date, time(10, 0))
    dt_slot_2 = datetime.combine(target_date, time(10, 30))

    engine = AppointmentEngine(db_session)

    # Book Slot 1 for Patient A
    res_a = await engine.book_appointment(
        hospital_id=hospital_a.id,
        patient_id=patient_a.id,
        doctor_id=doctor_a.id,
        appointment_datetime=dt_slot_1,
        source="PORTAL"
    )
    assert res_a["code"] == "BOOKING_SUCCESS"

    # Book Slot 2 for Patient B
    res_b = await engine.book_appointment(
        hospital_id=hospital_a.id,
        patient_id=patient_b.id,
        doctor_id=doctor_a.id,
        appointment_datetime=dt_slot_2,
        source="PORTAL"
    )
    assert res_b["code"] == "BOOKING_SUCCESS"
    await db_session.commit()

    # Patient B attempts to reschedule into Patient A's slot (Slot 1)
    res_resched = await engine.reschedule_appointment(
        appointment_id=res_b["appointment_id"],
        new_datetime=dt_slot_1
    )
    assert res_resched["code"] == "SLOT_FULL"

    # Verify Patient B appointment remains at Slot 2
    appt_b = (await db_session.execute(
        select(Appointment).where(Appointment.id == res_b["appointment_id"])
    )).scalar_one()
    assert appt_b.appointment_datetime == dt_slot_2
