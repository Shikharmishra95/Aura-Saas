# 🏥 AURA — Enterprise AI Healthcare Operating System & Voice Receptionist

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111.0-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB.svg?logo=react)](https://reactjs.org/)
[![Sentry](https://img.shields.io/badge/Sentry-Monitored-362D59.svg?logo=sentry)](https://sentry.io/)
[![Tests](https://img.shields.io/badge/tests-138%20passing-brightgreen.svg)](https://pytest.org)
[![License](https://img.shields.io/badge/license-Proprietary-red.svg)]()

> **AURA** is an enterprise-grade, multi-tenant healthcare SaaS platform powering autonomous AI voice receptionists, real-time clinical copilot engines, live OPD queue management, and patient self-service portals across hospital networks.

---

## 🏗️ System Architecture

```text
                                  ┌────────────────────────────────┐
                                  │   Caller (Telephone / Web)     │
                                  └───────────────┬────────────────┘
                                                  │ Twilio Voice (TwiML/Audio)
                                                  ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                FASTAPI APPLICATION CORE                                │
│                                                                                        │
│  ┌───────────────────────┐   ┌───────────────────────┐   ┌──────────────────────────┐  │
│  │   Voice State Machine │   │  5-Way Intent Router  │   │  Multi-Tenant RBAC Auth  │  │
│  │   (Twilio Call SIDs)  │   │  (ReAct Groq / LLaMA) │   │  (5 Roles / Row Scoped)  │  │
│  └───────────┬───────────┘   └───────────┬───────────┘   └────────────┬─────────────┘  │
│              │                           │                            │                │
│              ▼                           ▼                            ▼                │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│  │                              APPLICATION ENGINES LAYER                           │  │
│  │   • Scheduling Engine (Slot Generation & Leave / Holiday Calculation)           │  │
│  │   • RAG Knowledge Engine (BM25 + Cosine Semantic Knowledge Base)                │  │
│  │   • Tool Registry (Dynamic Zero-Trust Pruning per User Role)                     │  │
│  │   • Subscription Lifecycle (Plan Expiry Enforcement & Payment Routing)           │  │
│  └───────────────────────────────────────┬──────────────────────────────────────────┘  │
│                                          │                                             │
│                                          ▼                                             │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│  │                         RELIABILITY & OBSERVABILITY LAYER                        │  │
│  │   • Sentry Real-Time Error Tracking & Tracing (Backend & Frontend)               │  │
│  │   • Connection Pool Optimization (Oracle Always Free Compatible)                 │  │
│  │   • In-Memory OTP Rate Limiting (3 req / 10 min) & Webhook Call Deduplication   │  │
│  └──────────────────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────┬─────────────────────────────────────────────┘
                                           │
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        DATA PERSISTENCE & EXTERNAL GATEWAYS                            │
│  • MySQL 8.0 (Async SQLAlchemy 2.0 + Alembic Migrations + Composite Performance Indexes)│
│  • Twilio Voice & WhatsApp Notifications Gateway                                       │
│  • Razorpay Payment Gateway Integration                                                │
│  • Groq & Google Gemini LLM Inference API                                              │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🌟 Core Pillars & Capabilities

### 1. 📞 Autonomous Voice AI Receptionist
* Real-time conversational telephone booking via Twilio Webhooks and audio processing.
* Context-aware state machine guiding patients through doctor selection, department routing, and slot reservation.
* Built-in call deduplication preventing duplicate bookings on network retries.

### 2. 🧠 Role-Scoped AI Copilot Engine
* Powered by a **5-Way Intent Router** (Knowledge, Live Data, Action, Mixed, Unknown) with deterministic tool execution and ReAct LLM fallback.
* Role-based tool pruning: Doctors access clinical queues; Receptionists access booking tools; Admins access revenue KPIs.
* Adaptive fallback routing to SaaS consultation mode if a hospital tenant's subscription expires.

### 3. 👥 Live OPD Queue & Clinical Dashboard
* Real-time waiting room status (`WAITING`, `IN_CONSULTATION`, `COMPLETED`, `MISSED`).
* One-click consultation notes, e-prescriptions, and cash register audits.
* Automated hourly sweeper marking expired appointments as MISSED with WhatsApp notification alerts.

### 4. 📱 Patient Self-Service Portal
* Secure mobile OTP authentication with anti-spam rate limiting.
* Self-booking flow, live token status, and 1-time reschedule limits.
* Prescription downloads and family member record management.

### 5. 🏢 SuperAdmin Multi-Tenant Fleet Control Tower
* Centralized fleet dashboard tracking tenant health, active doctor quotas, and subscription expirations.
* Tiered billing models: **Starter (₹1,500/mo)**, **Pro (₹2,999/mo)**, and **Enterprise (₹29,999/yr)**.
* Automated online portal locking and feature suspension for lapsed subscriptions.

---

## 🧪 Testing & Quality Assurance

AURA incorporates **138 automated unit, integration, and security test suites**:

```bash
# Run complete test suite
pytest tests/ -v
```

* **Scheduling & Slot Generation:** Validates holiday blocks, doctor leaves, past-date protection, and 30-min interval calculations.
* **Authentication & RBAC:** Verifies password hashing (bcrypt), JWT validity, and cross-tenant data isolation.
* **Copilot & AI Routing:** Validates intent classification, tool pruning, and RAG context construction.
* **Concurrency & Safety:** Tests race condition prevention in appointment slot locking.

---

## 📁 Clean Repository Layout

```text
├── app/
│   ├── api/v1/endpoints/   # 13 Modular REST route groups
│   ├── core/               # Security, JWT, Logging, and Sentry configuration
│   ├── database/models/    # SQLAlchemy models (Appointment, Patient, Doctor, etc.)
│   ├── engines/            # AI Copilot, Intent Router, RAG, Scheduling engines
│   ├── schemas/            # Pydantic validation schemas
│   └── services/           # Twilio, WhatsApp, Gemini, and Automation services
├── frontend/
│   ├── src/components/     # Modular React components (DoctorQueue, CopilotWidget, etc.)
│   ├── src/pages/          # Dedicated page views (LoginPage, AdminDashboard, etc.)
│   └── src/PatientPortal.jsx # Full-featured self-service patient portal
├── migrations/versions/    # Alembic schema versioning & composite DB indexes
├── tests/                  # 138 Automated test suites (Unit & Integration)
├── docs/                   # Architecture specs, HLDs, and Audit documentation
├── Dockerfile              # Production-optimized container build
└── requirements.txt        # Production dependencies
```

---

## 🚀 Quickstart & Deployment

### 1. Local Setup
```bash
# 1. Clone & activate virtual environment
python -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt
cd frontend && npm install && npm run build && cd ..

# 3. Setup environment variables
cp .env.example .env

# 4. Run database migrations
alembic upgrade head

# 5. Launch FastAPI server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Docker Deployment
```bash
docker build -t aura-saas .
docker run -p 8000:8000 --env-file .env aura-saas
```

---

## 🛡️ Security & Observability

* **Real-time Error Tracking:** Integrated with **Sentry** across backend and frontend with PII masking.
* **Anti-Abuse Rate Limiting:** Enforces strict request quotas on public OTP and auth endpoints.
* **Tenant Isolation:** Every database entity is foreign-key scoped to `hospital_id` with zero cross-tenant query leakage.
* **Audit Logs:** Full traceability of sensitive actions recorded in `call_logs` and audit events.
