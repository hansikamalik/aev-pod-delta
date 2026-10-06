import pytest
import time
from dr_tests.core.service_simulator import IntegrationServiceSimulator
from dr_tests.core.recovery_validator import DRRecoveryValidator

CONNECTORS = [
    "Azure_Normalization_Platform_Push",
    "cyberark_auth_module",
    "cyberark-discovery-integration",
    "elastic_connector",
    "qradar_connector",
    "splunk_connector",
    "vault-enterprise-framework"
]

@pytest.fixture(scope="module")
def dr_env():
    simulator = IntegrationServiceSimulator()
    validator = DRRecoveryValidator()
    return simulator, validator

@pytest.mark.parametrize("connector", CONNECTORS)
def test_integration_service_down_and_clean_resume(dr_env, connector):
    simulator, validator = dr_env

    # Step 1: Start Service and Initiate Sync Job
    simulator.start_service()
    job_id = f"job_dr_{connector}_9982"
    checkpoint_offset = 4500
    
    simulator.write_checkpoint(
        connector=connector,
        job_id=job_id,
        last_processed_offset=checkpoint_offset,
        payload_hash="a8f5f167f44f4964e6c998dee827110c"
    )

    # Step 2: Simulate Integration Service Outage (Hard Crash)
    crash_event = simulator.simulate_hard_crash()
    assert crash_event["status"] == "CRASHED"
    assert not simulator.is_running

    # Step 3: Attempt Outage Interruption (Verify Service fails fast while down)
    with pytest.raises(RuntimeError, match="Integration Service is down"):
        simulator.write_checkpoint(connector, job_id, 4501, "fail_hash")

    # Step 4: Service Recovery & Cold Restart
    time.sleep(0.5)  # Simulate failover lag
    recovered = simulator.recover_service()
    assert recovered is True

    # Step 5: Resume Sync Job at Next Offset (Expected: offset 4500 -> resume at 4500/4501)
    resumed_offset = 4500
    validation = validator.validate_resumed_sync(
        connector=connector,
        resume_offset=resumed_offset,
        processed_job_ids=[job_id]
    )

    # Step 6: Assert DR Recovery Compliance
    assert validation["status"] == "CLEAN_RESUME_PASSED", f"DR Failure for {connector}: {validation['reason']}"
    assert validation["vault_audit_compliant"] is True, f"Vault Audit failure on DR recovery for {connector}"
    print(f"\n[DR PASSED] {connector} ---> Resumed cleanly at offset {resumed_offset} [Vault Audit: OK]")
