<#
  Week 4 build verification: build both SDK images clean, run each, and
  assert the sample connector actually reports SUCCESS.
    .\verify_docker.ps1
#>
$root = $PSScriptRoot
$fail = $false

function Check($Name, $Dir, $Image) {
    Write-Host "`n=== ${Name}: docker build (--no-cache) ===" -ForegroundColor Cyan
    docker build --no-cache -t $Image $Dir
    if ($LASTEXITCODE -ne 0) {
        Write-Host "FAIL  $Name  (build failed)" -ForegroundColor Red
        $script:fail = $true; return
    }

    Write-Host "=== ${Name}: docker run ===" -ForegroundColor Cyan
    $out = docker run --rm $Image
    $code = $LASTEXITCODE
    $out | Write-Host

    if ($code -ne 0) {
        Write-Host "FAIL  $Name  (exit code $code)" -ForegroundColor Red
        $script:fail = $true; return
    }
    if (-not ($out -match '"status":\s*"success"')) {
        Write-Host "FAIL  $Name  (exit 0 but status was not success)" -ForegroundColor Red
        $script:fail = $true; return
    }
    Write-Host "PASS  $Name" -ForegroundColor Green
}

Check "python-sdk" "$root\python" "connector-sdk-python:verify"
Check "ts-sdk"     "$root\ts"     "connector-sdk-ts:verify"

Write-Host ""
if ($fail) { Write-Host "FAILURES (see above)" -ForegroundColor Red; exit 1 }
else { Write-Host "ALL PASS" -ForegroundColor Green }
