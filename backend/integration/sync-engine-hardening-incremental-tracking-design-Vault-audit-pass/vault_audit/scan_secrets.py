"""
Early Vault-audit pass (Week 3 groundwork).

Scans every connector's source for:
  1. Hardcoded secret-looking assignments (password=, api_key=, token=, ...)
  2. Secrets logged or included in exception messages
  3. Credentials that bypass the Vault client (e.g. read directly from
     os.environ instead of going through the shared vault module)

This is a static first pass, not a replacement for a manual review.
Every hit should be triaged by a human and recorded in FINDINGS.md.
"""

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List

SECRET_ASSIGNMENT = re.compile(
    r"""(?ix)
    \b(password|passwd|secret|api[_-]?key|access[_-]?key|client[_-]?secret|
       auth[_-]?token|private[_-]?key|token)\b
    \s*[:=]\s*
    ['"][^'"\s]{4,}['"]
    """
)

ENV_BYPASS = re.compile(r"(?i)os\.environ(\.get)?\(\s*['\"](.*(SECRET|PASSWORD|KEY|TOKEN).*)['\"]")

LOG_WITH_SECRET_VAR = re.compile(
    r"(?i)(log(ger)?\.\w+|print)\s*\([^)]*\b(password|secret|api_key|token)\b"
)

EXCLUDED_DIR_NAMES = {".git", "__pycache__", "node_modules", "venv", ".venv"}
EXCLUDED_FILE_PREFIXES = ("test_",)


@dataclass
class Finding:
    path: str
    line_no: int
    line: str
    rule: str


def scan_file(path: Path) -> List[Finding]:
    findings: List[Finding] = []
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return findings

    for line_no, line in enumerate(text.splitlines(), start=1):
        if SECRET_ASSIGNMENT.search(line):
            findings.append(Finding(str(path), line_no, line.strip(), "hardcoded_secret"))
        if ENV_BYPASS.search(line):
            findings.append(Finding(str(path), line_no, line.strip(), "env_bypasses_vault"))
        if LOG_WITH_SECRET_VAR.search(line):
            findings.append(Finding(str(path), line_no, line.strip(), "secret_in_log"))

    return findings


def scan_directory(root: Path) -> List[Finding]:
    findings: List[Finding] = []
    for path in root.rglob("*.py"):
        if any(part in EXCLUDED_DIR_NAMES for part in path.parts):
            continue
        if path.name.startswith(EXCLUDED_FILE_PREFIXES):
            continue
        findings.extend(scan_file(path))
    return findings


def main() -> None:
    parser = argparse.ArgumentParser(description="Early Vault-audit static scan")
    parser.add_argument(
        "root",
        nargs="?",
        default=".",
        help="Directory to scan (default: current directory, e.g. backend/integration)",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    findings = scan_directory(root)

    if not findings:
        print(f"No obvious issues found under {root}")
        return

    print(f"{len(findings)} potential issue(s) found under {root}:\n")
    for f in findings:
        print(f"[{f.rule}] {f.path}:{f.line_no}\n    {f.line}\n")


if __name__ == "__main__":
    main()
