<#
  Runs both halves of the sandbox from one place.
    .\run_all.ps1              # python tests, then TS typecheck + tests
    .\run_all.ps1 -PythonOnly
    .\run_all.ps1 -TsOnly
    .\run_all.ps1 -Serve       # just start the mock server on :8080 (Ctrl+C to stop)
#>
param([switch]$PythonOnly, [switch]$TsOnly, [switch]$Serve)

$root = $PSScriptRoot
$results = [ordered]@{}
function Step($t) { Write-Host "`n=== $t ===" -ForegroundColor Cyan }

function Ensure-PythonEnv {
    Push-Location "$root\python"
    if (-not (Test-Path ".venv")) { Step "Python: creating .venv"; python -m venv .venv }
    Step "Python: installing (editable + dev)"
    & .\.venv\Scripts\python.exe -m pip install -q -e ".[dev]"
    $ok = ($LASTEXITCODE -eq 0)
    Pop-Location
    return $ok
}

if ($Serve) {
    if (-not (Ensure-PythonEnv)) { Write-Host "install failed" -ForegroundColor Red; exit 1 }
    Push-Location "$root\python"
    Step "Mock server on http://127.0.0.1:8080  (try /health and /api/assets?scenario=success)"
    & .\.venv\Scripts\python.exe -m uvicorn mock_server.server:app --port 8080
    Pop-Location; exit 0
}

if (-not $TsOnly) {
    if (Ensure-PythonEnv) {
        Push-Location "$root\python"
        Step "Python: pytest"
        & .\.venv\Scripts\python.exe -m pytest -v
        $results["python  pytest"] = ($LASTEXITCODE -eq 0)
        Pop-Location
    } else { $results["python  install"] = $false }
}

if (-not $PythonOnly) {
    Push-Location "$root\ts"
    if (-not (Test-Path "node_modules")) { Step "TS: npm install"; npm install --no-audit --no-fund }
    if ($LASTEXITCODE -eq 0) {
        Step "TS: typecheck"; npm run typecheck
        $results["ts      typecheck"] = ($LASTEXITCODE -eq 0)
        Step "TS: vitest";    npm test
        $results["ts      vitest"] = ($LASTEXITCODE -eq 0)
    } else { $results["ts      install"] = $false }
    Pop-Location
}

Step "Summary"
foreach ($k in $results.Keys) {
    $c = if ($results[$k]) { "Green" } else { "Red" }
    Write-Host ("{0,-20} {1}" -f $k, $(if ($results[$k]) { "PASS" } else { "FAIL" })) -ForegroundColor $c
}
if ($results.Values -contains $false) { exit 1 }
