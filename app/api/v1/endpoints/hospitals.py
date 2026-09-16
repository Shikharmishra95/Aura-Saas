import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Form, Query
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
import jwt as _jwt

from app.database.session import get_db
from app.core.dependencies import get_current_user
from app.core.config import settings
from app.core.logging import logger
from app.database.models.call_log import User, Role, UserRole
from app.database.models.appointment import Hospital, Department, Doctor, Appointment, HospitalSetting

router = APIRouter(tags=["hospital"])


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


@router.get("/hospitals", tags=["admin"])
async def list_hospitals(db: AsyncSession = Depends(get_db)):
    """Super Admin: Returns all registered hospitals with their details.
    Optimized: fetches all hospital_settings in ONE bulk query instead of 5 per-hospital queries.
    """
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
        twilio_helpline = s.get("twilio_helpline") or (settings.TWILIO_PHONE_NUMBER if h.id == "hosp_default" else "")
        result.append({
            "id": h.id,
            "name": h.name,
            "slug": h.slug,
            "phone": h.phone or "",
            "email": h.email or "",
            "address": h.address or "",
            "is_active": h.is_active,
            "subscription_plan": h.subscription_plan or "STARTER",
            "ai_voice_enabled": bool(h.ai_voice_enabled),
            "created_at": str(h.created_at),
            "helpline": twilio_helpline,
            "twilio_helpline": twilio_helpline,
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
    if "SUPER_ADMIN" not in roles and current_user.hospital_id != "super_admin":
        raise HTTPException(status_code=403, detail="Unauthorized: Only Platform Owner can delete hospitals.")

    # 1. Fetch Hospital
    hosp_stmt = select(Hospital).where(Hospital.id == hospital_id)
    hospital = (await db.execute(hosp_stmt)).scalar_one_or_none()
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital not found")

    # 2. Delete hospital
    await db.delete(hospital)
    
    # 4. Clean up users
    users_stmt = select(User).where(User.hospital_id == hospital_id)
    users = (await db.execute(users_stmt)).scalars().all()
    for u in users:
        await db.delete(u)

    await db.commit()
    return {"success": True, "message": "Hospital and associated records deleted successfully."}


@router.put("/hospitals/{hospital_id}/toggle-status", tags=["admin"])
async def toggle_hospital_status(
    hospital_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Toggles hospital active/inactive status."""
    stmt = select(Hospital).where(Hospital.id == hospital_id)
    hospital = (await db.execute(stmt)).scalar_one_or_none()
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital not found")
    
    hospital.is_active = not hospital.is_active
    await db.commit()
    return {
        "success": True,
        "is_active": hospital.is_active,
        "message": f"Hospital status updated to {'ACTIVE' if hospital.is_active else 'INACTIVE'}"
    }


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
    if "SUPER_ADMIN" not in roles and current_user.hospital_id != "super_admin":
        raise HTTPException(status_code=403, detail="Unauthorized: Only Platform Owner can configure Twilio.")

    # Sanitize Account SID prefix
    clean_sid = account_sid.strip()
    if not clean_sid.startswith("AC"):
        clean_sid = "AC" + clean_sid
    clean_token = auth_token.strip()

    if len(clean_sid) != 34:
        raise HTTPException(
            status_code=400,
            detail=f"❌ Invalid Twilio Account SID format: Account SID must be exactly 34 characters starting with AC. You entered {len(clean_sid)} characters ('{clean_sid}'). Please check Twilio Console."
        )

    if len(clean_token) != 32:
        raise HTTPException(
            status_code=400,
            detail=f"❌ Incomplete Twilio Auth Token: Twilio Auth Token must be exactly 32 characters. You entered {len(clean_token)} characters ('{clean_token}'). Please click 'Show' in Twilio Console and copy all 32 characters."
        )

    # Validate Twilio credentials live before saving
    try:
        from twilio.rest import Client as TwilioClient
        test_client = TwilioClient(clean_sid, clean_token)
        test_client.api.v2010.account.fetch()
    except Exception as twilio_err:
        err_msg = str(twilio_err)
        logger.error(f"Twilio validation error for hospital {hospital_id} (SID: {clean_sid[:6]}...): {err_msg}")
        raise HTTPException(
            status_code=400,
            detail=f"❌ Twilio Verification Failed: {err_msg}"
        )

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

    hosp_stmt = select(Hospital).where(Hospital.id == hospital_id)
    hospital_record = (await db.execute(hosp_stmt)).scalar_one_or_none()
    if hospital_record:
        if not hospital_record.ai_voice_enabled and "SUPER_ADMIN" not in roles and current_user.hospital_id != "super_admin":
            raise HTTPException(
                status_code=403,
                detail=f"🔒 AI Voice Lines are disabled for your {hospital_record.subscription_plan} Plan. Please Upgrade to Pro or Enterprise Plan to unlock AI Call Bot!"
            )
        hospital_record.phone = helpline.strip()
        db.add(hospital_record)

    await db.commit()
    return {"success": True, "message": "Twilio configuration saved and helpline injected successfully."}


@router.get("/hospital/departments", tags=["hospital"])
async def get_hospital_departments(
    request: Request,
    hospital_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Returns list of active departments scoped to the authenticated hospital or tenant ID."""
    target_hosp_id = hospital_id
    if not target_hosp_id:
        try:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                token_str = auth_header[7:]
                payload = _jwt.decode(token_str, settings.JWT_SECRET_KEY, algorithms=["HS256"])
                target_hosp_id = payload.get("hospital_id", "")
        except Exception:
            pass

    stmt = select(Department).where(Department.is_active == True)
    if target_hosp_id and target_hosp_id != "super_admin":
        stmt = stmt.where(Department.hospital_id == target_hosp_id)
    
    depts = (await db.execute(stmt)).scalars().all()
    
    seen_names = set()
    unique_depts = []
    for d in depts:
        if target_hosp_id and target_hosp_id != "super_admin":
            unique_depts.append({"id": d.id, "name": d.name})
        else:
            if d.name not in seen_names:
                seen_names.add(d.name)
                unique_depts.append({"id": d.id, "name": d.name})

    return unique_depts


@router.get("/hospital/stats", tags=["hospital"])
async def get_hospital_stats(
    request: Request,
    target_date: Optional[str] = Query(None, description="Filter stats by date YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_user)
):
    """Returns analytics dashboard metrics for a hospital, with optional per-day filtering."""
    role_stmt = select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == current_admin.id)
    db_roles = (await db.execute(role_stmt)).scalars().all()

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
                doc_bookings[doc.id]["revenue"] += doc.opd_fees if doc.opd_fees is not None else 500
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

    settings_stmt = select(HospitalSetting).where(HospitalSetting.hospital_id == hosp_id)
    settings_rows = (await db.execute(settings_stmt)).scalars().all()
    
    settings_dict = {}
    for row in settings_rows:
        settings_dict[row.setting_key] = row.setting_value

    admin_stmt = (
        select(User)
        .join(UserRole, UserRole.user_id == User.id)
        .join(Role, UserRole.role_id == Role.id)
        .where(User.hospital_id == hosp_id, Role.name == "ADMIN")
    )
    admin_user = (await db.execute(admin_stmt)).scalars().first()
    admin_username = settings_dict.get("admin_username", admin_user.username if admin_user else "")
    admin_password = settings_dict.get("admin_password", "••••••••")

    dedicated_helpline = settings_dict.get("twilio_helpline", "")

    days_left = 0
    is_expired = False
    if hosp.plan_expires_at:
        now_dt = datetime.now()
        exp_dt = hosp.plan_expires_at
        if isinstance(exp_dt, str):
            try:
                exp_dt = datetime.fromisoformat(exp_dt)
            except Exception:
                exp_dt = now_dt
        if isinstance(exp_dt, datetime):
            diff = (exp_dt.replace(tzinfo=None) - now_dt.replace(tzinfo=None)).total_seconds()
            days_left = max(0, int(diff / 86400))
            is_expired = diff <= 0
            if is_expired and hosp.plan_status != "EXPIRED":
                hosp.plan_status = "EXPIRED"
                await db.commit()

    doc_count_stmt = select(func.count(Doctor.id)).where(Doctor.hospital_id == hosp_id, Doctor.is_active == True)
    active_docs_count = (await db.execute(doc_count_stmt)).scalar_one_or_none() or 0
    max_docs = hosp.max_doctors or 1
    quota_used_pct = min(100, round((active_docs_count / max_docs) * 100)) if max_docs > 0 else 100

    return {
        "id": hosp.id,
        "name": hosp.name,
        "phone": hosp.phone or "",
        "helpline": dedicated_helpline,
        "twilio_helpline": dedicated_helpline,
        "email": hosp.email,
        "address": hosp.address,
        "is_active": hosp.is_active if not is_expired else False,
        "is_expired": is_expired,
        "days_left": days_left,
        "active_doctors_count": active_docs_count,
        "doctor_quota_used_pct": quota_used_pct,
        "slug": hosp.slug,
        "subscription_plan": hosp.subscription_plan or "STARTER",
        "max_doctors": max_docs,
        "ai_voice_enabled": hosp.ai_voice_enabled if hosp.ai_voice_enabled is not None else False,
        "plan_status": "EXPIRED" if is_expired else (hosp.plan_status or "ACTIVE"),
        "plan_expires_at": str(hosp.plan_expires_at) if hosp.plan_expires_at else "",
        "created_at": str(hosp.created_at) if hosp.created_at else "",
        "admin_username": admin_username,
        "admin_password": admin_password,
        "settings": {
            "twilio_helpline": dedicated_helpline,
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
    phone: Optional[str] = Form(None),
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

    for key, val in settings_to_save.items():
        if val is not None:
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
