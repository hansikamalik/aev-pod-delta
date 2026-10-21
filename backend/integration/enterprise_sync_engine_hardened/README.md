# Enterprise Sync Engine Hardened Platform

This repository houses the hardened enterprise sync engine, standardized connector contract[cite: 3], Vault credential management, monitoring telemetry, and automated regression test runners for all integrations.

## Quick Start
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -v
python3 operations/full_regression.py
python3 scripts/benchmark_sync.py

export PYTHONPATH=.

# 1. Run only per-connector health check triage
python3 operations/runbook.py --health-check

# 2. Run Vault credential audit
python3 operations/runbook.py --audit-vault

# 3. Execute full dynamic regression & generate evidence
python3 operations/runbook.py --regression

# 4. Execute the entire runbook sequence end-to-end
python3 operations/runbook.py --all
