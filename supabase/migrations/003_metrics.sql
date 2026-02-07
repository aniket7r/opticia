-- 003_metrics.sql
-- Enhancements for metrics and sessions tables
-- Run this in the Supabase SQL Editor after 001 and 002

-- Add additional index for date range queries on metrics
CREATE INDEX IF NOT EXISTS idx_metrics_recorded_at
ON metrics (recorded_at DESC);

-- Enable RLS on tables
ALTER TABLE metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;

-- Create policies for service role access (backend uses service key)
DO $$
BEGIN
    -- Drop existing policies if they exist to avoid errors
    DROP POLICY IF EXISTS "Service role can manage metrics" ON metrics;
    DROP POLICY IF EXISTS "Service role can manage sessions" ON sessions;
EXCEPTION
    WHEN undefined_object THEN NULL;
END $$;

CREATE POLICY "Service role can manage metrics" ON metrics
    FOR ALL
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Service role can manage sessions" ON sessions
    FOR ALL
    USING (true)
    WITH CHECK (true);

-- Add cleanup function for old metrics (older than 30 days)
CREATE OR REPLACE FUNCTION cleanup_old_metrics()
RETURNS void AS $$
BEGIN
    DELETE FROM metrics WHERE recorded_at < NOW() - INTERVAL '30 days';
    DELETE FROM sessions WHERE created_at < NOW() - INTERVAL '30 days';
END;
$$ LANGUAGE plpgsql;

-- Add comments
COMMENT ON TABLE metrics IS 'Operational metrics for admin dashboard - tracks sessions, tokens, costs, errors, etc.';
COMMENT ON TABLE sessions IS 'Session metadata for tracking and analytics';
