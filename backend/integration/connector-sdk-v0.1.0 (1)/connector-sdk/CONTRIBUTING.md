# Contributing to the Connector SDK

## Contract ownership

The Integration Lead owns `contract_v2.md` and the public surface of
`connector_sdk`. Anything that changes connector-visible behavior is a
contract change and needs Lead review before merge.

**Contract change (Lead review required):**

- adding, renaming, or removing a `Connector` method
- changing a method signature or return type
- adding or removing an `AssetType` or `SyncStatus` member
- changing required `Asset` or `SyncResult` fields
- changing how `sync()` derives status
- adding a runtime dependency

**Not a contract change (normal review):**

- new helpers in `schemas.py` that don't alter existing behavior
- new test doubles or contract tests that codify an existing rule
- docstrings, typing, internal refactors
- new exception subclasses under an existing base

## Versioning

SemVer. Week 1 is pinned to `0.1.0`. A contract change bumps the minor
version and is announced in the team channel with a migration note before
the pin moves — nobody should discover a breaking change from a red CI run.

## Adding a rule to the contract suite

Every assertion in `connector_sdk/testing/contract.py` must trace to a
numbered section of `contract_v2.md`. If a rule isn't in the document, add
it there first. A test without a contract reference gets rejected, because
it makes the suite an opinion rather than a spec.

New assertions are breaking for existing connectors, so land them with the
minor bump, not as a patch.

## Before opening a PR

```bash
ruff check src tests
mypy src
pytest --cov --cov-report=term-missing
```

`--cov` enforces 85% on `connector_sdk`. The base class and the status
derivation logic should be at or near 100% — they run on every sync of
every connector.

## Review checklist for connector PRs

See the Definition of Done in [README.md](README.md). The two things
reviewers miss most often:

1. **`ingest()` returning `len(assets)` unconditionally.** That reports
   platform-rejected assets as pushed and turns a partial sync into a false
   success. Return what the platform accepted.
2. **Non-deterministic asset IDs.** A UUID or a timestamp-derived ID creates
   duplicate assets on every scheduled run. The contract suite catches the
   obvious UUID case; a hash over a mutable field it cannot catch, so read
   the normalizer.
