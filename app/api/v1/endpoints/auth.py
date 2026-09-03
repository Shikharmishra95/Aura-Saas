import uuid
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Form, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.core.dependencies import create_access_token, verify_password, get_current_user, hash_password
from app.database.models.call_log import User, Role, UserRole
from app.database.models.appointment import Hospital, Department, HospitalSetting, Doctor, DoctorSchedule

router = APIRouter(tags=["auth"])


@router.post("/auth/register-hospital", tags=["auth"])
async def register_hospital(
    name: str = Form(..., description="Hospital Name"),
    address: Optional[str] = Form(None, description="Hospital Address"),
    phone: str = Form(..., description="Hospital phone (for notifications/helpline)"),
    admin_username: str = Form(..., description="Admin Username"),
    admin_email: str = Form(..., description="Admin Email (Gmail)"),
    admin_password: str = Form(..., description="Admin Password"),
    plan_name: Optional[str] = Form("STARTER", description="Subscription Plan: STARTER, PRO, ENTERPRISE"),
    db: AsyncSession = Depends(get_db)
):
    """
    Onboards a new Hospital tenant, creates a unique Hospital ID,
    and registers the Hospital Admin user with selected Subscription Plan.
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

        # Check only if hospital slug (name) is already registered — phone is now allowed to be shared
        chk_slug_stmt = select(Hospital).where(Hospital.slug == slug)
        existing_hosp = (await db.execute(chk_slug_stmt)).scalars().first()
        if existing_hosp and existing_hosp.slug == slug:
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

        # Determine plan limits
        selected_plan = (plan_name or "STARTER").upper().strip()
        max_docs = 1
        ai_enabled = False
        if selected_plan == "PRO":
            max_docs = 5
            ai_enabled = True
        elif selected_plan == "ENTERPRISE":
            max_docs = 999
            ai_enabled = True

        plan_duration_days = 365
        if selected_plan == "STARTER":
            plan_duration_days = 15
        elif selected_plan == "PRO":
            plan_duration_days = 30

        # 3. Create Hospital
        hospital = Hospital(
            id=unique_hosp_id,
            name=name,
            slug=slug,
            address=address,
            phone=phone,
            email=admin_email,
            is_active=True,
            subscription_plan=selected_plan,
            max_doctors=max_docs,
            ai_voice_enabled=ai_enabled,
            plan_status="ACTIVE",
            plan_expires_at=datetime.now() + timedelta(days=plan_duration_days)
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
        db.add(HospitalSetting(id=str(uuid.uuid4()), hospital_id=unique_hosp_id, setting_key="admin_username", setting_value=admin_username))
        db.add(HospitalSetting(id=str(uuid.uuid4()), hospital_id=unique_hosp_id, setting_key="admin_password", setting_value=admin_password))

        await db.commit()

        # Send WhatsApp welcome message to hospital phone with all credentials
        try:
            from app.services.whatsapp import WhatsAppNotificationService
            import asyncio as _asyncio
            _wa = WhatsAppNotificationService()
            _msg = (
                f"🏥 *AURA SaaS — Hospital Registered Successfully!*\n\n"
                f"*Hospital Name:* {name}\n"
                f"*Hospital ID:* {unique_hosp_id}\n"
                f"*Address:* {address or 'N/A'}\n\n"
                f"🔑 *Admin Login Credentials:*\n"
                f"• Username: {admin_username}\n"
                f"• Password: {admin_password}\n"
                f"• Email: {admin_email}\n\n"
                f"📌 Share the Hospital ID with your staff so they can login to their portals.\n"
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
        if isinstance(e, HTTPException):
            raise e
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auth/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    """Authenticates admin console, receptionist, and doctor users, and yields secure JWT tokens with role scope."""
    
    # 1. Dynamic Database User Lookup
    stmt = select(User).where(User.username == form_data.username, User.is_active == True)
    user = (await db.execute(stmt)).scalar_one_or_none()

    if user and verify_password(form_data.password, user.password_hash):
        role_stmt = select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == user.id)
        roles = (await db.execute(role_stmt)).scalars().all()
        user_role = roles[0] if roles else "RECEPTIONIST"

        hosp_slug = ""
        if user.hospital_id and user.hospital_id != "super_admin":
            h_stmt = select(Hospital).where(Hospital.id == user.hospital_id)
            h = (await db.execute(h_stmt)).scalar_one_or_none()
            if h:
                hosp_slug = h.slug
                if not h.is_active:
                    raise HTTPException(
                        status_code=403,
                        detail="This hospital account is deactivated. Please contact platform support."
                    )

        access_token = create_access_token(data={
            "sub": user.username,
            "role": user_role,
            "hospital_id": user.hospital_id or "",
            "hospital_slug": hosp_slug
        })
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "role": user_role,
            "hospital_id": user.hospital_id or "",
            "hospital_slug": hosp_slug,
            "username": user.username,
            "user_id": user.id
        }

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Bearer"},
    )


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
    role_stmt = select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == current_user.id)
    roles = (await db.execute(role_stmt)).scalars().all()
    is_super_admin = "SUPER_ADMIN" in roles or current_user.hospital_id == "super_admin"

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


@router.get("/auth/me", tags=["auth"])
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns full profile details of currently authenticated user across all roles.
    """
    role_stmt = select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == current_user.id)
    roles = (await db.execute(role_stmt)).scalars().all()
    primary_role = roles[0] if roles else ("SUPER_ADMIN" if current_user.hospital_id == "super_admin" or not current_user.hospital_id else "RECEPTIONIST")

    hosp_name = "AURA SaaS Platform"
    hosp_code = current_user.hospital_id or "PLATFORM-ROOT"
    if current_user.hospital_id:
        h_stmt = select(Hospital).where(Hospital.id == current_user.hospital_id)
        hosp = (await db.execute(h_stmt)).scalar_one_or_none()
        if hosp:
            hosp_name = hosp.name
            hosp_code = hosp.id

    profile_data = {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email or "",
        "first_name": current_user.first_name or "",
        "last_name": current_user.last_name or "",
        "role": primary_role,
        "hospital_id": current_user.hospital_id,
        "hospital_name": hosp_name,
        "hospital_code": hosp_code
    }

    # If Doctor, enrich with clinical profile
    if primary_role == "DOCTOR":
        doc_stmt = select(Doctor, Department).join(Department, Doctor.department_id == Department.id).where(Doctor.id == current_user.id)
        doc_res = (await db.execute(doc_stmt)).first()
        if doc_res:
            doc, dept = doc_res
            profile_data["first_name"] = doc.first_name
            profile_data["last_name"] = doc.last_name
            profile_data["email"] = doc.email or profile_data["email"]
            profile_data["phone"] = doc.phone or ""
            profile_data["department_name"] = dept.name if dept else "General OPD"
            profile_data["opd_fees"] = doc.opd_fees or 400
            profile_data["license_number"] = doc.license_number or ""

    return profile_data


@router.post("/auth/change-password", tags=["auth"])
async def change_my_password(
    current_password: str = Form(..., description="Current active password"),
    new_password: str = Form(..., description="New password to set (min 6 chars)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Allows any logged-in user (Doctor, Receptionist, Admin, SuperAdmin) to update their password.
    Synchronizes both users.password_hash (bcrypt) and hospital_settings (staff directory display).
    """
    if len(new_password.strip()) < 6:
        raise HTTPException(status_code=400, detail="New password must be at least 6 characters long.")

    # 1. Verify current password against database hash
    if not verify_password(current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password entered is incorrect.")

    # 2. Update users table password_hash
    current_user.password_hash = hash_password(new_password.strip())
    db.add(current_user)

    # 3. If user belongs to a hospital, update hospital_settings staff_pwd reference
    if current_user.hospital_id:
        pwd_setting_stmt = select(HospitalSetting).where(
            HospitalSetting.hospital_id == current_user.hospital_id,
            HospitalSetting.setting_key == f"staff_pwd_{current_user.id}"
        )
        pwd_setting = (await db.execute(pwd_setting_stmt)).scalar_one_or_none()
        if pwd_setting:
            pwd_setting.setting_value = new_password.strip()
            db.add(pwd_setting)
        else:
            new_setting = HospitalSetting(
                id=str(uuid.uuid4()),
                hospital_id=current_user.hospital_id,
                setting_key=f"staff_pwd_{current_user.id}",
                setting_value=new_password.strip()
            )
            db.add(new_setting)

    # Also update doctor hashed_password if user is a doctor
    doc_stmt = select(Doctor).where(Doctor.id == current_user.id)
    doctor = (await db.execute(doc_stmt)).scalar_one_or_none()
    if doctor:
        doctor.hashed_password = hash_password(new_password.strip())
        db.add(doctor)

    await db.commit()

    return {
        "success": True,
        "message": "Password updated successfully in real-time."
    }

