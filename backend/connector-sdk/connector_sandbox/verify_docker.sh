#!/usr/bin/env bash
# Week 4 build verification: build both SDK images clean, run each, and
# assert the sample connector actually reports SUCCESS -- not just that
# `docker build` didn't error.
set -u
root="$(cd "$(dirname "$0")" && pwd)"
fail=0

check() {
  local name="$1" dir="$2" image="$3"
  echo; echo "=== $name: docker build (--no-cache) ==="
  if ! docker build --no-cache -t "$image" "$dir"; then
    echo "FAIL  $name  (build failed)"; fail=1; return
  fi

  echo "=== $name: docker run ==="
  local out; out="$(docker run --rm "$image")"
  local code=$?
  echo "$out"

  if [ $code -ne 0 ]; then
    echo "FAIL  $name  (exit code $code)"; fail=1; return
  fi
  if ! echo "$out" | grep -q '"status": *"success"'; then
    echo "FAIL  $name  (exit 0 but status was not success)"; fail=1; return
  fi
  echo "PASS  $name"
}

check "python-sdk" "$root/python" "connector-sdk-python:verify"
check "ts-sdk"     "$root/ts"     "connector-sdk-ts:verify"

echo
[ $fail -eq 0 ] && echo "ALL PASS" || echo "FAILURES (see above)"
exit $fail
