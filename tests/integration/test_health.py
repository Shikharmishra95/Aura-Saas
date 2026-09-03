import pytest

@pytest.mark.asyncio
async def test_health_endpoint_returns_200_and_healthy(client):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "healthy"
