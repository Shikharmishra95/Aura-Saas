import pytest
import asyncio
import sys
import os
import random
from datetime import datetime, timedelta

# Force UTF-8 output
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

# Set root path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database.session import async_session_factory
from app.tools import (
    search_doctors, get_doctor_details, check_doctor_availability, get_available_slots,
    book_appointment, get_my_appointments, cancel_appointment, reschedule_appointment,
    get_patient_details, get_hospital_information,
    get_my_prescriptions, get_my_live_token_position, get_insurance_tpa_panels,
    save_consultation_notes, generate_appointment_payment_link,
    get_all_opd_queues, approve_or_reject_doctor_leave, update_doctor_schedule,
    get_expiring_subscriptions_report, extend_hospital_subscription, toggle_hospital_ai_voice_service
)
from app.engines.copilot_engine import copilot_engine
from app.engines.tool_registry import tool_registry

async def run_complete_suite():
    print("\n" + "="*80)
    print("AURA COMPLETE 5-PORTAL HMS AI TOOLS VERIFICATION SUITE")
    print("="*80)

    async with async_session_factory() as db:
        test_hospital_id = "HOSP-RAOH-4893"
        other_hospital_id = "HOSP-APOL-7457"
        
        # -------------------------------------------------------------
        # 1. TEST PATIENT PORTAL: get_insurance_tpa_panels
        # -------------------------------------------------------------
        print("\n[TEST 1] get_insurance_tpa_panels (Patient / All)")
        ins_res = await get_insurance_tpa_panels(hospital_id=test_hospital_id, db=db)
        print(f"Total Insurance Panels Found: {ins_res.get('total_count')}")
        assert "insurance_panels" in ins_res
        print("  [PASS] get_insurance_tpa_panels verified.")

        # -------------------------------------------------------------
        # 2. CREATE A FRESH APPOINTMENT FOR WORKFLOW TESTS
        # -------------------------------------------------------------
        print("\n[SETUP] Creating test booking for clinical & payment workflow...")
        today_date = datetime.now().strftime("%Y-%m-%d")
        test_phone = f"987{random.randint(1000000, 9999999)}"
        test_name = "Vikram Sharma"
        
        # Get doctor and live slot
        docs_res = await search_doctors(hospital_id=test_hospital_id, db=db)
        doc = docs_res["doctors"][0]
        
        slots_res = await get_available_slots(hospital_id=test_hospital_id, doctor_id=doc["doctor_id"], date_str=today_date, db=db)
        chosen_slot = slots_res.get("available_slots", ["04:00 PM"])[0] if slots_res.get("available_slots") else "05:00 PM"
        
        booking = await book_appointment(
            hospital_id=test_hospital_id,
            user_id="usr_patient_vikram",
            role="PATIENT",
            doctor_name_or_dept=doc["name"],
            date_str=today_date,
            time_slot=chosen_slot,
            patient_name=test_name,
            phone=test_phone,
            reason="Chest Pain & Routine Checkup",
            db=db
        )
        assert booking.get("success") is True
        appt_id = booking.get("appointment_id")
        print(f"  Created Appointment ID: {appt_id} for Doctor: {doc['name']}")

        # -------------------------------------------------------------
        # 3. TEST PATIENT PORTAL: get_my_live_token_position
        # -------------------------------------------------------------
        print("\n[TEST 2] get_my_live_token_position (Patient Live Queue)")
        queue_pos = await get_my_live_token_position(
            hospital_id=test_hospital_id,
            user_id="usr_patient_vikram",
            role="PATIENT",
            appointment_id_or_phone=appt_id,
            db=db
        )
        print(f"Token Status: {queue_pos.get('status')} | Patients Ahead: {queue_pos.get('patients_ahead')} | Est Wait: {queue_pos.get('estimated_wait_minutes')} min")
        assert queue_pos.get("has_active_appointment") is True
        print("  [PASS] get_my_live_token_position verified.")

        # -------------------------------------------------------------
        # 4. TEST PAYMENT: generate_appointment_payment_link
        # -------------------------------------------------------------
        print("\n[TEST 3] generate_appointment_payment_link (Payment Tools)")
        pay_link = await generate_appointment_payment_link(
            hospital_id=test_hospital_id,
            user_id="usr_patient_vikram",
            role="PATIENT",
            appointment_id=appt_id,
            db=db
        )
        print(f"Payment Link Generated: {pay_link.get('payment_link_url')} | Amount: INR {pay_link.get('amount')}")
        assert pay_link.get("success") is True
        assert "http" in pay_link.get("payment_link_url")
        print("  [PASS] generate_appointment_payment_link verified.")

        # -------------------------------------------------------------
        # 5. TEST DOCTOR PORTAL: save_consultation_notes
        # -------------------------------------------------------------
        print("\n[TEST 4] save_consultation_notes (Doctor Clinical Tool)")
        notes_res = await save_consultation_notes(
            hospital_id=test_hospital_id,
            user_id=doc["doctor_id"],
            role="DOCTOR",
            appointment_id=appt_id,
            clinical_notes="Patient presents with mild chest discomfort. ECG normal. BP 120/80.",
            prescription="Tab Ecosprin 75mg OD, Tab Atorva 10mg HS",
            follow_up_date_str=(datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d"),
            db=db
        )
        print(f"Save Notes Status: {notes_res.get('success')} | Consultation Status: {notes_res.get('status')}")
        assert notes_res.get("success") is True
        assert notes_res.get("status") == "COMPLETED"
        print("  [PASS] save_consultation_notes verified.")

        # -------------------------------------------------------------
        # 6. TEST PATIENT PORTAL: get_my_prescriptions
        # -------------------------------------------------------------
        print("\n[TEST 5] get_my_prescriptions (Patient Clinical Tool)")
        rx_res = await get_my_prescriptions(
            hospital_id=test_hospital_id,
            user_id="usr_patient_vikram",
            role="PATIENT",
            phone=test_phone,
            db=db
        )
        print(f"Prescriptions Found: {rx_res.get('total_count')}")
        assert rx_res.get("total_count", 0) >= 1
        assert "Ecosprin" in rx_res["prescriptions"][0]["prescription"]
        print("  [PASS] get_my_prescriptions verified.")

        # -------------------------------------------------------------
        # 7. TEST RECEPTIONIST / ADMIN: get_all_opd_queues
        # -------------------------------------------------------------
        print("\n[TEST 6] get_all_opd_queues (Multi-Wing OPD Overview)")
        opd_queues = await get_all_opd_queues(
            hospital_id=test_hospital_id,
            date_str=today_date,
            db=db
        )
        print(f"Total Appointments Today: {opd_queues.get('total_appointments')} | Completed: {opd_queues.get('total_completed')}")
        assert opd_queues.get("total_departments", 0) >= 1
        print("  [PASS] get_all_opd_queues verified.")

        # -------------------------------------------------------------
        # 8. TEST ADMIN PORTAL: update_doctor_schedule (Confirmation Flow)
        # -------------------------------------------------------------
        print("\n[TEST 7] update_doctor_schedule (Admin Shift Timetable Flow)")
        # 8a: Trigger update without token -> returns confirmation required
        sched_prompt = await update_doctor_schedule(
            hospital_id=test_hospital_id,
            user_id="usr_admin_01",
            role="ADMIN",
            doctor_id_or_name=doc["doctor_id"],
            day_of_week=2, # Tuesday
            start_time_str="09:30 AM",
            end_time_str="04:30 PM",
            slot_duration_minutes=25,
            db=db
        )
        assert sched_prompt.get("status") == "CONFIRMATION_REQUIRED"
        sched_token = sched_prompt.get("confirmation_token")
        print(f"Confirmation Token Generated: {sched_token}")

        # 8b: Execute confirmed update
        sched_done = await update_doctor_schedule(
            hospital_id=test_hospital_id,
            user_id="usr_admin_01",
            role="ADMIN",
            doctor_id_or_name=doc["doctor_id"],
            day_of_week=2,
            start_time_str="09:30 AM",
            end_time_str="04:30 PM",
            slot_duration_minutes=25,
            confirmation_token=sched_token,
            db=db
        )
        print(f"Schedule Update Status: {sched_done.get('success')} | Timings: {sched_done.get('start_time')} - {sched_done.get('end_time')}")
        assert sched_done.get("success") is True
        print("  [PASS] update_doctor_schedule with confirmation verified.")

        # -------------------------------------------------------------
        # 9. TEST SUPERADMIN CONTROL TOWER: get_expiring_subscriptions_report
        # -------------------------------------------------------------
        print("\n[TEST 8] get_expiring_subscriptions_report (SuperAdmin Tool)")
        exp_report = await get_expiring_subscriptions_report(
            days_threshold=365,
            db=db
        )
        print(f"Hospitals in Expiration Window: {exp_report.get('total_expiring')}")
        assert "expiring_hospitals" in exp_report
        print("  [PASS] get_expiring_subscriptions_report verified.")

        # -------------------------------------------------------------
        # 10. TEST SUPERADMIN CONTROL TOWER: extend_hospital_subscription
        # -------------------------------------------------------------
        print("\n[TEST 9] extend_hospital_subscription (SuperAdmin Ledger Flow)")
        # 10a: Trigger extension without token
        ext_prompt = await extend_hospital_subscription(
            hospital_id=test_hospital_id,
            duration_days=30,
            plan_name="ENTERPRISE",
            notes="Automated SaaS renewal test",
            user_id="usr_superadmin_01",
            db=db
        )
        assert ext_prompt.get("status") == "CONFIRMATION_REQUIRED"
        ext_token = ext_prompt.get("confirmation_token")
        print(f"Extension Confirmation Token: {ext_token}")

        # 10b: Execute confirmed extension
        ext_done = await extend_hospital_subscription(
            hospital_id=test_hospital_id,
            duration_days=30,
            plan_name="ENTERPRISE",
            notes="Automated SaaS renewal test",
            user_id="usr_superadmin_01",
            confirmation_token=ext_token,
            db=db
        )
        print(f"Extension Status: {ext_done.get('success')} | New Expiry: {ext_done.get('new_expiry_date')}")
        assert ext_done.get("success") is True
        print("  [PASS] extend_hospital_subscription with confirmation verified.")

        # -------------------------------------------------------------
        # 11. TEST SUPERADMIN CONTROL TOWER: toggle_hospital_ai_voice_service
        # -------------------------------------------------------------
        print("\n[TEST 10] toggle_hospital_ai_voice_service (SuperAdmin Voice Toggle)")
        # 11a: Trigger toggle
        voice_prompt = await toggle_hospital_ai_voice_service(
            hospital_id=test_hospital_id,
            enabled=True,
            user_id="usr_superadmin_01",
            db=db
        )
        assert voice_prompt.get("status") == "CONFIRMATION_REQUIRED"
        voice_token = voice_prompt.get("confirmation_token")

        # 11b: Execute confirmed toggle
        voice_done = await toggle_hospital_ai_voice_service(
            hospital_id=test_hospital_id,
            enabled=True,
            user_id="usr_superadmin_01",
            confirmation_token=voice_token,
            db=db
        )
        print(f"Voice Toggle Status: {voice_done.get('success')} | Voice Enabled: {voice_done.get('ai_voice_enabled')}")
        assert voice_done.get("success") is True
        print("  [PASS] toggle_hospital_ai_voice_service verified.")

        # -------------------------------------------------------------
        # 12. TEST ZERO-TRUST RBAC & ROLE HARD FILTERS
        # -------------------------------------------------------------
        print("\n[TEST 11] Zero-Trust RBAC Hard Filters Verification")
        assert tool_registry.is_authorized("get_my_prescriptions", "PATIENT") is True
        assert tool_registry.is_authorized("get_insurance_tpa_panels", "PATIENT") is True
        assert tool_registry.is_authorized("save_consultation_notes", "PATIENT") is False
        assert tool_registry.is_authorized("save_consultation_notes", "DOCTOR") is True
        assert tool_registry.is_authorized("approve_or_reject_doctor_leave", "DOCTOR") is False
        assert tool_registry.is_authorized("approve_or_reject_doctor_leave", "ADMIN") is True
        assert tool_registry.is_authorized("extend_hospital_subscription", "ADMIN") is False
        assert tool_registry.is_authorized("extend_hospital_subscription", "SUPER_ADMIN") is True
        print("  [PASS] Zero-Trust Role Matrix strictly enforced.")

        # -------------------------------------------------------------
        # 13. TEST COPILOT ENGINE NATURAL LANGUAGE MULTILINGUAL INVOCATION
        # -------------------------------------------------------------
        print("\n[TEST 12] CopilotEngine Natural Language Multi-Portal Turns")
        
        # 13a. Patient asking in Hindi about cashless insurance
        res_ins = await copilot_engine.chat(
            user_message="Kya hospital mein cashless insurance panel available hai?",
            user_id="usr_patient_vikram",
            hospital_id=test_hospital_id,
            role="PATIENT",
            hospital_name="Rao Hospital",
            active_tab="Dashboard",
            selected_date=today_date,
            chat_history=[],
            db=db
        )
        print(f"\n[Insurance Query Preview]:\n{res_ins['reply'][:250]}...")
        assert "insurance" in res_ins["reply"].lower() or "cashless" in res_ins["reply"].lower() or "tpa" in res_ins["reply"].lower() or "panel" in res_ins["reply"].lower()

        # 13b. Receptionist asking about all OPD load
        res_opd = await copilot_engine.chat(
            user_message="Sabhi departments ka live queue load aur patient count dikhao",
            user_id="usr_reception_01",
            hospital_id=test_hospital_id,
            role="RECEPTIONIST",
            hospital_name="Rao Hospital",
            active_tab="Queue",
            selected_date=today_date,
            chat_history=[],
            db=db
        )
        print(f"\n[OPD Queues Query Preview]:\n{res_opd['reply'][:250]}...")
        assert "department" in res_opd["reply"].lower() or "queue" in res_opd["reply"].lower() or "opd" in res_opd["reply"].lower()

        print("\n" + "="*80)
        print("ALL 12 TEST SUITE SCENARIOS PASSED SUCCESSFULLY!")
        print("="*80)

if __name__ == "__main__":
    asyncio.run(run_complete_suite())
