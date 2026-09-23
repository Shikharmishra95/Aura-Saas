# AURA SaaS — High-Level Design (HLD) Document
**Version:** 1.0 | **Date:** 2026-09-17 | **Author:** Antigravity AI

---

## 1. What is AURA?

AURA (AI Unified Receptionist & Analytics) is a **multi-tenant B2B SaaS platform** for Indian hospitals and clinics. It provides:

- **AI Voice Receptionist** — Twilio-powered phone agent books appointments by voice
- **AI Copilot Chatbot** — Context-aware assistant for staff (Admin, Doctor, Receptionist)
- **OPD Management** — Live queues, doctor dashboards, appointment workflows
- **Patient Portal** — Self-service booking by patients (web)
- **Admin Dashboard** — Revenue, analytics, roster management
- **Subscription Engine** — SaaS billing with plan enforcement

---

## 2. System Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                         AURA SaaS Platform                                    │
│                                                                                │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐ │
│  │  Hospital    │   │  Hospital    │   │  Hospital    │   │  SuperAdmin  │ │
│  │  Staff UI    │   │  Doctor UI   │   │  Patient     │   │  Control     │ │
│  │  (React SPA) │   │  (React SPA) │   │  Portal      │   │  Tower       │ │
│  └──────┬───────┘   └──────┬───────┘   └──────┬───────┘   └──────┬───────┘ │
│         │                  │                  │                  │           │
│         └──────────────────┴──────────────────┴──────────────────┘           │
│                                      │                                        │
│                             HTTPS / REST API                                  │
│                                      │                                        │
│  ┌───────────────────────────────────▼────────────────────────────────────┐  │
│  │                    FastAPI Backend (Python 3.12)                        │  │
│  │                                                                         │  │
│  │  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────────┐  │  │
│  │  │  Auth   │ │Hospitals │ │  Staff   │ │Appoint-  │ │  Copilot   │  │  │
│  │  │ /login  │ │  /admin  │ │ /doctors │ │  ments   │ │  /chat     │  │  │
│  │  └─────────┘ └──────────┘ └──────────┘ └──────────┘ └─────────────┘  │  │
│  │  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────────┐  │  │
│  │  │Patients │ │  Voice   │ │ Patient  │ │  Subs-   │ │  Payments  │  │  │
│  │  │ /search │ │ /webhook │ │  Portal  │ │criptions │ │ /razorpay  │  │  │
│  │  └─────────┘ └──────────┘ └──────────┘ └──────────┘ └─────────────┘  │  │
│  │                                                                         │  │
│  │  ┌────────────── AI Engine Layer ────────────────────────────────────┐ │  │
│  │  │  Intent Router → RAG Engine → Tool Registry → Copilot Engine     │ │  │
│  │  │  Voice State Machine → Groq Client → Gemini Client               │ │  │
│  │  └───────────────────────────────────────────────────────────────────┘ │  │
│  └──────────────────────────────┬──────────────────────────────────────────┘  │
│                                 │                                              │
│         ┌───────────────────────┼──────────────────────────┐                  │
│         │                       │                          │                  │
│  ┌──────▼──────┐  ┌─────────────▼──────┐  ┌──────────────▼──────┐           │
│  │   MySQL DB  │  │   Groq API         │  │   External Services  │           │
│  │  (Railway)  │  │  (LLM inference)   │  │  Twilio Voice/SMS    │           │
│  │             │  │  + Gemini Fallback  │  │  Razorpay Payments   │           │
│  │  15-35 conn │  │  qwen3.8-27b       │  │  WhatsApp (Twilio)   │           │
│  └─────────────┘  └────────────────────┘  │  n8n Automation      │           │
│                                            └─────────────────────┘           │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Technology Stack

| Layer | Technology | Version | Purpose |
|---|---|---|---|
| **Backend** | FastAPI (Python) | 0.111+ | REST API, WebSocket, async |
| **ORM** | SQLAlchemy | 2.0+ | Async DB queries |
| **Database** | MySQL | 8.x | Primary data store |
| **DB Host** | Railway | — | Cloud-managed MySQL |
| **Migrations** | Alembic | 1.13+ | Schema versioning |
| **Frontend** | React (Vite) | — | SPA dashboard + portals |
| **Frontend Deploy** | FastAPI StaticFiles | — | Served from `/assets` |
| **Primary LLM** | Groq → qwen3.8-27b | — | Copilot & tool calling |
| **Fallback LLM** | Google Gemini | 1.5-flash | LLM fallback |
| **RAG** | BM25 + Cosine (in-memory) | Custom | Knowledge retrieval |
| **Voice** | Twilio Voice API | — | Phone-based AI agent |
| **Payments** | Razorpay | 1.4+ | Subscription & appointment fees |
| **WhatsApp** | Twilio WhatsApp API | — | Patient notifications |
| **Auth** | JWT (PyJWT) | 2.8+ | Stateless authentication |
| **Automation** | n8n | — | Workflow automation |
| **Container** | Docker | — | Deployment packaging |
| **Server** | Uvicorn | 0.30+ | ASGI server |

---

## 4. Multi-Tenancy Model

AURA uses **Row-Level Isolation** — every hospital is a separate tenant but shares the same DB.

```
hospitals table
    id: "HOSP-BALA-8617"  ← Tenant ID (hospital_id)
    slug: "balaji"
    plan_status: "EXPIRED" | "ACTIVE"

Every other table has:
    hospital_id: FK → hospitals.id   ← ALL queries filtered by this
```

**Isolation enforced at every level:**
1. **JWT Token** — contains `hospital_id`, issued on login
2. **API Endpoint** — all DB queries add `WHERE hospital_id = ?`
3. **Tool Registry** — tools are filtered by role + hospital context
4. **RAG Engine** — knowledge chunks tagged with `hospital_id` or `global`
5. **Copilot Engine** — `actor_profile` carries `hospital_id` through full pipeline

**Multi-tenant threat model:** If a bug causes hospital A to read hospital B's data, it's a P0 incident. Current isolation is solid (every query scoped) but has no automated cross-tenant isolation test.

---

## 5. Component Deep-Dive

### 5.1 API Layer — 13 Route Groups

```
/api/v1/
├── /login, /refresh           → auth.py — JWT issuance
├── /hospitals/*               → hospitals.py — CRUD, settings
├── /subscriptions/*           → subscriptions.py — plans, billing
├── /staff/*                   → staff.py — doctor/receptionist CRUD
├── /leaves/*                  → leaves.py — doctor leave management
├── /payments/*                → payments.py — Razorpay webhooks
├── /patients/*                → patients.py — patient records
├── /doctor-queue/*            → doctor_queue.py — live OPD queue
├── /appointments/*            → appointments.py — booking engine (74KB!)
├── /voice/*                   → voice.py — Twilio Voice webhooks (59KB)
├── /patient/send-otp          → patient_auth.py — OTP flow
├── /patient/*                 → patient_portal.py — self-service portal
├── /owner/*                   → owner/ — SuperAdmin control tower
└── /copilot/chat              → copilot.py — AI chatbot endpoint
```

### 5.2 AI Copilot Engine Pipeline

Every message from a staff member goes through this exact pipeline:

```
User Message
    │
    ▼
[1] CopilotEngine.chat()
        ├── Load actor_profile (role, hospital_id, permissions, is_expired)
        ├── Build system_prompt (role-specific, hospital-specific)
        └── Load conversation_memory (last N turns)
    │
    ▼
[2] IntentRouter.route_query()
    ├── Regex match → ACTION | LIVE_DATA | KNOWLEDGE | MIXED | UNKNOWN
    ├── RAG search → fetch top-2 knowledge chunks
    ├── ToolRegistry.prune_tools_for_user() → top-6 relevant tools
    └── Returns: RouteType + knowledge_results + pruned_tools
    │
    ▼
[3] Route Execution Branch
    ├── KNOWLEDGE → Return RAG answer via Gemini/Groq (no tools)
    ├── LIVE_DATA → Send tools to LLM → Execute tool calls → Format response
    ├── ACTION    → Confirm → Execute mutation tool → Commit to DB
    ├── MIXED     → RAG context + Tool call combined
    └── UNKNOWN   → Re-route to LIVE_DATA (LLM fallback) ← added Sep 2026
    │
    ▼
[4] LLM Execution (Groq Client or Gemini)
    ├── Tool call detected → Execute Python function → Append result
    ├── Multi-turn tool loop (max 3 iterations)
    └── Format final response
    │
    ▼
[5] Response Builder
    ├── Build contextual suggestion pills
    ├── Append to conversation memory
    └── Return { reply, suggestions, route_type }
```

### 5.3 RAG Engine (In-Memory BM25 + Cosine)

```
At Server Startup:
  load_knowledge_catalog()
      ├── Hospital policies (visiting hours, refund policy, OPD timings)
      ├── AURA SaaS plans (Starter ₹1,500 / Pro ₹2,999 / Enterprise ₹29,999)
      ├── Insurance & TPA panels
      ├── SOP guidelines
      └── Per-hospital custom knowledge (if configured)

  build_index():
      ├── BM25 index (sparse, keyword-based)
      └── TF-IDF cosine vectors (dense-ish, semantic)

At Query Time:
  search(query, hospital_id, role, top_k=2, min_score=0.20):
      ├── BM25 score (keywords match)
      ├── Cosine similarity score (vector match)
      ├── Combined weighted score
      └── Return top-k chunks above min_score
```

**Current knowledge size:** ~200 chunks, ~50KB  
**Startup time:** ~1-2 seconds  
**Query latency:** ~2-5ms (all in-memory)

### 5.4 Voice AI State Machine

```
Phone Call → Twilio → POST /api/v1/voice/incoming
    │
    ▼
VoiceStateMachine
    ├── State: GREETING → play welcome, collect patient phone
    ├── State: COLLECT_NAME → ask for name
    ├── State: SELECT_DOCTOR → list available doctors
    ├── State: SELECT_DATE → offer tomorrow/day-after
    ├── State: CONFIRM → repeat booking summary
    └── State: BOOK → call appointment_tools.book_appointment()

WebSocket Stream:
    Twilio Media Stream → /api/v1/voice/stream (WebSocket)
    ├── Audio bytes → Twilio Speech-to-Text
    ├── Text → Groq/Gemini for understanding
    └── Response → Twilio TTS → Audio to caller
```

### 5.5 Tool Registry Architecture

```
tool_registry.py (~71KB)
    ├── RECEPTIONIST_TOOLS:
    │   book_appointment, search_patient, check_doctor_availability,
    │   get_live_queue, get_daily_revenue, check_doctor_leaves
    ├── ADMIN_TOOLS:
    │   + get_revenue_analytics, manage_staff, export_reports
    ├── DOCTOR_TOOLS:
    │   get_my_queue, record_consultation, apply_leave, view_my_earnings
    ├── SUPER_ADMIN_TOOLS:
    │   all_hospitals_overview, platform_revenue, subscription_management
    └── PATIENT_TOOLS:
        view_my_appointments, book_appointment (limited)

prune_tools_for_user(query, user_role, permissions, top_k=6):
    ├── Filter by role permissions
    ├── Score by keyword relevance to query
    └── Return top-6 most relevant tools for this specific query
```

---

## 6. Database Schema Overview

### Core Tables

```sql
hospitals           ← Tenant master table
    id, name, slug, phone, address
    plan_status, plan_expires_at, plan_type
    subscription_plan_id, whatsapp_number
    created_at, updated_at

users               ← Staff accounts (Admin, Doctor, Receptionist)
    id, hospital_id, username, hashed_password
    role, full_name, specialization
    is_active, created_at

patients            ← Patient records (per hospital)
    id, hospital_id, first_name, last_name
    phone, date_of_birth
    otp, otp_expires_at   ← Used for portal login
    created_at

appointments        ← Core booking table
    id, hospital_id, doctor_id, patient_id
    appointment_date, slot_time
    status (BOOKED | COMPLETED | CANCELLED | MISSED)
    reason, notes, fee_charged, payment_status
    booked_by_name, patient_name_override
    source (VOICE | COPILOT | PORTAL | WALKIN)
    created_at

doctors             ← (within users table with role=DOCTOR)
    specialization, opd_days, opd_start_time, opd_end_time
    slot_duration_minutes, max_patients_per_slot
    consultation_fee

leaves              ← Doctor leave records
    id, doctor_id, hospital_id
    leave_date, reason, status (PENDING|APPROVED|REJECTED)
    approved_by, created_at

subscription_plan_config  ← SaaS pricing master
    id, plan_name (STARTER|PRO|ENTERPRISE)
    monthly_price, max_doctors, max_appointments_per_month
    features_json

call_logs           ← Voice AI call records
    id, hospital_id, caller_phone
    duration_seconds, appointment_booked (bool)
    transcript_summary, created_at

conversations       ← Copilot chat history
    id, hospital_id, user_id, session_id
    messages_json, created_at
```

### Data Relationships

```
hospitals
    ├── 1:N → users (staff)
    ├── 1:N → patients
    ├── 1:N → appointments
    ├── 1:N → leaves
    ├── 1:N → call_logs
    ├── 1:N → conversations
    └── N:1 → subscription_plan_config

appointments
    ├── N:1 → hospitals
    ├── N:1 → patients
    └── N:1 → users (doctor)
```

---

## 7. Authentication & Authorization Flow

```
[Login Request]
POST /api/v1/login
    username + password
          │
          ▼
    Verify bcrypt hash
          │
          ▼
    Issue JWT:
    {
      "sub": "username",
      "user_id": "usr_xxx",
      "role": "ADMIN" | "DOCTOR" | "RECEPTIONIST" | "SUPER_ADMIN",
      "hospital_id": "HOSP-XXXX-YYYY",
      "exp": now + 1440min
    }
          │
          ▼
    Client stores token in localStorage
          │
          ▼
    Every API call: Authorization: Bearer <token>
          │
          ▼
    FastAPI dependency: get_current_user()
    ├── Decode JWT
    ├── Validate hospital_id scope
    └── Return actor_profile for endpoint to use
```

**5 User Roles and Permissions:**

| Role | Can See | Can Do |
|---|---|---|
| `SUPER_ADMIN` | All hospitals | Manage plans, create hospitals, see all revenue |
| `ADMIN` | Own hospital | Full CRUD on staff, appointments, settings |
| `DOCTOR` | Own queue | View/complete own appointments, apply leave |
| `RECEPTIONIST` | Own hospital | Book/cancel appointments, view queue |
| `PATIENT` | Own appointments | Self-book, view history |

---

## 8. Subscription Enforcement Architecture

```
Hospital Plan Status Check Flow:
    
    Any API Request
          │
          ▼
    JWT decoded → hospital_id extracted
          │
          ▼
    hospital.plan_status == "ACTIVE" ?
    ├── YES → Normal operation
    └── NO (EXPIRED / SUSPENDED):
        ├── Copilot → SaaS Consultant mode (no clinical tools)
        ├── Patient Portal → "Portal Paused" locked screen
        ├── Patient OTP → HTTP 403 (blocked)
        ├── Voice AI → Not functional (webhook returns error)
        └── Header → "🔒 Portal Paused" button (red)

Plans (from DB):
    STARTER  → ₹1,500/mo → Up to 3 doctors, basic features
    PRO      → ₹2,999/mo → Unlimited doctors, analytics, voice AI
    ENTERPRISE → ₹29,999/mo → Multi-branch, API access, dedicated support
```

---

## 9. Deployment Architecture (Current)

```
┌─────────────────────────────┐
│         Railway Cloud        │
│                              │
│  ┌────────────────────────┐  │
│  │   Docker Container     │  │
│  │   python:3.12-slim     │  │
│  │                        │  │
│  │   uvicorn app.main:app │  │
│  │   --host 0.0.0.0       │  │
│  │   --port 8000          │  │
│  │                        │  │
│  │   FastAPI + React SPA  │  │
│  │   (frontend/dist/)     │  │
│  └────────────────────────┘  │
│                              │
│  ┌────────────────────────┐  │
│  │   MySQL 8.x            │  │
│  │   Railway Managed      │  │
│  │   pool_size=15         │  │
│  │   max_overflow=20      │  │
│  └────────────────────────┘  │
└─────────────────────────────┘
         │
         │ HTTPS (Railway domain)
         │
    [Clients: Browsers, Twilio, Razorpay]
```

**Current limitations:**
- Single uvicorn worker (no horizontal scaling)
- No Redis (session data in-process)
- RAG in-process memory (shared with API)
- Logs to local disk (ephemeral container)

---

## 10. Scalability Roadmap

### Phase 1 — MVP Soft Launch (Now, 1-10 Hospitals)
✅ **Current architecture handles this**
- Single Railway container
- MySQL with pool_size=35
- Groq free tier (or pay-as-go)
- Single uvicorn worker
- **Max load: ~25 concurrent users, ~5 copilot req/min**

### Phase 2 — Growth (10-50 Hospitals)
🔧 **Changes needed:**
```
1. Add Redis (Railway Redis addon)
   ├── Session storage (conversation memory)
   └── Rate limiting (OTP, API abuse protection)

2. Multiple uvicorn workers
   CMD: uvicorn app.main:app --workers 4

3. Paid Groq / Gemini Flash as primary LLM
   ├── Groq Pay: $0.06/M tokens for qwen3.8b
   └── ~10x more capacity

4. Celery + Redis for async tasks
   ├── OTP SMS sending (non-blocking)
   ├── WhatsApp notifications
   └── Analytics report generation

5. Sentry error tracking
6. Database read replicas (Railway Pro)
```
**Expected load: ~100 concurrent users, ~50 copilot req/min**

### Phase 3 — Scale (50-200 Hospitals)
🏗️ **Major architecture changes:**
```
1. Microservices split:
   ├── aura-api (core business logic)
   ├── aura-copilot (AI engine — separate service)
   ├── aura-voice (Twilio voice service)
   └── aura-scheduler (Celery workers)

2. Vector DB for RAG
   ├── Qdrant (self-hosted on VPS) or Pinecone
   └── Per-hospital knowledge namespaces

3. API Gateway (Kong or AWS API Gateway)
   ├── Rate limiting per hospital
   └── Auth at gateway layer

4. Load balancer (nginx or Railway LB)
   └── Multiple backend instances

5. Database sharding or read replicas
   └── Separate by region (Mumbai, Delhi)
```
**Expected load: ~500 concurrent users, ~200 copilot req/min**

### Phase 4 — Enterprise (200+ Hospitals)
🚀 **Cloud-native:**
```
1. Kubernetes (GKE / EKS)
2. Service mesh (Istio)
3. Horizontal pod autoscaling
4. Multi-region MySQL (AWS RDS Aurora)
5. Kafka for event streaming (appointment events, analytics)
6. OpenTelemetry distributed tracing
7. Private LLM deployment (vLLM on GPU servers)
```
**Expected load: 5,000+ concurrent users**

---

## 11. AI Pipeline Architecture (Detail)

```
User Query: "Is Dr. Dewedi on leave tomorrow?"
    │
    ▼
[IntentRouter]
    ├── LIVE_DATA pattern match: "on leave" ✓
    ├── RAG search: no policy hit
    └── prune_tools: [check_doctor_leaves, get_doctor_roster]
    Result: RouteType.LIVE_DATA, confidence=0.88
    │
    ▼
[CopilotEngine — LIVE_DATA branch]
    System Prompt:
    ├── "You are AURA Copilot for Rao Hospital"
    ├── "Today: 2026-09-17, Role: RECEPTIONIST"
    └── "Available tools: [check_doctor_leaves, get_doctor_roster]"
    │
    ▼
[Groq API — qwen3.8-27b]
    Model selects: check_doctor_leaves(doctor_name="Dewedi", date="2026-09-18")
    │
    ▼
[Tool Execution — Python Function]
    DB Query: SELECT * FROM leaves WHERE doctor like '%dewedi%' AND leave_date='2026-09-18'
    Result: {"on_leave": false, "status": "available"}
    │
    ▼
[Groq API — Second turn]
    Tool result appended → LLM generates human response
    Output: "Dr. Dewedi is available tomorrow. No leaves recorded."
    │
    ▼
[Response Builder]
    ├── suggestions: ["Book appointment with Dr. Dewedi", "See full roster"]
    └── Return to frontend
```

---

## 12. Data Flow Diagrams

### Appointment Booking Flow (Via Copilot)

```
Receptionist → "Book appointment for Shivay Mishra with Dr. Agni tomorrow"
    │
    ▼
EntityExtractor → {patient_name: "Shivay Mishra", doctor: "Agni", date: "tomorrow"}
    │
    ▼
ACTION route → book_appointment() tool
    │
    ├── Find/create patient record
    │   ├── Search by phone + first_name exact match
    │   ├── If not found → CREATE new patient record
    │   └── Track booked_by_name (account holder)
    │
    ├── get_open_slots(doctor_id, date) → available times
    │
    ├── Confirm with receptionist (if required)
    │
    └── INSERT into appointments table
        ├── status: "BOOKED"
        ├── source: "COPILOT"
        └── appointment_id: "apt_xxxxx"
```

### Patient Portal Booking Flow

```
Patient visits /balaji-hospital (slug)
    │
    ▼
PatientPortal.jsx loads
    │
    ▼
GET /api/v1/patient/hospital/balaji
    ├── is_expired: true/false
    └── hospital info
    │
    ▼
If expired → Show "Portal Paused" screen (no login)
If active → Show OTP login form
    │
    ▼
POST /api/v1/patient/send-otp {phone, hospital_id}
    ├── Check plan_status → 403 if expired
    ├── Find/create patient record
    ├── Generate OTP → Send via SMS (currently hardcoded 1234)
    └── Store otp + otp_expires_at
    │
    ▼
POST /api/v1/patient/verify-otp {phone, otp}
    ├── Validate OTP + expiry
    ├── Issue PATIENT role JWT
    └── Return patient profile
    │
    ▼
Patient Dashboard:
    ├── View upcoming appointments
    ├── Book new appointment (max +2 days ahead)
    └── View visit history
```

---

## 13. Frontend Architecture

```
frontend/src/
├── App.jsx (354KB) ← MONOLITHIC — all hospital UI in one file
│   ├── Login screen
│   ├── Admin Dashboard
│   ├── Doctor Queue (embedded)
│   ├── Receptionist view
│   └── Appointment management
│
├── PatientPortal.jsx (61KB) ← Self-contained patient SPA
│   ├── Hospital slug-based routing
│   ├── OTP login flow
│   └── Appointment booking/viewing
│
└── components/
    ├── copilot/
    │   └── CopilotWidget.jsx (1,594 lines) ← AI chatbot widget
    ├── common/
    │   ├── Header.jsx ← Top nav with portal link
    │   └── ...
    └── doctor/
        └── DoctorQueue.jsx ← Live queue component

Build: Vite → frontend/dist/ → Served by FastAPI StaticFiles
```

**Technical Debt Note:** `App.jsx` at 354KB is the biggest maintainability risk. It should be split into ~15-20 separate page components before the codebase grows further.

---

## 14. Key Files Reference Map

| File | Size | Purpose |
|---|---|---|
| [`app/main.py`](file:///c:/Users/shiva/Desktop/AAA/app/main.py) | 3KB | App factory, CORS, static files |
| [`app/core/config.py`](file:///c:/Users/shiva/Desktop/AAA/app/core/config.py) | 3KB | All env vars and settings |
| [`app/api/v1/router.py`](file:///c:/Users/shiva/Desktop/AAA/app/api/v1/router.py) | 2KB | All 13 API route groups |
| [`app/engines/copilot_engine.py`](file:///c:/Users/shiva/Desktop/AAA/app/engines/copilot_engine.py) | **170KB** | Main AI brain — full pipeline |
| [`app/engines/intent_router.py`](file:///c:/Users/shiva/Desktop/AAA/app/engines/intent_router.py) | 13KB | 5-way intent classification |
| [`app/engines/rag_engine.py`](file:///c:/Users/shiva/Desktop/AAA/app/engines/rag_engine.py) | 21KB | Knowledge retrieval (BM25+Cosine) |
| [`app/engines/tool_registry.py`](file:///c:/Users/shiva/Desktop/AAA/app/engines/tool_registry.py) | 72KB | All tool specs + role permissions |
| [`app/engines/voice_state_machine.py`](file:///c:/Users/shiva/Desktop/AAA/app/engines/voice_state_machine.py) | 42KB | Phone call AI flow |
| [`app/engines/groq_client.py`](file:///c:/Users/shiva/Desktop/AAA/app/engines/groq_client.py) | 5KB | Groq LLM HTTP client |
| [`app/tools/appointment_tools.py`](file:///c:/Users/shiva/Desktop/AAA/app/tools/appointment_tools.py) | 21KB | Booking logic, patient matching |
| [`app/database/session.py`](file:///c:/Users/shiva/Desktop/AAA/app/database/session.py) | 2KB | DB pool (pool_size=15, max=35) |
| [`app/database/schema.sql`](file:///c:/Users/shiva/Desktop/AAA/app/database/schema.sql) | 23KB | Full DB schema reference |
| [`frontend/src/App.jsx`](file:///c:/Users/shiva/Desktop/AAA/frontend/src/App.jsx) | **354KB** | All hospital-facing UI |
| [`frontend/src/PatientPortal.jsx`](file:///c:/Users/shiva/Desktop/AAA/frontend/src/PatientPortal.jsx) | 61KB | Patient self-service portal |
| [`Dockerfile`](file:///c:/Users/shiva/Desktop/AAA/Dockerfile) | 1KB | Container build instructions |

---

## 15. Future Upgrade Paths

### Short Term (1-3 months)
- [ ] Real SMS OTP (Twilio / MSG91)
- [ ] Email notifications (Resend.com)
- [ ] Redis for session persistence
- [ ] Rate limiting middleware
- [ ] Sentry error monitoring
- [ ] Split `App.jsx` into page components

### Medium Term (3-6 months)
- [ ] WhatsApp Business (Meta-approved)
- [ ] Razorpay Subscription API (auto-renewal for hospitals)
- [ ] EMR (Electronic Medical Records) module
- [ ] AI-generated discharge summaries
- [ ] Analytics dashboard with charts (Recharts/Victory)
- [ ] Mobile app (React Native)

### Long Term (6-18 months)
- [ ] Multi-branch hospital support
- [ ] Lab reports integration
- [ ] Insurance / TPA claim automation
- [ ] HL7 FHIR compliance (for government integrations)
- [ ] Vector DB (Qdrant) for per-hospital RAG
- [ ] AI-driven triage assistant
- [ ] Revenue cycle management (RCM)
- [ ] API marketplace for third-party integrations

---

## 16. What Makes AURA Defensible (Moat)

1. **Voice AI + Chat AI + Portal = Complete automation** — competitors usually do one of these
2. **Multi-tenant SaaS from day 1** — not a single-clinic tool
3. **Indian Healthcare context** — Hindi/English mix, Indian insurance panels, Indian payment rails
4. **Role-aware AI** — Doctor sees different copilot than Receptionist vs Admin
5. **Subscription enforcement built-in** — upsell is automated (expired → consult pills)
6. **Offline-tolerant UX** — Patient Portal works on basic internet
7. **One binary to deploy** — FastAPI serves both API and React SPA from same container

---

*This HLD document should be updated whenever major architectural changes are made. Version this alongside the codebase.*
