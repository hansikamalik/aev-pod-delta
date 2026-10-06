import json
import os
import sys
from pathlib import Path
from jinja2 import Template
from core.log_parser import LogParser
from core.vault_audit_checker import VaultAuditChecker
from core.classifier import SeverityClassifier

def load_config() -> dict:
    config_path = Path(__file__).parent / "config" / "triage_rules.json"
    with open(config_path, "r") as f:
        return json.load(f)

def render_markdown(template_str: str, failure: dict, vault_check: dict, classification: dict, owner: str) -> str:
    template = Template(template_str)
    return template.render(
        failure=failure,
        vault_check=vault_check,
        classification=classification,
        owner=owner
    )

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 triage_cli.py <path_to_execution_log.txt>")
        sys.exit(1)

    log_file = sys.argv[1]
    if not os.path.exists(log_file):
        print(f"Error: File '{log_file}' not found.")
        sys.exit(1)

    with open(log_file, "r") as f:
        raw_logs = f.read()

    config = load_config()
    checker = VaultAuditChecker(config["secret_blacklist_tokens"])
    
    # 1. Parse pytest and runbook outputs
    pytest_failures = LogParser.parse_pytest_output(raw_logs)
    runbook_failures = LogParser.parse_runbook_output(raw_logs)
    all_failures = pytest_failures + runbook_failures

    if not all_failures:
        print("\n No UAT defects or Vault Audit failures detected in execution logs.")
        sys.exit(0)

    # 2. Load Markdown template
    template_path = Path(__file__).parent / "templates" / "bug_report_template.md"
    with open(template_path, "r") as f:
        template_str = f.read()

    print(f"\n================ UAT BUG TRIAGE SUMMARY: {len(all_failures)} ISSUE(S) FOUND ================\n")

    output_dir = Path(__file__).parent / "reports"
    output_dir.mkdir(exist_ok=True)

    for idx, failure in enumerate(all_failures, 1):
        connector = failure.get("connector", "Core Framework")
        owner = config["connector_owners"].get(connector, "Core Sync Engine Team")
        
        vault_check = checker.inspect_unredacted_secrets(failure["traceback"])
        classification = SeverityClassifier.classify_defect(failure, vault_check)
        
        md_report = render_markdown(template_str, failure, vault_check, classification, owner)
        
        report_filename = output_dir / f"UAT_BUG_{connector}_{idx}.md"
        with open(report_filename, "w") as f:
            f.write(md_report)

        print(f"[{classification['severity']}] {connector}")
        print(f"  ├─ Category: {classification['category']}")
        print(f"  ├─ Owner:    {owner}")
        print(f"  └─ Report:   {report_filename}\n")

if __name__ == "__main__":
    main()
