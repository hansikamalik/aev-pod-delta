# Review Standards — Integration Squad

Owner: Harshal Sahare. This is the rubric behind the PR template checkboxes —
use it when a checkbox needs a judgment call, not just a yes/no.

## 1. Merge gate

A connector PR merges only if:
1. `pytest connectors/<name>/tests` is green, including its
   `ConnectorContractTests` subclass.
2. `ruff check` is clean.
3. The reviewer can answer "what happens if the source is down right now?"
   from reading the diff, without asking the author.

If any of these isn't true, request changes — don't merge with a "fix in
follow-up" comment. Contract violations compound once Day 6 integration starts.

## 2. The two failure modes to read for specifically

These are the ones the automated suite catches structurally but a human
still has to *look* for, because a technically-passing test can hide them:

**a) `ingest()` inflating its count.**
```python
# WRONG — reports success even if the platform rejected everything
def ingest(self, assets):
    self._platform.push(assets)
    return len(assets)
```
```python
# RIGHT
def ingest(self, assets):
    assets = list(assets)
    return self._platform.bulk_upsert(assets)   # returns accepted count
```
Ask: "if `InMemoryPlatformClient(reject_ids=...)` rejected half of these,
would this method still claim full success?" If yes, block the PR.

**b) Non-deterministic or mutable-derived asset IDs.**
The contract suite catches literal UUIDs. It cannot catch a hash over a
field that changes between runs (e.g. hashing a timestamp or a full JSON
blob with a "last seen" field in it). Read the ID construction line by line;
ask "would this same VM produce the same ID tomorrow?"

## 3. Contract-change vs normal change

If a PR touches `connector_sdk/` itself (not a connector under
`connectors/`), classify it before reviewing — see `CONTRIBUTING.md`. A
contract change needs your explicit sign-off in the PR, not just an approve.

## 4. Standard review turnaround, Week 1

Given the 7-day timeline, reviews are same-day. If you can't review same-day,
say so in the channel immediately so the author isn't blocked overnight —
overnight blocks are the one thing the "no waiting" plan can't absorb.

## 5. What NOT to gate on

Don't block a Week-1 PR over:
- code style beyond what `ruff` catches
- missing incremental-sync support (full sync is acceptable if documented)
- test coverage below 85% on connector-specific code (the SDK itself holds
  that bar; a first-pass connector doesn't need to)

Save that feedback for the Day 7 regression pass, not Day 2–4 review.
