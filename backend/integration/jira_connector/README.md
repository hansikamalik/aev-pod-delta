# Jira Connector

Creates Jira tickets from platform-discovered exposures, and syncs the
status of those tickets back into the platform's asset service.

Built against the `connector_sdk.Connector` interface frozen with the
Integration squad in Week 1. Owner: Harshal Sahare.

## Install

```bash
pip install -r requirements.txt
```

## How it fits the Connector contract

Unlike AWS/Azure/GCP (one-directional: external system → platform),
Jira is used in **two directions**:

1. **Ticket creation from exposures** (platform → Jira): the platform
   finds an exposure, this connector opens a Jira ticket for it. This
   is `create_ticket_from_exposure()` — a connector-specific method,
   not part of the frozen 6-method contract, since only ITSM-style
   connectors need it.
2. **Status sync back to platform** (Jira → platform): this connector
   reads current ticket status from Jira and pushes it into the
   platform as `Asset` records of type `TICKET`. This direction *is*
   the frozen contract: `discover()` reads tickets, `ingest()` pushes
   their status to the platform.

## Configuration

`describe_config()`:

```json
{
  "type": "object",
  "properties": {
    "base_url": { "type": "string", "description": "Jira site URL, e.g. https://acme.atlassian.net" },
    "project_key": { "type": "string", "description": "Jira project key tickets are created in" }
  },
  "required": ["base_url", "project_key"]
}
```

## Credentials

`describe_credentials()`:

```json
{
  "type": "object",
  "properties": {
    "email": { "type": "string", "description": "Jira account email for Basic Auth" },
    "api_token": { "type": "string", "secret": true, "description": "Jira API token" }
  },
  "required": ["email", "api_token"]
}
```

### Setting up the API token (customer-side)

1. Create a dedicated Jira account (or use a bot account) for the
   platform integration — don't use a personal account's token.
2. In Atlassian account settings, generate an API token under
   **Security → API tokens**.
3. Grant the account "Create issues" and "Browse projects" permission
   on the target project — nothing broader is needed.
4. Store the email + token pair in the platform's secrets vault; paste
   the token into the connector's credential field during onboarding.

## Usage

```python
from jira_connector import JiraConnector

connector = JiraConnector(
    base_url="https://acme.atlassian.net",
    project_key="SEC",
    email="platform-bot@acme.com",
    api_token=vault.get_secret("jira/acme/api_token"),
)

# Direction 1: open a ticket for a new exposure
ticket = connector.create_ticket_from_exposure({
    "title": "Publicly exposed S3 bucket",
    "description": "Bucket demo-app-uploads allows public read access.",
})
print(ticket.id)  # e.g. "SEC-1042"

# Direction 2: sync current ticket status back to the platform
result = connector.sync()
print(result.status, result.assets_discovered, result.assets_pushed)
```

## Testing

```bash
python -m pytest tests/ -v
```

Tests run against `FakeJiraAPIClient`, which returns canned issue data
with the same shape the real Jira REST API returns — this is the
"sandbox/mock account" this week's checklist calls for, and covers
both ticket creation and status-sync without live Jira credentials.

> Note: `requests`, `pydantic`, and `pytest` could not be installed in
> the sandbox that generated this connector (no network access), so
> the suite was written and logic-checked by hand but not executed
> against the real libraries here. Run `pip install -r requirements.txt
> && python -m pytest tests/ -v` locally before merging.

## Health check

`check_health()` calls Jira's lightweight `/rest/api/3/myself` endpoint
to confirm the configured credentials are valid and the site is
reachable.

## Files

```
jira_connector/
├── jira_connector/
│   ├── __init__.py     # public exports
│   ├── auth.py          # API-token (Basic Auth) module
│   ├── client.py        # real (JiraAPIClient) + fake (FakeJiraAPIClient) API clients
│   └── connector.py     # JiraConnector: discover/ingest + create_ticket_from_exposure
├── tests/
│   └── test_jira_connector.py
├── requirements.txt
├── pyproject.toml
├── .gitignore
├── .github/workflows/ci.yml
└── README.md
```

## Status against the Week 3 task breakdown

| Sub-task | Status |
|---|---|
| Authentication module (API token) | Done — `auth.py`, Basic Auth |
| Credential configuration | Done — `describe_credentials()` |
| Ticket creation from exposures | Done — `create_ticket_from_exposure()` |
| Status sync back to platform | Done — `discover()` + `ingest()` |
| Unit tests | Written, not yet executed against real libs (see note above) |
| Integration testing (sandbox/mock account) | Done via `FakeJiraAPIClient` |
| Documentation | This file |
