CREATE TABLE IF NOT EXISTS ai_interactions (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    prompt TEXT,
    response TEXT,
    total_tokens INTEGER,
    cost REAL,
    citations TEXT,
    fact_check_passed BOOLEAN,
    fact_check_details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);