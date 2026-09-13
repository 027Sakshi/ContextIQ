$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root

Write-Host "===== ContextIQ release checks ====="

python -m pip check
if ($LASTEXITCODE -ne 0) { throw "Dependency check failed" }

python -m compileall -q backend frontend ai tests scripts
if ($LASTEXITCODE -ne 0) { throw "Compile check failed" }

python -m pytest -q
if ($LASTEXITCODE -ne 0) { throw "Tests failed" }

$forbidden = git ls-files | Select-String -Pattern "(^|/)credentials/|(^|/)data/google_tokens/|(^|/)data/gmail/|(^|/)data/attachments/|(^|/)\.env$|token\.json$|\.db$|\.sqlite"
if ($forbidden) {
    $forbidden
    throw "Forbidden runtime/secret file is tracked by Git"
}

$openAIRefs = Get-ChildItem backend,frontend,scripts -Recurse -File -Filter *.py | Select-String -Pattern "from openai|import openai"
$openAIReq = Select-String -Path requirements.txt -Pattern "openai==" -ErrorAction SilentlyContinue
if ($openAIRefs -or $openAIReq) {
    $openAIRefs
    $openAIReq
    throw "Legacy OpenAI client reference remains in production code"
}

if (git diff --check) { }
if ($LASTEXITCODE -ne 0) { throw "git diff --check failed" }

$dirty = git status --porcelain
if ($dirty) {
    $dirty
    throw "Working tree is not clean"
}

Write-Host "PASS: dependencies, compile, tests, native Gemini gate, secret-path gate and clean tree"
