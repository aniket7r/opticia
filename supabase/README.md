# Supabase Setup

## Quick Start

1. Create a new Supabase project at https://supabase.com

2. Go to SQL Editor and run the migration:
   ```sql
   -- Copy contents of migrations/001_initial_schema.sql
   ```

3. Get your credentials from Project Settings > API:
   - `SUPABASE_URL`: Project URL
   - `SUPABASE_ANON_KEY`: anon/public key

4. Add to `backend/.env`:
   ```
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_ANON_KEY=your_anon_key_here
   ```

## Schema

### sessions
Tracks session metadata for metrics. No PII stored.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| created_at | TIMESTAMPTZ | Session start |
| ended_at | TIMESTAMPTZ | Session end (null if active) |
| status | TEXT | active, ended, error |
| tool_calls_count | INT | Number of tool invocations |
| fallback_activations | INT | Times fallback chain triggered |
| total_tokens | INT | Total tokens used |

### metrics
Aggregated metrics for admin dashboard.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| recorded_at | TIMESTAMPTZ | When recorded |
| metric_type | TEXT | session_cost, token_usage, response_latency |
| value | NUMERIC | Metric value |
| metadata | JSONB | Additional context (session_id, etc.) |
