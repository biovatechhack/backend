-- ================================================================
-- ChronicCare Nour — Doctor Schema (Simplified)
-- ================================================================

-- ── 1. Doctors ────────────────────────────────────────────────────
CREATE TABLE doctors (
    id                  TEXT         PRIMARY KEY,
    name                VARCHAR(255) NOT NULL,
    email               VARCHAR(255) NOT NULL UNIQUE,
    specialty           VARCHAR(120) NOT NULL,
    clinic              VARCHAR(255),
    phone               VARCHAR(32),
    bio                 TEXT,    profile_picture_url TEXT,
    experience_years    INTEGER      DEFAULT 0,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- ── 2. Link Patients to Doctors ──────────────────────────────────
-- Updates the existing patients table to use a proper foreign key reference.
-- Note: Re-running this on a table that already has the column will error.
-- You can use: ALTER TABLE patients ADD COLUMN IF NOT EXISTS doctor_id TEXT;
ALTER TABLE patients ADD COLUMN IF NOT EXISTS doctor_id TEXT REFERENCES doctors(id) ON DELETE SET NULL;

-- ── 3. Doctor-Patient View ────────────────────────────────────────
CREATE OR REPLACE VIEW doctor_patients_view AS
SELECT 
    d.id AS doctor_id,
    d.name AS doctor_name,
    d.specialty,
    p.id AS patient_id,
    p.display_name AS patient_name,
    p.age,
    p.gender
FROM doctors d
JOIN patients p ON d.id = p.doctor_id;

-- ── 4. RLS Policies (Supabase) ────────────────────────────────────
ALTER TABLE doctors ENABLE ROW LEVEL SECURITY;

CREATE POLICY "allow_authenticated_read" ON doctors
    FOR SELECT USING (auth.role() = 'authenticated');
