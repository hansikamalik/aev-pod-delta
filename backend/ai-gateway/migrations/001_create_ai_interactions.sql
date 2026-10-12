
CREATE TABLE IF NOT EXISTS ai_interactions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    prompt TEXT NOT NULL,
    response TEXT NOT NULL,
    total_tokens INTEGER NOT NULL DEFAULT 0,
    cost DOUBLE PRECISION NOT NULL DEFAULT 0,
    citations JSONB NOT NULL DEFAULT '[]'::jsonb,
    fact_check_passed BOOLEAN,
    fact_check_details TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ai_interactions_created_at
    ON ai_interactions (created_at);

CREATE INDEX IF NOT EXISTS idx_ai_interactions_user_id
    ON ai_interactions (user_id);
