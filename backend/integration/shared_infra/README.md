# Shared Integration Infrastructure
**Owner:** Abhiram

Three pieces used by every connector:
- **Secrets Vault** (`secrets_vault.py`) — generic credential retrieval, so
  no connector hardcodes credentials. Retries on transient vault outages,
  caches resolved secrets.
- **Cron Scheduler** (`scheduler.py`) — interval-based job triggering.
- **Distributed Lock** (`distributed_lock.py`) — TTL-based lock so the
  scheduler never runs the same job twice concurrently (duplicate-run
  prevention).

Developed and tested against `dummy_connector.py`, per the parallel-work
rule: this module never waits on the real Azure or Splunk connectors.

## Files
- `src/secrets_vault.py`, `src/scheduler.py`, `src/distributed_lock.py`
- `src/dummy_connector.py` — stand-in connector for infra testing
- `tests/test_shared_infra.py` — unit tests for all three pieces

## Run
```bash
pip install -r requirements.txt
pytest tests/ -v
```

## Usage
```python
from secrets_vault import SecretsVaultClient, MockVaultBackend
from distributed_lock import DistributedLock, MockLockBackend
from scheduler import CronScheduler
from dummy_connector import DummyConnector

vault = SecretsVaultClient(MockVaultBackend(seed_secrets={"splunk/token": "abc"}))
lock = DistributedLock(MockLockBackend())
scheduler = CronScheduler(lock)

connector = DummyConnector()
connector.configure(vault.get_credential("splunk/token"))
scheduler.register_job("sync_job", interval_seconds=300, fn=lambda: connector.sync())
scheduler.tick()
```
