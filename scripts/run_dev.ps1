$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root

if (!(Test-Path ".\.venv\Scripts\python.exe")) {
    throw "Virtual environment not found. Run: py -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt"
}

$python = Join-Path $Root ".venv\Scripts\python.exe"
$streamlit = Join-Path $Root ".venv\Scripts\streamlit.exe"

Write-Host "Starting ContextIQ API on http://127.0.0.1:8000"
$api = Start-Process -FilePath $python -ArgumentList @("-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", "8000") -PassThru

try {
    Start-Sleep -Seconds 2
    Write-Host "Starting ContextIQ Streamlit on http://localhost:8501"
    & $streamlit run frontend/app.py --server.port 8501
}
finally {
    if ($api -and !$api.HasExited) {
        Stop-Process -Id $api.Id -Force
    }
}
