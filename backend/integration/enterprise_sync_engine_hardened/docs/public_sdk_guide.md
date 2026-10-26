### `docs/public_sdk_guide.md`
```markdown
# Public Connector SDK Developer Guide

## Core Contract Requirements
Every connector extends `BaseConnector`[cite: 3] and implements:
* `discover()`: Reads normalized assets.
* `ingest(assets)`: Pushes assets to platform.
* `sync()`: Orchestrates discover, deduplication, and ingestion.
* `health_check()`: Validates vendor connectivity.
* `get_config_schema()`: Describes configuration fields (secrets marked `secret: true`).
