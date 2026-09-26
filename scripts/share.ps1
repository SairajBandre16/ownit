# Share OwnIt from this PC through a free Cloudflare quick tunnel (no account, no card).
#
#   powershell -ExecutionPolicy Bypass -File scripts\share.ps1 -Site https://your-app.vercel.app
#
# Starts LanguageTool (:8010) and the API (:8000) if they aren't running, opens a tunnel to the
# API, and prints a public https address plus a share link for the website. The address is new
# every time. Press Ctrl+C to stop sharing; only the processes this script started are stopped.
#
# Options:
#   -Site <url>     your website (Vercel URL, or http://localhost:3000) for the share link
#   -NoGrammar      don't start LanguageTool (saves ~1 GB of memory; grammar checks are off)
#   -Minutes <n>    stop sharing automatically after n minutes (0 = until Ctrl+C)

param(
    [string]$Site = "",
    [switch]$NoGrammar,
    [int]$Minutes = 0
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root "backend"
$python = Join-Path $backend ".venv\Scripts\python.exe"
$tools = Join-Path $backend "data\tools"
$logs = Join-Path $backend "data\share-logs"
$cloudflared = Join-Path $tools "cloudflared.exe"
$cloudflaredUrl = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
New-Item -ItemType Directory -Force -Path $tools, $logs | Out-Null

function Test-Port([int]$port) {
    [bool](Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)
}

function Wait-Url([string]$url, [int]$seconds) {
    for ($i = 0; $i -lt $seconds; $i++) {
        try {
            Invoke-WebRequest -UseBasicParsing -TimeoutSec 3 -Uri $url | Out-Null
            return $true
        } catch {
            Start-Sleep -Seconds 1
        }
    }
    return $false
}

function Stop-Tree([int]$processId) {
    # the Java launcher and the venv Python both start child processes: stop the whole tree
    & taskkill.exe /T /F /PID $processId 2>$null | Out-Null
}

if (-not (Test-Path $python)) {
    throw "Backend environment not found ($python). Follow 'Quick start' in README.md first."
}

if (-not (Test-Path $cloudflared)) {
    Write-Host "Downloading cloudflared (one time, ~50 MB) ..."
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -UseBasicParsing -Uri $cloudflaredUrl -OutFile $cloudflared
}

$started = @()
try {
    # 1. LanguageTool
    if (-not $NoGrammar -and -not (Test-Port 8010)) {
        $lt = Get-ChildItem (Join-Path $backend "data\languagetool") -Directory -Filter "LanguageTool-*" -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($lt) {
            Write-Host "Starting LanguageTool ..."
            $p = Start-Process java -ArgumentList "-Xmx768m", "-cp", "languagetool-server.jar", "org.languagetool.server.HTTPServer", "--port", "8010" `
                -WorkingDirectory $lt.FullName -WindowStyle Hidden -PassThru `
                -RedirectStandardOutput (Join-Path $logs "languagetool.out.log") -RedirectStandardError (Join-Path $logs "languagetool.err.log")
            $started += $p
            if (-not (Wait-Url "http://127.0.0.1:8010/v2/languages" 90)) { Write-Warning "LanguageTool didn't start; grammar checks will be off." }
        } else {
            Write-Warning "LanguageTool isn't installed (scripts\download_resources.py --languagetool); grammar checks will be off."
        }
    }

    # 2. API
    if (-not (Test-Port 8000)) {
        Write-Host "Starting the OwnIt API ..."
        if ($NoGrammar) { $env:OWNIT_LANGUAGETOOL = "0" }
        $p = Start-Process $python -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000" `
            -WorkingDirectory $backend -WindowStyle Hidden -PassThru `
            -RedirectStandardOutput (Join-Path $logs "api.out.log") -RedirectStandardError (Join-Path $logs "api.err.log")
        $started += $p
        if (-not (Wait-Url "http://127.0.0.1:8000/health" 180)) { throw "The API didn't start. See $logs\api.err.log" }
    }
    Write-Host ("Local API: " + (Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:8000/health").Content)

    # 3. tunnel
    Write-Host "Opening the Cloudflare tunnel ..."
    $cfLog = Join-Path $logs "cloudflared.log"
    Remove-Item $cfLog -ErrorAction SilentlyContinue
    $cf = Start-Process $cloudflared -ArgumentList "tunnel", "--no-autoupdate", "--url", "http://127.0.0.1:8000" `
        -WindowStyle Hidden -PassThru -RedirectStandardError $cfLog -RedirectStandardOutput (Join-Path $logs "cloudflared.out.log")
    $started += $cf

    $public = $null
    for ($i = 0; $i -lt 60 -and -not $public; $i++) {
        Start-Sleep -Seconds 1
        if (Test-Path $cfLog) {
            $m = Select-String -Path $cfLog -Pattern "https://[a-z0-9-]+\.trycloudflare\.com" | Select-Object -First 1
            if ($m) { $public = $m.Matches[0].Value }
        }
    }
    if (-not $public) { throw "No tunnel address yet. See $cfLog" }
    # a brand-new trycloudflare.com name can take a minute or two to resolve
    Write-Host "Waiting for the address to go live ..."
    if (-not (Wait-Url "$public/health" 150)) {
        Write-Warning "This PC can't reach the new address yet (DNS). It usually works for others already; try it again in a minute."
    }

    Write-Host ""
    Write-Host "OwnIt is shared at:  $public" -ForegroundColor Green
    if ($Site) {
        $link = $Site.TrimEnd("/") + "/?api=" + [Uri]::EscapeDataString($public)
        Write-Host "Share this link:     $link" -ForegroundColor Green
    } else {
        Write-Host "Open your website with  ?api=$public  added to its address,"
        Write-Host "or paste the address into 'Server' in the website's top bar."
    }
    Write-Host ""
    if ($Minutes -gt 0) { Write-Host "Sharing for $Minutes minute(s). Ctrl+C stops it sooner." } else { Write-Host "Press Ctrl+C to stop sharing." }

    $deadline = if ($Minutes -gt 0) { (Get-Date).AddMinutes($Minutes) } else { [DateTime]::MaxValue }
    while ((Get-Date) -lt $deadline) {
        if ($cf.HasExited) { throw "The tunnel stopped. See $cfLog" }
        Start-Sleep -Seconds 2
    }
} finally {
    Write-Host "Stopping ..."
    foreach ($p in $started) { Stop-Tree $p.Id }
}
