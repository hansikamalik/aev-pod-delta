# Connector Failure-Triage Runbook

## Owner
Bhawook

## Connectors
- Google Workspace
- Microsoft 365

## 1. Purpose
Provide a consistent process for investigating connector failures,
recording evidence, and escalating unresolved issues.

## 2. Initial Checks
1. Identify the affected connector and the time of failure.
2. Record the command or test that failed.
3. Capture the complete error message and traceback.
4. Check whether authentication or API access is failing.
5. Check whether the failure occurred during discovery, ingestion,
   normalization, synchronization, or platform push.
6. Check the previous checkpoint and whether it changed after the run.

## 3. Google Workspace
Previously observed regression status: 6 failures.

1. Run the Google Workspace regression tests.
2. Save the complete test output.
3. Record each failing test and its error message.
4. Check authentication, event retrieval, deduplication, platform push,
   and checkpoint behavior.
5. Do not advance a checkpoint after an unsuccessful push unless the
   documented sync-engine design explicitly permits it.
6. Escalate unresolved failures with the test output and reproduction steps.

## 4. Microsoft 365
Previously observed regression status: 3 failures and 2 errors.

1. Run the Microsoft 365 regression tests.
2. Save the complete test output.
3. Record each failing test and its error message.
4. Check authentication, event retrieval, platform push, and checkpoint behavior.
5. Confirm that asynchronous calls are awaited where required.
6. Escalate unresolved failures with the test output and reproduction steps.

## 5. Recovery and Checkpoint Safety
1. Record the checkpoint before a test run.
2. Trigger or reproduce the failure in a test environment.
3. Verify whether the sync operation reports success, partial failure, or failure.
4. Check whether the checkpoint advanced.
5. Retry only after confirming that retrying is safe.
6. Verify that repeated processing does not create duplicate records.
7. Treat full service-restart recovery as unverified until a dedicated DR test passes.

## 6. Monitoring
1. Run the monitoring health tests.
2. Record the result and timestamp.
3. Capture relevant errors and available metrics.
4. Escalate missing or misleading monitoring information.

## 7. Evidence to Record
For every incident, record:
- Connector name
- Date and time
- Test or operation performed
- Expected behavior
- Actual behavior
- Error message
- Checkpoint before and after
- Retry result
- Related logs or test output
- Owner and follow-up action

## 8. Escalation
Escalate unresolved authentication, API, checkpoint, data integrity,
monitoring, or recovery problems to the relevant connector or sync-engine owner.

## 9. Current Outstanding Items
- Google Workspace regression: 6 failures previously reported; re-test required.
- Microsoft 365 regression: 3 failures and 2 errors previously reported; re-test required.
- Full Integration service-restart DR test: pending verification.
- Distributed-lock implementation: not confirmed by source search.
- Credential rotation: formal sign-off pending.
- UAT bug triage and closure: pending confirmation.

## 10. Sign-Off
Do not mark a connector fully regression-approved until its required regression
tests pass and the results are recorded. Record formal DR and credential-rotation
sign-offs separately.

## Disaster Recovery (DR) Test Status

- **Engine restart simulation:** PASSED.
- **Checkpoint recovery:** Verified using a newly created sync-engine instance and the same mock platform client.
- **Checkpoint resumption:** The test confirmed that the next incremental sync starts from the saved checkpoint when the lookback buffer is zero.
- **Real Integration service restart:** PENDING.
- **Production checkpoint durability:** NOT VERIFIED.
- **Distributed lock recovery:** NOT VERIFIED.

The passing test validates simulated engine recreation only. It does not establish that sync jobs resume successfully after a real Integration service outage.

### Remaining DR Actions

1. Stop or simulate the failure of the Integration service in a controlled test environment.
2. Restart the service and verify that sync jobs resume from their saved checkpoints.
3. Confirm that events are not lost or incorrectly duplicated.
4. Record logs, checkpoint values, and test results.
5. Obtain sign-off after the actual DR test passes.

## Credential Rotation Sign-off Status

**Responsible person:** Harshal Sahare
**Status:** PENDING FORMAL SIGN-OFF

### Verification checklist

- [ ] Confirm that connector credentials are retrieved through the approved Vault integration.
- [ ] Verify that no credentials are hardcoded in source code or configuration files.
- [ ] Perform a credential rotation test in an approved test environment.
- [ ] Confirm that connectors authenticate successfully after rotation.
- [ ] Verify that sync jobs continue successfully after credentials are rotated.
- [ ] Confirm that credential access and rotation events are logged as required.
- [ ] Record the test results and obtain formal sign-off from Harshal Sahare.

**Current evidence:** Formal credential rotation sign-off has not yet been confirmed in the available project records.

**Important:** This item remains pending until the rotation test has been executed, its results documented, and the responsible person has approved the outcome. Passing regression tests alone does not prove that credential rotation has passed.

## Final Regression Status

### Verified Passing Tests
- Monitoring health regression tests: PASSED.
- Full regression test suite: PASSED.
- Vault audit tests: PASSED.
- Sync-engine tests: PASSED, including the simulated restart recovery test.

### Outstanding Connector Regression Issues
- Google Workspace: Six regression test failures remain unresolved.
- Microsoft 365: The previously recorded run had 21 passed, 3 failed, and 2 errors. The coroutine/high-water-mark issue and missing VaultClient  argument remain unresolved.

### Disaster Recovery
- Simulated sync-engine restart and recovery test: PASSED.
- Actual Integration service outage and restart test: PENDING.
- Durable production checkpoint recovery and distributed-lock recovery: NOT VERIFIED.

### Credential Rotation
- Formal sign-off owner: Harshal Sahare.
- Status: PENDING FORMAL SIGN-OFF.
- Credential rotation testing and approval must be documented before this item is marked complete.

### Go-Live Readiness
**Status: NOT YET FULLY VERIFIED.**

The supporting tests pass, but outstanding connector failures, the real-service disaster recovery test, and formal credential rotation sign-off must be addressed or explicitly accepted by the responsible project owners before go-live readiness can be confirmed.

These results do not establish that all 21 connectors have passed regression.
