-- ═══════════════════════════════════════════════════════════════
--  NexusSwarm — PostgreSQL Schema
--  Runs automatically on first container start
-- ═══════════════════════════════════════════════════════════════

-- ─── EXTENSIONS ─────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ─── TASKS ──────────────────────────────────────────────────────
-- A "task" is a top-level user submission (e.g. "Build a REST API")
CREATE TABLE IF NOT EXISTS tasks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title           TEXT NOT NULL,
    description     TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending',
        -- pending | planning | engineering | qa | security | devops | complete | failed
    priority        INTEGER DEFAULT 1,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ,
    metadata        JSONB DEFAULT '{}'
);

-- ─── PIPELINES ──────────────────────────────────────────────────
-- One row per pipeline per task. Tracks health + progress.
CREATE TABLE IF NOT EXISTS pipelines (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id         UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
        -- planning | engineering | qa | security | devops
    status          TEXT NOT NULL DEFAULT 'idle',
        -- idle | active | blocked | done | failed
    progress        INTEGER DEFAULT 0 CHECK (progress BETWEEN 0 AND 100),
    manager_agent   TEXT NOT NULL,
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    error_message   TEXT,
    metadata        JSONB DEFAULT '{}'
);

-- ─── AGENT LOGS ─────────────────────────────────────────────────
-- Full immutable audit trail of every agent action
CREATE TABLE IF NOT EXISTS agent_logs (
    id              BIGSERIAL PRIMARY KEY,
    task_id         UUID REFERENCES tasks(id) ON DELETE SET NULL,
    pipeline_name   TEXT,
    agent_name      TEXT NOT NULL,
    agent_level     TEXT NOT NULL,
        -- orchestrator | manager | worker
    parent_manager  TEXT,
    event_type      TEXT NOT NULL,
        -- agent_action | pipeline_update | conflict | escalation | complete | error
    message         TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'in_progress',
        -- in_progress | done | error | blocked
    payload         JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── PIPELINE HEALTH ────────────────────────────────────────────
-- Snapshot of pipeline health — updated by Head Orchestrator
CREATE TABLE IF NOT EXISTS pipeline_health (
    id              BIGSERIAL PRIMARY KEY,
    task_id         UUID REFERENCES tasks(id) ON DELETE CASCADE,
    pipeline_name   TEXT NOT NULL,
    health_status   TEXT NOT NULL DEFAULT 'healthy',
        -- healthy | warning | critical
    failed_retries  INTEGER DEFAULT 0,
    stuck_agents    INTEGER DEFAULT 0,
    token_usage     INTEGER DEFAULT 0,
    latency_ms      INTEGER DEFAULT 0,
    notes           TEXT,
    recorded_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── TASK OUTPUTS ───────────────────────────────────────────────
-- Final outputs generated per task (code, reports, test results)
CREATE TABLE IF NOT EXISTS task_outputs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id         UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    output_type     TEXT NOT NULL,
        -- code | test_results | security_report | deployment_config | summary
    pipeline_name   TEXT NOT NULL,
    content         TEXT NOT NULL,
    file_path       TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── CONFLICTS ──────────────────────────────────────────────────
-- Conflicts escalated to Head Orchestrator for resolution
CREATE TABLE IF NOT EXISTS conflicts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id         UUID REFERENCES tasks(id) ON DELETE CASCADE,
    raised_by       TEXT NOT NULL,   -- which manager raised it
    blocked_by      TEXT NOT NULL,   -- which manager is blocking
    reason          TEXT NOT NULL,
    resolution      TEXT,
    status          TEXT NOT NULL DEFAULT 'open',
        -- open | resolved | escalated_to_human
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at     TIMESTAMPTZ
);

-- ─── INDEXES ────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_agent_logs_task_id   ON agent_logs(task_id);
CREATE INDEX IF NOT EXISTS idx_agent_logs_created   ON agent_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_pipelines_task_id    ON pipelines(task_id);
CREATE INDEX IF NOT EXISTS idx_task_outputs_task_id ON task_outputs(task_id);
CREATE INDEX IF NOT EXISTS idx_conflicts_task_id    ON conflicts(task_id);

-- ─── AUTO-UPDATE updated_at ─────────────────────────────────────
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tasks_updated_at
    BEFORE UPDATE ON tasks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ─── SEED: Default pipeline names ───────────────────────────────
-- (Just a reference comment — pipelines are created per-task at runtime)
-- planning | engineering | qa | security | devops

-- ─── EVALUATIONS ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS evaluations (
    id                      SERIAL PRIMARY KEY,
    task_id                 UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    agent_name              TEXT NOT NULL,
    accuracy_score          DOUBLE PRECISION,
    completeness_score      DOUBLE PRECISION,
    security_score          DOUBLE PRECISION,
    maintainability_score   DOUBLE PRECISION,
    scalability_score       DOUBLE PRECISION,
    overall_score           DOUBLE PRECISION,
    strengths               JSONB DEFAULT '[]',
    weaknesses              JSONB DEFAULT '[]',
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── BENCHMARK RESULTS ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS benchmark_results (
    id                      SERIAL PRIMARY KEY,
    benchmark_name          TEXT NOT NULL,
    task_id                 UUID REFERENCES tasks(id) ON DELETE SET NULL,
    pass                    BOOLEAN NOT NULL DEFAULT FALSE,
    score                   DOUBLE PRECISION,
    execution_time          DOUBLE PRECISION,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_evaluations_task_id ON evaluations(task_id);
CREATE INDEX IF NOT EXISTS idx_benchmark_results_task_id ON benchmark_results(task_id);

