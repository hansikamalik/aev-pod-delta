# Project Entry Point

# Azure Normalization & Platform Push Engine

A robust ingestion and processing framework designed to normalize raw Azure asset telemetry (VMs, Storage Accounts, Entra ID Users, SQL DBs, Function Apps) into unified **CyberArk Asset Model (CAM)** schema payloads, validate contract compliance, and deliver records via resilient REST HTTP streaming with Dead Letter Queue (DLQ) fallback.

## Quick Start

```bash
# Clone and setup environment
git clone <repository-url>
cd azure_normalization_push
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Execute Verification & Test Suite
./run_tests.sh
