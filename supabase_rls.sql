-- Row Level Security policies for ChronicCare Nour
-- Apply in the Supabase SQL editor (Database → SQL editor).
--
-- Rule: Flutter clients (authenticated via Supabase Auth) may READ any row.
--       All writes must go through the FastAPI backend using the service-role key,
--       which bypasses RLS entirely.

-- Enable RLS on every clinical table
ALTER TABLE patients          ENABLE ROW LEVEL SECURITY;
ALTER TABLE family_members    ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversation_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversation_turns ENABLE ROW LEVEL SECURITY;
ALTER TABLE risk_events       ENABLE ROW LEVEL SECURITY;
ALTER TABLE medication_logs   ENABLE ROW LEVEL SECURITY;

-- Authenticated users (Flutter) may SELECT
CREATE POLICY "allow_authenticated_read" ON patients
    FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "allow_authenticated_read" ON family_members
    FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "allow_authenticated_read" ON conversation_logs
    FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "allow_authenticated_read" ON conversation_turns
    FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "allow_authenticated_read" ON risk_events
    FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "allow_authenticated_read" ON medication_logs
    FOR SELECT USING (auth.role() = 'authenticated');

-- No INSERT/UPDATE/DELETE policies → only service-role (backend) can write
