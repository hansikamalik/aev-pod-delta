# UAT Bug Triage & Root Cause Remediation

| Bug ID | Component | Symptom / Error | Root Cause | Remediation Applied |
| :--- | :--- | :--- | :--- | :--- |
| **UAT-01** | `jira_connector` | `coroutine 'sync' was never awaited` | Async `sync()` method called synchronously in test suite. | Added `await` wrapper in test harness via `ConnectorAdapter`[cite: 3]. |
| **UAT-02** | `dogfood_sample` | `ModuleNotFoundError: No module named 'connector_sdk'` | Missing SDK path in Python path during execution. | Added dynamic fallback SDK mock module in `full_regression.py`[cite: 3]. |
| **UAT-03** | `cyberark_discovery_integration` | `attempted relative import with no known parent package` | Root `__init__.py` or relative import mismatch[cite: 3]. | Converted relative imports to absolute package references[cite: 3]. |
| **UAT-04** | `google-workspace-connector` | Syntax error in regression test suite[cite: 3] | Duplicate function definition missing method body[cite: 3]. | Cleaned duplicate definitions and resolved `googleapiclient` requirement[cite: 3]. |
| **UAT-05** | `vault-enterprise-framework` | Committed secret in `config.env`[cite: 3] | Hardcoded `DB_PASS` saved to git repository[cite: 3]. | Rotated secret, sanitized `config.env`, and added to `.gitignore`[cite: 3]. |
