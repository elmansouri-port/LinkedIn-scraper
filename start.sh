#!/usr/bin/env bash
# ================================================================
#  LinkedIn Scraper  -  uv-powered Setup & Launch
#  No system Python required — uv auto-downloads everything.
#
#  First time:  chmod +x start.sh && ./start.sh
#  After that:  ./start.sh
#
#  Flags:
#    --reconfigure   Re-run the setup wizard
#    --update        Reinstall / update Python packages + uv itself
#    --help          Show usage
# ================================================================
set -uo pipefail

# ── Versions (bump these to update toolchain) ───────────────────
UV_VERSION="0.6.10"

# ── ANSI colours ──────────────────────────────────────────────
RED='\033[0;31m' YLW='\033[1;33m' GRN='\033[0;32m'
CYN='\033[0;36m' WHT='\033[1;37m' GRY='\033[0;37m'
BLU='\033[0;34m' NC='\033[0m'

# ── Paths ─────────────────────────────────────────────────────
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UV_DIR="$ROOT/bin"
ENV_FILE="$ROOT/.env"
ENV_EXAMPLE="$ROOT/.env.example"
LOG_DIR="$ROOT/data/logs"
SRV_LOG="$LOG_DIR/server.log"
STAMP="$ROOT/.venv/setup_ok"
REQS="$ROOT/requirements.txt"
PORT=8000
SRV_PID=""

# ── Platform detection ─────────────────────────────────────────
OS="$(uname -s)"
ARCH="$(uname -m)"
UV_BINARY=""
case "$OS" in
    Linux)
        case "$ARCH" in
            x86_64)  UV_BINARY="uv-x86_64-unknown-linux-gnu" ;;
            aarch64|arm64) UV_BINARY="uv-aarch64-unknown-linux-gnu" ;;
            *) printf "  ${RED}Unsupported architecture: $ARCH${NC}\n"; exit 1 ;;
        esac
        UV_EXE="$UV_DIR/$UV_BINARY/uv"
        ;;
    Darwin)
        case "$ARCH" in
            x86_64)  UV_BINARY="uv-x86_64-apple-darwin" ;;
            arm64|aarch64) UV_BINARY="uv-aarch64-apple-darwin" ;;
            *) printf "  ${RED}Unsupported architecture: $ARCH${NC}\n"; exit 1 ;;
        esac
        UV_EXE="$UV_DIR/$UV_BINARY/uv"
        ;;
    *)
        printf "  ${RED}Unsupported OS: $OS${NC}\n"; exit 1 ;;
esac

# ── Flags ─────────────────────────────────────────────────────
RECONFIGURE=false; UPDATE=false; HELP=false
for arg in "$@"; do
    case "$arg" in
        --reconfigure|-r) RECONFIGURE=true ;;
        --update|-u)      UPDATE=true ;;
        --help|-h)        HELP=true ;;
    esac
done

# ── Output helpers ─────────────────────────────────────────────
hdr()     { echo; printf "  ${CYN}>> %s${NC}\n" "$1"; }
ok()      { printf "     ${GRN}[OK]${NC}  %s\n" "$1"; }
inf()     { printf "           ${GRY}%s${NC}\n" "$1"; }
warn()    { printf "     ${YLW}[!]${NC}   %s\n" "$1"; }
divider() { printf "  ${GRY}----------------------------------------------------------${NC}\n"; }

show_error() {
    echo
    printf "  ${RED}+--------------------------------------------------+${NC}\n"
    printf "  ${RED}|  ERROR: %-40s|${NC}\n" "$1"
    printf "  ${RED}+--------------------------------------------------+${NC}\n"
    echo
}

pause_exit() {
    echo; printf "  Press Enter to close...\n"; read -r || true; exit "${1:-1}"
}

# ── Cleanup on Ctrl+C or window close ─────────────────────────
cleanup() {
    if [ -n "$SRV_PID" ] && kill -0 "$SRV_PID" 2>/dev/null; then
        kill "$SRV_PID" 2>/dev/null || true
        wait "$SRV_PID" 2>/dev/null || true
    fi
    echo; printf "  ${GRY}Server stopped. Goodbye!${NC}\n"; echo
}
trap cleanup EXIT INT TERM

# ── Banner ─────────────────────────────────────────────────────
banner() {
    clear; echo
    printf "  ${BLU}+=========================================================+${NC}\n"
    printf "  ${BLU}|                                                         |${NC}\n"
    printf "  ${BLU}|   ${CYN}LinkedIn Scraper${NC}${WHT}  -  Automated Prospecting Suite${NC}${BLU}   |${NC}\n"
    printf "  ${BLU}|                                                         |${NC}\n"
    printf "  ${BLU}+=========================================================+${NC}\n"
    echo
}

if $HELP; then
    banner
    printf "  Usage:\n"
    printf "    ./start.sh                   Normal launch (setup on first use)\n"
    printf "    ./start.sh --reconfigure     Re-run the configuration wizard\n"
    printf "    ./start.sh --update          Upgrade uv + reinstall packages\n\n"
    exit 0
fi

# ════════════════════════════════════════════════════════════════
#  UV DOWNLOAD
# ════════════════════════════════════════════════════════════════
ensure_uv() {
    [ -f "$UV_EXE" ] && return 0

    echo
    inf "Downloading uv $UV_VERSION (one-time)..."
    mkdir -p "$UV_DIR"

    local url="https://github.com/astral-sh/uv/releases/download/$UV_VERSION/$UV_BINARY.tar.gz"
    local tarball="$UV_DIR/uv.tar.gz"

    if command -v curl &>/dev/null; then
        curl -fsSL "$url" -o "$tarball" || { show_error "Failed to download uv"; return 1; }
    elif command -v wget &>/dev/null; then
        wget -q "$url" -O "$tarball" || { show_error "Failed to download uv"; return 1; }
    else
        show_error "Neither curl nor wget found. Install one of them first."
        return 1
    fi

    # SHA256 verification
    local sha_url="$url.sha256"
    local sha_file="$UV_DIR/uv.tar.gz.sha256"
    if command -v sha256sum &>/dev/null; then
        SHA_CMD="sha256sum"
    elif command -v shasum &>/dev/null; then
        SHA_CMD="shasum -a 256"
    else
        SHA_CMD=""
    fi

    if [ -n "$SHA_CMD" ]; then
        if curl -fsSL "$sha_url" -o "$sha_file" 2>/dev/null || wget -q "$sha_url" -O "$sha_file" 2>/dev/null; then
            local expected_hash
            expected_hash=$(awk '{print $1}' "$sha_file" 2>/dev/null)
            local actual_hash
            actual_hash=$($SHA_CMD "$tarball" | awk '{print $1}')
            if [ "$expected_hash" != "$actual_hash" ]; then
                show_error "Download corrupted! Expected $expected_hash, got $actual_hash"
                rm -f "$tarball" "$sha_file"
                return 1
            fi
            rm -f "$sha_file"
            inf "Checksum verified"
        else
            warn "Could not verify checksum — continuing without verification"
        fi
    else
        warn "No SHA tool found — skipping checksum verification"
    fi

    tar -xzf "$tarball" -C "$UV_DIR" || { show_error "Failed to extract uv"; rm -f "$tarball"; return 1; }
    rm -f "$tarball"
    chmod +x "$UV_EXE"
    ok "uv $UV_VERSION ready at bin/$UV_BINARY/uv"
    return 0
}

# ════════════════════════════════════════════════════════════════
#  .ENV HELPERS
# ════════════════════════════════════════════════════════════════
get_env() {
    [ -f "$ENV_FILE" ] || { echo ""; return; }
    grep -E "^\s*${1}\s*=" "$ENV_FILE" 2>/dev/null | head -1 \
        | sed 's/^[^=]*=//' | sed 's/[[:space:]]*#.*//' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//'
}

_SET_ENV_PY='
import re, sys
key, value, path = sys.argv[1], sys.argv[2], sys.argv[3]
try:
    with open(path) as f:
        content = f.read()
except FileNotFoundError:
    content = ""
pattern = re.compile(r"(?m)^\s*" + re.escape(key) + r"\s*=.*")
if pattern.search(content):
    content = pattern.sub(key + "=" + value, content)
else:
    content = content.rstrip("\n") + "\n" + key + "=" + value
with open(path, "w") as f:
    f.write(content)
'

set_env() { "$UV_EXE" run python -c "$_SET_ENV_PY" "$1" "$2" "$ENV_FILE"; }

new_apikey() {
    "$UV_EXE" run python -c "
import secrets, string
pool = string.ascii_letters + string.digits
print(''.join(secrets.choice(pool) for _ in range(40)))
"
}

# ════════════════════════════════════════════════════════════════
#  SETUP WIZARD
# ════════════════════════════════════════════════════════════════
run_wizard() {
    echo
    printf "  ${YLW}+=========================================================+${NC}\n"
    printf "  ${YLW}|   First-time setup  -  takes about 2 minutes            |${NC}\n"
    printf "  ${YLW}+=========================================================+${NC}\n\n"
    printf "  Answer a few questions and the app will be ready to use.\n"
    printf "  ${GRY}All settings are saved in '.env' and can be changed later.${NC}\n\n"

    if [ ! -f "$ENV_FILE" ]; then
        if [ -f "$ENV_EXAMPLE" ]; then cp "$ENV_EXAMPLE" "$ENV_FILE"; else touch "$ENV_FILE"; fi
    fi

    # ── Step 1: LinkedIn ────────────────────────────────────────
    echo; printf "  ${CYN}--- Step 1 of 3 : LinkedIn Account ---------------------------${NC}\n\n"
    printf "  ${GRY}A dedicated 'test' LinkedIn account is strongly recommended.${NC}\n"
    printf "  ${GRY}Scraping from your main account risks a temporary restriction.${NC}\n\n"

    cur_email=$(get_env "LINKEDIN_EMAIL")
    case "$cur_email" in your-*|"") cur_email="" ;; esac

    li_email=""
    while [ -z "$li_email" ]; do
        if [ -n "$cur_email" ]; then
            printf "    LinkedIn email [%s]: " "$cur_email"; read -r li_email || li_email=""
            [ -z "$li_email" ] && li_email="$cur_email"
        else
            printf "    LinkedIn email: "; read -r li_email || li_email=""
            [ -z "$li_email" ] && warn "Email is required."
        fi
    done

    printf "    LinkedIn password: "; read -rs li_pass || li_pass=""; echo
    [ -z "$li_pass" ] && warn "Password empty — update it in .env before scraping."

    set_env "LINKEDIN_EMAIL"    "$li_email"
    set_env "LINKEDIN_PASSWORD" "$li_pass"
    ok "LinkedIn credentials saved."

    # ── Step 2: API key ─────────────────────────────────────────
    echo; printf "  ${CYN}--- Step 2 of 3 : API Security (auto-configured) ------------${NC}\n\n"
    printf "  ${GRY}The browser dashboard works without any password.${NC}\n"
    printf "  ${GRY}An API key is generated for programmatic / remote access.${NC}\n\n"

    exist_key=$(get_env "API_KEY")
    if echo "$exist_key" | grep -qE '^your[-_]' 2>/dev/null || [ "${#exist_key}" -lt 10 ]; then
        new_key=$(new_apikey)
        set_env "API_KEY" "$new_key"
        ok "API key generated and saved to .env."
        inf "(Developers: use header 'X-API-Key: ${new_key}' for direct API calls)"
    else
        ok "API key already configured."
    fi

    # ── Step 3: Groq AI ─────────────────────────────────────────
    echo; printf "  ${CYN}--- Step 3 of 3 : AI Features (optional) --------------------${NC}\n\n"
    printf "  ${GRY}Groq AI enables CV and cover-letter generation from profile data.${NC}\n"
    printf "  ${GRY}Free plan available at https://console.groq.com${NC}\n"
    printf "  ${GRY}Skip this now — you can add it to .env later.${NC}\n\n"

    cur_groq=$(get_env "GROQ_API_KEY")
    case "$cur_groq" in your-*|"") cur_groq="" ;; esac

    if [ -n "$cur_groq" ]; then
        printf "    Groq API key [%s...] (Enter to keep): " "${cur_groq:0:8}"
    else
        printf "    Groq API key (optional, Enter to skip): "
    fi
    read -r groq_key || groq_key=""
    [ -z "$groq_key" ] && groq_key="$cur_groq"
    if [ -n "$groq_key" ]; then set_env "GROQ_API_KEY" "$groq_key"; ok "Groq key saved."
    else inf "Skipped. CV generation will not be available."; fi

    echo; divider; ok "Setup complete. Settings saved to '.env'"; divider; echo; sleep 1
}

# ════════════════════════════════════════════════════════════════
#  WAIT FOR SERVER
# ════════════════════════════════════════════════════════════════
wait_for_server() {
    local port="$1" max_secs="${2:-40}"
    printf "    Waiting for server to start"
    local i=0 dots=0
    while [ "$i" -lt $((max_secs * 2)) ]; do
        sleep 0.5
        if "$UV_EXE" run python -c "
import urllib.request, sys
try:
    urllib.request.urlopen('http://localhost:$port/api/health', timeout=1)
    sys.exit(0)
except:
    sys.exit(1)
" 2>/dev/null; then
            printf "  ready!\n"; return 0
        fi
        [ "$dots" -lt 28 ] && { printf "."; dots=$((dots + 1)); }
        i=$((i + 1))
    done
    echo; return 1
}

# ════════════════════════════════════════════════════════════════
#  OPEN BROWSER
# ════════════════════════════════════════════════════════════════
open_browser() {
    local url="$1"
    if   command -v xdg-open  &>/dev/null; then xdg-open  "$url" &>/dev/null & disown
    elif command -v open       &>/dev/null; then open       "$url"
    elif command -v wslview   &>/dev/null; then wslview   "$url" &>/dev/null & disown
    fi
}

# ════════════════════════════════════════════════════════════════
#  AUTO UPDATE
# ════════════════════════════════════════════════════════════════
check_update() {
    local branch="master"
    if command -v git &>/dev/null; then
        local b; b=$(git branch --show-current 2>/dev/null || true)
        [ -n "$b" ] && branch="$b"
    fi

    local local_ver="0.0.0"
    if [ -f "version.json" ]; then
        local_ver=$(grep -o '"version": *"[^"]*"' version.json | sed 's/.*"version": *"\([^"]*\)".*/\1/')
        [ -z "$local_ver" ] && local_ver="0.0.0"
    fi

    local remote_url="https://raw.githubusercontent.com/elmansouri-port/LinkedIn-scraper/$branch/version.json"
    local remote_json=""
    
    if command -v curl &>/dev/null; then
        remote_json=$(curl -fsSL --max-time 5 "$remote_url" 2>/dev/null || true)
    elif command -v wget &>/dev/null; then
        remote_json=$(wget -qO- --timeout 5 "$remote_url" 2>/dev/null || true)
    fi

    if [ -n "$remote_json" ]; then
        local remote_ver; remote_ver=$(echo "$remote_json" | grep -o '"version": *"[^"]*"' | sed 's/.*"version": *"\([^"]*\)".*/\1/')
        if [ -n "$remote_ver" ] && [ "$remote_ver" != "$local_ver" ]; then
            echo
            printf "  ${CYN}[*] New version found: v%s (current: v%s)${NC}\n" "$remote_ver" "$local_ver"
            printf "      ${GRY}Downloading updates...${NC}\n"
            
            if [ -d ".git" ]; then
                git pull origin "$branch" >/dev/null 2>&1 || true
            else
                git init >/dev/null 2>&1
                git remote add origin "https://github.com/elmansouri-port/LinkedIn-scraper.git" >/dev/null 2>&1
                git fetch >/dev/null 2>&1
                git checkout -t origin/"$branch" >/dev/null 2>&1 || true
            fi
            
            printf "  ${GRN}[OK] Update complete. Restarting...${NC}\n"
            sleep 2
            exec "$0" "$@"
        fi
    fi
}

# ════════════════════════════════════════════════════════════════
#  CHROME CHECK
# ════════════════════════════════════════════════════════════════
has_chrome() {
    for cmd in google-chrome-stable google-chrome chromium-browser chromium brave-browser; do
        command -v "$cmd" &>/dev/null && return 0
    done
    [ -f "/snap/bin/chromium" ] && return 0
    for mac in \
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
        "/Applications/Chromium.app/Contents/MacOS/Chromium" \
        "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"; do
        [ -f "$mac" ] && return 0
    done
    return 1
}

# ════════════════════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════════════════════
banner
cd "$ROOT"
check_update

FIRST_RUN=false; [ ! -f "$STAMP" ] && FIRST_RUN=true
NEEDS_WIZARD=$FIRST_RUN; $RECONFIGURE && NEEDS_WIZARD=true

# ── 1. uv toolchain ────────────────────────────────────────────
hdr "Step 1 / 5  -  Toolchain"
if ! ensure_uv; then pause_exit; fi
ok "uv $UV_VERSION"

# ── 2. Python ──────────────────────────────────────────────────
hdr "Step 2 / 5  -  Python"
PY_VERSION="3.11"
PY_FROM_UV=true

inf "Downloading Python $PY_VERSION if not cached (one-time)..."
if ! "$UV_EXE" python install "$PY_VERSION" 2>/dev/null; then
    warn "Download failed. Retrying with system TLS (native-tls)..."
    if ! "$UV_EXE" --native-tls python install "$PY_VERSION" 2>/dev/null; then
        warn "Could not download Python $PY_VERSION via uv."
        inf "Checking for Python $PY_VERSION+ already on this system..."
        PY_FROM_UV=false
        FOUND_PY=""
        for cmd in python3 python; do
            if command -v "$cmd" &>/dev/null; then
                ver=$("$cmd" --version 2>&1)
                if echo "$ver" | grep -qE 'Python\s+3\.(1[1-9]|[2-9][0-9])'; then
                    FOUND_PY="$cmd"
                    ok "Found $(echo "$ver" | head -1) at '$cmd'"
                    break
                fi
            fi
        done
        if [ -z "$FOUND_PY" ]; then
            show_error "No Python $PY_VERSION+ found on this system."
            printf "  Install Python from https://www.python.org/downloads/\n"
            pause_exit
        fi
    fi
fi

# ── 3. Virtual environment ─────────────────────────────────────
hdr "Step 3 / 5  -  Environment"
if [ ! -d "$ROOT/.venv" ]; then
    if $PY_FROM_UV; then
        inf "Creating isolated Python environment (Python $PY_VERSION)..."
        "$UV_EXE" venv --python "$PY_VERSION" 2>&1 || { show_error "Failed to create virtual environment."; pause_exit; }
    else
        inf "Creating isolated Python environment ($FOUND_PY)..."
        "$UV_EXE" venv --python "$FOUND_PY" 2>&1 || { show_error "Failed to create virtual environment."; pause_exit; }
    fi
    ok "Virtual environment created"
else
    ok "Virtual environment ready"
fi

# ── 4. Dependencies ────────────────────────────────────────────
hdr "Step 4 / 5  -  Dependencies"
if $UPDATE; then
    inf "Upgrading uv to latest version..."
    "$UV_EXE" self update 2>&1 || true
    ok "uv updated"
fi

if $FIRST_RUN || $UPDATE; then
    inf "Installing packages via uv (fast!)..."
    if ! sync_out=$("$UV_EXE" sync 2>&1); then
        warn "Sync failed. Retrying with system TLS (native-tls)..."
        if ! sync_out=$("$UV_EXE" --native-tls sync 2>&1); then
            show_error "Failed to install packages."
            echo "$sync_out" | while IFS= read -r line; do printf "  ${RED}%s${NC}\n" "$line"; done
            pause_exit
        fi
    fi
    touch "$STAMP"
    ok "All packages installed"
else
    "$UV_EXE" sync 2>&1 >/dev/null || true
    ok "Packages up to date  (run with --update to refresh)"
fi

has_chrome || {
    echo; warn "Chrome/Chromium not detected — scraping requires a Chromium browser."
    if [ "$(uname -s)" = "Darwin" ]; then inf "Download: https://www.google.com/chrome"
    else inf "Ubuntu/Debian: sudo apt install chromium-browser"; fi
}

# ── 5. Configuration ───────────────────────────────────────────
hdr "Step 5 / 5  -  Configuration"
if $NEEDS_WIZARD; then
    run_wizard
else
    ok "Settings loaded from .env  (account: $(get_env "LINKEDIN_EMAIL"))"
    inf "Run with --reconfigure to change settings."
fi

ep=$(get_env "API_PORT")
case "$ep" in [0-9]*) PORT="$ep" ;; esac

# ── Launch ─────────────────────────────────────────────────────
echo; divider; echo
printf "  Starting server on port %s...\n" "$PORT"

mkdir -p "$LOG_DIR"
: > "$SRV_LOG"

"$UV_EXE" run uvicorn api.app:app --host 0.0.0.0 --port "$PORT" >> "$SRV_LOG" 2>&1 &
SRV_PID=$!

if ! wait_for_server "$PORT" 40; then
    echo; show_error "Server did not start in time."
    printf "  Last log output:\n\n"
    tail -20 "$SRV_LOG" 2>/dev/null | while IFS= read -r line; do
        printf "  ${RED}%s${NC}\n" "$line"
    done
    echo
    printf "  Common causes:\n"
    printf "   - Port %s already in use  (change API_PORT in .env)\n" "$PORT"
    printf "   - A Python import error  (see log above)\n"
    printf "   - Missing .env credentials\n\n"
    pause_exit 1
fi

URL="http://localhost:${PORT}"
open_browser "$URL"

echo
printf "  ${GRN}+=========================================================+${NC}\n"
printf "  ${GRN}|                                                         |${NC}\n"
printf "  ${GRN}|   LinkedIn Scraper is running!                          |${NC}\n"
printf "  ${GRN}|                                                         |${NC}\n"
printf "  ${GRN}|   Dashboard:  ${CYN}%-43s${GRN}|${NC}\n" "$URL"
printf "  ${GRN}|                                                         |${NC}\n"
printf "  ${GRN}|   No password needed — just open the link above.       |${NC}\n"
printf "  ${GRN}|   Press Ctrl+C to stop the server.                     |${NC}\n"
printf "  ${GRN}+=========================================================+${NC}\n\n"
printf "  Getting started:\n"
printf "   ${GRY}1. Go to the 'Auth' tab and connect your LinkedIn browser profile${NC}\n"
printf "   ${GRY}2. Use 'Scrape' to find LinkedIn profiles by keyword or group${NC}\n"
printf "   ${GRY}3. Use 'Profiles' to enrich them and see contact details${NC}\n"
printf "   ${GRY}4. Use 'Email' to build and send outreach campaigns${NC}\n\n"
divider
printf "  Server log (Ctrl+C to stop):\n"
divider; echo

tail -f "$SRV_LOG" 2>/dev/null | while IFS= read -r line; do
    if   echo "$line" | grep -qiE 'error';              then printf "  ${RED}%s${NC}\n" "$line"
    elif echo "$line" | grep -qiE 'warning|warn';       then printf "  ${YLW}%s${NC}\n" "$line"
    elif echo "$line" | grep -qiE 'uvicorn|started|running on'; then printf "  ${GRN}%s${NC}\n" "$line"
    else                                                     printf "  ${GRY}%s${NC}\n" "$line"
    fi
done

wait "$SRV_PID" 2>/dev/null || true
