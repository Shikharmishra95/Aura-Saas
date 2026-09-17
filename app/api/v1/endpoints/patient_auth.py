from fastapi import APIRouter, Depends, HTTPException, status, Body, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta, date
import random
import uuid

from app.database.session import get_db
from app.database.models.appointment import Patient, Hospital
from app.core.dependencies import create_access_token
from app.core.logging import logger

router = APIRouter()

# ─── Simple In-Memory OTP Rate Limiter ─────────────────────────────────────
# Tracks: { phone_number: [timestamp1, timestamp2, ...] }
# Allows max 3 OTP requests per phone per 10 minutes
_otp_request_tracker: dict = {}
OTP_MAX_REQUESTS = 3
OTP_WINDOW_MINUTES = 10

def _check_otp_rate_limit(phone: str):
    """Raises HTTP 429 if phone has exceeded OTP request limit in the time window."""
    now = datetime.utcnow()
    window_start = now - timedelta(minutes=OTP_WINDOW_MINUTES)
    
    # Clean old entries outside the window
    if phone in _otp_request_tracker:
        _otp_request_tracker[phone] = [
            ts for ts in _otp_request_tracker[phone] if ts > window_start
        ]
    
    request_count = len(_otp_request_tracker.get(phone, []))
    if request_count >= OTP_MAX_REQUESTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many OTP requests. Please wait {OTP_WINDOW_MINUTES} minutes before trying again."
        )
    
    # Record this request
    if phone not in _otp_request_tracker:
        _otp_request_tracker[phone] = []
    _otp_request_tracker[phone].append(now)
# ───────────────────────────────────────────────────────────────────────────

class SendOTPRequest(BaseModel):
    hospital_id: str
    phone: str

class VerifyOTPRequest(BaseModel):
    hospital_id: str
    phone: str
    otp: str
    name: Optional[str] = None
    age: Optional[int] = None  # Age in years, provided during first-time registration

@router.post("/send-otp")
async def send_otp(request: SendOTPRequest, db: AsyncSession = Depends(get_db)):
    """
    Sends an OTP to the patient's phone for login.
    If the patient does not exist, registers them temporarily.
    Rate limited: max 3 requests per phone per 10 minutes.
    """
    # Rate limit check — must be first before any DB work
    _check_otp_rate_limit(request.phone)

    # Check if hospital subscription is active
    hosp = await db.get(Hospital, request.hospital_id)
    if hosp and (hosp.plan_status == "EXPIRED" or (hosp.plan_expires_at and hosp.plan_expires_at < datetime.utcnow())):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hospital online patient services are currently suspended due to plan expiration. Please contact the hospital front desk directly."
        )

    stmt = select(Patient).where(Patient.phone == request.phone, Patient.hospital_id == request.hospital_id).order_by(Patient.created_at.asc())
    patient = (await db.execute(stmt)).scalars().first()
    
    is_new_user = False
    if not patient or patient.first_name == "New":
        is_new_user = True
        if not patient:
            patient = Patient(
                id=str(uuid.uuid4()),
                hospital_id=request.hospital_id,
                first_name="New",
                last_name="Patient",
                date_of_birth=date(1990, 1, 1), # Default MVP dob
                phone=request.phone
            )
            db.add(patient)
    
    # Generate OTP
    otp = "1234" # Hardcoded for MVP testing
    
    patient.otp = otp
    patient.otp_expires_at = datetime.utcnow() + timedelta(minutes=5)
    
    db.add(patient)
    await db.commit()
    
    # Simulate sending SMS
    logger.info(f"OTP for {request.phone} at hospital {request.hospital_id} is {otp}")
    
    return {"success": True, "message": "OTP sent successfully.", "is_new_user": is_new_user}

@router.post("/verify-otp")
async def verify_otp(request: VerifyOTPRequest, db: AsyncSession = Depends(get_db)):
    """
    Verifies the OTP and issues a PATIENT role JWT.
    Updates name if provided for new users.
    """
    stmt = select(Patient).where(Patient.phone == request.phone, Patient.hospital_id == request.hospital_id).order_by(Patient.created_at.asc())
    patient = (await db.execute(stmt)).scalars().first()
    
    if not patient:
        raise HTTPException(status_code=404, detail="Phone number not found.")
        
    if not patient.otp or patient.otp != request.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP.")
        
    if patient.otp_expires_at and patient.otp_expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="OTP has expired.")
        
    # Update name if provided (new user registration)
    if request.name:
        parts = request.name.strip().split(" ", 1)
        patient.first_name = parts[0]
        patient.last_name = parts[1] if len(parts) > 1 else ""

    # Update date_of_birth from age if provided
    if request.age and request.age > 0:
        birth_year = date.today().year - request.age
        patient.date_of_birth = date(birth_year, 1, 1)

    # Clear OTP
    patient.otp = None
    patient.otp_expires_at = None
    db.add(patient)
    await db.commit()
    
    # Issue JWT token
    access_token = create_access_token(data={
        "sub": patient.phone, 
        "user_id": patient.id,
        "role": "PATIENT", 
        "hospital_id": patient.hospital_id
    })
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "patient": {
            "id": patient.id,
            "name": f"{patient.first_name} {patient.last_name}".strip(),
            "phone": patient.phone,
            "hospital_id": patient.hospital_id
        }
    }
