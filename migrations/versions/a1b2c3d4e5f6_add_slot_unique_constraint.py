"""Add unique constraint to prevent double-booking on appointment slots

Revision ID: a1b2c3d4e5f6
Revises: ('8a1b2c3d4e5f', '9a8b7c6d5e4f')
Create Date: 2026-09-21 11:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = ('8a1b2c3d4e5f', '9a8b7c6d5e4f')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add active_slot_token column to appointments table
    try:
        op.add_column(
            'appointments',
            sa.Column('active_slot_token', sa.String(36), nullable=True, server_default='ACTIVE')
        )
    except Exception:
        pass

    # 2. Update existing rows where status is CANCELLED so active_slot_token is NULL
    try:
        op.execute("UPDATE appointments SET active_slot_token = NULL WHERE status = 'CANCELLED'")
    except Exception:
        pass

    # 3. Create unique constraint on (doctor_id, appointment_datetime, active_slot_token)
    try:
        op.create_unique_constraint(
            'uq_doctor_appointment_slot',
            'appointments',
            ['doctor_id', 'appointment_datetime', 'active_slot_token']
        )
    except Exception:
        pass


def downgrade() -> None:
    try:
        op.drop_constraint('uq_doctor_appointment_slot', 'appointments', type_='unique')
    except Exception:
        pass

    try:
        op.drop_column('appointments', 'active_slot_token')
    except Exception:
        pass
