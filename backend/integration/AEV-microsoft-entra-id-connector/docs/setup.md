# Microsoft Entra ID connector ΓÇö setup

**Squad:** Integration ┬╖ **Owner (Week 2):** Abhiram
**Sprint:** Week 2, Sep 11ΓÇôSep 17 ┬╖ Backlog item: "Entra ID (finish, solo)", P0, 3.5 days

Builds on Week 1's auth module (`auth.py`) to finish discovery,
normalization, and push.

## Object types synced

| Object type        | Graph endpoint       | Asset schema `asset_type` |
|---------------------|-----------------------|------------------------------|
| Users                | `/users`               | `identity` (metadata.entra_object_type = "user") |
| Groups               | `/groups`              | `identity` (metadata.entra_object_type = "group") |
| Service principals   | `/servicePrincipals`   | `identity` (metadata.entra_object_type = "service_principal") |

## Findings raised

A small, illustrative check: disabled-but-present users and service
principals are raised as `Severity.LOW` findings (stale/orphaned
identity cleanup). Deeper risk scoring is out of scope for this
connector ΓÇö that belongs to AI Context / AI Gateway.

## Required credentials

Set via Vault (`secret/connectors/microsoft_entra_id`) or env vars:

```
ENTRA_TENANT_ID
ENTRA_CLIENT_ID
ENTRA_CLIENT_SECRET
```

App registration needs `User.Read.All`, `Group.Read.All`, and
`Application.Read.All` (application permissions, admin-consented).

## Usage

```python
from connectors.microsoft_entra_id.connector import EntraIDConnector

connector = EntraIDConnector()
result = connector.run_sync()
# SyncResult(connector="microsoft_entra_id", status="success",
#            assets_discovered=N, findings_ingested=M, ...)
```

Individual pipeline stages (`discover`, `ingest`, `normalize`, `push`,
`health_check`) can also be called independently.

## Known follow-ups (not in Week 2 scope)

- `mfaRegistered` on users requires a Graph `$select`/beta-endpoint
  call not yet wired in.
- Conditional Access policies and sign-in risk are out of scope for
  this connector.
- No sandbox/mock-API harness wired in yet ΓÇö tests mock
  `requests`/`EntraIDAuth` directly. Swap in once Connector SDK's
  Python sandbox v2 supports Graph-shaped responses.

## Tests

```bash
pytest connectors/microsoft_entra_id/tests/ -v
```

Covers: multi-page Graph discovery across all three object types,
normalization mapping per object type, disabled-identity finding
logic, push delegation to `PlatformClient`, health-check success/
failure, and a full `run_sync()` integration path (mocked end-to-end).
