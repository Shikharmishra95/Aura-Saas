# AURA Control Tower — Enterprise SaaS Observability & Multi-Tenant Control Architecture

**Document Version:** 2.0.0  
**Status:** Approved Technical Architecture  
**Authors:** Principal SaaS Architect, Multi-Tenant Security Architect, SRE Lead, Senior FastAPI/React Architect, AI Platform Architect, Enterprise QA Lead  
**Classification:** Internal Architecture Specification

---

## 1. Executive Architecture & Mission

AURA is an enterprise multi-tenant Hospital AI Voice Receptionist and Clinical Management Platform. As the platform scales across hospitals, clinics, and health networks, the platform owner requires an **Enterprise Control Tower** rather than a simple CRUD admin screen.

The **AURA Control Tower** provides:
- Single-pane-of-glass observability across all hospital tenants.
- Real-time fault detection, isolation, and root-cause analysis down to individual requests, voice sessions, and tool calls.
- Full subscription and revenue lifecycle ledgering (SaaS collections vs hospital patient revenues).
- Live AI voice stream diagnostics, tool-call tracking, and WhatsApp delivery telemetry.
- Multi-tenant security guardrails and cross-tenant access attempt isolation.
- Structured incident management lifecycle decoupled from raw error streams.

```
                                    ┌────────────────────────────────────────┐
                                    │       AURA CONTROL TOWER (UI)          │
                                    │    (SuperAdmin Master Workspace)       │
                                    └───────────────────┬────────────────────┘
                                                        │
                   ┌────────────────────────────────────┼────────────────────────────────────┐
                   ▼                                    ▼                                    ▼
       ┌───────────────────────┐            ┌───────────────────────┐            ┌───────────────────────┐
       │   Operations & 360°   │            │ Observability & SRE   │            │ Billing & Governance  │
       │ - Hospital 360°       │            │ - Unified Traces      │            │ - Subscription Ledger │
       │ - Doctor Quotas       │            │ - Error Stream        │            │ - Razorpay Gateway    │
       │ - OPD Patient Funnels │            │ - Incident Lifecycle  │            │ - Platform Revenue    │
       │ - Voice & AI Telemetry│            │ - System Health Radar │            │ - Audit & Compliance  │
       └───────────────────────┘            └───────────────────────┘            └───────────────────────┘
                                                        │
                      ┌─────────────────────────────────┴─────────────────────────────────┐
                      ▼                                                                   ▼
       ┌───────────────────────────────┐                                   ┌───────────────────────────────┐
       │     FastAPI Owner Endpoints   │                                   │     PostgreSQL / MySQL        │
       │  /api/v1/owner/hospitals/     │                                   │  - hospital_subscription_hist │
       │  /api/v1/owner/health/        │                                   │  - platform_audit_logs        │
       │  /api/v1/owner/incidents/     │                                   │  - tenant_error_logs          │
       │  /api/v1/owner/voice-metrics/ │                                   │  - platform_incidents         │
       │  /api/v1/owner/audit-logs/    │                                   │  - platform_alerts            │
       └───────────────────────────────┘                                   └───────────────────────────────┘
```

---

## 2. Design Principles

1. **Zero Trust Multi-Tenancy**: All queries, mutations, and metrics must be explicitly tenant-scoped. SuperAdmin endpoints verify `SUPER_ADMIN` authorization at the FastAPI dependency layer; frontend claims are never trusted.
2. **Decoupled Observability & Auditing**: Runtime errors (`tenant_error_logs`) are separated from security/compliance audit trails (`platform_audit_logs`) and business incident records (`platform_incidents`).
3. **End-to-End Correlation**: Every inbound HTTP request, Twilio call webhook, Gemini Live AI session, and Razorpay webhook carries a unified `request_id` and `correlation_id`.
4. **Data Minimization & Safe Redaction**: Protected Health Information (PHI), patient credentials, and API secrets are never logged in plaintext.
5. **Fault Isolation & Graceful Degradation**: If an external provider (Twilio, Gemini, Razorpay, WhatsApp) degrades or fails, the Control Tower continues reporting platform status without crashing.

---

## 3. Owner Control Tower Modules

The Control Tower is partitioned into 9 domain modules:

| Module | Core Purpose | Primary Data Sources |
|---|---|---|
| **1. Executive Overview** | High-level business KPI summary, active tenants, MRR/ARR, platform health score | `hospitals`, `hospital_subscription_history`, `platform_incidents` |
| **2. Hospital 360°** | Full tenant lifecycle, doctor quota compliance, patient funnel, AI voice metrics | `hospitals`, `doctors`, `appointments`, `call_logs`, `tenant_error_logs` |
| **3. Subscription & Billing** | Multi-tiered subscription history, renewal countdowns, Razorpay transaction ledger | `hospital_subscription_history`, `hospital_billings`, Razorpay API |
| **4. System Observability** | Centralized, queryable, and filterable runtime error stream with stack traces | `tenant_error_logs`, Request Tracing Middleware |
| **5. AI & Voice Operations** | Live Twilio stream health, Gemini Live latency, tool-call conversion, dropped calls | `call_logs`, `conversations`, `tenant_error_logs` |
| **6. Incident Management** | Structured incident tracking (Detected → Acknowledged → Investigating → Resolved) | `platform_incidents`, `tenant_error_logs` |
| **7. Audit & Security** | Immutable log of administrative actions, plan overrides, and cross-tenant attempts | `platform_audit_logs` |
| **8. System Health Radar** | 4-state dependency & application health checks (MySQL, Twilio, Gemini, WhatsApp, Razorpay) | Health probes, latency benchmarks |
| **9. Platform Alerts** | Threshold-based notifications (high AI drop-rate, payment verification failures) | `platform_alerts`, Event bus |

---

## 4. Hospital 360° Architecture

The Hospital 360° view unifies the entire operational posture of a hospital into a single pane:

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ HOSPITAL 360° — Apollo Care Clinic [HOSP-APOL-7457]                                                    │
├────────────────────────┬────────────────────────┬────────────────────────┬─────────────────────────────┤
│ 💼 SUBSCRIPTION        │ 👨‍⚕️ OPERATIONS          │ 📞 AI VOICE RECEPTION   │ 🛡️ SECURITY & HEALTH         │
│ Plan: PRO AI (Monthly) │ Doctors: 4 / 5 Quota   │ Total Calls: 384 Calls │ Health: 🟢 ALL HEALTHY      │
│ Status: ACTIVE         │ Total Patients: 1,420  │ AI Booking Rate: 82%   │ Auth Failures: 0 (24h)      │
│ Expiry: In 28 Days     │ Today Bookings: 18     │ Avg Latency: 210ms     │ Tenant Violations: 0        │
│ Total Paid: ₹5,998     │ Completion Rate: 91%   │ Dropped Calls: 2 (0.5%)│ Error Rate: 0.02%           │
└────────────────────────┴────────────────────────┴────────────────────────┴─────────────────────────────┘
```

### Drill-Down Capabilities
- **Subscription History**: View exact date of join, every renewal receipt, price paid, days added, and payment reference.
- **Doctor Roster & Quotas**: View doctors, OPD fees, active schedules, and whether quota limits are reached.
- **Appointment Funnel**: Filter appointments by Completed, Pending Payment, Cancelled, or Missed.
- **Voice Sessions**: Inspect call durations, Gemini prompt execution timings, and tool-call outputs.
- **Diagnostics**: Filter error logs specifically generated by this tenant.

---

## 5. Observability & Correlation Tracing

### Request & Session Correlation Flow
Every event across the platform is linked via correlation identifiers:

```
[Inbound Twilio Webhook / HTTP API]
             │ (Generates request_id & correlation_id)
             ▼
    [FastAPI Middleware]
             │
             ├──► [Appointment Engine] ──► (Logs with correlation_id)
             │
             ├──► [Gemini Live AI Client] ──► (Logs tool_call with correlation_id)
             │
             ├──► [Database Mutation] ──► (Emits platform_audit_log with correlation_id)
             │
             └──► [WhatsApp Service] ──► (Dispatches notification with correlation_id)
```

If an error occurs anywhere in this chain, `tenant_error_logs` records the `correlation_id`, allowing the SuperAdmin to search one ID and see the entire lifecycle.

---

## 6. Error Event Model (`tenant_error_logs`)

```sql
CREATE TABLE tenant_error_logs (
    id VARCHAR(36) PRIMARY KEY,
    hospital_id VARCHAR(36) NULL,
    service_name VARCHAR(50) NOT NULL,    -- 'TWILIO_VOICE', 'GEMINI_AI', 'WHATSAPP', 'PAYMENT', 'DATABASE', 'AUTH'
    severity VARCHAR(20) NOT NULL,        -- 'CRITICAL', 'WARNING', 'INFO'
    error_code VARCHAR(100) NOT NULL,     -- 'GEMINI_TIMEOUT', 'TWILIO_CALL_DROP', 'RAZORPAY_SIGNATURE_MISMATCH'
    error_message TEXT NOT NULL,
    stack_trace TEXT NULL,
    environment VARCHAR(20) DEFAULT 'production',
    endpoint VARCHAR(255) NULL,
    http_method VARCHAR(10) NULL,
    http_status INT NULL,
    request_id VARCHAR(64) NULL,
    correlation_id VARCHAR(64) NULL,
    user_id VARCHAR(36) NULL,
    voice_session_id VARCHAR(64) NULL,
    call_id VARCHAR(64) NULL,
    appointment_id VARCHAR(36) NULL,
    payment_id VARCHAR(64) NULL,
    external_provider VARCHAR(50) NULL,
    provider_error_code VARCHAR(100) NULL,
    details JSON NULL,
    occurred_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at DATETIME NULL,
    resolution_status VARCHAR(20) DEFAULT 'UNRESOLVED',
    
    INDEX idx_error_hosp_time (hospital_id, occurred_at),
    INDEX idx_error_service_severity (service_name, severity),
    INDEX idx_error_correlation (correlation_id),
    INDEX idx_error_request (request_id),
    INDEX idx_error_code (error_code)
);
```

---

## 7. Platform Audit Event Model (`platform_audit_logs`)

Audit logs capture state mutations, configuration overrides, and security events:

```sql
CREATE TABLE platform_audit_logs (
    id VARCHAR(36) PRIMARY KEY,
    actor_id VARCHAR(36) NOT NULL,       -- User UUID or 'SYSTEM'
    actor_username VARCHAR(100) NOT NULL,
    actor_role VARCHAR(50) NOT NULL,     -- 'SUPER_ADMIN', 'ADMIN', 'DOCTOR', 'RECEPTIONIST'
    hospital_id VARCHAR(36) NULL,
    action VARCHAR(100) NOT NULL,        -- 'PLAN_UPGRADE', 'PLAN_RENEW', 'DOCTOR_CREATE', 'DOCTOR_DELETE', 'OVERRIDE_EXPIRY', 'CROSS_TENANT_ACCESS_BLOCKED'
    resource_type VARCHAR(50) NOT NULL,  -- 'HOSPITAL', 'DOCTOR', 'APPOINTMENT', 'SUBSCRIPTION', 'USER'
    resource_id VARCHAR(64) NULL,
    old_state JSON NULL,
    new_state JSON NULL,
    status VARCHAR(20) NOT NULL,         -- 'SUCCESS', 'FAILED', 'BLOCKED'
    ip_address VARCHAR(45) NULL,
    user_agent VARCHAR(255) NULL,
    request_id VARCHAR(64) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_audit_actor (actor_id, created_at),
    INDEX idx_audit_hospital (hospital_id, created_at),
    INDEX idx_audit_action (action),
    INDEX idx_audit_resource (resource_type, resource_id)
);
```

---

## 8. Incident Management Lifecycle (`platform_incidents`)

Errors do not automatically equal incidents. Incidents represent ongoing, actionable service degradations:

```
Error Spike / Anomaly ──► DETECTED ──► INCIDENT CREATED ──► ACKNOWLEDGED ──► INVESTIGATING ──► RESOLVED
```

```sql
CREATE TABLE platform_incidents (
    id VARCHAR(36) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    severity VARCHAR(20) NOT NULL,        -- 'P1_CRITICAL', 'P2_HIGH', 'P3_MEDIUM', 'P4_LOW'
    status VARCHAR(30) NOT NULL,          -- 'DETECTED', 'ACKNOWLEDGED', 'INVESTIGATING', 'MITIGATED', 'RESOLVED'
    hospital_id VARCHAR(36) NULL,         -- NULL if platform-wide, specific if tenant-isolated
    affected_service VARCHAR(50) NOT NULL,-- 'TWILIO_VOICE', 'GEMINI_AI', 'WHATSAPP', 'PAYMENTS', 'CORE_API'
    detected_by VARCHAR(50) NOT NULL,     -- 'AUTOMATED_RULE', 'SUPERADMIN_MANUAL', 'USER_REPORT'
    assigned_to VARCHAR(100) NULL,
    root_cause TEXT NULL,
    resolution_summary TEXT NULL,
    started_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    acknowledged_at DATETIME NULL,
    resolved_at DATETIME NULL,
    related_error_count INT DEFAULT 0,

    INDEX idx_incident_status (status, severity),
    INDEX idx_incident_service (affected_service),
    INDEX idx_incident_hospital (hospital_id)
);
```

---

## 9. Platform Alerting Model (`platform_alerts`)

```sql
CREATE TABLE platform_alerts (
    id VARCHAR(36) PRIMARY KEY,
    alert_name VARCHAR(100) NOT NULL,
    severity VARCHAR(20) NOT NULL,       -- 'CRITICAL', 'WARNING', 'INFO'
    trigger_rule VARCHAR(100) NOT NULL,  -- 'GEMINI_LATENCY_EXCEEDED', 'VOICE_DROP_SPIKE', 'SUBSCRIPTION_EXPIRING_SOON', 'CROSS_TENANT_VIOLATION'
    hospital_id VARCHAR(36) NULL,
    affected_service VARCHAR(50) NOT NULL,
    description TEXT NOT NULL,
    metric_value VARCHAR(100) NULL,
    threshold_value VARCHAR(100) NULL,
    status VARCHAR(20) DEFAULT 'ACTIVE', -- 'ACTIVE', 'ACKNOWLEDGED', 'RESOLVED', 'MUTED'
    incident_id VARCHAR(36) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at DATETIME NULL,

    FOREIGN KEY (incident_id) REFERENCES platform_incidents(id) ON DELETE SET NULL,
    INDEX idx_alert_status (status, severity),
    INDEX idx_alert_hospital (hospital_id)
);
```

---

## 10. System Health Model (4-State Matrix)

System health is evaluated across **4 Health Dimensions**:
1. **Infrastructure Health**: MySQL connection pool latency, FastAPI CPU/Memory load.
2. **Dependency Health**: Twilio API connectivity, Gemini AI endpoint response, WhatsApp webhook dispatch, Razorpay API.
3. **Application Health**: API response latency (P95 <= 200ms), 5xx error rate (< 0.1%).
4. **Business Health**: AI voice booking conversion rate (> 75%), WhatsApp delivery rate (> 98%).

### 4-State Health Definitions
- 🟢 **HEALTHY**: Latency < 300ms, error rate < 0.1%, all dependencies reachable.
- 🟡 **DEGRADED**: Latency between 300ms-1500ms, error rate 0.1%-5%, retry mechanisms active.
- 🔴 **DOWN**: Service unreachable, consecutive failures >= 3, critical business flow interrupted.
- ⚪ **UNKNOWN**: Probe timeout, agent unable to contact telemetry receiver.

---

## 11. AI & Voice Operations Telemetry

For each voice session handled by Twilio + Gemini Live AI, the system captures:
- `call_sid` & `voice_session_id`
- Total Call Duration (seconds)
- Latency per Turn (ms)
- Tool Calls Executed (`check_availability`, `book_appointment`, `cancel_appointment`)
- Termination Reason (`COMPLETED_BOOKING`, `CALLER_HUNG_UP`, `AI_TIMEOUT`, `TRANSFER_REQUESTED`, `ERROR`)
- Safe Redacted Transcript Excerpt (medical and payment data redacted)

---

## 12. Billing & Subscription Lifecycle Separation

The platform strictly separates **current state**, **audit ledger**, and **payment transactions**:

```
 ┌────────────────────────┐         ┌───────────────────────────────┐         ┌───────────────────────────┐
 │     Current State      │         │   Subscription History Ledger │         │   Payment Transactions    │
 │ (hospitals table)      │         │ (hospital_subscription_hist)  │         │ (hospital_billings)       │
 ├────────────────────────┤         ├───────────────────────────────┤         ├───────────────────────────┤
 │ subscription_plan: PRO │         │ Join: 2026-08-12 (STARTER)    │         │ pay_Nx716238: ₹2,999 PAID │
 │ plan_status: ACTIVE    │◄────────┤ Upgrade: 2026-08-27 (PRO)     │◄────────┤ pay_Qz823471: ₹2,999 PAID │
 │ plan_expires_at: Sep 26│         │ Renewal: 2026-09-26 (+30 Days)│         │ pay_Failed01: FAILED      │
 └────────────────────────┘         └───────────────────────────────┘         └───────────────────────────┘
```

---

## 13. Tenant Security & Cross-Tenant Violation Monitoring

When a user belonging to `Hospital A` attempts to read or mutate resources (doctors, patients, appointments) of `Hospital B`:
1. Request is blocked immediately with `403 Forbidden`.
2. A security audit record is written to `platform_audit_logs` (`action = 'CROSS_TENANT_ACCESS_BLOCKED'`).
3. An automated `platform_alerts` notification is raised for the SuperAdmin with `actor_id`, `source_hospital`, `target_hospital`, and `endpoint`.

---

## 14. Data Retention, Redaction & Privacy

### Redaction Rules
- **Passwords & Tokens**: Scrubber regex replaces any JWTs, passwords, or API keys with `[REDACTED]`.
- **Payment Information**: Raw card/UPI details never touch AURA servers (handled directly by Razorpay SDK).
- **PHI / Medical Data**: Clinical notes and prescriptions are viewable strictly by authorized hospital doctors; Control Tower error logs do not capture medical text in exception messages.

### Retention Schedule
| Entity | Retention Period | Archival Strategy |
|---|---|---|
| `tenant_error_logs` | 90 Days | Compressed cold-storage after 90 days; deleted after 1 year |
| `platform_audit_logs` | 7 Years | Immutable compliance retention |
| `platform_incidents` | Indefinite | Permanent post-mortem record |
| `hospital_subscription_history` | Indefinite | Permanent financial ledger |
| `call_logs` & Audio Streams | 180 Days | Transcripts kept; raw audio purged after 30 days |

---

## 15. API Architecture (Dedicated Modular Owner Routers)

To prevent code bloat, Owner endpoints are placed in a dedicated module `app/api/v1/endpoints/owner/`:

```
app/api/v1/endpoints/owner/
├── __init__.py
├── dashboard.py         # GET /api/v1/owner/overview
├── hospitals.py         # GET /api/v1/owner/hospitals, GET /api/v1/owner/hospitals/{id}/360
├── subscriptions.py     # GET /api/v1/owner/subscriptions/history, POST /api/v1/owner/subscriptions/override
├── observability.py     # GET /api/v1/owner/errors, GET /api/v1/owner/traces/{correlation_id}
├── incidents.py         # GET, POST, PATCH /api/v1/owner/incidents
├── audit.py             # GET /api/v1/owner/audit-logs
├── health.py            # GET /api/v1/owner/health-radar
└── voice_ops.py         # GET /api/v1/owner/voice/telemetry
```

### Authorization Dependency
All endpoints enforce:
```python
async def require_super_admin(current_user: User = Depends(get_current_user)):
    if current_user.hospital_id != "super_admin" and current_user.username != "shiva9532":
        raise HTTPException(status_code=403, detail="SuperAdmin privilege required")
    return current_user
```

---

## 16. Frontend Architecture (Modular Control Tower)

Instead of appending thousands of lines to `App.jsx`, the frontend is structured into modular SuperAdmin components:

```
frontend/src/components/superadmin/
├── ControlTowerLayout.jsx       # Header, navigation tabs, global health pill
├── ExecutiveOverview.jsx        # Business KPI cards, revenue graph, tenant health breakdown
├── Hospital360Modal.jsx         # 4-tab drill-down drawer (Overview, Subscription, Operations, Logs)
├── SystemObservability.jsx      # Live error log stream, correlation search, stack trace viewer
├── IncidentManager.jsx          # Incident creation, status transitions, root cause tagging
├── SystemHealthRadar.jsx        # Dependency probe tiles, latency sparklines
└── VoiceTelemetry.jsx          # Call duration distribution, AI tool-call charts
```

---

## 17. Failure & Graceful Degradation Strategy

The Control Tower is built with circuit breakers. If any subsystem is unreachable:
- **Twilio Down**: Control Tower displays `Twilio = 🔴 DOWN` while all other hospital analytics, doctor queues, and historical data remain fully operational.
- **Gemini Down**: Control Tower alerts owner with `Gemini = 🔴 DEGRADED`; receptionist fallback booking continues.
- **Database Latency Spike**: Fast cached metric rollups serve dashboard KPIs to prevent DB locks.

---

## 18. Testing & Verification Strategy

The Control Tower includes automated test coverage in `tests/integration/test_owner_control_tower_api.py`:
- 🛡️ **Role Authorization**: Verify `ADMIN`, `DOCTOR`, `RECEPTIONIST`, and unauthenticated requests receive `403 Forbidden` on all Owner routes.
- 📊 **360° Metric Calculation**: Verify accurate aggregation of doctor quotas, patient totals, and subscription countdowns.
- 💳 **Ledger Invariance**: Verify join, upgrade, and renewal events write immutable records to `hospital_subscription_history`.
- 🚨 **Incident State Transitions**: Test `DETECTED` → `ACKNOWLEDGED` → `RESOLVED` workflow.
- 🔄 **Correlation Tracing**: Verify search by `correlation_id` returns the full error trace.

---

## 19. Risks & Mitigations

| Identified Risk | Impact | Architecture Mitigation |
|---|---|---|
| Database write load from high error rates | High DB I/O | Error logging uses batching / rate limiting for repetitive error spikes |
| Accidental PHI leak in error traces | High Compliance Risk | Exception scrubbers filter patient names, phone numbers, and notes |
| Metric query slowdown with 100+ hospitals | Slow UI Load | Pre-aggregated summaries and indexed timestamp ranges |

---

## 20. Implementation Phases Summary

1. **Phase 1: Core Database Schema & Migrations** (`hospital_subscription_history`, `tenant_error_logs`, `platform_audit_logs`, `platform_incidents`, `platform_alerts`).
2. **Phase 2: Error & Audit Logging Middleware** (Automatic request correlation, exception logging, audit recording).
3. **Phase 3: Dedicated Owner API Routers** (`app/api/v1/endpoints/owner/*` with `require_super_admin`).
4. **Phase 4: Modular Frontend Control Tower UI** (React SuperAdmin components).
5. **Phase 5: Automated Pytest Suite & Regression Verification**.