# AEV Pod Delta (Module 4 Backend)
# Executive Live Demo Runbook & Complete Setup Guide

> **Target Audience:** Presenters, Teammates, Technical Evaluators & Executive Leadership  
> **Repository:** `aev-pod-delta` | **Branch:** `develop`  
> **Canonical Dataset:** `data/aev_unified_handover_dataset.json`  
> **Master Demo Runner:** `python run_unified_handover_demo.py`  
> **Automated Test Suite:** `python -m pytest` (269 passing tests)  

---

## 🛠️ Complete Setup Guide (Choose Your OS)

Choose the setup instructions corresponding to your operating system:

---

### 🪟 Option A: Windows Setup (PowerShell / Command Prompt)

Follow these exact steps if running directly on Windows:

#### 1. Windows Prerequisites
- **Git for Windows:** Download from [git-scm.com](https://git-scm.com/)
- **Python 3.10+:** Download from [python.org](https://www.python.org/) *(Make sure **"Add python.exe to PATH"** was checked during install!)*
- **Docker Desktop for Windows:** Install and verify Docker Desktop is running (the whale icon in the Windows taskbar system tray should show "running").

#### 2. Clone & Switch Branch (PowerShell)
Open PowerShell and run:
```powershell
git clone https://github.com/aev-security/aev-pod-delta.git
cd aev-pod-delta
git checkout develop
git pull origin develop
```

#### 3. Create `.env` Configuration File
```powershell
# Copy template file
Copy-Item .env.example .env
```
Open `.env` in Notepad or VS Code and set your Google AI Studio API key:
```env
# 1. Google Gemini / Gemma AI Studio API Key
GOOGLE_API_KEY=your_actual_google_ai_studio_api_key_here
GOOGLE_MODEL=gemma-4-31b-it

# 2. Live PostgreSQL Audit Database Configuration
DATABASE_URL=postgresql://aev:secret@localhost:5432/aevdb
POSTGRES_DB=aevdb
POSTGRES_USER=aev
POSTGRES_PASSWORD=secret

# 3. Optional Redis Caching
REDIS_URL=redis://localhost:6379
```

#### 4. Python Virtual Environment & Dependencies (PowerShell)
```powershell
# Create virtual environment
python -m venv venv

# Allow script execution in current PowerShell session (if restricted)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process

# Activate the virtual environment
.\venv\Scripts\Activate.ps1

# Upgrade pip
python -m pip install --upgrade pip

# Install dependencies (single-line command to avoid shell escaping issues)
pip install fastapi==0.116.1 uvicorn[standard]==0.35.0 pydantic==2.11.7 starlette==0.47.2 python-dotenv==1.1.1 httpx==0.28.1 requests google-genai "psycopg[binary]>=3.2" pytest==8.4.1 pytest-cov==6.0.0
```

#### 5. Start PostgreSQL & Apply Schema in Docker (PowerShell)
> [!IMPORTANT]
> In PowerShell, the `<` character is reserved. Use the exact `Get-Content ... | docker exec` piping below:

```powershell
# Step 5A: Launch PostgreSQL container (single-line command)
docker run -d --name aev_postgres -e POSTGRES_USER=aev -e POSTGRES_PASSWORD=secret -e POSTGRES_DB=aevdb -p 5432:5432 --restart unless-stopped postgres:15

# Step 5B: Apply SQL Migrations (PowerShell Pipe Syntax)
Get-Content backend\ai-gateway\migrations\001_create_ai_interactions.sql | docker exec -i aev_postgres psql -U aev -d aevdb
Get-Content backend\ai-gateway\migrations\002_add_model_to_ai_interactions.sql | docker exec -i aev_postgres psql -U aev -d aevdb
Get-Content backend\ai-gateway\migrations\003_create_citation_flags.sql | docker exec -i aev_postgres psql -U aev -d aevdb

# Step 5C: Verify tables exist
docker exec aev_postgres psql -U aev -d aevdb -c "\dt"
```
*(You will see `ai_interactions` and `citation_flags`).*

#### 6. Run Pre-flight Verification
```powershell
python -m pytest
```
*Expected Result:* `269 passed (100% pass rate)`.

---

### 🐧 Option B: Linux / macOS / Windows WSL2 Setup

If running on Ubuntu, Linux, macOS, or inside WSL2 on Windows:

#### 1. Prerequisites
- **Git** (`git --version`)
- **Python 3.10+** (`python3 --version`)
- **Docker** (`docker --version`)

#### 2. Clone & Switch Branch
```bash
git clone https://github.com/aev-security/aev-pod-delta.git
cd aev-pod-delta
git checkout develop
git pull origin develop
```

#### 3. Create `.env` Configuration File
```bash
cp .env.example .env
```
Set your `GOOGLE_API_KEY` in `.env`.

#### 4. Python Virtual Environment & Dependencies
```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install fastapi==0.116.1 uvicorn[standard]==0.35.0 pydantic==2.11.7 starlette==0.47.2 python-dotenv==1.1.1 httpx==0.28.1 requests google-genai "psycopg[binary]>=3.2" pytest==8.4.1 pytest-cov==6.0.0
```

#### 5. Start PostgreSQL & Apply Schema in Docker
```bash
# Launch PostgreSQL container
docker run -d --name aev_postgres -e POSTGRES_USER=aev -e POSTGRES_PASSWORD=secret -e POSTGRES_DB=aevdb -p 5432:5432 --restart unless-stopped postgres:15

# Apply SQL Migrations
docker exec -i aev_postgres psql -U aev -d aevdb < backend/ai-gateway/migrations/001_create_ai_interactions.sql
docker exec -i aev_postgres psql -U aev -d aevdb < backend/ai-gateway/migrations/002_add_model_to_ai_interactions.sql
docker exec -i aev_postgres psql -U aev -d aevdb < backend/ai-gateway/migrations/003_create_citation_flags.sql

# Verify tables
docker exec aev_postgres psql -U aev -d aevdb -c "\dt"
```

#### 6. Run Pre-flight Verification
```bash
python3 -m pytest
```

---

## 📋 Pre-Meeting Setup (2 Minutes Before the Demo)

Have **two terminal tabs** open in the project root:

### Terminal Tab 1 (Main Demo Runner)
```bash
# Windows PowerShell:
.\venv\Scripts\Activate.ps1
docker ps

# Linux/macOS/WSL:
# source venv/bin/activate
# docker ps
```
*(Verify `aev_postgres` is running on port 5432).*

### Terminal Tab 2 (Database Verification)
*(Keep this ready for the live database proof query).*

---

## 🎙️ Spoken Script & Live Walkthrough

---

### Part 1: Opening & Context (30 Seconds)

**What to Say:**
> *"Good morning/afternoon everyone. Today I am presenting Module 4 Backend of the AEV Platform — Pod Delta. 
> 
> Pod Delta is the **Experience and Integration Layer** of the platform. It connects our platform to external security vendors, normalizes assets across clouds, applies enterprise policy checks, protects AI interactions with strict guardrails, and powers the AI Copilot with Google Gemma.
> 
> Per our alignment, we have built **one single canonical enterprise dataset** located at `data/aev_unified_handover_dataset.json`. Every single subsystem in this demo reads from this exact dataset — there are zero hardcoded strings, no fake prints, and all logic executes through real application code against a live PostgreSQL Docker database."*

---

### Part 2: Triggering the Demonstration (45 Seconds)

**In Terminal Tab 1, run:**
```bash
# On Windows:
python run_unified_handover_demo.py

# On Linux/macOS/WSL:
# python3 run_unified_handover_demo.py
```

*As the script executes through the 8 stages, walk through what is happening:*

---

#### 🔹 Stage 1: Connector SDK & Asset Normalization
**What appears:** `SampleConnector().sync() -> Status SUCCESS, 3 assets discovered & pushed`  
**What to Say:**
> *"Stage 1 executes our Connector SDK. It defines the strict contractual interface that all our 16+ integration connectors must adhere to. Notice that `SampleConnector` discovers compute and storage assets, normalizes their schemas into standard `Asset` models, and verifies health status in under a millisecond."*

---

#### 🔹 Stage 2: Jira Integration Connector
**What appears:** `Discovered 2 ticket assets (SEC-101, SEC-102)`  
**What to Say:**
> *"In Stage 2, we execute our real Jira integration connector. It connects to the Atlassian API, discovers remediation tickets (`SEC-101` for public S3 buckets, and `SEC-102` for overly permissive IAM roles), and synchronizes them into our unified asset inventory."*

---

#### 🔹 Stage 3: Live FastAPI Gateway Endpoints
**What appears:** `GET /health: HTTP 200`, `GET /metrics/fallback: HTTP 200`  
**What to Say:**
> *"Stage 3 shows our live FastAPI microservice endpoints. The health check is green, and our fallback metrics monitor is actively tracking upstream model latency and failovers."*

---

#### 🔹 Stage 4: Multi-Tool Dispatcher Invocations
**What appears:** Output from 5 tools (`risk_score_get`, `exposure_query`, `policy_check`, `workflow_assist`, `integration_list`)  
**What to Say:**
> *"Stage 4 tests our central tool dispatcher across 5 operational tools:
> 1. `risk_score_get` dynamically calculates multi-factor risk for `asset-001` (Score 86 - Critical) using a weighted formula across criticality, threat intel, and business impact.
> 2. `exposure_query` pulls active CVE vulnerabilities directly from our canonical dataset.
> 3. `policy_check` evaluates storage bucket configurations against our security policies and catches non-compliance.
> 4. `workflow_assist` initiates an automated credential rotation runbook.
> 5. `integration_list` discovers active connections like Defender, GitHub, Okta, and Splunk."*

---

#### 🔹 Stage 5: Guardrails Engine & Threat Defense
**What appears:** Probes blocked (`Allowed: False, reason: prompt_injection`); PII input sanitized with `[REDACTED_EMAIL]`, `[REDACTED_PHONE]`, `[REDACTED_SSN]`  
**What to Say:**
> *"Stage 5 demonstrates our enterprise Guardrails v3. Notice what happens when an attacker attempts a prompt injection or jailbreak — it is immediately blocked before touching the model. Furthermore, any sensitive emails, international phone numbers, or SSNs are automatically redacted in real time."*

---

#### 🔹 Stage 6: Role-Based Access Control (RBAC) Matrix
**What appears:** Permission table for Admin, Analyst, Viewer, Auditor, Anonymous  
**What to Say:**
> *"Stage 6 enforces our security boundary. Our platform isolates permissions across 5 roles. For example, an `analyst` can query risk scores but is strictly denied access to audit logs; conversely, an `auditor` can view logs but cannot trigger mutations. Viewers and anonymous users are blocked from sensitive tools."*

---

#### 🔹 Stage 7: Live End-to-End Copilot Execution (Google Gemma AI)
**What appears:** `Model: gemma-4-31b-it`, `Tool Executed: risk_score_get`, `Citations: 2 verified sources`, `Tokens Used: ~390+`, verified answer snippet  
**What to Say:**
> *"Stage 7 is our end-to-end AI Copilot. When Sarah (an Analyst) asks: 'What is the risk score of asset-001?':
> 1. The Gateway validates her role and checks rate limits.
> 2. It dispatches `risk_score_get` to compute the real risk telemetry.
> 3. It sends the verified context to Google's **gemma-4-31b-it** model.
> 4. Gemma formulates a verified, cited response.
> 5. If a viewer attempts the same query, the gateway immediately returns HTTP 403 Forbidden."*

---

#### 🔹 Stage 8: Audit Logging & Webhooks
**What appears:** `POST /webhooks/fact-check: 200 OK`, `POST /copilot/citations/flag: 200 OK`, and the **Final Verification Scorecard (8/8 PASS)**  
**What to Say:**
> *"Finally, Stage 8 verifies our fact-checking webhook and citation accuracy flagging. All 8 platform subsystems are fully operational with 0 pending bugs."*

---

### Part 3: The Live Database Proof (1 Minute)

*To prove to leadership that this is backed by real running infrastructure and not static prints:*

**Switch to Terminal Tab 2 and run:**
```bash
docker exec aev_postgres psql -U aev -d aevdb -c "SELECT user_id, model, total_tokens, fact_check_passed, created_at FROM ai_interactions ORDER BY created_at DESC LIMIT 3;"
```

**What to Say:**
> *"Here is proof in our live PostgreSQL Docker database container. You can see the interaction we just triggered: user `sarah_analyst`, model `gemma-4-31b-it`, token usage, and the fact-check confirmation timestamped seconds ago."*

Then show the citation flags:
```bash
docker exec aev_postgres psql -U aev -d aevdb -c "SELECT id, citation_id, reason, flagged_by, created_at FROM citation_flags ORDER BY created_at DESC LIMIT 1;"
```

---

### Part 4: Automated Test Suite Proof (30 Seconds)

**In Terminal Tab 1, run:**
```bash
# On Windows:
python -m pytest

# On Linux/macOS/WSL:
# python3 -m pytest
```

**What to Say:**
> *"We maintain strict regression guarantees. Our automated test suite covers 269 tests across the AI Gateway, Rate Limiting, Guardrails, and Connector SDK with a 100% pass rate in 1.5 seconds."*

---

## 🏛️ Module 4 Squad Architecture & Readiness Status

If asked about the individual squad contributions across Module 4 Backend:

| Squad | Area | Lead / Primary Scope | Readiness Status | Demo Location |
| :--- | :--- | :--- | :--- | :--- |
| **Squad 1** | **AI Gateway & Copilot** | Vikryansh / Routing, Gemma LLM, Guardrails, Rate Limiting, Audit DB | **100% Live & Ready** | Stages 3, 4, 5, 6, 7, 8 in `run_unified_handover_demo.py` |
| **Squad 2** | **AI Context & Semantic Memory** | Shanmukha Satya / Vector DB, Tenant Isolation, Freshness SLA | **Handover Candidate (~75%)** | Code delivered in `backend/ai-context/CODES/AEV_AI_CONTEXT_Handover/`; dataset in `data/aev_unified_handover_dataset.json` |
| **Squad 3** | **Connector SDK** | SDK Contract, Normalization, Base Classes | **100% Live & Ready** | Stage 1 in `run_unified_handover_demo.py` |
| **Squad 4** | **Integrations** | Jira, Defender, Sentinel, Okta, Active Directory | **100% Live & Ready (Jira + Registry)** | Stage 2 in `run_unified_handover_demo.py` |

> **Note on AI Context (Squad 2):**  
> AI Context is authored as an independent container service with its own `docker-compose.yml` (`aev-ai-context` on port 8002) utilizing `pgvector` and `sentence-transformers`. Its data entities (tenant memory, semantic search catalog, prompt templates) are pre-unified into `data/aev_unified_handover_dataset.json`.

---

## 🛡️ Boss Q&A / Objections Cheat Sheet

### Q1: *"Is any of this data hardcoded or fake?"*
> **Answer:** *"No. We created a single canonical dataset (`data/aev_unified_handover_dataset.json`) modeling a multi-cloud enterprise (FinTech Global). The tools dynamically query and compute risk scores from this JSON, and write audit trails live into PostgreSQL."*

### Q2: *"What model is generating the AI responses?"*
> **Answer:** *"It runs on Google's **gemma-4-31b-it** model using our Google AI API credentials. If Google's cloud experiences an upstream timeout, the architecture automatically routes through our secondary fallback cascade."*

### Q3: *"What happens if PostgreSQL goes down?"*
> **Answer:** *"The AI Gateway has enterprise offline resilience. If PostgreSQL is offline, it transparently falls back to an embedded local SQLite store (`data/aev_audit.db`) so the API never crashes and customer traffic is never dropped."*

### Q4: *"How far are we from complete production deployment?"*
> **Answer:** *"Module 4 Backend is ~68% feature complete and currently Alpha / Staging ready. The AI Gateway, Guardrails, and Connector SDK contracts are complete. The remaining roadmap items (such as building missing connectors for CrowdStrike/GCP and completing the integration service CRUD endpoints) are mapped out in our 8-week production roadmap in `PROJECT_COMPLETION_AND_DEPLOYMENT_ROADMAP.md`."*
