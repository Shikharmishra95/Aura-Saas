import uuid
import asyncio
from datetime import datetime, time
from typing import List, Optional
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.core.dependencies import get_current_user, hash_password
from app.core.config import settings
from app.core.logging import logger
from app.database.models.call_log import User, Role, UserRole
from app.database.models.appointment import Hospital, Department, Doctor, DoctorSchedule, DoctorSpecialization, HospitalSetting
from app.schemas.appointment import DoctorCreate, DoctorRead
from app.services.whatsapp import WhatsAppNotificationService

router = APIRouter(tags=["staff"])


@router.post("/hospital/register-staff", tags=["hospital"])
async def register_staff(
    role: str = Form(..., description="DOCTOR or RECEPTIONIST"),
    username: str = Form(..., description="Staff Username"),
    email: str = Form(..., description="Staff Email"),
    password: str = Form(..., description="Staff Password"),
    first_name: str = Form(..., description="Staff First Name"),
    last_name: str = Form(..., description="Staff Last Name"),
    phone: str = Form(..., description="Staff Phone Number"),
    department_id: Optional[str] = Form(None, description="Department ID (required for DOCTOR)"),
    license_number: Optional[str] = Form(None, description="License Number (optional for DOCTOR)"),
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
    role_stmt = select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == current_admin.id)
    roles = (await db.execute(role_stmt)).scalars().all()
    if "ADMIN" not in roles:
        raise HTTPException(status_code=403, detail="Only Hospital Admins can register staff.")

    try:
        stmt = select(User).where((User.username == username) | (User.email == email))
        existing = (await db.execute(stmt)).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=400, detail="Username or email already registered.")

        role_name = role.upper()
        if role_name not in ["DOCTOR", "RECEPTIONIST"]:
            raise HTTPException(status_code=400, detail="Invalid role. Select DOCTOR or RECEPTIONIST.")

        target_role_stmt = select(Role).where(Role.name == role_name)
        target_role = (await db.execute(target_role_stmt)).scalar_one_or_none()
        if not target_role:
            target_role = Role(id=str(uuid.uuid4()), name=role_name, description=f"Hospital {role_name.capitalize()}")
            db.add(target_role)
            await db.flush()

        if role_name == "DOCTOR":
            hosp_stmt = select(Hospital).where(Hospital.id == current_admin.hospital_id)
            hosp = (await db.execute(hosp_stmt)).scalar_one_or_none()
            if hosp:
                doc_count_stmt = select(func.count(Doctor.id)).where(Doctor.hospital_id == current_admin.hospital_id)
                current_docs_count = (await db.execute(doc_count_stmt)).scalar() or 0
                if current_docs_count >= hosp.max_doctors:
                    raise HTTPException(
                        status_code=403,
                        detail=f"🔒 Doctor limit reached! Your {hosp.subscription_plan} plan includes Max {hosp.max_doctors} Doctor(s). Please Upgrade your plan to register more doctors!"
                    )

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

        user_role = UserRole(
            id=str(uuid.uuid4()),
            user_id=staff_user.id,
            role_id=target_role.id
        )
        db.add(user_role)
        await db.flush()

        db.add(HospitalSetting(
            id=str(uuid.uuid4()),
            hospital_id=current_admin.hospital_id,
            setting_key=f"staff_pwd_{staff_user.id}",
            setting_value=password
        ))

        if role_name == "DOCTOR":
            if not department_id:
                raise HTTPException(status_code=400, detail="department_id is required when role is DOCTOR.")
            
            # 1. Check if department_id directly matches by ID or Name in current hospital
            dept_stmt = select(Department).where(
                or_(Department.id == department_id, Department.name == department_id),
                Department.hospital_id == current_admin.hospital_id
            )
            dept = (await db.execute(dept_stmt)).scalars().first()

            # 2. If not found in current hospital, resolve clean name from global department or string
            if not dept:
                global_dept_stmt = select(Department).where(Department.id == department_id)
                global_dept = (await db.execute(global_dept_stmt)).scalar_one_or_none()
                clean_dept_name = global_dept.name if global_dept else department_id
                
                # Check if this clean name exists in current hospital
                hosp_dept_stmt = select(Department).where(
                    Department.hospital_id == current_admin.hospital_id,
                    Department.name == clean_dept_name
                )
                dept = (await db.execute(hosp_dept_stmt)).scalar_one_or_none()
                
                if not dept:
                    dept = Department(
                        id=f"dept_{clean_dept_name.lower()[:5]}_{current_admin.hospital_id}",
                        hospital_id=current_admin.hospital_id,
                        name=clean_dept_name,
                        description=f"{clean_dept_name} department",
                        is_active=True
                    )
                    db.add(dept)
                    await db.flush()
                
            real_department_id = dept.id

            doctor = Doctor(
                id=staff_user.id,
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

            _sst = (schedule_start_time or "").strip()
            _set = (schedule_end_time or "").strip()
            if schedule_days and _sst and _set:
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
                    except Exception:
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


@router.post("/doctors", response_model=DoctorRead)
async def create_doctor(
    payload: DoctorCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Registers a new doctor profile under the clinical network."""
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
    role_stmt = select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == current_user.id)
    roles = (await db.execute(role_stmt)).scalars().all()

    h_id = current_user.hospital_id if current_user.hospital_id else "hosp_default"
    if "SUPER_ADMIN" in roles and hospital_id:
        h_id = hospital_id

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
        sched_stmt = select(DoctorSchedule).where(DoctorSchedule.doctor_id == doc.id)
        schedules = (await db.execute(sched_stmt)).scalars().all()
        work_days = [s.day_of_week for s in schedules]
        
        timing_str = ""
        if schedules:
            session_times = defaultdict(list)
            for s in schedules:
                time_range = f"{s.start_time.strftime('%I:%M %p').lstrip('0')} - {s.end_time.strftime('%I:%M %p').lstrip('0')}"
                session_times[time_range].append(s.day_of_week)
            
            parts = []
            for tr, days_list in session_times.items():
                days_list.sort()
                day_names_map = {1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu", 5: "Fri", 6: "Sat", 7: "Sun"}
                if len(days_list) >= 5 and days_list == list(range(days_list[0], days_list[0] + len(days_list))):
                    days_str = f"{day_names_map.get(days_list[0])}–{day_names_map.get(days_list[-1])}"
                else:
                    days_str = ", ".join([day_names_map.get(d, str(d)) for d in days_list])
                parts.append(f"{days_str}, {tr}")
            timing_str = " | ".join(parts)
        else:
            timing_str = "Mon–Sat, 10:00 AM - 01:00 PM"
            work_days = [1, 2, 3, 4, 5, 6]

        distinct_sessions = sorted(list(set([(s.start_time, s.end_time) for s in schedules])), key=lambda x: x[0]) if schedules else []
        s1_start = distinct_sessions[0][0].strftime("%H:%M") if len(distinct_sessions) > 0 else "10:00"
        s1_end = distinct_sessions[0][1].strftime("%H:%M") if len(distinct_sessions) > 0 else "13:00"
        s2_start = distinct_sessions[1][0].strftime("%H:%M") if len(distinct_sessions) > 1 else ""
        s2_end = distinct_sessions[1][1].strftime("%H:%M") if len(distinct_sessions) > 1 else ""
        has_shift_2 = len(distinct_sessions) > 1

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
            "session_1_start": s1_start,
            "session_1_end": s1_end,
            "session_2_start": s2_start,
            "session_2_end": s2_end,
            "has_shift_2": has_shift_2,
            "username": u.username if u else (doc.email.split('@')[0] if doc.email else doc.id),
            "password": pwd_dict.get(doc.id, "••••••••")
        })
    return doctors_info


@router.get("/hospital/staff", tags=["hospital"])
async def list_hospital_staff(
    hospital_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Returns all staff (doctors + receptionists) for a hospital."""
    role_stmt = select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == current_user.id)
    roles = (await db.execute(role_stmt)).scalars().all()

    if "SUPER_ADMIN" in roles or current_user.hospital_id == "super_admin":
        target_hospital_id = hospital_id
    else:
        target_hospital_id = current_user.hospital_id

    if not target_hospital_id:
        return {"doctors": [], "receptionists": []}

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
        user_stmt = select(User).where(User.id == doc.id)
        user = (await db.execute(user_stmt)).scalar_one_or_none()
        
        sched_stmt = select(DoctorSchedule).where(DoctorSchedule.doctor_id == doc.id)
        schedules = (await db.execute(sched_stmt)).scalars().all()
        
        work_days = [s.day_of_week for s in schedules]
        slot_duration = schedules[0].slot_duration_minutes if schedules else 30
        
        timing_str = ""
        if schedules:
            session_times = defaultdict(list)
            for s in schedules:
                time_range = f"{s.start_time.strftime('%I:%M %p').lstrip('0')} - {s.end_time.strftime('%I:%M %p').lstrip('0')}"
                session_times[time_range].append(s.day_of_week)
            
            parts = []
            for tr, days_list in session_times.items():
                days_list.sort()
                day_names_map = {1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu", 5: "Fri", 6: "Sat", 7: "Sun"}
                if len(days_list) >= 5 and days_list == list(range(days_list[0], days_list[0] + len(days_list))):
                    days_str = f"{day_names_map.get(days_list[0])}–{day_names_map.get(days_list[-1])}"
                else:
                    days_str = ", ".join([day_names_map.get(d, str(d)) for d in days_list])
                parts.append(f"{days_str}, {tr}")
            timing_str = " | ".join(parts)

        distinct_sessions = sorted(list(set([(s.start_time, s.end_time) for s in schedules])), key=lambda x: x[0]) if schedules else []
        s1_start = distinct_sessions[0][0].strftime("%H:%M") if len(distinct_sessions) > 0 else "10:00"
        s1_end = distinct_sessions[0][1].strftime("%H:%M") if len(distinct_sessions) > 0 else "13:00"
        s2_start = distinct_sessions[1][0].strftime("%H:%M") if len(distinct_sessions) > 1 else ""
        s2_end = distinct_sessions[1][1].strftime("%H:%M") if len(distinct_sessions) > 1 else ""
        has_shift_2 = len(distinct_sessions) > 1

        doctors.append({
            "id": doc.id,
            "username": user.username if user else "",
            "password": pwd_dict.get(doc.id, "••••••••"),
            "email": doc.email,
            "first_name": doc.first_name,
            "last_name": doc.last_name,
            "phone": doc.phone or "",
            "department": dept.name,
            "department_name": dept.name,
            "license_number": doc.license_number or "",
            "opd_fees": doc.opd_fees or 0,
            "is_active": doc.is_active,
            "work_days": work_days,
            "slot_duration_minutes": slot_duration,
            "timings": timing_str,
            "session_1_start": s1_start,
            "session_1_end": s1_end,
            "session_2_start": s2_start,
            "session_2_end": s2_end,
            "has_shift_2": has_shift_2
        })

    # 2. Get Receptionists
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
    
    doc_stmt = select(Doctor).where((Doctor.id == user_id) & (Doctor.hospital_id == hosp_id))
    doctor = (await db.execute(doc_stmt)).scalar_one_or_none()
    
    if doctor:
        user_stmt = select(User).where((User.email == doctor.email) & (User.hospital_id == hosp_id))
        staff_user = (await db.execute(user_stmt)).scalar_one_or_none()
        await db.delete(doctor)
        if staff_user:
            await db.delete(staff_user)
    else:
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

        user_stmt = select(User).where(User.id == doctor_id)
        doc_user = (await db.execute(user_stmt)).scalar_one_or_none()

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

        def normalize_time_str(val: Optional[str]) -> Optional[str]:
            if not val:
                return None
            c = val.strip().lower()
            if c in ["", "null", "undefined", "--:--", "00:00", "0:0", "00:00:00"]:
                return None
            return val.strip()

        norm_s1_start = normalize_time_str(schedule_start_time)
        norm_s1_end = normalize_time_str(schedule_end_time)
        norm_s2_start = normalize_time_str(schedule_start_time_2)
        norm_s2_end = normalize_time_str(schedule_end_time_2)

        if schedule_days and norm_s1_start and norm_s1_end:
            def parse_time(value: Optional[str]) -> Optional[time]:
                if not value:
                    return None
                try:
                    parts = value.split(':')
                    return time(int(parts[0]), int(parts[1]))
                except Exception:
                    raise ValueError(f"Invalid time format: '{value}'. Expected HH:MM or HH:MM:SS.")

            try:
                t_start = parse_time(norm_s1_start)
                t_end = parse_time(norm_s1_end)
                t_start_2 = parse_time(norm_s2_start)
                t_end_2 = parse_time(norm_s2_end)
            except Exception as pe:
                logger.error(f"Time parsing failed during doctor profile update: {str(pe)}")
                raise HTTPException(status_code=400, detail="Invalid time format.")

            del_stmt = select(DoctorSchedule).where(DoctorSchedule.doctor_id == doctor.id)
            old_scheds = (await db.execute(del_stmt)).scalars().all()
            for osc in old_scheds:
                await db.delete(osc)
            
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
                    if t_start_2 and t_end_2 and t_start_2 != t_end_2 and t_start_2 != t_start:
                        s2 = DoctorSchedule(
                            id=str(uuid.uuid4()),
                            doctor_id=doctor.id,
                            day_of_week=day,
                            start_time=t_start_2,
                            end_time=t_end_2,
                            slot_duration_minutes=slot_duration_minutes or 30
                        )
                        db.add(s2)
                        
                await db.flush()
                
            except Exception as se:
                logger.error(f"Error rebuilding doctor schedule list: {str(se)}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Error inserting doctor schedules: {str(se)}"
                )

        await db.commit()
        
        if phone:
            try:
                wa_service = WhatsAppNotificationService()
                msg = f"🏥 *Hospital Update*\nDr. {first_name} {last_name},\nYour profile and working schedule has been successfully updated by the hospital administration. Please log in to your portal to verify the changes."
                asyncio.create_task(wa_service.send_custom_notification(phone, msg))
            except Exception:
                pass
            
        return {"status": "success", "message": "Doctor profile updated successfully"}
    except Exception as e:
        await db.rollback()
        logger.error(f"Transaction failed during doctor profile update: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Failed to update doctor profile: {str(e)}")
