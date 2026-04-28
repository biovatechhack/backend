-- ================================================================
-- ChronicCare Nour — Supabase schema + RLS
-- Run once in: Supabase Dashboard → SQL Editor → New query
-- ================================================================

-- ── 1. Tables ─────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS patients (
    id               TEXT PRIMARY KEY,
    display_name     VARCHAR(120)      NOT NULL,
    age              INTEGER           NOT NULL,
    bmi              DOUBLE PRECISION  NOT NULL,
    hba1c_last       DOUBLE PRECISION  NOT NULL,
    baseline_glucose DOUBLE PRECISION  NOT NULL,
    medications      JSONB             NOT NULL DEFAULT '[]',
    comorbidities    JSONB             NOT NULL DEFAULT '[]',
    doctor_email     VARCHAR(255)      NOT NULL,
    created_at       TIMESTAMPTZ       NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS conversation_logs (
    id               TEXT     PRIMARY KEY,
    patient_id       TEXT     NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    final_risk       VARCHAR(16)  NOT NULL,
    duration_seconds INTEGER  NOT NULL,
    gemini_calls     INTEGER  NOT NULL,
    pii_stripped     BOOLEAN  NOT NULL DEFAULT TRUE,
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS family_members (
    id                TEXT     PRIMARY KEY,
    patient_id        TEXT     NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    name              VARCHAR(120) NOT NULL,
    relationship      VARCHAR(64)  NOT NULL,
    phone_whatsapp    VARCHAR(32)  NOT NULL,
    alert_preferences JSONB    NOT NULL DEFAULT '[]',
    dashboard_access  VARCHAR(32)  NOT NULL DEFAULT 'full',
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS medication_logs (
    id           TEXT        PRIMARY KEY,
    patient_id   TEXT        NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    medication   VARCHAR(120) NOT NULL,
    scheduled_at TIMESTAMPTZ NOT NULL,
    taken        BOOLEAN     NOT NULL DEFAULT FALSE,
    meal_context VARCHAR(32) NOT NULL,
    confirmed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS conversation_turns (
    id                  TEXT         PRIMARY KEY,
    conversation_log_id TEXT         NOT NULL REFERENCES conversation_logs(id) ON DELETE CASCADE,
    role                VARCHAR(32)  NOT NULL,
    content_darija      VARCHAR(1000) NOT NULL,
    risk_at_turn        VARCHAR(16),
    turn_timestamp      TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS risk_events (
    id                    TEXT             PRIMARY KEY,
    patient_id            TEXT             NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    conversation_log_id   TEXT             NOT NULL REFERENCES conversation_logs(id) ON DELETE CASCADE,
    risk_level            VARCHAR(16)      NOT NULL,
    confidence            DOUBLE PRECISION NOT NULL,
    extracted_symptoms    JSONB            NOT NULL DEFAULT '[]',
    glucose_reading       DOUBLE PRECISION,
    top_decision_features JSONB            NOT NULL DEFAULT '[]',
    biometric_passed      BOOLEAN          NOT NULL DEFAULT FALSE,
    alerts_sent           JSONB            NOT NULL DEFAULT '[]',
    timestamp             TIMESTAMPTZ      NOT NULL DEFAULT now()
);

-- ── 2. Indexes ────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS ix_conversation_logs_patient_id
    ON conversation_logs (patient_id);

CREATE INDEX IF NOT EXISTS ix_family_members_patient_id
    ON family_members (patient_id);

CREATE INDEX IF NOT EXISTS ix_medication_logs_patient_id
    ON medication_logs (patient_id);

CREATE INDEX IF NOT EXISTS ix_conversation_turns_conversation_log_id
    ON conversation_turns (conversation_log_id);

CREATE INDEX IF NOT EXISTS ix_risk_events_patient_id
    ON risk_events (patient_id);

CREATE INDEX IF NOT EXISTS ix_risk_events_conversation_log_id
    ON risk_events (conversation_log_id);

-- ── 3. Row Level Security ─────────────────────────────────────────
-- Authenticated Flutter clients (anon/public key) may SELECT.
-- All writes go through the FastAPI backend (service-role key, bypasses RLS).

ALTER TABLE patients           ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversation_logs  ENABLE ROW LEVEL SECURITY;
ALTER TABLE family_members     ENABLE ROW LEVEL SECURITY;
ALTER TABLE medication_logs    ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversation_turns ENABLE ROW LEVEL SECURITY;
ALTER TABLE risk_events        ENABLE ROW LEVEL SECURITY;

CREATE POLICY "authenticated_read" ON patients
    FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "authenticated_read" ON conversation_logs
    FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "authenticated_read" ON family_members
    FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "authenticated_read" ON medication_logs
    FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "authenticated_read" ON conversation_turns
    FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "authenticated_read" ON risk_events
    FOR SELECT USING (auth.role() = 'authenticated');

-- No INSERT / UPDATE / DELETE policies.
-- Only the service-role key (backend) can write — it bypasses RLS entirely.
