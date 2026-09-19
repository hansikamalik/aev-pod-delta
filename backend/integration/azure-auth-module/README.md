# Azure Authentication & Credentials Module

**Owner:** Bhavesh K
**Workstream:** Integration Squad — Azure Connector (Week 1 Parallel Execution Plan)
**Deliverable:** Reusable Azure Authentication Module

## What this does

Handles everything needed to authenticate against Azure using a
service-principal (client ID / secret / tenant ID):

- Service-principal authentication (`ServicePrincipalAuthenticator`)
- Credential configuration & structural validation (`AzureCredentials`)
- Live credential validation against Azure AD, with retry + exponential
  backoff on throttling
- Token acquisition, caching, and refresh (`TokenManager`)
- A typed error hierarchy (`InvalidCredentialsError`,
  `CredentialValidationError`, `TokenExpiredError`, `ThrottledError`)
- A drop-in mock (`MockAzureAuthenticator`) so teammates never have to
  wait on this module to build against it

## Install

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in real values, or leave blank and use the mock
```

## Quick start — real authentication

```python
from azure_auth import ServicePrincipalAuthenticator, EnvCredentialProvider

auth = ServicePrincipalAuthenticator(EnvCredentialProvider())
auth.validate_credentials()      # raises on bad creds
token = auth.get_token()         # cached + auto-refreshed
print(token.access_token)
```

## Quick start — mock (for teammates developing in parallel)

```python
from azure_auth import MockAzureAuthenticator

auth = MockAzureAuthenticator()
token = auth.get_token()         # works instantly, no real Azure call

# Simulate failure modes for your own error-handling tests:
auth = MockAzureAuthenticator(should_fail=True)      # -> CredentialValidationError
auth = MockAzureAuthenticator(should_throttle=True)  # -> ThrottledError
```

Both classes implement the same `AzureAuthenticator` interface, so code
written against the mock switches to the real thing with a one-line
constructor swap.

## Run tests

```bash
python -m pytest tests/ -v
```

## Dependencies on other workstream members

This module is designed so nobody has to wait on anybody, per the plan's
"no waiting" rule. Specifics:

| Depends on | For what | Blocked until then? |
|---|---|---|
| **Abhiram** (Secrets Vault) | A real `CredentialProvider` backed by the Vault, replacing `EnvCredentialProvider` | No — `EnvCredentialProvider` is a working stand-in; swap later by implementing `get_credentials()` |
| **Harshal** (Connector contract) | If the shared connector interface expects a specific auth method signature | No — `AzureAuthenticator`'s three methods (`get_token`, `validate_credentials`, `is_authenticated`) are intentionally minimal; adjust signatures once the contract is published |

Who depends on this module:

| Consumer | What they need from here | Should they wait? |
|---|---|---|
| **Subramani** (Discovery) | A token/session to call Azure APIs | No — use `MockAzureAuthenticator` until the real module is finalized (Day 5 per schedule) |
| **Ashwin** (Normalization & Push) | `is_authenticated()` / error types to handle in the push pipeline | No — same, use the mock |
| **Bhawook** (QA) | Both real and mock classes for auth test coverage | No — mock is available from Day 1 |

## File structure

```
azure-auth-module/
├── azure_auth/
│   ├── __init__.py        # public exports
│   ├── auth.py             # AzureAuthenticator interface + real impl
│   ├── credentials.py       # AzureCredentials + CredentialProvider
│   ├── token_manager.py     # Token caching/refresh
│   ├── exceptions.py        # error hierarchy
│   └── mock_auth.py         # MockAzureAuthenticator
├── tests/
│   └── test_azure_auth.py
├── requirements.txt
├── .env.example
└── README.md
```
