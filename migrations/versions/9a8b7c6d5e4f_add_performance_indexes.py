"""Add performance indexes for appointments, patients, and leaves

Revision ID: 9a8b7c6d5e4f
Revises: ba53ba628a09
Create Date: 2026-09-17 15:10:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '9a8b7c6d5e4f'
down_revision: Union[str, None] = 'ba53ba628a09'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Safely create performance indexes
    try:
        op.create_index('idx_apt_hosp_date', 'appointments', ['hospital_id', 'appointment_datetime'], unique=False)
    except Exception:
        pass

    try:
        op.create_index('idx_apt_doctor_status', 'appointments', ['doctor_id', 'status'], unique=False)
    except Exception:
        pass

    try:
        op.create_index('idx_patient_phone_hosp', 'patients', ['phone', 'hospital_id'], unique=False)
    except Exception:
        pass

    try:
        op.create_index('idx_leaves_doctor_date', 'leaves', ['doctor_id', 'leave_date'], unique=False)
    except Exception:
        pass


def downgrade() -> None:
    try:
        op.drop_index('idx_leaves_doctor_date', table_name='leaves')
    except Exception:
        pass
    try:
        op.drop_index('idx_patient_phone_hosp', table_name='patients')
    except Exception:
        pass
    try:
        op.drop_index('idx_apt_doctor_status', table_name='appointments')
    except Exception:
        pass
    try:
        op.drop_index('idx_apt_hosp_date', table_name='appointments')
    except Exception:
        pass
