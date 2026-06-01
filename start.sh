#!/usr/bin/env bash
# ================================================================
#  LinkedIn Scraper — One-Click Setup & Launch
#  Linux / macOS
#
#  First time:  chmod +x start.sh && ./start.sh
#  After that:  ./start.sh
#
#  Flags:
#    --reconfigure   Re-run the setup wizard
#    --update        Reinstall / update Python packages
#    --help          Show usage
# ================================================================
set -uo pipefail

# ── ANSI colours ──────────────────────────────────────────────
RED='\033[0;31m' YLW='\033[1;33m' GRN='\033[0;32m'
CYN='\033[0;36m' WHT='\033[1;37m' GRY='\033[0;37m'
BLU='\033[0;34m' NC='\033[0m'

# ── Paths ─────────────────────────────────────────────────────
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$ROOT/venv"
REQS="$ROOT/requirements.txt"
ENV_FILE="$ROOT/.env"
ENV_EXAMPLE="$ROOT/.env.example"
LOG_DIR="$ROOT/data/logs"
SRV_LOG="$LOG_DIR/server.log"
STAMP="$VENV/.setup_ok"
PORT=8000
SRV_PID=""
PYTHON=""

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
    printf "    ./start.sh --update          Reinstall / upgrade Python packages\n\n"
    exit 0
fi

# ════════════════════════════════════════════════════════════════
#  PYTHON DETECTION
# ════════════════════════════════════════════════════════════════
find_python() {
    for cmd in python3 python py; do
        if command -v "$cmd" &>/dev/null; then
            if "$cmd" -c "import sys; assert sys.version_info >= (3,8)" 2>/dev/null; then
                echo "$cmd"; return 0
            fi
        fi
    done
    return 1
}

# ════════════════════════════════════════════════════════════════
#  .ENV HELPERS  (Python handles platform differences for us)
# ════════════════════════════════════════════════════════════════
get_env() {
    [ -f "$ENV_FILE" ] || { echo ""; return; }
    grep -E "^\s*${1}\s*=" "$ENV_FILE" 2>/dev/null | head -1 \
        | sed 's/^[^=]*=//' | sed 's/[[:space:]]*#.*//' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//'
}

# Pass key/value/path as sys.argv to avoid any bash quoting issues
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

set_env() { "$PYTHON" -c "$_SET_ENV_PY" "$1" "$2" "$ENV_FILE"; }

new_apikey() {
    "$PYTHON" -c "
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
#  WAIT FOR SERVER  (Python urllib — no curl dependency)
# ════════════════════════════════════════════════════════════════
wait_for_server() {
    local port="$1" max_secs="${2:-40}"
    printf "    Waiting for server to start"
    local i=0 dots=0
    while [ "$i" -lt $((max_secs * 2)) ]; do
        sleep 0.5
        if "$PYTHON" -c "
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

FIRST_RUN=false; [ ! -f "$STAMP" ] && FIRST_RUN=true
NEEDS_WIZARD=$FIRST_RUN; $RECONFIGURE && NEEDS_WIZARD=true
NEEDS_INSTALL=$FIRST_RUN; $UPDATE && NEEDS_INSTALL=true

# ── 1. Python ──────────────────────────────────────────────────
hdr "Step 1 / 4  -  Python"
SYS_PYTHON=""
if ! SYS_PYTHON=$(find_python); then
    echo
    printf "  ${YLW}Python 3.8+ was not found on this computer.${NC}\n"
    printf "  Python is free and required to run the scraper.\n\n"
    if [ "$(uname -s)" = "Darwin" ]; then
        printf "   ${CYN}brew install python3${NC}          (Homebrew)\n"
        printf "   Or download from https://www.python.org/downloads/\n"
    else
        printf "   ${CYN}sudo apt install python3 python3-venv python3-pip${NC}  (Ubuntu/Debian)\n"
        printf "   ${CYN}sudo dnf install python3 python3-pip${NC}               (Fedora/RHEL)\n"
        printf "   ${CYN}sudo pacman -S python${NC}                              (Arch)\n"
    fi
    echo; pause_exit 1
fi
ok "$($SYS_PYTHON --version 2>&1)"

# ── 2. Virtual environment ─────────────────────────────────────
hdr "Step 2 / 4  -  Environment"
if [ ! -d "$VENV" ] || [ ! -f "$VENV/bin/python" ]; then
    inf "Creating isolated Python environment..."
    "$SYS_PYTHON" -m venv "$VENV" || {
        # Some systems need python3-venv installed
        show_error "venv creation failed."
        printf "  Fix (Ubuntu/Debian): ${CYN}sudo apt install python3-venv${NC}\n\n"
        pause_exit 1
    }
    NEEDS_INSTALL=true
    ok "Virtual environment created"
else
    ok "Virtual environment ready"
fi

PYTHON="$VENV/bin/python"
PIP="$VENV/bin/pip"
"$PIP" install --quiet --upgrade pip 2>/dev/null || true

# ── 3. Packages ────────────────────────────────────────────────
if $NEEDS_INSTALL; then
    hdr "Step 3 / 4  -  Installing packages"
    inf "This takes 2-5 minutes on the first run. Please wait..."; echo

    pip_log="/tmp/linkedin_pip_$$.log"
    if "$PIP" install -r "$REQS" > "$pip_log" 2>&1; then
        grep -E "^Successfully installed" "$pip_log" | while IFS= read -r line; do inf "$line"; done || true
        rm -f "$pip_log"
        touch "$STAMP"
        ok "All packages installed"
    else
        grep -E "^(ERROR|error)" "$pip_log" | head -5 | while IFS= read -r line; do warn "$line"; done || true
        rm -f "$pip_log"
        show_error "Some packages failed to install."
        if [ "$(uname -s)" = "Darwin" ]; then
            printf "   Try: ${CYN}xcode-select --install${NC}  then run again\n"
        else
            printf "   Try: ${CYN}sudo apt install python3-dev build-essential${NC}\n"
        fi
        pause_exit 1
    fi
else
    hdr "Step 3 / 4  -  Packages"
    ok "Already installed  (run with --update to refresh)"
fi

has_chrome || {
    echo; warn "Chrome/Chromium not detected — scraping requires a Chromium browser."
    if [ "$(uname -s)" = "Darwin" ]; then inf "Download: https://www.google.com/chrome"
    else inf "Ubuntu/Debian: sudo apt install chromium-browser"; fi
}

# ── 4. Configuration ───────────────────────────────────────────
hdr "Step 4 / 4  -  Configuration"
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

"$PYTHON" -m uvicorn api.app:app --host 0.0.0.0 --port "$PORT" >> "$SRV_LOG" 2>&1 &
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
printf "  ${GRN}|                                                         |${NC}\n"
printf "  ${GRN}+=========================================================+${NC}\n\n"
printf "  Getting started:\n"
printf "   ${GRY}1. Go to the 'Auth' tab and connect your LinkedIn browser profile${NC}\n"
printf "   ${GRY}2. Use 'Scrape' to find LinkedIn profiles by keyword or group${NC}\n"
printf "   ${GRY}3. Use 'Profiles' to enrich them and see contact details${NC}\n"
printf "   ${GRY}4. Use 'Email' to build and send outreach campaigns${NC}\n\n"
divider
printf "  Server log (Ctrl+C to stop):\n"
divider; echo

# ── Stream server log ──────────────────────────────────────────
tail -f "$SRV_LOG" 2>/dev/null | while IFS= read -r line; do
    if   echo "$line" | grep -qiE 'error';              then printf "  ${RED}%s${NC}\n" "$line"
    elif echo "$line" | grep -qiE 'warning|warn';       then printf "  ${YLW}%s${NC}\n" "$line"
    elif echo "$line" | grep -qiE 'uvicorn|started|running on'; then printf "  ${GRN}%s${NC}\n" "$line"
    else                                                     printf "  ${GRY}%s${NC}\n" "$line"
    fi
done

wait "$SRV_PID" 2>/dev/null || true
