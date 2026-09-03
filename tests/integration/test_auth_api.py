import pytest

@pytest.mark.asyncio
async def test_login_with_valid_database_user_returns_jwt(client, admin_user_a):
    login_data = {
        "username": "admin_alpha",
        "password": "adminpass123"
    }
    response = await client.post("/api/v1/auth/login", data=login_data)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["username"] == "admin_alpha"
    assert data["role"] == "ADMIN"
    assert data["hospital_id"] == admin_user_a.hospital_id

@pytest.mark.asyncio
async def test_login_with_invalid_password_returns_401(client, admin_user_a):
    login_data = {
        "username": "admin_alpha",
        "password": "WrongPassword999"
    }
    response = await client.post("/api/v1/auth/login", data=login_data)
    assert response.status_code == 401
    assert "Incorrect username or password" in response.json()["detail"]

@pytest.mark.asyncio
async def test_login_with_nonexistent_user_returns_401(client):
    login_data = {
        "username": "non_existent_user",
        "password": "somepassword"
    }
    response = await client.post("/api/v1/auth/login", data=login_data)
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_register_hospital_creates_tenant_and_admin(client, seed_roles):
    onboard_data = {
        "name": "City Care Hospital",
        "address": "123 Main Road, City",
        "phone": "+919988776655",
        "admin_username": "city_admin",
        "admin_email": "admin@citycare.com",
        "admin_password": "securepassword123",
        "plan_name": "STARTER"
    }
    response = await client.post("/api/v1/auth/register-hospital", data=onboard_data)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "hospital_id" in data
    assert "hospital_slug" in data
    assert data["admin_username"] == "city_admin"
