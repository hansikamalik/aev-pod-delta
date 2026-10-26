# Enterprise Sync Engine On-Call Runbook

## Overview
This runbook provides incident response procedures, connector ownership matrices, and triage workflows for the production-grade sync engine hardening and vault audit compliance framework.

---

## Connector Ownership Matrix

| Functional Domain | Assigned Connectors | Primary On-Call Team | Escalation Path |
| :--- | :--- | :--- | :--- |
| **SIEM & Log Management** | `splunk_connector`, `qradar_connector`, `elastic_connector`, `gcp_chronicle`, `microsoft_sentinel` | `@sec-siem-oncall` | Platform Engineering Lead |
| **Cloud Security & Identity** | `aws_security_hub`, `Azure_Normalization_Platform_Push`, `okta_identity`, `ping_identity` | `@sec-cloud-idp` | Cloud Security Architect |
| **Endpoint & Vulnerability** | `crowdstrike_falcon`, `paloalto_cortex`, `qualys_vulnerability`, `tenable_io` | `@sec-endpoint-ops` | SecOps Manager |
| **ITSM & Incident Response**| `servicenow_itsm`, `jira_service_desk`, `slack_notifications`, `pagerduty_incidents` | `@sec-itsm-ops` | SRE Reliability Lead |
| **Vault & Auth Core** | `cyberark_auth_module`, `cyberark-discovery-integration`, `vault-enterprise-framework` | `@sec-vault-core` | Principal Security Engineer |

---

## Incident Triage & Troubleshooting Guide

### 1. HashiCorp Vault Authentication Failures (`403 Forbidden` / `VaultTokenExpired`)
* **Symptom:** Ingestion jobs or health checks fail with token expiration or unauthorized access to secrets.
* **Triage Steps:**
  1. Verify HashiCorp Vault cluster status: `vault status`
  2. Confirm active token rotation daemon health.
  3. Force an immediate manual credential rotation and sign-off check:
     ```bash
     python3 operations/credential_rotation_signoff.py
     ```

### 2. Upstream Rate Limiting & API Throttling (`429 Too Many Requests`)
* **Symptom:** Sync jobs stall or throw exception loops when pulling large datasets (frequent with `datadog_metrics`, `tenable_io`, and `servicenow_itsm`).
* **Triage Steps:**
  1. Check connector lookback buffer configurations and backoff jitter.
  2. Inspect API quota dashboards for the affected provider.

### 3. Checkpoint Stalls & Infinite Loops
* **Symptom:** Incremental sync processes continuously pull the same high-water mark without advancing.
* **Triage Steps:**
  1. Inspect the local or distributed checkpoint store.
  2. Clear stale state for the specific connector ID to trigger a clean lookback buffer re-initialization.
  3. Re-run DR resumption verification:
     ```bash
     python3 operations/dr_resumption_test.py
     ```
