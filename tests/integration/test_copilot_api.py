import pytest

@pytest.mark.asyncio
async def test_copilot_requires_auth(client):
    """Unauthenticated users must be blocked from querying Copilot."""
    response = await client.post("/api/v1/copilot/chat", json={
        "message": "28 August ko kitne appointments the?"
    })
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_copilot_authenticated_chat(client, admin_token_a):
    """Authenticated staff can query copilot and receive accurate responses."""
    response = await client.post(
        "/api/v1/copilot/chat",
        headers={"Authorization": f"Bearer {admin_token_a}"},
        json={
            "message": "Aaj ka appointments summary batao",
            "active_tab": "overview",
            "selected_date": "2026-09-03"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "reply" in data
    assert "conversation_id" in data


