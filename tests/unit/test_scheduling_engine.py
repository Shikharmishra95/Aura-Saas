import pytest
from datetime import date, time, datetime, timedelta, timezone
from app.engines.scheduling import SchedulingEngine
from app.database.models.appointment import (
    DoctorSchedule, DoctorLeave, HospitalHoliday, WorkingHour, Appointment
)

def get_future_weekday(days_ahead=1):
    """Returns a future date guaranteed to be between Monday and Friday."""
    ist_now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
    target = ist_now.date() + timedelta(days=days_ahead)
    while target.isoweekday() > 5:
        target += timedelta(days=1)
    return target

@pytest.mark.asyncio
async def test_doctor_not_found_returns_empty_slots(db_session):
    engine = SchedulingEngine(db_session)
    slots = await engine.get_available_slots("NON-EXISTENT-DOC", get_future_weekday())
    assert slots == []

@pytest.mark.asyncio
async def test_inactive_doctor_returns_empty_slots(db_session, doctor_a):
    doctor_a.is_active = False
    await db_session.commit()
    engine = SchedulingEngine(db_session)
    slots = await engine.get_available_slots(doctor_a.id, get_future_weekday())
    assert slots == []

@pytest.mark.asyncio
async def test_past_date_slot_generation_blocked(db_session, doctor_a):
    engine = SchedulingEngine(db_session)
    past_date = date(2020, 1, 1)
    slots = await engine.get_available_slots(doctor_a.id, past_date)
    assert slots == []

@pytest.mark.asyncio
async def test_valid_doctor_schedule_generates_30min_slots(db_session, doctor_a, doctor_schedule_a):
    engine = SchedulingEngine(db_session)
    target_date = get_future_weekday(1)
    slots = await engine.get_available_slots(doctor_a.id, target_date)
    # Schedule is 10:00 to 13:00 (3 hours = 6 slots of 30 mins)
    assert len(slots) == 6
    assert slots[0].start_time == time(10, 0)
    assert slots[0].end_time == time(10, 30)
    assert slots[5].start_time == time(12, 30)
    assert slots[5].end_time == time(13, 0)

@pytest.mark.asyncio
async def test_hospital_holiday_blocks_all_slots(db_session, hospital_a, doctor_a, doctor_schedule_a):
    target_date = get_future_weekday(1)
    holiday = HospitalHoliday(
        id="HOL-1",
        hospital_id=hospital_a.id,
        holiday_date=target_date,
        name="National Independence Day"
    )
    db_session.add(holiday)
    await db_session.commit()

    engine = SchedulingEngine(db_session)
    slots = await engine.get_available_slots(doctor_a.id, target_date)
    assert slots == []

@pytest.mark.asyncio
async def test_hospital_closed_working_hour_blocks_slots(db_session, hospital_a, doctor_a, doctor_schedule_a):
    target_date = get_future_weekday(1)
    day_num = target_date.isoweekday()
    wh = WorkingHour(
        id="WH-1",
        hospital_id=hospital_a.id,
        day_of_week=day_num,
        open_time=time(9, 0),
        close_time=time(18, 0),
        is_closed=True
    )
    db_session.add(wh)
    await db_session.commit()

    engine = SchedulingEngine(db_session)
    slots = await engine.get_available_slots(doctor_a.id, target_date)
    assert slots == []

@pytest.mark.asyncio
async def test_doctor_approved_leave_blocks_slots(db_session, doctor_a, doctor_schedule_a):
    target_date = get_future_weekday(1)
    leave = DoctorLeave(
        id="LEAVE-1",
        doctor_id=doctor_a.id,
        start_date=target_date,
        end_date=target_date,
        reason="Medical Conference",
        status="APPROVED"
    )
    db_session.add(leave)
    await db_session.commit()

    engine = SchedulingEngine(db_session)
    slots = await engine.get_available_slots(doctor_a.id, target_date)
    assert slots == []

@pytest.mark.asyncio
async def test_doctor_pending_leave_does_not_block_slots(db_session, doctor_a, doctor_schedule_a):
    target_date = get_future_weekday(1)
    leave = DoctorLeave(
        id="LEAVE-2",
        doctor_id=doctor_a.id,
        start_date=target_date,
        end_date=target_date,
        reason="Personal Leave",
        status="PENDING"
    )
    db_session.add(leave)
    await db_session.commit()

    engine = SchedulingEngine(db_session)
    slots = await engine.get_available_slots(doctor_a.id, target_date)
    assert len(slots) == 6

@pytest.mark.asyncio
async def test_existing_scheduled_appointment_excludes_slot(db_session, hospital_a, doctor_a, patient_a, doctor_schedule_a):
    target_date = get_future_weekday(1)
    booked_dt = datetime.combine(target_date, time(10, 30))
    appt = Appointment(
        id="APPT-EXCLUDE-1",
        hospital_id=hospital_a.id,
        patient_id=patient_a.id,
        doctor_id=doctor_a.id,
        appointment_datetime=booked_dt,
        duration_minutes=30,
        status="SCHEDULED",
        source="WEB"
    )
    db_session.add(appt)
    await db_session.commit()

    engine = SchedulingEngine(db_session)
    slots = await engine.get_available_slots(doctor_a.id, target_date)
    assert len(slots) == 5
    slot_times = [s.start_time for s in slots]
    assert time(10, 30) not in slot_times
    assert time(10, 0) in slot_times
    assert time(11, 0) in slot_times

@pytest.mark.asyncio
async def test_cancelled_appointment_does_not_exclude_slot(db_session, hospital_a, doctor_a, patient_a, doctor_schedule_a):
    target_date = get_future_weekday(1)
    booked_dt = datetime.combine(target_date, time(10, 30))
    appt = Appointment(
        id="APPT-CANCELLED-1",
        hospital_id=hospital_a.id,
        patient_id=patient_a.id,
        doctor_id=doctor_a.id,
        appointment_datetime=booked_dt,
        duration_minutes=30,
        status="CANCELLED",
        source="WEB"
    )
    db_session.add(appt)
    await db_session.commit()

    engine = SchedulingEngine(db_session)
    slots = await engine.get_available_slots(doctor_a.id, target_date)
    assert len(slots) == 6
    slot_times = [s.start_time for s in slots]
    assert time(10, 30) in slot_times
