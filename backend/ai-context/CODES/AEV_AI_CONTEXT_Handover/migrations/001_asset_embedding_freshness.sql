-- Apply once to the existing PostgreSQL database before deploying this code.
-- Back up the database first. Existing asset embeddings remain unchanged.
ALTER TABLE assets ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ;
ALTER TABLE assets ADD COLUMN IF NOT EXISTS embedding_updated_at TIMESTAMPTZ;
UPDATE assets SET updated_at = created_at WHERE updated_at IS NULL;
-- Do not infer when old embeddings were created. embedding_updated_at intentionally
-- stays NULL until app updates or generate_asset_embeddings.py refreshes the vector.
