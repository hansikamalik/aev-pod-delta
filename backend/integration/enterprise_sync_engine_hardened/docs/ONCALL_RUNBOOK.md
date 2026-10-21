# Enterprise Sync Engine: On-Call Runbook

## 1. Primary Triage Escalation Matrix

| Domain / Connectors | Owner Team | Health Method | Common Failure Cause | Action Plan |
| :--- | :--- | :--- | :--- | :--- |
| **Microsoft Identity** (`active-directory-connector`, `AEV-microsoft-entra-id-connector`, `microsoft-defender-connector`) | Team Identity | `check_health()` | Expired Azure Client Secret or incorrect tenant ID. | Verify secrets in Vault; rotate client credential if expired. |
| **DevOps** (`connector-github`, `connector-gitlab`, `connector-sentinelone`) | Team SecOps | `check_health()` | API Rate limit reached or invalidated PAT token. | Check token rate limits; update PAT in Vault. |
| **SIEM** (`qradar_connector`, `elastic_connector`, `splunk_connector`) | Team SIEM | `health_check()` | Endpoint HTTP timeout or cluster authentication failure. | Confirm network routing/VPN to SIEM host; test API token. |
| **ITSM** (`servicenow-connector`, `aev-connector-webhook`, `connector-microsoft-sentinel`) | Team Platform | `check_health()` | Webhook unreachable or missing connector class. | Confirm HTTP endpoint responder is up; check payload schema. |
| **PAM** (`cyberark-discovery-integration`, `cyberark_auth_module`, `vault-enterprise-framework`) | Team PAM | `health_check()` | Vault unseal state locked or relative import errors. | Run `unseal_vault.sh`; ensure package imports are absolute. |
| **Workspace** (`google-workspace-connector`, `google-workspace-auth`, `microsoft365-connector`) | Team Workspace | `check_health()` | Missing `googleapiclient` dependency or OAuth scope drop. | Ensure dependencies are installed; re-verify workspace scopes. |
| **Cloud Extras** (`azure_connector`, `okta_connector`, `jira_connector`, etc.) | Team Cloud Integrations | `check_health()` | Coroutine unawaited in async tests or missing SDK path. | Ensure `await` is called on sync coroutines; verify PYTHONPATH. |
