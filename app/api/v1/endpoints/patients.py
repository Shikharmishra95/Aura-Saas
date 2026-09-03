import uuid
from datetime import datetime
from typing import Optional
from collections import defaultdict
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.core.dependencies import get_current_user
from app.database.models.call_log import User, Role, UserRole
from app.database.models.appointment import Patient, Appointment, Doctor, ConsultationNote
from app.schemas.appointment import PatientCreate, PatientRead

router = APIRouter(tags=["patients"])


@router.post("/patients", response_model=PatientRead)
async def register_patient(
    payload: PatientCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Registers a new patient file in the central medical records database."""
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
    phone_digits = ''.join(c for c in query if c.isdigit())
    clean_q = query.strip()
    
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

    matched_phones = list({p.phone for p in matched_patients if p.phone})

    all_family_stmt = select(Patient).where(Patient.phone.in_(matched_phones), Patient.is_active == True).order_by(Patient.created_at.asc())
    all_family_patients = (await db.execute(all_family_stmt)).scalars().all()

    phone_to_patients = defaultdict(list)
    for p in all_family_patients:
        phone_to_patients[p.phone].append(p)

    # Determine target hospital for multi-tenant isolation
    target_hospital_id = None
    if current_user:
        role_stmt = select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == current_user.id)
        user_roles = (await db.execute(role_stmt)).scalars().all()
        if "SUPER_ADMIN" not in user_roles and current_user.hospital_id != "super_admin":
            target_hospital_id = current_user.hospital_id
    if not target_hospital_id and hospital_id:
        target_hospital_id = hospital_id

    all_patient_ids = [p.id for p in all_family_patients]

    if target_hospital_id:
        appt_stmt = (
            select(Appointment)
            .join(Doctor, Appointment.doctor_id == Doctor.id)
            .options(selectinload(Appointment.doctor))
            .where(
                Appointment.patient_id.in_(all_patient_ids),
                Doctor.hospital_id == target_hospital_id
            )
            .order_by(Appointment.appointment_datetime.desc())
        )
    else:
        appt_stmt = (
            select(Appointment)
            .options(selectinload(Appointment.doctor))
            .where(Appointment.patient_id.in_(all_patient_ids))
            .order_by(Appointment.appointment_datetime.desc())
        )
    all_appts = (await db.execute(appt_stmt)).scalars().all()

    if target_hospital_id:
        hosp_patient_ids = {a.patient_id for a in all_appts}
        if not hosp_patient_ids:
            return {"query": clean_q, "total_found": 0, "groups": []}
    else:
        hosp_patient_ids = set(all_patient_ids)

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
            if target_hospital_id and m.id not in hosp_patient_ids:
                continue
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

        if member_list:
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
