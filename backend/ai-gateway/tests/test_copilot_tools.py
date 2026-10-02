from app import tools


def call(name, args, role="admin", user_id="hansika"):
    return tools.dispatch_tool(name, args, user_id=user_id, role=role)


def test_all_four_tools_are_registered_and_advertised():
    names = {s["name"] for s in tools.get_tool_schemas()}
    assert {"workflow_assist", "policy_check", "audit_query", "integration_list"} <= names


# --- workflow_assist ---

def test_workflow_list():
    r = call("workflow_assist", {"action": "list"})
    assert r["ok"] and any(w["workflow_id"] == "isolate_host" for w in r["result"]["workflows"])


def test_workflow_run_defaults_to_dry_run():
    r = call("workflow_assist", {"action": "run", "workflow_id": "rescan_asset", "params": {"asset_id": "db-prod-01"}})
    assert r["ok"] and r["result"]["status"] == "dry_run"


def test_workflow_real_run_records_who_started_it():
    r = call(
        "workflow_assist",
        {"action": "run", "workflow_id": "rescan_asset", "params": {"asset_id": "db-prod-01"}, "dry_run": False},
    )
    assert r["result"]["status"] == "started"
    assert r["result"]["started_by"] == "hansika"


def test_workflow_run_missing_params_is_an_error():
    r = call("workflow_assist", {"action": "run", "workflow_id": "isolate_host"})
    assert r["ok"] is False and "host_id" in r["error"]


def test_workflow_invalid_action_rejected_by_schema():
    r = call("workflow_assist", {"action": "delete_everything"})
    assert r["ok"] is False


# --- policy_check ---

def test_policy_check_finds_violations():
    r = call("policy_check", {"resource_type": "storage_bucket", "config": {"public_access": True, "encrypted": True}})
    assert r["ok"] and r["result"]["compliant"] is False
    assert [v["policy_id"] for v in r["result"]["violations"]] == ["pol-no-public-access"]


def test_policy_check_compliant_resource():
    r = call("policy_check", {"resource_type": "user_account", "config": {"mfa_enabled": True}})
    assert r["result"]["compliant"] is True


def test_policy_check_unknown_resource_type_rejected():
    assert call("policy_check", {"resource_type": "toaster", "config": {}})["ok"] is False


# --- audit_query ---

def test_audit_query_filters_by_resource_and_window():
    r = call("audit_query", {"resource": "firewall", "since_days": 7})
    assert r["ok"] and r["result"]["count"] == 1
    assert r["result"]["entries"][0]["actor"] == "hansika"


def test_audit_query_rejects_out_of_range_window():
    assert call("audit_query", {"since_days": 500})["ok"] is False


def test_audit_query_wrong_type_rejected():
    assert call("audit_query", {"since_days": "7"})["ok"] is False


# --- integration_list ---

def test_integration_list_and_status_filter():
    assert call("integration_list", {})["result"]["count"] >= 3
    r = call("integration_list", {"status": "error"})
    assert [i["name"] for i in r["result"]["integrations"]] == ["Okta"]


# --- RBAC ---

def test_viewer_can_list_integrations_but_not_query_audit_or_run_workflows():
    assert call("integration_list", {}, role="viewer")["ok"] is True
    assert "not permitted" in call("audit_query", {}, role="viewer")["error"]
    assert "not permitted" in call("workflow_assist", {"action": "list"}, role="viewer")["error"]


def test_auditor_can_query_audit_but_not_run_workflows():
    assert call("audit_query", {}, role="auditor")["ok"] is True
    assert call("workflow_assist", {"action": "list"}, role="auditor")["ok"] is False
