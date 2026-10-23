# AEV Platform – Pod Delta (Module 4 Backend)
# Team Onboarding & Handover Quickstart Guide

> **Audience:** Incoming Engineers, Squad Leads, and Technical Stakeholders  
> **Purpose:** Detailed operational explanation of the Handover Dataset, Demo Runner, Presentation Guide, and Cross-Service Data Architecture (Points 3, 4, 5, and 6).  
> **Repository:** `aev-pod-delta` (Branch: `develop`)

---

## Quick Reference: Core Handover Files

| Asset | File Path | Primary Function |
|---|---|---|
| **Unified Dataset** | [`data/aev_unified_handover_dataset.json`](file:///home/vikryansh/Workspace/projects/aev-pod-delta/data/aev_unified_handover_dataset.json) | Single source of truth containing all multi-cloud assets, CVEs, policies, risk scores, and AI memory. |
| **Demo Runner** | [`run_unified_handover_demo.py`](file:///home/vikryansh/Workspace/projects/aev-pod-delta/run_unified_handover_demo.py) | Standalone test runner executing an end-to-end walkthrough of all 8 platform subsystems in < 0.1s. |
| **Executive Guide** | [`HANDOVER_EXECUTIVE_GUIDE.md`](file:///home/vikryansh/Workspace/projects/aev-pod-delta/HANDOVER_EXECUTIVE_GUIDE.md) | Presentation runbook and talking points for stakeholders, leadership, and client handovers. |
| **Gap Roadmap** | [`PROJECT_COMPLETION_AND_DEPLOYMENT_ROADMAP.md`](file:///home/vikryansh/Workspace/projects/aev-pod-delta/PROJECT_COMPLETION_AND_DEPLOYMENT_ROADMAP.md) | Comprehensive engineering gap analysis, test audit, and 8-week path to production. |

---

## 1. Deep Dive: The Single Unified Dataset (Point 3)

### Why It Was Created
Previously, squads relied on disconnected mock snippets (`backend/ai-gateway/app/mock_data.py` had 3 assets, `connector_sandbox` had separate fixtures, and AI Context had isolated database seeds). 

The unified dataset at `data/aev_unified_handover_dataset.json` brings all 4 squads into a single cohesive enterprise environment (**FinTech Global Technologies**, an enterprise customer with a $500 monthly budget cap).

### Dataset Schema Breakdown

```
data/aev_unified_handover_dataset.json
├── metadata              ➔ Dataset versioning, schema, timestamp
├── organization          ➔ Org ID, tier (enterprise), budget cap ($500), rate limit rules
├── assets                ➔ 9 normalized infrastructure assets spanning 7 core types
├── risk_factor_profiles  ➔ 6-factor weightings & values (0-100) per asset
├── exposures             ➔ Active CVEs & vulnerability links per asset
├── policy_rules          ➔ Enterprise compliance rules (encryption, public access, MFA, ports)
├── workflows             ➔ Automated runbooks (credential rotation, quarantine, rescanning)
├── integrations          ➔ 8 external vendor health statuses (Azure, Okta, Splunk, Jira, etc.)
├── ai_context_store      ➔ Semantic keywords, isolated user memories, prompt templates v1/v2
└── sample_eval_prompts   ➔ Pen-test injection attacks, PII strings, and valid analyst questions
```

### Key Entities in the Dataset:
1. **The 9 Multi-Cloud Assets:**
   - `asset-001` (`compute` · Azure): AI Gateway FastAPI core.
   - `asset-002` (`database` · AWS): Redis in-memory rate-limiter cluster.
   - `asset-003` (`database` · Azure): PostgreSQL primary storage (audit log + pgvector).
   - `asset-004` (`compute` · AWS): EKS Kubernetes worker node.
   - `asset-005` (`storage` · AWS): `s3-customer-pii-vault` (intentionally configured with public read access & no encryption to trigger policy alerts).
   - `asset-006` (`identity` · Okta): Privileged `user-admin-root` (intentionally missing MFA to test compliance rules).
   - `asset-007` (`network` · Azure): Edge firewall (intentionally has SSH port 22 exposed to 0.0.0.0/0).
   - `asset-008` (`ticket` · Jira): Remediation ticket `SEC-4091`.
   - `asset-009` (`detection` · SentinelOne): Endpoint threat detection `EDR-Alert-9921`.
2. **The 4 Security Policies:**
   - `pol-no-public-access`: S3 buckets and databases must not be public.
   - `pol-storage-encryption`: Data stores must have at-rest encryption enabled.
   - `pol-user-mfa`: Privileged user accounts must enforce MFA.
   - `pol-firewall-admin-ports`: Management ports (SSH/RDP) must not be internet-exposed.

### How Developers Can Add New Data
To add a new asset or policy, open `data/aev_unified_handover_dataset.json` and append an object following the standard schema. The demo runner and mock loaders automatically adapt to new entries without code changes.

---

## 2. Deep Dive: The Master Demonstration Runner (Point 4)

### Purpose & Design
The script `run_unified_handover_demo.py` is an executable proof that the platform's core algorithms, contracts, and guardrails function properly together. It requires **only Python 3.12 standard library**—it runs anywhere without Docker or live databases.

### How to Run
```bash
python3 run_unified_handover_demo.py
```

### The 8 Verification Stages Executed:

```
┌────────────────────────────────────────────────────────────────────────┐
│ run_unified_handover_demo.py Execution Flow                            │
├─────────┬───────────────────────────────────┬──────────────────────────┤
│ Stage 1 │ Connector SDK Normalization       │ Ingests 9 assets -> SDK  │
│ Stage 2 │ Enterprise Policy Engine          │ Evaluates 4 policies     │
│ Stage 3 │ Multi-Factor Risk Scoring         │ Computes 6-factor score  │
│ Stage 4 │ AI Context Vector & Memory        │ Semantic search & memory │
│ Stage 5 │ AI Gateway Guardrails             │ Injections & PII filter  │
│ Stage 6 │ AI Copilot Tool Dispatch          │ Exposures & Vault run    │
│ Stage 7 │ Gemma Answering & Fallback        │ Citations, tokens, cost  │
│ Stage 8 │ Audit Logging & Fact-Checking     │ SQL table & Webhook      │
└─────────┴───────────────────────────────────┴──────────────────────────┘
```

1. **Stage 1 (Connector SDK):** Validates raw payloads against the SDK `Asset` schema and outputs a signed `SyncResult` (`status: success`, `duration_seconds: 0.124`).
2. **Stage 2 (Compliance):** Catches **4 real non-compliance violations** (`asset-005` public S3 & unencrypted; `asset-006` missing MFA; `asset-007` open SSH) and generates policy citation URLs.
3. **Stage 3 (Risk Scoring):** Applies the official weighted formula:
   $$\text{Score} = \text{round}\left(\frac{\text{Crit}\times 25 + \text{Threat}\times 20 + \text{Sev}\times 20 + \text{Age}\times 10 + \text{Impact}\times 15 + \text{Like}\times 10}{100}\right)$$
   Categorizes assets into bands (`Critical`, `High`, `Medium`).
4. **Stage 4 (AI Context):** 
   - Runs semantic search: Query *"exposed customer storage"* ranks `asset-005` #1 (similarity 0.75+).
   - Verifies **User Memory Isolation**: `analyst_sarah` reads her notes; `admin_marcus` receives **HTTP 404** when trying to view Sarah's notes.
5. **Stage 5 (Guardrails):** 
   - Blocks prompt injection attacks (including Unicode homoglyphs like `\u0456gnore`).
   - Redacts all 4 PII types (email, phone, SSN, credit cards) to `[REDACTED_...]`.
6. **Stage 6 (Copilot Tools):** Dispatches `exposure_query`, triggers HashiCorp Vault credential rotation dry-run (`workflow_assist`), and outputs executive reports.
7. **Stage 7 (Copilot Response):** Generates structured LLM response with mandatory disclaimer (`"AI-generated, verify before acting."`), token counting, budget cap accounting, and structured citations (`cit-risk-asset-001`).
8. **Stage 8 (Audit Log & Webhook):** Inserts interaction into `ai_interactions` and processes AI Context fact-check callback.

---

## 3. Deep Dive: Executive Presentation Guide (Point 5)

[`HANDOVER_EXECUTIVE_GUIDE.md`](file:///home/vikryansh/Workspace/projects/aev-pod-delta/HANDOVER_EXECUTIVE_GUIDE.md) is the presentation script for the engineering lead or handover speaker.

### Key Talking Points for Stakeholders:
* **"One Single Source of Truth":** We moved away from fragmented mocks into a unified enterprise dataset.
* **"Defense in Depth":** The AI Gateway enforces guardrails *before* reaching Gemma, and redacts PII *after* model response.
* **"Mandatory Citation Guarantee":** Every answer links back to a verifiable platform asset, exposure, or risk score.
* **"Graceful Fallback":** If Google Cloud Gemma is unavailable, it automatically switches to Colab GPU, and finally to a labeled mock response without throwing 500 errors.

---

## 4. Deep Dive: Data Sharing Architecture (Point 6)

### How Different Parts of the Project Access the Data

Because Pod Delta consists of independent microservices running across separate containers, **they do not share in-memory RAM in production**. The system uses a two-mode architecture:

```
 MODE 1: STANDALONE DEMO RUNNER                MODE 2: DISTRIBUTED PRODUCTION
 (run_unified_handover_demo.py)                (Multi-Container Platform)

┌──────────────────────────────┐              ┌──────────────────────────────┐
│ data/unified_dataset.json    │              │ data/unified_dataset.json    │
└──────────────┬───────────────┘              └──────────────┬───────────────┘
               │                                             │
               │ (Loaded into RAM)                           │ (DB Seed Script)
               ▼                                             ▼
┌──────────────────────────────┐              ┌──────────────────────────────┐
│ Single Python Process Memory │              │ PostgreSQL + pgvector        │
│ (All stages called directly) │              │ (assets, audit, ai_memory)   │
└──────────────────────────────┘              └──────────────┬───────────────┘
                                                             │
                                              ┌──────────────┴───────────────┐
                                              ▼                              ▼
                                     ┌─────────────────┐            ┌─────────────────┐
                                     │   AI Gateway    │◄── HTTP ──►│   AI Context    │
                                     │  (FastAPI:8001) │            │  (FastAPI:8002) │
                                     └─────────────────┘            └─────────────────┘
```

### The Three Production Data Mechanisms:

#### 1. In-Process Demo Mode (How the runner works)
- The JSON file is read once into a Python dictionary.
- Functions from each subsystem are invoked sequentially with object references.
- **Advantage:** Runs in milliseconds without Docker, port conflicts, or DB setup.

#### 2. PostgreSQL + pgvector (How live services share state)
- In production, data is stored in PostgreSQL:
  - `assets`: 9 assets with 384-dimensional vector embeddings generated by `all-MiniLM-L6-v2`.
  - `ai_memory`: User preference notes partitioned by `user_id`.
  - `ai_interactions`: Audit trail recording prompts, answers, token counts, and citations.
  - `prompt_templates`: Versioned prompts (v1, v2).
- Both the AI Gateway and AI Context connect to this database via SQLAlchemy / psycopg.

#### 3. Inter-Service HTTP REST APIs (How services talk)
- Services communicate strictly over HTTP:
  - When the AI Gateway needs asset search, it calls:
    `POST http://ai-context:8002/copilot/asset-search`
  - When AI Context completes fact-checking, it calls:
    `POST http://ai-gateway:8001/webhooks/fact-check`
  - When Connectors push assets, they call the Integration Service ingestion endpoint.

---

## Summary for Developers

1. **To test everything locally:** Run `python3 run_unified_handover_demo.py`.
2. **To inspect or modify test data:** Edit `data/aev_unified_handover_dataset.json`.
3. **To see the gap analysis & remaining sprint tasks:** Read `PROJECT_COMPLETION_AND_DEPLOYMENT_ROADMAP.md`.
4. **To present to clients or management:** Follow `HANDOVER_EXECUTIVE_GUIDE.md`.
