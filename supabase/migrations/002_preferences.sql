-- 002_preferences.sql
-- User preferences table

CREATE TABLE IF NOT EXISTS preferences (
    session_id TEXT PRIMARY KEY,
    preferences JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for faster lookups
CREATE INDEX IF NOT EXISTS idx_preferences_session_id ON preferences(session_id);

-- Update trigger for updated_at
CREATE OR REPLACE FUNCTION update_preferences_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS preferences_updated_at ON preferences;
CREATE TRIGGER preferences_updated_at
    BEFORE UPDATE ON preferences
    FOR EACH ROW
    EXECUTE FUNCTION update_preferences_timestamp();
