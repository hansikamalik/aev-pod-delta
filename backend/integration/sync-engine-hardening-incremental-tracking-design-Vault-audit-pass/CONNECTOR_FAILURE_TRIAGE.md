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
