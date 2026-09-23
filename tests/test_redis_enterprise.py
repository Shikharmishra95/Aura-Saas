"""
AURA Enterprise Redis Cache & Distributed Locking Test Suite
============================================================
Validates:
1. Resilient Redis Manager key-value operations and TTL handling
2. Multi-tenant key isolation across tenant hospitals
3. Distributed atomic concurrency locking (race condition prevention)
4. Multi-turn conversation memory persistence across simulated worker restarts
5. Action confirmation token distributed validation
6. System health radar telemetry integration
"""

import asyncio
import time
import pytest
import pytest_asyncio

from app.core.redis import redis_manager
from app.engines.conversation_memory import (
    conversation_memory,
    ConversationMessage,
    SessionContextState
)


@pytest.mark.asyncio
async def test_redis_manager_lifecycle_and_fallback():
    """Verifies that Redis manager stores, retrieves, checks existence, and deletes data."""
    test_key = "aura:test:lifecycle:key1"
    test_payload = {"hospital_name": "Rao Hospital", "active_doctors": 4, "fee": 500}

    # Set
    success = await redis_manager.set_json(test_key, test_payload, ttl_seconds=60)
    assert success is True

    # Exists
    exists = await redis_manager.exists(test_key)
    assert exists is True

    # Get
    retrieved = await redis_manager.get_json(test_key)
    assert retrieved is not None
    assert retrieved.get("hospital_name") == "Rao Hospital"
    assert retrieved.get("active_doctors") == 4

    # Delete
    del_success = await redis_manager.delete(test_key)
    assert del_success is True

    # Verify gone
    retrieved_after = await redis_manager.get_json(test_key)
    assert retrieved_after is None


@pytest.mark.asyncio
async def test_redis_pattern_deletion():
    """Verifies non-blocking SCAN-based pattern invalidation."""
    prefix = "aura:test:pattern:hosp_del"
    await redis_manager.set_json(f"{prefix}:doc1:2026-09-24", {"slots": ["10:00", "10:30"]})
    await redis_manager.set_json(f"{prefix}:doc1:2026-09-25", {"slots": ["11:00", "11:30"]})
    await redis_manager.set_json(f"{prefix}:doc2:2026-09-24", {"slots": ["14:00"]})

    # Invalidate only doc1
    deleted_cnt = await redis_manager.delete_pattern(f"{prefix}:doc1:*")
    assert deleted_cnt >= 2

    # doc1 keys must be gone
    assert await redis_manager.get_json(f"{prefix}:doc1:2026-09-24") is None
    assert await redis_manager.get_json(f"{prefix}:doc1:2026-09-25") is None

    # doc2 key must still exist
    doc2_val = await redis_manager.get_json(f"{prefix}:doc2:2026-09-24")
    assert doc2_val is not None

    # Cleanup
    await redis_manager.delete(f"{prefix}:doc2:2026-09-24")


@pytest.mark.asyncio
async def test_multi_tenant_key_isolation():
    """Verifies that Hospital A data cannot be accessed or overwritten by Hospital B."""
    hosp_a_key = "aura:prod:HOSP-A:slots:doc1:today"
    hosp_b_key = "aura:prod:HOSP-B:slots:doc1:today"

    await redis_manager.set_json(hosp_a_key, {"hospital": "Alpha", "quota": 100})
    await redis_manager.set_json(hosp_b_key, {"hospital": "Beta", "quota": 200})

    res_a = await redis_manager.get_json(hosp_a_key)
    res_b = await redis_manager.get_json(hosp_b_key)

    assert res_a["hospital"] == "Alpha"
    assert res_b["hospital"] == "Beta"

    # Invalidate Hospital A slots
    await redis_manager.delete_pattern("aura:prod:HOSP-A:*")

    # Hospital B must remain completely intact
    assert await redis_manager.get_json(hosp_a_key) is None
    res_b_after = await redis_manager.get_json(hosp_b_key)
    assert res_b_after is not None
    assert res_b_after["hospital"] == "Beta"

    # Cleanup
    await redis_manager.delete(hosp_b_key)


@pytest.mark.asyncio
async def test_distributed_concurrency_lock():
    """Verifies distributed slot locking prevents simultaneous double-booking."""
    lock_key = "aura:prod:lock:slot:doc_42:2026-09-24T14:30"

    # Holder 1 acquires lock
    async with redis_manager.acquire_lock(lock_key, timeout=2.0, blocking_timeout=1.0):
        # Holder 2 tries to acquire the same lock -> must raise TimeoutError
        with pytest.raises(TimeoutError):
            async with redis_manager.acquire_lock(lock_key, timeout=1.0, blocking_timeout=0.1):
                pass

    # Once Holder 1 leaves the block, Holder 2 can acquire successfully
    acquired_second = False
    async with redis_manager.acquire_lock(lock_key, timeout=2.0, blocking_timeout=1.0):
        acquired_second = True

    assert acquired_second is True


@pytest.mark.asyncio
async def test_conversation_memory_redis_sync():
    """
    Simulates multi-worker persistence:
    Turn 1 runs on Worker A (writes to memory & Redis).
    Worker A's memory is wiped (simulating a separate Uvicorn worker process).
    Worker B loads state from Redis and retains full multi-turn context!
    """
    h_id = "HOSP-RAOH-4893"
    u_id = "USR-ADMIN-01"
    s_id = "worker_sim_session_99"

    # Worker A writes context
    state = conversation_memory.get_context_state(h_id, u_id, s_id)
    state.current_hospital_id = "HOSP-RAOH-4893"
    state.current_hospital_name = "Rao Hospital"
    state.current_doctor_name = "Dr. Nitin"
    state.current_doctor_id = "DOC-NITIN-01"

    # Worker A appends messages
    msg1 = ConversationMessage(role="user", content="how much doctor in rao hospital ?")
    msg2 = ConversationMessage(role="assistant", content="Rao Hospital currently has 4 active doctors.", tool_name="search_platform_hospital")
    conversation_memory.append_message(h_id, u_id, s_id, msg1)
    conversation_memory.append_message(h_id, u_id, s_id, msg2)

    # Save to Redis
    await conversation_memory.save_session_to_redis(h_id, u_id, s_id)

    # SIMULATE SEPARATE WORKER PROCESS: Wipe local in-memory dictionaries
    comp_key = conversation_memory._get_compound_key(h_id, u_id, s_id)
    conversation_memory._context_states.pop(comp_key, None)
    conversation_memory._sessions.pop(comp_key, None)

    # Verify local memory was completely emptied
    assert comp_key not in conversation_memory._context_states
    assert comp_key not in conversation_memory._sessions

    # Worker B loads from Redis
    await conversation_memory.load_session_from_redis(h_id, u_id, s_id)

    # Worker B inspects context
    loaded_state = conversation_memory.get_context_state(h_id, u_id, s_id)
    assert loaded_state.current_hospital_id == "HOSP-RAOH-4893"
    assert loaded_state.current_hospital_name == "Rao Hospital"
    assert loaded_state.current_doctor_name == "Dr. Nitin"

    loaded_history = conversation_memory.get_history(h_id, u_id, s_id)
    assert len(loaded_history) == 2
    assert loaded_history[0].content == "how much doctor in rao hospital ?"
    assert loaded_history[1].tool_name == "search_platform_hospital"


@pytest.mark.asyncio
async def test_confirmation_token_distributed_validation():
    """Verifies that high-risk action confirmation tokens work across distributed workers via Redis."""
    h_id = "HOSP-RAOH-4893"
    u_id = "USR-SUPERADMIN"

    # Create token on Worker A
    token_record = await conversation_memory.async_create_confirmation_token(
        hospital_id=h_id,
        user_id=u_id,
        action_name="apply_leave_for_doctor",
        action_args={"doctor_id": "DOC-1", "date": "2026-09-25"},
        summary="Apply leave for Dr. Nitin on 2026-09-25",
        expires_in_seconds=300
    )
    token_id = token_record.token

    # SIMULATE SEPARATE WORKER: Wipe Worker A's local token dictionary
    conversation_memory._pending_confirmations.pop(token_id, None)
    assert token_id not in conversation_memory._pending_confirmations

    # Worker B validates and consumes token from Redis
    consumed = await conversation_memory.async_validate_and_consume_token(
        token=token_id,
        hospital_id=h_id,
        user_id=u_id
    )
    assert consumed is not None
    assert consumed.action_name == "apply_leave_for_doctor"
    assert consumed.action_args["doctor_id"] == "DOC-1"

    # Second consumption attempt must fail (one-time use)
    second_attempt = await conversation_memory.async_validate_and_consume_token(
        token=token_id,
        hospital_id=h_id,
        user_id=u_id
    )
    assert second_attempt is None


@pytest.mark.asyncio
async def test_health_radar_telemetry():
    """Verifies health telemetry reporting for SuperAdmin Control Tower."""
    health = await redis_manager.get_health()
    assert health is not None
    assert "name" in health
    assert health["status"] in ["HEALTHY", "FALLBACK_IN_MEMORY"]
    assert "latency_ms" in health
    assert "provider" in health
