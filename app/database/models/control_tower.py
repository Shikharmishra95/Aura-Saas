import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import String, Integer, DateTime, Text, ForeignKey, Numeric, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database.declarative import Base

class HospitalSubscriptionHistory(Base):
    """
    Append-only immutable financial & subscription ledger.
    Tracks every initial join, renewal, upgrade, downgrade, and manual expiration override.
    """
    __tablename__ = "hospital_subscription_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    hospital_id: Mapped[str] = mapped_column(ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)  # INITIAL_JOIN, RENEWAL, UPGRADE, DOWNGRADE, EXPIRED, MANUAL_OVERRIDE
    plan_name: Mapped[str] = mapped_column(String(50), nullable=False)   # STARTER, PRO, ENTERPRISE
    amount_paid: Mapped[float] = mapped_column(Numeric(10, 2), default=0.0, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    payment_ref: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # Razorpay payment ID or 'TRIAL_ACTIVATION'
    duration_days_added: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    plan_started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    plan_expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    triggered_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # Username or 'SYSTEM'
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)

    # Relationships
    hospital: Mapped["Hospital"] = relationship("Hospital")

    __table_args__ = (
        Index("idx_sub_hist_hosp_time", "hospital_id", "created_at"),
        Index("idx_sub_hist_event", "event_type"),
    )


class TenantErrorLog(Base):
    """
    Centralized error telemetry stream.
    Captures runtime failures tagged by tenant ID, service, error code, and correlation ID.
    """
    __tablename__ = "tenant_error_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    hospital_id: Mapped[Optional[str]] = mapped_column(ForeignKey("hospitals.id", ondelete="SET NULL"), nullable=True, index=True)
    service_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # TWILIO_VOICE, GEMINI_AI, WHATSAPP, PAYMENT, DATABASE, AUTH, CORE_API
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="WARNING", index=True)  # CRITICAL, WARNING, INFO
    error_code: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    stack_trace: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    environment: Mapped[str] = mapped_column(String(20), default="production", nullable=False)
    endpoint: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    http_method: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    http_status: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    request_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    correlation_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    voice_session_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    call_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    appointment_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    payment_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    external_provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # TWILIO, GEMINI, RAZORPAY, WHATSAPP
    provider_error_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    resolution_status: Mapped[str] = mapped_column(String(20), default="UNRESOLVED", nullable=False)

    # Relationships
    hospital: Mapped[Optional["Hospital"]] = relationship("Hospital")

    __table_args__ = (
        Index("idx_err_hosp_occurred", "hospital_id", "occurred_at"),
        Index("idx_err_svc_sev", "service_name", "severity"),
        Index("idx_err_code", "error_code"),
    )


class PlatformAuditLog(Base):
    """
    Append-only security and compliance audit trail.
    Answers: Who did what to which resource, when, from where, and with what outcome.
    """
    __tablename__ = "platform_audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    actor_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    actor_username: Mapped[str] = mapped_column(String(100), nullable=False)
    actor_role: Mapped[str] = mapped_column(String(50), nullable=False)  # SUPER_ADMIN, ADMIN, DOCTOR, RECEPTIONIST, SYSTEM
    hospital_id: Mapped[Optional[str]] = mapped_column(ForeignKey("hospitals.id", ondelete="SET NULL"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # PLAN_UPGRADE, PLAN_RENEW, DOCTOR_CREATE, OVERRIDE_EXPIRY, CROSS_TENANT_BLOCKED
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # HOSPITAL, DOCTOR, APPOINTMENT, SUBSCRIPTION, USER
    resource_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    old_state: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    new_state: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="SUCCESS", nullable=False)  # SUCCESS, FAILED, BLOCKED
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    request_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    correlation_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)

    # Relationships
    hospital: Mapped[Optional["Hospital"]] = relationship("Hospital")

    __table_args__ = (
        Index("idx_audit_hosp_created", "hospital_id", "created_at"),
        Index("idx_audit_action_res", "action", "resource_type"),
    )


class PlatformIncident(Base):
    """
    Formal operational incident lifecycle tracker.
    Lifecycle: DETECTED -> ACKNOWLEDGED -> INVESTIGATING -> MITIGATED -> RESOLVED
    """
    __tablename__ = "platform_incidents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="P3_MEDIUM", nullable=False, index=True)  # P1_CRITICAL, P2_HIGH, P3_MEDIUM, P4_LOW
    status: Mapped[str] = mapped_column(String(30), default="DETECTED", nullable=False, index=True)    # DETECTED, ACKNOWLEDGED, INVESTIGATING, MITIGATED, RESOLVED
    hospital_id: Mapped[Optional[str]] = mapped_column(ForeignKey("hospitals.id", ondelete="SET NULL"), nullable=True, index=True)  # NULL if platform-wide
    affected_service: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # TWILIO_VOICE, GEMINI_AI, WHATSAPP, PAYMENTS, CORE_API
    detected_by: Mapped[str] = mapped_column(String(50), default="AUTOMATED_RULE", nullable=False)
    assigned_to: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    root_cause: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolution_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    related_error_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    hospital: Mapped[Optional["Hospital"]] = relationship("Hospital")
    alerts: Mapped[List["PlatformAlert"]] = relationship("PlatformAlert", back_populates="incident")


class PlatformAlert(Base):
    """
    Automated and manual alerts for platform threshold violations.
    Status: ACTIVE, ACKNOWLEDGED, RESOLVED, MUTED
    """
    __tablename__ = "platform_alerts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    alert_name: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # CRITICAL, WARNING, INFO
    trigger_rule: Mapped[str] = mapped_column(String(100), nullable=False)  # GEMINI_LATENCY_EXCEEDED, VOICE_DROP_SPIKE, SUBSCRIPTION_EXPIRING_SOON
    hospital_id: Mapped[Optional[str]] = mapped_column(ForeignKey("hospitals.id", ondelete="SET NULL"), nullable=True, index=True)
    affected_service: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    metric_value: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    threshold_value: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", nullable=False, index=True)  # ACTIVE, ACKNOWLEDGED, RESOLVED, MUTED
    incident_id: Mapped[Optional[str]] = mapped_column(ForeignKey("platform_incidents.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    hospital: Mapped[Optional["Hospital"]] = relationship("Hospital")
    incident: Mapped[Optional["PlatformIncident"]] = relationship("PlatformIncident", back_populates="alerts")


class SubscriptionPlanConfig(Base):
    """
    Dynamic subscription tier and pricing definition table.
    Allows SuperAdmin to configure plan price, doctor limit, AI voice enablement, and feature bullets.
    """
    __tablename__ = "subscription_plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    plan_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)  # STARTER, PRO, ENTERPRISE
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    price_inr: Mapped[float] = mapped_column(Numeric(10, 2), default=0.0, nullable=False)
    billing_cycle: Mapped[str] = mapped_column(String(20), default="MONTHLY", nullable=False)  # TRIAL, MONTHLY, YEARLY
    duration_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    max_doctors: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    ai_voice_enabled: Mapped[bool] = mapped_column(Integer, default=1, nullable=False)
    whatsapp_enabled: Mapped[bool] = mapped_column(Integer, default=1, nullable=False)
    online_opd_enabled: Mapped[bool] = mapped_column(Integer, default=1, nullable=False)
    features_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array
    is_active: Mapped[bool] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

