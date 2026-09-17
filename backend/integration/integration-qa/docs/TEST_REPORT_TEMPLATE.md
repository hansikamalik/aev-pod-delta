# Integration Squad — Final Test Report

**Sprint:** Week 1 — Integration
**QA Owner:** Bhawook Priyam
**Date:** <YYYY-MM-DD>
**Verdict:** PASS / FAIL / CONDITIONAL

## 1. Summary

| Metric | Value |
|---|---|
| Total tests | <n> |
| Passed / Failed / Skipped | <n> / <n> / <n> |
| Contract suite | PASS/FAIL (<n> connectors tested) |
| Integration suite | PASS/FAIL |
| Regression suite | PASS/FAIL |
| Coverage (module tests) | <n>% |
| CI status on main | green/red |
| Suite runtime | <n>s |

## 2. Results by workstream

| Workstream | Owner | Suite | Result | Notes |
|---|---|---|---|---|
| Connector contract | Harshal | tests/contract | | |
| Azure auth | Bhavesh K | tests/azure::TestAzureAuth | | |
| Azure discovery | Subramani | tests/azure::TestAzureDiscovery | | |
| Azure normalize/push | Ashwin | tests/azure::TestAzureNormalization, TestAzurePush | | |
| Splunk connector | Ayyappatadi | tests/splunk | | |
| Vault/scheduler/lock | Abhiram | tests/infra | | |
| End-to-end | all | tests/integration | | |

## 3. Defects found

| ID | Severity | Area | Description | Status |
|---|---|---|---|---|
| | | | | |

## 4. Weekly checklist verification

- [ ] Contract test passing for all connectors
- [ ] Azure auth + credentials tested
- [ ] Azure discovery (VM/Storage/AAD/SQL/Functions) tested
- [ ] Azure normalization + push tested
- [ ] Splunk auth, forwarding, normalization tested
- [ ] Vault: no credentials hardcoded (automated scan pass)
- [ ] Cron scheduling + distributed lock tested
- [ ] Integration + regression suites passing
- [ ] Documentation updated
- [ ] CI green, PRs merged

## 5. Sign-off

QA sign-off: ______________  Date: ______
Integration Lead sign-off: ______________  Date: ______
