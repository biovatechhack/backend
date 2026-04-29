"""Add medication_schedules table."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260428_0003"
down_revision = "20260428_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "medication_schedules",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("patient_id", sa.String(length=36), nullable=False),
        sa.Column("medication", sa.String(length=120), nullable=False),
        sa.Column("scheduled_time", sa.String(length=5), nullable=False),
        sa.Column("frequency", sa.String(length=16), nullable=False),
        sa.Column("meal_context", sa.String(length=8), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "frequency IN ('daily', 'twice_daily')",
            name="ck_medication_schedules_frequency",
        ),
        sa.CheckConstraint(
            "meal_context IN ('before', 'after')",
            name="ck_medication_schedules_meal_context",
        ),
        sa.CheckConstraint(
            "scheduled_time GLOB '[0-2][0-9]:[0-5][0-9]'",
            name="ck_medication_schedules_time_format",
        ),
    )
    op.create_index(
        "ix_medication_schedules_patient_id",
        "medication_schedules",
        ["patient_id"],
        unique=False,
    )
    op.create_index(
        "ix_medication_schedules_active",
        "medication_schedules",
        ["active", "scheduled_time"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_medication_schedules_active", table_name="medication_schedules")
    op.drop_index("ix_medication_schedules_patient_id", table_name="medication_schedules")
    op.drop_table("medication_schedules")
