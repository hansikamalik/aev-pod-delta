# AEV Pod Delta — Machine Setup Guide
### From a Brand-New Machine to a Running Live Stack

> This guide assumes zero prior setup. Follow it top-to-bottom for your OS.
> Time estimate: **20–30 minutes** on a clean machine with a decent internet connection.

---

## Prerequisites Overview

Before running any commands, you need three things installed:

| Tool | Why You Need It |
|---|---|
| **Git** | Clone the project repository |
| **Docker Desktop / Docker Engine** | Run all services in containers |
| **Python 3.12** | Run the database seeder and demo script |

---

## Part 1 — Windows Setup

### Step 1: Install Git

1. Go to https://git-scm.com/download/win
2. Download and run the installer (all defaults are fine)
3. Verify in a new terminal (PowerShell or CMD):
   ```
   git --version
   ```
   Expected: `git version 2.x.x`

### Step 2: Install Docker Desktop

1. Go to https://www.docker.com/products/docker-desktop/
2. Download **Docker Desktop for Windows**
3. Run the installer — it will install Docker Engine + Docker Compose together
4. After install, restart your machine if prompted
5. Open Docker Desktop and wait until it says **"Engine Running"** in the bottom-left
6. Verify in PowerShell:
   ```
   docker --version
   docker compose version
   ```
   Expected:
   ```
   Docker version 27.x.x
   Docker Compose version v2.x.x
   ```

> **WSL 2 Note:** Docker Desktop on Windows uses WSL 2 by default. If prompted during install, enable WSL 2. The installer handles this automatically.

### Step 3: Install Python 3.12

1. Go to https://www.python.org/downloads/
2. Download Python **3.12.x** (the latest 3.12 release)
3. Run the installer — **check "Add Python to PATH"** on the first screen
4. Verify in a new PowerShell window:
   ```
   python --version
   ```
   Expected: `Python 3.12.x`

### Step 4: Clone the Repository

Open PowerShell and run:

```powershell
git clone https://github.com/hansikamalik/aev-pod-delta.git
cd aev-pod-delta
```

> If the repo is private, you'll be prompted for GitHub credentials or a personal access token.

### Step 5: Install psycopg (for the database seeder)

Run this from inside the cloned project folder:

```powershell
pip install "psycopg[binary]"
```

---

## Part 2 — Linux Setup

### Step 1: Install Git

**Ubuntu/Debian:**
```bash
sudo apt update && sudo apt install -y git
```

**Fedora/RHEL:**
```bash
sudo dnf install -y git
```

Verify:
```bash
git --version
```

### Step 2: Install Docker Engine + Docker Compose

**Ubuntu/Debian (official Docker install):**
```bash
# Remove old versions if any
sudo apt remove -y docker docker-engine docker.io containerd runc

# Install dependencies
sudo apt update
sudo apt install -y ca-certificates curl gnupg lsb-release

# Add Docker's GPG key
sudo mkdir -m 0755 -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Add Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

**Allow running Docker without sudo:**
```bash
sudo usermod -aG docker $USER
newgrp docker
```

**Verify:**
```bash
docker --version
docker compose version
```

### Step 3: Install Python 3.12

**Ubuntu 22.04 / 24.04:**
```bash
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3-pip
```

**Verify:**
```bash
python3.12 --version
```

### Step 4: Install psycopg (for the database seeder)

```bash
pip3 install "psycopg[binary]"
```

### Step 5: Clone the Repository

```bash
git clone https://github.com/hansikamalik/aev-pod-delta.git
cd aev-pod-delta
```

> If the repo is private, you'll be prompted for GitHub credentials or a personal access token.

---

## Part 3 — Project Configuration (Both OS)

### Step 1: Set Up the Environment File

From inside the `aev-pod-delta` project directory:

**Windows (PowerShell):**
```powershell
Copy-Item .env.example .env
notepad .env
```

**Linux:**
```bash
cp .env.example .env
nano .env   # or vim .env, or code .env
```

### Step 2: Configure the Required Values

Open `.env` and fill in these fields. The rest can stay as defaults for a local demo.

```
# REQUIRED: Get from https://aistudio.google.com/apikey
GOOGLE_API_KEY=your_actual_google_api_key_here

# These can stay as-is for a local demo
GOOGLE_MODEL=gemma-4-31b-it
POSTGRES_PASSWORD=secret

# Set BOTH — docker-compose.prod.yml reads JWT_SECRET,
# while the Python gateway config reads JWT_SECRET_KEY
JWT_SECRET=aev-pod-delta-jwt-secret-local-dev-32chars
JWT_SECRET_KEY=aev-pod-delta-jwt-secret-local-dev-32chars
```

> **How to get a Google API Key:**
> 1. Go to https://aistudio.google.com/apikey
> 2. Sign in with a Google account
> 3. Click **"Create API key"**
> 4. Copy the key and paste it into `.env`

---

## Part 4 — Launch the Stack

### Step 1: Build and Start All Services

From the project root directory:

```bash
docker compose up --build -d
```

This command:
- Builds Docker images for all three microservices (first run takes 3–5 minutes)
- Starts PostgreSQL 15 with pgvector, Redis 7, AI Gateway, AI Context, and Integration Service
- Runs everything in the background (`-d`)

Watch the startup:
```bash
docker compose logs -f
```

Press `Ctrl+C` to stop watching logs (services keep running).

### Step 2: Wait for All Services to Be Healthy

Check status:

**Windows:**
```powershell
docker ps
```

**Linux:**
```bash
docker ps
```

Wait until all containers show **`Up`** or **`healthy`** status. This usually takes 30–60 seconds after the first build.

### Step 3: Verify Health Endpoints

Run these in a new terminal:

**Windows (PowerShell):**
```powershell
Invoke-WebRequest -Uri http://localhost:8001/health | Select-Object -Expand Content
Invoke-WebRequest -Uri http://localhost:8002/health | Select-Object -Expand Content
Invoke-WebRequest -Uri http://localhost:8003/health | Select-Object -Expand Content
```

**Linux / macOS / Git Bash:**
```bash
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
```

Expected responses:
```
{"status":"healthy","service":"AI Gateway Service"}
{"status":"Healthy"}
{"status":"ok","service":"integration-service"}
```

> Note: `GET /` on port 8003 returns a richer response (`{"service":"AEV Integration Service","status":"online","docs_url":"/docs"}`), but the `/health` liveness endpoint returns the compact form above.

If any service is not healthy yet, wait 30 more seconds and try again.

### Step 4: Seed the Database

This populates PostgreSQL with 9 enterprise assets, user memories, and prompt templates — all with pre-computed pgvector embeddings.

**Windows (PowerShell):**
```powershell
$env:DATABASE_URL="postgresql://aev:secret@localhost:5432/aevdb"
python scripts/seed_database.py
```

**Linux:**
```bash
DATABASE_URL="postgresql://aev:secret@localhost:5432/aevdb" python3 scripts/seed_database.py
```

Expected output:
```
Connecting to database: postgresql://aev:secret@localhost:5432/aevdb...
Seeding 9 assets...
Seeding 3 user memories...
Seeding 2 prompt templates...
✔ Database successfully seeded with canonical dataset & pgvector embeddings!
```

---

## Part 5 — Verify Everything Is Working

### Quick Smoke Test

**Linux/Git Bash:**
```bash
# 1. AI Gateway — ask the Copilot a question (no auth needed in dev mode)
curl -s -X POST http://localhost:8001/copilot/query \
  -H "Content-Type: application/json" \
  -H "X-User-ID: demo-user" \
  -H "X-User-Role: analyst" \
  -d '{"question": "What is the risk score of asset-001?"}' | python3 -m json.tool

# 2. AI Context — run a semantic asset search
curl -s -X POST http://localhost:8002/copilot/asset-search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer aev-internal-service-token-32chars-min" \
  -d '{"query": "database with sensitive records", "limit": 3}' | python3 -m json.tool

# 3. Integration Service — list available connectors
curl -s http://localhost:8003/api/v1/integrations/catalog | python3 -m json.tool
```

**Windows (PowerShell):**
```powershell
# AI Gateway query
$body = '{"question": "What is the risk score of asset-001?"}'
$headers = @{"Content-Type"="application/json"; "X-User-ID"="demo-user"; "X-User-Role"="analyst"}
Invoke-RestMethod -Method POST -Uri http://localhost:8001/copilot/query -Headers $headers -Body $body

# Integration catalog
Invoke-RestMethod -Uri http://localhost:8003/api/v1/integrations/catalog
```

### Interactive API Docs

Open these in a browser — all three have auto-generated Swagger UIs:

- AI Gateway docs: http://localhost:8001/docs
- AI Context docs: http://localhost:8002/docs
- Integration Service docs: http://localhost:8003/docs

---

## Part 6 — Optional: Production Stack with NGINX Ingress

For demonstrating the production architecture (NGINX routing on port 80):

**Windows (PowerShell):**
```powershell
docker compose -f docker-compose.prod.yml up -d
```

**Linux:**
```bash
docker compose -f docker-compose.prod.yml up -d
```

Verify unified ingress:

**Linux / Git Bash:**
```bash
# Verify NGINX ingress health (returns "healthy")
curl http://localhost/health

# Verify reverse proxy routing to integration-service through NGINX
curl http://localhost/api/v1/integrations/catalog | python3 -m json.tool
```

**Windows (PowerShell):**
```powershell
Invoke-WebRequest -Uri http://localhost/health | Select-Object -Expand Content
Invoke-RestMethod -Uri http://localhost/api/v1/integrations/catalog
```

---

## Part 7 — Running the Tests

**Linux:**
```bash
# Root test suite (AI Gateway + Connector SDK) — 370 tests
python3 -m pytest -c pytest.ini

# Integration Service tests — 36 tests
cd backend/integration && python3 -m pytest -c pytest.ini && cd ../..

# AI Context tests — 30 tests
cd backend/ai-context/CODES/AEV_AI_CONTEXT_Handover
PYTHONPATH=. python3 -m pytest app/tests/ -o pythonpath=.
cd ../../../..
```

**Windows (PowerShell):**
```powershell
# Root test suite (AI Gateway + Connector SDK) — 370 tests
python -m pytest -c pytest.ini

# Integration Service tests — 36 tests
cd backend\integration
python -m pytest -c pytest.ini
cd ..\..

# AI Context tests — 30 tests
cd backend\ai-context\CODES\AEV_AI_CONTEXT_Handover
$env:PYTHONPATH="."
python -m pytest app/tests/ -o pythonpath=.
cd ..\..\..\..
```

---

## Part 8 — Stopping and Restarting

These commands work identically on Windows (PowerShell) and Linux:

```bash
# Stop all containers (keeps data)
docker compose down

# Stop and delete all data (fresh start)
docker compose down -v

# Restart after stopping
docker compose up -d
# Then re-run the seeder if you used -v above
```

---

## Troubleshooting

### Port already in use

If you see `address already in use` for port 8001, 8002, 8003, or 5432:

```bash
# Find what's using the port (Linux)
sudo lsof -i :8001

# Windows
netstat -ano | findstr :8001
```

Kill that process, or change the port mapping in `docker-compose.yml`.

### Docker build fails for ai-context

The AI Context service builds from a nested path. If you see a Dockerfile error:

```bash
docker compose build ai-context --no-cache
```

### Database seeder fails with "connection refused"

The database container isn't ready yet. Wait 30 seconds and try again. Or:

```bash
docker compose logs postgres
```

Make sure you see: `database system is ready to accept connections`

### Google API Key errors in the gateway

The AI Gateway will start but LLM calls will fail if `GOOGLE_API_KEY` is not set or is invalid. Check your `.env` file and restart:

```bash
docker compose restart ai-gateway
```

### Container running but health check failing (Windows)

This sometimes happens on first boot of Docker Desktop. Run:

```powershell
docker compose restart
```

---

## Quick Reference

| Service | URL | Docs |
|---|---|---|
| AI Gateway (Copilot) | http://localhost:8001 | http://localhost:8001/docs |
| AI Context (Vector Search) | http://localhost:8002 | http://localhost:8002/docs |
| Integration Service | http://localhost:8003 | http://localhost:8003/docs |
| NGINX Ingress (prod stack) | http://localhost:80 | — |

| Command | Description |
|---|---|
| `docker compose up --build -d` | Start everything (first time) |
| `docker compose up -d` | Start after first build |
| `docker compose down` | Stop everything |
| `docker compose logs -f` | Watch live logs |
| `docker compose ps` | Check container status |
| `python3 scripts/seed_database.py` | Seed database — Linux |
| `python scripts/seed_database.py` | Seed database — Windows |
| `python3 run_unified_handover_demo.py` | Run zero-dependency demo — Linux |
| `python run_unified_handover_demo.py` | Run zero-dependency demo — Windows |
