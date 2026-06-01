# Architecture Deep Dive

## Overview

The application is a FastAPI backend with a vanilla JS single-page frontend. There is no React, no build step, no bundler. The HTML is served as a static file by FastAPI; JavaScript calls the API with `fetch()`.

All scraping runs Selenium against a local Chrome instance. All persistent data goes into a single SQLite file. All background work uses FastAPI's `BackgroundTasks` with an in-memory job dictionary.

---

## Layer Breakdown

### Layer 1 — Frontend (frontend/)

Static files: `index.html`, `app.js`, `styles.css`.

Served by FastAPI via `StaticFiles`:
```python
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
```

`app.js` contains all JavaScript. Pattern:
- One `init*()` function per tab, called from `DOMContentLoaded`
- All API calls go through `apiFetch(url, method, body)` which adds the `X-API-Key` header
- Long-running operations return a `job_id` and the UI polls `/api/jobs/{job_id}` every 2s
- Toast notifications via `showToast(message, type)`
- HTML escaping via `esc(str)` before inserting user data into the DOM

The UI uses CSS custom properties (`--accent`, `--surface`, `--border`, etc.) and a dark theme defined in `styles.css`. No external UI library.

### Layer 2 — API (api/)

FastAPI application. Each feature has its own router file in `api/routes/`. Routers are registered in `api/app.py`:
```python
app.include_router(email_router, prefix="/api")
```

**Request handling flow:**
1. FastAPI receives request → validates Pydantic model
2. `Depends(verify_api_key)` runs: passes if localhost, checks header otherwise
3. Route handler creates a job (for long tasks) or executes directly (for CRUD)
4. Background task thread calls service layer
5. Response returns immediately (job_id) or with data (CRUD)

**Job store** (`api/dependencies.py`):
```python
jobs_store: dict[str, dict] = {}

def create_job(job_type: str) -> str:
    job_id = str(uuid4())
    jobs_store[job_id] = {"status": "pending", "progress": 0, ...}
    return job_id

def update_job(job_id: str, **kwargs):
    jobs_store[job_id].update(kwargs)
```

The job store is in-memory only — it resets on server restart. Job IDs are UUIDs. The client polls `GET /api/jobs/{job_id}` to track progress.

### Layer 3 — Services (core/services/)

Business logic lives here. Services are stateless classes with `@staticmethod` methods. They do not touch Selenium directly — they receive a `driver` argument.

```
ScraperService            → calls scraper/ modules
ConnectionService         → calls actions/connection_sender.py
MessagingService          → calls actions/group_outreach.py
ProfileEnricherService    → calls scraper/profile_enricher/enricher.py
EmailSendingService       → calls core/email_sender.py + core/database.py
EmailTestingService       → calls core/email_tester.py
EmailScheduler            → orchestrates scheduled campaigns
```

### Layer 4 — Core (core/)

Infrastructure that multiple services share:

| Module | Responsibility |
|---|---|
| `database.py` | All SQLite queries — the only place SQL is written |
| `driver_manager.py` | Chrome WebDriver creation, profile detection, cleanup |
| `auth_manager.py` (in auth/) | LinkedIn login strategy chain |
| `email_sender.py` | SMTP connection, sending, preset config |
| `email_tester.py` | Email validation (DNS MX + SMTP probe) |
| `groq_service.py` | Groq AI API wrapper with fallback chain |
| `cv_generator.py` | LaTeX CV generation from profile data |
| `export_manager.py` | CSV/Excel export |

### Layer 5 — Components (components/)

Selenium UI interactions, organized by LinkedIn page section. This layer is the only place that should reference XPath/CSS selectors.

```
components/selectors.py         All XPath and CSS strings — one file
components/common/
    navigation.py               navigate_to(driver, url)
    scrolling.py                scroll_to_element(), scroll_page()
    waits.py                    Custom ExpectedConditions
    popups.py                   Dismiss modals and overlays
components/connection/
    buttons.py                  click_connect_button()
    modal.py                    Handle the connection note modal
components/profile/
    header.py                   Extract name, title, company from profile header
    about.py                    Extract the About section
    experience.py               Extract job history
    education.py                Extract education
components/group/
    members.py                  Scroll and collect group member elements
    search.py                   Group search interface
components/search/
    results.py                  Parse search result cards
    pagination.py               Navigate to next page
    google_selectors.py         Google-specific element selectors
    google_utils.py             Google search utilities
components/messaging/
    compose.py                  Open message compose window
```

### Layer 6 — Scrapers (scraper/)

High-level scraping orchestration that uses `components/` for element interactions.

```
scraper/group_scraper.py              Scroll + collect group members
scraper/smart_search_group.py         Advanced group search
scraper/profile_enricher/
    enricher.py                       Main pipeline — reads CSV → enriches → saves
    profile_scraper.py                Visit one profile, extract all data
    domain_finder.py                  Google search for company domain
    email_generator.py                Generate email address formats
    csv_processor.py                  CSV I/O
```

---

## Data Flow: Scraping a Group

```
User clicks "Scrape Group" in dashboard
    → POST /api/scrape/group {group_url, max_members}
    → create_job("scrape_group") → returns job_id immediately
    → BackgroundTask starts:
        → DriverManager.setup_chrome_driver()
        → AuthManager.login(driver)
        → ScraperService.scrape_group_members(driver, group_url, max_members)
            → group_scraper.py scrolls and collects member elements
            → components/group/members.py extracts data from each element
            → database.py save_search_profile() for each member (batched)
        → update_job(job_id, status="completed", result={count: n})
        → DriverManager.cleanup_driver(driver)
    
Client polls GET /api/jobs/{job_id} every 2s
    → returns {status, progress, result}
    → on "completed": renders results in UI
```

## Data Flow: Email Campaign Send

```
User prepares a campaign:
    POST /api/email/campaigns/{id}/prepare
        → EmailSendingService.prepare_campaign_emails(campaign_id)
            → get_all_enriched_profiles() from DB
            → for each profile: create email_sends row with status="pending"
        → returns {count: n}

User sends the campaign:
    POST /api/email/campaigns/{id}/send {smtp_preset, username, password}
        → BackgroundTask starts:
            → get_campaign_email_sends(campaign_id, status="pending")
            → EmailSender.from_preset(preset, user, pwd) as SMTP context
            → for each pending send:
                → render template with profile variables
                → sender.send_email(to, subject, body)
                → update_email_send_status(send_id, "sent")
                → random delay (EMAIL_MIN_DELAY to EMAIL_MAX_DELAY seconds)
            → update_campaign_stats(campaign_id)
```

## Data Flow: Profile Enrichment

```
POST /api/enrich/db {max_profiles: 50}
    → BackgroundTask:
        → DriverManager.setup_chrome_driver()
        → AuthManager.login(driver)
        → ProfileEnricherService.enrich_profiles_from_db(driver, max_profiles=50)
            → get_all_enriched_profiles(not_yet_enriched=True)
            → for each profile_url:
                → driver.get(profile_url)
                → profile_scraper.scrape_profile_data(driver)
                    → components/profile/header.py → name, title, company
                    → components/profile/about.py → about text
                    → components/profile/experience.py → job history
                → domain_finder.find_domain(company_name)
                    → Google search "site:linkedin.com company_name"
                    → extract domain from result
                → email_generator.generate_all_formats(first, last, domain)
                → database.save_enriched_profile(profile_data)
                → sleep(ENRICHER_PROFILE_DELAY)
        → DriverManager.cleanup_driver(driver)
```

---

## Authentication Flow

`AuthManager.login(driver)` tries three strategies in order:

1. **Already logged in** — `_verify_login(driver, timeout=3)` checks if the LinkedIn feed is loaded. If so, nothing to do.

2. **Cookie login** — if `.auth/cookies.pkl` exists, loads and injects cookies, then navigates to LinkedIn and checks login status.

3. **Credential login** — fills in email/password on the LinkedIn login page. Saves cookies on success.

**Browser profile** — if the user has selected a Chrome profile via the Auth tab, `DriverManager.get_active_profile_config()` returns that profile's data dir. Chrome is launched pointing to that profile, which already has the LinkedIn session. Strategy 1 immediately succeeds.

---

## API Key Authentication

`api/middleware/auth.py` defines `verify_api_key()`:

```python
async def verify_api_key(request: Request, x_api_key: str = Header(None)):
    client = request.client
    host = client.host if client else ""
    if host in ("127.0.0.1", "::1", "localhost"):
        return  # localhost always passes
    valid = [k for k in APIConfig.API_KEYS if k]
    if not valid:
        return  # no key configured = open
    if x_api_key not in valid:
        raise HTTPException(403, "Invalid API key")
```

The browser dashboard (which runs at localhost) never needs a key. Remote integrations must send `X-API-Key: value` in the header.

---

## Background Job Lifecycle

```
create_job(type)
    status = "pending"
    
update_job(id, status="running", progress=10)
    status = "running"
    progress = 10

update_job(id, status="completed", progress=100, result={...})
    status = "completed"
    progress = 100

-- or on failure:

update_job(id, status="failed", error="message")
    status = "failed"
    error = "message"
```

The in-memory store has no expiry — jobs accumulate until server restart. This is fine for the current single-user usage pattern. If adding persistence or multi-user support, replace `jobs_store` dict in `api/dependencies.py` with Redis or a database table.

---

## Email Scheduler

`core/services/email_scheduler.py` implements `EmailScheduler.run()`:

1. Load all campaigns with `scheduled_at` set and status != "completed"
2. For each campaign, check if today matches `send_days` (0=Mon…6=Sun)
3. Check if current time is within `send_time_start`…`send_time_end`
4. Load active accounts; if `use_account_rotation=True`, rotate through them
5. Check each account's `daily_sent_today` vs `daily_limit`
6. Send up to `emails_per_day` emails for the campaign
7. Update `daily_sent_today` after each send

The scheduler runs on-demand via `POST /api/email/scheduler/run`. It is not a cron job — the user triggers it manually, or it can be called from an external scheduler (e.g. Windows Task Scheduler calling `start.bat`, or a cron job calling `curl`).

---

## Cross-Platform Browser Detection

`core/driver_manager.py` detects Chrome/Chromium in platform-specific locations:

**Windows** (`os.name == "nt"`):
- `%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe`
- `%PROGRAMFILES%\Google\Chrome\Application\chrome.exe`
- `%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe`
- `%PROGRAMFILES%\Microsoft\Edge\Application\msedge.exe`

**macOS** (`sys.platform == "darwin"`):
- `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`
- `/Applications/Chromium.app/Contents/MacOS/Chromium`
- `/Applications/Brave Browser.app/Contents/MacOS/Brave Browser`

**Linux** — `shutil.which()` for `google-chrome-stable`, `chromium-browser`, `chromium`, `brave-browser`; also checks `/snap/bin/chromium`

User-agent strings are also matched to the detected platform to avoid UA/OS mismatch.

---

## Groq AI Integration

`core/groq_service.py` wraps the Groq Python SDK:

- Default model: `llama-3.3-70b-versatile`
- Rate limit handling: catches 429, waits 60s, retries
- Fallback chain: if primary model fails 3 times, tries next model in `GroqConfig.FALLBACK_MODELS`
- CV generation: sends profile JSON + prompt to model, receives LaTeX string
- LaTeX compilation: `subprocess.run(["pdflatex", ...])` if pdflatex is installed

The Groq free tier allows ~30 requests/minute. The 60s wait on 429 handles this automatically.
