# Week 3 Status — Integration Squad (Sep 18 – Sep 24)

**Lead:** Harshal Sahare · **Pod Delta, M4** · Halfway milestone week

## Lead deliverables

| Deliverable | Status | Evidence |
| --- | --- | --- |
| Webhook (custom) connector — URL/auth/signing | Done | `signing.py`, `auth.py`, `config.py` |
| Per-event subscription | Done | `subscriptions.py`, `POST/GET/PATCH/DELETE /subscriptions` |
| Retry | Done | `retry.py`, `client.py` — backoff + jitter, dead-lettering |
| Delivery log | Done | `delivery_log.py`, `GET /deliveries`, manual redelivery |
| Connector-interface-stability doc | Done | `docs/CONNECTOR_INTERFACE_STABILITY.md` |
| Squad-wide coordination | Ongoing | See squad table below |

Quality gates: `ruff check` clean, 86 tests passing, zero network egress in CI.

## Squad table

| Member | Week 3 task | Depends on |
| --- | --- | --- |
| Bhavesh Kanekar | GitLab (full) | Vault access |
| Ashwin | HashiCorp Vault (full) — 2nd connector | CyberArk experience |
| Bhawook | Microsoft 365 (full) — 2nd connector | Google Workspace experience |
| Harshal Sahare | Webhook (custom) + interface doc | All connectors built |
| Subramani, Kumar Ayyappa Swamy Tadi, Abhiram | Sync-engine groundwork + early Vault audit | — |

## Week 3 checklist (Integration scope)

- [x] All 21 connectors + the custom webhook built and in staging
- [x] Connector interface frozen and documented; RFC path defined for changes
- [x] Webhook signing verified against tamper, replay, and rotation cases
- [x] Delivery log retention aligned with the `ai_interactions` 1-year rule
- [ ] All Week 3 work merged to `develop` with CI green

## Cross-squad notes

- **Connector SDK (Likith TV):** the webhook's method-for-method conformance is
  the reference case for the TS parity check. Interface changes now need the SDK
  lead's sign-off per §4 of the stability doc.
- **AI Gateway:** `integration_list` reads connector `name` and `version`, both
  of which are now frozen identifiers.

## Carried into Week 4

- Wire the delivery log to Postgres (the in-memory store is sandbox/test only).
- Move retry from in-process backoff onto the sync engine's scheduler using
  `due_for_retry()`.
- Vault audit pass across all 21 connectors.
