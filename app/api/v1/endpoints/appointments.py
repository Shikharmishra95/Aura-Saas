import uuid
import asyncio
from datetime import date, datetime, timezone, timedelta
from typing import List, Optional
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException, Request, status, Query, Form
from pydantic import BaseModel
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import HTMLResponse
from sqlalchemy import select, and_, or_, update
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.core.dependencies import create_access_token, verify_password, get_current_user, hash_password
from app.core.config import settings
from app.core.logging import logger
from app.database.models.call_log import User, Role, UserRole


async def auto_update_missed_appointments(db: AsyncSession):
    """
    Sweeper that auto-marks expired appointments as MISSED and dispatches WhatsApp notifications:
    - Any appointment (Paid or Unpaid) whose appointment_datetime has passed and is not COMPLETED/CANCELLED/MISSED is marked MISSED.
    - Sends WhatsApp missed notification for each newly marked missed appointment.
    """
    try:
        now = datetime.now()
        # Only mark as MISSED if the appointment was on a PREVIOUS day (not same day)
        # This lets receptionists complete/update same-day appointments without them auto-expiring
        start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        from app.database.models.appointment import Appointment, Patient, Doctor, Hospital
        stmt = select(Appointment).where(
            and_(
                Appointment.appointment_datetime < start_of_today,
                Appointment.status.in_(["SCHEDULED", "CONFIRMED", "PENDING_PAYMENT", "RESCHEDULED"])
            )
        )
        expired_appts = (await db.execute(stmt)).scalars().all()
        
        if not expired_appts:
            return

        from app.services.whatsapp import WhatsAppNotificationService
        wa_service = WhatsAppNotificationService()
        
        for appt in expired_appts:
            appt.status = "MISSED"
            appt.consultation_status = "MISSED"
            appt.updated_at = now
            
            # Dispatch WhatsApp Missed Notification
            try:
                pat_stmt = select(Patient).where(Patient.id == appt.patient_id)
                patient = (await db.execute(pat_stmt)).scalar_one_or_none()
                doc_stmt = select(Doctor).where(Doctor.id == appt.doctor_id)
                doctor = (await db.execute(doc_stmt)).scalar_one_or_none()
                hosp_stmt = select(Hospital).where(Hospital.id == appt.hospital_id)
                hospital = (await db.execute(hosp_stmt)).scalar_one_or_none()
                
                if patient and doctor and hospital:
                    details = {
                        "patient_phone": patient.phone,
                        "patient_name": f"{patient.first_name} {patient.last_name}".strip(),
                        "doctor_name": f"Dr. {doctor.first_name} {doctor.last_name}",
                        "date": appt.appointment_datetime.strftime("%Y-%m-%d"),
                        "time": appt.appointment_datetime.strftime("%I:%M %p"),
                        "hospital_name": hospital.name,
                        "hospital_id": hospital.id
                    }
                    asyncio.create_task(wa_service.send_missed_notification(details))
            except Exception as wa_err:
                logger.error(f"Failed to send missed WA msg for {appt.id}: {wa_err}")

        await db.commit()
    except Exception as e:
        logger.error(f"Error running auto-missed sweep: {str(e)}", exc_info=True)

from app.database.models.appointment import Doctor, Patient, Hospital, Department, Appointment
from app.engines.appointment import AppointmentEngine
from app.engines.scheduling import SchedulingEngine
from app.schemas.appointment import (
    AppointmentCreate, AppointmentRead, AppointmentUpdate,
    DoctorCreate, DoctorRead, PatientCreate, PatientRead,
    AvailableSlotsResponse, SlotQuery
)


class PaymentOrderRequest(BaseModel):
    appointment_id: str
    amount: int

class PaymentVerifyRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    appointment_id: str

router = APIRouter()


@router.get("/health", tags=["system"])
async def api_health_check(db: AsyncSession = Depends(get_db)):
    """API-level health check with DB ping."""
    from sqlalchemy import text
    db_status = "healthy"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        logger.error(f"API database health check failed: {str(e)}")
        db_status = f"unhealthy: {str(e)}"
        
    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "database": db_status,
        "environment": settings.ENV,
        "project": settings.PROJECT_NAME
    }


# ==========================================
# HOSPITALS LIST (Super Admin)
# ==========================================
@router.get("/hospitals", tags=["admin"])
async def list_hospitals(db: AsyncSession = Depends(get_db)):
    """Super Admin: Returns all registered hospitals with their details.
    Optimized: fetches all hospital_settings in ONE bulk query instead of 5 per-hospital queries.
    """
    from app.database.models.appointment import HospitalSetting
    from sqlalchemy import or_

    # 1. Fetch all hospitals in one query
    hospitals = (await db.execute(select(Hospital))).scalars().all()
    if not hospitals:
        return []

    hospital_ids = [h.id for h in hospitals]

    # 2. Fetch ALL settings for ALL hospitals in one query
    settings_keys = ["twilio_account_sid", "twilio_auth_token", "twilio_helpline", "whatsapp_number", "admin_username", "admin_password"]
    settings_stmt = select(HospitalSetting).where(
        HospitalSetting.hospital_id.in_(hospital_ids),
        HospitalSetting.setting_key.in_(settings_keys)
    )
    all_settings_rows = (await db.execute(settings_stmt)).scalars().all()

    # 3. Build a lookup dict: { hospital_id: { setting_key: setting_value } }
    settings_map: dict = {}
    for row in all_settings_rows:
        if row.hospital_id not in settings_map:
            settings_map[row.hospital_id] = {}
        settings_map[row.hospital_id][row.setting_key] = row.setting_value

    # 4. Assemble final result from in-memory dict (zero extra DB calls)
    result = []
    for h in hospitals:
        s = settings_map.get(h.id, {})
        result.append({
            "id": h.id,
            "name": h.name,
            "slug": h.slug,
            "phone": h.phone,
            "email": h.email,
            "address": h.address,
            "is_active": h.is_active,
            "created_at": str(h.created_at),
            "helpline": s.get("twilio_helpline") or (settings.TWILIO_PHONE_NUMBER if h.id == "hosp_default" else h.phone or ""),
            "whatsapp_number": s.get("whatsapp_number") or (settings.TWILIO_WHATSAPP_FROM if h.id == "hosp_default" else ""),
            "twilio_account_sid": s.get("twilio_account_sid") or (settings.TWILIO_ACCOUNT_SID if h.id == "hosp_default" else ""),
            "twilio_auth_token": s.get("twilio_auth_token") or (settings.TWILIO_AUTH_TOKEN if h.id == "hosp_default" else ""),
            "admin_username": s.get("admin_username", ""),
            "admin_password": s.get("admin_password", "")
        })
    return result


@router.delete("/hospitals/{hospital_id}", tags=["admin"])
async def delete_hospital(
    hospital_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Super Admin: Deletes a registered hospital and all associated records."""
    role_stmt = select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == current_user.id)
    roles = (await db.execute(role_stmt)).scalars().all()
    if "SUPER_ADMIN" not in roles and current_user.username != "shiva9532":
        raise HTTPException(status_code=403, detail="Unauthorized: Only Platform Owner can delete hospitals.")

    # 1. Fetch Hospital
    hosp_stmt = select(Hospital).where(Hospital.id == hospital_id)
    hospital = (await db.execute(hosp_stmt)).scalar_one_or_none()
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital not found")

    # 2. Prevent deleting default tenant
    if hospital_id == "hosp_default":
        raise HTTPException(status_code=400, detail="Cannot delete default hospital tenant.")

    # 3. Delete hospital
    await db.delete(hospital)
    
    # 4. Clean up users
    users_stmt = select(User).where(User.hospital_id == hospital_id)
    users = (await db.execute(users_stmt)).scalars().all()
    for u in users:
        await db.delete(u)

    await db.commit()
    return {"success": True, "message": "Hospital and associated records deleted successfully."}


@router.post("/hospitals/{hospital_id}/twilio", tags=["admin"])
async def save_hospital_twilio(
    hospital_id: str,
    account_sid: str = Form(...),
    auth_token: str = Form(...),
    helpline: str = Form(...),
    whatsapp_number: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Super Admin: Saves custom Twilio configuration parameters for a specific hospital tenant."""
    role_stmt = select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == current_user.id)
    roles = (await db.execute(role_stmt)).scalars().all()
    if "SUPER_ADMIN" not in roles and current_user.username != "shiva9532":
        raise HTTPException(status_code=403, detail="Unauthorized: Only Platform Owner can configure Twilio.")

    # Sanitize Account SID prefix
    clean_sid = account_sid.strip()
    if not clean_sid.startswith("AC"):
        clean_sid = "AC" + clean_sid
    clean_token = auth_token.strip()

    # Validate Twilio credentials live before saving
    try:
        from twilio.rest import Client as TwilioClient
        test_client = TwilioClient(clean_sid, clean_token)
        # Fetch account details to verify credentials
        test_client.api.v2010.accounts(clean_sid).fetch()
    except Exception as twilio_err:
        err_msg = str(twilio_err)
        if "401" in err_msg or "Authenticate" in err_msg or "20003" in err_msg:
            raise HTTPException(
                status_code=400,
                detail="❌ Twilio Credentials Invalid: Account SID ya Auth Token galat hai. Please Twilio Console se exact copy karke enter karein."
            )

    from app.database.models.appointment import HospitalSetting
    import uuid

    async def set_setting(key: str, val: str):
        if val is None:
            return
        stmt = select(HospitalSetting).where(HospitalSetting.hospital_id == hospital_id, HospitalSetting.setting_key == key)
        row = (await db.execute(stmt)).scalar_one_or_none()
        if row:
            row.setting_value = val
        else:
            new_row = HospitalSetting(
                id=str(uuid.uuid4()),
                hospital_id=hospital_id,
                setting_key=key,
                setting_value=val
            )
            db.add(new_row)

    await set_setting("twilio_account_sid", clean_sid)
    await set_setting("twilio_auth_token", clean_token)
    await set_setting("twilio_helpline", helpline.strip())
    if whatsapp_number is not None:
        await set_setting("whatsapp_number", whatsapp_number.strip())

    # Also update the main phone number column on the Hospital table for inbound routing
    hosp_stmt = select(Hospital).where(Hospital.id == hospital_id)
    hospital_record = (await db.execute(hosp_stmt)).scalar_one_or_none()
    if hospital_record:
        hospital_record.phone = helpline.strip()
        db.add(hospital_record)
    
    await db.commit()
    return {"success": True, "message": "Twilio configuration persisted and helpline injected successfully."}


# ==========================================
# HOSPITAL DEPARTMENTS (Dropdown lookup)
# ==========================================

@router.get("/hospital/departments", tags=["hospital"])
async def get_hospital_departments(db: AsyncSession = Depends(get_db)):
    """Returns list of all active departments for onboarding."""
    stmt = select(Department).where(Department.is_active == True)
    depts = (await db.execute(stmt)).scalars().all()
    return [{"id": d.id, "name": d.name} for d in depts]


# ==========================================
# HOSPITAL ANALYTICS & STATS (Admin Metrics)
# ==========================================

@router.get("/hospital/stats", tags=["hospital"])
async def get_hospital_stats(
    request: Request,
    target_date: Optional[str] = Query(None, description="Filter stats by date YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_user)
):
    """Returns analytics dashboard metrics for a hospital, with optional per-day filtering."""
    from fastapi import Request as _Request
    import jwt as _jwt

    # First check DB roles
    role_stmt = select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == current_admin.id)
    db_roles = (await db.execute(role_stmt)).scalars().all()

    # Also check JWT embedded role claim (for hardcoded seed users)
    jwt_role = ""
    try:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token_str = auth_header[7:]
            payload = _jwt.decode(token_str, settings.JWT_SECRET_KEY, algorithms=["HS256"])
            jwt_role = payload.get("role", "")
    except Exception:
        pass

    all_roles = list(db_roles) + ([jwt_role] if jwt_role else [])
    if "ADMIN" not in all_roles and "SUPER_ADMIN" not in all_roles:
        raise HTTPException(status_code=403, detail="Unauthorized")

    hosp_id = current_admin.hospital_id if current_admin.hospital_id else "hosp_default"
    h_stmt = select(Hospital).where(Hospital.id == hosp_id)
    hosp = (await db.execute(h_stmt)).scalar_one_or_none()

    from app.database.models.appointment import HospitalSetting
    setting_stmt = select(HospitalSetting.setting_value).where(
        HospitalSetting.hospital_id == hosp_id,
        HospitalSetting.setting_key == "twilio_helpline"
    )
    custom_helpline = (await db.execute(setting_stmt)).scalar_one_or_none()
    hospital_phone = custom_helpline or (hosp.phone if hosp else "")

    # Get all doctors
    doctors_stmt = select(Doctor, Department).join(Department, Doctor.department_id == Department.id).where(Doctor.hospital_id == hosp_id)
    doctors_db = (await db.execute(doctors_stmt)).all()

    # Get all appointments for this hospital with optional date filter
    appts_stmt = select(Appointment, Doctor).join(Doctor, Appointment.doctor_id == Doctor.id).where(Doctor.hospital_id == hosp_id)
    
    if target_date:
        try:
            from datetime import datetime as _dt
            df = _dt.strptime(target_date, "%Y-%m-%d")
            dt_start = _dt.combine(df.date(), _dt.min.time())
            dt_end = _dt.combine(df.date(), _dt.max.time())
            appts_stmt = appts_stmt.where(Appointment.appointment_datetime >= dt_start, Appointment.appointment_datetime <= dt_end)
        except ValueError:
            pass

    appts_db = (await db.execute(appts_stmt)).all()

    # Detailed status breakdown
    confirmed_appts = [(a, d) for a, d in appts_db if a.status in ["SCHEDULED", "COMPLETED", "ARRIVED", "RESCHEDULED"]]
    completed_appts = [(a, d) for a, d in appts_db if a.status == "COMPLETED"]
    missed_appts = [(a, d) for a, d in appts_db if a.status in ["MISSED", "CANCELLED"]]
    pending_appts = [(a, d) for a, d in appts_db if a.status == "PENDING_PAYMENT"]

    total_revenue = sum([d.opd_fees if d.opd_fees is not None else 500 for a, d in confirmed_appts])

    # Doctor booking counts
    doc_bookings = {}
    for doc, dept in doctors_db:
        doc_bookings[doc.id] = {
            "id": doc.id,
            "name": f"Dr. {doc.first_name} {doc.last_name}",
            "department": dept.name,
            "license": doc.license_number or "N/A",
            "is_active": doc.is_active,
            "opd_fees": doc.opd_fees if doc.opd_fees is not None else 500,
            "booking_count": 0,
            "confirmed_count": 0,
            "completed_count": 0,
            "missed_count": 0,
            "pending_count": 0,
            "revenue": 0
        }

    for appt, doc in appts_db:
        if doc.id in doc_bookings:
            doc_bookings[doc.id]["booking_count"] += 1
            if appt.status in ["SCHEDULED", "COMPLETED", "ARRIVED", "RESCHEDULED"]:
                doc_bookings[doc.id]["confirmed_count"] += 1
                doc_bookings[doc.id]["revenue"] += doc.opd_fees if doc.opd_fees else fees_map.get(doc.id, 500)
            if appt.status == "COMPLETED":
                doc_bookings[doc.id]["completed_count"] += 1
            if appt.status in ["MISSED", "CANCELLED"]:
                doc_bookings[doc.id]["missed_count"] += 1
            if appt.status == "PENDING_PAYMENT":
                doc_bookings[doc.id]["pending_count"] += 1

    return {
        "hospital_id": hosp_id,
        "hospital_name": hosp.name if hosp else "",
        "hospital_phone": hospital_phone,
        "hospital_email": hosp.email if hosp else "",
        "hospital_address": hosp.address if hosp else "",
        "total_revenue": total_revenue,
        "total_bookings": len(appts_db),
        "confirmed_bookings": len(confirmed_appts),
        "completed_bookings": len(completed_appts),
        "missed_bookings": len(missed_appts),
        "pending_bookings": len(pending_appts),
        "active_doctors_count": len(doctors_db),
        "doctors": list(doc_bookings.values())
    }


# ==========================================
# AUTHENTICATION & MULTI-SAAS ONBOARDING  
# ==========================================

@router.post("/auth/register-hospital", tags=["auth"])
async def register_hospital(
    name: str = Form(..., description="Hospital Name"),
    address: Optional[str] = Form(None, description="Hospital Address"),
    phone: str = Form(..., description="Hospital phone (for notifications/helpline)"),
    admin_username: str = Form(..., description="Admin Username"),
    admin_email: str = Form(..., description="Admin Email (Gmail)"),
    admin_password: str = Form(..., description="Admin Password"),
    db: AsyncSession = Depends(get_db)
):
    """
    Onboards a new Hospital tenant, creates a unique Hospital ID,
    and registers the Hospital Admin user.
    """
    import random

    try:
        # 1. Check if user username/email or hospital phone/slug already exists
        stmt = select(User).where((User.username == admin_username) | (User.email == admin_email))
        existing_user = (await db.execute(stmt)).scalar_one_or_none()
        if existing_user:
            raise HTTPException(status_code=400, detail="Username or email already registered.")

        # Generate hospital slug
        slug = name.lower().replace(" ", "-")
        slug = "".join([c for c in slug if c.isalnum() or c == "-"])

        # Check if hospital phone or slug is already registered
        chk_phone_stmt = select(Hospital).where((Hospital.phone == phone) | (Hospital.slug == slug))
        existing_hosp = (await db.execute(chk_phone_stmt)).scalars().first()
        if existing_hosp:
            if existing_hosp.phone == phone:
                raise HTTPException(status_code=400, detail=f"Phone number '{phone}' is already registered with hospital '{existing_hosp.name}'. Please use a different phone number.")
            if existing_hosp.slug == slug:
                raise HTTPException(status_code=400, detail=f"A hospital with name '{name}' already exists. Please choose a slightly different name.")

        # 2. Generate unique Hospital ID
        prefix = "".join([c for c in name if c.isalnum()]).upper()[:4]
        if not prefix:
            prefix = "HOSP"
        
        unique_hosp_id = None
        for _ in range(10):  # try 10 times to avoid collision
            temp_id = f"HOSP-{prefix}-{random.randint(1000, 9999)}"
            chk_stmt = select(Hospital).where(Hospital.id == temp_id)
            exists = (await db.execute(chk_stmt)).scalar_one_or_none()
            if not exists:
                unique_hosp_id = temp_id
                break
                
        if not unique_hosp_id:
            unique_hosp_id = f"HOSP-{random.randint(100000, 999999)}"

        # 3. Create Hospital
        hospital = Hospital(
            id=unique_hosp_id,
            name=name,
            slug=slug,
            address=address,
            phone=phone,
            email=admin_email,
            is_active=True
        )
        db.add(hospital)
        await db.flush()

        # Auto-seed standard departments for the new hospital
        standard_depts = [
            ("dept_med",    "General Medicine",   "Primary Care / Internal Medicine"),
            ("dept_cardio", "Cardiology",          "Heart & Cardiovascular Specialist"),
            ("dept_eye",    "Ophthalmology",       "Eye Specialist"),
            ("dept_ortho",  "Orthopedics",         "Bone & Joint Specialist"),
            ("dept_peds",   "Pediatrics",          "Child Specialist"),
            ("dept_gyn",    "Gynecology",          "Women's Health & Obstetrics"),
            ("dept_ent",    "ENT",                 "Ear, Nose & Throat Specialist"),
            ("dept_derm",   "Dermatology",         "Skin & Hair Specialist"),
            ("dept_neuro",  "Neurology",           "Brain & Nervous System Specialist"),
            ("dept_psych",  "Psychiatry",          "Mental Health Specialist"),
            ("dept_dental", "Dental",              "Dentist / Oral Health"),
            ("dept_urology","Urology",             "Urinary & Kidney Specialist"),
            ("dept_onco",   "Oncology",            "Cancer Specialist"),
            ("dept_gastro", "Gastroenterology",    "Digestive System Specialist"),
            ("dept_pulmo",  "Pulmonology",         "Lung & Respiratory Specialist"),
            ("dept_diab",   "Diabetology",         "Diabetes & Endocrinology"),
        ]
        for dept_suffix, dept_name, dept_desc in standard_depts:
            dept_id = f"{dept_suffix}_{unique_hosp_id}"
            db_dept = Department(
                id=dept_id,
                hospital_id=unique_hosp_id,
                name=dept_name,
                description=dept_desc,
                is_active=True
            )
            db.add(db_dept)
        await db.flush()

        # 4. Fetch or Create Role ADMIN
        role_stmt = select(Role).where(Role.name == "ADMIN")
        admin_role = (await db.execute(role_stmt)).scalar_one_or_none()
        if not admin_role:
            admin_role = Role(id=str(uuid.uuid4()), name="ADMIN", description="Hospital Administrator")
            db.add(admin_role)
            await db.flush()

        # 5. Create Admin User
        admin_user = User(
            id=str(uuid.uuid4()),
            hospital_id=unique_hosp_id,
            username=admin_username,
            email=admin_email,
            password_hash=hash_password(admin_password),
            is_active=True
        )
        db.add(admin_user)
        await db.flush()

        # 6. Map User to Role
        user_role = UserRole(
            id=str(uuid.uuid4()),
            user_id=admin_user.id,
            role_id=admin_role.id
        )
        db.add(user_role)
        
        # Store admin credentials
        from app.database.models.appointment import HospitalSetting
        db.add(HospitalSetting(id=str(uuid.uuid4()), hospital_id=unique_hosp_id, setting_key="admin_username", setting_value=admin_username))
        db.add(HospitalSetting(id=str(uuid.uuid4()), hospital_id=unique_hosp_id, setting_key="admin_password", setting_value=admin_password))

        await db.commit()

        # Send WhatsApp welcome message to hospital phone with all credentials
        try:
            from app.services.whatsapp import WhatsAppNotificationService
            import asyncio as _asyncio
            _wa = WhatsAppNotificationService()
            _msg = (
                f"🏥 *AURA SaaS — Hospital Registered Successfully!*\\n\\n"
                f"*Hospital Name:* {name}\\n"
                f"*Hospital ID:* {unique_hosp_id}\\n"
                f"*Address:* {address or 'N/A'}\\n\\n"
                f"🔑 *Admin Login Credentials:*\\n"
                f"• Username: {admin_username}\\n"
                f"• Password: {admin_password}\\n"
                f"• Email: {admin_email}\\n\\n"
                f"📌 Share the Hospital ID with your staff so they can login to their portals.\\n"
                f"_— AURA SaaS AI Platform_"
            )
            _asyncio.create_task(_wa.send_custom_notification(phone, _msg))
        except Exception:
            pass

        return {
            "success": True,
            "message": "Hospital registered successfully.",
            "hospital_id": unique_hosp_id,
            "hospital_slug": slug,
            "admin_username": admin_username
        }
    except Exception as e:
        print(f"Exception in register_hospital: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/hospital/register-staff", tags=["hospital"])
async def register_staff(
    role: str = Form(..., description="DOCTOR or RECEPTIONIST"),
    username: str = Form(..., description="Staff Username"),
    email: str = Form(..., description="Staff Email"),
    password: str = Form(..., description="Staff Password"),
    first_name: str = Form(..., description="Staff First Name"),
    last_name: str = Form(..., description="Staff Last Name"),
    phone: str = Form(..., description="Staff Phone Number"),
    # Doctor specific parameters (if registering a doctor)
    department_id: Optional[str] = Form(None, description="Department ID (required for DOCTOR)"),
    license_number: Optional[str] = Form(None, description="License Number (optional for DOCTOR)"),
    # Schedule fields
    schedule_days: Optional[str] = Form(None, description="Mon-Sun comma-separated values, e.g. 1,2,3,4,5"),
    schedule_start_time: Optional[str] = Form(None, description="Start time (HH:MM)"),
    schedule_end_time: Optional[str] = Form(None, description="End time (HH:MM)"),
    schedule_start_time_2: Optional[str] = Form(None, description="Session 2 start time"),
    schedule_end_time_2: Optional[str] = Form(None, description="Session 2 end time"),
    opd_fees: Optional[int] = Form(500, description="OPD Fees"),
    slot_duration_minutes: Optional[int] = Form(30, description="Slot Duration in Minutes"),
    current_admin: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Hospital Admin endpoint to add Doctors or Receptionists.
    Automatically links staff members to the admin's hospital_id, and dispatches credentials via WhatsApp.
    """
    from app.services.whatsapp import WhatsAppNotificationService
    from sqlalchemy import and_, or_

    # 1. Fetch admin roles to verify authorization
    role_stmt = select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == current_admin.id)
    roles = (await db.execute(role_stmt)).scalars().all()
    if "ADMIN" not in roles:
        raise HTTPException(status_code=403, detail="Only Hospital Admins can register staff.")

    try:
        # 2. Check if username or email already exists
        stmt = select(User).where((User.username == username) | (User.email == email))
        existing = (await db.execute(stmt)).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=400, detail="Username or email already registered.")

        # 3. Fetch or Create target Role (DOCTOR or RECEPTIONIST)
        role_name = role.upper()
        if role_name not in ["DOCTOR", "RECEPTIONIST"]:
            raise HTTPException(status_code=400, detail="Invalid role. Select DOCTOR or RECEPTIONIST.")

        target_role_stmt = select(Role).where(Role.name == role_name)
        target_role = (await db.execute(target_role_stmt)).scalar_one_or_none()
        if not target_role:
            target_role = Role(id=str(uuid.uuid4()), name=role_name, description=f"Hospital {role_name.capitalize()}")
            db.add(target_role)
            await db.flush()

        # 4. Create User Record
        staff_user = User(
            id=str(uuid.uuid4()),
            hospital_id=current_admin.hospital_id,
            username=username,
            email=email,
            password_hash=hash_password(password),
            is_active=True
        )
        db.add(staff_user)
        await db.flush()

        # 5. Map User to Role
        user_role = UserRole(
            id=str(uuid.uuid4()),
            user_id=staff_user.id,
            role_id=target_role.id
        )
        db.add(user_role)
        await db.flush()

        # Store staff plain text password
        from app.database.models.appointment import HospitalSetting
        db.add(HospitalSetting(
            id=str(uuid.uuid4()),
            hospital_id=current_admin.hospital_id,
            setting_key=f"staff_pwd_{staff_user.id}",
            setting_value=password
        ))

        # 6. If role is DOCTOR, create Doctor record
        if role_name == "DOCTOR":
            if not department_id:
                raise HTTPException(status_code=400, detail="department_id is required when role is DOCTOR.")
            
            # Verify department belongs to the hospital or auto-create if missing
            dept_stmt = select(Department).where(
                and_(
                    or_(Department.id == department_id, Department.name == department_id),
                    Department.hospital_id == current_admin.hospital_id
                )
            )
            dept = (await db.execute(dept_stmt)).scalar_one_or_none()
            if not dept:
                dept = Department(
                    id=str(uuid.uuid4()),
                    hospital_id=current_admin.hospital_id,
                    name=department_id,
                    description=f"{department_id} department",
                    is_active=True
                )
                db.add(dept)
                await db.flush()
                
            real_department_id = dept.id

            doctor = Doctor(
                id=staff_user.id,  # Use same ID for unified joins
                hospital_id=current_admin.hospital_id,
                department_id=real_department_id,
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                license_number=license_number,
                opd_fees=opd_fees,
                hashed_password=hash_password(password),
                is_active=True
            )
            db.add(doctor)
            await db.flush()

            # Save schedule details if provided
            _sst = (schedule_start_time or "").strip()
            _set = (schedule_end_time or "").strip()
            if schedule_days and _sst and _set:
                from datetime import time
                from app.database.models.appointment import DoctorSchedule
                
                def is_valid_session_str(val: Optional[str]) -> bool:
                    if not val:
                        return False
                    return val.strip().lower() not in ["", "null", "undefined", "--:--"]

                def parse_time(value: Optional[str]) -> Optional[time]:
                    if not value:
                        return None
                    val_clean = value.strip()
                    if not val_clean or val_clean in ["", "null", "undefined", "--:--"]:
                        return None
                    try:
                        parts = val_clean.split(':')
                        return time(int(parts[0]), int(parts[1]))
                    except Exception as e:
                        raise ValueError(f"Invalid time format: '{value}'")
                
                norm_s1_start = _sst
                norm_s1_end = _set
                norm_s2_start = schedule_start_time_2.strip() if is_valid_session_str(schedule_start_time_2) else None
                norm_s2_end = schedule_end_time_2.strip() if is_valid_session_str(schedule_end_time_2) else None

                try:
                    t_start = parse_time(norm_s1_start)
                    t_end = parse_time(norm_s1_end)
                    t_start_2 = parse_time(norm_s2_start)
                    t_end_2 = parse_time(norm_s2_end)

                    days = [int(d.strip()) for d in schedule_days.split(',') if d.strip().isdigit()]
                    for day in days:
                        s1 = DoctorSchedule(
                            id=str(uuid.uuid4()),
                            doctor_id=doctor.id,
                            day_of_week=day,
                            start_time=t_start,
                            end_time=t_end,
                            slot_duration_minutes=slot_duration_minutes or 30
                        )
                        db.add(s1)
                        if t_start_2 and t_end_2:
                            s2 = DoctorSchedule(
                                id=str(uuid.uuid4()),
                                doctor_id=doctor.id,
                                day_of_week=day,
                                start_time=t_start_2,
                                end_time=t_end_2,
                                slot_duration_minutes=slot_duration_minutes or 30
                            )
                            db.add(s2)
                except Exception as se:
                    logger.error(f"Error saving doctor schedule: {str(se)}")
                    raise HTTPException(status_code=400, detail="Invalid schedule parameters provided.")

        # 7. Fetch hospital details for onboarding message
        hosp_stmt = select(Hospital).where(Hospital.id == current_admin.hospital_id)
        hospital = (await db.execute(hosp_stmt)).scalar_one_or_none()
        hospital_name = hospital.name if hospital else "CP Tiwari Hospital"

        await db.commit()
    except Exception as exc:
        await db.rollback()
        logger.error(f"Failed to register staff: {str(exc)}")
        if isinstance(exc, HTTPException):
            raise exc
        raise HTTPException(status_code=500, detail="Failed to register staff due to internal error.")

    # 8. Send WhatsApp notification with credentials
    wa_service = WhatsAppNotificationService()
    wa_details = {
        "phone": phone,
        "staff_name": f"{first_name} {last_name}".strip(),
        "hospital_name": hospital_name,
        "hospital_id": current_admin.hospital_id if current_admin.hospital_id else "hosp_default",
        "role": role_name,
        "username": username,
        "password": password,
        "login_url": f"{settings.PAYMENT_BASE_URL.split('/appointment')[0]}/login"
    }
    
    # Run synchronously to guarantee dispatch and capture logs
    try:
        await wa_service.send_staff_credentials_notification(wa_details)
    except Exception as wa_err:
        logger.error(f"Failed to send staff credentials via WhatsApp: {str(wa_err)}")

    return {
        "success": True,
        "message": f"{role_name.capitalize()} staff created successfully.",
        "username": username,
        "hospital_id": current_admin.hospital_id
    }


@router.post("/auth/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    """Authenticates admin console, receptionist, and doctor users, and yields secure JWT tokens with role scope."""
    # 1. Platform Owner Login (Super Admin)
    if form_data.username == "shiva9532" and form_data.password == "#@112233":
        access_token = create_access_token(data={
            "sub": "shiva9532",
            "role": "SUPER_ADMIN",
            "hospital_id": "super_admin",
            "hospital_slug": ""
        })
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "role": "SUPER_ADMIN",
            "hospital_id": "super_admin",
            "hospital_slug": "",
            "username": "shiva9532",
            "user_id": "shiva9532"
        }

    # 2. Existing Hospital Admin Login (CP Tiwari Hospital)
    if form_data.username == "admin_cp" and form_data.password == "password123":
        access_token = create_access_token(data={
            "sub": "admin_cp",
            "role": "ADMIN",
            "hospital_id": "hosp_default",
            "hospital_slug": "cp-tiwari-hospital"
        })
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "role": "ADMIN",
            "hospital_id": "hosp_default",
            "hospital_slug": "cp-tiwari-hospital",
            "username": "admin_cp",
            "user_id": "admin_cp"
        }

    # 3. Existing Hospital Doctor Login (CP Tiwari Hospital)
    if form_data.username == "doctor_cp" and form_data.password == "password123":
        access_token = create_access_token(data={
            "sub": "doctor_cp",
            "role": "DOCTOR",
            "hospital_id": "hosp_default",
            "hospital_slug": "cp-tiwari-hospital"
        })
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "role": "DOCTOR",
            "hospital_id": "hosp_default",
            "hospital_slug": "cp-tiwari-hospital",
            "username": "doctor_cp",
            "user_id": "doctor_cp"
        }

    # 4. Existing Hospital Receptionist Login (CP Tiwari Hospital)
    if form_data.username == "receptionist_cp" and form_data.password == "password123":
        access_token = create_access_token(data={
            "sub": "receptionist_cp",
            "role": "RECEPTIONIST",
            "hospital_id": "hosp_default",
            "hospital_slug": "cp-tiwari-hospital"
        })
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "role": "RECEPTIONIST",
            "hospital_id": "hosp_default",
            "hospital_slug": "cp-tiwari-hospital",
            "username": "receptionist_cp",
            "user_id": "receptionist_cp"
        }

    stmt = select(User).where(User.username == form_data.username, User.is_active == True)
    user = (await db.execute(stmt)).scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.password_hash):
        # Admin bootstrapping logic (only if no users exist in database)
        user_count_stmt = select(User)
        users_exist = (await db.execute(user_count_stmt)).scalars().all()
        if not users_exist and form_data.username == "admin":
            new_admin = User(
                id="usr_admin",
                username="admin",
                email="admin@hospital.com",
                password_hash=hash_password(form_data.password),
                is_active=True
            )
            db.add(new_admin)
            await db.commit()
            access_token = create_access_token(data={"sub": "admin", "role": "ADMIN", "hospital_id": "hosp_default"})
            return {"access_token": access_token, "token_type": "bearer", "role": "ADMIN", "hospital_id": "hosp_default", "user_id": "usr_admin"}

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Load roles of the user
    role_stmt = select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == user.id)
    roles = (await db.execute(role_stmt)).scalars().all()
    user_role = roles[0] if roles else "RECEPTIONIST"  # fallback

    # Load hospital details (if linked)
    hospital_slug = ""
    if user.hospital_id:
        hosp_stmt = select(Hospital).where(Hospital.id == user.hospital_id)
        hosp = (await db.execute(hosp_stmt)).scalar_one_or_none()
        if hosp:
            hospital_slug = hosp.slug

    resolved_hosp_id = user.hospital_id
    if user_role == "SUPER_ADMIN":
        resolved_hosp_id = "super_admin"

    access_token = create_access_token(data={
        "sub": user.username,
        "role": user_role,
        "hospital_id": resolved_hosp_id,
        "hospital_slug": hospital_slug
    })
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user_role,
        "hospital_id": resolved_hosp_id,
        "hospital_slug": hospital_slug,
        "username": user.username,
        "user_id": user.id
    }


@router.post("/super-admin/register", tags=["super_admin"])
async def register_super_admin(
    username: str = Form(..., description="Super Admin Username"),
    email: str = Form(..., description="Super Admin Email"),
    password: str = Form(..., description="Super Admin Password"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Registers a new database-backed Platform Owner (SUPER_ADMIN) account.
    Restricted to existing SUPER_ADMINs.
    """
    is_super_admin = current_user.username == "shiva9532"
    if not is_super_admin:
        role_stmt = select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == current_user.id)
        roles = (await db.execute(role_stmt)).scalars().all()
        if "SUPER_ADMIN" in roles:
            is_super_admin = True

    if not is_super_admin:
        raise HTTPException(status_code=403, detail="Only Platform Owners can register other Platform Owners.")

    stmt = select(User).where((User.username == username) | (User.email == email))
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Username or email already registered.")

    role_name = "SUPER_ADMIN"
    target_role_stmt = select(Role).where(Role.name == role_name)
    target_role = (await db.execute(target_role_stmt)).scalar_one_or_none()
    if not target_role:
        target_role = Role(id="role_super_admin", name=role_name, description="Platform Owner")
        db.add(target_role)
        await db.flush()

    new_user = User(
        id=str(uuid.uuid4()),
        hospital_id=None,
        username=username,
        email=email,
        password_hash=hash_password(password),
        is_active=True
    )
    db.add(new_user)
    await db.flush()

    user_role = UserRole(
        id=str(uuid.uuid4()),
        user_id=new_user.id,
        role_id=target_role.id
    )
    db.add(user_role)
    await db.commit()

    return {
        "success": True,
        "message": "New Platform Owner account registered successfully.",
        "username": username
    }


# ==========================================
# APPOINTMENT MANAGEMENT
# ==========================================

@router.get("/appointments", tags=["appointments"])
async def list_all_appointments(
    doctor_id: Optional[str] = None,
    status: Optional[str] = Query(None, description="Filter by status: SCHEDULED, PENDING_PAYMENT, ARRIVED, MISSED, COMPLETED, CANCELLED"),
    search: Optional[str] = Query(None, description="Search by patient name or phone"),
    date_from: Optional[str] = Query(None, description="Filter from date YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="Filter to date YYYY-MM-DD"),
    limit: int = Query(100, ge=1, le=500, description="Max records to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieves appointments with pagination, filtering, and search support."""
    from sqlalchemy import and_, or_, cast, String
    from datetime import datetime as _dt
    from app.database.models.appointment import ConsultationNote

    await auto_update_missed_appointments(db)

    stmt = (
        select(Appointment, Patient, Doctor, Department, ConsultationNote)
        .join(Patient, Appointment.patient_id == Patient.id)
        .join(Doctor, Appointment.doctor_id == Doctor.id)
        .join(Department, Doctor.department_id == Department.id)
        .outerjoin(ConsultationNote, Appointment.id == ConsultationNote.appointment_id)
    )

    # Scope by hospital
    if doctor_id:
        stmt = stmt.where(Appointment.doctor_id == doctor_id)
    elif current_user.hospital_id:
        stmt = stmt.where(Appointment.hospital_id == current_user.hospital_id)

    # Status filter
    if status:
        stmt = stmt.where(Appointment.status == status.upper())

    # Date range filter
    if date_from:
        try:
            df = _dt.strptime(date_from, "%Y-%m-%d")
            stmt = stmt.where(Appointment.appointment_datetime >= df)
        except ValueError:
            pass
    if date_to:
        try:
            dt = _dt.strptime(date_to, "%Y-%m-%d")
            stmt = stmt.where(Appointment.appointment_datetime <= dt)
        except ValueError:
            pass

    # Search by patient name or phone
    if search:
        search_term = f"%{search}%"
        stmt = stmt.where(
            or_(
                Patient.first_name.ilike(search_term),
                Patient.last_name.ilike(search_term),
                Patient.phone.ilike(search_term)
            )
        )

    # Order newest first, apply pagination
    stmt = stmt.order_by(Appointment.appointment_datetime.desc()).limit(limit).offset(offset)

    results = (await db.execute(stmt)).all()

    appts = []
    for appt, patient, doctor, dept, note in results:
        # Calculate age from date_of_birth
        patient_age = None
        if patient.date_of_birth:
            from datetime import date as date_type
            today = date_type.today()
            dob = patient.date_of_birth
            patient_age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            # Skip default DOB 1990-01-01 stored for users who registered without age
            if dob.year == 1990 and dob.month == 1 and dob.day == 1:
                patient_age = None

        appts.append({
            "id": appt.id,
            "patient_id": patient.id,
            "patient_name": f"{patient.first_name} {patient.last_name}".strip(),
            "patient_phone": patient.phone,
            "patient_age": patient_age,
            "booked_by_name": appt.booked_by_name if hasattr(appt, 'booked_by_name') else None,
            "doctor_id": doctor.id,
            "doctor_name": f"Dr. {doctor.first_name} {doctor.last_name}",
            "department_name": dept.name,
            "appointment_datetime": appt.appointment_datetime.isoformat(),
            "reason": appt.reason,
            "payment_status": appt.payment_status,
            "consultation_status": appt.consultation_status,
            "status": appt.status,
            "source": appt.source if hasattr(appt, 'source') else "MANUAL",
            "clinical_notes": note.clinical_notes if note else None,
            "prescription": note.prescription if note else None,
            "follow_up_date": note.follow_up_date.isoformat() if note and note.follow_up_date else None,
            "consultation_completed_at": note.created_at.isoformat() if note and note.created_at else None,
            "created_at": appt.created_at.isoformat() if appt.created_at else None
        })
    return appts



@router.post("/appointments", response_model=AppointmentRead)
async def create_appointment(
    payload: AppointmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Creates a new patient booking, verifying slots availability."""
    from app.database.models.appointment import Appointment, Hospital, Patient, Doctor

    # Idempotency check: if active appointment already exists with same patient, doctor, and time, return it immediately.
    try:
        existing_stmt = select(Appointment).where(
            Appointment.patient_id == payload.patient_id,
            Appointment.doctor_id == payload.doctor_id,
            Appointment.appointment_datetime == payload.appointment_datetime,
            Appointment.status.in_(["SCHEDULED", "PENDING_PAYMENT"])
        )
        existing = (await db.execute(existing_stmt)).scalar_one_or_none()
        if existing:
            logger.info(f"Idempotent booking triggered: Appointment already exists for patient={payload.patient_id}, doctor={payload.doctor_id}, time={payload.appointment_datetime}. Returning cached record.")
            return existing
    except Exception as ie:
        logger.error(f"Error during idempotency lookup: {str(ie)}")
        # Continue to book anyway, but safely
        
    try:
        engine = AppointmentEngine(db)
        res = await engine.book_appointment(
            hospital_id=payload.hospital_id,
            patient_id=payload.patient_id,
            doctor_id=payload.doctor_id,
            appointment_datetime=payload.appointment_datetime,
            reason=payload.reason or "General Consultation",
            source="PORTAL"
        )
        if res.get("code") != "BOOKING_SUCCESS":
            raise HTTPException(status_code=400, detail=res.get("message", "Booking failed"))
        
        # Retrieve the flushed appointment from db to return it
        appt_stmt = select(Appointment).where(Appointment.id == res["appointment_id"])
        appt = (await db.execute(appt_stmt)).scalar_one_or_none()
        if not appt:
            raise HTTPException(status_code=500, detail="Appointment created but could not be retrieved")
            
        # Commit first
        await db.commit()
        logger.info(f"Booking successfully committed to DB. Appointment ID: {appt.id}")
    except Exception as ex:
        await db.rollback()
        logger.error(f"Error during appointment creation database transaction: {str(ex)}")
        if isinstance(ex, HTTPException):
            raise ex
        raise HTTPException(status_code=500, detail=f"Booking failed due to internal error: {str(ex)}")
        
    # Send WhatsApp confirmation to patient
    warning_code = None
    try:
        from twilio.rest import Client
        from twilio.base.exceptions import TwilioRestException
        
        # Log hospital whatsapp config
        logger.info(f"Twilio Config: ACCOUNT_SID={settings.TWILIO_ACCOUNT_SID}, SENDER={settings.TWILIO_WHATSAPP_FROM}")
        
        # Resolve names and phone numbers
        h_stmt = select(Hospital).where(Hospital.id == appt.hospital_id)
        hospital = (await db.execute(h_stmt)).scalar_one_or_none()
        h_name = hospital.name if hospital else "Hospital"
        
        p_stmt = select(Patient).where(Patient.id == appt.patient_id)
        patient = (await db.execute(p_stmt)).scalar_one_or_none()
        p_name = f"{patient.first_name} {patient.last_name}".strip() if patient else "Patient"
        p_phone = patient.phone if patient else ""
        
        d_stmt = select(Doctor).where(Doctor.id == appt.doctor_id)
        doctor = (await db.execute(d_stmt)).scalar_one_or_none()
        d_name = f"Dr. {doctor.first_name} {doctor.last_name}" if doctor else "Doctor"

        # Formulate to and from numbers
        raw_to = p_phone.strip()
        if raw_to:
            if not raw_to.startswith("+"):
                if len(raw_to) == 10:
                    raw_to = "+91" + raw_to
                else:
                    raw_to = "+" + raw_to
            final_to = f"whatsapp:{raw_to}"
        else:
            final_to = ""
            
        final_from = settings.TWILIO_WHATSAPP_FROM
        if final_from and not final_from.startswith("whatsapp:"):
            final_from = f"whatsapp:{final_from}"
            
        # Log final to/from numbers
        logger.info(f"Sending WhatsApp message: from_={final_from}, to={final_to}")
        
        if final_to and final_from:
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            
            # Format message body
            appt_display = appt.appointment_datetime.strftime("%d %b %Y, %I:%M %p")
            appt_id_short = appt.id[-8:]
            
            import os
            railway_domain = os.environ.get("RAILWAY_STATIC_URL") or os.environ.get("RAILWAY_PUBLIC_DOMAIN")
            if railway_domain:
                base_url = f"https://{railway_domain}" if not railway_domain.startswith("http") else railway_domain.rstrip('/')
            else:
                base_url = settings.TWILIO_WEBHOOK_URL.rstrip('/') if settings.TWILIO_WEBHOOK_URL else settings.PAYMENT_BASE_URL.rstrip('/')
            
            payment_link = f"{base_url}/payment/checkout?appt={appt_id_short}"
            
            message_body = (
                f"🏥 *{h_name}*\n"
                f"✅ *आपकी अपॉइंटमेंट बुक हो गई!*\n\n"
                f"👤 *नाम:* {p_name}\n"
                f"👨‍⚕️ *डॉक्टर:* {d_name}\n"
                f"📅 *तारीख व समय:* {appt_display}\n"
                f"🩺 *समस्या:* {appt.reason}\n"
                f"🆔 *Appointment ID:* {appt_id_short}\n\n"
                f"💳 *Payment करें और अपॉइंटमेंट Confirm करें:*\n"
                f"{payment_link}\n\n"
                f"_Payment के बाद आपकी अपॉइंटमेंट confirmed हो जाएगी।_\n"
                f"_किसी सहायता के लिए हमें call करें।_"
            )
            
            try:
                # Sync send message
                message = client.messages.create(
                    body=message_body,
                    from_=final_from,
                    to=final_to
                )
                # Log Twilio response SID
                logger.info(f"Twilio response message sent successfully. SID: {message.sid}")
            except TwilioRestException as tre:
                # Log Twilio exception body
                logger.error(f"TwilioRestException caught during synchronous send: code={tre.code}, status={tre.status}, msg={tre.msg}")
                # Check for sandbox user not joined error (e.g. code 63012) or general opt-in error
                if tre.code == 63012 or "sandbox" in str(tre.msg).lower() or "not opted in" in str(tre.msg).lower():
                    warning_code = "BOOKED_BUT_WHATSAPP_NOT_DELIVERED_SANDBOX"
                else:
                    warning_code = f"TWILIO_ERROR_{tre.code}"
            except Exception as inner_err:
                logger.error(f"Unexpected inner exception in Twilio client send: {str(inner_err)}")
                warning_code = "WHATSAPP_SEND_FAILED"
    except Exception as wa_err:
        logger.error(f"Twilio client initialization or formatting error: {str(wa_err)}")
        warning_code = "WHATSAPP_CONFIG_ERROR"

    if warning_code:
        appt.warning = warning_code
        logger.warning(f"Appointment warning set: {warning_code}")
        
    return appt


@router.delete("/appointments/{appointment_id}", response_model=AppointmentRead)
async def cancel_appointment(
    appointment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cancels an existing appointment."""
    engine = AppointmentEngine(db)
    res = await engine.cancel_appointment(appointment_id)
    if res.get("code") not in ["CANCELLED", "ALREADY_CANCELLED"]:
        raise HTTPException(status_code=400, detail=res.get("message", "Cancellation failed"))
    
    # Retrieve the cancelled appointment to return it
    from app.database.models.appointment import Appointment
    appt_stmt = select(Appointment).where(Appointment.id == appointment_id)
    appt = (await db.execute(appt_stmt)).scalar_one_or_none()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return appt


@router.get("/appointments/availability", response_model=AvailableSlotsResponse)
async def get_doctor_availability(
    doctor_id: str,
    target_date: date,
    db: AsyncSession = Depends(get_db)
):
    """Public query endpoint to fetch free booking slots for a specific doctor."""
    scheduler = SchedulingEngine(db)
    slots = await scheduler.get_available_slots(doctor_id, target_date)
    return AvailableSlotsResponse(doctor_id=doctor_id, slots=slots)


# ==========================================
# DOCTORS MANAGEMENT
# ==========================================

@router.post("/doctors", response_model=DoctorRead)
async def create_doctor(
    payload: DoctorCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Registers a new doctor profile under the clinical network."""
    import uuid
    from app.database.models.appointment import DoctorSpecialization

    doc_id = str(uuid.uuid4())
    doctor = Doctor(
        id=doc_id,
        hospital_id=payload.hospital_id,
        department_id=payload.department_id,
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=payload.email,
        phone=payload.phone,
        license_number=payload.license_number,
        is_active=True
    )
    db.add(doctor)

    for spec in payload.specializations:
        from app.database.models.appointment import DoctorSpecialization
        spec_row = DoctorSpecialization(
            id=str(uuid.uuid4()),
            doctor_id=doc_id,
            specialization=spec
        )
        db.add(spec_row)

    await db.commit()
    await db.refresh(doctor)
    return doctor


@router.get("/doctors", tags=["hospital"])
async def list_doctors(
    hospital_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieves all active doctor listings with schedules and details."""
    from app.database.models.appointment import DoctorSchedule
    role_stmt = select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == current_user.id)
    roles = (await db.execute(role_stmt)).scalars().all()

    h_id = current_user.hospital_id if current_user.hospital_id else "hosp_default"
    if "SUPER_ADMIN" in roles and hospital_id:
        h_id = hospital_id

    # Fetch passwords from settings
    from app.database.models.appointment import HospitalSetting
    pwd_stmt = select(HospitalSetting).where(
        HospitalSetting.hospital_id == h_id,
        HospitalSetting.setting_key.like("staff_pwd_%")
    )
    pwd_rows = (await db.execute(pwd_stmt)).scalars().all()
    pwd_dict = {row.setting_key.replace("staff_pwd_", ""): row.setting_value for row in pwd_rows}

    stmt = (
        select(Doctor, Department, User)
        .join(Department, Doctor.department_id == Department.id)
        .outerjoin(User, Doctor.id == User.id)
        .where(Doctor.is_active == True)
    )

    if "SUPER_ADMIN" not in roles:
        stmt = stmt.where(Doctor.hospital_id == h_id)
    elif hospital_id:
        stmt = stmt.where(Doctor.hospital_id == hospital_id)

    results = (await db.execute(stmt)).all()
    
    doctors_info = []
    for doc, dept, u in results:
        # Get schedules
        sched_stmt = select(DoctorSchedule).where(DoctorSchedule.doctor_id == doc.id)
        schedules = (await db.execute(sched_stmt)).scalars().all()
        
        # day of week list
        work_days = [s.day_of_week for s in schedules]
        
        # Timing representation in Hindi (Dynamic)
        timing_str = ""
        if schedules:
            from collections import defaultdict
            session_times = defaultdict(list)
            for s in schedules:
                time_range = f"{s.start_time.strftime('%I:%M %p').lstrip('0')} - {s.end_time.strftime('%I:%M %p').lstrip('0')}"
                session_times[time_range].append(s.day_of_week)
            
            parts = []
            for tr, days_list in session_times.items():
                days_list.sort()
                day_names_map = {1: "सोम", 2: "मंगल", 3: "बुध", 4: "गुरु", 5: "शुक्र", 6: "शनि", 7: "रवि"}
                if len(days_list) >= 5 and days_list == list(range(days_list[0], days_list[0] + len(days_list))):
                    days_str = f"{day_names_map.get(days_list[0])}–{day_names_map.get(days_list[-1])}"
                else:
                    days_str = ", ".join([day_names_map.get(d, str(d)) for d in days_list])
                parts.append(f"{days_str}, {tr}")
            timing_str = " | ".join(parts)
        else:
            # Fallback for seeded doctors
            timing_str = "सोम–शुक्र, 10:00 AM - 01:00 PM | 02:00 PM - 05:00 PM"
            work_days = [1, 2, 3, 4, 5]

        doctors_info.append({
            "id": doc.id,
            "hospital_id": doc.hospital_id,
            "department_id": doc.department_id,
            "department_name": dept.name,
            "first_name": doc.first_name,
            "last_name": doc.last_name,
            "email": doc.email,
            "phone": doc.phone,
            "license_number": doc.license_number,
            "is_active": doc.is_active,
            "opd_fees": doc.opd_fees,
            "timings": timing_str,
            "work_days": work_days,
            "username": u.username if u else (doc.email.split('@')[0] if doc.email else doc.id),
            "password": pwd_dict.get(doc.id, "••••••••")
        })
    return doctors_info


# ==========================================
# HOSPITAL STAFF LISTING (for Platform Owner drilldown)
# ==========================================

@router.get("/hospital/staff", tags=["hospital"])
async def list_hospital_staff(
    hospital_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns all staff (doctors + receptionists) for a hospital.
    Super Admin can pass hospital_id param to see any hospital's staff.
    Admins see their own hospital automatically.
    """
    # Determine which hospital to query
    role_stmt = select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == current_user.id)
    roles = (await db.execute(role_stmt)).scalars().all()

    if "SUPER_ADMIN" in roles or current_user.username == "shiva9532":
        target_hospital_id = hospital_id  # super admin can view any
    else:
        target_hospital_id = current_user.hospital_id

    if not target_hospital_id:
        return {"doctors": [], "receptionists": []}

    # Fetch passwords from settings
    from app.database.models.appointment import HospitalSetting
    pwd_stmt = select(HospitalSetting).where(
        HospitalSetting.hospital_id == target_hospital_id,
        HospitalSetting.setting_key.like("staff_pwd_%")
    )
    pwd_rows = (await db.execute(pwd_stmt)).scalars().all()
    pwd_dict = {row.setting_key.replace("staff_pwd_", ""): row.setting_value for row in pwd_rows}

    # 1. Get Doctors
    doc_stmt = select(Doctor, Department).join(
        Department, Doctor.department_id == Department.id
    ).where(Doctor.hospital_id == target_hospital_id, Doctor.is_active == True)
    doc_results = (await db.execute(doc_stmt)).all()

    doctors = []
    for doc, dept in doc_results:
        # Get username from users table (Doctor id == User id)
        user_stmt = select(User).where(User.id == doc.id)
        user = (await db.execute(user_stmt)).scalar_one_or_none()
        
        # Get schedules
        from app.database.models.appointment import DoctorSchedule
        sched_stmt = select(DoctorSchedule).where(DoctorSchedule.doctor_id == doc.id)
        schedules = (await db.execute(sched_stmt)).scalars().all()
        
        work_days = [s.day_of_week for s in schedules]
        slot_duration = schedules[0].slot_duration_minutes if schedules else 30
        
        # Timing representation in Hindi (Dynamic)
        timing_str = ""
        if schedules:
            from collections import defaultdict
            session_times = defaultdict(list)
            for s in schedules:
                time_range = f"{s.start_time.strftime('%I:%M %p').lstrip('0')} - {s.end_time.strftime('%I:%M %p').lstrip('0')}"
                session_times[time_range].append(s.day_of_week)
            
            parts = []
            for tr, days_list in session_times.items():
                days_list.sort()
                day_names_map = {1: "सोम", 2: "मंगल", 3: "बुध", 4: "गुरु", 5: "शुक्र", 6: "शनि", 7: "रवि"}
                if len(days_list) >= 5 and days_list == list(range(days_list[0], days_list[0] + len(days_list))):
                    days_str = f"{day_names_map.get(days_list[0])}–{day_names_map.get(days_list[-1])}"
                else:
                    days_str = ", ".join([day_names_map.get(d, str(d)) for d in days_list])
                parts.append(f"{days_str}, {tr}")
            timing_str = " | ".join(parts)
        else:
            timing_str = ""

        doctors.append({
            "id": doc.id,
            "username": user.username if user else "",
            "password": pwd_dict.get(doc.id, "••••••••"),
            "email": doc.email,
            "first_name": doc.first_name,
            "last_name": doc.last_name,
            "phone": doc.phone or "",
            "department": dept.name,
            "license_number": doc.license_number or "",
            "opd_fees": doc.opd_fees or 0,
            "is_active": doc.is_active,
            "work_days": work_days,
            "slot_duration_minutes": slot_duration,
            "timings": timing_str
        })

    # 2. Get Receptionists - query users with RECEPTIONIST role in this hospital
    recep_role_stmt = select(Role).where(Role.name == "RECEPTIONIST")
    recep_role = (await db.execute(recep_role_stmt)).scalar_one_or_none()

    receptionists = []
    if recep_role:
        recep_stmt = select(User).join(
            UserRole, UserRole.user_id == User.id
        ).where(
            UserRole.role_id == recep_role.id,
            User.hospital_id == target_hospital_id,
            User.is_active == True
        )
        recep_results = (await db.execute(recep_stmt)).scalars().all()
        for u in recep_results:
            receptionists.append({
                "id": u.id,
                "username": u.username,
                "password": pwd_dict.get(u.id, "••••••••"),
                "email": u.email,
                "first_name": u.first_name or "",
                "last_name": u.last_name or "",
                "phone": "",
                "is_active": u.is_active,
            })

    return {"doctors": doctors, "receptionists": receptionists}


# ==========================================
# LEAVES & STAFF CRUD MANAGEMENT
# ==========================================

from app.schemas.appointment import DoctorLeaveCreate, DoctorLeaveRead
from app.database.models.appointment import DoctorLeave

@router.post("/hospital/leaves", response_model=DoctorLeaveRead, tags=["hospital"])
async def create_doctor_leave(
    payload: DoctorLeaveCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Allows Doctor or Admin to register a date/range of leave."""
    import uuid
    hosp_id = current_user.hospital_id if current_user.hospital_id else "hosp_default"
    
    # Auto-detect doctor if current user is a DOCTOR
    role_stmt = select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == current_user.id)
    roles = (await db.execute(role_stmt)).scalars().all()
    if "DOCTOR" in roles:
        doc_stmt_curr = select(Doctor).where(Doctor.id == current_user.id)
        curr_doc = (await db.execute(doc_stmt_curr)).scalar_one_or_none()
        if curr_doc:
            payload.doctor_id = curr_doc.id

    doc_stmt = select(Doctor).where(Doctor.id == payload.doctor_id)
    doctor = (await db.execute(doc_stmt)).scalar_one_or_none()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    
    if doctor.hospital_id != hosp_id and current_user.username != "super_admin":
        raise HTTPException(status_code=403, detail="Unauthorized hospital access")
    
    leave_id = str(uuid.uuid4())
    new_leave = DoctorLeave(
        id=leave_id,
        doctor_id=payload.doctor_id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        reason=payload.reason,
        status=payload.status or "PENDING"
    )
    db.add(new_leave)
    await db.commit()
    await db.refresh(new_leave)
    return new_leave


@router.get("/hospital/leaves", tags=["hospital"])
async def list_doctor_leaves(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetches all registered doctor leaves for the hospital."""
    hosp_id = current_user.hospital_id if current_user.hospital_id else "hosp_default"
    stmt = select(DoctorLeave, Doctor).join(Doctor, DoctorLeave.doctor_id == Doctor.id).where(Doctor.hospital_id == hosp_id)
    results = (await db.execute(stmt)).all()
    
    leaves_info = []
    for leave, doc in results:
        leaves_info.append({
            "id": leave.id,
            "doctor_id": doc.id,
            "doctor_name": f"Dr. {doc.first_name} {doc.last_name}",
            "start_date": leave.start_date.isoformat(),
            "end_date": leave.end_date.isoformat(),
            "reason": leave.reason,
            "status": leave.status,
            "created_at": leave.created_at.isoformat()
        })
    return leaves_info


@router.delete("/hospital/leaves/{leave_id}", tags=["hospital"])
async def delete_doctor_leave(
    leave_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cancels/deletes a doctor leave record."""
    hosp_id = current_user.hospital_id if current_user.hospital_id else "hosp_default"
    stmt = select(DoctorLeave).join(Doctor, DoctorLeave.doctor_id == Doctor.id).where(
        (DoctorLeave.id == leave_id) & (Doctor.hospital_id == hosp_id)
    )
    leave = (await db.execute(stmt)).scalar_one_or_none()
    if not leave:
        raise HTTPException(status_code=404, detail="Leave record not found or unauthorized")
    
    await db.delete(leave)
    await db.commit()
    return {"status": "success", "message": "Leave deleted successfully"}


@router.post("/hospital/leaves/{leave_id}/approve", tags=["hospital"])
async def approve_doctor_leave(
    leave_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Approves a pending doctor leave request (Admin or Receptionist only)."""
    # Verify current user is Admin or Receptionist
    role_stmt = select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == current_user.id)
    roles = (await db.execute(role_stmt)).scalars().all()
    if "ADMIN" not in roles and "RECEPTIONIST" not in roles:
        raise HTTPException(status_code=403, detail="Only Hospital Admins and Receptionists can approve leaves.")

    hosp_id = current_user.hospital_id if current_user.hospital_id else "hosp_default"
    stmt = select(DoctorLeave).join(Doctor, DoctorLeave.doctor_id == Doctor.id).where(
        (DoctorLeave.id == leave_id) & (Doctor.hospital_id == hosp_id)
    )
    leave = (await db.execute(stmt)).scalar_one_or_none()
    if not leave:
        raise HTTPException(status_code=404, detail="Leave record not found or unauthorized")

    leave.status = "APPROVED"
    await db.commit()
    return {"status": "success", "message": "Leave request approved successfully"}


@router.post("/hospital/leaves/{leave_id}/reject", tags=["hospital"])
async def reject_doctor_leave(
    leave_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Rejects a pending doctor leave request (Admin or Receptionist only)."""
    # Verify current user is Admin or Receptionist
    role_stmt = select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == current_user.id)
    roles = (await db.execute(role_stmt)).scalars().all()
    if "ADMIN" not in roles and "RECEPTIONIST" not in roles:
        raise HTTPException(status_code=403, detail="Only Hospital Admins and Receptionists can reject leaves.")

    hosp_id = current_user.hospital_id if current_user.hospital_id else "hosp_default"
    stmt = select(DoctorLeave).join(Doctor, DoctorLeave.doctor_id == Doctor.id).where(
        (DoctorLeave.id == leave_id) & (Doctor.hospital_id == hosp_id)
    )
    leave = (await db.execute(stmt)).scalar_one_or_none()
    if not leave:
        raise HTTPException(status_code=404, detail="Leave record not found or unauthorized")

    leave.status = "REJECTED"
    await db.commit()
    return {"status": "success", "message": "Leave request rejected successfully"}


@router.delete("/hospital/staff/{user_id}", tags=["hospital"])
async def delete_staff_member(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Allows Hospital Admin to delete a staff member (Doctor or Receptionist) by user ID or Doctor ID."""
    role_stmt = select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == current_user.id)
    roles = (await db.execute(role_stmt)).scalars().all()
    if "ADMIN" not in roles and "SUPER_ADMIN" not in roles:
        raise HTTPException(status_code=403, detail="Unauthorized")
        
    hosp_id = current_user.hospital_id if current_user.hospital_id else "hosp_default"
    
    # 1. Check if user_id refers to a Doctor
    doc_stmt = select(Doctor).where((Doctor.id == user_id) & (Doctor.hospital_id == hosp_id))
    doctor = (await db.execute(doc_stmt)).scalar_one_or_none()
    
    if doctor:
        user_stmt = select(User).where((User.email == doctor.email) & (User.hospital_id == hosp_id))
        staff_user = (await db.execute(user_stmt)).scalar_one_or_none()
        await db.delete(doctor)
        if staff_user:
            await db.delete(staff_user)
    else:
        # 2. Fallback to direct User ID lookup
        user_stmt = select(User).where((User.id == user_id) & (User.hospital_id == hosp_id))
        staff_user = (await db.execute(user_stmt)).scalar_one_or_none()
        if not staff_user:
            raise HTTPException(status_code=404, detail="Staff member not found under this hospital")
            
        doc_stmt2 = select(Doctor).where(Doctor.email == staff_user.email)
        doctor2 = (await db.execute(doc_stmt2)).scalar_one_or_none()
        if doctor2:
            await db.delete(doctor2)
            
        await db.delete(staff_user)
        
    await db.commit()
    return {"status": "success", "message": "Staff member deleted successfully"}


@router.put("/hospital/staff/doctor/{doctor_id}", tags=["hospital"])
async def update_doctor_profile(
    doctor_id: str,
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    license_number: Optional[str] = Form(None),
    opd_fees: Optional[int] = Form(500),
    slot_duration_minutes: Optional[int] = Form(30),
    schedule_days: Optional[str] = Form(None),
    schedule_start_time: Optional[str] = Form(None),
    schedule_end_time: Optional[str] = Form(None),
    schedule_start_time_2: Optional[str] = Form(None),
    schedule_end_time_2: Optional[str] = Form(None),
    username: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Updates doctor profile, credentials, and rebuilds OPD schedules."""
    role_stmt = select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == current_user.id)
    roles = (await db.execute(role_stmt)).scalars().all()
    if "ADMIN" not in roles and "SUPER_ADMIN" not in roles:
        raise HTTPException(status_code=403, detail="Unauthorized")
        
    try:
        doc_stmt = select(Doctor).where(Doctor.id == doctor_id)
        if "SUPER_ADMIN" not in roles and current_user.hospital_id:
            doc_stmt = doc_stmt.where(Doctor.hospital_id == current_user.hospital_id)

        doctor = (await db.execute(doc_stmt)).scalar_one_or_none()
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor profile not found")
            
        h_id = doctor.hospital_id
        doctor.first_name = first_name
        doctor.last_name = last_name
        doctor.email = email
        doctor.phone = phone
        doctor.license_number = license_number or doctor.license_number
        doctor.opd_fees = opd_fees if opd_fees is not None else doctor.opd_fees

        # Sync User account
        user_stmt = select(User).where(User.id == doctor_id)
        doc_user = (await db.execute(user_stmt)).scalar_one_or_none()

        from app.core.dependencies import hash_password
        from app.database.models.appointment import HospitalSetting

        if not doc_user:
            target_username = (username or f"doc_{doctor_id[:6]}").strip()
            doc_user = User(
                id=doctor.id,
                hospital_id=h_id,
                username=target_username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                password_hash=hash_password(password or "password123"),
                is_active=True
            )
            db.add(doc_user)
            await db.flush()

            # Add DOCTOR role
            role_lookup = select(Role).where(Role.name == "DOCTOR")
            doc_role = (await db.execute(role_lookup)).scalar_one_or_none()
            if doc_role:
                db.add(UserRole(id=str(uuid.uuid4()), user_id=doc_user.id, role_id=doc_role.id))
        else:
            if username and username.strip():
                doc_user.username = username.strip()
            doc_user.email = email
            doc_user.first_name = first_name
            doc_user.last_name = last_name
            if password and password.strip():
                doc_user.password_hash = hash_password(password.strip())

        if password and password.strip():
            setting_key = f"staff_pwd_{doctor.id}"
            st_stmt = select(HospitalSetting).where(
                (HospitalSetting.hospital_id == h_id) & 
                (HospitalSetting.setting_key == setting_key)
            )
            pw_setting = (await db.execute(st_stmt)).scalar_one_or_none()
            if pw_setting:
                pw_setting.setting_value = password.strip()
            else:
                db.add(HospitalSetting(
                    id=str(uuid.uuid4()), 
                    hospital_id=h_id, 
                    setting_key=setting_key, 
                    setting_value=password.strip()
                ))

        # Rebuild schedules if schedule information is provided
        def normalize_time_str(val: Optional[str]) -> Optional[str]:
            if not val:
                return None
            c = val.strip().lower()
            if c in ["", "null", "undefined", "--:--"]:
                return None
            return val.strip()

        norm_s1_start = normalize_time_str(schedule_start_time)
        norm_s1_end = normalize_time_str(schedule_end_time)
        norm_s2_start = normalize_time_str(schedule_start_time_2)
        norm_s2_end = normalize_time_str(schedule_end_time_2)

        if schedule_days and norm_s1_start and norm_s1_end:
            from app.database.models.appointment import DoctorSchedule
            from datetime import time

            def parse_time(value: Optional[str]) -> Optional[time]:
                if not value:
                    return None
                try:
                    parts = value.split(':')
                    return time(int(parts[0]), int(parts[1]))
                except Exception as parse_err:
                    raise ValueError(f"Invalid time format: '{value}'. Expected HH:MM or HH:MM:SS.")

            try:
                t_start = parse_time(norm_s1_start)
                t_end = parse_time(norm_s1_end)
                t_start_2 = parse_time(norm_s2_start)
                t_end_2 = parse_time(norm_s2_end)
            except Exception as pe:
                logger.error(f"Time parsing failed during doctor profile update: {str(pe)}")
                raise HTTPException(status_code=400, detail="Invalid time format.")

            # Clear old schedules
            del_stmt = select(DoctorSchedule).where(DoctorSchedule.doctor_id == doctor.id)
            old_scheds = (await db.execute(del_stmt)).scalars().all()
            for osc in old_scheds:
                await db.delete(osc)
            
            # Flush after deletion
            await db.flush()

            try:
                days = list(set([int(d.strip()) for d in schedule_days.split(',') if d.strip().isdigit()]))
                for day in days:
                    s1 = DoctorSchedule(
                        id=str(uuid.uuid4()),
                        doctor_id=doctor.id,
                        day_of_week=day,
                        start_time=t_start,
                        end_time=t_end,
                        slot_duration_minutes=slot_duration_minutes or 30
                    )
                    db.add(s1)
                    if t_start_2 and t_end_2 and t_start_2 != t_start:
                        s2 = DoctorSchedule(
                            id=str(uuid.uuid4()),
                            doctor_id=doctor.id,
                            day_of_week=day,
                            start_time=t_start_2,
                            end_time=t_end_2,
                            slot_duration_minutes=slot_duration_minutes or 30
                        )
                        db.add(s2)
                        
                # Flush after insertion
                await db.flush()
                
            except Exception as se:
                logger.error(f"Error rebuilding doctor schedule list: {str(se)}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Error inserting doctor schedules: {str(se)}"
                )

        await db.commit()
        logger.info(f"Database commit success for doctor profile update of ID {doctor.id}.")
        
        # Send WhatsApp schedule update notification
        if phone:
            from app.services.whatsapp import WhatsAppNotificationService
            import asyncio
            wa_service = WhatsAppNotificationService()
            msg = f"🏥 *Hospital Update*\nDr. {first_name} {last_name},\nYour profile and working schedule has been successfully updated by the hospital administration. Please log in to your portal to verify the changes."
            # Await synchronously or fire in background
            asyncio.create_task(wa_service.send_custom_notification(phone, msg))
            logger.info("WhatsApp schedule update notification queued for doctor.")
            
        return {"status": "success", "message": "Doctor profile updated successfully"}
    except Exception as e:
        await db.rollback()
        logger.error(f"Transaction failed during doctor profile update: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Failed to update doctor profile: {str(e)}")


# ==========================================
# PATIENTS MANAGEMENT
# ==========================================

@router.post("/patients", response_model=PatientRead)
async def register_patient(
    payload: PatientCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Registers a new patient file in the central medical records database."""
    import uuid
    pat_id = str(uuid.uuid4())
    patient = Patient(
        id=pat_id,
        hospital_id=payload.hospital_id,
        first_name=payload.first_name,
        last_name=payload.last_name,
        date_of_birth=payload.date_of_birth,
        gender=payload.gender,
        phone=payload.phone,
        email=payload.email,
        insurance_provider_id=payload.insurance_provider_id,
        insurance_policy_number=payload.insurance_policy_number
    )
    db.add(patient)
    await db.commit()
    await db.refresh(patient)
    return patient


# ==========================================
# RECEPTIONIST SCHEDULE DASHBOARD (No Auth Required)
# Open in browser: http://your-server/receptionist/schedule
# ==========================================

@router.get("/receptionist/schedule", response_class=HTMLResponse, tags=["receptionist"])
async def receptionist_today_schedule(
    date_str: Optional[str] = Query(None, description="Date in YYYY-MM-DD format. Defaults to today."),
    hospital_id: str = Query("hosp_default"),
    db: AsyncSession = Depends(get_db)
):
    """
    Human receptionist dashboard — shows all appointments for a given date organized by doctor.
    No authentication required. Auto-refreshes every 30 seconds.
    """
    await auto_update_missed_appointments(db)

    if date_str:
        try:
            target_date = date.fromisoformat(date_str)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
    else:
        target_date = date.today()

    start_dt = datetime.combine(target_date, datetime.min.time())
    end_dt = datetime.combine(target_date, datetime.max.time())

    appt_stmt = (
        select(Appointment, Patient, Doctor, Department)
        .join(Patient, Appointment.patient_id == Patient.id)
        .join(Doctor, Appointment.doctor_id == Doctor.id)
        .join(Department, Doctor.department_id == Department.id)
        .where(
            and_(
                Appointment.hospital_id == hospital_id,
                Appointment.appointment_datetime >= start_dt,
                Appointment.appointment_datetime <= end_dt,
                Appointment.status.in_(["SCHEDULED", "PENDING_PAYMENT", "COMPLETED", "CANCELLED", "MISSED", "RESCHEDULED"])
            )
        )
        .order_by(Doctor.first_name, Appointment.appointment_datetime)
    )
    results = (await db.execute(appt_stmt)).all()

    hosp_stmt = select(Hospital).where(Hospital.id == hospital_id)
    hospital_obj = (await db.execute(hosp_stmt)).scalar_one_or_none()
    hosp_name = hospital_obj.name if hospital_obj else "CP Tiwari Hospital"

    # Fetch active doctors and calculate their free slots
    docs_stmt = (
        select(Doctor, Department)
        .join(Department, Doctor.department_id == Department.id)
        .where(Doctor.is_active == True)
    )
    doctors_db = (await db.execute(docs_stmt)).all()
    
    scheduler = SchedulingEngine(db)
    doctors_info = []
    
    for doc, dept in doctors_db:
        free_slots = await scheduler.get_available_slots(doc.id, target_date)
        fees = f"₹{doc.opd_fees}" if (doc.opd_fees is not None) else "₹500"
        
        # Timing representation in Hindi (Dynamic)
        from app.database.models.appointment import DoctorSchedule
        sched_stmt = select(DoctorSchedule).where(DoctorSchedule.doctor_id == doc.id)
        doc_schedules = (await db.execute(sched_stmt)).scalars().all()
        if doc_schedules:
            from collections import defaultdict
            day_to_ranges = defaultdict(list)
            for s in doc_schedules:
                tr = f"{s.start_time.strftime('%I:%M %p').lstrip('0')} - {s.end_time.strftime('%I:%M %p').lstrip('0')}"
                if tr not in day_to_ranges[s.day_of_week]:
                    day_to_ranges[s.day_of_week].append(tr)
            
            times_tuple_to_days = defaultdict(list)
            for day, ranges in day_to_ranges.items():
                times_tuple = tuple(ranges)
                times_tuple_to_days[times_tuple].append(day)
            
            parts = []
            day_names_map = {1: "सोम", 2: "मंगल", 3: "बुध", 4: "गुरु", 5: "शुक्र", 6: "शनि", 7: "रवि"}
            for times_tuple, days_list in times_tuple_to_days.items():
                days_list.sort()
                if len(days_list) >= 5 and days_list == list(range(days_list[0], days_list[0] + len(days_list))):
                    days_str = f"{day_names_map.get(days_list[0])}–{day_names_map.get(days_list[-1])}"
                else:
                    days_str = ", ".join([day_names_map.get(d, str(d)) for d in days_list])
                time_slots_str = ", ".join(times_tuple)
                parts.append(f"{days_str} ({time_slots_str})")
            
            timing_str = " | ".join(parts)
        else:
            timing_str = "सोम–शुक्र (10:00 AM - 1:00 PM, 2:00 PM - 5:00 PM)"
        
        doctors_info.append({
            "name": f"Dr. {doc.first_name} {doc.last_name}",
            "dept": dept.name,
            "fees": fees,
            "timings": timing_str,
            "free_slots_count": len(free_slots)
        })

    by_doctor: dict = defaultdict(list)
    for appt, patient, doctor, dept in results:
        # Load intake info for this appointment (if exists)
        from app.database.models.appointment import PatientIntake
        intake_stmt = select(PatientIntake).where(PatientIntake.appointment_id == appt.id)
        intake_obj = (await db.execute(intake_stmt)).scalar_one_or_none()
        intake_html_parts = []
        if intake_obj:
            if intake_obj.has_visited_before is not None:
                intake_html_parts.append(f"🔁 पहले दिखाया: {'हाँ — ' + (intake_obj.previous_doctor or '') if intake_obj.has_visited_before else 'नहीं'}")
            if intake_obj.has_reports is not None:
                intake_html_parts.append(f"📄 Reports: {'हाँ — ' + (intake_obj.report_details or '') if intake_obj.has_reports else 'नहीं'}")
            if intake_obj.current_medicines:
                intake_html_parts.append(f"💊 दवाइयाँ: {intake_obj.current_medicines}")
            if intake_obj.additional_notes:
                intake_html_parts.append(f"📝 नोट: {intake_obj.additional_notes}")

        key = (f"Dr. {doctor.first_name} {doctor.last_name}", dept.name)
        by_doctor[key].append({
            "appointment_id": appt.id,
            "doctor_id": doctor.id,
            "time": appt.appointment_datetime.strftime("%I:%M %p"),
            "time_24": appt.appointment_datetime.strftime("%H:%M"),
            "appointment_datetime_iso": appt.appointment_datetime.isoformat(),
            "patient_name": f"{patient.first_name} {patient.last_name}".strip(),
            "patient_phone": patient.phone,
            "reason": appt.reason or "—",
            "status": appt.status,
            "intake_html": "<br>".join(intake_html_parts) if intake_html_parts else "",
        })

    day_display = target_date.strftime("%d %B %Y")
    day_name = target_date.strftime("%A")
    prev_date = (target_date - timedelta(days=1)).isoformat()
    next_date = (target_date + timedelta(days=1)).isoformat()
    total = len(results)
    confirmed = sum(1 for appt, *_ in results if appt.status == "SCHEDULED")
    pending = total - confirmed
    is_today = (target_date == date.today())
    now_str = datetime.now().strftime("%I:%M:%S %p")

    dept_icons = {
        "Orthopedics": "🦴", "Cardiology": "❤️", "Ophthalmology": "👁️",
        "Heart": "❤️", "Eye": "👁️", "Haddi": "🦴",
    }

    doctor_sections = ""
    if not by_doctor:
        doctor_sections = """
        <div class="empty-card">
            <div class="empty-icon">📅</div>
            <h3>इस दिन कोई अपॉइंटमेंट नहीं है</h3>
            <p>अभी तक कोई बुकिंग नहीं आई है। जैसे ही AI Receptionist call लेगी, यहाँ दिखेगी।</p>
        </div>"""
    else:
        for (doc_name, dept_name), appts in by_doctor.items():
            icon = next((v for k, v in dept_icons.items() if k.lower() in dept_name.lower()), "👨‍⚕️")
            rows = ""
            for i, a in enumerate(appts, 1):
                appt_id = a['appointment_id']
                status = a['status']
                # Status badge
                badge_map = {
                    'SCHEDULED': '<span class="badge confirmed">✅ Confirmed</span>',
                    'PENDING_PAYMENT': '<span class="badge pending-pay">⏳ Payment Pending</span>',
                    'COMPLETED': '<span class="badge completed">🎉 Completed</span>',
                    'CANCELLED': '<span class="badge cancelled">❌ Cancelled</span>',
                    'MISSED': '<span class="badge missed">🚫 Missed</span>',
                    'RESCHEDULED': '<span class="badge rescheduled">📅 Rescheduled</span>',
                }
                badge = badge_map.get(status, f'<span class="badge">{status}</span>')

                # Status action buttons (only for actionable statuses)
                action_btns = ""
                if status in ["SCHEDULED", "PENDING_PAYMENT", "RESCHEDULED"]:
                    # Do not show Reschedule if payment is pending
                    reschedule_btn = f"""<button class="act-btn blue" onclick="openReschedule('{appt_id}', '{a["doctor_id"]}', '{status}')">📅 Reschedule</button>""" if status != "PENDING_PAYMENT" else ""
                    
                    action_btns = f"""
                    <div class="action-btns" id="actions-{appt_id}">
                        <button class="act-btn green" onclick="updateStatus('{appt_id}', 'COMPLETED', '{status}')">✅ Completed</button>
                        <button class="act-btn red" onclick="updateStatus('{appt_id}', 'CANCELLED', '{status}')">❌ Cancel</button>
                        <button class="act-btn orange" onclick="updateStatus('{appt_id}', 'MISSED', '{status}')">🚫 Missed</button>
                        {reschedule_btn}
                    </div>"""

                # Intake info panel
                intake_panel = ""
                if a.get('intake_html'):
                    intake_panel = f"""<div class="intake-panel"><span class="intake-label">🩺 AI Intake:</span> {a['intake_html']}</div>"""

                rows += f"""
                <tr class="appt-row" id="row-{appt_id}">
                    <td class="td-sno">{i}</td>
                    <td class="td-time">
                        <span class="time-pill">{a["time"]}</span>
                    </td>
                    <td class="td-patient">
                        <div class="patient-name">{a["patient_name"]}</div>
                        {intake_panel}
                    </td>
                    <td class="td-phone">
                        <a href="tel:{a["patient_phone"]}" class="phone-link">📞 {a["patient_phone"]}</a>
                    </td>
                    <td class="td-reason">{a["reason"]}</td>
                    <td class="td-status">
                        <div id="badge-{appt_id}">{badge}</div>
                        {action_btns}
                    </td>
                </tr>"""
            doctor_sections += f"""
            <div class="doctor-card">
                <div class="doctor-header">
                    <div class="doctor-left">
                        <div class="doc-icon">{icon}</div>
                        <div class="doc-details">
                            <div class="doc-name">{doc_name}</div>
                            <div class="doc-dept">{dept_name}</div>
                        </div>
                    </div>
                    <div class="doc-right">
                        <div class="doc-count">{len(appts)}</div>
                        <div class="doc-count-label">अपॉइंटमेंट</div>
                    </div>
                </div>
                <div class="table-wrap">
                    <table>
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>⏰ समय</th>
                                <th>👤 मरीज़ का नाम</th>
                                <th>📞 मोबाइल</th>
                                <th>🩺 समस्या</th>
                                <th>स्थिति / कार्रवाई</th>
                            </tr>
                        </thead>
                        <tbody>{rows}</tbody>
                    </table>
                </div>
            </div>"""

    # Build the Sidebar Doctors Timings & Availability HTML
    sidebar_html = ""
    for d in doctors_info:
        badge_class = "slots-badge" if d["free_slots_count"] > 0 else "slots-badge empty"
        badge_text = f"{d['free_slots_count']} slots free" if d["free_slots_count"] > 0 else "Full / Closed"
        sidebar_html += f"""
        <div class="sidebar-doc-item">
            <div class="sidebar-doc-name">{d["name"]}</div>
            <div class="sidebar-doc-dept">{d["dept"]}</div>
            <div class="sidebar-doc-detail">
                <span>⏰ Timing:</span>
                <span>{d["timings"].replace("Timing:", "").strip()}</span>
            </div>
            <div class="sidebar-doc-detail">
                <span>💰 OPD Fees:</span>
                <span>{d["fees"]}</span>
            </div>
            <div class="sidebar-doc-detail" style="margin-top: 8px;">
                <span>📅 Slots status:</span>
                <span class="{badge_class}">{badge_text}</span>
            </div>
        </div>"""

    today_flag = '<span class="today-badge">आज</span>' if is_today else ""

    html = f"""<!DOCTYPE html>
<html lang="hi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{hosp_name} — रिसेप्शनिस्ट डैशबोर्ड</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {{
            --primary: #1a4fa0;
            --primary-dark: #0f3276;
            --primary-light: #dbeafe;
            --accent: #0ea5e9;
            --green: #16a34a;
            --green-bg: #dcfce7;
            --yellow: #b45309;
            --yellow-bg: #fef9c3;
            --bg: #f0f5fc;
            --card-bg: #ffffff;
            --text: #0f172a;
            --text-muted: #64748b;
            --border: #e2e8f0;
            --shadow: 0 4px 20px rgba(26,79,160,0.10);
            --radius: 16px;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Inter', system-ui, sans-serif;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
        }}

        /* ── HEADER ── */
        .header {{
            background: linear-gradient(135deg, #0f3276 0%, #1a4fa0 50%, #1e6cc4 100%);
            padding: 0;
            box-shadow: 0 4px 24px rgba(15,50,118,0.35);
        }}
        .header-inner {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 18px 28px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
            flex-wrap: wrap;
        }}
        .header-brand {{
            display: flex;
            align-items: center;
            gap: 14px;
        }}
        .header-logo {{
            width: 52px;
            height: 52px;
            background: rgba(255,255,255,0.15);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 26px;
            border: 1px solid rgba(255,255,255,0.25);
        }}
        .header-title {{ color: white; }}
        .header-title h1 {{ font-size: 20px; font-weight: 800; letter-spacing: -0.3px; }}
        .header-title p {{ font-size: 12px; color: rgba(255,255,255,0.75); margin-top: 2px; }}
        .header-right {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .live-clock {{
            background: rgba(255,255,255,0.12);
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 10px;
            padding: 8px 16px;
            color: white;
            font-size: 15px;
            font-weight: 600;
            font-variant-numeric: tabular-nums;
            min-width: 100px;
            text-align: center;
        }}
        .refresh-btn {{
            background: rgba(255,255,255,0.15);
            border: 1px solid rgba(255,255,255,0.3);
            color: white;
            padding: 8px 16px;
            border-radius: 10px;
            font-size: 13px;
            font-weight: 600;
            text-decoration: none;
            cursor: pointer;
            transition: background 0.2s;
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        .refresh-btn:hover {{ background: rgba(255,255,255,0.28); }}

        /* ── DATE NAV BAR ── */
        .date-bar {{
            background: white;
            border-bottom: 1px solid var(--border);
        }}
        .date-bar-inner {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 14px 28px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 12px;
        }}
        .date-info {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .date-text {{
            font-size: 17px;
            font-weight: 700;
            color: var(--primary-dark);
        }}
        .day-text {{
            font-size: 13px;
            color: var(--text-muted);
            font-weight: 500;
        }}
        .today-badge {{
            background: var(--primary);
            color: white;
            padding: 3px 10px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 700;
        }}
        .date-nav {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .date-nav a {{
            padding: 7px 14px;
            border: 1.5px solid var(--border);
            border-radius: 8px;
            text-decoration: none;
            color: var(--text-muted);
            font-size: 13px;
            font-weight: 600;
            transition: all 0.15s;
        }}
        .date-nav a:hover {{ background: var(--primary-light); border-color: var(--accent); color: var(--primary); }}
        .date-nav a.today-btn {{ background: var(--primary); color: white; border-color: var(--primary); }}
        .date-nav a.today-btn:hover {{ background: var(--primary-dark); }}

        /* ── CONTAINER & LAYOUT ── */
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 24px 28px;
        }}
        .dashboard-layout {{
            display: grid;
            grid-template-columns: 2.2fr 1fr;
            gap: 24px;
            align-items: start;
        }}
        @media (max-width: 950px) {{
            .dashboard-layout {{
                grid-template-columns: 1fr;
            }}
        }}

        /* ── STAT CARDS ── */
        .stats-row {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 16px;
            margin-bottom: 24px;
        }}
        .stat-card {{
            background: white;
            border-radius: var(--radius);
            padding: 20px 24px;
            box-shadow: var(--shadow);
            display: flex;
            align-items: center;
            gap: 16px;
        }}
        .stat-icon {{
            width: 48px;
            height: 48px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 22px;
            flex-shrink: 0;
        }}
        .stat-icon.blue {{ background: var(--primary-light); }}
        .stat-icon.green {{ background: var(--green-bg); }}
        .stat-icon.yellow {{ background: var(--yellow-bg); }}
        .stat-value {{ font-size: 28px; font-weight: 800; color: var(--text); line-height: 1; }}
        .stat-label {{ font-size: 12px; color: var(--text-muted); font-weight: 500; margin-top: 4px; }}

        /* ── DOCTOR CARD ── */
        .doctor-card {{
            background: var(--card-bg);
            border-radius: var(--radius);
            margin-bottom: 20px;
            box-shadow: var(--shadow);
            overflow: hidden;
            border: 1px solid var(--border);
        }}
        .doctor-header {{
            padding: 18px 24px;
            background: linear-gradient(135deg, #eff6ff 0%, #e0f2fe 100%);
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #bfdbfe;
        }}
        .doctor-left {{
            display: flex;
            align-items: center;
            gap: 14px;
        }}
        .doc-icon {{
            width: 44px;
            height: 44px;
            background: white;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 22px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }}
        .doc-name {{ font-size: 17px; font-weight: 700; color: var(--primary-dark); }}
        .doc-dept {{
            display: inline-block;
            margin-top: 4px;
            background: var(--primary);
            color: white;
            padding: 2px 10px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 600;
        }}
        .doc-right {{ text-align: center; }}
        .doc-count {{ font-size: 28px; font-weight: 800; color: var(--primary); }}
        .doc-count-label {{ font-size: 11px; color: var(--text-muted); font-weight: 500; }}

        /* ── SIDEBAR DOCTOR TIMINGS ── */
        .sidebar-card {{
            background: white;
            border-radius: var(--radius);
            padding: 24px;
            box-shadow: var(--shadow);
            border: 1px solid var(--border);
            position: sticky;
            top: 24px;
        }}
        .sidebar-title {{
            font-size: 16px;
            font-weight: 800;
            color: var(--primary-dark);
            margin-bottom: 18px;
            display: flex;
            align-items: center;
            gap: 8px;
            border-bottom: 2px solid var(--primary-light);
            padding-bottom: 10px;
        }}
        .sidebar-doc-item {{
            padding: 16px 0;
            border-bottom: 1px dashed var(--border);
        }}
        .sidebar-doc-item:last-child {{
            border-bottom: none;
            padding-bottom: 0;
        }}
        .sidebar-doc-item:first-child {{
            padding-top: 0;
        }}
        .sidebar-doc-name {{
            font-size: 15px;
            font-weight: 700;
            color: var(--text);
        }}
        .sidebar-doc-dept {{
            font-size: 10px;
            font-weight: 700;
            background: var(--primary-light);
            color: var(--primary-dark);
            padding: 2px 8px;
            border-radius: 12px;
            display: inline-block;
            margin-top: 4px;
            text-transform: uppercase;
        }}
        .sidebar-doc-detail {{
            font-size: 12px;
            color: var(--text-muted);
            margin-top: 8px;
            display: flex;
            justify-content: space-between;
            font-weight: 500;
        }}
        .slots-badge {{
            background: var(--green-bg);
            color: var(--green);
            padding: 2px 8px;
            border-radius: 6px;
            font-weight: 700;
            font-size: 11px;
        }}
        .slots-badge.empty {{
            background: #fee2e2;
            color: #ef4444;
        }}

        /* ── TABLE ── */
        .table-wrap {{ overflow-x: auto; }}
        table {{ width: 100%; border-collapse: collapse; }}
        thead tr {{ background: #f8fafc; }}
        th {{
            padding: 11px 16px;
            text-align: left;
            font-size: 11px;
            font-weight: 700;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.06em;
            border-bottom: 1.5px solid var(--border);
            white-space: nowrap;
        }}
        td {{
            padding: 13px 16px;
            border-bottom: 1px solid #f1f5f9;
            font-size: 14px;
            vertical-align: middle;
        }}
        .appt-row:last-child td {{ border-bottom: none; }}
        .appt-row:hover {{ background: #f8fafc; }}
        .td-sno {{ color: #cbd5e1; font-weight: 700; font-size: 13px; width: 36px; }}
        .time-pill {{
            background: var(--primary-light);
            color: var(--primary-dark);
            padding: 5px 12px;
            border-radius: 20px;
            font-weight: 700;
            font-size: 13px;
            white-space: nowrap;
            display: inline-block;
        }}
        .patient-name {{ font-weight: 600; color: var(--text); font-size: 14px; }}
        .phone-link {{ color: var(--text-muted); text-decoration: none; font-size: 13px; white-space: nowrap; }}
        .phone-link:hover {{ color: var(--primary); }}
        .td-reason {{ color: var(--text-muted); font-size: 13px; max-width: 180px; }}
        .badge {{
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 700;
            white-space: nowrap;
            display: inline-block;
        }}
        .badge.confirmed {{ background: var(--green-bg); color: var(--green); }}
        .badge.pending-pay {{ background: var(--yellow-bg); color: var(--yellow); }}

        /* ── EMPTY STATE ── */
        .empty-card {{
            background: white;
            border-radius: var(--radius);
            padding: 60px 20px;
            text-align: center;
            box-shadow: var(--shadow);
            border: 1px solid var(--border);
        }}
        .empty-icon {{ font-size: 52px; margin-bottom: 16px; }}
        .empty-card h3 {{ font-size: 18px; font-weight: 700; color: var(--text); margin-bottom: 8px; }}
        .empty-card p {{ font-size: 14px; color: var(--text-muted); max-width: 360px; margin: 0 auto; }}

        /* ── FOOTER ── */
        .footer {{
            text-align: center;
            color: #94a3b8;
            font-size: 12px;
            padding: 20px;
        }}

        /* ── RESPONSIVE ── */
        @media (max-width: 700px) {{
            .header-inner, .date-bar-inner, .container {{ padding: 14px 16px; }}
            .stats-row {{ grid-template-columns: 1fr; }}
            th, td {{ padding: 10px 12px; }}
            .header-title h1 {{ font-size: 16px; }}
            .date-text {{ font-size: 14px; }}
        }}
        @media (max-width: 480px) {{
            .stats-row {{ grid-template-columns: 1fr 1fr; }}
            .stat-card:first-child {{ grid-column: span 2; }}
        }}

        /* ── STATUS ACTION BUTTONS ── */
        .action-btns {{
            display: flex;
            flex-wrap: wrap;
            gap: 5px;
            margin-top: 8px;
        }}
        .act-btn {{
            padding: 4px 9px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 700;
            border: none;
            cursor: pointer;
            transition: all 0.15s;
            white-space: nowrap;
        }}
        .act-btn.green {{ background: #dcfce7; color: #15803d; }}
        .act-btn.green:hover {{ background: #bbf7d0; }}
        .act-btn.red {{ background: #fee2e2; color: #b91c1c; }}
        .act-btn.red:hover {{ background: #fecaca; }}
        .act-btn.orange {{ background: #fff7ed; color: #c2410c; }}
        .act-btn.orange:hover {{ background: #fed7aa; }}
        .act-btn.blue {{ background: #dbeafe; color: #1d4ed8; }}
        .act-btn.blue:hover {{ background: #bfdbfe; }}

        /* ── EXTRA STATUS BADGES ── */
        .badge.completed {{ background: #dcfce7; color: #15803d; }}
        .badge.cancelled {{ background: #fee2e2; color: #b91c1c; }}
        .badge.missed {{ background: #fef3c7; color: #92400e; }}
        .badge.rescheduled {{ background: #ede9fe; color: #6d28d9; }}

        /* ── AI INTAKE PANEL ── */
        .intake-panel {{
            margin-top: 6px;
            background: #f0f9ff;
            border: 1px solid #bae6fd;
            border-radius: 7px;
            padding: 6px 10px;
            font-size: 11.5px;
            color: #0369a1;
            line-height: 1.6;
        }}
        .intake-label {{
            font-weight: 700;
            display: block;
            margin-bottom: 2px;
        }}

        /* ── RESCHEDULE MODAL ── */
        .modal-overlay {{
            display: none;
            position: fixed;
            inset: 0;
            background: rgba(15,50,118,0.45);
            z-index: 9000;
            align-items: center;
            justify-content: center;
        }}
        .modal-overlay.open {{ display: flex; }}
        .modal-box {{
            background: white;
            border-radius: 18px;
            padding: 32px;
            max-width: 460px;
            width: 95%;
            box-shadow: 0 20px 60px rgba(15,50,118,0.25);
        }}
        .modal-title {{ font-size: 18px; font-weight: 800; color: var(--primary-dark); margin-bottom: 20px; }}
        .modal-label {{ font-size: 13px; font-weight: 600; color: var(--text-muted); margin-bottom: 6px; }}
        .modal-input {{
            width: 100%;
            padding: 10px 14px;
            border: 1.5px solid var(--border);
            border-radius: 9px;
            font-size: 14px;
            margin-bottom: 16px;
            font-family: inherit;
        }}
        .modal-input:focus {{ outline: none; border-color: var(--primary); }}
        .modal-actions {{ display: flex; gap: 10px; justify-content: flex-end; margin-top: 8px; }}
        .modal-btn {{
            padding: 10px 20px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 700;
            border: none;
            cursor: pointer;
            transition: background 0.15s;
        }}
        .modal-btn.confirm {{ background: var(--primary); color: white; }}
        .modal-btn.confirm:hover {{ background: var(--primary-dark); }}
        .modal-btn.cancel {{ background: #f1f5f9; color: var(--text-muted); }}
        .modal-btn.cancel:hover {{ background: #e2e8f0; }}
    </style>
</head>
<body>

    <div class="header">
        <div class="header-inner">
            <div class="header-brand">
                <div class="header-logo">🏥</div>
                <div class="header-title">
                    <h1>{hosp_name}</h1>
                    <p>रिसेप्शनिस्ट डैशबोर्ड — AI Voice Booking System</p>
                </div>
            </div>
            <div class="header-right">
                <div class="live-clock" id="clock">{now_str}</div>
                <a class="refresh-btn" href="/receptionist/schedule?hospital_id={hospital_id}">
                    🔄 Refresh
                </a>
            </div>
        </div>
    </div>

    <div class="date-bar">
        <div class="date-bar-inner">
            <div class="date-info">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <div class="header-logo" style="width: 40px; height: 40px; font-size: 20px; background: var(--primary-light); color: var(--primary); cursor: pointer; border: 1.5px solid var(--border); display: flex; align-items: center; justify-content: center; border-radius: 10px;" onclick="document.getElementById('date-select').showPicker()">📅</div>
                    <div>
                        <div class="date-text" style="display: flex; align-items: center; gap: 6px; cursor: pointer; color: var(--primary-dark); font-weight: 700; font-size: 17px;" onclick="document.getElementById('date-select').showPicker()">
                            {day_display} {today_flag}
                            <span style="font-size: 11px; color: var(--accent); vertical-align: middle;">▼</span>
                        </div>
                        <div class="day-text">{day_name}</div>
                    </div>
                    <!-- Hidden native date input triggered by calendar click -->
                    <input type="date" id="date-select" value="{target_date.isoformat()}" 
                           style="opacity: 0; width: 0; height: 0; position: absolute;"
                           onchange="window.location.href='/receptionist/schedule?hospital_id={hospital_id}&date_str=' + this.value">
                </div>
            </div>
            <div class="date-nav">
                <a href="/receptionist/schedule?date_str={prev_date}&hospital_id={hospital_id}">◀ पिछला</a>
                <a href="/receptionist/schedule?hospital_id={hospital_id}" class="today-btn">आज</a>
                <a href="/receptionist/schedule?date_str={next_date}&hospital_id={hospital_id}">अगला ▶</a>
            </div>
        </div>
    </div>

    <div class="container">

        <div class="stats-row">
            <div class="stat-card">
                <div class="stat-icon blue">📋</div>
                <div>
                    <div class="stat-value">{total}</div>
                    <div class="stat-label">कुल अपॉइंटमेंट</div>
                </div>
            </div>
            <div class="stat-card">
                <div class="stat-icon green">✅</div>
                <div>
                    <div class="stat-value">{confirmed}</div>
                    <div class="stat-label">Confirmed</div>
                </div>
            </div>
            <div class="stat-card">
                <div class="stat-icon yellow">⏳</div>
                <div>
                    <div class="stat-value">{pending}</div>
                    <div class="stat-label">Payment Pending</div>
                </div>
            </div>
        </div>

        <div class="dashboard-layout">
            <!-- Left Side: Appointments List -->
            <div class="main-content">
                {doctor_sections}
            </div>

            <!-- Right Side: Doctors & Timings Sidebar -->
            <div class="sidebar-content">
                <div class="sidebar-card">
                    <div class="sidebar-title">
                        <span>👨‍⚕️</span> डॉक्टर, समय एवं फीस सूची
                    </div>
                    <div class="sidebar-list">
                        {sidebar_html}
                    </div>
                </div>
            </div>
        </div>

        <div class="footer">
            अंतिम अपडेट: {datetime.now().strftime("%d %b %Y, %I:%M:%S %p")}
        </div>
    </div>

    <!-- Reschedule Modal -->
    <div class="modal-overlay" id="rescheduleModal">
        <div class="modal-box">
            <div class="modal-title">📅 Appointment Reschedule करें</div>
            <input type="hidden" id="modal-appt-id">
            <input type="hidden" id="modal-doctor-id">
            <label class="modal-label">नई Date और Time:</label>
            <input type="datetime-local" class="modal-input" id="modal-new-datetime" onchange="fetchBusySlots()">
            
            <!-- Booked Slots list container -->
            <div id="busy-slots-container" style="display:none; margin-bottom: 16px;">
                <label class="modal-label" style="color: #b91c1c; display: flex; align-items: center; gap: 4px;">
                    🚫 व्यस्त स्लॉट्स (Already Booked Times):
                </label>
                <div id="busy-slots-list" style="display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px;"></div>
            </div>

            <label class="modal-label">मरीज़ के लिए पहुँचने की Cutoff Note (optional):</label>
            <input type="text" class="modal-input" id="modal-cutoff" placeholder="जैसे: कृपया 10 बजे तक पहुँचें">
            <div class="modal-actions">
                <button class="modal-btn cancel" onclick="closeReschedule()">रद्द करें</button>
                <button class="modal-btn confirm" onclick="confirmReschedule()">📅 Reschedule करें</button>
            </div>
        </div>
    </div>

    <script>
        // Live clock update every second
        function updateClock() {{
            const now = new Date();
            const h = String(now.getHours() % 12 || 12).padStart(2, '0');
            const m = String(now.getMinutes()).padStart(2, '0');
            const s = String(now.getSeconds()).padStart(2, '0');
            const ampm = now.getHours() >= 12 ? 'PM' : 'AM';
            document.getElementById('clock').textContent = h + ':' + m + ':' + s + ' ' + ampm;
        }}
        setInterval(updateClock, 1000);
        updateClock();

        // Update appointment status (Completed / Cancelled / Missed)
        async function updateStatus(apptId, newStatus, currentStatus) {{
            const label = {{COMPLETED: 'Completed ✅', CANCELLED: 'Cancelled ❌', MISSED: 'Missed 🚫'}}[newStatus] || newStatus;
            
            let cancelReason = null;
            if (newStatus === 'CANCELLED' && currentStatus === 'SCHEDULED') {{
                cancelReason = prompt("इस Paid Appointment को निरस्त करने का कारण (Reason) दर्ज करें (यह मरीज़ को WhatsApp रिफंड सूचना के साथ भेजा जाएगा):");
                if (cancelReason === null) return; // user cancelled prompt
                if (!cancelReason.trim()) cancelReason = "अस्पताल के अनुरोध पर";
            }}

            if (!confirm(`क्या आप इस appointment को "${{label}}" mark करना चाहते हैं?`)) return;

            const formData = new FormData();
            formData.append('new_status', newStatus);
            if (cancelReason) {{
                formData.append('cancellation_reason', cancelReason);
            }}

            try {{
                const res = await fetch(`/appointments/${{apptId}}/status`, {{
                    method: 'POST',
                    body: formData
                }});
                const data = await res.json();
                if (data.success) {{
                    const badgeMap = {{
                        COMPLETED: '<span class="badge completed">🎉 Completed</span>',
                        CANCELLED: '<span class="badge cancelled">❌ Cancelled</span>',
                        MISSED: '<span class="badge missed">🚫 Missed</span>',
                    }};
                    document.getElementById(`badge-${{apptId}}`).innerHTML = badgeMap[newStatus] || newStatus;
                    const actionsDiv = document.getElementById(`actions-${{apptId}}`);
                    if (actionsDiv) actionsDiv.remove();
                    if (newStatus === 'CANCELLED' && currentStatus === 'SCHEDULED') {{
                        alert('✅ Appointment निरस्त कर दी गई है और मरीज़ को रिफंड की सूचना WhatsApp कर दी गई है।');
                    }}
                }} else {{
                    alert('कुछ गड़बड़ हो गई। दोबारा कोशिश करें।');
                }}
            }} catch (e) {{
                alert('Network error. Please try again.');
            }}
        }}

        // Open reschedule modal
        function openReschedule(apptId, doctorId, currentStatus) {{
            if (currentStatus === 'PENDING_PAYMENT') {{
                alert('❌ भुगतान अपूर्ण है (Payment Pending)। रीशेड्यूल केवल भुगतान पूरा होने के बाद ही संभव है।');
                return;
            }}

            document.getElementById('modal-appt-id').value = apptId;
            document.getElementById('modal-doctor-id').value = doctorId;
            
            const dtInput = document.getElementById('modal-new-datetime');
            dtInput.value = '';
            
            const now = new Date();
            const tzOffset = now.getTimezoneOffset() * 60000;
            const minDt = new Date(now.getTime() - tzOffset).toISOString().slice(0, 16);
            const maxDate = new Date(now.getTime() + 2 * 24 * 60 * 60 * 1000);
            const maxDt = new Date(maxDate.getTime() - tzOffset).toISOString().slice(0, 16);
            
            dtInput.min = minDt;
            dtInput.max = maxDt;
            
            document.getElementById('modal-cutoff').value = '';
            
            // Hide busy slots list
            document.getElementById('busy-slots-container').style.display = 'none';
            document.getElementById('busy-slots-list').innerHTML = '';

            document.getElementById('rescheduleModal').classList.add('open');
        }}

        function closeReschedule() {{
            document.getElementById('rescheduleModal').classList.remove('open');
        }}

        // Fetch busy slots dynamically
        async function fetchBusySlots() {{
            const docId = document.getElementById('modal-doctor-id').value;
            const newDtVal = document.getElementById('modal-new-datetime').value;
            if (!newDtVal) return;

            // Extract date (YYYY-MM-DD)
            const dateStr = newDtVal.split('T')[0];

            try {{
                const res = await fetch(`/receptionist/booked-slots?doctor_id=${{docId}}&date_str=${{dateStr}}`);
                const data = await res.json();
                const container = document.getElementById('busy-slots-container');
                const list = document.getElementById('busy-slots-list');
                
                list.innerHTML = '';
                if (data.booked_slots && data.booked_slots.length > 0) {{
                    data.booked_slots.forEach(slot => {{
                        const badge = document.createElement('span');
                        badge.className = 'badge cancelled';
                        badge.style.fontSize = '11px';
                        badge.style.padding = '3px 8px';
                        badge.style.background = '#fee2e2';
                        badge.style.color = '#b91c1c';
                        badge.textContent = slot;
                        list.appendChild(badge);
                    }});
                    container.style.display = 'block';
                }} else {{
                    list.innerHTML = '<span style="font-size:11px;color:#16a34a">💡 इस दिन कोई अन्य बुकिंग नहीं है। सारे स्लॉट्स खाली हैं।</span>';
                    container.style.display = 'block';
                }}
            }} catch (e) {{
                console.error("Failed to fetch busy slots", e);
            }}
        }}

        // Confirm reschedule — calls backend and sends WhatsApp
        async function confirmReschedule() {{
            const apptId = document.getElementById('modal-appt-id').value;
            const newDt = document.getElementById('modal-new-datetime').value;
            const cutoff = document.getElementById('modal-cutoff').value;

            if (!newDt) {{
                alert('कृपया नई Date और Time चुनें।');
                return;
            }}

            const formData = new FormData();
            formData.append('new_status', 'RESCHEDULED');
            formData.append('new_datetime', newDt);
            formData.append('cutoff_note', cutoff);

            try {{
                const res = await fetch(`/appointments/${{apptId}}/status`, {{
                    method: 'POST',
                    body: formData
                }});
                
                if (res.status === 400) {{
                    const errData = await res.json();
                    if (errData.detail === 'appointment already rescheduled once') {{
                        alert('⚠️ यह अपॉइंटमेंट पहले ही 1 बार reschedule की जा चुकी है। इसे दोबारा reschedule नहीं किया जा सकता।');
                        closeReschedule();
                        return;
                    }}
                }}

                const data = await res.json();
                if (data.success) {{
                    closeReschedule();
                    document.getElementById(`badge-${{apptId}}`).innerHTML = '<span class="badge rescheduled">📅 Rescheduled</span>';
                    const actionsDiv = document.getElementById(`actions-${{apptId}}`);
                    if (actionsDiv) actionsDiv.remove(); // Only allow 1 reschedule, so remove actions
                    alert('✅ Reschedule हो गया! मरीज़ के WhatsApp पर नया समय भेज दिया गया है।');
                }} else {{
                    alert('कुछ गड़बड़ हो गई।');
                }}
            }} catch (e) {{
                alert('Network error. Please try again.');
            }}
        }}

        // Close modal on backdrop click
        document.getElementById('rescheduleModal').addEventListener('click', function(e) {{
            if (e.target === this) closeReschedule();
        }});
    </script>

</body>
</html>"""
    return HTMLResponse(content=html)



# ==========================================
# RAZORPAY INTEGRATION
# ==========================================

def get_razorpay_client():
    key_id = os.environ.get("RAZORPAY_KEY_ID", "")
    key_secret = os.environ.get("RAZORPAY_KEY_SECRET", "")
    if not key_id or not key_secret:
        return None
    return razorpay.Client(auth=(key_id, key_secret))

@router.post("/payment/create-order", tags=["payment"])
async def create_razorpay_order(req: PaymentOrderRequest, db: AsyncSession = Depends(get_db)):
    client = get_razorpay_client()
    if not client:
        # Fallback to simulated payment if keys not configured
        return {"simulated": True, "order_id": "sim_" + str(uuid.uuid4())}
        
    try:
        # Amount in paise
        order_data = {
            "amount": req.amount * 100, 
            "currency": "INR",
            "receipt": req.appointment_id[:40]
        }
        order = client.order.create(data=order_data)
        return {"simulated": False, "order_id": order["id"], "key_id": os.environ.get("RAZORPAY_KEY_ID")}
    except Exception as e:
        logger.error(f"Razorpay order creation failed: {e}")
        raise HTTPException(status_code=500, detail="Could not create payment order")

@router.post("/payment/verify", tags=["payment"])
async def verify_razorpay_payment(req: PaymentVerifyRequest, db: AsyncSession = Depends(get_db)):
    client = get_razorpay_client()
    if not client:
        # Simulated success
        pass
    else:
        try:
            client.utility.verify_payment_signature({
                'razorpay_order_id': req.razorpay_order_id,
                'razorpay_payment_id': req.razorpay_payment_id,
                'razorpay_signature': req.razorpay_signature
            })
        except razorpay.errors.SignatureVerificationError:
            raise HTTPException(status_code=400, detail="Invalid payment signature")
        except Exception as e:
            logger.error(f"Razorpay verification failed: {e}")
            raise HTTPException(status_code=500, detail="Payment verification failed")
            
    # Payment verified successfully! Update appointment status
    from app.database.models.appointment import Appointment, AppointmentStatusHistory
    stmt = select(Appointment).where(Appointment.id == req.appointment_id)
    appointment = (await db.execute(stmt)).scalar_one_or_none()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
        
    if appointment.status == "PENDING_PAYMENT":
        history = AppointmentStatusHistory(
            id=str(uuid.uuid4()),
            appointment_id=appointment.id,
            previous_status="PENDING_PAYMENT",
            new_status="SCHEDULED",
            change_reason="Payment successful via Razorpay"
        )
        appointment.status = "SCHEDULED"
        db.add(history)
        await db.commit()
        
    return {"status": "success", "message": "Payment verified and appointment confirmed"}


# ==========================================
# SIMULATED PAYMENT WEBHOOK & CHECKOUT GATEWAY
# ==========================================

@router.get("/payment/checkout", response_class=HTMLResponse, tags=["payment"])
async def payment_checkout_page(
    appt: str = Query(..., description="Full ID or last 8 characters of the appointment ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Simulated CP Tiwari Hospital payment checkout page.
    Renders details, billing amount, and simulated gateway confirm button.
    """
    from app.database.models.appointment import Appointment, Patient, Doctor, Department, Hospital
    
    # Query appointment by full ID or last 8 characters
    if len(appt.strip()) == 8:
        stmt = (
            select(Appointment, Patient, Doctor, Department, Hospital)
            .join(Patient, Appointment.patient_id == Patient.id)
            .join(Doctor, Appointment.doctor_id == Doctor.id)
            .join(Department, Doctor.department_id == Department.id)
            .join(Hospital, Appointment.hospital_id == Hospital.id)
            .where(Appointment.id.like(f"%{appt.strip()}"))
        )
    else:
        stmt = (
            select(Appointment, Patient, Doctor, Department, Hospital)
            .join(Patient, Appointment.patient_id == Patient.id)
            .join(Doctor, Appointment.doctor_id == Doctor.id)
            .join(Department, Doctor.department_id == Department.id)
            .join(Hospital, Appointment.hospital_id == Hospital.id)
            .where(Appointment.id == appt.strip())
        )

    res = (await db.execute(stmt)).first()
    if not res:
        return HTMLResponse(
            content="<h3>त्रुटि (Error): अपॉइंटमेंट नहीं मिला। कृपया लिंक दोबारा जांचें।</h3>",
            status_code=404
        )

    appointment, patient, doctor, department, hospital = res
    appt_display_time = appointment.appointment_datetime.strftime("%d %b %Y, %I:%M %p")
    amount = doctor.opd_fees if (doctor and doctor.opd_fees is not None) else 500

    # Check if already paid
    if appointment.status == "SCHEDULED":
        return HTMLResponse(content=f"""<!DOCTYPE html>
<html lang="hi">
<head>
    <meta charset="UTF-8">
    <title>पेमेंट रसीद — {hospital.name}</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>
        body {{ font-family: 'Inter', sans-serif; background: #f0f5fc; color: #0f172a; padding: 40px 20px; text-align: center; }}
        .card {{ background: white; max-width: 480px; margin: 0 auto; padding: 40px; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); border: 1px solid #e2e8f0; }}
        .success-icon {{ font-size: 56px; color: #16a34a; margin-bottom: 20px; }}
        h2 {{ font-size: 22px; font-weight: 800; color: #0f3276; margin-bottom: 12px; }}
        p {{ color: #64748b; font-size: 14px; margin-bottom: 24px; line-height: 1.5; }}
        .details {{ text-align: left; background: #f8fafc; padding: 20px; border-radius: 12px; margin-bottom: 24px; border: 1px dashed #cbd5e1; }}
        .detail-row {{ display: flex; justify-content: space-between; margin-bottom: 10px; font-size: 13px; }}
        .detail-row:last-child {{ margin-bottom: 0; }}
        .label {{ color: #64748b; font-weight: 500; }}
        .val {{ color: #0f172a; font-weight: 700; }}
        .badge {{ background: #dcfce7; color: #16a34a; padding: 4px 10px; border-radius: 8px; font-weight: 700; }}
        .btn {{ display: inline-block; background: #0f3276; color: white; padding: 12px 24px; border-radius: 10px; text-decoration: none; font-weight: 600; font-size: 14px; margin-top: 10px; }}
        .btn:hover {{ background: #1a4fa0; }}
    </style>
</head>
<body>
    <div class="card">
        <div class="success-icon">🎉</div>
        <h2>पेमेंट पहले ही हो चुका है!</h2>
        <p>इस अपॉइंटमेंट के लिए पेमेंट सफलतापूर्वक प्राप्त हो चुका है और अपॉइंटमेंट कन्फर्म है।</p>
        <div class="details">
            <div class="detail-row"><span class="label">मरीज़:</span><span class="val">{patient.first_name} {patient.last_name}</span></div>
            <div class="detail-row"><span class="label">डॉक्टर:</span><span class="val">Dr. {doctor.first_name} {doctor.last_name}</span></div>
            <div class="detail-row"><span class="label">समय:</span><span class="val">{appt_display_time}</span></div>
            <div class="detail-row"><span class="label">राशि:</span><span class="val">₹{amount} (Paid)</span></div>
            <div class="detail-row"><span class="label">स्थिति:</span><span class="val"><span class="badge">कन्फर्म (Confirmed)</span></span></div>
        </div>
        <a href="/receptionist/schedule" class="btn">डैशबोर्ड पर जाएं</a>
    </div>
</body>
</html>""")

    checkout_html = f"""<!DOCTYPE html>
<html lang="hi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>सुरक्षित भुगतान द्वार (Checkout) — {hospital.name}</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {{
            --primary: #1a4fa0;
            --primary-dark: #0f3276;
            --primary-light: #dbeafe;
            --bg: #f0f5fc;
            --text: #0f172a;
            --text-muted: #64748b;
            --border: #e2e8f0;
            --radius: 16px;
        }}
        body {{
            font-family: 'Inter', sans-serif;
            background: var(--bg);
            color: var(--text);
            padding: 40px 20px;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .checkout-box {{
            background: white;
            width: 100%;
            max-width: 480px;
            border-radius: var(--radius);
            box-shadow: 0 10px 30px rgba(15,50,118,0.12);
            border: 1px solid var(--border);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #0f3276 0%, #1a4fa0 100%);
            padding: 24px;
            color: white;
            text-align: center;
        }}
        .header h2 {{ font-size: 20px; font-weight: 800; letter-spacing: -0.3px; }}
        .header p {{ font-size: 12px; color: rgba(255,255,255,0.8); margin-top: 4px; }}
        .body {{
            padding: 28px;
        }}
        .summary-card {{
            background: #f8fafc;
            border-radius: 12px;
            padding: 20px;
            border: 1px solid var(--border);
            margin-bottom: 24px;
        }}
        .summary-title {{
            font-size: 13px;
            font-weight: 700;
            color: var(--primary-dark);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 14px;
            border-bottom: 1.5px solid var(--primary-light);
            padding-bottom: 6px;
        }}
        .summary-row {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 10px;
            font-size: 13.5px;
        }}
        .summary-row:last-child {{ margin-bottom: 0; }}
        .label {{ color: var(--text-muted); font-weight: 500; }}
        .value {{ color: var(--text); font-weight: 700; }}
        
        .amount-card {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: #eff6ff;
            border: 1px solid #bfdbfe;
            padding: 16px 20px;
            border-radius: 12px;
            margin-bottom: 24px;
        }}
        .amount-label {{ font-size: 14px; font-weight: 600; color: var(--primary-dark); }}
        .amount-val {{ font-size: 24px; font-weight: 800; color: var(--primary-dark); }}

        .pay-btn {{
            width: 100%;
            background: #16a34a;
            color: white;
            border: none;
            padding: 14px 20px;
            border-radius: 10px;
            font-size: 15px;
            font-weight: 700;
            cursor: pointer;
            transition: background 0.2s;
            box-shadow: 0 4px 12px rgba(22,163,74,0.25);
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }}
        .pay-btn:hover {{ background: #15803d; }}
        .pay-btn:disabled {{ background: #a3a3a3; cursor: not-allowed; box-shadow: none; }}
        
        .footer {{
            text-align: center;
            font-size: 11px;
            color: var(--text-muted);
            margin-top: 20px;
        }}
    </style>
</head>
<body>

    <div class="checkout-box">
        <div class="header">
            <h2>🏥 {hospital.name}</h2>
            <p>सुरक्षित ओपीडी भुगतान पोर्टल (Secure Payment Gateway)</p>
        </div>
        <div class="body">
            <div class="summary-card">
                <div class="summary-title">अपॉइंटमेंट सारांश</div>
                <div class="summary-row">
                    <span class="label">मरीज़ का नाम:</span>
                    <span class="value">{patient.first_name} {patient.last_name}</span>
                </div>
                <div class="summary-row">
                    <span class="label">मोबाइल नंबर:</span>
                    <span class="value">{patient.phone}</span>
                </div>
                <div class="summary-row">
                    <span class="label">डॉक्टर का नाम:</span>
                    <span class="value">Dr. {doctor.first_name} {doctor.last_name} ({department.name})</span>
                </div>
                <div class="summary-row">
                    <span class="label">दिनांक व समय:</span>
                    <span class="value">{appt_display_time}</span>
                </div>
                <div class="summary-row">
                    <span class="label">भुगतान स्थिति:</span>
                    <span class="value" style="color: var(--yellow);">⏳ Payment Pending</span>
                </div>
            </div>

            <div class="amount-card">
                <span class="amount-label">कुल भुगतान राशि:</span>
                <span class="amount-val">₹{amount}</span>
            </div>

            <button class="pay-btn" id="payBtn" onclick="processPayment()">
                🔒 भुगतान करें (Pay ₹{amount})
            </button>
            
            <div class="footer">
                🛡️ PCI-DSS अनुपालन • 256-Bit SSL सुरक्षित एन्क्रिप्शन
            </div>
        </div>
    </div>

    <script src="https://checkout.razorpay.com/v1/checkout.js"></script>
    <script>
        async function processPayment() {{
            const btn = document.getElementById('payBtn');
            btn.disabled = true;
            btn.textContent = '🔄 Order बन रहा है...';

            try {{
                // Step 1: Create Razorpay Order on backend
                const orderRes = await fetch('/payment/create-order?appt={appointment.id}', {{
                    method: 'POST'
                }});
                const orderData = await orderRes.json();

                if (orderData.already_paid) {{
                    document.body.innerHTML = `<div style="text-align:center;padding:60px;font-family:Inter,sans-serif"><div style="font-size:56px">🎉</div><h2 style="color:#0f3276">पेमेंट पहले हो चुका है!</h2><p style="color:#64748b">आपकी अपॉइंटमेंट पहले से Confirmed है।</p></div>`;
                    return;
                }}

                // Step 2: Open Razorpay Checkout Modal
                const options = {{
                    key: orderData.key_id,
                    amount: orderData.amount,
                    currency: orderData.currency,
                    name: 'CP Tiwari Hospital',
                    description: 'OPD Appointment Fee',
                    handler: async function(response) {{
                        // Step 3: Verify payment on backend
                        const formData = new FormData();
                        if (response.razorpay_order_id) {{
                            formData.append('razorpay_order_id', response.razorpay_order_id);
                        }}
                        formData.append('razorpay_payment_id', response.razorpay_payment_id);
                        if (response.razorpay_signature) {{
                            formData.append('razorpay_signature', response.razorpay_signature);
            
                "key": "rzp_test_TDfSGFZwtVgpme",
                "amount": {int(amount * 100)}, // in paise
                "currency": "INR",
                "name": "{hospital.name}",
                "description": "Appointment Booking",
                "handler": async function (response){{
                    // Payment successful, call backend confirm
                    btn.innerHTML = 'पेमेंट कन्फर्म हो रहा है...';
                    try {{
                        const res = await fetch('/api/v1/payment/confirm', {{
                            method: 'POST',
                            headers: {{
                                'Content-Type': 'application/json'
                            }},
                            body: JSON.stringify({{ appointment_id: "{appointment.id}", amount: {amount} }})
                        }});
                        if (res.ok) {{
                            btn.innerHTML = '✅ पेमेंट सफल (Success)';
                            setTimeout(() => {{
                                window.location.reload();
                            }}, 1500);
                        }} else {{
                            alert("Payment confirmed but failed to update status.");
                            btn.innerHTML = '🔒 भुगतान करें (Pay ₹{amount})';
                            btn.disabled = false;
                        }}
                    }} catch (e) {{
                        alert("Network error updating payment status.");
                        btn.innerHTML = '🔒 भुगतान करें (Pay ₹{amount})';
                        btn.disabled = false;
                    }}
                }},
                "prefill": {{
                    "name": "{patient.first_name} {patient.last_name}",
                    "contact": "{patient.phone}"
                }},
                "theme": {{
                    "color": "#0f3276"
                }}
            }};
            
            var rzp1 = new Razorpay(options);
            rzp1.on('payment.failed', function (response){{
                alert("Payment Failed: " + response.error.description);
                btn.innerHTML = '🔒 भुगतान करें (Pay ₹{amount})';
                btn.disabled = false;
            }});
            
            rzp1.open();
        }}
    </script>
</body>
</html>"""
    
    return HTMLResponse(content=checkout_html)


# ==========================================
# RAZORPAY — CREATE ORDER
# ==========================================

@router.post("/payment/create-order", tags=["payment"])
async def create_razorpay_order(
    appt: str = Query(..., description="Appointment ID"),
    db: AsyncSession = Depends(get_db)
):
    """Creates a Razorpay Order and returns order_id + key_id to the frontend."""
    from app.database.models.appointment import Appointment, Doctor
    import razorpay

    stmt = select(Appointment).where(Appointment.id == appt)
    appointment = (await db.execute(stmt)).scalar_one_or_none()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found.")

    if appointment.status == "SCHEDULED":
        return {"already_paid": True}

    doctor_stmt = select(Doctor).where(Doctor.id == appointment.doctor_id)
    doctor = (await db.execute(doctor_stmt)).scalar_one_or_none()
    amount_inr = doctor.opd_fees if (doctor and doctor.opd_fees is not None) else 500
    amount_paise = amount_inr * 100  # Razorpay uses paise

    # If secret is blank, don't request Order ID from Razorpay (use direct integration fallback)
    order_id = None
    if settings.RAZORPAY_KEY_SECRET:
        try:
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            order_data = {
                "amount": amount_paise,
                "currency": "INR",
                "receipt": f"rcpt_{appointment.id[-8:]}",
                "notes": {
                    "appointment_id": appointment.id,
                    "doctor": appointment.doctor_id
                }
            }
            import asyncio as _asyncio
            order = await _asyncio.to_thread(client.order.create, data=order_data)
            order_id = order["id"]
        except Exception as e:
            logger.error(f"Razorpay order creation failed: {str(e)}")

    return {
        "order_id": order_id,
        "key_id": settings.RAZORPAY_KEY_ID,
        "amount": amount_paise,
        "amount_inr": amount_inr,
        "appointment_id": appointment.id,
        "currency": "INR"
    }


# ==========================================
# RAZORPAY — VERIFY PAYMENT & TRIGGER INTAKE
# ==========================================

@router.post("/payment/verify", tags=["payment"])
async def verify_razorpay_payment(
    razorpay_order_id: Optional[str] = Form(None),
    razorpay_payment_id: str = Form(...),
    razorpay_signature: Optional[str] = Form(None),
    appointment_id: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """Verifies Razorpay payment signature, marks appointment SCHEDULED, sends WhatsApp, and triggers AI intake call."""
    import razorpay
    import hmac
    import hashlib
    from app.database.models.appointment import Appointment, Patient, Doctor, AppointmentStatusHistory

    # 1. Verify digital signature if key secret is configured and signature/order details exist
    if settings.RAZORPAY_KEY_SECRET and razorpay_order_id and razorpay_signature:
        key_secret = settings.RAZORPAY_KEY_SECRET.encode()
        message = f"{razorpay_order_id}|{razorpay_payment_id}".encode()
        expected_sig = hmac.new(key_secret, message, hashlib.sha256).hexdigest()
        if expected_sig != razorpay_signature:
            raise HTTPException(status_code=400, detail="Payment signature verification failed.")
    else:
        logger.warning("Bypassing HMAC signature check because RAZORPAY_KEY_SECRET is not configured or direct payment was used.")

    # 2. Load appointment
    stmt = select(Appointment).where(Appointment.id == appointment_id)
    appointment = (await db.execute(stmt)).scalar_one_or_none()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found.")

    if appointment.status == "SCHEDULED":
        return {"success": True, "message": "Already confirmed"}

    # 3. Update appointment status
    old_status = appointment.status
    appointment.status = "SCHEDULED"
    appointment.updated_at = datetime.now()

    status_history = AppointmentStatusHistory(
        id=str(uuid.uuid4()),
        appointment_id=appointment.id,
        previous_status=old_status,
        new_status="SCHEDULED",
        change_reason=f"Razorpay payment verified. Payment ID: {razorpay_payment_id}"
    )
    db.add(status_history)
    await db.flush()

    # 4. Load patient and doctor
    patient_stmt = select(Patient).where(Patient.id == appointment.patient_id)
    patient = (await db.execute(patient_stmt)).scalar_one_or_none()
    doctor_stmt = select(Doctor).where(Doctor.id == appointment.doctor_id)
    doctor = (await db.execute(doctor_stmt)).scalar_one_or_none()

    await db.commit()

    # 5. Send payment confirmed WhatsApp to patient
    if patient and doctor:
        from app.services.whatsapp import WhatsAppNotificationService
        wa_service = WhatsAppNotificationService()
        wa_details = {
            "appointment_id": appointment.id,
            "patient_name": f"{patient.first_name} {patient.last_name}".strip(),
            "patient_phone": patient.phone,
            "doctor_name": f"Dr. {doctor.first_name} {doctor.last_name}",
            "appointment_datetime": appointment.appointment_datetime.isoformat(),
            "reason": appointment.reason
        }
        asyncio.create_task(wa_service.send_payment_confirmation(wa_details))

        # 6. Start WhatsApp AI intake conversation after a short delay
        async def start_whatsapp_intake():
            await asyncio.sleep(5)  # 5 seconds after payment confirmation WhatsApp
            try:
                from app.services.whatsapp_intake import get_intake_service
                intake_svc = get_intake_service()
                await intake_svc.start_intake_conversation(
                    appointment_id=appointment.id,
                    patient_name=f"{patient.first_name} {patient.last_name}".strip(),
                    patient_phone=patient.phone,
                    doctor_name=f"Dr. {doctor.first_name} {doctor.last_name}",
                    appointment_datetime=appointment.appointment_datetime.isoformat()
                )
            except Exception as intake_err:
                logger.error(f"WhatsApp intake start failed (non-critical): {str(intake_err)}")

        asyncio.create_task(start_whatsapp_intake())

    return {
        "success": True,
        "message": "Payment verified. Appointment confirmed. WhatsApp intake conversation started.",
        "phone": patient.phone if patient else ""
    }


# ==========================================
# LEGACY — SIMULATED PAYMENT CONFIRM (kept for backward compat)
# ==========================================

@router.post("/payment/confirm/{appointment_id}", tags=["payment"])
async def payment_confirmation_webhook(
    appointment_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Simulated / test payment confirmation fallback.
    Updates appointment status to SCHEDULED and dispatches WhatsApp notification.
    """
    from app.database.models.appointment import Appointment, Patient, Doctor, AppointmentStatusHistory
    from app.services.whatsapp import WhatsAppNotificationService

    try:
        stmt = select(Appointment).where(Appointment.id == appointment_id)
        appointment = (await db.execute(stmt)).scalar_one_or_none()
        if not appointment:
            raise HTTPException(status_code=404, detail="Appointment not found.")

        if appointment.status == "SCHEDULED":
            return {"success": True, "message": "Already confirmed", "phone": "N/A"}

        old_status = appointment.status
        appointment.payment_status = "PAID"
        appointment.updated_at = datetime.now()

        status_history = AppointmentStatusHistory(
            id=str(uuid.uuid4()),
            appointment_id=appointment.id,
            previous_status=old_status,
            new_status="SCHEDULED",
            change_reason="Payment confirmed successfully via online portal"
        )
        db.add(status_history)
        await db.flush()

        patient_stmt = select(Patient).where(Patient.id == appointment.patient_id)
        patient = (await db.execute(patient_stmt)).scalar_one_or_none()
        doctor_stmt = select(Doctor).where(Doctor.id == appointment.doctor_id)
        doctor = (await db.execute(doctor_stmt)).scalar_one_or_none()

        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to confirm payment for appointment {appointment_id}: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail="Internal error during payment confirmation.")

    if patient and doctor:
        wa_service = WhatsAppNotificationService()
        wa_details = {
            "appointment_id": appointment.id,
            "patient_name": f"{patient.first_name} {patient.last_name}".strip(),
            "patient_phone": patient.phone,
            "doctor_name": f"Dr. {doctor.first_name} {doctor.last_name}",
            "appointment_datetime": appointment.appointment_datetime.isoformat(),
            "reason": appointment.reason
        }
        try:
            await wa_service.send_payment_confirmation(wa_details)
        except Exception as wa_err:
            logger.error(f"WhatsApp payment confirmation failed: {str(wa_err)}")

    return {
        "success": True,
        "message": "Payment confirmed and WhatsApp dispatched.",
        "phone": patient.phone if patient else ""
    }


@router.post("/appointments/{appointment_id}/status", tags=["receptionist"])
async def update_appointment_status(
    appointment_id: str,
    new_status: str = Form(..., description="COMPLETED, CANCELLED, MISSED, or RESCHEDULED"),
    new_datetime: Optional[str] = Form(None, description="ISO datetime for RESCHEDULED status"),
    cutoff_note: Optional[str] = Form(None, description="Arrival cutoff instruction for patient"),
    cancellation_reason: Optional[str] = Form(None, description="Reason for cancellation (for refund WhatsApp)"),
    db: AsyncSession = Depends(get_db)
):
    """
    Receptionist action endpoint to update appointment status.
    On RESCHEDULED, updates time and sends WhatsApp to patient.
    """
    from app.database.models.appointment import Appointment, Patient, Doctor, AppointmentStatusHistory
    from app.services.whatsapp import WhatsAppNotificationService

    stmt = select(Appointment).where(Appointment.id == appointment_id)
    appointment = (await db.execute(stmt)).scalar_one_or_none()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found.")

    old_status = appointment.status

    # Validate reschedule rules
    if new_status == "RESCHEDULED":
        # 1. Payment completion check: Unpaid appointments cannot be rescheduled
        if appointment.payment_status != "PAID" or old_status == "PENDING_PAYMENT":
            raise HTTPException(status_code=400, detail="Reschedule is not allowed for unpaid appointments.")
        
        # 2. 48-hour deadline check for missed / expired appointments
        now = datetime.now()
        if old_status == "MISSED" or appointment.appointment_datetime < now:
            if now > appointment.appointment_datetime + timedelta(hours=48):
                raise HTTPException(status_code=400, detail="Reschedule window expired. Rescheduling is only allowed within 48 hours of missed appointment time.")

        # 3. Reschedule count check (limit: 1 time)
        history_check_stmt = select(AppointmentStatusHistory).where(
            and_(
                AppointmentStatusHistory.appointment_id == appointment_id,
                AppointmentStatusHistory.new_status == "RESCHEDULED"
            )
        )
        existing_reschedules = (await db.execute(history_check_stmt)).all()
        if len(existing_reschedules) >= 1:
            raise HTTPException(status_code=400, detail="appointment already rescheduled once")

        if not new_datetime:
            raise HTTPException(status_code=400, detail="New datetime required for rescheduling")

        try:
            appointment.appointment_datetime = datetime.fromisoformat(new_datetime)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid datetime format. Use ISO format.")

    appointment.status = new_status
    appointment.updated_at = datetime.now()

    history = AppointmentStatusHistory(
        id=str(uuid.uuid4()),
        appointment_id=appointment.id,
        previous_status=old_status,
        new_status=new_status,
        change_reason=f"Receptionist action: {new_status}"
    )
    db.add(history)
    await db.flush()

    patient_stmt = select(Patient).where(Patient.id == appointment.patient_id)
    patient = (await db.execute(patient_stmt)).scalar_one_or_none()
    doctor_stmt = select(Doctor).where(Doctor.id == appointment.doctor_id)
    doctor = (await db.execute(doctor_stmt)).scalar_one_or_none()

    await db.commit()

    # Send WhatsApp notification for reschedule
    if new_status == "RESCHEDULED" and patient and new_datetime:
        wa_service = WhatsAppNotificationService()
        wa_details = {
            "patient_name": f"{patient.first_name} {patient.last_name}".strip(),
            "patient_phone": patient.phone,
            "doctor_name": f"Dr. {doctor.first_name} {doctor.last_name}" if doctor else "Doctor",
            "new_datetime": new_datetime,
            "cutoff_note": cutoff_note or ""
        }
        asyncio.create_task(wa_service.send_reschedule_notification(wa_details))

    # Send WhatsApp notification for missed appointment
    elif new_status == "MISSED" and patient:
        wa_service = WhatsAppNotificationService()
        wa_details = {
            "patient_name": f"{patient.first_name} {patient.last_name}".strip(),
            "patient_phone": patient.phone,
            "doctor_name": f"Dr. {doctor.first_name} {doctor.last_name}" if doctor else "Doctor",
            "appointment_datetime": appointment.appointment_datetime.isoformat(),
            "reason": appointment.reason or "General consultation"
        }
        asyncio.create_task(wa_service.send_missed_notification(wa_details))

    # Send WhatsApp notification for cancellation (Refund info if paid)
    elif new_status == "CANCELLED" and patient:
        wa_service = WhatsAppNotificationService()
        wa_details = {
            "patient_name": f"{patient.first_name} {patient.last_name}".strip(),
            "patient_phone": patient.phone,
            "doctor_name": f"Dr. {doctor.first_name} {doctor.last_name}" if doctor else "Doctor",
            "appointment_datetime": appointment.appointment_datetime.isoformat(),
            "reason": cancellation_reason or "अस्पताल के अनुरोध पर",
            "is_paid": old_status == "SCHEDULED"
        }
        asyncio.create_task(wa_service.send_cancellation_refund_notification(wa_details))

    return {"success": True, "appointment_id": appointment_id, "new_status": new_status}


@router.post("/appointments/{appointment_id}/complete", tags=["doctor"])
async def complete_consultation(
    appointment_id: str,
    clinical_notes: str = Form("", description="Doctor's clinical summary/notes"),
    prescription: str = Form("", description="Prescription medicines details"),
    follow_up_date: Optional[str] = Form(None, description="Follow-up date in YYYY-MM-DD format"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Saves consultation summary, writes prescription,
    transitions status to COMPLETED, and sends prescription details via WhatsApp.
    """
    from app.services.whatsapp import WhatsAppNotificationService

    # 1. Fetch user roles to verify authorization
    role_stmt = select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == current_user.id)
    roles = (await db.execute(role_stmt)).scalars().all()
    if "DOCTOR" not in roles and "ADMIN" not in roles and "RECEPTIONIST" not in roles and "SUPER_ADMIN" not in roles:
        raise HTTPException(status_code=403, detail="Only Doctors, Receptionists, or Admins can complete a consultation.")

    try:
        # 2. Fetch appointment details
        appt_stmt = select(Appointment).where(
            and_(
                Appointment.id == appointment_id,
                Appointment.hospital_id == current_user.hospital_id
            )
        )
        appt = (await db.execute(appt_stmt)).scalar_one_or_none()
        if not appt:
            raise HTTPException(status_code=404, detail="Appointment not found in this hospital.")

        old_status = appt.status
        if old_status == "COMPLETED":
            raise HTTPException(status_code=400, detail="Consultation already completed.")

        # 3. Transition status to COMPLETED and consultation to DONE
        appt.status = "COMPLETED"
        appt.consultation_status = "DONE"
        appt.updated_at = datetime.now()

        # 4. Save Status History
        from app.database.models.appointment import AppointmentStatusHistory
        history = AppointmentStatusHistory(
            id=str(uuid.uuid4()),
            appointment_id=appt.id,
            previous_status=old_status,
            new_status="COMPLETED",
            changed_by_user_id=current_user.id,
            change_reason="Consultation completed by doctor."
        )
        db.add(history)

        # 5. Parse follow-up date
        f_up_date = None
        if follow_up_date and follow_up_date.strip() and follow_up_date.strip().lower() not in ["", "null", "undefined"]:
            try:
                f_up_date = datetime.strptime(follow_up_date.strip(), "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format for follow_up_date. Use YYYY-MM-DD.")

        # 6. Save or Update ConsultationNote
        from app.database.models.appointment import ConsultationNote
        note_stmt = select(ConsultationNote).where(ConsultationNote.appointment_id == appointment_id)
        note = (await db.execute(note_stmt)).scalar_one_or_none()
        if not note:
            note = ConsultationNote(
                id=str(uuid.uuid4()),
                appointment_id=appointment_id,
                patient_id=appt.patient_id,
                doctor_id=appt.doctor_id,
                clinical_notes=clinical_notes,
                prescription=prescription,
                follow_up_date=f_up_date
            )
            db.add(note)
        else:
            note.clinical_notes = clinical_notes
            note.prescription = prescription
            note.follow_up_date = f_up_date

        # Fetch extra info before commit
        patient_stmt = select(Patient).where(Patient.id == appt.patient_id)
        patient = (await db.execute(patient_stmt)).scalar_one_or_none()
        
        doctor_stmt = select(Doctor).where(Doctor.id == appt.doctor_id)
        doctor = (await db.execute(doctor_stmt)).scalar_one_or_none()
        doc_name = f"Dr. {doctor.first_name} {doctor.last_name}" if doctor else "Doctor"

        hosp_stmt = select(Hospital).where(Hospital.id == appt.hospital_id)
        hospital = (await db.execute(hosp_stmt)).scalar_one_or_none()
        hosp_name = hospital.name if hospital else "Hospital"

        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.error(f"Error completing consultation transaction: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail="Failed to complete consultation.")

    # 7. Send WhatsApp Prescription details
    if patient and patient.phone:
        wa_service = WhatsAppNotificationService()
        wa_details = {
            "phone": patient.phone,
            "patient_name": f"{patient.first_name} {patient.last_name}".strip(),
            "doctor_name": doc_name,
            "hospital_name": hosp_name,
            "clinical_notes": clinical_notes,
            "prescription": prescription,
            "follow_up_date": follow_up_date or "N/A"
        }
        try:
            await wa_service.send_prescription_notification(wa_details)
        except Exception as wa_err:
            logger.error(f"WhatsApp prescription notification failed: {str(wa_err)}")

    return {
        "success": True,
        "message": "Consultation completed and prescription sent to patient.",
        "appointment_id": appointment_id
    }


# ==========================================
# RECEPTIONIST — FETCH BOOKED SLOTS API
# ==========================================

@router.get("/receptionist/booked-slots", tags=["receptionist"])
async def get_booked_slots(
    doctor_id: str = Query(...),
    date_str: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns a list of start times for all booked appointments of a doctor on a specific date.
    Used by the dashboard to show busy slots in RED inside the reschedule modal.
    """
    try:
        from datetime import date as date_type
        target_date = date_type.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    start_dt = datetime.combine(target_date, datetime.min.time())
    end_dt = datetime.combine(target_date, datetime.max.time())

    # Fetch active booked appointments (excluding cancelled)
    stmt = (
        select(Appointment)
        .where(
            and_(
                Appointment.doctor_id == doctor_id,
                Appointment.appointment_datetime >= start_dt,
                Appointment.appointment_datetime <= end_dt,
                Appointment.status.in_(["SCHEDULED", "PENDING_PAYMENT", "RESCHEDULED"])
            )
        )
    )
    appointments = (await db.execute(stmt)).scalars().all()
    booked_times = [appt.appointment_datetime.strftime("%I:%M %p") for appt in appointments]
    
    # Dynamically generate all possible slots based on schedule & leaves
    all_slots = []
    from app.database.models.appointment import Doctor, DoctorSchedule, DoctorLeave
    doc_stmt = select(Doctor).where(Doctor.id == doctor_id, Doctor.is_active == True)
    doctor = (await db.execute(doc_stmt)).scalar_one_or_none()
    
    if doctor:
        day_of_week = target_date.isoweekday()
        
        # Check if doctor is on approved leave
        leave_stmt = select(DoctorLeave).where(
            and_(
                DoctorLeave.doctor_id == doctor_id,
                DoctorLeave.start_date <= target_date,
                DoctorLeave.end_date >= target_date,
                DoctorLeave.status == "APPROVED"
            )
        )
        leave = (await db.execute(leave_stmt)).scalar_one_or_none()
        
        if not leave:
            sched_stmt = select(DoctorSchedule).where(
                and_(
                    DoctorSchedule.doctor_id == doctor_id,
                    DoctorSchedule.day_of_week == day_of_week
                )
            )
            schedules = (await db.execute(sched_stmt)).scalars().all()
            for sched in schedules:
                if sched.slot_duration_minutes and sched.slot_duration_minutes > 0:
                    from datetime import timedelta
                    current_time = datetime.combine(target_date, sched.start_time)
                    end_time_limit = datetime.combine(target_date, sched.end_time)
                    dur = timedelta(minutes=sched.slot_duration_minutes)
                    
                    while current_time + dur <= end_time_limit:
                        # Format as %I:%M %p, but strictly avoiding leading zeros if we want to match frontend... 
                        # Wait, frontend uses "09:00 AM". So "%I:%M %p" is exactly what frontend has.
                        all_slots.append(current_time.strftime("%I:%M %p"))
                        current_time += dur
                        
    # Sort all_slots chronologically just in case
    def sort_key(time_str):
        from datetime import datetime
        return datetime.strptime(time_str, "%I:%M %p")
    all_slots = sorted(list(set(all_slots)), key=sort_key)
    
    return {"booked_slots": booked_times, "all_slots": all_slots}

@router.post("/appointments/mark-missed", tags=["hospital"])
async def mark_past_appointments_missed(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Marks all CONFIRMED or SCHEDULED appointments that are in the past as MISSED."""
    hosp_id = current_user.hospital_id if current_user.hospital_id else "hosp_default"
    now = datetime.now()
    
    # Find past appointments not yet completed or cancelled
    stmt = select(Appointment).where(
        Appointment.hospital_id == hosp_id,
        Appointment.appointment_datetime < now,
        Appointment.status.in_(["SCHEDULED", "CONFIRMED"])
    )
    past_appts = (await db.execute(stmt)).scalars().all()
    
    count = 0
    
    # Pre-fetch wa_service
    from app.services.whatsapp import WhatsAppNotificationService
    from app.database.models.appointment import Patient, Doctor, Hospital
    wa_service = WhatsAppNotificationService()
    
    for appt in past_appts:
        appt.status = "MISSED"
        appt.consultation_status = "MISSED"
        count += 1
        
        # Send WhatsApp Notification
        try:
            pat_stmt = select(Patient).where(Patient.id == appt.patient_id)
            patient = (await db.execute(pat_stmt)).scalar_one_or_none()
            doc_stmt = select(Doctor).where(Doctor.id == appt.doctor_id)
            doctor = (await db.execute(doc_stmt)).scalar_one_or_none()
            hosp_stmt = select(Hospital).where(Hospital.id == appt.hospital_id)
            hospital = (await db.execute(hosp_stmt)).scalar_one_or_none()
            
            if patient and doctor and hospital:
                details = {
                    "patient_phone": patient.phone,
                    "patient_name": f"{patient.first_name} {patient.last_name}".strip(),
                    "doctor_name": doctor.name,
                    "date": appt.appointment_datetime.strftime("%Y-%m-%d"),
                    "time": appt.appointment_datetime.strftime("%I:%M %p"),
                    "hospital_name": hospital.name,
                    "hospital_id": hospital.id
                }
                import asyncio
                asyncio.create_task(wa_service.send_missed_notification(details))
        except Exception as wa_err:
            from app.core.logging import logger
            logger.error(f"Failed to send missed WA msg for {appt.id}: {wa_err}")
            
    if count > 0:
        await db.commit()
        
    return {"success": True, "marked_count": count}


class BulkCancelRequest(BaseModel):
    doctor_id: str
    target_date: date
    reason: str

@router.post("/appointments/bulk-cancel", tags=["hospital"])
async def bulk_cancel_appointments(
    payload: BulkCancelRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Cancels all pending/scheduled appointments for a doctor on a specific date."""
    hosp_id = current_user.hospital_id if current_user.hospital_id else "hosp_default"
    
    # 1. Fetch relevant appointments
    start_dt = datetime.combine(payload.target_date, datetime.min.time())
    end_dt = datetime.combine(payload.target_date, datetime.max.time())
    
    stmt = select(Appointment).where(
        Appointment.hospital_id == hosp_id,
        Appointment.doctor_id == payload.doctor_id,
        Appointment.appointment_datetime >= start_dt,
        Appointment.appointment_datetime <= end_dt,
        Appointment.status.in_(["SCHEDULED", "CONFIRMED", "PENDING_PAYMENT"])
    )
    appts_to_cancel = (await db.execute(stmt)).scalars().all()
    
    # 2. Cancel and notify
    from app.engines.appointment import AppointmentEngine
    engine = AppointmentEngine(db)
    
    count = 0
    for appt in appts_to_cancel:
        res = await engine.cancel_appointment(appt.id, reason=payload.reason)
        if res.get("code") == "CANCELLED":
            count += 1
            
    if count > 0:
        await db.commit()
        
    return {"success": True, "cancelled_count": count}


@router.get("/hospital/profile", tags=["hospital"])
async def get_hospital_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    hosp_id = current_user.hospital_id if current_user.hospital_id else "hosp_default"
    hosp_stmt = select(Hospital).where(Hospital.id == hosp_id)
    hosp = (await db.execute(hosp_stmt)).scalar_one_or_none()
    if not hosp:
        raise HTTPException(status_code=404, detail="Hospital not found.")

    # Also fetch the settings (whatsapp_number, greeting_prompt, full_custom_prompt)
    from app.database.models.appointment import HospitalSetting
    
    settings_stmt = select(HospitalSetting).where(HospitalSetting.hospital_id == hosp_id)
    settings_rows = (await db.execute(settings_stmt)).scalars().all()
    
    settings_dict = {}
    for row in settings_rows:
        settings_dict[row.setting_key] = row.setting_value

    # Fallback to User table if not in settings yet
    admin_stmt = (
        select(User)
        .join(UserRole, UserRole.user_id == User.id)
        .join(Role, UserRole.role_id == Role.id)
        .where(User.hospital_id == hosp_id, Role.name == "ADMIN")
    )
    admin_user = (await db.execute(admin_stmt)).scalars().first()
    admin_username = settings_dict.get("admin_username", admin_user.username if admin_user else "")
    admin_password = settings_dict.get("admin_password", "••••••••")

    helpline_number = settings_dict.get("twilio_helpline") or hosp.phone or ""

    return {
        "id": hosp.id,
        "name": hosp.name,
        "phone": helpline_number,
        "helpline": helpline_number,
        "email": hosp.email,
        "address": hosp.address,
        "is_active": hosp.is_active,
        "slug": hosp.slug,
        "admin_username": admin_username,
        "admin_password": admin_password,
        "settings": {
            "twilio_helpline": helpline_number,
            "twilio_account_sid": settings_dict.get("twilio_account_sid", ""),
            "twilio_auth_token": settings_dict.get("twilio_auth_token", ""),
            "whatsapp_number": settings_dict.get("whatsapp_number", ""),
            "greeting_prompt": settings_dict.get("greeting_prompt", ""),
            "full_custom_prompt": settings_dict.get("full_custom_prompt", "")
        }
    }


@router.put("/hospital/profile", tags=["hospital"])
async def update_hospital_profile(
    name: str = Form(...),
    address: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),  # Made optional, ignored on update
    email: Optional[str] = Form(None),
    admin_username: Optional[str] = Form(None),
    admin_password: Optional[str] = Form(None),
    current_admin: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    role_stmt = select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == current_admin.id)
    roles = (await db.execute(role_stmt)).scalars().all()
    if "ADMIN" not in roles:
        raise HTTPException(status_code=403, detail="Only Hospital Admins can update hospital profile.")

    hosp_id = current_admin.hospital_id if current_admin.hospital_id else "hosp_default"
    hosp_stmt = select(Hospital).where(Hospital.id == hosp_id)
    hosp = (await db.execute(hosp_stmt)).scalar_one_or_none()
    if not hosp:
        raise HTTPException(status_code=404, detail="Hospital not found.")

    hosp.name = name
    hosp.address = address
    hosp.email = email
    # Note: hosp.phone and twilio_helpline are NOT modified here. Only Platform Owner can configure them.

    # Update admin user credentials in database and plain text configurations
    admin_stmt = (
        select(User)
        .join(UserRole, UserRole.user_id == User.id)
        .join(Role, UserRole.role_id == Role.id)
        .where(User.hospital_id == hosp_id, Role.name == "ADMIN")
    )
    admin_user = (await db.execute(admin_stmt)).scalars().first()
    if admin_user:
        if admin_username:
            admin_user.username = admin_username
            un_stmt = select(HospitalSetting).where(HospitalSetting.hospital_id == hosp_id, HospitalSetting.setting_key == "admin_username")
            un_setting = (await db.execute(un_stmt)).scalar_one_or_none()
            if un_setting:
                un_setting.setting_value = admin_username
            else:
                db.add(HospitalSetting(id=str(uuid.uuid4()), hospital_id=hosp_id, setting_key="admin_username", setting_value=admin_username))
                
        if admin_password and admin_password.strip():
            from app.core.dependencies import hash_password
            admin_user.password_hash = hash_password(admin_password)
            pw_stmt = select(HospitalSetting).where(HospitalSetting.hospital_id == hosp_id, HospitalSetting.setting_key == "admin_password")
            pw_setting = (await db.execute(pw_stmt)).scalar_one_or_none()
            if pw_setting:
                pw_setting.setting_value = admin_password
            else:
                db.add(HospitalSetting(id=str(uuid.uuid4()), hospital_id=hosp_id, setting_key="admin_password", setting_value=admin_password))

    await db.commit()
    return {"status": "success", "message": "Hospital profile updated successfully"}





@router.post("/hospital/settings", tags=["hospital"])
async def save_hospital_settings(
    whatsapp_number: Optional[str] = Form(None),
    greeting_prompt: Optional[str] = Form(None),
    full_custom_prompt: Optional[str] = Form(None),
    current_admin: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    role_stmt = select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == current_admin.id)
    roles = (await db.execute(role_stmt)).scalars().all()
    if "ADMIN" not in roles:
        raise HTTPException(status_code=403, detail="Only Hospital Admins can update settings.")

    hosp_id = current_admin.hospital_id if current_admin.hospital_id else "hosp_default"
    
    settings_to_save = {
        "whatsapp_number": whatsapp_number,
        "greeting_prompt": greeting_prompt,
        "full_custom_prompt": full_custom_prompt
    }

    from app.database.models.appointment import HospitalSetting
    for key, val in settings_to_save.items():
        if val is not None:
            # Check if setting exists
            stmt = select(HospitalSetting).where(HospitalSetting.hospital_id == hosp_id, HospitalSetting.setting_key == key)
            setting = (await db.execute(stmt)).scalar_one_or_none()
            if setting:
                setting.setting_value = val
            else:
                new_setting = HospitalSetting(
                    id=str(uuid.uuid4()),
                    hospital_id=hosp_id,
                    setting_key=key,
                    setting_value=val
                )
                db.add(new_setting)

    await db.commit()
    return {"status": "success", "message": "Hospital settings saved successfully"}


# ==========================================
# RECEPTIONIST — WALK-IN / MANUAL BOOKING WITH CASH VS ONLINE
# ==========================================

class ReceptionistBookRequest(BaseModel):
    patient_name: str
    patient_phone: str
    patient_gender: Optional[str] = "Male"
    patient_dob: Optional[str] = None
    doctor_id: str
    appointment_datetime: datetime
    reason: Optional[str] = None
    payment_mode: Optional[str] = "CASH" # "CASH" or "ONLINE"
    hospital_id: Optional[str] = None

@router.post("/receptionist/book-appointment", tags=["receptionist"])
async def book_receptionist_appointment(
    req: ReceptionistBookRequest,
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Receptionist Manual Booking Endpoint.
    - Cash Mode: Marks status SCHEDULED, payment_status PAID, sends WhatsApp confirmation without payment link.
    - Online Mode: Marks status PENDING_PAYMENT, payment_status PENDING, sends WhatsApp with checkout link.
    """
    import uuid
    from app.core.logging import logger
    from app.database.models.appointment import Appointment, Patient, Doctor, Hospital

    hosp_id = req.hospital_id or (current_user.hospital_id if current_user and current_user.hospital_id else None)
    if not hosp_id:
        # Fallback to first hospital in DB
        h_stmt = select(Hospital.id).limit(1)
        hosp_id = (await db.execute(h_stmt)).scalar_one_or_none() or "hosp_default"

    clean_phone = req.patient_phone.strip()
    if clean_phone.startswith("whatsapp:"):
        clean_phone = clean_phone.replace("whatsapp:", "").strip()

    # 1. Resolve or create patient
    name_parts = req.patient_name.strip().split(" ", 1)
    p_first = name_parts[0]
    p_last = name_parts[1] if len(name_parts) > 1 else ""

    p_stmt = select(Patient).where(Patient.hospital_id == hosp_id, Patient.phone == clean_phone, Patient.first_name == p_first)
    patient = (await db.execute(p_stmt)).scalars().first()

    payment_mode = (req.payment_mode or "CASH").upper()

    if patient:
        # Idempotency check: if active appointment already exists with same patient, doctor, and time, return it immediately.
        existing_stmt = select(Appointment).where(
            Appointment.patient_id == patient.id,
            Appointment.doctor_id == req.doctor_id,
            Appointment.appointment_datetime == req.appointment_datetime,
            Appointment.status.in_(["SCHEDULED", "PENDING_PAYMENT", "RESCHEDULED"])
        )
        existing = (await db.execute(existing_stmt)).scalar_one_or_none()
        if existing:
            import json
            from app.core.logging import request_id_context
            log_data = {
                "event": "idempotent_receptionist_booking_triggered",
                "patient_id": patient.id,
                "doctor_id": req.doctor_id,
                "time": req.appointment_datetime.isoformat()
            }
            req_id = request_id_context.get()
            if req_id:
                log_data["request_id"] = req_id
            logger.info(json.dumps(log_data))
            return {"success": True, "appointment_id": existing.id, "payment_mode": payment_mode, "idempotent": True}

    try:
        if not patient:
            dob = None
            if req.patient_dob:
                try:
                    dob = datetime.strptime(req.patient_dob, "%Y-%m-%d").date()
                except:
                    dob = datetime.now().date()
            else:
                dob = datetime.now().date()

            patient = Patient(
                id=str(uuid.uuid4()),
                hospital_id=hosp_id,
                first_name=p_first,
                last_name=p_last,
                phone=clean_phone,
                gender=req.patient_gender,
                date_of_birth=dob,
                is_active=True
            )
            db.add(patient)
            await db.flush()

        if payment_mode == "CASH":
            appt_status = "SCHEDULED"
            pay_status = "PAID"
        else:
            appt_status = "PENDING_PAYMENT"
            pay_status = "PENDING"

        appt = Appointment(
            id=str(uuid.uuid4()),
            hospital_id=hosp_id,
            patient_id=patient.id,
            doctor_id=req.doctor_id,
            appointment_datetime=req.appointment_datetime,
            duration_minutes=30,
            status=appt_status,
            payment_status=pay_status,
            payment_method=payment_mode,
            consultation_status="SCHEDULED",
            reason=req.reason or "Walk-in Booking",
            source="RECEPTIONIST_PORTAL",
            booked_by_name=f"{current_user.first_name} {current_user.last_name}".strip() if current_user and hasattr(current_user, 'first_name') else None
        )
        db.add(appt)
        await db.flush()
        await db.commit()
        
        import json
        from app.core.logging import request_id_context
        log_data = {
            "event": "receptionist_appointment_booked",
            "appointment_id": appt.id,
            "doctor_id": req.doctor_id,
            "patient_phone": clean_phone
        }
        req_id = request_id_context.get()
        if req_id:
            log_data["request_id"] = req_id
        logger.info(json.dumps(log_data))
    except Exception as e:
        await db.rollback()
        logger.error(f"Error during receptionist booking database transaction: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Booking failed due to database transaction error: {str(e)}")

    # Trigger WhatsApp notification
    try:
        from app.services.whatsapp import WhatsAppNotificationService
        wa_service = WhatsAppNotificationService()

        doc_stmt = select(Doctor).where(Doctor.id == req.doctor_id)
        doctor = (await db.execute(doc_stmt)).scalar_one_or_none()
        hosp_stmt = select(Hospital).where(Hospital.id == hosp_id)
        hospital = (await db.execute(hosp_stmt)).scalar_one_or_none()

        if doctor and hospital:
            wa_details = {
                "hospital_id": hospital.id,
                "hospital_name": hospital.name,
                "appointment_id": appt.id,
                "patient_name": f"{patient.first_name} {patient.last_name}".strip(),
                "patient_phone": patient.phone,
                "doctor_name": f"{doctor.first_name} {doctor.last_name}".strip(),
                "appointment_datetime": appt.appointment_datetime.isoformat(),
                "reason": appt.reason or "",
                "fees": doctor.opd_fees or 500
            }
            if payment_mode == "CASH":
                asyncio.create_task(wa_service.send_cash_booking_confirmation(wa_details))
            else:
                asyncio.create_task(wa_service.send_patient_confirmation(wa_details))
    except Exception as wa_err:
        logger.error(f"WhatsApp notification failed in receptionist booking: {wa_err}")

    return {
        "success": True,
        "appointment_id": appt.id,
        "payment_status": pay_status,
        "payment_mode": payment_mode,
        "message": f"Appointment booked successfully with {payment_mode} payment."
    }


# ==========================================
# RECEPTIONIST — PATIENT LOOKUP ENGINE (SEARCH API)
# ==========================================

@router.get("/hospital/patients/search", tags=["receptionist"])
async def search_patients_for_receptionist(
    query: str = Query(..., min_length=1, description="10-digit mobile number or patient/family member name"),
    hospital_id: Optional[str] = Query(None),
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    AI Patient Lookup Engine:
    Searches patients by phone number or name, returning primary patient + family members,
    upcoming & history appointments, prescriptions, and payment status (PAID/PENDING).
    """
    from app.database.models.appointment import Patient, Appointment, Doctor, ConsultationNote
    from collections import defaultdict

    hosp_id = hospital_id or (current_user.hospital_id if current_user and current_user.hospital_id else None)
    
    phone_digits = ''.join(c for c in query if c.isdigit())
    clean_q = query.strip()
    
    # 1. Search patients matching phone or name
    p_stmt = select(Patient).where(Patient.is_active == True)

    if phone_digits and len(phone_digits) >= 6:
        last10 = phone_digits[-10:]
        p_stmt = p_stmt.where(
            or_(
                Patient.phone.contains(phone_digits),
                Patient.phone.contains(last10),
                Patient.first_name.ilike(f"%{clean_q}%"),
                Patient.last_name.ilike(f"%{clean_q}%")
            )
        )
    else:
        p_stmt = p_stmt.where(
            or_(
                Patient.first_name.ilike(f"%{clean_q}%"),
                Patient.last_name.ilike(f"%{clean_q}%"),
                Patient.phone.contains(clean_q)
            )
        )

    matched_patients = (await db.execute(p_stmt)).scalars().all()
    if not matched_patients:
        return {"query": clean_q, "total_found": 0, "groups": []}

    # Gather all phones from matched patients to fetch full family tree
    matched_phones = list({p.phone for p in matched_patients if p.phone})

    # Query all family members under those phones
    all_family_stmt = select(Patient).where(Patient.phone.in_(matched_phones), Patient.is_active == True).order_by(Patient.created_at.asc())
    all_family_patients = (await db.execute(all_family_stmt)).scalars().all()

    # Group patients by phone
    phone_to_patients = defaultdict(list)
    for p in all_family_patients:
        phone_to_patients[p.phone].append(p)

    all_patient_ids = [p.id for p in all_family_patients]

    # Fetch all appointments for these patient IDs
    appt_stmt = (
        select(Appointment)
        .options(selectinload(Appointment.doctor))
        .where(Appointment.patient_id.in_(all_patient_ids))
        .order_by(Appointment.appointment_datetime.desc())
    )
    all_appts = (await db.execute(appt_stmt)).scalars().all()

    # Fetch all consultation notes for prescriptions
    appt_ids = [a.id for a in all_appts]
    notes_map = {}
    if appt_ids:
        notes_stmt = select(ConsultationNote).where(ConsultationNote.appointment_id.in_(appt_ids))
        notes = (await db.execute(notes_stmt)).scalars().all()
        notes_map = {n.appointment_id: n for n in notes}

    patient_to_appts = defaultdict(list)
    for a in all_appts:
        patient_to_appts[a.patient_id].append(a)

    now = datetime.now()
    result_groups = []

    for phone_num, members in phone_to_patients.items():
        member_list = []
        for idx, m in enumerate(members):
            m_appts = patient_to_appts[m.id]
            upcoming = []
            history = []

            for a in m_appts:
                doc_name = f"Dr. {a.doctor.first_name} {a.doctor.last_name}" if a.doctor else "Doctor"
                has_presc = a.id in notes_map
                presc_data = None
                if has_presc:
                    cn = notes_map[a.id]
                    presc_data = {
                        "clinical_notes": cn.clinical_notes,
                        "prescription": cn.prescription,
                        "follow_up_date": str(cn.follow_up_date) if cn.follow_up_date else None
                    }

                item = {
                    "appointment_id": a.id,
                    "datetime": a.appointment_datetime.isoformat(),
                    "datetime_display": a.appointment_datetime.strftime("%d %b %Y, %I:%M %p"),
                    "doctor_name": doc_name,
                    "reason": a.reason or "Consultation",
                    "status": a.status,
                    "payment_status": a.payment_status,
                    "payment_method": a.payment_method or "N/A",
                    "has_prescription": has_presc,
                    "prescription": presc_data
                }

                if a.appointment_datetime >= now and a.status not in ["COMPLETED", "CANCELLED"]:
                    upcoming.append(item)
                else:
                    history.append(item)

            # Age calculation
            age = None
            if m.date_of_birth:
                age = (now.date() - m.date_of_birth).days // 365

            member_list.append({
                "id": m.id,
                "name": f"{m.first_name} {m.last_name}".strip(),
                "phone": m.phone,
                "gender": m.gender or "Not Specified",
                "age": age or "N/A",
                "is_primary": (idx == 0),
                "upcoming_appointments": upcoming,
                "history_appointments": history
            })

        result_groups.append({
            "primary_phone": phone_num,
            "total_members": len(member_list),
            "members": member_list
        })

    return {
        "query": clean_q,
        "total_groups": len(result_groups),
        "groups": result_groups
    }