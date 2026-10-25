# AEV Pod Delta — Machine Setup Guide
### Full Developer Onboarding for Windows & Linux

> **Audience:** New developers joining the project on any machine  
> **Time to complete:** ~30–45 minutes (first time) | ~10 minutes (with API keys ready)  
> **Branch:** `develop` | **Repo:** `https://github.com/hansikamalik/aev-pod-delta`

---

## Table of Contents

1. [Prerequisites at a Glance](#1-prerequisites-at-a-glance)
2. [Acquiring Your API Keys](#2-acquiring-your-api-keys) ← **Start here if you have nothing**
3. [Windows Setup](#3-windows-setup)
4. [Linux Setup](#4-linux-setup)
5. [Clone & Configure the Repository](#5-clone--configure-the-repository)
6. [Run the Services](#6-run-the-services)
7. [Run the Test Suite](#7-run-the-test-suite)
8. [Environment Variable Reference](#8-environment-variable-reference)
9. [Troubleshooting](#9-troubleshooting)

---

## 1. Prerequisites at a Glance

| Tool | Version | Required For |
|---|---|---|
| Python | **3.12+** | All backend services |
| Git | Any recent | Cloning the repo |
| Docker Desktop | **24+** | Full stack & prod compose |
| Docker Compose | **v2** (bundled) | Multi-service orchestration |
| PostgreSQL | 15+ (or via Docker) | AI Gateway & Context DB |
| Redis | 7+ (or via Docker) | Distributed locks & caching |

> **Tip:** If you use Docker, you do **not** need to install PostgreSQL or Redis locally — Docker handles them automatically.

---

## 2. Acquiring Your API Keys

This project needs **one mandatory API key** and several optional ones depending on which connectors you run.

---

### 🔑 2.1 Google AI Studio API Key (MANDATORY — for Gemma LLM)

The AI Gateway routes questions through **Google Gemma** via the Google AI/Gemini API. Without this key the Copilot returns mock responses only.

**Steps:**

1. Open **[https://aistudio.google.com/](https://aistudio.google.com/)** in your browser
2. Sign in with a Google account (personal or Workspace)
3. Click **"Get API key"** in the top-left sidebar
4. Click **"Create API key"** → choose **"Create API key in new project"**
5. Copy the generated key — it looks like `AIzaSy...` (39 characters)
6. Paste it into your `.env` file as:
   ```
   GOOGLE_API_KEY=AIzaSyYourKeyHere
   GOOGLE_MODEL=gemma-4-31b-it
   ```

> **Free tier:** Google AI Studio provides free quota (60 requests/minute on Gemma models). No credit card needed for development.  
> **Paid tier:** For production loads, enable billing at [https://console.cloud.google.com/billing](https://console.cloud.google.com/billing)

---

### 🔑 2.2 JWT Secret Key (MANDATORY — for authentication)

This is **not** a third-party key — you generate it yourself. It must be at least 32 characters.

**Generate one instantly:**

```bash
# Linux / macOS / Git Bash (Windows)
python3 -c "import secrets; print(secrets.token_hex(32))"

# PowerShell (Windows)
python -c "import secrets; print(secrets.token_hex(32))"
```

Copy the output and set it in `.env`:
```
JWT_SECRET_KEY=a1b2c3d4e5f6...   # your 64-char hex string
JWT_ALGORITHM=HS256
JWT_ISSUER=aev-pod-alpha
JWT_AUDIENCE=aev-pod-delta
```

---

### 🔑 2.3 Azure Credentials (OPTIONAL — only for Azure connector)

Only needed if you're running the Azure Discovery or Normalization connectors.

**Steps:**

1. Log in at **[https://portal.azure.com/](https://portal.azure.com/)**
2. Go to **Azure Active Directory → App registrations → New registration**
3. Name it `aev-pod-delta-dev`, set redirect URI to `http://localhost`
4. After creation, copy:
   - **Application (client) ID** → `AZURE_CLIENT_ID`
   - **Directory (tenant) ID** → `AZURE_TENANT_ID`
5. Go to **Certificates & secrets → New client secret** → copy the value → `AZURE_CLIENT_SECRET`
6. Go to **Subscriptions** → copy your subscription ID → `AZURE_SUBSCRIPTION_ID`

```
AZURE_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
AZURE_CLIENT_SECRET=your~secret~value
AZURE_TENANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
AZURE_SUBSCRIPTION_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

> **Sandbox:** Use [Azure Free Account](https://azure.microsoft.com/free/) — $200 credit for 30 days, no production data needed.

---

### 🔑 2.4 Okta API Token (OPTIONAL — only for Okta connector)

1. Log in to your Okta admin console (e.g., `https://dev-XXXXXX-admin.okta.com`)
2. Go to **Security → API → Tokens → Create Token**
3. Name it `aev-dev`, copy the token value

```
OKTA_ORG_URL=https://dev-XXXXXX.okta.com
OKTA_API_TOKEN=00abc123...
```

> **Free sandbox:** Sign up at [https://developer.okta.com/](https://developer.okta.com/) — free forever for dev.

---

### 🔑 2.5 Slack Webhook (OPTIONAL — for spend/alert notifications)

1. Go to **[https://api.slack.com/apps](https://api.slack.com/apps)** → **Create New App → From scratch**
2. Name it `AEV Alerts`, select your workspace
3. Go to **Incoming Webhooks → Activate → Add New Webhook to Workspace**
4. Choose a channel (e.g., `#aev-alerts`), click **Allow**, copy the URL

```
SLACK_ALERT_WEBHOOK_URL=https://hooks.slack.com/services/T00/B00/XXXX
```

---

### 🔑 2.6 ServiceNow Credentials (OPTIONAL — for ServiceNow connector)

Use a **Personal Developer Instance (PDI)** — free at [https://developer.servicenow.com/](https://developer.servicenow.com/)

```
SN_INSTANCE_URL=https://devXXXXXX.service-now.com
SN_USERNAME=admin
SN_PASSWORD=your_pdi_password
SN_AUTH_METHOD=basic
```

---

### 🔑 2.7 HashiCorp Vault Token (OPTIONAL — for Vault connector)

For local dev, run Vault in dev mode (no setup needed):

```bash
# Install Vault first, then:
vault server -dev
# Copy the Root Token printed in the terminal
```

```
VAULT_ADDR=http://127.0.0.1:8200
VAULT_TOKEN=hvs.your_dev_root_token
VAULT_KV_MOUNT=secret
```

---

## 3. Windows Setup

### Step 1 — Install Python 3.12

1. Download from **[https://www.python.org/downloads/](https://www.python.org/downloads/)**
2. Run the installer — **check "Add Python to PATH"** before clicking Install
3. Verify in a new terminal:

```powershell
python --version        # Should show 3.12.x
pip --version
```

---

### Step 2 — Install Git

1. Download **Git for Windows** from **[https://git-scm.com/download/win](https://git-scm.com/download/win)**
2. During install, choose **"Git from the command line and also from 3rd-party software"**
3. Verify:

```powershell
git --version
```

---

### Step 3 — Install Docker Desktop

1. Download from **[https://www.docker.com/products/docker-desktop/](https://www.docker.com/products/docker-desktop/)**
2. During install, ensure **WSL 2 backend** is selected (recommended)
3. Restart your machine after install
4. Open Docker Desktop and wait for the engine to start (whale icon in taskbar)
5. Verify:

```powershell
docker --version
docker compose version
```

> **WSL 2 note:** If WSL 2 isn't installed, run in PowerShell as Administrator:
> ```powershell
> wsl --install
> ```
> Then restart.

---

### Step 4 — (Optional) Windows Terminal + PowerShell 7

For the best experience, install **Windows Terminal** from the Microsoft Store and **PowerShell 7**:

```powershell
winget install Microsoft.PowerShell
winget install Microsoft.WindowsTerminal
```

---

## 4. Linux Setup

### Ubuntu / Debian

```bash
# 1. Update package list
sudo apt update && sudo apt upgrade -y

# 2. Install Python 3.12
sudo apt install -y software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3.12-dev

# Make python3.12 the default python3 (optional)
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1

# 3. Install pip
curl -sS https://bootstrap.pypa.io/get-pip.py | python3.12

# 4. Install Git
sudo apt install -y git

# 5. Install Docker Engine
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker

# Verify
python3 --version
docker --version
docker compose version
```

---

### Fedora / RHEL / CentOS

```bash
# 1. Install Python 3.12
sudo dnf install -y python3.12 python3.12-pip

# 2. Install Git
sudo dnf install -y git

# 3. Install Docker
sudo dnf install -y docker
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER
newgrp docker

# Install Docker Compose v2 plugin
sudo dnf install -y docker-compose-plugin
```

---

### Arch Linux

```bash
sudo pacman -Syu python python-pip git docker docker-compose
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER
```

---

## 5. Clone & Configure the Repository

### Step 1 — Clone

```bash
# Linux / macOS / Git Bash
git clone https://github.com/hansikamalik/aev-pod-delta.git
cd aev-pod-delta
git checkout develop

# Windows PowerShell (same commands work)
```

---

### Step 2 — Create your `.env` file

```bash
# Linux
cp .env.example .env

# Windows PowerShell
Copy-Item .env.example .env
```

Now open `.env` in your editor and fill in the values you collected in [Section 2](#2-acquiring-your-api-keys):

```bash
# Linux — use nano, vim, or VS Code
nano .env
# or
code .env

# Windows — use Notepad or VS Code
notepad .env
# or
code .env
```

**Minimum required values for local dev:**

```env
GOOGLE_API_KEY=AIzaSyYourKeyHere
GOOGLE_MODEL=gemma-4-31b-it
JWT_SECRET_KEY=your_64_char_hex_string_here
DATABASE_URL=postgresql://aev:secret@localhost:5432/aevdb
REDIS_URL=redis://localhost:6379/0
```

---

### Step 3 — Set up Python virtual environment

```bash
# Linux
python3 -m venv .venv
source .venv/bin/activate

# Windows PowerShell
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Windows CMD
.venv\Scripts\activate.bat
```

Verify the venv is active — your prompt should show `(.venv)`.

---

### Step 4 — Install dependencies

```bash
# AI Gateway (primary service)
pip install -r backend/ai-gateway/requirements.txt

# Connector SDK
pip install -e backend/connector-sdk/

# Integration Service
pip install -r backend/integration/requirements.txt

# AI Context Service (heavy — includes torch + sentence-transformers)
pip install -r backend/ai-context/CODES/AEV_AI_CONTEXT_Handover/requirements.txt
```

> **Note on AI Context:** Installing `torch` and `sentence-transformers` can take 5–10 minutes and ~3 GB of disk space. Skip this service if you only need the Gateway + Integration services.

---

## 6. Run the Services

### Option A — Docker (Recommended, simplest)

Starts all services (Gateway, Context, Integration, PostgreSQL, Redis, NGINX) in one command:

```bash
# Development stack
docker compose up --build -d

# Verify all containers are running
docker compose ps

# View logs
docker compose logs -f ai-gateway
```

**Service URLs after startup:**

| Service | URL |
|---|---|
| AI Gateway (Copilot API) | http://localhost:8000 |
| AI Context Service | http://localhost:8002 |
| Integration Service | http://localhost:8001 |
| API Docs (Gateway) | http://localhost:8000/docs |
| API Docs (Integration) | http://localhost:8001/docs |

---

### Option B — Production Stack with NGINX (P2-1)

```bash
docker compose -f docker-compose.prod.yml up -d
```

All traffic routes through NGINX on **port 80**:

| Path | Routes To |
|---|---|
| `http://localhost/api/v1/copilot` | AI Gateway |
| `http://localhost/api/v1/context` | AI Context |
| `http://localhost/api/v1/integrations` | Integration Service |
| `http://localhost/health` | Health check |

---

### Option C — Run services individually (no Docker)

**AI Gateway:**
```bash
cd backend/ai-gateway
PYTHONPATH=. uvicorn app.main:app --reload --port 8000
```

**Integration Service:**
```bash
cd backend/integration/integration-service
PYTHONPATH=. uvicorn app.main:app --reload --port 8001
```

**AI Context Service:**
```bash
cd backend/ai-context/CODES/AEV_AI_CONTEXT_Handover
PYTHONPATH=. uvicorn app.main:app --reload --port 8002
```

---

## 7. Run the Test Suite

```bash
# 1. Root suite — AI Gateway + Connector SDK (370 tests)
python3 -m pytest -c pytest.ini -v

# 2. Integration service suite (36 tests)
cd backend/integration
python3 -m pytest -v
cd ../..

# 3. AI Context suite (30 tests)
cd backend/ai-context/CODES/AEV_AI_CONTEXT_Handover
PYTHONPATH=. python3 -m pytest app/tests/ -v
cd ../../../..

# 4. AI Gateway with coverage report
cd backend/ai-gateway
PYTHONPATH=. python3 -m pytest -v --cov=app --cov-report=term-missing
cd ../..
```

**Expected results:**

| Suite | Tests | Coverage |
|---|---|---|
| Root (Gateway + SDK) | 370 passed | — |
| Integration Service | 36 passed | — |
| AI Context | 30 passed | — |
| AI Gateway (standalone) | 297 passed | 87.6% |
| **Total** | **436** | ✅ |

---

## 8. Environment Variable Reference

### Core (Always Required)

| Variable | Example | Description |
|---|---|---|
| `GOOGLE_API_KEY` | `AIzaSy...` | Google AI Studio key for Gemma LLM |
| `GOOGLE_MODEL` | `gemma-4-31b-it` | Gemma model to use |
| `JWT_SECRET_KEY` | 64-char hex | Signing key for Pod Alpha JWT tokens |
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm |
| `JWT_ISSUER` | `aev-pod-alpha` | Expected issuer claim |
| `JWT_AUDIENCE` | `aev-pod-delta` | Expected audience claim |
| `DATABASE_URL` | `postgresql://aev:secret@localhost:5432/aevdb` | PostgreSQL connection string |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection string |

### AI Gateway

| Variable | Example | Description |
|---|---|---|
| `AI_CONTEXT_URL` | `http://localhost:8002` | Internal URL to AI Context service |
| `AI_CONTEXT_TOKEN` | 32+ char token | Service-to-service auth token |
| `COLAB_GEMMA_URL` | `https://...ngrok.io` | Fallback Google Colab T4 GPU tunnel |
| `JWT_AUTH_REQUIRED` | `false` | Set `true` for strict Bearer-only mode |

### Alerting (Optional)

| Variable | Example | Description |
|---|---|---|
| `SLACK_ALERT_WEBHOOK_URL` | `https://hooks.slack.com/...` | Spend threshold alerts |
| `PAGERDUTY_ALERT_WEBHOOK_URL` | `https://events.pagerduty.com/...` | On-call escalation |

### Connectors (Optional — set only what you use)

| Variable | Connector |
|---|---|
| `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID` | Azure Discovery |
| `OKTA_ORG_URL`, `OKTA_API_TOKEN` | Okta |
| `SN_INSTANCE_URL`, `SN_USERNAME`, `SN_PASSWORD` | ServiceNow |
| `VAULT_ADDR`, `VAULT_TOKEN` | HashiCorp Vault |
| `CYBERARK_PVWA_URL`, `CYBERARK_USER`, `CYBERARK_PASS` | CyberArk |

---

## 9. Troubleshooting

### ❌ `ModuleNotFoundError` when running pytest

Make sure you're running from the right directory with PYTHONPATH set:

```bash
# For AI Gateway
cd backend/ai-gateway && PYTHONPATH=. python3 -m pytest

# For Integration
cd backend/integration && python3 -m pytest   # pytest.ini handles PYTHONPATH

# For AI Context
cd backend/ai-context/CODES/AEV_AI_CONTEXT_Handover && PYTHONPATH=. python3 -m pytest app/tests/
```

---

### ❌ Docker containers keep restarting

```bash
# Check logs for the failing container
docker compose logs ai-gateway

# Most common cause: missing .env file or wrong DATABASE_URL
# Make sure .env exists at the repo root
ls -la .env
```

---

### ❌ `psycopg` connection error / DB not found

If running without Docker, start PostgreSQL locally and create the database:

```bash
# Linux
sudo -u postgres psql -c "CREATE USER aev WITH PASSWORD 'secret';"
sudo -u postgres psql -c "CREATE DATABASE aevdb OWNER aev;"

# Windows (PowerShell, assuming PostgreSQL is installed)
psql -U postgres -c "CREATE USER aev WITH PASSWORD 'secret';"
psql -U postgres -c "CREATE DATABASE aevdb OWNER aev;"
```

---

### ❌ `GOOGLE_API_KEY` not working / 403 error

- Verify the key at [https://aistudio.google.com/](https://aistudio.google.com/) — check it's active
- Ensure you copied the **full** key with no extra spaces
- The gateway falls back to mock mode automatically — check logs for `"Using mock Gemma response"`

---

### ❌ Windows: `Activate.ps1` execution policy error

```powershell
# Run this once as Administrator
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

### ❌ `sentence-transformers` / `torch` install takes forever (AI Context)

This is expected — PyTorch is ~2 GB. Use a faster mirror:

```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install sentence-transformers
```

Or skip the AI Context service entirely — the Gateway and Integration services work independently.

---

### ❌ Port already in use

```bash
# Linux — find and kill process using port 8000
sudo lsof -i :8000
kill -9 <PID>

# Windows PowerShell
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

---

*Last updated: October 2026 | Branch: `develop` | All 436 tests verified*
