# CyberArk Auth Module

A production-grade Python SDK for authentication and credential retrieval across CyberArk Identity Platform, Password Vault Web Access (PVWA), and Central Credential Provider (CCP).

## Features
* **Dynamic Factory Pattern**: Easily instantiate authenticators based on configuration strings.
* **Resilient HTTP Engine**: Automated backoff retries for transient HTTP failures (429, 500, 502, 503, 504).
* **OAuth2 Support**: Client Credentials Grant integration for CyberArk Identity.
* **CCP Service Integration**: Fast credential fetches via Central Credential Provider AIM Web Services.

## Quickstart

### Installation
```bash
pip install .
