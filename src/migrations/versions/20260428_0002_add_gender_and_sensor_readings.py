"""Add gender to patients and create sensor_readings table."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260428_0002"
down_revision = "20260427_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # SQLite doesn't support ADD CONSTRAINT via ALTER TABLE; use batch mode.
    with op.batch_alter_table("patients") as batch_op:
        batch_op.add_column(
            sa.Column("gender", sa.String(length=1), nullable=False, server_default="M")
        )
        batch_op.create_check_constraint("ck_patients_gender", "gender IN ('M', 'F')")

    op.create_table(
        "sensor_readings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("patient_id", sa.String(length=36), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("glucose_mg_dl", sa.Float(), nullable=False),
        sa.Column("heart_rate_bpm", sa.Integer(), nullable=False),
        sa.Column("spo2_pct", sa.Integer(), nullable=False),
        sa.Column("steps_today", sa.Integer(), nullable=False),
        sa.Column("sleep_hours", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("spo2_pct BETWEEN 0 AND 100", name="ck_sensor_readings_spo2"),
    )
    op.create_index(
        "ix_sensor_readings_patient_id", "sensor_readings", ["patient_id"], unique=False
    )
    op.create_index(
        "ix_sensor_readings_recorded_at",
        "sensor_readings",
        ["patient_id", "recorded_at"],
        unique=False,
    )

    with op.batch_alter_table("risk_events") as batch_op:
        batch_op.create_check_constraint(
            "ck_risk_events_risk_level",
            "risk_level IN ('low', 'moderate', 'high')",
        )


def downgrade() -> None:
    with op.batch_alter_table("risk_events") as batch_op:
        batch_op.drop_constraint("ck_risk_events_risk_level", type_="check")
    op.drop_index("ix_sensor_readings_recorded_at", table_name="sensor_readings")
    op.drop_index("ix_sensor_readings_patient_id", table_name="sensor_readings")
    op.drop_table("sensor_readings")
    with op.batch_alter_table("patients") as batch_op:
        batch_op.drop_constraint("ck_patients_gender", type_="check")
        batch_op.drop_column("gender")
