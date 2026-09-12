$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root

Write-Host "===== ContextIQ release checks ====="

python -m compileall -q backend frontend ai tests
if ($LASTEXITCODE -ne 0) { throw "Compile check failed" }

python -m pytest -q
if ($LASTEXITCODE -ne 0) { throw "Tests failed" }

$forbidden = git ls-files | Select-String -Pattern "(^|/)credentials/|(^|/)data/google_tokens/|(^|/)data/gmail/|(^|/)data/attachments/|(^|/)\.env$|token\.json$|\.db$|\.sqlite"
if ($forbidden) {
    $forbidden
    throw "Forbidden runtime/secret file is tracked by Git"
}

if (git diff --check) { }
if ($LASTEXITCODE -ne 0) { throw "git diff --check failed" }

Write-Host "PASS: compile, tests, secret-path gate and diff checks"
