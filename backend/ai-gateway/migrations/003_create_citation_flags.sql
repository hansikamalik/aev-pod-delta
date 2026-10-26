CREATE TABLE IF NOT EXISTS citation_flags (
    id SERIAL PRIMARY KEY,
    interaction_id TEXT NOT NULL,
    citation_id TEXT NOT NULL,
    reason TEXT NOT NULL,
    flagged_by TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_citation_flags_interaction_id
    ON citation_flags (interaction_id);
