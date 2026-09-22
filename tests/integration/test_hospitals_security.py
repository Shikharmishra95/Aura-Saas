import uuid
import pytest
from app.database.models.call_log import User, UserRole
from app.database.models.appointment import HospitalSetting
from app.core.dependencies import hash_password, create_access_token
from app.core.config import settings

@pytest.mark.asyncio
async def test_get_hospitals_unauthenticated_returns_401(client):
    """Verifies unauthenticated requests to GET /hospitals are rejected with 401."""
    response = await client.get("/api/v1/hospitals")
    assert response.status_code == 401
    assert "detail" in response.json()


@pytest.mark.asyncio
async def test_get_hospitals_normal_user_returns_403(client, db_session, hospital_a, seed_roles):
    """Verifies normal authenticated user (e.g. PATIENT role) is rejected with 403."""
    user = User(
        id="USER-NORMAL-1",
        hospital_id=hospital_a.id,
        username="normal_user",
        email="normal@alpha.com",
        password_hash=hash_password("userpass123"),
        first_name="Normal",
        last_name="User",
        is_active=True
    )
    db_session.add(user)
    await db_session.flush()
    ur = UserRole(
        id=str(uuid.uuid4()),
        user_id=user.id,
        role_id=seed_roles["PATIENT"].id
    )
    db_session.add(ur)
    await db_session.commit()

    token = create_access_token({
        "sub": user.username,
        "role": "PATIENT",
        "hospital_id": user.hospital_id,
        "user_id": user.id
    })
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.get("/api/v1/hospitals", headers=headers)
    assert response.status_code == 403
    assert "SuperAdmin" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_hospitals_receptionist_returns_403(client, hospital_a, receptionist_token_a):
    """Verifies receptionist user is rejected with 403."""
    headers = {"Authorization": f"Bearer {receptionist_token_a}"}
    response = await client.get("/api/v1/hospitals", headers=headers)
    assert response.status_code == 403
    assert "SuperAdmin" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_hospitals_doctor_returns_403(client, hospital_a, doctor_token_a):
    """Verifies doctor user is rejected with 403."""
    headers = {"Authorization": f"Bearer {doctor_token_a}"}
    response = await client.get("/api/v1/hospitals", headers=headers)
    assert response.status_code == 403
    assert "SuperAdmin" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_hospitals_hospital_admin_returns_403(client, hospital_a, auth_token_headers):
    """Verifies hospital admin is rejected with 403 (requires SUPER_ADMIN)."""
    response = await client.get("/api/v1/hospitals", headers=auth_token_headers)
    assert response.status_code == 403
    assert "SuperAdmin" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_hospitals_super_admin_returns_200(client, hospital_a, superadmin_token_headers):
    """Verifies SUPER_ADMIN is granted access to GET /hospitals."""
    response = await client.get("/api/v1/hospitals", headers=superadmin_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    ids = [h["id"] for h in data]
    assert hospital_a.id in ids


@pytest.mark.asyncio
async def test_get_hospitals_redacts_plaintext_secrets(client, db_session, hospital_a, superadmin_token_headers):
    """Verifies that sensitive credentials (admin_password, twilio_auth_token) are redacted."""
    raw_secret_password = "SuperSecretPassword999!"
    raw_secret_token = "a1b2c3d4e5f60718293a4b5c6d7e8f90"

    # Add sensitive settings for hospital_a
    db_session.add(HospitalSetting(
        id=str(uuid.uuid4()),
        hospital_id=hospital_a.id,
        setting_key="admin_password",
        setting_value=raw_secret_password
    ))
    db_session.add(HospitalSetting(
        id=str(uuid.uuid4()),
        hospital_id=hospital_a.id,
        setting_key="twilio_auth_token",
        setting_value=raw_secret_token
    ))
    await db_session.commit()

    response = await client.get("/api/v1/hospitals", headers=superadmin_token_headers)
    assert response.status_code == 200

    # Ensure plaintext secrets are NOT exposed anywhere in the raw response body
    assert raw_secret_password not in response.text
    assert raw_secret_token not in response.text
    if settings.TWILIO_AUTH_TOKEN:
        assert settings.TWILIO_AUTH_TOKEN not in response.text

    # Verify structured fields in the JSON response
    data = response.json()
    hosp = next((h for h in data if h["id"] == hospital_a.id), None)
    assert hosp is not None

    assert hosp["admin_password"] != raw_secret_password
    assert hosp["admin_password"] == "••••••••"

    assert hosp["twilio_auth_token"] != raw_secret_token
    assert hosp["twilio_auth_token"] == "••••••••"
