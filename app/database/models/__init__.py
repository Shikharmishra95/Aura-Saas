"""
AI Voice Receptionist - Central Model Registry
"""
from app.database.models.appointment import (
    Hospital,
    HospitalSetting,
    WorkingHour,
    Department,
    Doctor,
    DoctorSchedule,
    HospitalHoliday,
    Patient,
    Appointment,
    ConsultationNote,
    DoctorLeave
)
from app.database.models.conversation import (
    CallLog,
    VoiceSession,
    ConversationLog,
    ConversationMemory,
    ToolExecutionLog,
    DoctorAvailabilityCache,
    KnowledgeBase,
    FAQ
)
from app.database.models.call_log import User, Role, UserRole, Notification, NotificationLog, AuditLog

__all__ = [
    "Hospital",
    "HospitalSetting",
    "WorkingHour",
    "Department",
    "Doctor",
    "DoctorSchedule",
    "HospitalHoliday",
    "Patient",
    "Appointment",
    "ConsultationNote",
    "DoctorLeave",
    "CallLog",
    "VoiceSession",
    "ConversationLog",
    "ConversationMemory",
    "ToolExecutionLog",
    "DoctorAvailabilityCache",
    "KnowledgeBase",
    "FAQ",
    "User",
    "Role",
    "UserRole"
]
