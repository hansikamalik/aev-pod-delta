# AEV Pod Delta — Kubernetes & Helm Deployment Guide

This directory contains production and staging deployment manifests for the AEV Pod Delta platform:
- **Raw Kubernetes Manifests:** `deploy/k8s/`
- **Helm v3 Chart:** `deploy/helm/aev-pod-delta/`

---

## 1. Architecture Overview

The deployed services within the `aev-system` namespace include:
- **`postgres`:** PostgreSQL 15 with `pgvector` extension for vector similarity search and persistent storage.
- **`redis`:** Redis 7 for distributed locks (`SyncLockManager`) and event freshness queues.
- **`ai-gateway`:** Core FastAPI service handling Gemma/Gemini orchestration, dynamic tool routing, JWT auth, and spend tracking.
- **`ai-context`:** Vector search service maintaining asset embeddings and real-time freshness SLA.
- **`integration-service`:** Connector lifecycle hub managing discovery, ingestion, and sync checkpoints.
- **`ingress`:** NGINX ingress controller routing external API requests to internal services.

---

## 2. Option A: Deploying with Helm (Recommended)

### Prerequisites
- Kubernetes cluster v1.26+
- Helm v3.10+
- Ingress-NGINX controller installed in cluster

### Step 1: Install Chart
```bash
helm install aev-pod-delta deploy/helm/aev-pod-delta \
  --namespace aev-system \
  --create-namespace \
  --set secrets.postgresPassword="your_strong_postgres_password" \
  --set secrets.googleApiKey="your_google_ai_studio_key" \
  --set secrets.jwtSecret="your_minimum_32_character_jwt_secret"
```

### Step 2: Custom Values Deployment
For staging and production environments, maintain an external values file:
```bash
helm upgrade --install aev-pod-delta deploy/helm/aev-pod-delta \
  --namespace aev-system \
  -f staging-values.yaml
```

### Step 3: Verify Deployment
```bash
kubectl get pods,svc,hpa,ingress -n aev-system
```

---

## 3. Option B: Deploying with `kubectl`

### Step 1: Create Namespace, ConfigMap & Secrets
```bash
kubectl apply -f deploy/k8s/namespace.yaml
kubectl apply -f deploy/k8s/configmap.yaml
```

Edit `deploy/k8s/secret.yaml` with your base64-encoded credentials:
```bash
# Example base64 generation:
echo -n "your_password" | base64

kubectl apply -f deploy/k8s/secret.yaml
```

### Step 2: Deploy Infrastructure & Applications
```bash
kubectl apply -f deploy/k8s/postgres-deployment.yaml
kubectl apply -f deploy/k8s/redis-deployment.yaml
kubectl apply -f deploy/k8s/ai-gateway-deployment.yaml
kubectl apply -f deploy/k8s/ai-context-deployment.yaml
kubectl apply -f deploy/k8s/integration-service-deployment.yaml
kubectl apply -f deploy/k8s/ingress.yaml
kubectl apply -f deploy/k8s/hpa.yaml
```

---

## 4. Production Secrets Management

In production, do not store plain secrets in Git or command history:
- **HashiCorp Vault:** Inject secrets using the Vault Agent Sidecar or External Secrets Operator (ESO).
- **Kubernetes Secret Store CSI Driver:** Sync secrets directly from AWS Secrets Manager, GCP Secret Manager, or Azure Key Vault.
- **Sealed Secrets:** Encrypt `Secret` manifests before committing to version control.
