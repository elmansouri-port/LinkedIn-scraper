<# 2>NUL
@echo off
chcp 65001 > nul 2>&1
powershell -NoProfile -ExecutionPolicy Bypass -File "%~f0" %*
exit /b %ERRORLEVEL%
#>

# ================================================================
#  LinkedIn Scraper - One-Click Setup & Launch
#  Double-click start.bat  -or-  right-click > Run with PowerShell
# ================================================================
#  Flags:
#    --Reconfigure   Re-run the setup wizard
#    --Update        Reinstall / update Python packages
#    --Help          Show usage
# ================================================================

param(
    [switch]$Reconfigure,
    [switch]$Update,
    [switch]$Help
)

Set-StrictMode -Off
$ErrorActionPreference = "Stop"

# ---- Paths ---------------------------------------------------
$ROOT        = Split-Path -Parent $MyInvocation.MyCommand.Path
$VENV        = Join-Path $ROOT "venv"
$PY_VENV     = Join-Path $VENV "Scripts\python.exe"
$PIP_VENV    = Join-Path $VENV "Scripts\pip.exe"
$REQS        = Join-Path $ROOT "requirements.txt"
$ENV_FILE    = Join-Path $ROOT ".env"
$ENV_EXAMPLE = Join-Path $ROOT ".env.example"
$LOG_DIR     = Join-Path $ROOT "data\logs"
$SRV_LOG     = Join-Path $LOG_DIR "server.log"
$STAMP       = Join-Path $VENV ".setup_ok"

# ---- Console -------------------------------------------------
$Host.UI.RawUI.WindowTitle = "LinkedIn Scraper"
try { $Host.UI.RawUI.BufferSize  = New-Object System.Management.Automation.Host.Size(120, 3000) } catch {}
try { $Host.UI.RawUI.WindowSize  = New-Object System.Management.Automation.Host.Size(
        [Math]::Min(110, $Host.UI.RawUI.MaxWindowSize.Width), 38) } catch {}

# ---- Output helpers ------------------------------------------
function hdr([string]$t) { Write-Host ""; Write-Host "  >> $t" -ForegroundColor Cyan }
function ok([string]$t)  { Write-Host "     [OK]  $t" -ForegroundColor Green }
function inf([string]$t) { Write-Host "           $t" -ForegroundColor DarkGray }
function warn([string]$t){ Write-Host "     [!]   $t" -ForegroundColor Yellow }
function err([string]$t) {
    Write-Host ""
    Write-Host "  +--------------------------------------------------+" -ForegroundColor Red
    Write-Host "  |  ERROR: $t" -ForegroundColor Red
    Write-Host "  +--------------------------------------------------+" -ForegroundColor Red
    Write-Host ""
}
function divider { Write-Host "  ----------------------------------------------------------" -ForegroundColor DarkGray }
function pause-exit([int]$c=1) {
    Write-Host ""
    Write-Host "  Press any key to close..." -ForegroundColor DarkGray
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit $c
}

# ---- Banner --------------------------------------------------
function banner {
    Clear-Host
    Write-Host ""
    Write-Host "  +=========================================================+" -ForegroundColor Blue
    Write-Host "  |                                                         |" -ForegroundColor Blue
    Write-Host "  |   " -ForegroundColor Blue -NoNewline
    Write-Host "LinkedIn Scraper" -ForegroundColor Cyan -NoNewline
    Write-Host "  -  Automated Prospecting Suite" -ForegroundColor White -NoNewline
    Write-Host "   |" -ForegroundColor Blue
    Write-Host "  |                                                         |" -ForegroundColor Blue
    Write-Host "  +=========================================================+" -ForegroundColor Blue
    Write-Host ""
}

# ---- Help ----------------------------------------------------
if ($Help) {
    banner
    Write-Host "  Usage:" -ForegroundColor White
    Write-Host "    start.bat                   Normal launch (runs setup on first use)"
    Write-Host "    start.bat --Reconfigure     Re-run the configuration wizard"
    Write-Host "    start.bat --Update          Reinstall / upgrade Python packages"
    Write-Host ""
    pause-exit 0
}

# ==============================================================
#  PYTHON DETECTION
# ==============================================================
function find-python {
    foreach ($cmd in @("py", "python3", "python")) {
        try {
            $v = & $cmd --version 2>&1
            if ($v -match 'Python\s+(\d+)\.(\d+)') {
                if ([int]$Matches[1] -ge 3 -and [int]$Matches[2] -ge 8) { return $cmd }
            }
        } catch {}
    }
    return $null
}

function install-python {
    Write-Host ""
    Write-Host "  Python was not found on this computer." -ForegroundColor Yellow
    Write-Host "  Python is free and needed to run the scraper." -ForegroundColor White
    Write-Host ""
    Write-Host "   [1]  Auto-install via Windows Package Manager  (easiest)" -ForegroundColor Cyan
    Write-Host "   [2]  Open python.org download page in browser" -ForegroundColor White
    Write-Host "   [3]  Cancel" -ForegroundColor DarkGray
    Write-Host ""
    $c = (Read-Host "  Your choice").Trim()
    switch ($c) {
        "1" {
            hdr "Auto-installing Python 3.11 via winget..."
            try {
                winget install --id Python.Python.3.11 --source winget --silent `
                    --accept-package-agreements --accept-source-agreements | Out-Null
                $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") +
                            ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
                ok "Python installed. Continuing setup..."
                return $true
            } catch {
                warn "Winget install failed. Try option [2] to install manually."
                return $false
            }
        }
        "2" {
            Start-Process "https://www.python.org/downloads/windows/"
            Write-Host ""
            Write-Host "  Instructions:" -ForegroundColor White
            Write-Host "   1. Download the latest Python 3.x installer" -ForegroundColor Gray
            Write-Host "   2. Run it, and CHECK the box 'Add Python to PATH'" -ForegroundColor Yellow
            Write-Host "   3. After install, close this window and run start.bat again" -ForegroundColor Gray
            Write-Host ""
            pause-exit 0
        }
        default { pause-exit 0 }
    }
    return $false
}

# ==============================================================
#  .ENV HELPERS
# ==============================================================
function get-env([string]$key) {
    if (-not (Test-Path $ENV_FILE)) { return "" }
    $line = Get-Content $ENV_FILE -ErrorAction SilentlyContinue |
            Where-Object { $_ -match ('^\s*' + [regex]::Escape($key) + '\s*=') } |
            Select-Object -First 1
    if (-not $line) { return "" }
    return (($line -split "=", 2)[1] -replace '\s*#.*$', '').Trim()
}

function set-env([string]$key, [string]$value) {
    $raw = if (Test-Path $ENV_FILE) { Get-Content $ENV_FILE -Raw -ErrorAction SilentlyContinue } else { "" }
    if (-not $raw) { $raw = "" }
    $pattern = '(?m)^\s*' + [regex]::Escape($key) + '\s*=.*'
    if ($raw -match $pattern) {
        $raw = $raw -replace $pattern, "$key=$value"
    } else {
        $raw = $raw.TrimEnd() + "`n$key=$value"
    }
    $raw | Set-Content -Path $ENV_FILE -Encoding UTF8 -NoNewline
}

function new-apikey {
    $pool = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return -join (1..40 | ForEach-Object { $pool[(Get-Random -Maximum $pool.Length)] })
}

# ---- Input prompts -------------------------------------------
function ask([string]$prompt, [string]$cur="") {
    while ($true) {
        if ($cur) { Write-Host "    ${prompt} [${cur}]: " -NoNewline -ForegroundColor White }
        else       { Write-Host "    ${prompt}: "          -NoNewline -ForegroundColor White }
        $v = (Read-Host).Trim()
        if ($v -eq "" -and $cur -ne "") { return $cur }
        if ($v -ne "") { return $v }
        warn "This field is required."
    }
}

function ask-opt([string]$prompt, [string]$cur="") {
    if ($cur) { Write-Host "    ${prompt} [${cur}] (Enter to keep): " -NoNewline -ForegroundColor White }
    else       { Write-Host "    ${prompt} (optional, Enter to skip): " -NoNewline -ForegroundColor DarkGray }
    $v = (Read-Host).Trim()
    if ($v -eq "") { return $cur }
    return $v
}

function ask-secret([string]$prompt) {
    Write-Host "    ${prompt}: " -NoNewline -ForegroundColor White
    $ss = Read-Host -AsSecureString
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($ss)
    $plain = [Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    return $plain
}

# ==============================================================
#  SETUP WIZARD
# ==============================================================
function run-wizard {
    Write-Host ""
    Write-Host "  +=========================================================+" -ForegroundColor Yellow
    Write-Host "  |   First-time setup  -  takes about 2 minutes            |" -ForegroundColor Yellow
    Write-Host "  +=========================================================+" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  Answer a few questions and the app will be ready to use." -ForegroundColor White
    Write-Host "  All settings are saved in '.env' and can be changed later." -ForegroundColor DarkGray
    Write-Host ""

    if (-not (Test-Path $ENV_FILE)) {
        if (Test-Path $ENV_EXAMPLE) { Copy-Item $ENV_EXAMPLE $ENV_FILE -Force }
        else { "" | Set-Content $ENV_FILE -Encoding UTF8 }
    }

    # ---- Step 1: LinkedIn ----
    Write-Host ""
    Write-Host "  --- Step 1 of 3 : LinkedIn Account ---------------------------" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  A dedicated 'test' LinkedIn account is strongly recommended." -ForegroundColor DarkGray
    Write-Host "  Scraping from your main account risks a temporary restriction." -ForegroundColor DarkGray
    Write-Host ""
    $curEmail = get-env "LINKEDIN_EMAIL"
    if ($curEmail -match '^your-') { $curEmail = "" }
    $liEmail = ask "  LinkedIn email" $curEmail
    $liPass  = ask-secret "  LinkedIn password"
    if ($liPass.Length -eq 0) { warn "Password empty - update it in .env before scraping." }
    set-env "LINKEDIN_EMAIL"    $liEmail
    set-env "LINKEDIN_PASSWORD" $liPass
    ok "LinkedIn credentials saved."

    # ---- Step 2: API key ----
    Write-Host ""
    Write-Host "  --- Step 2 of 3 : API Security (auto-configured) -------------" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  The browser dashboard works without any password." -ForegroundColor DarkGray
    Write-Host "  An API key is generated for programmatic / remote access." -ForegroundColor DarkGray
    Write-Host ""
    $existKey = get-env "API_KEY"
    if ($existKey -match '^your[-_]' -or $existKey.Length -lt 10) {
        $newKey = new-apikey
        set-env "API_KEY" $newKey
        ok "API key generated and saved to .env."
        inf "(Developers: use header 'X-API-Key: $newKey' for direct API calls)"
    } else {
        ok "API key already configured."
    }

    # ---- Step 3: Groq AI ----
    Write-Host ""
    Write-Host "  --- Step 3 of 3 : AI Features (optional) --------------------" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  Groq AI is used for CV and cover-letter generation." -ForegroundColor DarkGray
    Write-Host "  Free plan available at https://console.groq.com" -ForegroundColor DarkGray
    Write-Host "  Skip this now - you can add it to .env later." -ForegroundColor DarkGray
    Write-Host ""
    $curGroq = get-env "GROQ_API_KEY"
    if ($curGroq -match '^your-') { $curGroq = "" }
    $groqKey = ask-opt "  Groq API key" $curGroq
    if ($groqKey) { set-env "GROQ_API_KEY" $groqKey; ok "Groq key saved." }
    else { inf "Skipped. CV generation will not be available." }

    Write-Host ""
    divider
    ok "Setup complete. Settings saved to '.env'"
    divider
    Write-Host ""
    Start-Sleep -Seconds 1
}

# ==============================================================
#  WAIT FOR SERVER
# ==============================================================
function wait-server([int]$port, [int]$secs=40) {
    Write-Host "    Waiting for server to start" -NoNewline -ForegroundColor DarkGray
    $n = 0
    for ($i = 0; $i -lt $secs * 2; $i++) {
        Start-Sleep -Milliseconds 500
        try {
            $req = [System.Net.WebRequest]::Create("http://localhost:$port/api/health")
            $req.Timeout = 900
            $r = $req.GetResponse()
            $r.Close()
            Write-Host "  ready!" -ForegroundColor Green
            return $true
        } catch {}
        if ($n -lt 28) { Write-Host "." -NoNewline -ForegroundColor DarkGray; $n++ }
    }
    Write-Host ""
    return $false
}

# ==============================================================
#  CHROME CHECK
# ==============================================================
function has-chrome {
    $paths = @(
        "$env:PROGRAMFILES\Google\Chrome\Application\chrome.exe",
        "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe",
        "${env:PROGRAMFILES(x86)}\Google\Chrome\Application\chrome.exe"
    )
    return ($paths | Where-Object { Test-Path $_ }).Count -gt 0
}

# ==============================================================
#  MAIN
# ==============================================================
banner
Set-Location $ROOT

$firstRun     = -not (Test-Path $STAMP)
$needsWizard  = $firstRun -or $Reconfigure
$needsInstall = $firstRun -or $Update -or (-not (Test-Path $PY_VENV))

# -- 1. Python -------------------------------------------------
hdr "Step 1 / 4  -  Python"
$sysPy = find-python

if (-not $sysPy) {
    $ok = install-python
    $sysPy = find-python
    if (-not $sysPy) {
        err "Python not found after install. Restart this script."
        pause-exit
    }
}
$pyVer = (& $sysPy --version 2>&1).ToString().Trim()
ok $pyVer

# -- 2. Virtual environment ------------------------------------
hdr "Step 2 / 4  -  Environment"
if (-not (Test-Path $VENV)) {
    inf "Creating isolated Python environment..."
    & $sysPy -m venv $VENV 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { err "Failed to create virtual environment."; pause-exit }
    ok "Virtual environment created"
} else {
    ok "Virtual environment ready"
}

& $PIP_VENV install --quiet --upgrade pip 2>&1 | Out-Null

# -- 3. Packages -----------------------------------------------
if ($needsInstall) {
    hdr "Step 3 / 4  -  Installing packages"
    inf "This takes 2-5 minutes on the first run. Please wait..."
    Write-Host ""

    $pipOut    = & $PIP_VENV install -r $REQS 2>&1
    $pipFailed = $LASTEXITCODE -ne 0

    $pipOut | Where-Object { $_ -match '^(Successfully installed|ERROR|error)' } |
              ForEach-Object { inf $_ }

    if ($pipFailed) {
        err "Some packages failed to install."
        Write-Host "  Common fixes:" -ForegroundColor White
        Write-Host "   - Check your internet connection" -ForegroundColor Gray
        Write-Host "   - Temporarily disable antivirus / Windows Defender" -ForegroundColor Gray
        Write-Host "   - Run start.bat as Administrator" -ForegroundColor Gray
        pause-exit
    }
    "" | Set-Content $STAMP -Encoding UTF8
    ok "All packages installed"
} else {
    hdr "Step 3 / 4  -  Packages"
    ok "Already installed  (tip: run with --Update to refresh)"
}

if (-not (has-chrome)) {
    Write-Host ""
    warn "Google Chrome not detected. Scraping features require Chrome."
    inf  "Download from https://www.google.com/chrome and install, then restart."
}

# -- 4. Configuration ------------------------------------------
hdr "Step 4 / 4  -  Configuration"
if ($needsWizard) {
    run-wizard
} else {
    $who = get-env "LINKEDIN_EMAIL"
    ok "Settings loaded from .env  (account: $who)"
    inf "Run with --Reconfigure to change settings."
}

# Read port (default 8000)
$PORT = 8000
$ep   = get-env "API_PORT"
if ($ep -match '^\d+$') { $PORT = [int]$ep }

# -- Launch ----------------------------------------------------
Write-Host ""
divider
Write-Host ""
Write-Host "  Starting server on port $PORT..." -ForegroundColor White

New-Item -ItemType Directory -Force -Path $LOG_DIR | Out-Null
"" | Set-Content $SRV_LOG -Encoding UTF8

$srvProc = Start-Process `
    -FilePath $PY_VENV `
    -ArgumentList @("-m", "uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "$PORT") `
    -WorkingDirectory $ROOT `
    -RedirectStandardOutput $SRV_LOG `
    -RedirectStandardError  $SRV_LOG `
    -PassThru

$ready = wait-server $PORT 40

if (-not $ready) {
    Write-Host ""
    err "Server did not start in time."
    Write-Host "  Last log output:" -ForegroundColor White
    Write-Host ""
    if (Test-Path $SRV_LOG) {
        Get-Content $SRV_LOG | Select-Object -Last 20 | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
    }
    Write-Host ""
    Write-Host "  Common causes:" -ForegroundColor White
    Write-Host "   - Port $PORT is already in use  (change API_PORT in .env)" -ForegroundColor Gray
    Write-Host "   - A Python import error  (see log above)" -ForegroundColor Gray
    Write-Host "   - LinkedIn credentials missing from .env" -ForegroundColor Gray
    Write-Host ""
    if (-not $srvProc.HasExited) { $srvProc.Kill() }
    pause-exit
}

$url = "http://localhost:$PORT"
Start-Process $url

Write-Host ""
Write-Host "  +=========================================================+" -ForegroundColor Green
Write-Host "  |                                                         |" -ForegroundColor Green
Write-Host "  |   LinkedIn Scraper is running!                          |" -ForegroundColor Green
Write-Host "  |                                                         |" -ForegroundColor Green
Write-Host "  |   Dashboard:  " -ForegroundColor Green -NoNewline
Write-Host ($url.PadRight(42)) -ForegroundColor Cyan -NoNewline
Write-Host "|" -ForegroundColor Green
Write-Host "  |                                                         |" -ForegroundColor Green
Write-Host "  |   No password needed - just open the link above.       |" -ForegroundColor Green
Write-Host "  |   Close this window at any time to stop the server.    |" -ForegroundColor Green
Write-Host "  |                                                         |" -ForegroundColor Green
Write-Host "  +=========================================================+" -ForegroundColor Green
Write-Host ""
Write-Host "  Getting started:" -ForegroundColor White
Write-Host "   1. Go to the 'Auth' tab and connect your LinkedIn browser profile" -ForegroundColor Gray
Write-Host "   2. Use 'Scrape' to find LinkedIn profiles by keyword or group" -ForegroundColor Gray
Write-Host "   3. Use 'Profiles' to enrich them and see contact details" -ForegroundColor Gray
Write-Host "   4. Use 'Email' to build and send outreach campaigns" -ForegroundColor Gray
Write-Host ""
divider
Write-Host "  Server log  (Ctrl+C to stop):" -ForegroundColor DarkGray
divider
Write-Host ""

# Stream server log to console
try {
    Get-Content $SRV_LOG -Wait -ErrorAction SilentlyContinue | ForEach-Object {
        if     ($_ -match 'ERROR|error|Error')   { Write-Host "  $_" -ForegroundColor Red }
        elseif ($_ -match 'WARNING|WARN|warn')   { Write-Host "  $_" -ForegroundColor Yellow }
        elseif ($_ -match 'Uvicorn|started|port'){ Write-Host "  $_" -ForegroundColor Green }
        else                                     { Write-Host "  $_" -ForegroundColor DarkGray }
    }
} catch {
    # Ctrl+C or window close
} finally {
    if (-not $srvProc.HasExited) {
        $srvProc.Kill()
        $null = $srvProc.WaitForExit(3000)
    }
    Write-Host ""
    Write-Host "  Server stopped. Goodbye!" -ForegroundColor DarkGray
    Write-Host ""
}
