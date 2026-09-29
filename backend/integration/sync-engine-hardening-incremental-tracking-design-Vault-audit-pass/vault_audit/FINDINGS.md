# Vault Audit — Early Pass (Week 3)

Scope: connectors already built as of Week 3 (see `sync-engine-hardening-incremental-tracking-design-Vault-audit-pass`
in the AEV Pod Delta M4 plan). This is the early groundwork pass; a full
pass is expected in Week 4.

How this was produced:

```powershell
cd backend\integration
python vault_audit\scan_secrets.py .
```

Paste the raw output below, then triage each line as one of:
- **Confirmed issue** — needs a fix before Week 4
- **False positive** — explain why (e.g. a test fixture, a variable name
  that happens to match but isn't a real secret)
- **Needs vendor follow-up** — can't resolve without more information

## Checklist per connector

For each connector folder, confirm:

- [ ] All credentials are fetched from the shared Vault client at runtime
      (no `os.environ` reads for secrets, no hardcoded values)
- [ ] Secrets are never passed into a log call or an exception message
- [ ] Tokens/keys are not cached to disk or committed in any config file
- [ ] `.env.example` (if present) contains placeholder values only

## Findings

| Connector | Rule | File:Line | Status | Notes |
|---|---|---|---|---|
| _(fill in)_ | | | | |

## Summary

- Connectors scanned: _(fill in)_
- Confirmed issues: _(fill in)_
- Carried to Week 4 full audit: _(fill in)_
