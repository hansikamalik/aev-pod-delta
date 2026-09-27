Markdown

# CyberArk Discovery & Integration Engine

An enterprise discovery, normalization, and automated onboarding integration engine that harvests raw unmanaged accounts across hybrid infrastructure and stages them into **CyberArk Privileged Access Manager (PVWA) Pending Accounts**.

---

## Technical Highlights
- **Pluggable Discovery Interfaces:** Modular connectors for LDAP/AD, AWS/Azure Cloud APIs, and CMDB inventory services.
- **Rules-Based Normalization Engine:** Strips service accounts/health checks via configurable JSON rules and maps OS types to valid CyberArk `PlatformID`s.
- **Enterprise Push Layer:** Performs batch HTTP REST onboarding into CyberArk PVWA with automatic session management and error resilience.
- **Built-in Mocking & Dry-Run Support:** Full execution capabilities without live PVWA infrastructure dependencies.

---

## Execution Workflow

1. **Discovery:** Scans target scopes defined under `config/discovery_targets.yaml`.
2. **Normalization:** Validates against `config/normalization_rules.json` and maps raw records to the standard CyberArk payload model.
3. **Dispatch:** Posts processed accounts to CyberArk's `/api/PendingAccounts` endpoint.

---

## Quickstart

### 1. Setup Environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
