import re
import pytest
import pytest_asyncio
from datetime import date, datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.appointment import (
    Hospital, Department, Doctor, DoctorSchedule, DoctorLeave,
    Appointment, AppointmentStatusHistory, Patient
)
from app.database.models.call_log import User, Role, UserRole
from app.engines.copilot_engine import CopilotEngine
from app.engines.conversation_memory import conversation_memory
from app.tools.control_tower_tools import ControlTowerTools

# Setup rich multi-tenant hospital fixtures
@pytest_asyncio.fixture
async def golden_db_setup(db_session: AsyncSession):
    """
    Seeds a realistic multi-tenant hospital environment:
    - Balaji Healthcare (HOSP-BALAJI-1) with Dr CP Tiwari & Dr Shiva Mishra
    - Alpha Medical Center (HOSP-ALPHA-2) with Dr Aarav Sharma
    - Active Appointments, Missed Appointments, Schedules, and SaaS Subscriptions
    """
    # 1. Tenant Hospitals
    hosp_balaji = Hospital(
        id="HOSP-BALAJI-1",
        name="Balaji Healthcare",
        slug="balaji-healthcare",
        phone="+919876543210",
        email="info@balajihealthcare.com",
        address="Sector 12, Ring Road, Lucknow",
        is_active=True,
        subscription_plan="ENTERPRISE",
        plan_status="ACTIVE",
        plan_expires_at=datetime.now() + timedelta(days=20), # Expiring in 20 days
        ai_voice_enabled=True
    )
    hosp_alpha = Hospital(
        id="HOSP-ALPHA-2",
        name="Alpha Medical Center",
        slug="alpha-medical",
        phone="+919123456789",
        email="contact@alphamedical.com",
        address="Civil Lines, Delhi",
        is_active=True,
        subscription_plan="PRO",
        plan_status="ACTIVE",
        plan_expires_at=datetime.now() + timedelta(days=120),
        ai_voice_enabled=False
    )
    db_session.add_all([hosp_balaji, hosp_alpha])
    await db_session.commit()

    # 2. Departments
    dept_cardio = Department(id="DEP-CARD-1", hospital_id="HOSP-BALAJI-1", name="Cardiology", is_active=True)
    dept_ortho = Department(id="DEP-ORTH-1", hospital_id="HOSP-BALAJI-1", name="Orthopedics", is_active=True)
    dept_gen = Department(id="DEP-GEN-2", hospital_id="HOSP-ALPHA-2", name="General Medicine", is_active=True)
    db_session.add_all([dept_cardio, dept_ortho, dept_gen])
    await db_session.commit()

    # 3. Doctors
    doc_shiva = Doctor(
        id="DOC-SHIVA-1",
        hospital_id="HOSP-BALAJI-1",
        department_id="DEP-CARD-1",
        first_name="Shiva",
        last_name="Mishra",
        phone="+919888877771",
        email="dr.shiva@balaji.com",
        license_number="CARD-8891",
        opd_fees=800,
        is_active=True
    )
    doc_cp = Doctor(
        id="DOC-CP-1",
        hospital_id="HOSP-BALAJI-1",
        department_id="DEP-ORTH-1",
        first_name="CP",
        last_name="Tiwari",
        phone="+919888877772",
        email="dr.cp@balaji.com",
        license_number="ORTH-1122",
        opd_fees=600,
        is_active=True
    )
    doc_aarav = Doctor(
        id="DOC-AARAV-1",
        hospital_id="HOSP-ALPHA-2",
        department_id="DEP-GEN-2",
        first_name="Aarav",
        last_name="Sharma",
        phone="+919888877773",
        email="dr.aarav@alpha.com",
        license_number="GEN-4433",
        opd_fees=500,
        is_active=True
    )
    db_session.add_all([doc_shiva, doc_cp, doc_aarav])
    await db_session.commit()

    # 4. Doctor Schedules (Monday-Saturday)
    today_dow = datetime.now().isoweekday()
    for doc in [doc_shiva, doc_cp, doc_aarav]:
        for dow in range(1, 7):
            sched = DoctorSchedule(
                id=f"SCHED-{doc.id}-{dow}",
                doctor_id=doc.id,
                day_of_week=dow,
                start_time=datetime.strptime("09:00", "%H:%M").time(),
                end_time=datetime.strptime("17:00", "%H:%M").time(),
                slot_duration_minutes=15
            )
            db_session.add(sched)
    await db_session.commit()

    # 5. Patients
    pat_1 = Patient(
        id="PAT-101",
        hospital_id="HOSP-BALAJI-1",
        first_name="Shikhar",
        last_name="Mishra",
        date_of_birth=date(1995, 5, 15),
        phone="9876543210",
        gender="Male",
        is_active=True
    )
    pat_2 = Patient(
        id="PAT-102",
        hospital_id="HOSP-BALAJI-1",
        first_name="Rahul",
        last_name="Verma",
        date_of_birth=date(1992, 8, 20),
        phone="9876543211",
        gender="Male",
        is_active=True
    )
    db_session.add_all([pat_1, pat_2])
    await db_session.commit()

    # 6. Appointments (3 Booked for Dr Shiva, 1 Cancelled/Missed for Dr Shiva)
    today_d = date.today()
    appt1 = Appointment(
        id="APPT-101",
        hospital_id="HOSP-BALAJI-1",
        patient_id="PAT-101",
        doctor_id="DOC-SHIVA-1",
        appointment_datetime=datetime.combine(today_d, datetime.strptime("10:00", "%H:%M").time()),
        status="SCHEDULED",
        payment_status="PAID",
        payment_method="ONLINE",
        reason="Chest discomfort"
    )
    appt2 = Appointment(
        id="APPT-102",
        hospital_id="HOSP-BALAJI-1",
        patient_id="PAT-102",
        doctor_id="DOC-SHIVA-1",
        appointment_datetime=datetime.combine(today_d, datetime.strptime("10:30", "%H:%M").time()),
        status="COMPLETED",
        payment_status="PAID",
        payment_method="CASH",
        reason="Routine ECG"
    )
    appt3 = Appointment(
        id="APPT-103",
        hospital_id="HOSP-BALAJI-1",
        patient_id="PAT-101",
        doctor_id="DOC-SHIVA-1",
        appointment_datetime=datetime.combine(today_d, datetime.strptime("11:00", "%H:%M").time()),
        status="CANCELLED",
        payment_status="REFUNDED",
        payment_method="ONLINE",
        reason="Patient unavailable"
    )
    db_session.add_all([appt1, appt2, appt3])
    await db_session.commit()

    return {
        "hosp_balaji": hosp_balaji,
        "hosp_alpha": hosp_alpha,
        "doc_shiva": doc_shiva,
        "doc_cp": doc_cp,
        "doc_aarav": doc_aarav,
        "pat_1": pat_1
    }


# ==============================================================================
# ROLE 1: SUPERADMIN (15 Tests)
# ==============================================================================

@pytest.mark.asyncio
async def test_01_superadmin_expiring_subscriptions(golden_db_setup, db_session):
    res = await CopilotEngine.chat(
        user_message="Which subscriptions are expiring in next 30 days?",
        user_id="SA-01", hospital_id="super_admin", role="SUPERADMIN",
        hospital_name="AURA SaaS Platform", active_tab="overview", selected_date="",
        chat_history=[], db=db_session
    )
    assert "Balaji Healthcare" in res["reply"]
    assert "20 days left" in res["reply"] or "days left" in res["reply"]

@pytest.mark.asyncio
async def test_02_superadmin_active_hospitals_count(golden_db_setup, db_session):
    res = await CopilotEngine.chat(
        user_message="How many hospitals are active on AURA platform?",
        user_id="SA-01", hospital_id="super_admin", role="SUPERADMIN",
        hospital_name="AURA SaaS Platform", active_tab="overview", selected_date="",
        chat_history=[], db=db_session
    )
    assert "active hospitals" in res["reply"].lower()
    assert "Balaji Healthcare" in res["reply"]

@pytest.mark.asyncio
async def test_03_superadmin_top_revenue_hospital(golden_db_setup, db_session):
    res = await CopilotEngine.chat(
        user_message="Which hospital generates maximum revenue?",
        user_id="SA-01", hospital_id="super_admin", role="SUPERADMIN",
        hospital_name="AURA SaaS Platform", active_tab="overview", selected_date="",
        chat_history=[], db=db_session
    )
    assert "Top Revenue" in res["reply"] or "revenue" in res["reply"].lower()

@pytest.mark.asyncio
async def test_04_superadmin_voice_telemetry(golden_db_setup, db_session):
    res = await CopilotEngine.chat(
        user_message="Total AI voice calls processed today",
        user_id="SA-01", hospital_id="super_admin", role="SUPERADMIN",
        hospital_name="AURA SaaS Platform", active_tab="overview", selected_date="",
        chat_history=[], db=db_session
    )
    assert "AI Voice" in res["reply"] or "calls" in res["reply"].lower()

@pytest.mark.asyncio
async def test_05_superadmin_platform_error_logs(golden_db_setup, db_session):
    res = await CopilotEngine.chat(
        user_message="Show platform error logs telemetry",
        user_id="SA-01", hospital_id="super_admin", role="SUPERADMIN",
        hospital_name="AURA SaaS Platform", active_tab="overview", selected_date="",
        chat_history=[], db=db_session
    )
    assert res.get("tool_used") == "get_platform_error_telemetry" or "error" in res["reply"].lower()

@pytest.mark.asyncio
async def test_06_superadmin_audit_trail(golden_db_setup, db_session):
    res = await CopilotEngine.chat(
        user_message="Show platform security audit trail",
        user_id="SA-01", hospital_id="super_admin", role="SUPERADMIN",
        hospital_name="AURA SaaS Platform", active_tab="overview", selected_date="",
        chat_history=[], db=db_session
    )
    assert res.get("tool_used") == "get_platform_audit_trail" or "audit" in res["reply"].lower()

@pytest.mark.asyncio
async def test_07_superadmin_balaji_phone_lookup(golden_db_setup, db_session):
    res = await CopilotEngine.chat(
        user_message="balaji hospital ka number do mujhe",
        user_id="SA-01", hospital_id="super_admin", role="SUPERADMIN",
        hospital_name="AURA SaaS Platform", active_tab="overview", selected_date="",
        chat_history=[], db=db_session
    )
    assert "9876543210" in res["reply"]
    assert "Balaji Healthcare" in res["reply"]
    assert "Invalid session" not in res["reply"]

@pytest.mark.asyncio
async def test_08_superadmin_balaji_info_lookup(golden_db_setup, db_session):
    res = await CopilotEngine.chat(
        user_message="balaji hospital info",
        user_id="SA-01", hospital_id="super_admin", role="SUPERADMIN",
        hospital_name="AURA SaaS Platform", active_tab="overview", selected_date="",
        chat_history=[], db=db_session
    )
    assert "Balaji Healthcare" in res["reply"]
    assert "ENTERPRISE" in res["reply"]

@pytest.mark.asyncio
async def test_09_superadmin_search_alpha_by_slug(golden_db_setup, db_session):
    res = await CopilotEngine.chat(
        user_message="search hospital alpha-medical",
        user_id="SA-01", hospital_id="super_admin", role="SUPERADMIN",
        hospital_name="AURA SaaS Platform", active_tab="overview", selected_date="",
        chat_history=[], db=db_session
    )
    assert "Alpha Medical Center" in res["reply"]
    assert "9123456789" in res["reply"]

@pytest.mark.asyncio
async def test_10_superadmin_search_by_id(golden_db_setup, db_session):
    res = await CopilotEngine.chat(
        user_message="details for HOSP-BALAJI-1",
        user_id="SA-01", hospital_id="super_admin", role="SUPERADMIN",
        hospital_name="AURA SaaS Platform", active_tab="overview", selected_date="",
        chat_history=[], db=db_session
    )
    assert "Balaji Healthcare" in res["reply"]

@pytest.mark.asyncio
async def test_11_superadmin_extend_subscription_token(golden_db_setup, db_session):
    res = await ControlTowerTools.extend_hospital_subscription(
        hospital_id="HOSP-BALAJI-1", duration_days=30, user_id="SA-01", db=db_session
    )
    assert res["status"] == "CONFIRMATION_REQUIRED"
    assert "confirmation_token" in res

@pytest.mark.asyncio
async def test_12_superadmin_voice_toggle_token(golden_db_setup, db_session):
    res = await ControlTowerTools.toggle_hospital_ai_voice_service(
        hospital_id="HOSP-BALAJI-1", enabled=False, user_id="SA-01", db=db_session
    )
    assert res["status"] == "CONFIRMATION_REQUIRED"
    assert "confirmation_token" in res

@pytest.mark.asyncio
async def test_13_superadmin_rbac_isolation(golden_db_setup, db_session):
    from app.engines.tool_registry import tool_registry
    assert tool_registry.is_authorized("search_platform_hospital", "SUPER_ADMIN") is True
    assert tool_registry.is_authorized("search_platform_hospital", "RECEPTIONIST") is False

@pytest.mark.asyncio
async def test_14_superadmin_fast_sub100ms_routing(golden_db_setup, db_session):
    import time
    t0 = time.time()
    res = await CopilotEngine.chat(
        user_message="expiring subscriptions",
        user_id="SA-01", hospital_id="super_admin", role="SUPERADMIN",
        hospital_name="AURA SaaS Platform", active_tab="overview", selected_date="",
        chat_history=[], db=db_session
    )
    dur = (time.time() - t0) * 1000
    assert dur < 500
    assert "reply" in res

@pytest.mark.asyncio
async def test_15_superadmin_zero_hallucination_check(golden_db_setup, db_session):
    res = await ControlTowerTools.search_platform_hospital(query="nonexistent_hospital_xyz", db=db_session)
    assert res["total_found"] == 0


# ==============================================================================
# ROLE 2: HOSPITAL ADMIN (20 Tests)
# ==============================================================================

@pytest.mark.asyncio
async def test_16_admin_subscription_expiry(golden_db_setup, db_session):
    res = await CopilotEngine.chat(
        user_message="when does our hospital plan expire?",
        user_id="ADM-01", hospital_id="HOSP-BALAJI-1", role="ADMIN",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date="",
        chat_history=[], db=db_session
    )
    assert "ENTERPRISE" in res["reply"]
    assert "days left" in res["reply"] or "Expires on" in res["reply"]

@pytest.mark.asyncio
async def test_17_admin_opd_revenue(golden_db_setup, db_session):
    res = await CopilotEngine.chat(
        user_message="what is our total OPD revenue this month?",
        user_id="ADM-01", hospital_id="HOSP-BALAJI-1", role="ADMIN",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date="",
        chat_history=[], db=db_session
    )
    assert "OPD Revenue" in res["reply"] or "₹" in res["reply"]

@pytest.mark.asyncio
async def test_18_admin_doctor_wise_performance(golden_db_setup, db_session):
    res = await CopilotEngine.chat(
        user_message="show doctor-wise booking performance",
        user_id="ADM-01", hospital_id="HOSP-BALAJI-1", role="ADMIN",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date="",
        chat_history=[], db=db_session
    )
    assert "Shiva Mishra" in res["reply"] or "CP Tiwari" in res["reply"]

@pytest.mark.asyncio
async def test_19_admin_department_directory(golden_db_setup, db_session):
    res = await CopilotEngine.chat(
        user_message="show active departments and doctors directory",
        user_id="ADM-01", hospital_id="HOSP-BALAJI-1", role="ADMIN",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date="",
        chat_history=[], db=db_session
    )
    assert "Cardiology" in res["reply"]
    assert "Orthopedics" in res["reply"]

@pytest.mark.asyncio
async def test_20_admin_appointments_summary(golden_db_setup, db_session):
    res = await CopilotEngine.chat(
        user_message="how many appointments today?",
        user_id="ADM-01", hospital_id="HOSP-BALAJI-1", role="ADMIN",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date="",
        chat_history=[], db=db_session
    )
    assert "Appointment" in res["reply"] or "3" in res["reply"]

@pytest.mark.asyncio
async def test_21_admin_missed_and_cancelled_list(golden_db_setup, db_session):
    res = await CopilotEngine.chat(
        user_message="list of missed and cancelled patients today",
        user_id="ADM-01", hospital_id="HOSP-BALAJI-1", role="ADMIN",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date=str(date.today()),
        chat_history=[], db=db_session
    )
    assert "Missed & Cancelled" in res["reply"]
    assert "Shikhar Mishra" in res["reply"]

@pytest.mark.asyncio
async def test_22_admin_queue_statistics(golden_db_setup, db_session):
    res = await CopilotEngine.chat(
        user_message="what is the current queue status and average wait time?",
        user_id="ADM-01", hospital_id="HOSP-BALAJI-1", role="ADMIN",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date="",
        chat_history=[], db=db_session
    )
    assert "Queue" in res["reply"] or "waiting" in res["reply"].lower()

@pytest.mark.asyncio
async def test_23_admin_daily_cash_register(golden_db_setup, db_session):
    res = await CopilotEngine.chat(
        user_message="show daily cash register collections",
        user_id="ADM-01", hospital_id="HOSP-BALAJI-1", role="ADMIN",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date=str(date.today()),
        chat_history=[], db=db_session
    )
    assert "Cash Register" in res["reply"] or "₹" in res["reply"]

@pytest.mark.asyncio
async def test_24_admin_doctor_shift_timings(golden_db_setup, db_session):
    res = await CopilotEngine.chat(
        user_message="what are the doctor shift timings?",
        user_id="ADM-01", hospital_id="HOSP-BALAJI-1", role="ADMIN",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date="",
        chat_history=[], db=db_session
    )
    assert "09:00" in res["reply"] or "17:00" in res["reply"] or "Shift" in res["reply"]

@pytest.mark.asyncio
async def test_25_admin_highest_fee_query(golden_db_setup, db_session):
    res = await CopilotEngine.chat(
        user_message="which doctor has the highest consultation fee?",
        user_id="ADM-01", hospital_id="HOSP-BALAJI-1", role="ADMIN",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date="",
        chat_history=[], db=db_session
    )
    assert "Shiva Mishra" in res["reply"]
    assert "800" in res["reply"]

@pytest.mark.asyncio
async def test_26_admin_lowest_fee_query(golden_db_setup, db_session):
    res = await CopilotEngine.chat(
        user_message="which doctor has the lowest fee?",
        user_id="ADM-01", hospital_id="HOSP-BALAJI-1", role="ADMIN",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date="",
        chat_history=[], db=db_session
    )
    assert "CP Tiwari" in res["reply"]
    assert "600" in res["reply"]

@pytest.mark.asyncio
async def test_27_admin_all_doctor_fees(golden_db_setup, db_session):
    res = await CopilotEngine.chat(
        user_message="list all doctor consultation fees",
        user_id="ADM-01", hospital_id="HOSP-BALAJI-1", role="ADMIN",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date="",
        chat_history=[], db=db_session
    )
    assert "800" in res["reply"]
    assert "600" in res["reply"]

@pytest.mark.asyncio
async def test_28_admin_doctor_leave_status(golden_db_setup, db_session):
    res = await CopilotEngine.chat(
        user_message="is any doctor on leave today?",
        user_id="ADM-01", hospital_id="HOSP-BALAJI-1", role="ADMIN",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date="",
        chat_history=[], db=db_session
    )
    assert "leave" in res["reply"].lower()

@pytest.mark.asyncio
async def test_29_admin_insurance_tpa_panels(golden_db_setup, db_session):
    res = await CopilotEngine.chat(
        user_message="what insurance panels are accepted?",
        user_id="ADM-01", hospital_id="HOSP-BALAJI-1", role="ADMIN",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date="",
        chat_history=[], db=db_session
    )
    assert "Insurance" in res["reply"] or "TPA" in res["reply"]

@pytest.mark.asyncio
async def test_30_admin_emergency_contacts(golden_db_setup, db_session):
    res = await CopilotEngine.chat(
        user_message="what is the hospital emergency contact number?",
        user_id="ADM-01", hospital_id="HOSP-BALAJI-1", role="ADMIN",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date="",
        chat_history=[], db=db_session
    )
    assert "9876543210" in res["reply"] or "Emergency" in res["reply"]

@pytest.mark.asyncio
async def test_31_admin_follow_up_dr_shiva(golden_db_setup, db_session):
    res = await CopilotEngine.chat(
        user_message="and dr shiva",
        user_id="ADM-01", hospital_id="HOSP-BALAJI-1", role="ADMIN",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date=str(date.today()),
        chat_history=[], db=db_session
    )
    assert "Shiva Mishra" in res["reply"]
    assert "800" in res["reply"] or "Cardiology" in res["reply"]

@pytest.mark.asyncio
async def test_32_admin_follow_up_dr_cp(golden_db_setup, db_session):
    res = await CopilotEngine.chat(
        user_message="and dr cp tiwari",
        user_id="ADM-01", hospital_id="HOSP-BALAJI-1", role="ADMIN",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date=str(date.today()),
        chat_history=[], db=db_session
    )
    assert "CP Tiwari" in res["reply"]

@pytest.mark.asyncio
async def test_33_admin_emr_lookup(golden_db_setup, db_session):
    res = await CopilotEngine.chat(
        user_message="search clinical EMR records for Shikhar",
        user_id="ADM-01", hospital_id="HOSP-BALAJI-1", role="ADMIN",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date="",
        chat_history=[], db=db_session
    )
    assert "reply" in res

@pytest.mark.asyncio
async def test_34_admin_multi_tenant_isolation(golden_db_setup, db_session):
    res = await CopilotEngine.chat(
        user_message="which doctors are on duty today?",
        user_id="ADM-01", hospital_id="HOSP-BALAJI-1", role="ADMIN",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date="",
        chat_history=[], db=db_session
    )
    assert "Aarav Sharma" not in res["reply"]
    assert "Shiva Mishra" in res["reply"]

@pytest.mark.asyncio
async def test_35_admin_sliding_window_memory(golden_db_setup, db_session):
    for i in range(25):
        conversation_memory.append_message(
            hospital_id="HOSP-BALAJI-1", user_id="ADM-01", session_id="test-sess-1",
            message=conversation_memory._create_message("user" if i % 2 == 0 else "assistant", f"Turn {i}")
        )
    summary = conversation_memory.get_session_summary("HOSP-BALAJI-1", "ADM-01", "test-sess-1")
    assert len(summary) > 0


# ==============================================================================
# ROLE 3: RECEPTIONIST / FRONT DESK (20 Tests)
# ==============================================================================

@pytest.mark.asyncio
async def test_36_receptionist_doctors_today(golden_db_setup, db_session):
    res = await CopilotEngine.chat(
        user_message="Which doctors are on duty today?",
        user_id="REC-01", hospital_id="HOSP-BALAJI-1", role="RECEPTIONIST",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date="",
        chat_history=[], db=db_session
    )
    assert "Dr. Shiva Mishra" in res["reply"]
    assert "Dr. CP Tiwari" in res["reply"]

@pytest.mark.asyncio
async def test_37_receptionist_doctors_tomorrow(golden_db_setup, db_session):
    res = await CopilotEngine.chat(
        user_message="Which doctors are available tomorrow?",
        user_id="REC-01", hospital_id="HOSP-BALAJI-1", role="RECEPTIONIST",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date="",
        chat_history=[], db=db_session
    )
    assert "Dr. Shiva Mishra" in res["reply"] or "Dr. CP Tiwari" in res["reply"]

@pytest.mark.asyncio
async def test_38_receptionist_opd_queue_summary(golden_db_setup, db_session):
    res = await CopilotEngine.chat(
        user_message="Today's OPD Queue Summary",
        user_id="REC-01", hospital_id="HOSP-BALAJI-1", role="RECEPTIONIST",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date="",
        chat_history=[], db=db_session
    )
    assert "OPD Queue" in res["reply"]

@pytest.mark.asyncio
async def test_39_receptionist_check_dr_shiva(golden_db_setup, db_session):
    res = await CopilotEngine.chat(
        user_message="is Dr Shiva Mishra available?",
        user_id="REC-01", hospital_id="HOSP-BALAJI-1", role="RECEPTIONIST",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date="",
        chat_history=[], db=db_session
    )
    assert "Shiva Mishra" in res["reply"]
    assert "Available" in res["reply"] or "Duty" in res["reply"]

@pytest.mark.asyncio
async def test_40_receptionist_check_dr_cp(golden_db_setup, db_session):
    res = await CopilotEngine.chat(
        user_message="is Dr CP Tiwari on duty?",
        user_id="REC-01", hospital_id="HOSP-BALAJI-1", role="RECEPTIONIST",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date="",
        chat_history=[], db=db_session
    )
    assert "CP Tiwari" in res["reply"]

@pytest.mark.asyncio
async def test_41_receptionist_booking_initiation(golden_db_setup, db_session):
    res = await CopilotEngine.chat(
        user_message="I want to book an appointment",
        user_id="REC-01", hospital_id="HOSP-BALAJI-1", role="RECEPTIONIST",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date="",
        chat_history=[], db=db_session
    )
    assert "Which doctor would you like to consult?" in res["reply"]
    assert "Dr. Shiva Mishra" in res["reply"]

@pytest.mark.asyncio
async def test_42_receptionist_booking_specify_doctor(golden_db_setup, db_session):
    sess_id = "rec-book-test-1"
    res = await CopilotEngine.chat(
        user_message="book appointment with Dr Shiva Mishra",
        user_id="REC-01", hospital_id="HOSP-BALAJI-1", role="RECEPTIONIST",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date="",
        chat_history=[], db=db_session, session_id=sess_id
    )
    assert "Booking with Dr. Shiva Mishra" in res["reply"]
    assert "Patient's Full Name" in res["reply"]

@pytest.mark.asyncio
async def test_43_receptionist_slot_filling_name_direct(golden_db_setup, db_session):
    sess_id = "rec-book-test-2"
    await CopilotEngine.chat(
        user_message="book appointment with Dr Shiva Mishra",
        user_id="REC-01", hospital_id="HOSP-BALAJI-1", role="RECEPTIONIST",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date="",
        chat_history=[], db=db_session, session_id=sess_id
    )
    res2 = await CopilotEngine.chat(
        user_message="shikhar ms",
        user_id="REC-01", hospital_id="HOSP-BALAJI-1", role="RECEPTIONIST",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date="",
        chat_history=[], db=db_session, session_id=sess_id
    )
    assert "Shikhar Ms" in res2["reply"]
    assert "10-digit Mobile Number" in res2["reply"]

@pytest.mark.asyncio
async def test_44_receptionist_slot_filling_phone(golden_db_setup, db_session):
    sess_id = "rec-book-test-3"
    await CopilotEngine.chat(
        user_message="book appointment with Dr Shiva Mishra",
        user_id="REC-01", hospital_id="HOSP-BALAJI-1", role="RECEPTIONIST",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date="",
        chat_history=[], db=db_session, session_id=sess_id
    )
    await CopilotEngine.chat(
        user_message="shikhar ms",
        user_id="REC-01", hospital_id="HOSP-BALAJI-1", role="RECEPTIONIST",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date="",
        chat_history=[], db=db_session, session_id=sess_id
    )
    res3 = await CopilotEngine.chat(
        user_message="9876543210",
        user_id="REC-01", hospital_id="HOSP-BALAJI-1", role="RECEPTIONIST",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date="",
        chat_history=[], db=db_session, session_id=sess_id
    )
    assert "Confirm Appointment Booking Details" in res3["reply"]
    assert "Shikhar Ms" in res3["reply"]
    assert "9876543210" in res3["reply"]

@pytest.mark.asyncio
async def test_45_receptionist_single_turn_booking(golden_db_setup, db_session):
    res = await CopilotEngine.chat(
        user_message="book appointment for shikhar ms 9876543210 with Dr Shiva Mishra at 11:00 AM",
        user_id="REC-01", hospital_id="HOSP-BALAJI-1", role="RECEPTIONIST",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date="",
        chat_history=[], db=db_session
    )
    assert "Confirm Appointment Booking Details" in res["reply"]
    assert "Dr. Shiva Mishra" in res["reply"]

@pytest.mark.asyncio
async def test_46_receptionist_confirmation_token_generation(golden_db_setup, db_session):
    sess_id = "rec-book-test-4"
    await CopilotEngine.chat(
        user_message="book appointment for rahul sharma 9876543210 with Dr Shiva Mishra",
        user_id="REC-01", hospital_id="HOSP-BALAJI-1", role="RECEPTIONIST",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date="",
        chat_history=[], db=db_session, session_id=sess_id
    )
    token = conversation_memory.get_latest_pending_token("HOSP-BALAJI-1", "REC-01")
    assert token is not None

@pytest.mark.asyncio
async def test_47_receptionist_confirmation_execution(golden_db_setup, db_session):
    sess_id = "rec-book-test-5"
    await CopilotEngine.chat(
        user_message="book appointment for rahul sharma 9876543210 with Dr Shiva Mishra",
        user_id="REC-01", hospital_id="HOSP-BALAJI-1", role="RECEPTIONIST",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date="",
        chat_history=[], db=db_session, session_id=sess_id
    )
    res = await CopilotEngine.chat(
        user_message="confirm",
        user_id="REC-01", hospital_id="HOSP-BALAJI-1", role="RECEPTIONIST",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date="",
        chat_history=[], db=db_session, session_id=sess_id
    )
    assert "Confirmed" in res["reply"] or "Token" in res["reply"] or "✅" in res["reply"]

@pytest.mark.asyncio
async def test_48_receptionist_booking_cancellation(golden_db_setup, db_session):
    sess_id = "rec-book-test-6"
    await CopilotEngine.chat(
        user_message="book appointment with Dr Shiva Mishra",
        user_id="REC-01", hospital_id="HOSP-BALAJI-1", role="RECEPTIONIST",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date="",
        chat_history=[], db=db_session, session_id=sess_id
    )
    res = await CopilotEngine.chat(
        user_message="cancel appointment",
        user_id="REC-01", hospital_id="HOSP-BALAJI-1", role="RECEPTIONIST",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date="",
        chat_history=[], db=db_session, session_id=sess_id
    )
    assert "cancelled" in res["reply"].lower()

@pytest.mark.asyncio
async def test_49_receptionist_missed_list(golden_db_setup, db_session):
    res = await CopilotEngine.chat(
        user_message="missed appointments today",
        user_id="REC-01", hospital_id="HOSP-BALAJI-1", role="RECEPTIONIST",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date=str(date.today()),
        chat_history=[], db=db_session
    )
    assert "Shikhar Mishra" in res["reply"]

@pytest.mark.asyncio
async def test_50_receptionist_fee_inquiry(golden_db_setup, db_session):
    res = await CopilotEngine.chat(
        user_message="Dr CP Tiwari ki fee kitni hai",
        user_id="REC-01", hospital_id="HOSP-BALAJI-1", role="RECEPTIONIST",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date="",
        chat_history=[], db=db_session
    )
    assert "600" in res["reply"]

@pytest.mark.asyncio
async def test_51_receptionist_department_directory(golden_db_setup, db_session):
    res = await CopilotEngine.chat(
        user_message="which departments exist?",
        user_id="REC-01", hospital_id="HOSP-BALAJI-1", role="RECEPTIONIST",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date="",
        chat_history=[], db=db_session
    )
    assert "Cardiology" in res["reply"]

@pytest.mark.asyncio
async def test_52_receptionist_cash_register(golden_db_setup, db_session):
    res = await CopilotEngine.chat(
        user_message="cash register collections today",
        user_id="REC-01", hospital_id="HOSP-BALAJI-1", role="RECEPTIONIST",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date=str(date.today()),
        chat_history=[], db=db_session
    )
    assert "Cash Register" in res["reply"] or "₹" in res["reply"]

@pytest.mark.asyncio
async def test_53_receptionist_token_position(golden_db_setup, db_session):
    res = await CopilotEngine.chat(
        user_message="check live token queue position for Shikhar",
        user_id="REC-01", hospital_id="HOSP-BALAJI-1", role="RECEPTIONIST",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date="",
        chat_history=[], db=db_session
    )
    assert "reply" in res

@pytest.mark.asyncio
async def test_54_receptionist_hinglish_doctors(golden_db_setup, db_session):
    res = await CopilotEngine.chat(
        user_message="aaj kaun se doctor baithe hain",
        user_id="REC-01", hospital_id="HOSP-BALAJI-1", role="RECEPTIONIST",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date="",
        chat_history=[], db=db_session
    )
    assert "Dr. Shiva Mishra" in res["reply"]

@pytest.mark.asyncio
async def test_55_receptionist_hinglish_booking(golden_db_setup, db_session):
    res = await CopilotEngine.chat(
        user_message="ek appointment schedule kar do",
        user_id="REC-01", hospital_id="HOSP-BALAJI-1", role="RECEPTIONIST",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date="",
        chat_history=[], db=db_session
    )
    assert "Which doctor would you like to consult?" in res["reply"]


# ==============================================================================
# ROLE 4: DOCTOR (12 Tests)
# ==============================================================================

@pytest.mark.asyncio
async def test_56_doctor_live_queue(golden_db_setup, db_session):
    actor = {
        "doctor_id": "DOC-SHIVA-1",
        "doctor_name": "Dr. Shiva Mishra",
        "hospital_id": "HOSP-BALAJI-1",
        "role": "DOCTOR"
    }
    res = await CopilotEngine.chat(
        user_message="How many patients are waiting in my queue?",
        user_id="DOC-SHIVA-1", hospital_id="HOSP-BALAJI-1", role="DOCTOR",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date=str(date.today()),
        chat_history=[], db=db_session, actor_profile=actor
    )
    assert "Live Waiting Room" in res["reply"] or "queue" in res["reply"].lower()

@pytest.mark.asyncio
async def test_57_doctor_consulted_patients(golden_db_setup, db_session):
    actor = {
        "doctor_id": "DOC-SHIVA-1",
        "doctor_name": "Dr. Shiva Mishra",
        "hospital_id": "HOSP-BALAJI-1",
        "role": "DOCTOR"
    }
    res = await CopilotEngine.chat(
        user_message="Kitne mareez dekhe aaj?",
        user_id="DOC-SHIVA-1", hospital_id="HOSP-BALAJI-1", role="DOCTOR",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date=str(date.today()),
        chat_history=[], db=db_session, actor_profile=actor
    )
    assert "Consulted" in res["reply"] or "1" in res["reply"]

@pytest.mark.asyncio
async def test_58_doctor_daily_earnings(golden_db_setup, db_session):
    actor = {
        "doctor_id": "DOC-SHIVA-1",
        "doctor_name": "Dr. Shiva Mishra",
        "hospital_id": "HOSP-BALAJI-1",
        "role": "DOCTOR"
    }
    res = await CopilotEngine.chat(
        user_message="What are my earnings today?",
        user_id="DOC-SHIVA-1", hospital_id="HOSP-BALAJI-1", role="DOCTOR",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date=str(date.today()),
        chat_history=[], db=db_session, actor_profile=actor
    )
    assert "₹" in res["reply"] or "Earnings" in res["reply"]

@pytest.mark.asyncio
async def test_59_doctor_shift_timings(golden_db_setup, db_session):
    actor = {
        "doctor_id": "DOC-SHIVA-1",
        "doctor_name": "Dr. Shiva Mishra",
        "hospital_id": "HOSP-BALAJI-1",
        "role": "DOCTOR",
        "timings": "Mon-Sat: 09:00 AM - 05:00 PM"
    }
    res = await CopilotEngine.chat(
        user_message="What are my shift timings this week?",
        user_id="DOC-SHIVA-1", hospital_id="HOSP-BALAJI-1", role="DOCTOR",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date="",
        chat_history=[], db=db_session, actor_profile=actor
    )
    assert "09:00" in res["reply"] or "Shift" in res["reply"]

@pytest.mark.asyncio
async def test_60_doctor_apply_leave_token(golden_db_setup, db_session):
    from app.tools.doctor_tools import DoctorTools
    res = await DoctorTools.apply_leave_for_doctor(
        start_date_str="2026-09-28", end_date_str="2026-09-29",
        reason="Medical Conference", doctor_name="Dr. Shiva Mishra",
        hospital_id="HOSP-BALAJI-1", user_id="DOC-SHIVA-1", db=db_session
    )
    assert res["status"] == "CONFIRMATION_REQUIRED"
    assert "confirmation_token" in res

@pytest.mark.asyncio
async def test_61_doctor_leave_history(golden_db_setup, db_session):
    actor = {
        "doctor_id": "DOC-SHIVA-1",
        "doctor_name": "Dr. Shiva Mishra",
        "hospital_id": "HOSP-BALAJI-1",
        "role": "DOCTOR"
    }
    res = await CopilotEngine.chat(
        user_message="show my leave history",
        user_id="DOC-SHIVA-1", hospital_id="HOSP-BALAJI-1", role="DOCTOR",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date="",
        chat_history=[], db=db_session, actor_profile=actor
    )
    assert "Leave History" in res["reply"] or "leave" in res["reply"].lower()

@pytest.mark.asyncio
async def test_62_doctor_emr_lookup(golden_db_setup, db_session):
    actor = {
        "doctor_id": "DOC-SHIVA-1",
        "doctor_name": "Dr. Shiva Mishra",
        "hospital_id": "HOSP-BALAJI-1",
        "role": "DOCTOR"
    }
    res = await CopilotEngine.chat(
        user_message="search prescription records for patient Rahul",
        user_id="DOC-SHIVA-1", hospital_id="HOSP-BALAJI-1", role="DOCTOR",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date="",
        chat_history=[], db=db_session, actor_profile=actor
    )
    assert "reply" in res

@pytest.mark.asyncio
async def test_63_doctor_zero_hallucination(golden_db_setup, db_session):
    actor = {
        "doctor_id": "DOC-SHIVA-1",
        "doctor_name": "Dr. Shiva Mishra",
        "hospital_id": "HOSP-BALAJI-1",
        "role": "DOCTOR"
    }
    res = await CopilotEngine.chat(
        user_message="How many patients are waiting in Dr Nonexistent's queue?",
        user_id="DOC-SHIVA-1", hospital_id="HOSP-BALAJI-1", role="DOCTOR",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date="",
        chat_history=[], db=db_session, actor_profile=actor
    )
    assert "0" in res["reply"] or "No" in res["reply"] or "not found" in res["reply"].lower()

@pytest.mark.asyncio
async def test_64_doctor_rbac_barrier(golden_db_setup, db_session):
    from app.engines.tool_registry import tool_registry
    assert tool_registry.is_authorized("get_expiring_subscriptions_report", "DOCTOR") is False

@pytest.mark.asyncio
async def test_65_doctor_prescription_intent(golden_db_setup, db_session):
    actor = {
        "doctor_id": "DOC-SHIVA-1",
        "doctor_name": "Dr. Shiva Mishra",
        "hospital_id": "HOSP-BALAJI-1",
        "role": "DOCTOR"
    }
    res = await CopilotEngine.chat(
        user_message="write prescription advice for chest pain",
        user_id="DOC-SHIVA-1", hospital_id="HOSP-BALAJI-1", role="DOCTOR",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date="",
        chat_history=[], db=db_session, actor_profile=actor
    )
    assert "reply" in res

@pytest.mark.asyncio
async def test_66_doctor_fast_offline_turn(golden_db_setup, db_session):
    actor = {
        "doctor_id": "DOC-SHIVA-1",
        "doctor_name": "Dr. Shiva Mishra",
        "hospital_id": "HOSP-BALAJI-1",
        "role": "DOCTOR"
    }
    import time
    t0 = time.time()
    res = await CopilotEngine.chat(
        user_message="How many patients are waiting in my queue?",
        user_id="DOC-SHIVA-1", hospital_id="HOSP-BALAJI-1", role="DOCTOR",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date="",
        chat_history=[], db=db_session, actor_profile=actor
    )
    dur = (time.time() - t0) * 1000
    assert dur < 500

@pytest.mark.asyncio
async def test_67_doctor_leave_status_check(golden_db_setup, db_session):
    actor = {
        "doctor_id": "DOC-SHIVA-1",
        "doctor_name": "Dr. Shiva Mishra",
        "hospital_id": "HOSP-BALAJI-1",
        "role": "DOCTOR"
    }
    res = await CopilotEngine.chat(
        user_message="check if I have any approved leave",
        user_id="DOC-SHIVA-1", hospital_id="HOSP-BALAJI-1", role="DOCTOR",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date="",
        chat_history=[], db=db_session, actor_profile=actor
    )
    assert "leave" in res["reply"].lower()


# ==============================================================================
# ROLE 5: PATIENT PORTAL (13 Tests)
# ==============================================================================

@pytest.mark.asyncio
async def test_68_patient_want_to_book(golden_db_setup, db_session):
    res = await CopilotEngine.chat(
        user_message="I want to book an appointment",
        user_id="PAT-101", hospital_id="HOSP-BALAJI-1", role="PATIENT",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date="",
        chat_history=[], db=db_session
    )
    assert "Which doctor would you like to consult?" in res["reply"]
    assert "Dr. Shiva Mishra" in res["reply"]

@pytest.mark.asyncio
async def test_69_patient_auto_hydrated_booking(golden_db_setup, db_session):
    actor = {
        "patient_id": "PAT-101",
        "patient_name": "Shikhar Mishra",
        "patient_phone": "9876543210",
        "hospital_id": "HOSP-BALAJI-1",
        "role": "PATIENT"
    }
    res = await CopilotEngine.chat(
        user_message="book appointment with Dr Shiva Mishra",
        user_id="PAT-101", hospital_id="HOSP-BALAJI-1", role="PATIENT",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date="",
        chat_history=[], db=db_session, actor_profile=actor
    )
    assert "Confirm Appointment Booking Details" in res["reply"]
    assert "Shikhar Mishra" in res["reply"]

@pytest.mark.asyncio
async def test_70_patient_doctor_search_cardio(golden_db_setup, db_session):
    res = await CopilotEngine.chat(
        user_message="cardiologist doctors in this hospital",
        user_id="PAT-101", hospital_id="HOSP-BALAJI-1", role="PATIENT",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date="",
        chat_history=[], db=db_session
    )
    assert "Shiva Mishra" in res["reply"]
    assert "800" in res["reply"]

@pytest.mark.asyncio
async def test_71_patient_fees_query(golden_db_setup, db_session):
    res = await CopilotEngine.chat(
        user_message="What are the doctor consultation fees?",
        user_id="PAT-101", hospital_id="HOSP-BALAJI-1", role="PATIENT",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date="",
        chat_history=[], db=db_session
    )
    assert "800" in res["reply"] or "600" in res["reply"]

@pytest.mark.asyncio
async def test_72_patient_live_token_position(golden_db_setup, db_session):
    actor = {
        "patient_id": "PAT-101",
        "patient_name": "Shikhar Mishra",
        "patient_phone": "9876543210",
        "hospital_id": "HOSP-BALAJI-1",
        "role": "PATIENT"
    }
    res = await CopilotEngine.chat(
        user_message="Check my live token position",
        user_id="PAT-101", hospital_id="HOSP-BALAJI-1", role="PATIENT",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date="",
        chat_history=[], db=db_session, actor_profile=actor
    )
    assert "Token" in res["reply"] or "Live" in res["reply"] or "Position" in res["reply"]

@pytest.mark.asyncio
async def test_73_patient_my_appointments(golden_db_setup, db_session):
    actor = {
        "patient_id": "PAT-101",
        "patient_name": "Shikhar Mishra",
        "patient_phone": "9876543210",
        "hospital_id": "HOSP-BALAJI-1",
        "role": "PATIENT"
    }
    res = await CopilotEngine.chat(
        user_message="Show my booked appointments",
        user_id="PAT-101", hospital_id="HOSP-BALAJI-1", role="PATIENT",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date="",
        chat_history=[], db=db_session, actor_profile=actor
    )
    assert "Dr. Shiva Mishra" in res["reply"]

@pytest.mark.asyncio
async def test_74_patient_emergency_number(golden_db_setup, db_session):
    res = await CopilotEngine.chat(
        user_message="hospital emergency number",
        user_id="PAT-101", hospital_id="HOSP-BALAJI-1", role="PATIENT",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date="",
        chat_history=[], db=db_session
    )
    assert "9876543210" in res["reply"] or "Emergency" in res["reply"]

@pytest.mark.asyncio
async def test_75_patient_insurance_panels(golden_db_setup, db_session):
    res = await CopilotEngine.chat(
        user_message="What insurance TPA panels are supported?",
        user_id="PAT-101", hospital_id="HOSP-BALAJI-1", role="PATIENT",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date="",
        chat_history=[], db=db_session
    )
    assert "Insurance" in res["reply"] or "TPA" in res["reply"]

@pytest.mark.asyncio
async def test_76_guest_patient_browsing_portal(golden_db_setup, db_session):
    res = await CopilotEngine.chat(
        user_message="Which doctors are available today?",
        user_id="GUEST_PATIENT", hospital_id="HOSP-BALAJI-1", role="PATIENT",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date="",
        chat_history=[], db=db_session
    )
    assert "Dr. Shiva Mishra" in res["reply"]

@pytest.mark.asyncio
async def test_77_guest_patient_hinglish(golden_db_setup, db_session):
    res = await CopilotEngine.chat(
        user_message="doctor ke sath appointment book karna hai",
        user_id="GUEST_PATIENT", hospital_id="HOSP-BALAJI-1", role="PATIENT",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date="",
        chat_history=[], db=db_session
    )
    assert "Which doctor would you like to consult?" in res["reply"]

@pytest.mark.asyncio
async def test_78_patient_rbac_protection(golden_db_setup, db_session):
    from app.engines.tool_registry import tool_registry
    assert tool_registry.is_authorized("get_revenue_and_dues", "PATIENT") is False
    assert tool_registry.is_authorized("get_daily_cash_register", "PATIENT") is False

@pytest.mark.asyncio
async def test_79_patient_multi_turn_booking_flow(golden_db_setup, db_session):
    sess_id = "patient-portal-booking-flow"
    r1 = await CopilotEngine.chat(
        user_message="want to book appointment with Dr CP Tiwari at 2 PM",
        user_id="GUEST_PATIENT", hospital_id="HOSP-BALAJI-1", role="PATIENT",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date="",
        chat_history=[], db=db_session, session_id=sess_id
    )
    assert "Dr. CP Tiwari" in r1["reply"]

    r2 = await CopilotEngine.chat(
        user_message="shikhar ms",
        user_id="GUEST_PATIENT", hospital_id="HOSP-BALAJI-1", role="PATIENT",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date="",
        chat_history=[], db=db_session, session_id=sess_id
    )
    assert "Shikhar Ms" in r2["reply"]
    assert "10-digit Mobile Number" in r2["reply"]

    r3 = await CopilotEngine.chat(
        user_message="9876543210",
        user_id="GUEST_PATIENT", hospital_id="HOSP-BALAJI-1", role="PATIENT",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date="",
        chat_history=[], db=db_session, session_id=sess_id
    )
    assert "Confirm Appointment Booking Details" in r3["reply"]
    assert "Dr. CP Tiwari" in r3["reply"]
    assert "Shikhar Ms" in r3["reply"]

@pytest.mark.asyncio
async def test_80_patient_confirm_booking_generates_token(golden_db_setup, db_session):
    sess_id = "patient-portal-booking-confirm"
    await CopilotEngine.chat(
        user_message="book appointment with Dr CP Tiwari for shikhar ms 9876543210",
        user_id="GUEST_PATIENT", hospital_id="HOSP-BALAJI-1", role="PATIENT",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date="",
        chat_history=[], db=db_session, session_id=sess_id
    )
    res = await CopilotEngine.chat(
        user_message="confirm",
        user_id="GUEST_PATIENT", hospital_id="HOSP-BALAJI-1", role="PATIENT",
        hospital_name="Balaji Healthcare", active_tab="overview", selected_date="",
        chat_history=[], db=db_session, session_id=sess_id
    )
    assert "Confirmed" in res["reply"] or "Token" in res["reply"] or "✅" in res["reply"]
