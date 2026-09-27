# Elasticsearch Connector

A production-ready Elasticsearch connector implementing the Connector SDK Contract v2.

## File Structure

```text
elastic_connector/
├── __init__.py
├── connector.py
├── client.py
├── config.py
├── models.py
├── pyproject.toml
├── README.md
└── tests/
    ├── __init__.py
    ├── test_discover.py
    ├── test_health.py
    ├── test_ingest.py
    └── test_sync.py
