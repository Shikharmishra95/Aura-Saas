from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth,
    hospitals,
    subscriptions,
    staff,
    leaves,
    payments,
    patients,
    doctor_queue,
    appointments,
    voice,
    patient_auth,
    patient_portal,
    copilot,
)
from app.api.v1.endpoints.owner import owner_router

api_router = APIRouter()

# 1. Authentication & Tenant Onboarding
api_router.include_router(auth.router, tags=["auth"])

# 2. Hospitals & Multi-tenant Admin Config
api_router.include_router(hospitals.router, tags=["hospital"])

# 3. SaaS Subscription Plans & Dynamic Pricing Engine
api_router.include_router(subscriptions.router, tags=["subscription"])

# 4. Staff & Doctor Management
api_router.include_router(staff.router, tags=["staff"])

# 5. Doctor Leaves & Scheduling Overrides
api_router.include_router(leaves.router, tags=["leaves"])

# 6. Online Payments & Razorpay Integration
api_router.include_router(payments.router, tags=["payment"])

# 7. Patients Records & Search
api_router.include_router(patients.router, tags=["patients"])

# 8. Doctor Consultation Queue & OPD Workflow
api_router.include_router(doctor_queue.router, tags=["doctor"])

# 9. Appointments, Bookings & Availability Sweeper
api_router.include_router(appointments.router, tags=["appointments"])

# 10. Voice Stream Webhooks (Twilio & Live Call Bot)
api_router.include_router(voice.router, prefix="/voice", tags=["voice"])

# 11. Patient Portal & Auth
api_router.include_router(patient_auth.router, prefix="/patient", tags=["patient_auth"])
api_router.include_router(patient_portal.router, prefix="/patient", tags=["patient_portal"])

# 12. Super Admin Control Tower
api_router.include_router(owner_router, prefix="/owner", tags=["owner_control_tower"])

# 13. Context-Aware AI Copilot Chatbot
api_router.include_router(copilot.router, tags=["copilot"])
