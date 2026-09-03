# AURA Control Tower — Phased Implementation Plan

This document outlines the step-by-step rollout of the AURA Control Tower across backend, database, APIs, and frontend.

---

## Phase 1: Database Foundation & Schema Additions
- [ ] Create `HospitalSubscriptionHistory` model in `app/database/models/subscription_history.py`.
- [ ] Create `TenantErrorLog` model in `app/database/models/observability.py`.
- [ ] Create `PlatformAuditLog` model in `app/database/models/audit.py`.
- [ ] Create `PlatformIncident` and `PlatformAlert` models in `app/database/models/incidents.py`.
- [ ] Register all new models in `app/database/models/__init__.py`.
- [ ] Execute database migration / table creation scripts and backfill initial records for existing hospitals.

---

## Phase 2: Error Scrubbing, Correlation Tracing & Audit Middleware
- [ ] Enhance `app/core/middleware.py` with automatic `request_id` and `correlation_id` injection.
- [ ] Build `app/services/error_recorder.py` with sensitive data scrubber (redacts JWTs, passwords, PHI).
- [ ] Build `app/services/audit_recorder.py` for immutable event recording.
- [ ] Hook audit recorder into `/register-hospital`, `/upgrade-plan`, and `/renew-plan`.

---

## Phase 3: Dedicated Owner API Endpoints (`app/api/v1/endpoints/owner/`)
- [ ] Create `app/api/v1/endpoints/owner/dependencies.py` enforcing `require_super_admin`.
- [ ] Implement `overview.py`: Global MRR, active hospitals, error rates, platform health.
- [ ] Implement `hospitals.py`: Master hospital table and deep `GET /hospitals/{id}/360` metrics.
- [ ] Implement `subscriptions.py`: History ledger and manual admin override capabilities.
- [ ] Implement `observability.py`: Filterable error stream, correlation trace lookup.
- [ ] Implement `incidents.py`: Incident creation, status transitions, and error associations.
- [ ] Implement `health.py`: Live 4-state dependency health probe (MySQL, Twilio, Gemini, WhatsApp, Razorpay).
- [ ] Register owner router in `app/api/v1/router.py` under prefix `/owner`.

---

## Phase 4: Frontend Control Tower UI (React Modular SuperAdmin)
- [ ] Create `frontend/src/components/superadmin/ControlTowerLayout.jsx`.
- [ ] Implement `ExecutiveOverview.jsx`: Top KPI summary, health status badge, revenue breakdown.
- [ ] Implement `Hospital360Modal.jsx`: 4-tab interactive drawer (Overview, Subscription Ledger, Operations, Diagnostics).
- [ ] Implement `SystemObservability.jsx`: Live error table, severity filters, stack trace viewer.
- [ ] Implement `IncidentManager.jsx`: Incident lifecycle tracking with status badges.
- [ ] Implement `SystemHealthRadar.jsx`: Real-time probe cards for all services.
- [ ] Integrate Control Tower seamlessly into SuperAdmin view in `App.jsx`.

---

## Phase 5: Automated Testing & Verification
- [ ] Create `tests/integration/test_owner_control_tower_api.py`.
- [ ] Test strict 403 Forbidden enforcement for non-superadmin roles.
- [ ] Test subscription history recording on registration, renewal, and upgrade.
- [ ] Test incident creation and resolution lifecycle.
- [ ] Test error filtering and trace correlation lookups.
- [ ] Verify 100% pass on all 41 existing unit & regression tests.
- [ ] Verify `npm run build` in `frontend/` compiles with 0 errors.