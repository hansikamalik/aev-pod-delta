# Vendor Sandbox Validation Trials & Operational Runbook

> **Target Audience:** Integration Engineers, Squad 4 Leads, Platform Operations  
> **Status:** Stage 2 Operational Guide | **Scope:** Live & Mock Sandbox Validation

This document establishes the official test and verification runbook for live third-party vendor sandbox trials across three high-value enterprise platforms:
1. **Atlassian Jira Cloud**
2. **Microsoft Azure Sandbox**
3. **GitHub Enterprise / GitHub App**

---

## 1. Objectives & Compliance Boundary

The canonical `ConnectorSDK` (`AsyncConnector` / `Connector`) requires validation against realistic external vendor environments to verify:
- **Authentication Handshake & Token Refresh:** Handling OAuth 2.0 / PAT expiry and rotation.
- **Pagination & Cursor Progression:** Streaming large asset catalogs without memory leaks.
- **Rate-Limiting & Backoff:** Adhering to vendor HTTP 429 and `Retry-After` headers.
- **Data Normalization:** Converting raw API JSON payloads into unified `Asset` schema instances (`AssetType.HOST`, `APPLICATION`, `USER`, etc.).

---

## 2. Platform 1: Atlassian Jira Cloud

### Sandbox Credential Requirements
- **Endpoint URL:** `https://your-org.atlassian.net`
- **Username / Email:** `service-account@your-org.com`
- **API Token:** Generated from Atlassian Account Security Portal (PAT)
- **Required Scopes:** `read:jira-work`, `read:jira-user`

### Live Sync Execution Procedure
```bash
# Trigger on-demand discovery sync via Integration Service API
curl -X POST http://localhost:8000/api/v1/integrations/jira-cloud-01/sync \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>"
```

### Rate Limits & Mitigation Strategy
- **Atlassian Limit:** Tier 1 REST endpoints limit burst to 100 requests/minute.
- **Mitigation:** The connector uses exponential backoff with jitter up to 5 attempts when HTTP 429 is received. Checkpoints save the JQL `startAt` cursor so syncs resume seamlessly without duplicating assets.

---

## 3. Platform 2: Microsoft Azure Sandbox

### Sandbox Credential Requirements
- **Tenant ID:** `AZURE_TENANT_ID`
- **Client ID (App ID):** `AZURE_CLIENT_ID`
- **Client Secret:** `AZURE_CLIENT_SECRET`
- **Subscription ID:** `AZURE_SUBSCRIPTION_ID`
- **Required RBAC Role:** `Reader` across target Resource Groups / Subscriptions.

### Discovered Asset Types
- `Microsoft.Compute/virtualMachines` -> `AssetType.HOST`
- `Microsoft.Network/networkSecurityGroups` -> `AssetType.NETWORK`
- `Microsoft.Storage/storageAccounts` -> `AssetType.STORAGE`

### Rate Limits & Mitigation Strategy
- **ARM Throttling Limit:** Azure Resource Manager throttles read calls at 12,000 requests/hour per subscription.
- **Mitigation:** Batch resource queries via Azure Resource Graph (ARG) where possible rather than per-resource ARM calls. Synchronous checkpoints store the `$skipToken` cursor in PostgreSQL.

---

## 4. Platform 3: GitHub Enterprise / GitHub App

### Sandbox Credential Requirements
- **GitHub Organization:** `GITHUB_ORG`
- **App ID & Private Key:** `GITHUB_APP_ID`, `GITHUB_PRIVATE_KEY` (PEM format)
- **Installation ID:** `GITHUB_INSTALLATION_ID`
- **Permissions:** `Administration: read`, `Vulnerabilities: read`, `Metadata: read`

### Discovered Asset Types
- Organization Repositories -> `AssetType.CODE_REPOSITORY`
- Dependabot & Secret Alerts -> `AssetType.VULNERABILITY`
- Org Members & Collaborators -> `AssetType.IDENTITY`

### Rate Limits & Mitigation Strategy
- **GitHub Rate Limit:** 5,000 requests/hour for GitHub App installations.
- **Mitigation:** Inspect `X-RateLimit-Remaining` and `X-RateLimit-Reset` response headers on every response. Connector automatically pauses when remaining calls drop below 50.

---

## 5. Verification & Test Execution

Run the connector test suite locally against vendor fixtures and mocks:
```bash
# 1. Jira Connector tests
PYTHONPATH=backend/connector-sdk python3 -m pytest backend/connector-sdk/tests/test_jira_connector.py -v

# 2. Azure Normalization tests
PYTHONPATH="backend/integration/Azure Normalizaton and Platform Push" python3 -m pytest "backend/integration/Azure Normalizaton and Platform Push/tests" -v

# 3. GitHub Connector tests
PYTHONPATH="backend/integration/connector-github/connector-github" python3 -m pytest "backend/integration/connector-github/connector-github/tests" -v
```
