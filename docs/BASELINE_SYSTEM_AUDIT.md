# BASELINE SYSTEM AUDIT & PRE-PRODUCTION VERIFICATION
**Project**: AURA SaaS (Hospital AI Voice Receptionist & Hospital Management Platform)  
**Date**: August 27, 2026  
**Auditors**: Principal FastAPI + React + SQLAlchemy Engineer & Lead QA Engineer  
**Status**: READ-ONLY PRE-HARDENING BASELINE (No Business Logic or Schema Modified)

---

## A. COMPLETE PROJECT STRUCTURE

```
c:\Users\shiva\Desktop\AAA\
├── .env                              # Active environment variable definitions (MySQL, JWT, Twilio, Gemini, Razorpay)
├── .env.example                      # Reference template for required deployment environment variables
├── .gitignore                        # Git exclusion configuration
├── .dockerignore                     # Docker build artifact exclusion rules
├── Dockerfile                        # Multi-stage/Python 3.11-slim containerization spec for backend service
├── docker-compose.yml                # Multi-container orchestration (FastAPI app + MySQL 8.0)
├── requirements.txt                  # Python runtime dependencies (FastAPI, SQLAlchemy, PyMySQL, Twilio, Google GenAI, etc.)
├── alembic.ini                       # Database migration tool configuration
├── README.md                         # Project documentation and high-level setup guide
├── roles.txt                         # User role definitions reference
├── cleanup_ghost_hospital.py         # Utility script for removing orphaned hospital records
├── smoke_test.py                     # Standalone HTTP client script testing core API flows
├── test_login_api.py                 # Standalone script testing auth login endpoint
├── test_slot_full.py                 # Standalone script verifying doctor slot limit algorithms
├── verify_db.py                      # Standalone database connectivity & table count verification script
├── docs/                             # Architecture and system documentation
│   ├── ai_brain_design.md            # LLM prompt design and conversation state machine documentation
│   ├── technical_audit.md            # Early technical review notes
│   └── BASELINE_SYSTEM_AUDIT.md      # THIS DOCUMENT: Official baseline pre-production audit
├── migrations/                       # Alembic schema versioning scripts
│   ├── env.py                        # Migration environment setup connecting SQLAlchemy metadata
│   ├── script.py.mako                # Migration file template
│   └── versions/                     # Migration step revisions (5 revisions tracked)
├── app/                              # Backend FastAPI Application Package
│   ├── __init__.py                   # Package initializer
│   ├── main.py                       # Application factory, global CORS, middleware, and router assembly
│   ├── api/                          # HTTP and WebSocket Routers
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py             # Top-level v1 aggregator router
│   │       └── endpoints/
│   │           ├── appointments.py   # Primary monolithic route file (4,799 lines: auth, hospitals, appointments, payments)
│   │           ├── patient_portal.py # Patient-facing booking and prescription retrieval APIs
│   │           ├── patient_auth.py   # Patient phone OTP authentication endpoints
│   │           ├── voice.py          # Twilio voice webhooks & Gemini Live WebSocket media stream handler
│   │           └── whatsapp_webhook.py # Twilio WhatsApp incoming webhook handler
│   ├── core/                         # Core infrastructure & configuration
│   │   ├── config.py                 # Pydantic BaseSettings class loading .env with property URL generators
│   │   ├── dependencies.py           # JWT token generation, OAuth2 bearer retrieval, and get_current_user
│   │   ├── exceptions.py             # Custom application domain exceptions & global exception handlers
│   │   ├── logging.py                # Contextual logging infrastructure with request_id and hospital_id contextvars
│   │   └── middleware.py             # HTTP request correlation middleware extracting X-Request-ID and X-Hospital-ID
│   ├── database/                     # Database layer
│   │   ├── base.py                   # Model registry importing all declarative models for Alembic
│   │   ├── declarative.py            # SQLAlchemy DeclarativeBase instantiation
│   │   ├── session.py                # AsyncSessionMaker and get_db FastAPI dependency generator
│   │   ├── schema.sql                # Full reference MySQL 8.0 schema DDL
│   │   └── models/                   # SQLAlchemy ORM Model Classes
│   │       ├── appointment.py        # Hospital, Department, Doctor, Patient, Appointment, DoctorSchedule, Leave models
│   │       ├── conversation.py       # VoiceSession, ConversationLog, ConversationMemory, ToolExecutionLog models
│   │       └── call_log.py           # CallLog, PaymentLink, Payment, Notification, User, Role, UserRole models
│   ├── domain/                       # Domain logic interfaces
│   ├── engines/                      # Core business calculation engines
│   │   ├── appointment.py            # AppointmentEngine: validation, duplicate protection, and booking execution
│   │   ├── scheduling.py             # SchedulingEngine: calendar slot generation, leaves, and availability calculation
│   │   └── voice_state_machine.py    # Multi-turn conversation state machine managing voice caller intents
│   ├── managers/                     # Prompt & conversation management
│   │   └── prompt.py                 # System prompt templates and hospital context injection
│   ├── schemas/                      # Pydantic validation schemas
│   │   └── appointment.py            # Pydantic DTO models for Appointments, Doctors, and Patients
│   ├── services/                     # Third-party integrations
│   │   ├── automation.py             # Outbound n8n webhook notifications
│   │   ├── gemini_live.py            # Google Gemini 2.0 / 1.5 Live bidirectional audio streaming client
│   │   ├── twilio_service.py         # Twilio REST API client for call control, TwiML generation, and SMS
│   │   ├── whatsapp.py               # WhatsApp notification service via Twilio messaging API
│   │   └── whatsapp_intake.py        # Post-consultation patient medical intake dialogue manager
│   └── utils/                        # Audio and data transformation utilities
│       └── audio.py                  # μ-law to linear PCM converter, resampler (8kHz to 16kHz), amplitude calculator
├── frontend/                         # Vite + React 19 Frontend Application
│   ├── index.html                    # Single-page application root HTML entry
│   ├── package.json                  # Frontend dependencies (React 19, Lucide icons, Vite 8)
│   ├── vite.config.js                # Vite development server and /api proxy configuration
│   └── src/
│       ├── main.jsx                  # React DOM entry point wrapping App in StrictMode
│       ├── App.jsx                   # Primary monolithic frontend application (4,822 lines: all staff portals & state)
│       ├── App.css                   # Global dashboard styling rules
│       ├── PatientPortal.jsx         # Standalone patient booking and digital prescription portal (1,040 lines)
│       ├── PatientPortal.css         # Patient portal specific UI themes
│       ├── index.css                 # Base CSS reset and typography
│       ├── pages/
│       │   └── LoginPage.jsx         # Landing page, hospital onboarding checkout, and staff login component
│       └── components/
│           ├── common/
│           │   ├── Header.jsx        # Top header navigation bar component
│           │   └── Sidebar.jsx       # Standalone sidebar navigation component
│           └── doctor/
│               └── DoctorQueue.jsx   # Doctor workstation patient queue and consultation card component
└── tests/                            # Automated test suite directory
    ├── __init__.py
    ├── conftest.py                   # Pytest fixtures configuration (currently stub)
    ├── unit/                         # Unit tests directory
    └── integration/                  # Integration tests directory
```

---

## B. BACKEND ARCHITECTURE

1. **`app/main.py`**:
   - Implements application factory `create_app()` returning a `FastAPI` instance.
   - Configures `CORSMiddleware` with origins from `settings.BACKEND_CORS_ORIGINS`.
   - Attaches `LogContextMiddleware` to inject correlation IDs into log streams.
   - Registers exception handlers via `register_exception_handlers(app)`.
   - Includes API routers with `/api/v1` prefixes.
   - Defines `/health` endpoint performing a live `SELECT 1` ping against the database.
   - Mounts static files from `frontend/dist` and serves `index.html` on catch-all routes.
2. **`app/api/`**:
   - `v1/router.py`: Central routing aggregator.
   - `endpoints/appointments.py` (4,799 lines): Contains authentication (`/auth/login`, `/auth/register-hospital`), hospital management, staff management, appointment lifecycle, leaves, and payment endpoints.
   - `endpoints/patient_portal.py`: Provides unauthenticated public doctor slot queries and patient JWT-protected booking.
   - `endpoints/patient_auth.py`: Provides OTP delivery (`/send-otp`) and verification (`/verify-otp`) for patient portal access.
   - `endpoints/voice.py`: Manages Twilio webhook endpoints (`/voice/inbound`, `/voice/gather`, `/voice/fallback`) and WebSocket streaming (`/voice/stream/{session_id}`).
   - `endpoints/whatsapp_webhook.py`: Receives incoming WhatsApp messages from Twilio for patient intake conversations.
3. **`app/core/`**:
   - `config.py`: Uses `pydantic-settings` to parse `.env`. Generates dynamic `ASYNC_DATABASE_URL` (`mysql+aiomysql://...`) and `SYNC_DATABASE_URL` (`mysql+pymysql://...`).
   - `dependencies.py`: Defines OAuth2 scheme (`/api/v1/auth/login`), password hashing functions (`bcrypt`), JWT token generator `create_access_token`, and auth dependency `get_current_user`.
   - `exceptions.py`: Domain exceptions mapped to standard HTTP status codes.
   - `logging.py` & `middleware.py`: ContextVar-driven structured logging tracking `request_id` and `hospital_id`.
4. **`app/database/`**:
   - `session.py`: Manages `create_async_engine` connection pools and async session context managers (`get_db`).
   - `models/`: Normalized SQLAlchemy declarative models with explicit foreign key constraints.
5. **`app/engines/`**:
   - `SchedulingEngine`: Computes doctor working hours, break periods, holiday blockouts, approved leaves, and available 30-minute booking slots.
   - `AppointmentEngine`: Enforces booking rules (no past dates, no same-day calls, no duplicate bookings) and executes atomic slot reservations.
   - `VoiceStateMachine`: Manages multi-turn conversation flow for inbound callers, using Gemini to extract intent entities and call scheduling functions.
6. **`app/services/`**:
   - `TwilioService`: Constructs TwiML XML responses and handles outbound REST calls.
   - `GeminiLiveClient`: Manages bidirectional streaming with Google GenAI.
   - `WhatsAppNotificationService`: Sends SMS and WhatsApp messages for booking confirmations, reminders, and prescriptions.

---

## C. FRONTEND ARCHITECTURE

1. **`App.jsx` (4,822 lines)**:
   - Primary monolithic container managing state for all staff roles (`RECEPTIONIST`, `DOCTOR`, `ADMIN`, `SUPER_ADMIN`).
   - Routing: Uses state-based navigation (`activeTab`) and URL inspection (`window.location.pathname.startsWith('/p/')`) instead of `react-router-dom`.
   - Real-time refresh: Polling loop (`setInterval`) executing every 5 seconds for Receptionist and Doctor views.
   - State variables: 40+ top-level `useState` hooks controlling modal visibility, active datasets, and form parameters.
   - Localization: In-memory `TRANSLATIONS` dictionary supporting English (`en`) and Hindi (`hi`).
2. **`LoginPage.jsx` (628 lines)**:
   - Houses the public landing page, SaaS pricing cards, Razorpay onboarding checkout, and staff login form.
   - Contains hardcoded test credentials in JSX quick-pills (`shiva9532`, `BALAJI932`, `cptiwari`, `recep`).
3. **`PatientPortal.jsx` (1,040 lines)**:
   - Standalone patient self-service application loaded on `/p/:slug` or `/patient`.
   - Supports patient phone OTP authentication, doctor selection, slot calendar view, online Razorpay OPD fee payment, counter booking, and prescription viewing.
4. **`DoctorQueue.jsx` (565 lines)**:
   - Doctor workstation interface displaying active queue, past consultations, patient medical intake notes, clinical note editor, and digital prescription builder.

---

## D. DATABASE

### Core Tables & Relationships

| Table Name | Primary Key | Foreign Keys | Tenancy (`hospital_id`) | Core Relationships | Purpose |
|---|---|---|---|---|---|
| `hospitals` | `id` (VARCHAR 36) | None | Root Tenant | 1:N with departments, doctors, patients, appointments | Hospital master tenant record |
| `hospital_settings` | `id` (VARCHAR 36) | `hospital_id` -> `hospitals.id` | YES | N:1 with hospitals | Key-value custom prompt & Twilio settings |
| `working_hours` | `id` (VARCHAR 36) | `hospital_id` -> `hospitals.id` | YES | N:1 with hospitals | Weekly hospital opening/closing times |
| `departments` | `id` (VARCHAR 36) | `hospital_id` -> `hospitals.id` | YES | 1:N with doctors | Clinical departments |
| `doctors` | `id` (VARCHAR 36) | `hospital_id`, `department_id` | YES | 1:N schedules, leaves, appointments | Doctor profiles & OPD fees |
| `doctor_schedules` | `id` (VARCHAR 36) | `doctor_id` -> `doctors.id` | Indirect | N:1 with doctors | Weekly shift timing templates |
| `doctor_leaves` | `id` (VARCHAR 36) | `doctor_id` -> `doctors.id` | Indirect | N:1 with doctors | Doctor leave dates & approval status |
| `hospital_holidays` | `id` (VARCHAR 36) | `hospital_id` -> `hospitals.id` | YES | N:1 with hospitals | Public holiday schedule blockouts |
| `patients` | `id` (VARCHAR 36) | `hospital_id`, `insurance_provider_id` | YES | 1:N appointments | Patient records & phone identity |
| `appointments` | `id` (VARCHAR 36) | `hospital_id`, `patient_id`, `doctor_id` | YES | 1:N status_history, 1:1 intake, 1:1 consultation | Central booking records |
| `appointment_status_history`| `id` (VARCHAR 36) | `appointment_id` -> `appointments.id` | Indirect | N:1 with appointments | Audit trail of status transitions |
| `patient_intakes` | `id` (VARCHAR 36) | `appointment_id` -> `appointments.id` | Indirect | 1:1 with appointments | Post-booking AI medical questionnaire data |
| `consultation_notes` | `id` (VARCHAR 36) | `appointment_id`, `patient_id`, `doctor_id` | Indirect | 1:1 with appointments | Doctor clinical notes & prescriptions |
| `call_logs` | `id` (VARCHAR 36) | `hospital_id` -> `hospitals.id` | YES | 1:1 voice_sessions | Twilio incoming call telemetry |
| `voice_sessions` | `id` (VARCHAR 36) | `call_log_id`, `patient_id` | Indirect | 1:N conversation_logs | Active AI voice call state |
| `conversation_logs` | `id` (VARCHAR 36) | `voice_session_id` -> `voice_sessions.id` | Indirect | N:1 with voice_sessions | Transcript lines for AI and caller |
| `payment_links` | `id` (VARCHAR 36) | `appointment_id` -> `appointments.id` | Indirect | 1:N payments | Payment gateway transaction requests |
| `payments` | `id` (VARCHAR 36) | `payment_link_id` -> `payment_links.id` | Indirect | N:1 with payment_links | Gateway payment transaction records |
| `users` | `id` (VARCHAR 36) | `hospital_id` -> `hospitals.id` | YES (Nullable for SuperAdmin)| 1:N user_roles | Staff and dashboard login accounts |
| `roles` | `id` (VARCHAR 36) | None | Global | 1:N user_roles, role_permissions | RBAC system roles |
| `user_roles` | `id` (VARCHAR 36) | `user_id`, `role_id` | Indirect | N:1 users, N:1 roles | User-to-Role assignments |

---

## E. COMPLETE API INVENTORY

| # | Method | Path | Purpose | Auth Required | Role Required | DB Tables | Frontend Consumer | External Services | Known Risks |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `GET` | `/health` | DB ping & service health | No | None | None (`SELECT 1`) | Monitoring / Docker | MySQL | Returns raw DB error string if connection fails. |
| 2 | `GET` | `/api/v1/hospitals` | List all hospitals | Yes | `SUPER_ADMIN` | `hospitals`, `hospital_settings` | `App.jsx` (Super Admin) | None | Returns plaintext Twilio Auth Tokens in response. |
| 3 | `DELETE`| `/api/v1/hospitals/{hospital_id}` | Delete hospital tenant | Yes | `SUPER_ADMIN` | `hospitals` | `App.jsx` (Super Admin) | None | Permanent cascade deletion of all tenant data. |
| 4 | `PUT` | `/api/v1/hospitals/{hospital_id}/toggle-status` | Suspend/Activate hospital | Yes | `SUPER_ADMIN` | `hospitals` | `App.jsx` (Super Admin) | None | No audit logging. |
| 5 | `POST` | `/api/v1/hospitals/{hospital_id}/upgrade-plan` | Upgrade SaaS tier | Yes | `SUPER_ADMIN` | `hospitals` | `App.jsx` (Super Admin / Admin) | Razorpay | No server-side payment verification for upgrade. |
| 6 | `POST` | `/api/v1/hospitals/{hospital_id}/twilio` | Save Twilio keys | Yes | `SUPER_ADMIN` | `hospital_settings` | `App.jsx` (Super Admin) | Twilio | Stores unencrypted Twilio Auth Tokens in DB. |
| 7 | `GET` | `/api/v1/hospital/departments` | List departments | Yes | `ADMIN`, `RECEPTIONIST` | `departments` | `App.jsx` (Receptionist / Admin) | None | Defaults to `hosp_default` if tenant context null. |
| 8 | `GET` | `/api/v1/hospital/stats` | Hospital dashboard metrics | Yes | `ADMIN`, `SUPER_ADMIN` | `appointments`, `doctors`, `patients` | `App.jsx` (Admin) | None | Computes live aggregates on every page load. |
| 9 | `POST` | `/api/v1/auth/register-hospital` | Hospital self-onboarding | No | None | `hospitals`, `users`, `roles`, `user_roles` | `LoginPage.jsx` (Onboarding) | Razorpay | Seeds default doctor without transaction rollback if error. |
| 10 | `POST` | `/api/v1/hospital/register-staff` | Create doctor/receptionist | Yes | `ADMIN`, `SUPER_ADMIN` | `users`, `user_roles`, `doctors`, `doctor_schedules` | `App.jsx` (Admin) | None | Plaintext password hashed via bcrypt. |
| 11 | `POST` | `/api/v1/auth/login` | Staff OAuth2 login | No | None | `users`, `user_roles`, `roles` | `LoginPage.jsx` (Login) | None | Hardcoded backdoor credentials bypass database. |
| 12 | `POST` | `/api/v1/super-admin/register` | Create super admin | Yes | `SUPER_ADMIN` | `users`, `user_roles`, `roles` | `App.jsx` (Super Admin) | None | Scoped strictly to super admin. |
| 13 | `GET` | `/api/v1/appointments` | List appointments | Yes | Authenticated staff | `appointments`, `patients`, `doctors` | `App.jsx` (Receptionist / Doctor) | None | 5-second polling creates high DB query load. |
| 14 | `POST` | `/api/v1/appointments` | Create appointment (Internal)| Yes | `ADMIN`, `RECEPTIONIST` | `appointments`, `patients` | None (Direct API) | None | Schema validated via Pydantic. |
| 15 | `DELETE`| `/api/v1/appointments/{appointment_id}` | Hard delete appointment | Yes | `ADMIN`, `SUPER_ADMIN` | `appointments` | None (Direct API) | None | Hard delete destroys audit trail. |
| 16 | `GET` | `/api/v1/appointments/availability` | Public slot checker | No | None | `doctor_schedules`, `appointments`, `doctor_leaves` | `App.jsx` | None | Publicly accessible without rate limiting. |
| 17 | `POST` | `/api/v1/doctors` | Legacy doctor creation | Yes | `ADMIN`, `SUPER_ADMIN` | `doctors` | None (Legacy) | None | Superseded by `register-staff`. |
| 18 | `GET` | `/api/v1/doctors` | List doctors | Yes | Authenticated staff | `doctors`, `departments` | `App.jsx` (Receptionist / Admin) | None | Returns active doctor profiles. |
| 19 | `GET` | `/api/v1/hospital/staff` | List staff members | Yes | `ADMIN`, `SUPER_ADMIN` | `users`, `user_roles`, `doctors` | `App.jsx` (Admin) | None | Exposes staff phone and email. |
| 20 | `POST` | `/api/v1/hospital/leaves` | Apply doctor leave | Yes | `DOCTOR`, `ADMIN` | `doctor_leaves` | `App.jsx` (Doctor / Admin) | None | Defaults to `PENDING` status. |
| 21 | `GET` | `/api/v1/hospital/leaves` | List leaves | Yes | Authenticated staff | `doctor_leaves`, `doctors` | `App.jsx` (Doctor / Admin) | None | Scoped to active `hospital_id`. |
| 22 | `DELETE`| `/api/v1/hospital/leaves/{leave_id}` | Delete leave | Yes | `DOCTOR`, `ADMIN` | `doctor_leaves` | `App.jsx` (Doctor / Admin) | None | Validates ownership. |
| 23 | `POST` | `/api/v1/hospital/leaves/{leave_id}/approve` | Approve leave | Yes | `ADMIN`, `SUPER_ADMIN` | `doctor_leaves`, `appointments` | `App.jsx` (Admin) | None | Auto-cancels conflicting appointments. |
| 24 | `POST` | `/api/v1/hospital/leaves/{leave_id}/reject` | Reject leave | Yes | `ADMIN`, `SUPER_ADMIN` | `doctor_leaves` | `App.jsx` (Admin) | None | Reverts leave status. |
| 25 | `DELETE`| `/api/v1/hospital/staff/{user_id}` | Delete staff user | Yes | `ADMIN`, `SUPER_ADMIN` | `users`, `doctors` | `App.jsx` (Admin) | None | Deletes user and associated doctor record. |
| 26 | `PUT` | `/api/v1/hospital/staff/doctor/{doctor_id}` | Update doctor schedule | Yes | `ADMIN`, `SUPER_ADMIN` | `doctors`, `doctor_schedules` | `App.jsx` (Admin) | None | Replaces schedule records. |
| 27 | `POST` | `/api/v1/patients` | Register patient | Yes | `ADMIN`, `RECEPTIONIST` | `patients` | `App.jsx` (Receptionist) | None | Internal registration. |
| 28 | `GET` | `/api/v1/receptionist/schedule` | HTML schedule view | No | None | `doctors`, `appointments` | None (Browser debug) | None | Unauthenticated HTML page left in codebase. |
| 29 | `POST` | `/api/v1/payment/create-order` | Razorpay order creation | Yes | Authenticated staff | `appointments`, `payment_links` | None (Direct API) | Razorpay | Requires Razorpay keys in `.env`. |
| 30 | `POST` | `/api/v1/payment/verify` | Verify payment signature | Yes | Authenticated staff | `payments`, `appointments` | None (Direct API) | Razorpay | Validates HMAC signature. |
| 31 | `GET` | `/api/v1/payment/checkout` | HTML checkout page | No | None | `appointments` | None (Legacy) | Razorpay | Legacy hosted checkout page. |
| 32 | `POST` | `/api/v1/payment/confirm/{appointment_id}` | Counter payment confirmation | Yes | `RECEPTIONIST`, `ADMIN` | `appointments`, `status_history` | `App.jsx` (Receptionist) | None | Sets `payment_status = 'PAID'`. |
| 33 | `POST` | `/api/v1/appointments/{appointment_id}/status` | Status transition (Reschedule/Cancel) | Yes | `RECEPTIONIST`, `ADMIN` | `appointments`, `status_history` | `App.jsx` (Receptionist) | WhatsApp (Twilio) | IDOR vulnerability: Missing hospital tenancy check. |
| 34 | `POST` | `/api/v1/appointments/{appointment_id}/finish-consultation` | Finish doctor consult | Yes | `DOCTOR`, `ADMIN` | `appointments` | `App.jsx` (Doctor Queue) | None | Sets status to `CONSULTATION_FINISHED`. |
| 35 | `POST` | `/api/v1/appointments/{appointment_id}/complete` | Complete & prescribe | Yes | `DOCTOR`, `RECEPTIONIST`, `ADMIN` | `appointments`, `consultation_notes` | `App.jsx` (Doctor Queue) | WhatsApp (Twilio) | Sends prescription text to patient phone. |
| 36 | `GET` | `/api/v1/receptionist/booked-slots` | Fetch busy slots | Yes | Authenticated staff | `appointments`, `doctor_schedules` | `App.jsx` (Receptionist) | None | Missing explicit role restriction. |
| 37 | `POST` | `/api/v1/appointments/mark-missed` | Bulk mark missed | Yes | `RECEPTIONIST`, `ADMIN` | `appointments` | `App.jsx` (Receptionist) | None | Scoped by `hospital_id`. |
| 38 | `POST` | `/api/v1/appointments/bulk-cancel` | Bulk cancel doctor day | Yes | `ADMIN`, `RECEPTIONIST` | `appointments`, `status_history` | `App.jsx` (Receptionist) | WhatsApp (Twilio) | Triggers outbound WhatsApp notifications. |
| 39 | `GET` | `/api/v1/hospital/profile` | Active hospital details | Yes | `ADMIN`, `SUPER_ADMIN` | `hospitals`, `users` | `App.jsx` (Admin) | None | Returns plaintext `admin_password` in JSON. |
| 40 | `PUT` | `/api/v1/hospital/profile` | Update hospital profile | Yes | `ADMIN`, `SUPER_ADMIN` | `hospitals`, `users` | `App.jsx` (Admin) | None | Updates hospital name and admin password. |
| 41 | `POST` | `/api/v1/hospital/settings` | Save LLM system prompt | Yes | `ADMIN`, `SUPER_ADMIN` | `hospital_settings` | `App.jsx` (Admin) | None | Customizes prompt behavior. |
| 42 | `POST` | `/api/v1/receptionist/book-appointment` | Receptionist manual booking | Yes | `RECEPTIONIST`, `ADMIN` | `patients`, `appointments` | `App.jsx` (Receptionist) | WhatsApp (Twilio) | Sends confirmation WhatsApp to patient. |
| 43 | `GET` | `/api/v1/hospital/patients/search` | Search patients | Yes | `RECEPTIONIST`, `ADMIN` | `patients`, `appointments` | `App.jsx` (Receptionist) | None | Missing LIKE wildcard sanitization. |
| 44 | `GET` | `/api/v1/patient/hospital/{slug}` | Public hospital page | No | None | `hospitals`, `departments`, `doctors` | `PatientPortal.jsx` | None | Public landing view for patient portal. |
| 45 | `GET` | `/api/v1/patient/doctors` | Public doctor list | No | None | `doctors`, `departments` | `PatientPortal.jsx` | None | Returns doctor profiles and OPD fees. |
| 46 | `GET` | `/api/v1/patient/doctors/{doctor_id}/slots` | Public slot calculator | No | None | `doctor_schedules`, `appointments`, `doctor_leaves` | `PatientPortal.jsx` | None | Computes 30-min available slots for date. |
| 47 | `POST` | `/api/v1/patient/appointments` | Patient self booking | Yes (Patient JWT) | `PATIENT` | `appointments`, `patients` | `PatientPortal.jsx` | WhatsApp (Twilio) | Supports family booking (`patient_name_override`). |
| 48 | `GET` | `/api/v1/patient/appointments` | Patient appointment list | Yes (Patient JWT) | `PATIENT` | `appointments`, `doctors` | `PatientPortal.jsx` | None | Scoped by authenticated patient phone/ID. |
| 49 | `GET` | `/api/v1/patient/appointments/{appointment_id}/prescription` | View prescription | Yes (Patient JWT) | `PATIENT` | `consultation_notes`, `appointments` | `PatientPortal.jsx` | None | Accessible once appointment is `COMPLETED`. |
| 50 | `POST` | `/api/v1/patient/appointments/{appointment_id}/confirm-payment` | Confirm patient payment | Yes (Patient JWT) | `PATIENT` | `appointments` | `PatientPortal.jsx` | None | Critical Bug: `bookedAppointmentId` is null in UI. |
| 51 | `GET` | `/api/v1/patient/profile` | Get patient profile | Yes (Patient JWT) | `PATIENT` | `patients` | `PatientPortal.jsx` | None | Returns registered patient details. |
| 52 | `PUT` | `/api/v1/patient/profile` | Update patient profile | Yes (Patient JWT) | `PATIENT` | `patients` | `PatientPortal.jsx` | None | Updates name and DOB. |
| 53 | `POST` | `/api/v1/voice/inbound` | Twilio inbound webhook | No | None | `hospitals`, `call_logs`, `voice_sessions` | Twilio Voice Service | Twilio | Missing `X-Twilio-Signature` verification. |
| 54 | `POST` | `/api/v1/voice/gather/{voice_session_id}` | Twilio Gather fallback | No | None | `voice_sessions`, `call_logs` | Twilio Voice Service | Twilio | Fallback speech recognition handler. |
| 55 | `POST` | `/api/v1/voice/fallback` | Twilio error fallback | No | None | `call_logs` | Twilio Voice Service | Twilio | Returns emergency hangup TwiML. |
| 56 | `WS` | `/api/v1/voice/stream/{voice_session_id}` | Bidirectional audio WS | No | None | `voice_sessions`, `conversation_logs`, `appointments` | Twilio Media Stream | Twilio & Gemini Live | Connects Twilio μ-law audio to Google Gemini Live. |
| 57 | `POST` | `/api/v1/whatsapp/webhook` | Incoming WhatsApp webhook | No | None | `appointments`, `patient_intakes` | Twilio WhatsApp API | Twilio & Gemini | Missing Twilio signature verification. |

---

## F. AUTHENTICATION FLOW

```
1. Client submits credentials -> POST /api/v1/auth/login (OAuth2 URLSearchParams)
2. Hardcoded Backdoor Check:
   - If username in ["shiva9532", "admin_cp", "doctor_cp", "receptionist_cp"] and password matches hardcoded list:
     -> Generates JWT token without database lookup.
3. Database Verification (for non-backdoor users):
   - Queries SELECT * FROM users WHERE username = :username AND is_active = True
   - Verifies plain text password against bcrypt hash via bcrypt.checkpw()
   - Queries user roles from user_roles and roles tables
4. JWT Access Token Creation:
   - Payload: {"sub": username, "role": role_name, "hospital_id": hospital_id, "user_id": user_id, "exp": now + 24h}
   - Signed with settings.JWT_SECRET_KEY using HS256
5. Client Storage:
   - Stored in browser localStorage: 'jwt_token', 'user_role', 'hospital_id', 'user_id', 'username'
6. Authenticated Requests:
   - Sent via HTTP Header: `Authorization: Bearer <jwt_token>`
7. Backend Token Validation (get_current_user dependency):
   - Decodes token using settings.JWT_SECRET_KEY
   - If sub in ["admin_cp", "doctor_cp", "receptionist_cp", "shiva9532"]:
     -> Returns synthetic User instance (DB bypassed)
   - Otherwise: Queries User table to return active user
8. Multi-Tenant Scoping:
   - Routes inspect `current_user.hospital_id` to filter database queries
   - Flaw: Multiple routes fallback to `"hosp_default"` if `current_user.hospital_id` is null.
```

---

## G. APPOINTMENT FLOW

```
1. Selection: Patient or Receptionist selects Doctor, Target Date, and Desired Slot.
2. Slot Calculation (SchedulingEngine):
   - Loads DoctorSchedule for day of week.
   - Generates 30-minute intervals (e.g. 10:00, 10:30, 11:00).
   - Excludes hospital holidays, doctor approved leaves, and existing booked appointments.
3. Booking Execution (AppointmentEngine):
   - Validates patient exists, doctor exists, and date is not in the past.
   - Rejects same-day phone bookings (source='VOICE').
   - Inserts record into `appointments` with status='SCHEDULED', payment_status='PENDING' (or 'PAID' for counter cash).
   - Records initial entry in `appointment_status_history`.
4. Payment:
   - Online: Razorpay checkout modal executes on frontend.
   - Counter: Receptionist collects cash and clicks "Mark Paid" (`POST /payment/confirm/{id}`).
5. Notification:
   - Triggers `WhatsAppNotificationService` to deliver WhatsApp confirmation with date, time, and doctor name.
6. Doctor Queue:
   - Appointment appears in Doctor Workstation (`DoctorQueue.jsx`) via 5-second polling.
7. Consultation:
   - Doctor clicks "Finish Consultation" -> Sets status to `CONSULTATION_FINISHED`.
8. Prescription & Completion:
   - Doctor or Receptionist enters clinical summary, prescription medicines, and follow-up date.
   - Submits `POST /appointments/{id}/complete` -> Status transitions to `COMPLETED`.
   - Prescription record saved to `consultation_notes` and dispatched to patient via WhatsApp.
```

---

## H. VOICE FLOW

```
1. Phone Call: Caller dials hospital phone number.
2. Twilio Webhook: Twilio issues HTTP POST to `/api/v1/voice/inbound`.
3. Inbound Match:
   - Backend matches 'To' line to `Hospital.phone` or `HospitalSetting.twilio_helpline`.
   - Creates `CallLog` (status='in-progress') and `VoiceSession` (status='ACTIVE', state='GREETING').
   - Responds with TwiML XML containing `<Connect><Stream url="wss://<host>/api/v1/voice/stream/{session_id}" /></Connect>`.
4. WebSocket Stream:
   - Twilio establishes bidirectional WebSocket with `/api/v1/voice/stream/{voice_session_id}`.
   - Twilio transmits raw μ-law audio packets (8kHz) wrapped in JSON.
5. Audio Processing:
   - `audio.py` converts μ-law (8kHz) -> Linear PCM 16-bit (16kHz).
   - Audio buffer dispatched to `GeminiLiveClient`.
6. Gemini Live Execution:
   - Google Gemini 2.0 / 1.5 Live streams conversational responses.
   - Executes function calling tools: `book_appointment`, `get_available_slots`, `transfer_to_receptionist`.
7. Appointment Engine:
   - Function calls invoke `AppointmentEngine.book_appointment` to create database records.
8. Response Stream:
   - Gemini PCM audio transformed back to μ-law (8kHz) -> Sent as JSON media events to Twilio.
9. Termination:
   - On hangup, WebSocket closes, `VoiceSession` marked 'TERMINATED', `CallLog` duration persisted.
```

---

## I. EXTERNAL SERVICES

1. **Remote Database**: MySQL 8.0 hosted on Railway Cloud (`aiomysql` async + `pymysql` sync).
2. **Twilio Voice API**: Manages inbound telephony, TwiML call routing, and bidirectional media streams.
3. **Twilio Messaging API**: Delivers automated WhatsApp notifications and SMS OTPs.
4. **Google Gemini Live (Generative AI)**: `gemini-2.5-flash` / `gemini-1.5-flash-latest` for real-time speech processing and entity extraction.
5. **Razorpay Payment Gateway**: Collects OPD consultation fees and SaaS hospital subscription billing.
6. **n8n Automation Engine**: Optional outbound webhook integration for webhook dispatch (`N8N_WEBHOOK_URL`).

---

## J. CURRENT TESTING

| Test Suite Category | Found Items | Description |
|---|---|---|
| **Pytest Automated Tests** | **0 tests** | `tests/conftest.py` is an empty stub; `tests/unit/` and `tests/integration/` contain only `__init__.py`. |
| **`smoke_test.py`** | 1 script | Standalone script executing live HTTP requests against localhost port 8000. |
| **`test_login_api.py`** | 1 script | 15-line script testing `/api/v1/auth/login`. |
| **`test_slot_full.py`** | 1 script | Direct DB script inserting and deleting mock appointments to test slot limits. |
| **`verify_db.py`** | 1 script | Direct DB query script inspecting hospital and doctor counts. |

*Total Automated Test Cases: **0***  
*Total Manual / Ad-hoc Test Scripts: **4***

---

## K. RUNTIME BASELINE VERIFICATION

| Verification Check | Target Component | Command Executed | Result Status | Observed Output |
|---|---|---|---|---|
| **Backend Import Check** | Python / FastAPI Factory | `python -c "import app.main; print(app.main.app.title)"` | **VERIFIED (PASS)** | `FastAPI application instance successfully created and configured.` |
| **Database Connectivity** | MySQL / Railway Cloud | `python -c "<asyncio DB ping script>"` | **VERIFIED (PASS)** | `Database connectivity successful! Result: 1 (Hospitals: 1, Users: 3, Appointments: 5)` |
| **Alembic Migration State**| Alembic Engine | `python -m alembic heads` | **VERIFIED (PASS)** | Current head: `ba53ba628a09 (head)` |
| **Frontend Build Check** | Vite / React 19 Client | `npm run build` (in `frontend/`) | **VERIFIED (PASS)** | `✓ built in 1.64s` (0 build errors, assets generated) |
| **Automated Test Run** | Pytest Suite | `python -m pytest tests/` | **VERIFIED (EMPTY)** | `collected 0 items, no tests ran in 0.07s` (Exit code 1) |

---

## L. BASELINE BUG LIST

### Critical Severity (Must Be Fixed Before Launch)
1. **[CRITICAL] Hardcoded Backdoor Credentials in `/auth/login`**: `appointments.py` (lines 945–1020) and `dependencies.py` (lines 70–87) allow bypassing database authentication with static passwords (`#@112233`, `12345678`, `password123`).
2. **[CRITICAL] Plaintext Admin Password Leak in API**: `GET /api/v1/hospital/profile` returns the hospital's plaintext `admin_password` in JSON responses (`App.jsx` line 843).
3. **[CRITICAL] Exposed Twilio Auth Tokens**: `GET /api/v1/hospitals` returns plaintext Twilio Account SIDs and Auth Tokens to any authenticated Super Admin client.
4. **[CRITICAL] Patient Portal Payment Confirmation Crash**: `PatientPortal.jsx` (line 459) calls `/patient/appointments/null/confirm-payment` because `bookedAppointmentId` is never assigned prior to `bookStep === 4`.
5. **[CRITICAL] Unverified Payment Confirmations**: `POST /patient/appointments/{id}/confirm-payment` marks appointments as `PAID` without verifying Razorpay HMAC signatures.
6. **[CRITICAL] Hardcoded Test Razorpay Keys in Frontend**: `LoginPage.jsx`, `PatientPortal.jsx`, and `App.jsx` hardcode test key `rzp_test_TDfSGFZwtVgpme`.
7. **[CRITICAL] Static Patient OTP Delivery**: `patient_auth.py` (line 52) assigns static OTP `"1234"` to all patients.
8. **[CRITICAL] IDOR on Appointment Status Updates**: `POST /appointments/{id}/status` lacks a `hospital_id` tenancy filter.
9. **[CRITICAL] Unauthenticated Inbound Twilio Webhooks**: `voice.py` and `whatsapp_webhook.py` do not validate `X-Twilio-Signature`.

### High Severity
1. **[HIGH] Monolithic File Structure**: `appointments.py` (4,799 lines) and `App.jsx` (4,822 lines) violate modular software design.
2. **[HIGH] Default Hospital Fallback Data Leaks**: Routes default to `"hosp_default"` when user `hospital_id` is null.
3. **[HIGH] Double Booking Race Condition**: `AppointmentEngine` lacks `with_for_update()` database locks on slot reservation.
4. **[HIGH] Insecure Wildcard CORS**: `BACKEND_CORS_ORIGINS = ["*"]` combined with `allow_credentials=True`.
5. **[HIGH] 0% Automated Test Coverage**: No pytest tests protect core clinical and scheduling logic.
6. **[HIGH] Hardcoded Quick-Login Credentials in UI**: `LoginPage.jsx` displays admin and doctor passwords in public UI pills.

### Medium Severity
1. **[MEDIUM] 5-Second HTTP Polling**: Doctor and Receptionist dashboards poll the server every 5 seconds instead of using WebSockets.
2. **[MEDIUM] Missing Top-Level React Error Boundary**: Uncaught component errors crash the application to a white screen.
3. **[MEDIUM] Missing Database Indexes**: No indexes on `appointments.status`, `payment_status`, or `patient_name_override`.
4. **[MEDIUM] Dead Frontend Component**: `Sidebar.jsx` is imported but never rendered.
5. **[MEDIUM] Hardcoded Logging String**: `middleware.py` matches `"balaji"` in URL path to hardcode hospital ID.

### Low Severity
1. **[LOW] Console Debug Logs**: Verbose `console.log` statements present in production client code.
2. **[LOW] Missing Localization Key**: PatientPortal lacks `'cancel'` key in its translation table.
3. **[LOW] Hardcoded Hospital Names in Placeholders**: "C P Tiwari Hospital" and "Apollo Hospital" hardcoded in settings input placeholders.

---

## M. PRODUCTION BLOCKERS

1. **Removal of all hardcoded credentials and backdoors from backend and frontend**.
2. **Implementation of server-side Razorpay signature verification**.
3. **Correction of the Patient Portal payment confirmation null-pointer bug**.
4. **Implementation of cryptographic Twilio webhook signature validation**.
5. **Enforcement of strict multi-tenant scoping on all appointment status and mutation endpoints**.
6. **Replacement of static OTP `"1234"` with real SMS/WhatsApp OTP delivery**.
7. **Creation of an automated pytest regression test suite**.

---

## N. SAFE CHANGE PLAN

```
┌────────────────────────────────────────────────────────────────────────────┐
│ STEP 1: TEST HARNESS & REGRESSION BASELINE (NON-BREAKING)                  │
│ - Set up pytest configuration and SQLite / local MySQL test fixtures.     │
│ - Implement unit tests for SchedulingEngine, AppointmentEngine, & Auth.    │
│ - Verify all baseline tests PASS against current business rules.           │
└─────────────────────────────────────┬──────────────────────────────────────┘
                                      │
                                      ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ STEP 2: CRITICAL SECURITY & AUTHENTICATION HARDENING                       │
│ - Remove hardcoded backdoors in appointments.py and dependencies.py.       │
│ - Strip admin_password and Twilio auth tokens from API response payloads.  │
│ - Fix PatientPortal confirmPayment UUID assignment bug.                    │
│ - Implement server-side Razorpay HMAC signature verification.              │
│ - Replace static OTP '1234' with dynamic OTP generation.                   │
│ - Add hospital_id tenancy check to POST /appointments/{id}/status.         │
│ - Validate changes against Step 1 test harness.                            │
└─────────────────────────────────────┬──────────────────────────────────────┘
                                      │
                                      ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ STEP 3: MULTI-TENANT ISOLATION & WEBHOOK VALIDATION                        │
│ - Eliminate all hosp_default fallback leaks.                               │
│ - Implement X-Twilio-Signature validation for voice & WhatsApp webhooks.   │
│ - Add with_for_update() row locking to appointment booking transactions.   │
│ - Restrict CORS origins in production configuration.                       │
└─────────────────────────────────────┬──────────────────────────────────────┘
                                      │
                                      ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ STEP 4: ARCHITECTURAL MODULARIZATION & UI ROBUSTNESS                       │
│ - Modularize appointments.py into dedicated v1 endpoint routers.           │
│ - Introduce react-router-dom and decompose App.jsx into portal pages.      │
│ - Add top-level React ErrorBoundary.                                       │
│ - Synchronize Alembic migrations with full database model schema.          │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## BASELINE STATUS SUMMARY

* **Backend**: **PASS** (Imports clean, Uvicorn factory initializes without error)
* **Frontend**: **PASS** (Vite builds cleanly in 1.64s with 0 errors)
* **Database**: **PASS** (Async connection verified, all tables queryable)
* **API Startup**: **PASS** (FastAPI app factory configured on port 8001)
* **Existing Tests**: **0 Automated Tests (4 Manual Scripts)**
* **Production Readiness**: **NOT READY (42%)**

---

### Commands Executed and Results

1. **Backend Import Verification**:
   ```powershell
   python -c "import app.main; print('Backend import successful! App title:', app.main.app.title)"
   ```
   *Result*: `Backend import successful! App title: Hospital AI Voice Receptionist` (Exit Code 0).

2. **Database Connectivity Verification**:
   ```powershell
   python -c "<asyncio DB ping script>"
   ```
   *Result*: `Database connectivity successful! Result: 1 (Total hospitals: 1, Total users: 3, Total appointments: 5)` (Exit Code 0).

3. **Alembic Revisions Check**:
   ```powershell
   python -m alembic heads
   ```
   *Result*: `ba53ba628a09 (head)` (Exit Code 0).

4. **Frontend Build Verification**:
   ```powershell
   npm run build # inside frontend/
   ```
   *Result*: `dist/assets/index-BMYJn6Ua.js 443.90 kB │ gzip: 112.57 kB | ✓ built in 1.64s` (Exit Code 0).

5. **Pytest Suite Verification**:
   ```powershell
   python -m pytest tests/
   ```
   *Result*: `collected 0 items | no tests ran in 0.07s` (Exit Code 1).
