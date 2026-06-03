# ================================================================
#  LinkedIn Scraper  -  uv-powered Setup & Launch
#  No system Python required - uv auto-downloads everything.
#  This file is launched by LinkedIn Scraper.bat (double-click to run).
# ================================================================
#  Flags:
#    --Reconfigure   Re-run the setup wizard
#    --Update        Reinstall / update Python packages + uv itself
#    --Help          Show usage
# ================================================================

param(
    [switch]$Reconfigure,
    [switch]$Update,
    [switch]$Help
)

Set-StrictMode -Off
$ErrorActionPreference = "Continue"

# ---- Versions (bump these to update toolchain) ----------------
$UV_VERSION = "0.6.10"

# ---- Paths ---------------------------------------------------
$ROOT        = Split-Path -Parent $MyInvocation.MyCommand.Path
$UV_DIR      = Join-Path $ROOT "bin"
$UV_EXE      = Join-Path $UV_DIR "uv.exe"
$ENV_FILE    = Join-Path $ROOT ".env"
$ENV_EXAMPLE = Join-Path $ROOT ".env.example"
$LOG_DIR     = Join-Path $ROOT "data\logs"
$SRV_LOG     = Join-Path $LOG_DIR "server.log"
$STAMP       = Join-Path $ROOT ".venv\setup_ok"
$REQS        = Join-Path $ROOT "requirements.txt"

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
    Write-Host "    LinkedIn Scraper.bat                   Normal launch (setup on first use)"
    Write-Host "    LinkedIn Scraper.bat --Reconfigure     Re-run the configuration wizard"
    Write-Host "    LinkedIn Scraper.bat --Update          Upgrade uv + reinstall packages"
    Write-Host ""
    pause-exit 0
}

# ==============================================================
#  UV DOWNLOAD
# ==============================================================
function ensure-uv {
    if (Test-Path $UV_EXE) { return $true }

    Write-Host ""
    inf "Downloading uv $UV_VERSION (one-time)..."
    New-Item -ItemType Directory -Force -Path $UV_DIR | Out-Null

    $url = "https://github.com/astral-sh/uv/releases/download/$UV_VERSION/uv-x86_64-pc-windows-msvc.zip"
    $zip = Join-Path $UV_DIR "uv.zip"

    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -Uri $url -OutFile $zip -UseBasicParsing

        # SHA256 verification
        $shaUrl = "$url.sha256"
        $shaFile = Join-Path $UV_DIR "uv.zip.sha256"
        try {
            Invoke-WebRequest -Uri $shaUrl -OutFile $shaFile -UseBasicParsing -ErrorAction Stop
            $expectedHash = ((Get-Content $shaFile -Raw) -split '\s+')[0]
            $actualHash = (Get-FileHash -Path $zip -Algorithm SHA256).Hash
            if ($expectedHash -ne $actualHash) {
                err "Download corrupted! Expected $expectedHash, got $actualHash"
                Remove-Item $zip, $shaFile -Force -ErrorAction SilentlyContinue
                return $false
            }
            Remove-Item $shaFile -Force
            inf "Checksum verified"
        } catch {
            warn "Could not verify checksum - continuing without verification"
        }

        Expand-Archive -Path $zip -DestinationPath $UV_DIR -Force
        Remove-Item $zip -Force
        ok "uv $UV_VERSION ready at bin\uv.exe"
        return $true
    } catch {
        err "Failed to download uv. Check your internet connection."
        return $false
    }
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

# Top-level error handler — catches any terminating error so the
# window stays open and the user can read what happened.
try {

# -- 1. uv toolchain -------------------------------------------
hdr "Step 1 / 5  -  Toolchain"
if (-not (ensure-uv)) { pause-exit }
ok "uv $UV_VERSION"

# -- 2. Python -------------------------------------------------
hdr "Step 2 / 5  -  Python"

$pyVersion = "3.11"
$pyFromUv = $true

inf "Downloading Python $pyVersion if not cached (one-time)..."
$null = & $UV_EXE python install $pyVersion 2>&1 | %{ "$_" }
$pyOk = $LASTEXITCODE -eq 0

if (-not $pyOk) {
    warn "Download failed. Retrying with system TLS (native-tls)..."
    $null = & $UV_EXE --native-tls python install $pyVersion 2>&1 | %{ "$_" }
    $pyOk = $LASTEXITCODE -eq 0
}

if (-not $pyOk) {
    $pyFromUv = $false

    # Warning box — explain the situation, don't scare the user
    Write-Host ""
    Write-Host "  +----------------------------------------------------------+" -ForegroundColor Yellow
    Write-Host "  |  [!] Python download failed (SSL / proxy issue)          |" -ForegroundColor Yellow
    Write-Host "  |                                                          |" -ForegroundColor Yellow
    Write-Host "  |  Your network is blocking the download.                  |" -ForegroundColor Yellow
    Write-Host "  |  This is common on corporate networks (Zscaler etc.)     |" -ForegroundColor Yellow
    Write-Host "  |                                                          |" -ForegroundColor Yellow
    Write-Host "  |  Do NOT close this window.                               |" -ForegroundColor Yellow
    Write-Host "  |  Checking for a local Python installation...             |" -ForegroundColor Yellow
    Write-Host "  +----------------------------------------------------------+" -ForegroundColor Yellow
    Write-Host ""

    # Retry loop: check for system Python, let user install and retry (max 3)
    $foundPy = $null
    for ($attempt = 1; $attempt -le 3; $attempt++) {
        inf "Checking for Python $pyVersion+ on this system..."
        foreach ($cmd in @("py", "python3", "python")) {
            try {
                $v = (& $cmd --version 2>&1 | %{ "$_" }) -join " "
                if ($v -match 'Python\s+3\.(1[1-9]|[2-9]\d)') {
                    $foundPy = $cmd
                    ok "Found $($v.Trim()) at '$foundPy'"
                    break
                }
            } catch {}
        }

        if ($foundPy) { break }

        if ($attempt -lt 3) {
            Write-Host ""
            Write-Host "  Python $pyVersion+ is not installed on this system." -ForegroundColor White
            Write-Host ""
            Write-Host "  Option 1 — Install Python from python.org:" -ForegroundColor White
            Write-Host "    https://www.python.org/downloads/" -ForegroundColor Cyan
            Write-Host "    (check 'Add Python to PATH' during install)" -ForegroundColor DarkGray
            Write-Host ""
            Write-Host "  Option 2 — Press Q to quit and fix this later." -ForegroundColor Yellow
            Write-Host ""
            Write-Host "  After installing, press any key to try again..." -NoNewline -ForegroundColor DarkGray
            $key = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
            Write-Host ""
            if ($key.Character -eq 'q' -or $key.Character -eq 'Q') {
                Write-Host ""
                Write-Host "  Exiting as requested. Run LinkedIn Scraper.bat again when ready." -ForegroundColor Yellow
                pause-exit
            }
        } else {
            Write-Host ""
            Write-Host "  Python $pyVersion+ is not installed on this system." -ForegroundColor White
            Write-Host ""
            err "Could not find Python after 3 attempts."
            Write-Host ""
            Write-Host "  Install Python from:" -ForegroundColor White
            Write-Host "    https://www.python.org/downloads/" -ForegroundColor Cyan
            Write-Host "  Make sure to check 'Add Python to PATH' during install." -ForegroundColor DarkGray
            Write-Host "  Then run LinkedIn Scraper.bat again." -ForegroundColor White
            pause-exit
        }
    }
}

# -- 3. Virtual environment ------------------------------------
hdr "Step 3 / 5  -  Environment"

$venvExists = Test-Path (Join-Path $ROOT ".venv")
if (-not $venvExists) {
    if ($pyFromUv) {
        inf "Creating isolated Python environment (Python $pyVersion)..."
    } else {
        inf "Creating isolated Python environment ($foundPy)..."
    }
    $null = & $UV_EXE venv --python $(if ($pyFromUv) { $pyVersion } else { $foundPy }) 2>&1 | %{ "$_" }
    if ($LASTEXITCODE -ne 0) { err "Failed to create virtual environment."; pause-exit }
    ok "Virtual environment created"
} else {
    ok "Virtual environment ready"
}

# -- 4. Dependencies -------------------------------------------
hdr "Step 4 / 5  -  Dependencies"

if ($Update) {
    inf "Upgrading uv to latest version..."
    $null = & $UV_EXE self update 2>&1 | %{ "$_" }
    ok "uv updated"
}

if ($firstRun -or $Update) {
    inf "Installing packages via uv (fast!)..."
    $syncOut = & $UV_EXE sync 2>&1 | %{ "$_" }
    $syncOk = $LASTEXITCODE -eq 0
    if (-not $syncOk) {
        warn "Sync failed. Retrying with system TLS (native-tls)..."
        $syncOut = & $UV_EXE --native-tls sync 2>&1 | %{ "$_" }
        $syncOk = $LASTEXITCODE -eq 0
    }
    if (-not $syncOk) {
        err "Failed to install packages."
        Write-Host ""
        $syncOut | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
        pause-exit
    }
    "" | Set-Content $STAMP -Encoding UTF8
    ok "All packages installed"
} else {
    $null = & $UV_EXE sync 2>&1 | %{ "$_" }
    ok "Packages up to date  (run with --Update to refresh)"
}

if (-not (has-chrome)) {
    Write-Host ""
    warn "Google Chrome not detected. Scraping features require Chrome."
    inf  "Download from https://www.google.com/chrome and install, then restart."
}

# -- 5. Configuration ------------------------------------------
hdr "Step 5 / 5  -  Configuration"
if ($needsWizard) {
    run-wizard
} else {
    $who = get-env "LINKEDIN_EMAIL"
    ok "Settings loaded from .env  (account: $who)"
    inf "Run with --Reconfigure to change settings."
}

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
    -FilePath $UV_EXE `
    -ArgumentList @("run", "uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "$PORT") `
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

try {
    Get-Content $SRV_LOG -Wait -ErrorAction SilentlyContinue | ForEach-Object {
        if     ($_ -match 'ERROR|error|Error')   { Write-Host "  $_" -ForegroundColor Red }
        elseif ($_ -match 'WARNING|WARN|warn')   { Write-Host "  $_" -ForegroundColor Yellow }
        elseif ($_ -match 'Uvicorn|started|port'){ Write-Host "  $_" -ForegroundColor Green }
        else                                     { Write-Host "  $_" -ForegroundColor DarkGray }
    }
} catch {
} finally {
    if (-not $srvProc.HasExited) {
        $srvProc.Kill()
        $null = $srvProc.WaitForExit(3000)
    }
    Write-Host ""
    Write-Host "  Server stopped. Goodbye!" -ForegroundColor DarkGray
    Write-Host ""
}
} catch {
    Write-Host ""
    Write-Host "  +--------------------------------------------------+" -ForegroundColor Red
    Write-Host "  |  UNEXPECTED ERROR                                |" -ForegroundColor Red
    Write-Host "  |                                                  |" -ForegroundColor Red
    Write-Host "  |  $($_.Exception.Message.PadRight(46))" -ForegroundColor Red
    Write-Host "  +--------------------------------------------------+" -ForegroundColor Red
    Write-Host ""
    Write-Host "  This was not a script failure, but an unexpected" -ForegroundColor White
    Write-Host "  PowerShell error. The details are above." -ForegroundColor White
    Write-Host ""
    Write-Host "  Press any key to close..." -ForegroundColor DarkGray
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit 1
}
