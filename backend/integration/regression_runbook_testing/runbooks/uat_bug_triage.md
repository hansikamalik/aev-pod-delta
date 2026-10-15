# UAT Bug Triage & Resolution Framework

## Severity Classifications

| Severity | Definition | SLA for Acknowledgment | SLA for Resolution |
| :--- | :--- | :--- | :--- |
| **Sev-1 (Critical)** | Complete sync failure across multiple connectors or active Vault token leak in logs. | 15 minutes | 2 hours |
| **Sev-2 (Major)** | Single connector ingestion failure or intermittent checkpoint corruption. | 1 hour | 4 hours |
| **Sev-3 (Moderate)** | Non-blocking telemetry warning or minor latency in health check reporting. | 4 hours | 24 hours |
| **Sev-4 (Low)** | Documentation typos, cosmetic UI log formatting quirks. | 24 hours | Next Sprint |

---

## Bug Triage Workflow

1. **Ingest & Categorize:**
   * Run the full regression test suite to isolate whether the failure is systemic or connector-specific:
     ```bash
     PYTHONPATH=. python3 -m pytest -v tests/ vault_audit_rotation/
     python3 operations/full_regression.py
     ```
2. **Audit Sanitization Check:**
   * Verify that no sensitive credentials or Vault tokens (`vault_token_*`) appear in plain text within any diagnostic logs or bug reports.
3. **Assign Ownership:**
   * Route the bug ticket to the respective team listed in the **Connector Ownership Matrix** in the On-Call Runbook.
4. **Patch & Verify:**
   * Implement fixes within `sync_engine/` or specific `connectors/` modules, execute regression scripts, and attach the JSON report sign-off to the closure ticket.
