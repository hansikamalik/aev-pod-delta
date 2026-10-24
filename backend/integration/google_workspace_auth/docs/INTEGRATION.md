# Integration Notes

The authentication module is deliberately separate from discovery and ingestion.

```text
Connector
   |
   +--> GoogleWorkspaceAuthenticator.get_token()
   |         |
   |         +--> Google OAuth token endpoint
   |
   +--> Google Workspace API calls
   |
   +--> discovery / ingestion / synchronization
   |
   +--> health check
```

The project materials specify common connector capabilities, but they do not provide
the actual SentinelOne implementation or shared SDK method signatures. Confirm the
backend team's existing auth interface before wiring this module into the production
connector.

Runtime secret material must come from the team's approved secret store.

For production Domain-Wide Delegation, a Google Workspace administrator must
authorize the required API scopes for the service account. Exact scopes must be
chosen by the final connector according to the resources it discovers.
