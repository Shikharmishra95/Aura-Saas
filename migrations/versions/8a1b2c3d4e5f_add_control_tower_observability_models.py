"""add control tower observability models

Revision ID: 8a1b2c3d4e5f
Revises: 4dfbad769d3d
Create Date: 2026-08-27 15:35:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '8a1b2c3d4e5f'
down_revision: Union[str, None] = '4dfbad769d3d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. hospital_subscription_history
    op.create_table(
        'hospital_subscription_history',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('hospital_id', sa.String(length=36), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('plan_name', sa.String(length=50), nullable=False),
        sa.Column('amount_paid', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0.00'),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='INR'),
        sa.Column('payment_ref', sa.String(length=100), nullable=True),
        sa.Column('duration_days_added', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('plan_started_at', sa.DateTime(), nullable=False),
        sa.Column('plan_expires_at', sa.DateTime(), nullable=False),
        sa.Column('triggered_by', sa.String(length=100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['hospital_id'], ['hospitals.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_sub_hist_hosp_time', 'hospital_subscription_history', ['hospital_id', 'created_at'])
    op.create_index('idx_sub_hist_event', 'hospital_subscription_history', ['event_type'])

    # 2. tenant_error_logs
    op.create_table(
        'tenant_error_logs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('hospital_id', sa.String(length=36), nullable=True),
        sa.Column('service_name', sa.String(length=50), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False, server_default='WARNING'),
        sa.Column('error_code', sa.String(length=100), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=False),
        sa.Column('stack_trace', sa.Text(), nullable=True),
        sa.Column('environment', sa.String(length=20), nullable=False, server_default='production'),
        sa.Column('endpoint', sa.String(length=255), nullable=True),
        sa.Column('http_method', sa.String(length=10), nullable=True),
        sa.Column('http_status', sa.Integer(), nullable=True),
        sa.Column('request_id', sa.String(length=64), nullable=True),
        sa.Column('correlation_id', sa.String(length=64), nullable=True),
        sa.Column('user_id', sa.String(length=36), nullable=True),
        sa.Column('voice_session_id', sa.String(length=64), nullable=True),
        sa.Column('call_id', sa.String(length=64), nullable=True),
        sa.Column('appointment_id', sa.String(length=36), nullable=True),
        sa.Column('payment_id', sa.String(length=64), nullable=True),
        sa.Column('external_provider', sa.String(length=50), nullable=True),
        sa.Column('provider_error_code', sa.String(length=100), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('occurred_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('resolution_status', sa.String(length=20), nullable=False, server_default='UNRESOLVED'),
        sa.ForeignKeyConstraint(['hospital_id'], ['hospitals.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_err_hosp_occurred', 'tenant_error_logs', ['hospital_id', 'occurred_at'])
    op.create_index('idx_err_svc_sev', 'tenant_error_logs', ['service_name', 'severity'])
    op.create_index('idx_err_code', 'tenant_error_logs', ['error_code'])
    op.create_index('idx_err_request', 'tenant_error_logs', ['request_id'])
    op.create_index('idx_err_correlation', 'tenant_error_logs', ['correlation_id'])

    # 3. platform_audit_logs
    op.create_table(
        'platform_audit_logs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('actor_id', sa.String(length=36), nullable=False),
        sa.Column('actor_username', sa.String(length=100), nullable=False),
        sa.Column('actor_role', sa.String(length=50), nullable=False),
        sa.Column('hospital_id', sa.String(length=36), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('resource_type', sa.String(length=50), nullable=False),
        sa.Column('resource_id', sa.String(length=64), nullable=True),
        sa.Column('old_state', sa.JSON(), nullable=True),
        sa.Column('new_state', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='SUCCESS'),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=255), nullable=True),
        sa.Column('request_id', sa.String(length=64), nullable=True),
        sa.Column('correlation_id', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['hospital_id'], ['hospitals.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_audit_hosp_created', 'platform_audit_logs', ['hospital_id', 'created_at'])
    op.create_index('idx_audit_action_res', 'platform_audit_logs', ['action', 'resource_type'])
    op.create_index('idx_audit_actor', 'platform_audit_logs', ['actor_id'])

    # 4. platform_incidents
    op.create_table(
        'platform_incidents',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False, server_default='P3_MEDIUM'),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='DETECTED'),
        sa.Column('hospital_id', sa.String(length=36), nullable=True),
        sa.Column('affected_service', sa.String(length=50), nullable=False),
        sa.Column('detected_by', sa.String(length=50), nullable=False, server_default='AUTOMATED_RULE'),
        sa.Column('assigned_to', sa.String(length=100), nullable=True),
        sa.Column('root_cause', sa.Text(), nullable=True),
        sa.Column('resolution_summary', sa.Text(), nullable=True),
        sa.Column('related_error_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('started_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('acknowledged_at', sa.DateTime(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['hospital_id'], ['hospitals.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_incident_status_sev', 'platform_incidents', ['status', 'severity'])
    op.create_index('idx_incident_service', 'platform_incidents', ['affected_service'])
    op.create_index('idx_incident_hospital', 'platform_incidents', ['hospital_id'])

    # 5. platform_alerts
    op.create_table(
        'platform_alerts',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('alert_name', sa.String(length=100), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False, server_default='WARNING'),
        sa.Column('trigger_rule', sa.String(length=100), nullable=False),
        sa.Column('hospital_id', sa.String(length=36), nullable=True),
        sa.Column('affected_service', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('metric_value', sa.String(length=100), nullable=True),
        sa.Column('threshold_value', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='ACTIVE'),
        sa.Column('incident_id', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['hospital_id'], ['hospitals.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['incident_id'], ['platform_incidents.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_alert_status_sev', 'platform_alerts', ['status', 'severity'])
    op.create_index('idx_alert_hospital', 'platform_alerts', ['hospital_id'])

def downgrade() -> None:
    op.drop_table('platform_alerts')
    op.drop_table('platform_incidents')
    op.drop_table('platform_audit_logs')
    op.drop_table('tenant_error_logs')
    op.drop_table('hospital_subscription_history')
