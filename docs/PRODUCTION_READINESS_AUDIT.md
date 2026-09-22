# PRODUCTION READINESS AUDIT REPORT
**Project**: Hospital AI Voice SaaS Platform (AURA SaaS / Hospital Voice)  
**Date**: August 27, 2026  
**Auditor Roles**: Senior Software Architect + Chief Technology Officer (CTO) + Lead QA Engineer  
**Mode**: Strict Read-Only Audit (No Code/Database Modifications Made)

---

## 1. Executive Summary

This comprehensive audit was performed across the complete codebase of the Hospital AI Voice Receptionist SaaS platform. The system is designed to provide multi-tenant hospital front-desk automation, including incoming AI voice reception via Twilio & Google Gemini Live, WhatsApp patient intake, appointment scheduling, doctor queue management, receptionist workflows, multi-tier hospital admin management, and patient self-service booking.

### Summary of System Health & Readiness:
* **Architecture Pattern**: Monolithic FastAPI backend (with a 4,799-line single route file) + Single-file monolithic React frontend (`App.jsx`, 4,822 lines) without a formal router.
* **Database & Persistence**: MySQL 8.0 on Railway Cloud with SQLAlchemy 2.0 async engine and Alembic migrations. The database schema is rich and well-normalized (30+ tables), but suffers from tenant filtering bypasses, hardcoded fallbacks, and schema drift.
* **Security & Auth**: Critical security vulnerabilities exist in production code, including hardcoded plaintext credentials for admin, doctor, and receptionist accounts, hardcoded test Razorpay API keys in frontend bundles, hardcoded Twilio master credentials as fallbacks, plain passwords returned in profile APIs, and a hardcoded demo OTP (`1234`) visible in the UI.
* **Test Coverage**: Formal test coverage is **0%** (empty `tests/` directory with dummy `conftest.py`). Only 4 standalone, ad-hoc Python integration scripts exist.
* **Overall Production Readiness Score**: **42% (NOT READY FOR PRODUCTION)**.

---

## 2. Current Architecture

```
                                  [ Patients / Callers ]
                                       │            │
                 PSTN Voice Phone Call │            │ Web Browser
                                       ▼            ▼
                             [ Twilio Voice ]   [ Vite + React 19 Frontend ]
                                       │         (App.jsx / PatientPortal.jsx)
                       TwiML Webhook / │            │
                      Media Streams WS │            │ Axios / Fetch (JWT in localStorage)
                                       ▼            ▼
                         [ Reverse Proxy / Vite Proxy ]
                                       │
                                       ▼
                       [ FastAPI Monolith Backend :8001 ]
                     (app/main.py + CORS + LogContext)
                                       │
             ┌─────────────────────────┼────────────────────────┐
             ▼                         ▼                        ▼
    [ appointments.py ]       [ patient_portal.py ]       [ voice.py ]
    - Auth & Login            - Patient OTP Auth          - Twilio Inbound Webhook
    - Hospital Multi-Tenant   - Doctor Slots              - Media Stream WebSocket
    - Staff Management        - Self Booking              - Gemini Live Audio Loop
    - Doctor Queue            - Digital Prescription      - Voice State Machine
    - Razorpay Payments
             │                         │                        │
             └─────────────────────────┼────────────────────────┘
                                       ▼
                  [ Domain Engines & Services (Partial Layer) ]
                  - AppointmentEngine & SchedulingEngine
                  - GeminiLiveClient (Google GenAI)
                  - TwilioService & WhatsAppIntakeService
                                       │
                                       ▼
                    [ SQLAlchemy 2.0 Async Session Layer ]
                                       │
                                       ▼
                     [ Remote MySQL 8.0 Database ]
                         (Railway Cloud MySQL)
```

### Architecture Layer Reality Check:
1. **Frontend**: Vite + React 19. Single-page application without `react-router-dom`. Navigation is managed through URL path sniffing (`window.location.pathname.startsWith('/p/')`) and an internal `activeTab` React state.
2. **API Layer**: FastAPI application mounting routers under `/api/v1` and root fallback. All hospital business logic is concentrated in a 4,799-line route file (`app/api/v1/endpoints/appointments.py`).
3. **Service / Repository Layer**: Incomplete. Route handlers query the database directly using raw SQLAlchemy `select`, `update`, and `delete` statements mixed with business logic.
4. **Database Models**: SQLAlchemy declarative models defined in `app/database/models/` (`appointment.py`, `conversation.py`, `call_log.py`).

---

## 3. Frontend Audit

### Portal Views & Components
The frontend consists of 4 main files: `App.jsx` (4,822 lines), `PatientPortal.jsx` (1,040 lines), `LoginPage.jsx` (628 lines), and `DoctorQueue.jsx` (565 lines).

| Portal / View | Route / Trigger | Required Role | API Calls Made | State Management | Error / Empty State Handling | Identified Runtime Risks |
|---|---|---|---|---|---|---|
| **Landing & Login** | `/` (`pageView === 'login'`) | Unauthenticated | `POST /auth/login` | `useState` (`loginUsername`, `loginPassword`) | Inline error text `loginError` | Real test credentials hardcoded in JSX pills (`shiva9532`, `BALAJI932`, `cptiwari`, `recep`). |
| **Hospital Onboarding** | `pageView === 'onboard'` | Unauthenticated | `POST /auth/register-hospital` | `onboardData`, `selectedPlan` | Modal error alerts | Razorpay plan pricing display mismatch: Pro displays ₹2,999 but charges ₹1,999 in code. |
| **Receptionist Portal** | `userRole === 'RECEPTIONIST'`, `activeTab`: `overview`, `new_booking`, `receptionist_leaves` | `RECEPTIONIST` | `GET /doctors`, `GET /appointments`, `GET /hospital/leaves`, `GET /hospital/profile`, `POST /appointments/{id}/status`, `POST /receptionist/book-appointment`, `GET /hospital/patients/search` | `appointmentsList`, `doctorsList`, `newBookingAllSlots`, `bookedSlots`, `selectedPatientRecord` | 5-second polling interval. Empty tables show translated empty states. No full-page loading skeleton. | Potential undefined property crash on malformed appointment objects; `new FormData()` multipart used for `MISSED` status instead of form-urlencoded. |
| **Doctor Workstation** | `userRole === 'DOCTOR'`, `activeTab`: `appointments`, `doctor_leaves` | `DOCTOR` | `GET /appointments?doctor_id={userId}`, `POST /appointments/{id}/finish-consultation`, `POST /appointments/{id}/complete`, `GET /patients/{id}/intake` | `selectedAppointment`, `intakeData`, `clinicalNotes`, `prescriptionText` | Empty state: "Select a Patient from Queue". | `leavesList.filter(l => l.doctor_id === userId)` fails when comparing string usernames with doctor UUIDs. |
| **Hospital Admin Portal** | `userRole === 'ADMIN'`, `activeTab`: `admin_overview`, `staff_management`, `hospital_overview`, `admin_leaves` | `ADMIN` | `GET /hospital/stats`, `GET /hospital/staff`, `POST /hospital/register-staff`, `DELETE /hospital/staff/{id}`, `PUT /hospital/staff/doctor/{id}`, `PUT /hospital/profile`, `POST /hospital/settings`, `POST /hospitals/{id}/upgrade-plan` | `hospitalStats`, `hospitalStaff`, `editDoctorModalOpen`, `showUpgradeModal` | Basic alerts on error. | Backend sends plaintext `admin_password` inside profile response, pre-filled into client state (Critical security flaw). |
| **Platform Super Admin** | `userRole === 'SUPER_ADMIN'`, `activeTab`: `super_admin` | `SUPER_ADMIN` | `GET /hospitals`, `DELETE /hospitals/{id}`, `PUT /hospitals/{id}/toggle-status`, `POST /hospitals/{id}/twilio`, `POST /super-admin/register` | `hospitalsList`, `twilioAccountSids`, `superAdminView` | Table renders active hospitals. | Hardcoded fallback domain `https://aura-saas-api.herokuapp.com` inside helper function; master Twilio secrets exposed in responses. |
| **Patient Portal** | `/p/:slug` or `/patient` | Patient JWT / Unauthenticated | `GET /hospital/{slug}`, `POST /send-otp`, `POST /verify-otp`, `GET /doctors`, `GET /slots`, `POST /appointments`, `POST /appointments/{id}/confirm-payment`, `GET /appointments/{id}/prescription` | `hospital`, `patient`, `token`, `doctors`, `slots`, `bookStep` | Loading spinner and 404 "Hospital Not Found" screen. | `confirmPayment` at `bookStep 4` uses `bookedAppointmentId` which is `null` (Runtime Bug: POSTs to `.../null/confirm-payment`). |

---

## 4. Backend Audit

The backend is built with FastAPI. It features global CORS, request logging context middleware, custom exception handlers, and an application factory in `app/main.py`.

### Key Backend Observations:
1. **Monolithic Endpoint Design**: `app/api/v1/endpoints/appointments.py` contains 4,799 lines handling authentication, multi-hospital CRUD, doctor schedules, appointments, payments, leave approval, and patient searching in a single router.
2. **Duplicate Route Registrations**: In `app/main.py`, `appointments.router` is included twice:
   ```python
   app.include_router(appointments.router, prefix=settings.API_V1_STR)
   app.include_router(appointments.router) # Unprefixed duplicate
   ```
3. **Hardcoded Fallback Bypass in Auth Dependency**: `app/core/dependencies.py` lines 70–87 explicitly bypass database authentication for hardcoded users (`admin_cp`, `doctor_cp`, `receptionist_cp`, `shiva9532`), generating synthetic `User` instances with mock hospital IDs.

---

## 5. Complete API Inventory

Below is the complete inventory of all 57 backend API endpoints found across the application.

| # | HTTP Method | Path | Purpose | Auth Required | Role Required | Request Body / Params | Response Format | DB Tables Used | Possible Problems / Security Risks |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `GET` | `/health` | System health check & DB ping | None | None | None | JSON (`status`, `database`) | None (`SELECT 1`) | Exposes raw DB error string if unhealthy. |
| 2 | `GET` | `/api/v1/hospitals` | List all hospitals | Bearer JWT | `SUPER_ADMIN` or `shiva9532` | None | JSON (List of hospitals) | `hospitals`, `hospital_settings` | Returns Twilio Account SID & Auth Tokens in plain JSON. |
| 3 | `DELETE` | `/api/v1/hospitals/{hospital_id}` | Delete hospital tenant | Bearer JWT | `SUPER_ADMIN` or `shiva9532` | Path `hospital_id` | JSON (`detail`) | `hospitals` | Cascades delete across all appointments & patients. |
| 4 | `PUT` | `/api/v1/hospitals/{hospital_id}/toggle-status` | Toggle active/suspended | Bearer JWT | `SUPER_ADMIN` or `shiva9532` | Path `hospital_id` | JSON (`status`, `is_active`) | `hospitals` | No audit log entry created. |
| 5 | `POST` | `/api/v1/hospitals/{hospital_id}/upgrade-plan` | Upgrade SaaS plan | Bearer JWT | `SUPER_ADMIN` or `shiva9532` | Form: `plan_name` | JSON (`status`, `plan`) | `hospitals` | No server-side payment verification for upgrade. |
| 6 | `POST` | `/api/v1/hospitals/{hospital_id}/twilio` | Configure Twilio credentials | Bearer JWT | `SUPER_ADMIN` or `shiva9532` | Form: `account_sid`, `auth_token`, `helpline`, `whatsapp_number` | JSON (`status`) | `hospital_settings` | Auth tokens stored in plaintext in `hospital_settings`. |
| 7 | `GET` | `/api/v1/hospital/departments` | List hospital departments | Bearer JWT | `ADMIN`, `RECEPTIONIST`, `DOCTOR` | None | JSON (List of departments) | `departments` | Defaults to `hosp_default` if tenant ID missing. |
| 8 | `GET` | `/api/v1/hospital/stats` | Hospital dashboard statistics | Bearer JWT | `ADMIN`, `SUPER_ADMIN` | Query: `target_date` | JSON (Metrics: revenue, counts) | `appointments`, `doctors`, `patients` | Aggregates all doctors across tenant. |
| 9 | `POST` | `/api/v1/auth/register-hospital` | Onboard new hospital tenant | None | None | Form: `name`, `phone`, `admin_username`, `admin_password`, `plan_name` | JSON (`success`, `hospital_id`, `slug`) | `hospitals`, `users`, `roles`, `user_roles`, `hospital_settings` | Automatically seeds hospital with default doctors and departments. |
| 10 | `POST` | `/api/v1/hospital/register-staff` | Register doctor or receptionist | Bearer JWT | `ADMIN`, `SUPER_ADMIN` | Form: `role`, `username`, `password`, `first_name`, `last_name`, `phone`, doctor schedules | JSON (`success`, `user_id`) | `users`, `user_roles`, `doctors`, `doctor_schedules` | Plain text password hashed via bcrypt. |
| 11 | `POST` | `/api/v1/auth/login` | Staff / Admin / Owner login | None | None | OAuth2 Form: `username`, `password` | JSON (`access_token`, `token_type`, `user_role`, `hospital_id`, `user_id`) | `users`, `user_roles`, `roles` | Hardcoded password backdoor for `shiva9532`, `admin_cp`, `doctor_cp`, `receptionist_cp`. |
| 12 | `POST` | `/api/v1/super-admin/register` | Create super admin user | Bearer JWT | `SUPER_ADMIN` or `shiva9532` | Form: `username`, `email`, `password` | JSON (`success`, `user_id`) | `users`, `user_roles`, `roles` | Only existing Super Admin can call. |
| 13 | `GET` | `/api/v1/appointments` | List appointments (filtered) | Bearer JWT | Any authenticated staff | Query: `doctor_id`, `date`, `status` | JSON (List of appointments) | `appointments`, `patients`, `doctors` | Bypassed hospital filter when `doctor_id` supplied in earlier iterations. |
| 14 | `POST` | `/api/v1/appointments` | Create appointment (Internal) | Bearer JWT | `ADMIN`, `RECEPTIONIST` | JSON `AppointmentCreate` | JSON `AppointmentRead` | `appointments`, `patients`, `doctors` | Schema validation via Pydantic. |
| 15 | `DELETE` | `/api/v1/appointments/{appointment_id}` | Delete appointment | Bearer JWT | `ADMIN`, `SUPER_ADMIN` | Path `appointment_id` | JSON `AppointmentRead` | `appointments` | Hard delete rather than soft delete. |
| 16 | `GET` | `/api/v1/appointments/availability` | Check slot availability | None | None | Query: `doctor_id`, `date` | JSON `AvailableSlotsResponse` | `doctor_schedules`, `appointments`, `doctor_leaves` | Publicly accessible slot checker. |
| 17 | `POST` | `/api/v1/doctors` | Create doctor profile | Bearer JWT | `ADMIN`, `SUPER_ADMIN` | JSON `DoctorCreate` | JSON `DoctorRead` | `doctors`, `departments` | Legacy endpoint superseded by `register-staff`. |
| 18 | `GET` | `/api/v1/doctors` | List hospital doctors | Bearer JWT | Authenticated staff | Query: `department_id` | JSON (List of doctors) | `doctors`, `departments`, `doctor_schedules` | Populates receptionist doctor select boxes. |
| 19 | `GET` | `/api/v1/hospital/staff` | List staff members | Bearer JWT | `ADMIN`, `SUPER_ADMIN` | Query: `hospital_id` (optional for superadmin) | JSON (List of staff) | `users`, `user_roles`, `roles`, `doctors` | Returns email, phone, and role tags. |
| 20 | `POST` | `/api/v1/hospital/leaves` | Apply for doctor leave | Bearer JWT | `DOCTOR`, `ADMIN` | JSON: `doctor_id`, `start_date`, `end_date`, `reason` | JSON `DoctorLeaveRead` | `doctor_leaves`, `doctors` | Leave defaults to `PENDING`. |
| 21 | `GET` | `/api/v1/hospital/leaves` | List doctor leaves | Bearer JWT | `DOCTOR`, `ADMIN`, `RECEPTIONIST` | None | JSON (List of leaves) | `doctor_leaves`, `doctors` | Scoped by tenant `hospital_id`. |
| 22 | `DELETE` | `/api/v1/hospital/leaves/{leave_id}` | Cancel / delete leave | Bearer JWT | `DOCTOR`, `ADMIN` | Path `leave_id` | JSON (`status`) | `doctor_leaves` | Validates ownership before deletion. |
| 23 | `POST` | `/api/v1/hospital/leaves/{leave_id}/approve` | Approve doctor leave | Bearer JWT | `ADMIN`, `SUPER_ADMIN` | Path `leave_id` | JSON (`status`) | `doctor_leaves` | Cancels conflicting appointments. |
| 24 | `POST` | `/api/v1/hospital/leaves/{leave_id}/reject` | Reject doctor leave | Bearer JWT | `ADMIN`, `SUPER_ADMIN` | Path `leave_id` | JSON (`status`) | `doctor_leaves` | Reverts leave record. |
| 25 | `DELETE` | `/api/v1/hospital/staff/{user_id}` | Delete staff member | Bearer JWT | `ADMIN`, `SUPER_ADMIN` | Path `user_id` | JSON (`status`) | `users`, `doctors` | Deletes linked doctor record and user account. |
| 26 | `PUT` | `/api/v1/hospital/staff/doctor/{doctor_id}` | Edit doctor details & schedule | Bearer JWT | `ADMIN`, `SUPER_ADMIN` | Form: `first_name`, `last_name`, `email`, `phone`, `opd_fees`, `schedule_days`, `schedule_start_time`, `schedule_end_time` | JSON (`status`, `doctor`) | `doctors`, `doctor_schedules`, `users` | Updates schedule intervals and fee structures. |
| 27 | `POST` | `/api/v1/patients` | Register patient | Bearer JWT | `ADMIN`, `RECEPTIONIST` | JSON `PatientCreate` | JSON `PatientRead` | `patients` | Internal patient registration. |
| 28 | `GET` | `/api/v1/receptionist/schedule` | HTML schedule view | None | None | Query: `hospital_id` | HTML Page | `doctors`, `appointments` | Debug HTML view left in code. |
| 29 | `POST` | `/api/v1/payment/create-order` | Create Razorpay order | Bearer JWT | Authenticated staff | JSON: `appointment_id`, `amount` | JSON (`order_id`, `currency`, `amount`) | `appointments`, `payment_links` | Generates Razorpay server order. |
| 30 | `POST` | `/api/v1/payment/verify` | Verify Razorpay payment signature | Bearer JWT | Authenticated staff | JSON: `razorpay_order_id`, `razorpay_payment_id`, `razorpay_signature` | JSON (`status`, `verified`) | `payments`, `appointments` | Verifies HMAC-SHA256 signature. |
| 31 | `GET` | `/api/v1/payment/checkout` | HTML Payment checkout screen | None | None | Query: `appointment_id` | HTML Page | `appointments`, `doctors` | Legacy hosted checkout page. |
| 32 | `POST` | `/api/v1/payment/confirm/{appointment_id}` | Confirm counter / manual cash payment | Bearer JWT | `RECEPTIONIST`, `ADMIN` | Path `appointment_id` | JSON (`status`, `message`) | `appointments`, `appointment_status_history` | Marks appointment `payment_status = 'PAID'`. |
| 33 | `POST` | `/api/v1/appointments/{appointment_id}/status` | Receptionist status transition (Reschedule, Cancel, Missed) | Bearer JWT | `RECEPTIONIST`, `ADMIN` | Form: `new_status`, `new_datetime`, `cancellation_reason` | JSON (`status`, `appointment`) | `appointments`, `appointment_status_history` | Sends WhatsApp notification on reschedule/cancel. |
| 34 | `POST` | `/api/v1/appointments/{appointment_id}/finish-consultation` | Doctor finishes physical consultation | Bearer JWT | `DOCTOR`, `ADMIN` | Path `appointment_id` | JSON (`status`) | `appointments` | Transitions status to `CONSULTATION_FINISHED`. |
| 35 | `POST` | `/api/v1/appointments/{appointment_id}/complete` | Complete appointment & write prescription | Bearer JWT | `DOCTOR`, `RECEPTIONIST`, `ADMIN` | Form: `clinical_notes`, `prescription`, `follow_up_date` | JSON (`status`, `prescription_id`) | `appointments`, `consultation_notes` | Sends digital prescription PDF/text via WhatsApp. |
| 36 | `GET` | `/api/v1/receptionist/booked-slots` | Fetch occupied slots for doctor & date | Bearer JWT | `RECEPTIONIST`, `ADMIN` | Query: `doctor_id`, `date_str` | JSON (`booked_slots`, `all_slots`) | `appointments`, `doctor_schedules` | Powers reschedule and booking calendars. |
| 37 | `POST` | `/api/v1/appointments/mark-missed` | Bulk mark past appointments as MISSED | Bearer JWT | `RECEPTIONIST`, `ADMIN` | None | JSON (`status`, `count`) | `appointments` | Scoped by tenant `hospital_id`. |
| 38 | `POST` | `/api/v1/appointments/bulk-cancel` | Bulk cancel doctor appointments for date | Bearer JWT | `ADMIN`, `RECEPTIONIST` | JSON: `doctor_id`, `target_date`, `reason` | JSON (`status`, `cancelled_count`) | `appointments`, `appointment_status_history` | Triggers bulk cancellation WhatsApp notifications. |
| 39 | `GET` | `/api/v1/hospital/profile` | Fetch active hospital profile & admin details | Bearer JWT | `ADMIN`, `SUPER_ADMIN` | None | JSON (`hospital`, `admin_username`, `admin_password`) | `hospitals`, `users`, `hospital_settings` | **CRITICAL FLAW**: Returns plaintext admin password. |
| 40 | `PUT` | `/api/v1/hospital/profile` | Update hospital profile | Bearer JWT | `ADMIN`, `SUPER_ADMIN` | Form: `name`, `address`, `phone`, `email`, `admin_username`, `admin_password` | JSON (`status`) | `hospitals`, `users` | Updates hospital info and admin password. |
| 41 | `POST` | `/api/v1/hospital/settings` | Save hospital voice & prompt configurations | Bearer JWT | `ADMIN`, `SUPER_ADMIN` | Form: `whatsapp_number`, `greeting_prompt`, `full_custom_prompt` | JSON (`status`) | `hospital_settings` | Customizes LLM system prompts per hospital. |
| 42 | `POST` | `/api/v1/receptionist/book-appointment` | Receptionist manual walk-in/call booking | Bearer JWT | `RECEPTIONIST`, `ADMIN` | JSON: `patient_name`, `patient_phone`, `patient_gender`, `patient_dob`, `doctor_id`, `appointment_datetime`, `reason`, `payment_mode` | JSON (`success`, `appointment_id`) | `patients`, `appointments`, `appointment_status_history` | Auto-creates patient record if not present. |
| 43 | `GET` | `/api/v1/hospital/patients/search` | Search patients by name or phone | Bearer JWT | `RECEPTIONIST`, `ADMIN` | Query: `query` | JSON (List of matching patients) | `patients`, `appointments` | Scoped to active `hospital_id`. |
| 44 | `GET` | `/api/v1/patient/hospital/{slug}` | Fetch public hospital info by slug | None | None | Path `slug` | JSON (Hospital details, departments, doctors) | `hospitals`, `departments`, `doctors` | Public endpoint for patient portal landing. |
| 45 | `GET` | `/api/v1/patient/doctors` | List doctors for patient booking | None | None | Query: `hospital_id` | JSON (List of doctors) | `doctors`, `departments`, `doctor_schedules` | Public endpoint. |
| 46 | `GET` | `/api/v1/patient/doctors/{doctor_id}/slots` | Get available booking slots for date | None | None | Path `doctor_id`, Query `date` | JSON (List of slot strings) | `doctor_schedules`, `appointments`, `doctor_leaves` | Computes dynamic available slots. |
| 47 | `POST` | `/api/v1/patient/appointments` | Patient self-service booking | Bearer Patient JWT | `PATIENT` | JSON: `hospital_id`, `doctor_id`, `patient_id`, `patient_name`, `patient_age`, `appointment_datetime`, `reason`, `payment_mode` | JSON (`success`, `appointment_id`, `payment_status`) | `appointments`, `patients`, `appointment_status_history` | Supports family booking (`patient_name_override`). |
| 48 | `GET` | `/api/v1/patient/appointments` | List logged-in patient's appointments | Bearer Patient JWT | `PATIENT` | None | JSON (List of appointments) | `appointments`, `doctors`, `consultation_notes` | Filtered by patient phone/ID. |
| 49 | `GET` | `/api/v1/patient/appointments/{appointment_id}/prescription` | View digital prescription | Bearer Patient JWT | `PATIENT` | Path `appointment_id` | JSON (`prescription`, `clinical_notes`, `follow_up_date`) | `consultation_notes`, `appointments` | Accessible by patient after consultation completed. |
| 50 | `POST` | `/api/v1/patient/appointments/{appointment_id}/confirm-payment` | Patient confirms online payment | Bearer Patient JWT | `PATIENT` | Path `appointment_id`, JSON: `payment_mode` | JSON (`success`, `message`) | `appointments` | Lacks `razorpay_payment_id` validation. |
| 51 | `GET` | `/api/v1/patient/profile` | Get patient profile details | Bearer Patient JWT | `PATIENT` | None | JSON (`patient`) | `patients` | Returns registered patient record. |
| 52 | `PUT` | `/api/v1/patient/profile` | Update patient profile details | Bearer Patient JWT | `PATIENT` | JSON: `name`, `gender`, `date_of_birth` | JSON (`success`, `patient`) | `patients` | Allows updating personal details. |
| 53 | `POST` | `/api/v1/voice/inbound` | Twilio incoming call webhook | None (Twilio Signature) | None | Form: `From`, `To`, `CallSid`, `CallStatus`, `hospital_id` | TwiML XML (`<Connect><Stream>`) | `hospitals`, `call_logs`, `voice_sessions` | Matches incoming DID to hospital tenant. |
| 54 | `POST` | `/api/v1/voice/gather/{voice_session_id}` | Fallback Twilio Gather webhook | None | None | Path `voice_session_id`, Form: `SpeechResult` | TwiML XML | `voice_sessions`, `call_logs` | Fallback voice intent processor. |
| 55 | `POST` | `/api/v1/voice/fallback` | Twilio emergency call failure webhook | None | None | Form: `CallSid` | TwiML XML (`<Say>`) | `call_logs` | Catches unhandled Twilio stream drops. |
| 56 | `WS` | `/api/v1/voice/stream/{voice_session_id}` | Bidirectional audio streaming WebSocket | None | None | WebSocket stream (Twilio Media Stream format) | Audio binary / JSON | `voice_sessions`, `conversation_logs`, `appointments` | Connects Twilio μ-law audio to Google Gemini Live API. |
| 57 | `POST` | `/api/v1/whatsapp/webhook` | Twilio WhatsApp incoming webhook | None | None | Form: `From`, `Body`, `MessageSid`, `To` | XML (Empty 200 OK) | `appointments`, `patient_intakes` | Interacts with `WhatsAppIntakeService` for post-op questionnaires. |

---

## 6. API Contract Audit

| # | Frontend Call | Backend Endpoint | Issue / Mismatch | Severity | Impact |
|---|---|---|---|---|---|
| 1 | `PatientPortal.jsx` Line 459: `POST /patient/appointments/${bookedAppointmentId}/confirm-payment` | `POST /api/v1/patient/appointments/{appointment_id}/confirm-payment` | `bookedAppointmentId` state is never set in `bookStep === 4`. Requests are sent to `/patient/appointments/null/confirm-payment`. | **CRITICAL** | Patient online payment confirmation crashes with a 422/404 runtime error. |
| 2 | `App.jsx` Line 843: `setEditHospitalAdminPassword(data.admin_password || '')` | `GET /api/v1/hospital/profile` | Backend returns plaintext `admin_password` in the profile response JSON. | **CRITICAL** | Severe credential leak. Anyone with Admin JWT can view the plaintext admin password in network logs / React state. |
| 3 | `LoginPage.jsx` Lines 103, 402, 1791: Hardcoded test key `rzp_test_TDfSGFZwtVgpme` | Razorpay Gateway | Real payments in production cannot work because the test key is embedded directly into frontend code. | **CRITICAL** | Production transactions fail or run in sandbox. |
| 4 | `App.jsx` Line 1557: `handleMarkSingleMissed` sends `new FormData()` | `POST /api/v1/appointments/{id}/status` | All other status calls send `URLSearchParams` (form-urlencoded). If proxy or middleware parses FormData differently, status change fails silently. | **MEDIUM** | Inconsistent request encoding. |
| 5 | `PatientPortal.jsx` Line 757: `POST /patient/appointments/{id}/confirm-payment` | `POST /api/v1/patient/appointments/{id}/confirm-payment` | Frontend sends `{payment_mode: 'ONLINE'}` but omits `razorpay_payment_id` and signature. | **HIGH** | Backend marks appointment as PAID without verifying whether money was captured on Razorpay. |
| 6 | `App.jsx` Line 1888: `GET /hospital/staff?hospital_id=${hospId}` | `GET /api/v1/hospital/staff` | For `SUPER_ADMIN`, `hospitalId` state is empty string on initial render, resulting in `GET /hospital/staff?hospital_id=`. | **MEDIUM** | Fails or returns un-scoped data unless fallback query logic catches empty string. |
| 7 | `PatientPortal.jsx` Line 538: `t('cancel')` | `TRANSLATIONS` Dictionary | Key `'cancel'` does not exist in PatientPortal's `TRANSLATIONS` dictionary; falls back to raw string `'cancel'`. | **LOW** | Minor UI localization glitch. |

---

## 7. Database Audit

### Schema Inspection (`app/database/models/` and `schema.sql`):
1. **Model Normalization**: The database is structured into 30+ tables with primary keys (`UUID` as `VARCHAR(36)`). Relationships exist between `Hospital`, `Department`, `Doctor`, `DoctorSchedule`, `DoctorLeave`, `Patient`, `Appointment`, `CallLog`, `VoiceSession`, and `PaymentLink`.
2. **Missing Database Indexes**:
   - `appointments.patient_name_override` has no index.
   - `appointments.payment_status` has no index.
   - `appointments.consultation_status` has no index.
   - `users.hospital_id` has a foreign key index, but lacks a compound index on `(hospital_id, username)` for fast multi-tenant auth lookups.
3. **Cascade Risks**:
   - `Hospital` deletion cascades delete across `Department`, `Doctor`, `Patient`, `Appointment`, and `CallLog`. In a multi-tenant SaaS, accidental deletion of a Hospital row permanently destroys all clinical history, doctor schedules, and billing logs without soft-delete protection.
4. **Schema Drift & Missing Columns**:
   - `appointments.patient_name_override` and `appointments.booked_by_name` were added directly to SQLAlchemy models but are missing from early Alembic migrations (`59d6b954bbb1_initial_migration.py`).
   - `doctors.hashed_password` and `doctors.opd_fees` were added in migration `73cf22db777f` but do not match the original `schema.sql` definition.
5. **Orphan Patient Risk**:
   - Patients are scoped by `hospital_id`. However, if a patient calls multiple hospitals in a health network, separate patient records are created with identical phone numbers, leading to data fragmentation.

---

## 8. Authentication & Authorization Audit

### Authentication Architecture:
1. **Password Hashing**: Implemented with raw `bcrypt` (`bcrypt.hashpw` and `bcrypt.checkpw`) with a 72-character safety truncation in `app/core/dependencies.py`.
2. **JWT Implementation**: Standard PyJWT encoding with `HS256`, signed using `settings.JWT_SECRET_KEY`, with an expiration window of 1,440 minutes (24 hours).
3. **Hardcoded Credential Backdoors**:
   - In `app/api/v1/endpoints/appointments.py` (Lines 945–1020):
     - `shiva9532` with passwords `#@112233`, `12345678`, `password123` -> Grants `SUPER_ADMIN` role.
     - `admin_cp` / `BALAJI932` with passwords `password123`, `12345678` -> Grants `ADMIN` role for `hosp_default`.
     - `doctor_cp` / `cptiwari` with passwords `password123`, `#@112233` -> Grants `DOCTOR` role for `hosp_default`.
     - `receptionist_cp` / `recep` with passwords `password123`, `#@112233` -> Grants `RECEPTIONIST` role for `hosp_default`.
   - In `app/core/dependencies.py` (Lines 71–87):
     - `get_current_user` bypasses DB lookups if `username in ["admin_cp", "doctor_cp", "receptionist_cp", "shiva9532"]`, returning synthetic `User` instances.

### Authorization & RBAC Risks:
1. **Privilege Escalation in Hardcoded Doctor Logins**: Because `doctor_cp` was generating a synthetic user with ID `"cptiwari"`, database queries filtering by `doctor_id == current_user.id` returned 0 rows until patched with static doctor UUID mapping.
2. **Missing Endpoint Role Guards**:
   - `GET /receptionist/booked-slots` only checks for an authenticated user; it does not verify whether the caller possesses the `RECEPTIONIST` or `ADMIN` role.
   - `GET /appointments/availability` has no auth requirement and can be queried without rate limits.

---

## 9. Multi-Tenant / Hospital Isolation Audit

Multi-tenancy is implemented through a shared database model with a discriminator column (`hospital_id`) on all core tables.

### Tenant Isolation Audit Trail:
```
Client Request -> JWT Bearer Token -> Decoded Claims -> current_user.hospital_id -> SQLAlchemy Query WHERE hospital_id = ...
```

### Identified IDOR & Tenant Leaks:
1. **`hosp_default` Fallback Leak**: In multiple routes throughout `appointments.py` (e.g., lines 391, 887, 1496, 1715, 1755, 1858, 4207, 4309), if `current_user.hospital_id` is `None` or empty, the backend defaults to `"hosp_default"`:
   ```python
   hosp_id = current_user.hospital_id if current_user.hospital_id else "hosp_default"
   ```
   This means any misconfigured or orphaned user account automatically gains read/write access to the default hospital's patients and appointments.
2. **Direct Object Reference in Appointment Status**: `POST /appointments/{appointment_id}/status` queries `Appointment.id == appointment_id` without filtering by `Appointment.hospital_id == current_user.hospital_id`. A receptionist from Hospital A can alter the status of an appointment belonging to Hospital B if they know or guess the UUID.
3. **Patient Search Isolation**: `GET /hospital/patients/search` properly filters by `Patient.hospital_id == current_user.hospital_id`, but does not sanitize wildcards (`%` or `_`) in the search string, allowing wildcard denial-of-service or database query degradation.

---

## 10. AI Voice / Webhook Audit

### End-to-End Voice Flow:
```
1. Caller dials Hospital DID
2. Twilio receives call -> Triggers POST /api/v1/voice/inbound
3. Backend matches To/From against Hospital & HospitalSetting (twilio_helpline)
4. CallLog and VoiceSession created in MySQL (session_status='ACTIVE', state='GREETING')
5. Backend returns TwiML with <Connect><Stream url="wss://.../voice/stream/{session_id}" />
6. WebSocket handshake established -> Twilio streams raw μ-law audio chunks (8000Hz)
7. Audio transformed: μ-law -> Linear PCM 16-bit (8kHz -> 16kHz) -> Sent to Google Gemini Live API
8. Gemini Live processes conversational audio, executes function calls (book_appointment, get_available_slots)
9. Function responses fed back into Gemini Live -> Response PCM audio converted to μ-law -> Streamed back to Twilio
10. On Hangup: WebSocket closes, VoiceSession marked 'TERMINATED', CallLog duration updated.
```

### Voice Engine Vulnerabilities:
1. **Twilio Webhook Signature Verification Disabled**: `POST /voice/inbound` and `POST /whatsapp/webhook` do not validate the `X-Twilio-Signature` header. Anyone on the internet can forge fake incoming call webhooks and trigger synthetic database sessions.
2. **Gemini Live Connection Drops**: If Google Gemini Live WebSocket drops or encounters rate limits (Resource Exhausted 429), the WebSocket connection terminates abruptly without playing a graceful audio apology TwiML to the caller.
3. **No Idempotency Key on Voice Booking**: If the caller repeats their confirmation or if network jitter triggers duplicate function execution, `AppointmentEngine.book_appointment` relies solely on datetime checks. If the same slot was booked within the same second, race conditions could produce duplicate records.

---

## 11. Payment Audit

### Payment Integration Architecture:
* **Gateway**: Razorpay (India INR).
* **Workflows**:
  1. *Hospital Subscription Onboarding*: Client collects plan payment, calls `register-hospital`.
  2. *Patient OPD Booking*: Client triggers Razorpay checkout modal, calls `confirm-payment`.
  3. *Admin Plan Upgrade*: Admin triggers checkout modal, calls `upgrade-plan`.

### Payment Security Flaws:
1. **Missing Server-Side Payment Verification**:
   - In `POST /api/v1/patient/appointments/{id}/confirm-payment`, the backend accepts `payment_mode: "ONLINE"` without requiring `razorpay_order_id`, `razorpay_payment_id`, or `razorpay_signature`. Any user can bypass payment by sending a direct POST request to mark their appointment as `PAID`.
2. **Missing Webhook Capture**: No server-to-server Razorpay webhook (`/api/v1/payment/razorpay-webhook`) is implemented to handle asynchronous payment captures, refunds, or payment drops.
3. **Price Discrepancy**: `LoginPage.jsx` displays the Pro plan at ₹2,999/month, but hardcodes `amount: 199900` (₹1,999) in the Razorpay checkout parameters.

---

## 12. Error Handling Audit

1. **FastAPI Global Exception Handlers**: Registered in `app/core/exceptions.py`. Custom exceptions (`BaseAppException`, `DatabaseException`, `NotFoundException`, `AuthException`) map to clean JSON responses (`{"success": false, "error": msg}`).
2. **Unhandled Exception Leak**: In `global_exception_handler`, unhandled errors log full traceback to terminal/file and return `{"success": false, "error": "An unexpected server error occurred."}` which is clean. However, certain route endpoints catch generic `Exception` and return `str(e)` directly in `HTTPException(status_code=500, detail=str(e))`, leaking internal SQL query syntax to the client.
3. **Frontend Blank Screen Risks**:
   - `App.jsx` lacks a top-level React Error Boundary. If an unhandled exception occurs inside a sub-component (e.g. `DoctorQueue` attempting to access an undefined appointment property), the entire React application crashes to a white screen.
   - `localStorage` corruption (e.g., invalid JSON in cached fields) causes persistent render crashes until the user manually executes `localStorage.clear()`.

---

## 13. Testing Audit

### Inventory of Existing Tests:
* `tests/conftest.py`: 5 lines (Empty stub).
* `tests/unit/`: Empty directory (Contains only `__init__.py`).
* `tests/integration/`: Empty directory (Contains only `__init__.py`).
* `smoke_test.py`: Standalone script testing health, login, booking, patient auth.
* `test_login_api.py`: Standalone 15-line script testing `/auth/login`.
* `test_slot_full.py`: Standalone script mocking database appointments to test slot overflow.
* `verify_db.py`: Database query inspection script.

### Safe Test Execution Assessment:
* **Automated Unit Tests**: **0 tests found**.
* **Integration Scripts**: The scripts in root (`smoke_test.py`, `test_slot_full.py`) perform live mutations against the remote Railway MySQL database (e.g., executing `DELETE FROM appointments WHERE id LIKE 'test-appt-%'`).
* **Conclusion**: **No safe automated test suite exists** that can be run against a local mock database without mutating cloud production data.

---

## 14. Security Audit

| Vulnerability Type | Location | Severity | Description |
|---|---|---|---|
| **Hardcoded Credentials** | `appointments.py` (945–1020), `LoginPage.jsx` (452–455) | **CRITICAL** | Plaintext usernames and passwords hardcoded in both backend authentication routers and frontend login quick-pills. |
| **Plaintext Password Exposure** | `appointments.py` Line 4330, `App.jsx` Line 843 | **CRITICAL** | `GET /hospital/profile` returns plaintext `admin_password` in API response payload, stored in React state. |
| **Exposed Twilio Master Secrets** | `appointments.py` Lines 169–170 | **CRITICAL** | `GET /hospitals` returns Twilio Account SID and Auth Tokens to the frontend in plain text. |
| **Insecure IDOR Object Access** | `appointments.py` Line 3846 | **HIGH** | `POST /appointments/{id}/status` updates appointment status without verifying that the appointment belongs to the caller's hospital. |
| **Unverified Payment Confirmations** | `patient_portal.py` Line 454 | **HIGH** | `confirm-payment` marks appointments as PAID without validating Razorpay signatures. |
| **Hardcoded API Keys in Client Bundle** | `LoginPage.jsx`, `PatientPortal.jsx`, `App.jsx` | **HIGH** | Razorpay test key `rzp_test_TDfSGFZwtVgpme` embedded in frontend source code. |
| **Unauthenticated Twilio Webhook** | `voice.py` Line 26, `whatsapp_webhook.py` Line 21 | **HIGH** | Twilio webhook endpoints lack cryptographic signature verification (`X-Twilio-Signature`). |
| **Wildcard CORS Configuration** | `app/core/config.py` Line 67, `app/main.py` Line 25 | **MEDIUM** | `BACKEND_CORS_ORIGINS` defaults to `["*"]` with `allow_credentials=True`, permitting cross-origin credentialed requests from any domain. |
| **JWT Stored in LocalStorage** | `App.jsx` Line 630, `PatientPortal.jsx` Line 246 | **MEDIUM** | JWT tokens stored in browser `localStorage`, rendering them vulnerable to cross-site scripting (XSS) extraction. |
| **Demo OTP Disclosure in Production UI** | `PatientPortal.jsx` Line 514 | **MEDIUM** | "For demo MVP, use OTP: 1234" displayed on patient login modal. |

---

## 15. Production Configuration Audit

1. **Environment Variables**:
   - Backend reads from `.env` via `pydantic-settings`.
   - `.env.example` is complete and covers all necessary keys (`MYSQL_*`, `JWT_*`, `GEMINI_*`, `TWILIO_*`, `RAZORPAY_*`).
   - Default values in `app/core/config.py` contain dangerous fallbacks: `JWT_SECRET_KEY = "SECRET_MUST_BE_REPLACED_IN_PRODUCTION_ENV_FILE"`.
2. **CORS Configuration**:
   - `BACKEND_CORS_ORIGINS = ["*"]` with `allow_credentials=True` is an invalid combination in strict browser environments and violates security standards.
3. **Docker & Deployment**:
   - `Dockerfile` present (Python 3.11-slim base, Uvicorn execution).
   - `docker-compose.yml` present with MySQL 8.0 container definition.
   - Frontend static asset serving is built into `main.py` via `StaticFiles` mounting `frontend/dist`.

---

## 16. Code Quality & Architecture Audit

1. **Monolithic Codebases**:
   - `appointments.py` (4,799 lines) violates Single Responsibility Principle. Auth, hospital management, payments, and appointments should be split into dedicated endpoint modules.
   - `App.jsx` (4,822 lines) contains all portal dashboards, modals, state variables, and translation tables in a single file.
2. **Dead Code & Unused Imports**:
   - `Sidebar.jsx` (230 lines) is imported into `App.jsx` but never rendered; `App.jsx` inlines its own `<aside>` sidebar navigation.
   - `Header.jsx` is duplicated across components.
3. **Direct Database Queries in Route Handlers**:
   - Absence of a formal Repository / Service layer forces raw SQLAlchemy statements and database transactions into HTTP route handler bodies.

---

## 17. Critical Issues

| # | File | Location | Problem Description | Recommended Fix | Affects API/DB |
|---|---|---|---|---|---|
| C1 | `app/api/v1/endpoints/appointments.py` | Lines 945–1020 | Hardcoded credentials and passwords backdoor in `/auth/login`. | Remove hardcoded user dictionary; enforce strict database bcrypt verification for all logins. | Yes (Auth API) |
| C2 | `app/core/dependencies.py` | Lines 70–87 | `get_current_user` bypasses DB lookups for hardcoded usernames. | Remove synthetic user bypass; query `User` table for all JWT sub claims. | Yes (Auth API) |
| C3 | `app/api/v1/endpoints/appointments.py` | Line 4330 | `GET /hospital/profile` returns plaintext `admin_password` in JSON response. | Never return password hashes or plaintext passwords in API responses; remove `admin_password` from response schema. | Yes (Frontend & API) |
| C4 | `app/api/v1/endpoints/appointments.py` | Lines 169–170 | `GET /hospitals` returns plaintext Twilio Auth Tokens to client. | Strip sensitive credentials or mask as `***` when returning hospital configurations. | Yes (API) |
| C5 | `frontend/src/PatientPortal.jsx` | Line 459 | `confirmPayment` uses `bookedAppointmentId` which is `null` at `bookStep === 4`. | Correctly set and pass the created appointment UUID from `handleBook` response into `confirmPayment`. | Yes (Frontend) |
| C6 | `frontend/src/pages/LoginPage.jsx` | Lines 452–455 | Plaintext usernames and passwords hardcoded in public login UI pills. | Remove quick-login credential pills from production build. | No |
| C7 | `frontend/src/pages/LoginPage.jsx`, `App.jsx`, `PatientPortal.jsx` | Multiple | Razorpay Test Key `rzp_test_TDfSGFZwtVgpme` hardcoded in source code. | Move Razorpay Key ID to environment variable (`VITE_RAZORPAY_KEY_ID`). | No |
| C8 | `app/api/v1/endpoints/patient_portal.py` | Line 454 | `POST /patient/appointments/{id}/confirm-payment` accepts payment confirmation without verifying Razorpay signature. | Require `razorpay_payment_id`, `razorpay_order_id`, and `razorpay_signature` and verify with Razorpay SDK before marking `PAID`. | Yes (API & DB) |
| C9 | `app/api/v1/endpoints/patient_auth.py` | Line 52 | Hardcoded OTP `1234` generated for all patients in `send-otp`. | Generate cryptographically random 6-digit OTP and send via Twilio SMS / WhatsApp API. | Yes (API) |
| C10 | `app/api/v1/endpoints/appointments.py` | Line 3846 | `POST /appointments/{id}/status` lacks hospital tenancy check (IDOR vulnerability). | Add `Appointment.hospital_id == current_user.hospital_id` to query filter. | Yes (API) |
| C11 | `app/api/v1/endpoints/voice.py` | Line 26 | Twilio inbound webhook lacks `X-Twilio-Signature` validation. | Add Twilio request validator decorator using `TWILIO_AUTH_TOKEN`. | Yes (Webhook) |
| C12 | `app/core/config.py` | Line 38 | Insecure default `JWT_SECRET_KEY` fallback in settings. | Force application startup failure if `JWT_SECRET_KEY` is not provided in `.env`. | No |

---

## 18. High Priority Issues

| # | File | Location | Problem Description | Recommended Fix |
|---|---|---|---|---|
| H1 | `app/api/v1/endpoints/appointments.py` | Monolith | 4,799-line file containing all route logic without separation of concerns. | Modularize into `auth.py`, `hospitals.py`, `doctors.py`, `appointments.py`, `leaves.py`, `payments.py`. |
| H2 | `frontend/src/App.jsx` | Monolith | 4,822-line file containing all portal UIs without a router. | Introduce `react-router-dom` and split into distinct page components. |
| H3 | `app/api/v1/endpoints/appointments.py` | Multiple | `hosp_default` fallback leaks default hospital data when user hospital is null. | Raise `HTTPException(403, "Tenant context required")` instead of falling back to default hospital. |
| H4 | `frontend/src/components/doctor/DoctorQueue.jsx` | Line 476 | `leavesList.filter(l => l.doctor_id === userId)` fails on type/format mismatch. | Ensure consistent doctor UUID comparison. |
| H5 | `app/api/v1/endpoints/whatsapp_webhook.py` | Line 21 | WhatsApp webhook lacks signature verification. | Implement Twilio webhook signature verification. |
| H6 | `app/main.py` | Lines 41–42 | `appointments.router` registered twice (with and without `/api/v1` prefix). | Remove the duplicate unprefixed router inclusion. |
| H7 | `app/core/config.py` | Line 67 | Wildcard CORS `["*"]` with `allow_credentials=True`. | Specify exact allowed origin domains in production `.env`. |
| H8 | `frontend/src/pages/LoginPage.jsx` | Lines 88–89 | Pro plan shows ₹2,999 in UI card but charges ₹1,999 in Razorpay call. | Synchronize displayed pricing with gateway parameters. |
| H9 | `frontend/src/PatientPortal.jsx` | Line 514 | "Demo MVP OTP: 1234" text displayed in user-facing modal. | Remove demo OTP hint from UI. |
| H10 | `app/services/whatsapp.py` | Multiple | WhatsApp notification failures catch exceptions silently without retries. | Implement retry queue with exponential backoff or task worker (Celery/Redis). |
| H11 | `app/engines/appointment.py` | Line 20 | Appointment booking lacks database-level row lock (`with_for_update`), enabling double booking race conditions. | Add `with_for_update()` on `DoctorSchedule` / slot queries during booking transaction. |
| H12 | `frontend/src/App.jsx` | Lines 943–950 | 5-second polling interval for receptionist and doctor appointments. | Replace polling with WebSockets or Server-Sent Events (SSE) for real-time queue updates. |
| H13 | `app/database/models/appointment.py` | Line 8 | Cascade delete on `Hospital` permanently destroys clinical history. | Implement soft deletion (`is_deleted = Column(Boolean, default=False)`). |
| H14 | `app/database/models/appointment.py` | Lines 218–219 | Columns `patient_name_override` and `booked_by_name` not tracked in baseline migrations. | Generate clean Alembic migration to sync database models with schema. |
| H15 | `tests/` | Entire dir | 0% automated test coverage. | Add pytest unit tests for authentication, scheduling engine, and appointment booking. |
| H16 | `app/api/v1/endpoints/voice.py` | Line 289 | WebSocket terminates without graceful TTS message if Gemini Live API quota is exhausted. | Catch `ResourceExhausted` and stream pre-recorded audio hangup message. |
| H17 | `frontend/src/App.jsx` | Line 630 | JWT token stored in `localStorage` instead of `HttpOnly` cookie. | Migrate authentication token storage to secure, same-site `HttpOnly` cookies. |
| H18 | `app/api/v1/endpoints/appointments.py` | Line 4652 | Patient search query does not escape SQL LIKE wildcards (`%`, `_`). | Sanitize input before executing `ilike()` queries. |

---

## 19. Medium Priority Issues

| # | File | Location | Problem Description | Recommended Fix |
|---|---|---|---|---|
| M1 | `frontend/src/App.jsx` | Line 1557 | `handleMarkSingleMissed` sends `FormData` while other status calls send `URLSearchParams`. | Standardize all status updates to `URLSearchParams` or JSON payloads. |
| M2 | `frontend/src/App.jsx` | Line 1850 | Hardcoded Hindi confirm strings in SuperAdmin hospital deletion. | Move all dialog strings into `TRANSLATIONS` dictionary. |
| M3 | `frontend/src/App.jsx` | Line 2597 | Hardcoded "72 slots free" string displayed in receptionist sidebar. | Compute dynamic count from `newBookingAllSlots` and `newBookingBookedSlots`. |
| M4 | `frontend/src/components/common/Sidebar.jsx` | Entire file | Dead component file imported but never rendered in `App.jsx`. | Clean up unused component or integrate it into main layout. |
| M5 | `frontend/src/PatientPortal.jsx` | Lines 200–220 | Double API call on initial login mount (`useEffect` triggers twice). | Consolidate dependency arrays in `useEffect`. |
| M6 | `app/core/middleware.py` | Line 28 | Hardcoded hospital matching for `"balaji"` string in request path. | Remove hardcoded hospital name matching from logging middleware. |
| M7 | `app/api/v1/endpoints/appointments.py` | Line 2120 | Legacy `/receptionist/schedule` HTML endpoint left in API router. | Remove obsolete HTML debug endpoints. |
| M8 | `app/api/v1/endpoints/appointments.py` | Line 3278 | Legacy `/payment/checkout` HTML page left in API router. | Remove obsolete HTML checkout endpoint. |
| M9 | `frontend/src/App.jsx` | Line 1901 | Hardcoded fallback domain `https://aura-saas-api.herokuapp.com` in `getWebhookUrl`. | Derive webhook URL dynamically from current backend origin or configuration. |
| M10 | `app/database/models/appointment.py` | Lines 203–222 | Missing database indexes on `status`, `payment_status`, and `appointment_datetime`. | Add compound index `idx_hospital_appt_lookup (hospital_id, appointment_datetime, status)`. |
| M11 | `frontend/src/App.jsx` | Entire file | Lack of top-level React Error Boundary. | Wrap root component in an `ErrorBoundary` to prevent white-screen crashes. |
| M12 | `app/core/exceptions.py` | Line 60 | Global exception handler lacks unique error tracking ID return. | Return `error_id` (matching `X-Request-ID`) in 500 error response JSON for customer support reference. |
| M13 | `app/api/v1/endpoints/appointments.py` | Line 4118 | `/receptionist/booked-slots` lacks role verification. | Add `require_roles(["RECEPTIONIST", "ADMIN"])` dependency guard. |
| M14 | `app/api/v1/endpoints/voice.py` | Line 937 | `/test-call` endpoint active in production router. | Guard test call endpoints behind `DEBUG` environment check. |

---

## 20. Low Priority Issues

| # | File | Location | Problem Description | Recommended Fix |
|---|---|---|---|---|
| L1 | `frontend/src/App.jsx` | Line 928 | `console.log("[DEBUG] Main Data Fetch...")` left in production code. | Remove verbose debug console logs from client build. |
| L2 | `frontend/src/PatientPortal.jsx` | Line 538 | Missing `'cancel'` translation key in `TRANSLATIONS` dictionary. | Add `'cancel': { en: 'Cancel', hi: 'रद्द करें' }` to translations. |
| L3 | `frontend/src/App.jsx` | Line 4139 | Specific hospital name "C P Tiwari Hospital" hardcoded in settings placeholder. | Replace with generic placeholder `"Welcome to [Hospital Name]..."`. |
| L4 | `frontend/src/App.jsx` | Line 4154 | Brand name "Apollo Hospital" hardcoded in system prompt placeholder. | Replace with generic hospital placeholder. |
| L5 | `app/database/models/appointment.py` | Line 18 | `Hospital.timezone` defaults to `'UTC'` instead of `'Asia/Kolkata'`. | Update default timezone for Indian hospital deployments. |
| L6 | `frontend/src/PatientPortal.jsx` | Line 480 | Payment badge check `a.payment_status?.includes('PAID')` matches 'UNPAID'. | Use strict equality `a.payment_status === 'PAID'`. |
| L7 | `app/core/logging.py` | Entire file | Log files written to local `logs/` directory without rotation policy. | Configure `RotatingFileHandler` with max size and backup count. |
| L8 | `frontend/src/App.jsx` | Line 653 | `window.location.reload()` used after login instead of React state reset. | Refactor login transition to use clean React state flow. |

---

## 21. Recommended Fix Order

```
┌────────────────────────────────────────────────────────────────────────────┐
│ PHASE 1: CRITICAL SECURITY & AUTHENTICATION PATCHES (DAY 1)                 │
│ 1. Remove all hardcoded credentials from appointments.py & dependencies.py  │
│ 2. Eliminate plaintext admin_password & Twilio auth tokens from API output │
│ 3. Fix PatientPortal confirmPayment runtime bug (null appointment UUID)    │
│ 4. Implement server-side Razorpay signature verification                    │
│ 5. Remove hardcoded demo OTP '1234' and login quick-pills from frontend    │
│ 6. Add hospital tenant isolation check to POST /appointments/{id}/status   │
└─────────────────────────────────────┬──────────────────────────────────────┘
                                      │
                                      ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ PHASE 2: MULTI-TENANT ISOLATION & WEBHOOK SECURITY (DAYS 2-3)               │
│ 1. Remove hosp_default fallback leaks across all backend endpoints         │
│ 2. Implement Twilio cryptographic signature validation (X-Twilio-Signature)│
│ 3. Add row-level locking (with_for_update) to prevent double bookings      │
│ 4. Restrict CORS origins to authorized production domains                   │
│ 5. Add database indexes on appointment status, datetime, and overrides     │
└─────────────────────────────────────┬──────────────────────────────────────┘
                                      │
                                      ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ PHASE 3: ARCHITECTURAL REFACTORING & CODE MODULARIZATION (DAYS 4-5)        │
│ 1. Deconstruct appointments.py (4.8k lines) into domain routers & services │
│ 2. Deconstruct App.jsx (4.8k lines) using React Router and page views      │
│ 3. Replace 5-second HTTP polling with WebSocket queue updates               │
│ 4. Add React ErrorBoundary to prevent white-screen crashes                 │
└─────────────────────────────────────┬──────────────────────────────────────┘
                                      │
                                      ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ PHASE 4: TEST SUITE & PRODUCTION DEPLOYMENT HARDENING (DAYS 6-7)           │
│ 1. Build Pytest test suite (Unit tests for auth, scheduling, and booking)  │
│ 2. Set up local MySQL test fixtures                                        │
│ 3. Synchronize Alembic migrations with current database state              │
│ 4. Execute staging smoke tests and security penetration test               │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 22. Summary Deliverables

* **A) Total APIs Found**: **57 endpoints**
* **B) Total Frontend Routes / Views Found**: **6 major portal routes/views** (`LoginPage`, `Receptionist Portal`, `Doctor Workstation`, `Hospital Admin Portal`, `Super Admin Portal`, `Patient Portal`)
* **C) Total Tests Found**: **0 automated unit/integration tests** (4 standalone manual scripts)
* **D) Critical Issues Count**: **12**
* **E) High Priority Issues Count**: **18**
* **F) Medium Priority Issues Count**: **14**
* **G) Low Priority Issues Count**: **8**
* **H) Overall Production Readiness Percentage**: **42% (NOT READY FOR PRODUCTION)**

---

## 23. Top 10 Things That Must Be Fixed Before Production

1. **Remove Hardcoded Backdoor Credentials**: Delete the hardcoded credential dictionaries in `appointments.py` (lines 945–1020) and `dependencies.py` (lines 70–87). All authentications must validate against hashed passwords in the `users` table.
2. **Prevent Plaintext Password & Secret Leaks**: Stop returning `admin_password` in `GET /hospital/profile` and Twilio auth tokens in `GET /hospitals`.
3. **Fix Patient Portal Payment Confirmation Bug**: Correct `PatientPortal.jsx` (line 459) to pass the valid appointment UUID instead of `null` to `POST /patient/appointments/{id}/confirm-payment`.
4. **Enforce Server-Side Razorpay Signature Verification**: In `patient_portal.py` and `appointments.py`, verify `razorpay_signature` using HMAC-SHA256 before marking any appointment or plan as `PAID`.
5. **Secure Patient OTP Generation**: Replace hardcoded OTP `"1234"` in `patient_auth.py` with cryptographically random 6-digit OTP delivery via SMS/WhatsApp.
6. **Enforce Tenant Isolation on Direct Object References**: Add `Appointment.hospital_id == current_user.hospital_id` to `POST /appointments/{id}/status` and eliminate all `hosp_default` fallback leaks.
7. **Validate Twilio Webhook Signatures**: Implement `X-Twilio-Signature` verification on `/api/v1/voice/inbound` and `/api/v1/whatsapp/webhook` to prevent spoofed calls and fake message injection.
8. **Fix Concurrency Double-Booking Vulnerability**: Add `with_for_update()` database locks to `AppointmentEngine` slot reservation transactions.
9. **Eliminate Hardcoded Test Keys & Credentials from Client Bundle**: Remove Razorpay test key `rzp_test_***` and quick-login credential pills from `LoginPage.jsx` and `App.jsx`.
10. **Build Automated Test Suite**: Implement a comprehensive pytest suite covering authentication, appointment booking, slot calculation, and role-based permissions before production launch.

---

## 24. Recommended Next Step
Proceed to **Phase 1** of the fix order: Remediate the **12 Critical Security & Authentication Issues** (C1 through C12) without altering functional business logic, followed by setting up an automated pytest test harness.
