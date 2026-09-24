#!/usr/bin/env python3
import os
import re

SEARCH_DIR = "."
DEPRECATED_DATETIME_PATTERN = re.compile(r"datetime\.utcnow\(\)")
UNGUARDED_SECRET_PATTERN = re.compile(r"((\"|')(bearer_token|api_key|password|secret)(\"|')\s*:\s*(\"|')[^\"']+(\"|'))")


def run_vault_audit():
    print("=== Starting Vault-Audit Pass across Connectors ===")
    violations = 0

    for root, _, files in os.walk(SEARCH_DIR):
        if "venv" in root or ".pytest_cache" in root or ".git" in root:
            continue
            
        for file in files:
            if not file.endswith(".py"):
                continue
                
            filepath = os.path.join(root, file)
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()

            for line_num, line in enumerate(lines, start=1):
                if DEPRECATED_DATETIME_PATTERN.search(line):
                    print(f"[FAIL] [Deprecated Datetime] {filepath}:{line_num} -> Use datetime.now(timezone.utc)")
                    violations += 1

                if "tests/" not in filepath and UNGUARDED_SECRET_PATTERN.search(line):
                    print(f"[WARN] [Possible Hardcoded Secret] {filepath}:{line_num} -> Verify secret sourcing from Vault")
                    violations += 1

    print("-----------------------------------------------------------------")
    if violations == 0:
        print("✓ Audit passed cleanly! Zero violations detected across all connector code.")
    else:
        print(f"✗ Found {violations} total issue(s) requiring remediation.")


if __name__ == "__main__":
    run_vault_audit()
