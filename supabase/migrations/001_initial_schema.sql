-- 001_initial_schema.sql
-- Initial database schema for gemini3

-- Session metadata (ephemeral, for metrics only)
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    status TEXT DEFAULT 'active',
    tool_calls_count INT DEFAULT 0,
    fallback_activations INT DEFAULT 0,
    total_tokens INT DEFAULT 0
);

-- Metrics aggregation
CREATE TABLE metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recorded_at TIMESTAMPTZ DEFAULT NOW(),
    metric_type TEXT NOT NULL,
    value NUMERIC NOT NULL,
    metadata JSONB
);

-- Indexes for query performance
CREATE INDEX idx_sessions_created_at ON sessions(created_at);
CREATE INDEX idx_sessions_status ON sessions(status);
CREATE INDEX idx_metrics_type_recorded ON metrics(metric_type, recorded_at);

-- Row Level Security (disabled for MVP, enable in production)
-- ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE metrics ENABLE ROW LEVEL SECURITY;
