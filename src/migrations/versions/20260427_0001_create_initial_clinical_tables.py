"""create initial chroniccare tables from architecture schemas"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260427_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "patients",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("age", sa.Integer(), nullable=False),
        sa.Column("bmi", sa.Float(), nullable=False),
        sa.Column("hba1c_last", sa.Float(), nullable=False),
        sa.Column("baseline_glucose", sa.Float(), nullable=False),
        sa.Column("medications", sa.JSON(), nullable=False),
        sa.Column("comorbidities", sa.JSON(), nullable=False),
        sa.Column("doctor_email", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "conversation_logs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("patient_id", sa.String(length=36), nullable=False),
        sa.Column("final_risk", sa.String(length=16), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=False),
        sa.Column("gemini_calls", sa.Integer(), nullable=False),
        sa.Column("pii_stripped", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_conversation_logs_patient_id", "conversation_logs", ["patient_id"], unique=False)
    op.create_table(
        "family_members",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("patient_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("relationship", sa.String(length=64), nullable=False),
        sa.Column("phone_whatsapp", sa.String(length=32), nullable=False),
        sa.Column("alert_preferences", sa.JSON(), nullable=False),
        sa.Column("dashboard_access", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_family_members_patient_id", "family_members", ["patient_id"], unique=False)
    op.create_table(
        "medication_logs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("patient_id", sa.String(length=36), nullable=False),
        sa.Column("medication", sa.String(length=120), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("taken", sa.Boolean(), nullable=False),
        sa.Column("meal_context", sa.String(length=32), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_medication_logs_patient_id", "medication_logs", ["patient_id"], unique=False)
    op.create_table(
        "conversation_turns",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("conversation_log_id", sa.String(length=36), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("content_darija", sa.String(length=1000), nullable=False),
        sa.Column("risk_at_turn", sa.String(length=16), nullable=True),
        sa.Column("turn_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["conversation_log_id"], ["conversation_logs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_conversation_turns_conversation_log_id",
        "conversation_turns",
        ["conversation_log_id"],
        unique=False,
    )
    op.create_table(
        "risk_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("patient_id", sa.String(length=36), nullable=False),
        sa.Column("conversation_log_id", sa.String(length=36), nullable=False),
        sa.Column("risk_level", sa.String(length=16), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("extracted_symptoms", sa.JSON(), nullable=False),
        sa.Column("glucose_reading", sa.Float(), nullable=True),
        sa.Column("top_decision_features", sa.JSON(), nullable=False),
        sa.Column("biometric_passed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("alerts_sent", sa.JSON(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["conversation_log_id"], ["conversation_logs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_risk_events_conversation_log_id", "risk_events", ["conversation_log_id"], unique=False)
    op.create_index("ix_risk_events_patient_id", "risk_events", ["patient_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_risk_events_patient_id", table_name="risk_events")
    op.drop_index("ix_risk_events_conversation_log_id", table_name="risk_events")
    op.drop_table("risk_events")
    op.drop_index("ix_conversation_turns_conversation_log_id", table_name="conversation_turns")
    op.drop_table("conversation_turns")
    op.drop_index("ix_medication_logs_patient_id", table_name="medication_logs")
    op.drop_table("medication_logs")
    op.drop_index("ix_family_members_patient_id", table_name="family_members")
    op.drop_table("family_members")
    op.drop_index("ix_conversation_logs_patient_id", table_name="conversation_logs")
    op.drop_table("conversation_logs")
    op.drop_table("patients")
