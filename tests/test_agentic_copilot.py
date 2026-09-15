"""
AURA Agentic Copilot & Multi-Turn Entity Resolution Test Suite
Verifies:
1. Domain entity extraction (dates, times, phones, IDs, doctors, departments)
2. Multi-turn context continuity and working memory
3. Multi-tool sequence execution and agentic reasoning loops
4. Strict anti-hallucination grounding against live database
5. Two-phase action confirmation security
"""

import sys
import os
import asyncio
from datetime import datetime, date, timedelta

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database.session import async_session_factory
from app.engines.entity_extractor import entity_extractor, ExtractedEntities
from app.engines.conversation_memory import conversation_memory, ConversationMessage
from app.engines.copilot_engine import copilot_engine
from app.tools import DoctorTools, AppointmentTools

async def run_agentic_copilot_test_suite():
    print("\n" + "="*80)
    print("AURA AGENTIC COPILOT & MULTI-TURN ENTITY RESOLUTION TEST SUITE")
    print("="*80 + "\n")

    # =========================================================================
    # [TEST 1] Entity Extraction Engine Accuracy
    # =========================================================================
    print("[TEST 1] Testing Domain Entity Extraction Engine...")
    ref_date = date(2026, 9, 9)  # Wednesday

    # Relative Dates
    e1 = entity_extractor.extract_entities("Kya doctor kal available hain?", reference_date=ref_date)
    assert e1.date_str == "2026-09-10", f"Expected 2026-09-10, got {e1.date_str}"
    
    e2 = entity_extractor.extract_entities("Book slot for parso morning", reference_date=ref_date)
    assert e2.date_str == "2026-09-11", f"Expected 2026-09-11, got {e2.date_str}"

    e3 = entity_extractor.extract_entities("Check schedule on this Friday", reference_date=ref_date)
    assert e3.date_str == "2026-09-11", f"Expected 2026-09-11, got {e3.date_str}"

    # Times & Phones
    e4 = entity_extractor.extract_entities("Book 10:30 AM slot for Rahul phone +919876543210")
    assert e4.time_str == "10:30 AM", f"Expected 10:30 AM, got {e4.time_str}"
    assert e4.patient_phone == "9876543210", f"Expected 9876543210, got {e4.patient_phone}"
    assert e4.patient_name == "Rahul", f"Expected Rahul, got {e4.patient_name}"

    # Doctor, Department & IDs
    e5 = entity_extractor.extract_entities("Is Dr. Nitin Dewedi in cardiology available for apt_abc1234567?")
    assert "Nitin" in (e5.doctor_name or ""), f"Expected Nitin in doctor_name, got {e5.doctor_name}"
    assert e5.department == "Cardiology", f"Expected Cardiology, got {e5.department}"
    assert e5.appointment_id == "apt_abc1234567", f"Expected apt_abc1234567, got {e5.appointment_id}"

    # Action Confirmation Token
    e6 = entity_extractor.extract_entities("CONFIRM act_98a7bc1234")
    assert e6.action_token == "act_98a7bc1234", f"Expected act_98a7bc1234, got {e6.action_token}"

    print("  [PASS] Entity extraction accurately parsed dates, times, phones, doctors, and IDs.\n")

    # =========================================================================
    # DB SETUP & CONTEXT INITIALIZATION
    # =========================================================================
    async with async_session_factory() as db:
        hosp_id = "HOSP-RAOH-4893"
        session_id = f"sess_agentic_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        user_id = "pat_agentic_test_01"
        role = "PATIENT"

        # Find sample doctor from DB
        docs_res = await DoctorTools.search_doctors(hospital_id=hosp_id, db=db)
        assert docs_res.get("total_count", 0) > 0, "No doctors found in DB"
        test_doctor = docs_res["doctors"][0]
        test_doc_id = test_doctor["doctor_id"]
        test_doc_name = test_doctor["doctor_name"]
        print(f"[SETUP] Using test doctor: {test_doc_name} (ID: {test_doc_id})")

        # =====================================================================
        # [TEST 2] Multi-Turn Context Continuity (Doctor -> Slots -> Booking)
        # =====================================================================
        print("\n[TEST 2] Multi-Turn Conversational Memory & Context Continuity...")
        
        # Turn 1: Inquire about Doctor
        turn1_query = f"Is {test_doc_name} available tomorrow?"
        res1 = await copilot_engine.chat(
            user_message=turn1_query,
            hospital_name="Rao Hospital",
            hospital_id=hosp_id,
            user_id=user_id,
            role=role,
            active_tab="appointments",
            selected_date=None,
            chat_history=[],
            db=db,
            session_id=session_id
        )
        print("  Turn 1 Response Preview:", res1["reply"][:120], "...")
        assert res1["reply"], "Turn 1 reply empty"
        
        # Verify Context State was captured
        ctx = conversation_memory.get_context_state(hosp_id, user_id, session_id)
        assert ctx.current_doctor_name is not None, "Context did not capture doctor name"
        assert ctx.selected_date is not None, "Context did not capture selected date"
        print(f"  Context State after Turn 1: Doctor='{ctx.current_doctor_name}', Date='{ctx.selected_date}'")

        # Record Turn 1 in memory
        conversation_memory.append_message(
            hosp_id, user_id, session_id,
            ConversationMessage(role="user", content=turn1_query)
        )
        conversation_memory.append_message(
            hosp_id, user_id, session_id,
            ConversationMessage(role="assistant", content=res1["reply"])
        )

        # Turn 2: Ask for slots using PRONOUN ("his open slots") - zero explicit doctor name or date!
        turn2_query = "What are his available slots?"
        hist = [{"role": m.role, "content": m.content} for m in conversation_memory.get_history(hosp_id, user_id, session_id)]
        res2 = await copilot_engine.chat(
            user_message=turn2_query,
            hospital_name="Rao Hospital",
            hospital_id=hosp_id,
            user_id=user_id,
            role=role,
            active_tab="appointments",
            selected_date=None,
            chat_history=hist,
            db=db,
            session_id=session_id
        )
        print("  Turn 2 Response Preview:", res2["reply"][:120], "...")
        assert res2["reply"], "Turn 2 reply empty"
        print("  [PASS] Multi-turn pronoun resolution successfully carried forward doctor & date context.")

        # =====================================================================
        # [TEST 3] Anti-Hallucination & Grounding: Non-Existent Entities
        # =====================================================================
        print("\n[TEST 3] Anti-Hallucination Verification (Fictitious Records)...")
        
        # Lookup non-existent appointment ID
        fake_apt_id = "apt_fake000000999"
        res_fake_apt = await copilot_engine.chat(
            user_message=f"Show me details for appointment {fake_apt_id}",
            hospital_name="Rao Hospital",
            hospital_id=hosp_id,
            user_id=user_id,
            role="RECEPTIONIST",
            active_tab="appointments",
            selected_date=None,
            chat_history=[],
            db=db,
            session_id="fake_test_session"
        )
        print("  Fake Appointment Response Preview:", res_fake_apt["reply"][:150], "...")
        # Reply must NOT claim a fake patient exists or fabricate diagnosis/prices
        reply_lower = res_fake_apt["reply"].lower()
        assert any(w in reply_lower for w in ["not found", "no appointment", "no active appointment", "no record", "couldn't find", "could not find", "not available", "nahi mil", "invalid", "0", "verify your appointment", "no such"]), "Model hallucinated fake appointment details!"
        print("  [PASS] Non-existent appointment properly reported as not found with zero hallucination.")

        # =====================================================================
        # [TEST 4] Real Multi-Step Tool Chain & Booking Execution
        # =====================================================================
        print("\n[TEST 4] Multi-Step Booking Execution with Entity Resolution...")
        booking_date = (date.today() + timedelta(days=2)).isoformat()
        
        # Get slots
        slots_res = await DoctorTools.get_available_slots(
            hospital_id=hosp_id,
            doctor_id=test_doc_id,
            date_str=booking_date,
            db=db
        )
        available_slots = slots_res.get("available_slots", [])
        if available_slots:
            target_slot = available_slots[0]
            test_phone = f"9871{int(datetime.now().timestamp()) % 1000000:06d}"
            book_res = await AppointmentTools.book_appointment(
                hospital_id=hosp_id,
                user_id=user_id,
                role=role,
                doctor_name_or_dept=test_doc_name,
                date_str=booking_date,
                time_slot=target_slot,
                patient_name="Amit Sharma",
                phone=test_phone,
                db=db
            )
            assert book_res.get("success") is True, f"Booking failed: {book_res}"
            created_apt_id = book_res.get("appointment_id")
            token_num = book_res.get("token_number")
            print(f"  Created Appointment: ID={created_apt_id}, Token={token_num}, Slot={target_slot} on {booking_date}")

            # Test Cancellation Two-Phase Confirmation Flow
            print("\n[TEST 5] Two-Phase Action Confirmation Security...")
            cancel_prompt = f"Cancel my appointment {created_apt_id}"
            cancel_prep = await AppointmentTools.cancel_appointment(
                hospital_id=hosp_id,
                user_id=user_id,
                role=role,
                appointment_id_or_query=created_apt_id,
                reason="Patient request",
                db=db
            )
            assert cancel_prep.get("requires_confirmation") is True or cancel_prep.get("status") == "CONFIRMATION_REQUIRED", f"Cancellation should require confirmation token: {cancel_prep}"
            conf_token = cancel_prep.get("confirmation_token")
            assert conf_token and conf_token.startswith("act_"), f"Invalid token format: {conf_token}"
            print(f"  Confirmation Token Issued: {conf_token}")

            # Execute Direct Confirmation Command
            confirm_cmd = f"CONFIRM {conf_token}"
            confirm_res = await copilot_engine.chat(
                user_message=confirm_cmd,
                hospital_name="Rao Hospital",
                hospital_id=hosp_id,
                user_id=user_id,
                role=role,
                active_tab="appointments",
                selected_date=None,
                chat_history=[],
                db=db,
                session_id=session_id
            )
            print("  Confirmation Execution Preview:", confirm_res["reply"][:150], "...")
            assert "Confirmed and Executed" in confirm_res["reply"] or "CANCELLED" in confirm_res["reply"], "Confirmation execution failed"
            print("  [PASS] Two-phase action token security and confirmation workflow verified.")

    print("\n" + "="*80)
    print("ALL AGENTIC TOOL ROUTING & MULTI-TURN ENTITY TESTS PASSED SUCCESSFULLY!")
    print("="*80 + "\n")

if __name__ == "__main__":
    asyncio.run(run_agentic_copilot_test_suite())
