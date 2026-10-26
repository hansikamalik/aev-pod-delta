# Microsoft 365 Regression Status

## Earlier test run
The saved test-results file reports a collection error:
ModuleNotFoundError: No module named 'sync_engine'

The tests did not complete in this run because the shared sync-engine
package was not importable from the Microsoft 365 connector test environment.

## Later test run
A subsequent run with PYTHONPATH configured collected and executed tests.

Reported result:
- 21 passed
- 3 failed
- 2 errors

The failures and errors remain outstanding and require investigation.


cat > ../microsoft365-connector/REGRESSION_STATUS.md <<'EOF'
# Microsoft 365 Regression Status

## Earlier test run
The saved test-results file reports a collection error:
ModuleNotFoundError: No module named 'sync_engine'

The tests did not complete in this run because the shared sync-engine
package was not importable from the Microsoft 365 connector test environment.

## Later test run
A subsequent run with PYTHONPATH configured collected and executed tests.

Reported result:
- 21 passed
- 3 failed
- 2 errors

The failures and errors remain outstanding and require investigation.

## Current status
Regression sign-off: BLOCKED

Do not mark the Microsoft 365 connector fully regression-approved until
the import environment is reproducible and the required regression tests pass.
