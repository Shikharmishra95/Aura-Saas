"""
AURA AI Copilot Golden Test Suite
=================================
Automated evaluation test runner across all portals and multi-turn flows:
1. SuperAdmin Multi-Turn Context (Rao Hospital doctor count -> revenue scoping)
2. SuperAdmin SaaS Platform Revenue vs OPD Appointment Revenue (₹62,997 LTV match)
3. Zero-Hallucination verification (tool_used is mandatory on numerical queries)
4. Human-friendly brevity (no unwanted massive markdown table dumps)
"""

import pytest
import pytest_asyncio
from app.database.session import async_session_factory
from app.engines.copilot_engine import CopilotEngine
from app.engines.conversation_memory import conversation_memory


@pytest.mark.asyncio
async def test_superadmin_multi_turn_rao_hospital_context():
    """
    Verifies that when Super Admin queries Rao Hospital doctors in Turn 1,
    Turn 2 'total appointment revenue?' stays scoped to Rao Hospital (HOSP-RAOH-4893)
    and reports exact DB revenue rather than platform-wide ₹1.015 Crore.
    """
    session_id = "test_golden_rao_multiturn"
    user_id = "golden_test_super_admin"
    hospital_id = "super_admin"
    role = "SUPER_ADMIN"

    async with async_session_factory() as db:
        # Turn 1: Doctor inquiry for Rao Hospital
        t1 = await CopilotEngine.chat(
            user_message="how much doctor in rao hospital ?",
            hospital_id=hospital_id,
            user_id=user_id,
            role=role,
            hospital_name="Platform Control Tower",
            active_tab="overview",
            selected_date="2026-09-23",
            chat_history=[],
            db=db,
            session_id=session_id
        )
        assert t1 is not None
        reply_1 = t1.get("reply", "")
        assert "4" in reply_1 or "Rao" in reply_1

        # Check memory context state
        ctx = conversation_memory.get_context_state(hospital_id, user_id, session_id)
        assert ctx.current_hospital_id == "HOSP-RAOH-4893" or "Rao" in (ctx.current_hospital_name or "")

        # Turn 2: Follow-up revenue query without repeating hospital name
        history = [
            {"role": "user", "content": "how much doctor in rao hospital ?"},
            {"role": "assistant", "content": reply_1}
        ]
        t2 = await CopilotEngine.chat(
            user_message="total appointment revenue?",
            hospital_id=hospital_id,
            user_id=user_id,
            role=role,
            hospital_name="Platform Control Tower",
            active_tab="overview",
            selected_date="2026-09-23",
            chat_history=history,
            db=db,
            session_id=session_id
        )
        assert t2 is not None
        assert t2.get("tool_used") == "get_revenue_and_dues"

        # Verify exact database scoping (Must NOT be platform-wide or hallucinated 1 Crore!)
        tool_res = t2.get("tool_result") or {}
        assert tool_res.get("hospital_id") == "HOSP-RAOH-4893"
        assert tool_res.get("total_appointments") == 14

        reply_2 = t2.get("reply", "")
        # Brevity verification: Must NOT dump two massive tables
        assert reply_2.count("|---|") <= 1
        # Must not fabricate 1 Crore
        assert "1,01,50,000" not in reply_2
        assert "1.015" not in reply_2


@pytest.mark.asyncio
async def test_superadmin_saas_platform_revenue_analytics():
    """
    Verifies that 'total platform saas revenue?' triggers get_platform_revenue_analytics
    and returns exact Control Tower subscription revenue (₹62,997).
    """
    session_id = "test_golden_saas_rev"
    user_id = "golden_test_super_admin"
    hospital_id = "super_admin"
    role = "SUPER_ADMIN"

    async with async_session_factory() as db:
        res = await CopilotEngine.chat(
            user_message="total platform saas revenue?",
            hospital_id=hospital_id,
            user_id=user_id,
            role=role,
            hospital_name="Platform Control Tower",
            active_tab="overview",
            selected_date="2026-09-23",
            chat_history=[],
            db=db,
            session_id=session_id
        )
        assert res is not None
        assert res.get("tool_used") in ["get_platform_revenue_analytics", "get_platform_control_tower_overview"]
        tool_res = res.get("tool_result") or {}
        rev_val = str(tool_res.get("total_platform_saas_revenue", "")) + str(tool_res.get("total_platform_saas_revenue_formatted", ""))
        assert "62,997" in rev_val or tool_res.get("total_platform_saas_revenue") == 62997.0 or tool_res.get("total_platform_saas_revenue") == 62997
        reply = res.get("reply", "")
        assert "62,997" in reply
