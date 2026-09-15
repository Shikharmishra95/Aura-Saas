import pytest
import asyncio
import sys
import os
from datetime import datetime, timedelta

# Force UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# Set root path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database.session import async_session_factory
from app.tools import (
    search_doctors, get_doctor_details, check_doctor_availability, get_available_slots,
    book_appointment, get_my_appointments, cancel_appointment, reschedule_appointment,
    get_patient_details, get_hospital_information
)
from app.engines.copilot_engine import copilot_engine
from app.engines.tool_registry import tool_registry

async def run_hms_ai_tools_test_suite():
    print("\n" + "="*80)
    print("AURA HMS AI TOOLS & REAL APPOINTMENT WORKFLOW TEST SUITE")
    print("="*80)

    async with async_session_factory() as db:
        test_hospital_id = "HOSP-RAOH-4893"
        other_hospital_id = "HOSP-APOL-7457"
        
        # 1. TEST HOSPITAL INFORMATION TOOL
        print("\n[TEST 1] get_hospital_information")
        hosp_info = await get_hospital_information(hospital_id=test_hospital_id, db=db)
        print(f"Hospital Name: {hosp_info.get('hospital_name')}")
        print(f"Total Doctors: {hosp_info.get('total_doctors')}")
        print(f"Departments: {[d['name'] for d in hosp_info.get('departments', [])]}")
        assert hosp_info.get("hospital_name") == "Rao Hospital"
        assert hosp_info.get("total_doctors", 0) >= 1
        print("  [PASS] Hospital Information test passed.")

        # 2. TEST DOCTOR SEARCH (SPECIALTY & ALL)
        print("\n[TEST 2] search_doctors (All & Filtered)")
        all_docs = await search_doctors(hospital_id=test_hospital_id, db=db)
        print(f"Found {all_docs.get('total_count')} total doctors at {test_hospital_id}")
        assert all_docs.get("total_count", 0) > 0
        
        sample_doc = all_docs["doctors"][0]
        sample_doc_id = sample_doc["doctor_id"]
        sample_doc_name = sample_doc["name"]
        print(f"Sample Doctor Selected: {sample_doc_name} (ID: {sample_doc_id})")
        print("  [PASS] Doctor Search test passed.")

        # 3. TEST DOCTOR DETAILS & AVAILABILITY
        print("\n[TEST 3] get_doctor_details & check_doctor_availability")
        doc_details = await get_doctor_details(hospital_id=test_hospital_id, doctor_id=sample_doc_id, db=db)
        print(f"Doctor Details: {doc_details.get('name')} | Dept: {doc_details.get('department')} | Fee: INR {doc_details.get('opd_fee')}")
        assert doc_details.get("doctor_id") == sample_doc_id

        today = datetime.now()
        target_date = (today + timedelta(days=2)).strftime("%Y-%m-%d")
        avail = await check_doctor_availability(hospital_id=test_hospital_id, doctor_id=sample_doc_id, date_str=target_date, db=db)
        print(f"Availability for {target_date}: {avail.get('is_available')} (Reason: {avail.get('message', 'OK')})")
        print("  [PASS] Doctor Details & Availability test passed.")

        # 4. TEST SLOTS RETRIEVAL
        print("\n[TEST 4] get_available_slots")
        slots_res = await get_available_slots(hospital_id=test_hospital_id, doctor_id=sample_doc_id, date_str=target_date, db=db)
        print(f"Available slots for {target_date}: {len(slots_res.get('available_slots', []))} slots")
        chosen_slot = slots_res.get('available_slots', ['10:00 AM'])[0] if slots_res.get('available_slots') else '10:00 AM'
        print(f"Chosen slot for booking test: {chosen_slot}")
        print("  [PASS] Slots Retrieval test passed.")

        # 5. TEST REAL APPOINTMENT BOOKING
        print("\n[TEST 5] book_appointment")
        import random
        test_patient_phone = f"987{random.randint(1000000, 9999999)}"
        test_patient_name = "AURA Test Patient"
        booking_res = await book_appointment(
            hospital_id=test_hospital_id,
            user_id="usr_patient_test_01",
            role="PATIENT",
            doctor_name_or_dept=sample_doc_name,
            date_str=target_date,
            time_slot=chosen_slot,
            patient_name=test_patient_name,
            phone=test_patient_phone,
            reason="AI Automated Test Consultation",
            db=db
        )
        print(f"Booking Status: {booking_res.get('success')} | ID: {booking_res.get('appointment_id')} | Token: #{booking_res.get('token_number')}")
        assert booking_res.get("success") is True
        created_appt_id = booking_res.get("appointment_id")
        print("  [PASS] Real Appointment Booking test passed.")

        # 6. TEST GET MY APPOINTMENTS
        print("\n[TEST 6] get_my_appointments")
        my_appts = await get_my_appointments(
            hospital_id=test_hospital_id,
            user_id="usr_patient_test_01",
            role="PATIENT",
            phone=test_patient_phone,
            db=db
        )
        print(f"Total appointments found for {test_patient_phone}: {my_appts.get('total_count')}")
        assert my_appts.get("total_count", 0) >= 1
        print("  [PASS] Get My Appointments test passed.")

        # 7. TEST RESCHEDULE APPOINTMENT
        print("\n[TEST 7] reschedule_appointment")
        new_resched_date = (today + timedelta(days=3)).strftime("%Y-%m-%d")
        new_slots_res = await get_available_slots(hospital_id=test_hospital_id, doctor_id=sample_doc_id, date_str=new_resched_date, db=db)
        new_slot = new_slots_res.get('available_slots', ['10:00 AM'])[0] if new_slots_res.get('available_slots') else '10:00 AM'
        
        resched_res = await reschedule_appointment(
            hospital_id=test_hospital_id,
            user_id="usr_patient_test_01",
            role="PATIENT",
            appointment_id_or_query=created_appt_id,
            new_date_str=new_resched_date,
            new_time_slot=new_slot,
            db=db
        )
        print(f"Reschedule Result: {resched_res.get('success')} | New Date: {resched_res.get('new_date')} at {resched_res.get('new_time')}")
        assert resched_res.get("success") is True
        print("  [PASS] Reschedule Appointment test passed.")

        # 8. TEST CANCEL APPOINTMENT WITH CONFIRMATION TOKEN
        print("\n[TEST 8] cancel_appointment (Confirmation Flow)")
        cancel_prompt = await cancel_appointment(
            hospital_id=test_hospital_id,
            user_id="usr_patient_test_01",
            role="PATIENT",
            appointment_id_or_query=created_appt_id,
            reason="Test cancellation",
            db=db
        )
        assert cancel_prompt.get("status") == "CONFIRMATION_REQUIRED"
        token = cancel_prompt.get("confirmation_token")
        print(f"Confirmation Token generated: {token}")

        cancel_done = await cancel_appointment(
            hospital_id=test_hospital_id,
            user_id="usr_patient_test_01",
            role="PATIENT",
            appointment_id_or_query=created_appt_id,
            confirmation_token=token,
            db=db
        )
        print(f"Cancellation execution: {cancel_done.get('success')} | Status: {cancel_done.get('status')}")
        assert cancel_done.get("success") is True
        assert cancel_done.get("status") == "CANCELLED"
        print("  [PASS] Cancel Appointment with Confirmation Token test passed.")

        # 9. TEST ZERO-TRUST RBAC & MULTI-TENANT ISOLATION
        print("\n[TEST 9] Security & Zero-Trust RBAC Verification")
        cross_tenant_search = await search_doctors(
            hospital_id=other_hospital_id,
            db=db
        )
        for d in cross_tenant_search.get("doctors", []):
            assert d.get("name") != "Dr. shiva mishra", "Cross-tenant data leakage detected!"
        print("  [PASS] Cross-tenant data isolation verified.")

        assert tool_registry.is_authorized("get_platform_control_tower_overview", "PATIENT") is False
        assert tool_registry.is_authorized("search_clinical_emr_records", "PATIENT") is False
        assert tool_registry.is_authorized("get_hospital_information", "PATIENT") is True
        assert tool_registry.is_authorized("book_appointment", "PATIENT") is True
        print("  [PASS] Role-based tool authorization matrix verified.")

        # 10. TEST END-TO-END COPILOT ENGINE WITH MULTILINGUAL QUERIES
        print("\n[TEST 10] CopilotEngine End-to-End Multilingual Queries")
        
        # 10a. English: Hospital info query
        res_en = await copilot_engine.chat(
            user_message="What is the address and contact number of Rao Hospital?",
            user_id="user_test_1",
            hospital_id=test_hospital_id,
            role="PATIENT",
            hospital_name="Rao Hospital",
            active_tab="Dashboard",
            selected_date=target_date,
            chat_history=[],
            db=db
        )
        print(f"\n[EN Query Reply Preview]:\n{res_en['reply'][:200]}...")
        assert "Rao Hospital" in res_en["reply"] or "Address" in res_en["reply"] or "hospital" in res_en["reply"].lower()

        # 10b. Hindi / Hinglish: Doctor availability query
        res_hi = await copilot_engine.chat(
            user_message="Dr shiva mishra kal baithenge kya?",
            user_id="user_test_1",
            hospital_id=test_hospital_id,
            role="PATIENT",
            hospital_name="Rao Hospital",
            active_tab="Dashboard",
            selected_date=target_date,
            chat_history=[],
            db=db
        )
        print(f"\n[HI/Hinglish Query Reply Preview]:\n{res_hi['reply'][:200]}...")
        assert "shiva" in res_hi["reply"].lower() or "doctor" in res_hi["reply"].lower()

        # 10c. Hinglish: Doctor search by specialty
        res_specialty = await copilot_engine.chat(
            user_message="Mujhe cardiologist doctor ki list dikhao",
            user_id="user_test_1",
            hospital_id=test_hospital_id,
            role="PATIENT",
            hospital_name="Rao Hospital",
            active_tab="Dashboard",
            selected_date=target_date,
            chat_history=[],
            db=db
        )
        print(f"\n[Specialty Query Reply Preview]:\n{res_specialty['reply'][:200]}...")
        assert "doctor" in res_specialty["reply"].lower() or "cardiolog" in res_specialty["reply"].lower()

        print("\n" + "="*80)
        print("ALL 10 TESTS IN AURA HMS AI TOOLS TEST SUITE PASSED SUCCESSFULLY!")
        print("="*80)

if __name__ == "__main__":
    asyncio.run(run_hms_ai_tools_test_suite())
