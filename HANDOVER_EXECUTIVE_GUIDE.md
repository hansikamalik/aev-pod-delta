# AEV Platform – Pod Delta (Module 4 Backend)
# Executive Handover Guide & Unified Dataset Demonstration

> **Handover Target:** Module 4 Backend Demonstration  
> **Prepared for:** Executive Leadership & Handover Review Panel  
> **Canonical Dataset:** [`data/aev_unified_handover_dataset.json`](file:///home/vikryansh/Workspace/projects/aev-pod-delta/data/aev_unified_handover_dataset.json)  
> **Master Demo Runner:** [`run_unified_handover_demo.py`](file:///home/vikryansh/Workspace/projects/aev-pod-delta/run_unified_handover_demo.py)  
> **Execution Command:** `python3 run_unified_handover_demo.py`

---

## 1. Executive Summary

As requested for the executive handover, this repository now features **one single canonical dataset** that feeds all four backend squads (Connector SDK, Integration Hub, AI Context, and AI Gateway Copilot). 

Using this single dataset, the master runner demonstrates, step-by-step, that every subsystem ingests the same data, processes it according to platform rules, and produces verified outputs.

```
                               UNIFIED DATASET
                    (data/aev_unified_handover_dataset.json)
                                      │
         ┌────────────────────────────┼────────────────────────────┐
         ▼                            ▼                            ▼
   Connector SDK               Policy Engine              AI Context Layer
  (Normalization)         (Violations & Citations)     (Semantic Vector Search)
         │                            │                            │
         └────────────────────────────┼────────────────────────────┘
                                      │
                                      ▼
                               AI Copilot Gateway
             (Guardrails ➔ Tool Dispatch ➔ Gemma LLM ➔ Audit Log)
```

---

## 2. What Is Inside the Single Unified Dataset?

Located at [`data/aev_unified_handover_dataset.json`](file:///home/vikryansh/Workspace/projects/aev-pod-delta/data/aev_unified_handover_dataset.json), the dataset models a real-world enterprise scenario (**FinTech Global Technologies**, an enterprise-tier customer with $500/mo budget cap):

1. **9 Enterprise Assets Across 7 Asset Types:**
   - `asset-001` (Compute): AI Gateway Web Core (Debian 12, port 8001)
   - `asset-002` (Database/Cache): Redis Rate Limiter cluster
   - `asset-003` (Database): PostgreSQL primary database (audit logs & pgvector)
   - `asset-004` (Compute): Kubernetes worker node (EKS us-east-1)
   - `asset-005` (Storage): AWS S3 customer PII bucket (contains critical security misconfigurations)
   - `asset-006` (Identity): Okta root admin account (missing mandatory MFA)
   - `asset-007` (Network): Perimeter gateway firewall (open SSH port 22)
   - `asset-008` (Ticket): Jira remediation ticket `SEC-4091`
   - `asset-009` (Detection): SentinelOne EDR detection `EDR-Alert-9921`
2. **5 Linked Security Exposures:**
   - Real CVE references (CVE-2024-21626, CVE-2023-5868, CWE-306, CWE-284).
3. **Multi-Factor Risk Scoring Profiles:**
   - Per-asset breakdown for all 6 platform factors (`criticality`, `threat_intel`, `severity`, `age`, `business_impact`, `likelihood`).
4. **4 Organizational Security Policies:**
   - `pol-no-public-access`, `pol-storage-encryption`, `pol-user-mfa`, `pol-firewall-admin-ports`.
5. **AI Context Vector Embeddings & User Memories:**
   - Semantic keyword catalog for natural-language search.
   - User memory notes with tenant isolation (`analyst_sarah` vs `admin_marcus`).
   - Versioned prompt templates (`asset_security_summary` v2).
6. **Guardrail Penetration Probes & PII Payloads:**
   - Real prompt injections, Unicode lookalike attacks, and sensitive PII test data.

---

## 3. How to Run the Demonstration

From the root of the repository, execute:

```bash
python3 run_unified_handover_demo.py
```

Execution takes **< 1 second**, requires **zero external dependencies** (runs on Python 3.12 stdlib), and outputs a complete terminal presentation.

---

## 4. Step-by-Step Walkthrough (What You Will See)

### Stage 1: Connector SDK & Ingestion Normalization
- **What it shows:** 9 raw multi-cloud payloads (AWS, Azure, Okta, Jira, SentinelOne) are validated against the standard SDK `Asset` schema.
- **Output:** Emits normalized assets and a signed `SyncResult` (`status: success`, `assets_discovered: 9`, `assets_pushed: 9`, `errors: []`).

### Stage 2: Enterprise Security Policy & Compliance Engine
- **What it shows:** Evaluates the unified assets against platform policies.
- **Output:** Catches **3 real policy violations** directly from the dataset:
  1. `asset-005` (S3 bucket): Violates `pol-no-public-access` and `pol-storage-encryption`.
  2. `asset-006` (Okta admin): Violates `pol-user-mfa`.
  3. `asset-007` (Edge firewall): Violates `pol-firewall-admin-ports` (SSH open to internet).
  Generates verified citation URLs for each violation.

### Stage 3: Multi-Factor Risk Scoring Engine
- **What it shows:** Calculates composite risk scores using the official 6-factor weighted algorithm:
  $$\text{Score} = \text{round}\left(\frac{\sum \text{factor}_i \times \text{weight}_i}{100}\right)$$
- **Output:** 
  - `asset-005` (S3 PII Vault): **Score 94 (Critical)**
  - `asset-001` (AI Gateway): **Score 85 (Critical)**
  - `asset-006` (Admin Account): **Score 81 (Critical)**
  - `asset-007` (Edge Firewall): **Score 83 (Critical)**
  - `asset-003` (Postgres DB): **Score 72 (High)**
  - `asset-002` (Redis Cache): **Score 35 (Medium)**

### Stage 4: AI Context Vector Search & User Memory Isolation
- **What it shows:** 
  1. **Semantic Asset Search:** Queries like `"exposed customer storage bucket with sensitive records"` rank `asset-005` #1 (similarity 0.75+).
  2. **User Memory Isolation:** Retrieves private workflow preferences for `analyst_sarah`; blocks `admin_marcus` with **HTTP 404** when attempting to view her notes.
  3. **Versioned Templates:** Demonstrates `asset_security_summary` version 2 is active without overwriting version 1.

### Stage 5: AI Gateway Guardrails & Threat Defense
- **What it shows:** 
  1. **Prompt Injection Defense:** Blocks standard attacks (`"ignore all previous instructions"`), DAN roleplay jailbreaks, and Unicode homoglyph bypasses (`\u0456gnore`).
  2. **PII Sanitization:** Replaces emails, international phone numbers, SSNs, and credit cards with `[REDACTED_...]` markers before sending to the model.

### Stage 6: AI Copilot Tool Dispatch & Workflows
- **What it shows:** Dispatches tools against the unified dataset:
  - `exposure_query(severity='critical')` returns the S3 bucket exposure.
  - `workflow_assist` triggers HashiCorp Vault credential rotation dry-run for `asset-005`.
  - `report_generate` produces executive risk posture summaries.

### Stage 7: LLM Copilot Answering & Fallback
- **What it shows:** Answers `"What is the risk score of asset-001?"`:
  - Enriches question with tool data.
  - Returns answer with mandatory disclaimer `"AI-generated, verify before acting."`
  - Attaches structured citations (`cit-risk-asset-001`, `cit-exposure-asset-001`).
  - Tracks token usage (405 tokens) and updates customer budget metrics.

### Stage 8: Audit Logging & Fact-Checking Hook
- **What it shows:** Persists interaction into the PostgreSQL `ai_interactions` schema with UUID, and receives a verified fact-check hook confirmation from AI Context.

---

## 5. Handover Verification Scorecard

At the end of execution, the runner displays this sign-off scorecard:

| Verification Area | Result | Evidence & Details |
|---|---|---|
| Connector SDK Normalization & SyncResult | **PASS** | Verified normalized Asset & SyncResult contracts |
| Multi-Cloud Integration & Policy Engine | **PASS** | Evaluated 4 policies; caught 3 real violations |
| Multi-Factor Risk Scoring Algorithm | **PASS** | Computed 6-factor composite score across assets |
| AI Context Semantic Vector Search | **PASS** | Vector search & User Memory isolation verified |
| AI Gateway Guardrails & Anti-Jailbreak | **PASS** | Blocked prompt injections & sanitized PII |
| AI Copilot Tool Dispatch & Workflows | **PASS** | Dispatched exposure_query & Vault credential rotation |
| LLM Copilot Answering & Citations | **PASS** | Answer verified with mandatory citation guarantee |
| Audit Logging & Fact-Check Webhook | **PASS** | Persisted interaction row & verified fact-check |

**ALL 8 CORE SUBSYSTEMS ARE OPERATIONAL AND PROVEN ON THE UNIFIED DATASET.**
