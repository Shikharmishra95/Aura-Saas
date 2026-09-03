import asyncio
from datetime import date, time, datetime, timedelta, timezone
import uuid
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock, patch

from app.database.declarative import Base
import app.database.base
from app.database.session import get_db
from app.main import app
from app.core.dependencies import hash_password, create_access_token
from app.database.models.appointment import (
    Hospital, Department, Doctor, DoctorSchedule, DoctorLeave, HospitalHoliday,
    WorkingHour, Patient, Appointment, AppointmentStatusHistory
)
from app.database.models.call_log import User, Role, UserRole

@pytest_asyncio.fixture
async def db_engine():
    """Creates an isolated, in-memory SQLite database for testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest_asyncio.fixture
async def db_session(db_engine):
    """Yields an active AsyncSession bound to the in-memory SQLite database."""
    session_factory = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False
    )
    async with session_factory() as session:
        yield session

@pytest_asyncio.fixture
async def client(db_session):
    """Provides an AsyncClient targeting the FastAPI app with the test database overridden."""
    async def _get_test_db():
        yield db_session

    app.dependency_overrides[get_db] = _get_test_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()

@pytest.fixture(autouse=True)
def mock_external_services():
    """Globally mocks Twilio, Gemini, WhatsApp, and Razorpay to guarantee zero outbound network calls."""
    with patch("app.services.twilio_service.TwilioService") as mock_twilio,          patch("app.services.gemini_live.GeminiLiveClient") as mock_gemini,          patch("app.services.whatsapp.WhatsAppNotificationService._send_sync", return_value="MOCK-MSG-SID") as mock_wa_sync,          patch("twilio.rest.Client") as mock_twilio_client,          patch("razorpay.Client") as mock_rzp:
        
        yield {
            "twilio": mock_twilio,
            "gemini": mock_gemini,
            "whatsapp_sync": mock_wa_sync,
            "razorpay": mock_rzp
        }

@pytest_asyncio.fixture
async def seed_roles(db_session):
    """Seeds standard RBAC roles in the test database."""
    roles = [
        Role(id="ROLE-SUPER", name="SUPER_ADMIN", description="Super Administrator"),
        Role(id="ROLE-ADMIN", name="ADMIN", description="Hospital Administrator"),
        Role(id="ROLE-DOCTOR", name="DOCTOR", description="Medical Doctor"),
        Role(id="ROLE-RECEP", name="RECEPTIONIST", description="Front Desk Receptionist"),
        Role(id="ROLE-PATIENT", name="PATIENT", description="Registered Patient")
    ]
    for r in roles:
        db_session.add(r)
    await db_session.commit()
    return {r.name: r for r in roles}

@pytest_asyncio.fixture
async def hospital_a(db_session):
    """Test Hospital A fixture."""
    hosp = Hospital(
        id="HOSP-TEST-A",
        name="Alpha Medical Center",
        slug="alpha-medical",
        phone="+911111111111",
        email="contact@alpha.com",
        timezone="UTC",
        is_active=True,
        subscription_plan="PRO"
    )
    db_session.add(hosp)
    await db_session.commit()
    await db_session.refresh(hosp)
    return hosp

@pytest_asyncio.fixture
async def hospital_b(db_session):
    """Test Hospital B fixture for multi-tenancy testing."""
    hosp = Hospital(
        id="HOSP-TEST-B",
        name="Beta General Hospital",
        slug="beta-hospital",
        phone="+912222222222",
        email="contact@beta.com",
        timezone="UTC",
        is_active=True,
        subscription_plan="BASIC"
    )
    db_session.add(hosp)
    await db_session.commit()
    await db_session.refresh(hosp)
    return hosp

@pytest_asyncio.fixture
async def department_a(db_session, hospital_a):
    """Test Department for Hospital A."""
    dept = Department(
        id="DEP-A-1",
        hospital_id=hospital_a.id,
        name="General Medicine",
        is_active=True
    )
    db_session.add(dept)
    await db_session.commit()
    await db_session.refresh(dept)
    return dept

@pytest_asyncio.fixture
async def department_b(db_session, hospital_b):
    """Test Department for Hospital B."""
    dept = Department(
        id="DEP-B-1",
        hospital_id=hospital_b.id,
        name="Pediatrics",
        is_active=True
    )
    db_session.add(dept)
    await db_session.commit()
    await db_session.refresh(dept)
    return dept

@pytest_asyncio.fixture
async def doctor_a(db_session, hospital_a, department_a):
    """Test Doctor for Hospital A."""
    doc = Doctor(
        id="DOC-A-1",
        hospital_id=hospital_a.id,
        department_id=department_a.id,
        first_name="Aarav",
        last_name="Sharma",
        email="aarav.sharma@alpha.com",
        phone="+919876543210",
        license_number="MED-12345",
        opd_fees=500,
        is_active=True
    )
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)
    return doc

@pytest_asyncio.fixture
async def doctor_b(db_session, hospital_b, department_b):
    """Test Doctor for Hospital B."""
    doc = Doctor(
        id="DOC-B-1",
        hospital_id=hospital_b.id,
        department_id=department_b.id,
        first_name="Bob",
        last_name="Smith",
        email="bob.smith@beta.com",
        phone="+919876543211",
        license_number="MED-67890",
        opd_fees=600,
        is_active=True
    )
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)
    return doc

@pytest_asyncio.fixture
async def doctor_schedule_a(db_session, doctor_a):
    """Creates a standard Mon-Sat 10:00 - 13:00 schedule for Doctor A."""
    schedules = []
    for day in range(1, 7):
        s = DoctorSchedule(
            id=f"SCHED-DOC-A-{day}",
            doctor_id=doctor_a.id,
            day_of_week=day,
            start_time=time(10, 0),
            end_time=time(13, 0),
            slot_duration_minutes=30
        )
        db_session.add(s)
        schedules.append(s)
    await db_session.commit()
    return schedules

@pytest_asyncio.fixture
async def patient_a(db_session, hospital_a):
    """Test Patient for Hospital A."""
    pat = Patient(
        id="PAT-A-1",
        hospital_id=hospital_a.id,
        first_name="Rohan",
        last_name="Verma",
        date_of_birth=date(1995, 4, 10),
        gender="Male",
        phone="+919999900001",
        email="rohan@example.com",
        is_active=True
    )
    db_session.add(pat)
    await db_session.commit()
    await db_session.refresh(pat)
    return pat

@pytest_asyncio.fixture
async def patient_b(db_session, hospital_b):
    """Test Patient for Hospital B."""
    pat = Patient(
        id="PAT-B-1",
        hospital_id=hospital_b.id,
        first_name="David",
        last_name="Miller",
        date_of_birth=date(1988, 7, 22),
        gender="Male",
        phone="+919999900002",
        email="david@example.com",
        is_active=True
    )
    db_session.add(pat)
    await db_session.commit()
    await db_session.refresh(pat)
    return pat

@pytest_asyncio.fixture
async def admin_user_a(db_session, hospital_a, seed_roles):
    """Admin user for Hospital A."""
    user = User(
        id="USER-ADM-A",
        hospital_id=hospital_a.id,
        username="admin_alpha",
        email="admin@alpha.com",
        password_hash=hash_password("adminpass123"),
        first_name="Alpha",
        last_name="Admin",
        is_active=True
    )
    db_session.add(user)
    await db_session.flush()
    ur = UserRole(
        id=str(uuid.uuid4()),
        user_id=user.id,
        role_id=seed_roles["ADMIN"].id
    )
    db_session.add(ur)
    await db_session.commit()
    await db_session.refresh(user)
    return user

@pytest_asyncio.fixture
async def admin_token_a(admin_user_a):
    """JWT for Admin A."""
    return create_access_token({
        "sub": admin_user_a.username,
        "role": "ADMIN",
        "hospital_id": admin_user_a.hospital_id,
        "user_id": admin_user_a.id
    })

@pytest_asyncio.fixture
async def receptionist_user_a(db_session, hospital_a, seed_roles):
    """Receptionist user for Hospital A."""
    user = User(
        id="USER-REC-A",
        hospital_id=hospital_a.id,
        username="recep_alpha",
        email="recep@alpha.com",
        password_hash=hash_password("receppass123"),
        first_name="Alpha",
        last_name="Receptionist",
        is_active=True
    )
    db_session.add(user)
    await db_session.flush()
    ur = UserRole(
        id=str(uuid.uuid4()),
        user_id=user.id,
        role_id=seed_roles["RECEPTIONIST"].id
    )
    db_session.add(ur)
    await db_session.commit()
    await db_session.refresh(user)
    return user

@pytest_asyncio.fixture
async def receptionist_token_a(receptionist_user_a):
    """JWT for Receptionist A."""
    return create_access_token({
        "sub": receptionist_user_a.username,
        "role": "RECEPTIONIST",
        "hospital_id": receptionist_user_a.hospital_id,
        "user_id": receptionist_user_a.id
    })

@pytest_asyncio.fixture
async def doctor_user_a(db_session, hospital_a, doctor_a, seed_roles):
    """Doctor user for Doctor A."""
    user = User(
        id=doctor_a.id,
        hospital_id=hospital_a.id,
        username="doctor_aarav",
        email="aarav.sharma@alpha.com",
        password_hash=hash_password("docpass123"),
        first_name="Aarav",
        last_name="Sharma",
        is_active=True
    )
    db_session.add(user)
    await db_session.flush()
    ur = UserRole(
        id=str(uuid.uuid4()),
        user_id=user.id,
        role_id=seed_roles["DOCTOR"].id
    )
    db_session.add(ur)
    await db_session.commit()
    await db_session.refresh(user)
    return user

@pytest_asyncio.fixture
async def doctor_token_a(doctor_user_a):
    """JWT for Doctor A."""
    return create_access_token({
        "sub": doctor_user_a.username,
        "role": "DOCTOR",
        "hospital_id": doctor_user_a.hospital_id,
        "user_id": doctor_user_a.id
    })

@pytest_asyncio.fixture
async def patient_token_a(patient_a):
    """JWT for Patient A."""
    return create_access_token({
        "sub": patient_a.phone,
        "role": "PATIENT",
        "hospital_id": patient_a.hospital_id,
        "patient_id": patient_a.id,
        "name": f"{patient_a.first_name} {patient_a.last_name}"
    })

@pytest_asyncio.fixture
async def super_admin_user(db_session, seed_roles):
    """Seeds a Super Admin user into test database."""
    user = User(
        id="USER-SUPER-1",
        hospital_id=None,
        username="shiva9532",
        email="shiva9532@gmail.com",
        password_hash=hash_password("adminpass123"),
        first_name="Shiva",
        last_name="SuperAdmin",
        is_active=True
    )
    db_session.add(user)
    await db_session.flush()
    ur = UserRole(
        id=str(uuid.uuid4()),
        user_id=user.id,
        role_id=seed_roles["SUPER_ADMIN"].id
    )
    db_session.add(ur)
    await db_session.commit()
    await db_session.refresh(user)
    return user

@pytest.fixture
def superadmin_token_headers(super_admin_user):
    token = create_access_token({
        "sub": super_admin_user.username,
        "role": "SUPER_ADMIN",
        "hospital_id": "super_admin",
        "user_id": super_admin_user.id
    })
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def auth_token_headers(admin_token_a):
    return {"Authorization": f"Bearer {admin_token_a}"}


