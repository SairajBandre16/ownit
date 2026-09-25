# Start the full OwnIt stack natively on Windows (no Docker needed):
#   LanguageTool (Java) on :8010, FastAPI backend on :8000, Next.js frontend on :3000.
#
#   powershell -ExecutionPolicy Bypass -File scripts\dev.ps1
#
# Each service opens in its own window. Close the windows to stop them.

$root = Split-Path -Parent $PSScriptRoot
$lt = Get-ChildItem "$root\backend\data\languagetool" -Directory -Filter "LanguageTool-*" -ErrorAction SilentlyContinue | Select-Object -First 1

if ($lt) {
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$($lt.FullName)'; java -cp languagetool-server.jar org.languagetool.server.HTTPServer --port 8010 --allow-origin '*'"
} else {
    Write-Warning "LanguageTool not found. Run: backend\.venv\Scripts\python backend\scripts\download_resources.py --languagetool"
}

Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\backend'; .\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\frontend'; npm run dev"

Write-Host "Frontend: http://localhost:3000   API: http://localhost:8000/docs"
