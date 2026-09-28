#!/usr/bin/env bash
# ./run_all.sh [--python-only|--ts-only|--serve]
set -u
root="$(cd "$(dirname "$0")" && pwd)"; mode="${1:-all}"; fail=0
step() { printf '\n=== %s ===\n' "$1"; }

py_env() {
  cd "$root/python" || return 1
  [ -d .venv ] || { step "Python: creating .venv"; python3 -m venv .venv; }
  step "Python: installing (editable + dev)"
  .venv/bin/python -m pip install -q -e ".[dev]"
}

if [ "$mode" = "--serve" ]; then
  py_env || exit 1
  step "Mock server on http://127.0.0.1:8080"
  exec .venv/bin/python -m uvicorn mock_server.server:app --port 8080
fi

if [ "$mode" != "--ts-only" ]; then
  if py_env; then step "Python: pytest"; (cd "$root/python" && .venv/bin/python -m pytest -v) || fail=1
  else echo "python install failed"; fail=1; fi
fi

if [ "$mode" != "--python-only" ]; then
  cd "$root/ts" || exit 1
  [ -d node_modules ] || { step "TS: npm install"; npm install --no-audit --no-fund; }
  step "TS: typecheck"; npm run typecheck || fail=1
  step "TS: vitest";    npm test || fail=1
fi

step "Summary"; [ $fail -eq 0 ] && echo "ALL PASS" || echo "FAILURES (see above)"
exit $fail
