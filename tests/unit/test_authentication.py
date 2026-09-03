import pytest
from datetime import timedelta
import jwt
from fastapi import HTTPException
from app.core.config import settings
from app.core.dependencies import (
    hash_password, verify_password, create_access_token, get_current_user
)

def test_hash_and_verify_password_success():
    plain = "SuperSecurePassword123!"
    hashed = hash_password(plain)
    assert hashed != plain
    assert verify_password(plain, hashed) is True
    assert verify_password("WrongPassword", hashed) is False

def test_password_length_truncation_safety():
    very_long_pwd = "A" * 150
    hashed = hash_password(very_long_pwd)
    assert verify_password(very_long_pwd, hashed) is True

def test_create_access_token_and_decode():
    data = {"sub": "testuser", "role": "ADMIN", "hospital_id": "HOSP-123"}
    token = create_access_token(data, expires_delta=timedelta(minutes=15))
    
    payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    assert payload["sub"] == "testuser"
    assert payload["role"] == "ADMIN"
    assert payload["hospital_id"] == "HOSP-123"
    assert "exp" in payload

def test_jwt_expired_raises_error():
    data = {"sub": "testuser"}
    token = create_access_token(data, expires_delta=timedelta(minutes=-5))
    
    with pytest.raises(jwt.PyJWTError):
        jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])

@pytest.mark.asyncio
async def test_get_current_user_valid_db_user(db_session, admin_user_a, admin_token_a):
    user = await get_current_user(token=admin_token_a, db=db_session)
    assert user.id == admin_user_a.id
    assert user.username == admin_user_a.username
    assert user.hospital_id == admin_user_a.hospital_id

@pytest.mark.asyncio
async def test_get_current_user_inactive_user_raises_401(db_session, admin_user_a, admin_token_a):
    admin_user_a.is_active = False
    await db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(token=admin_token_a, db=db_session)
    assert exc_info.value.status_code == 401

@pytest.mark.asyncio
async def test_get_current_user_unknown_user_raises_401(db_session):
    token = create_access_token({"sub": "ghost_user_9999"})
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(token=token, db=db_session)
    assert exc_info.value.status_code == 401
