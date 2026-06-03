# LinkedIn Scraper — LLM Project Guide

This file is loaded automatically by Claude Code. It gives you everything you need to work effectively in this codebase without reading every file first.

## What this project is

A full-stack LinkedIn automation platform. Users scrape LinkedIn profiles, enrich them with contact info, run email campaigns, and send connection/message requests — all from a browser dashboard or REST API.

**Stack:** FastAPI + Selenium + SQLite + vanilla JS frontend. No framework on the frontend. Python 3.8+.

**Entry point:** `api/app.py` — the FastAPI application. Run with `python -m uvicorn api.app:app --host 0.0.0.0 --port 8000`.

**Launchers:** `LinkedIn Scraper.bat` (Windows) and `start.sh` (Linux/macOS) — one-click setup and run for non-technical users.

---

## Architecture in one page

```
frontend/              Vanilla JS dashboard served as static files
    index.html         Single-page app — all tabs in one file
    app.js             All JS — fetch() to the API, no bundler
    styles.css         CSS custom properties for dark theme

api/
    app.py             FastAPI app registration + shared routes (enrich, stats, jobs)
    dependencies.py    In-memory job store — create_job / update_job / get_job
    middleware/auth.py API key check — localhost always passes
    routes/            One file per feature area
    models/            Pydantic request + response models

core/
    database.py        ALL SQLite queries — one place for all DB access
    driver_manager.py  Chrome setup, profile detection, cross-platform
    email_sender.py    SMTP with preset support
    groq_service.py    Groq AI client with fallback chain
    services/          Business logic — one service class per domain

auth/
    auth_manager.py    Login: check profile → try cookies → try credentials

components/            Selenium element interactions — layered by LinkedIn UI section
    selectors.py       ALL XPath/CSS selectors in one place
    common/            navigation, scrolling, waits, popups
    connection/        connect button, note modal
    profile/           header, about, experience, education extraction
    group/             group member list
    search/            search results, pagination
    messaging/         compose window

scraper/
    group_scraper.py
    profile_enricher/  enricher.py → profile_scraper + domain_finder + email_generator

config/
    scraper_config.py  All config classes reading from env vars
    api_config.py      API-specific settings (CORS origins, rate limits)
```

---

## Key patterns to follow

### 1. Database access — always through `core/database.py`
Never write SQL in routes or services. Add a function to `core/database.py` and call it.

```python
# In core/database.py
def get_my_data(filter: str, db_path: str = None):
    conn = get_connection(db_path)
    ...
    conn.close()
    return result

# In a route or service
from core.database import get_my_data
data = get_my_data("value")
```

### 2. Background jobs — always use `create_job` / `update_job`
Long-running tasks (scraping, enrichment) return a job_id immediately and run in a background thread.

```python
from api.dependencies import create_job, update_job

@router.post("/my-route")
async def my_route(req: MyRequest, background_tasks: BackgroundTasks):
    job_id = create_job("my_job_type")

    def task():
        update_job(job_id, status="running", progress=10)
        # ... do work ...
        update_job(job_id, status="completed", progress=100, result={"count": n})

    background_tasks.add_task(task)
    return {"job_id": job_id, "status": "pending"}
```

Client polls: `GET /api/jobs/{job_id}`

### 3. Routes — always use `Depends(verify_api_key)` on new routes
```python
from api.middleware.auth import verify_api_key
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/my-feature", tags=["My Feature"])

@router.get("/items", dependencies=[Depends(verify_api_key)])
async def list_items():
    ...
```

Localhost bypasses the check automatically. Remote callers need `X-API-Key` header.

### 4. Selenium — use `DriverManager`, never build WebDriver directly
```python
from core.driver_manager import DriverManager

driver, profile_dir = DriverManager.setup_chrome_driver()
try:
    # do work
finally:
    DriverManager.cleanup_driver(driver)
```

### 5. Selectors — all XPath in `components/selectors.py`
Never put XPath strings in routes, services, or action files. Define in selectors.py and import.

### 6. Configuration — all env vars in `config/scraper_config.py`
New settings go in the appropriate Config class there. Never hardcode values in routes or services.

### 7. Logging — always use `logging.getLogger(__name__)`
```python
import logging
logger = logging.getLogger(__name__)
logger.info("...")
logger.warning("...")
logger.error("...")
```

Do not use `print()` in any module except the CLI entry points.

### 8. Frontend API calls — always use `apiFetch()`
```javascript
// app.js pattern — all fetch calls go through apiFetch()
const res  = await apiFetch(`${API_BASE}/api/email/accounts`);
const data = await res.json();
```

New frontend features: add a section to `frontend/index.html` and a function to `frontend/app.js`. Wire it up in the `DOMContentLoaded` block at the bottom of `app.js`.

---

## Adding a new feature — checklist

1. **Database** — add table/columns to `init_db()` in `core/database.py`, add query functions
2. **Service** — add a class or functions to `core/services/`
3. **Route file** — create `api/routes/my_feature_routes.py` with an `APIRouter`
4. **Register router** — in `api/app.py`: `app.include_router(my_router, prefix="/api")`
5. **Pydantic models** — add request/response models to `api/models/requests.py` / `responses.py`
6. **Frontend HTML** — add tab button and content section to `frontend/index.html`
7. **Frontend JS** — add load/submit functions to `frontend/app.js`, wire in `DOMContentLoaded`
8. **Frontend CSS** — add styles to `frontend/styles.css` before the `/* Responsive */` section
9. **Config** — add env vars to `config/scraper_config.py` and `.env.example`

---

## File map — quick reference

| File | Read this when you want to... |
|---|---|
| `api/app.py` | Understand app startup, shared routes (enrich, stats, export), job polling |
| `api/dependencies.py` | Understand how background jobs work |
| `api/middleware/auth.py` | Change auth logic |
| `api/routes/email_routes.py` | Work on email campaigns (most complex route file) |
| `api/routes/scraper_routes.py` | Work on scraping endpoints |
| `core/database.py` | Add/change any database table or query |
| `core/driver_manager.py` | Chrome/browser setup, profile detection, cross-platform paths |
| `core/email_sender.py` | SMTP sending, preset configuration |
| `core/groq_service.py` | Groq AI integration, model fallback |
| `core/services/email_sending_service.py` | Campaign prepare/send/retry logic |
| `core/services/email_scheduler.py` | Scheduled sending, daily limits, account rotation |
| `config/scraper_config.py` | All configuration classes and env var mappings |
| `components/selectors.py` | All XPath/CSS selectors for LinkedIn elements |
| `scraper/profile_enricher/enricher.py` | End-to-end enrichment pipeline |
| `frontend/app.js` | All dashboard JavaScript |
| `frontend/index.html` | Dashboard HTML structure and tab layout |
| `frontend/styles.css` | All styles, CSS custom properties |

---

## Database schema summary

```sql
-- Profiles found by scraping (search results)
search_profiles (id, profile_url, name, title, company, location, description, search_keyword, scraped_at)

-- Profiles fully enriched by visiting their LinkedIn page
enriched_profiles (id, profile_url, name, email, company, title, location, about,
                   experience_json, education_json, emails_json, domain, enriched_at)

-- Email campaigns
email_campaigns (id, name, subject, body_template, body_template_html,
                 cv_path, cover_letter_path, status,
                 scheduled_at, send_days, send_time_start, send_time_end,
                 emails_per_day, use_account_rotation, created_at)

-- Individual sends within a campaign
email_sends (id, campaign_id, profile_id, email, first_name, last_name, company,
             status [pending/sent/failed], sent_at, error_message, custom_cv_path)

-- SMTP accounts for sending
email_accounts (id, email, smtp_preset, username, password, daily_limit,
                daily_sent_today, last_used_date, is_active, created_at)
```

---

## Environment variables — the most important ones

```env
LINKEDIN_EMAIL        LinkedIn account email
LINKEDIN_PASSWORD     LinkedIn account password
API_KEY               40-char random key (auto-generated by launchers)
GROQ_API_KEY          Groq API key for CV generation
API_PORT              Server port (default 8000)
HEADLESS_MODE         true/false — run Chrome without GUI
LOG_LEVEL             DEBUG / INFO / WARNING / ERROR
```

Full list in `.env.example`.

---

## What NOT to do

- Do not put SQL queries in routes or services — use `core/database.py`
- Do not build `webdriver.Chrome()` directly — use `DriverManager.setup_chrome_driver()`
- Do not hardcode delays, timeouts, or limits — read from `config/scraper_config.py`
- Do not put XPath strings in services or routes — add to `components/selectors.py`
- Do not use `print()` in modules — use `logger = logging.getLogger(__name__)`
- Do not add auth checks for `localhost` in new routes — `verify_api_key` handles this automatically

---

## Cross-platform notes

The project runs on Windows, macOS, and Linux. These files already handle platform differences:

- `core/driver_manager.py` — browser binary detection and profile paths per OS
- `LinkedIn Scraper.bat` — Windows only (PowerShell)
- `start.sh` — Linux/macOS (bash)

When adding new file paths: use `os.path.join()` or `pathlib.Path`. Never hardcode `/` or `\` separators.

---

## Stale files to ignore

The following root-level .md files are old development notes from early iterations. They may be outdated — prefer `docs/llm/` and this file for current information:
- `API_EXAMPLES.md`, `AUTH_MIGRATION.md`, `AUTH_REFACTORING_SUMMARY.md`
- `QUICKSTART.md`, `PROFILE_ENRICHER_*.md`, `full_structure.md`, `refactor.md`

---

## More detailed docs

See `docs/llm/` for deeper references:

- `docs/llm/architecture.md` — Full architecture, data flow, background job lifecycle
- `docs/llm/api_reference.md` — Every endpoint with request/response shapes
- `docs/llm/development_guide.md` — Step-by-step guide for common development tasks
- `docs/llm/database.md` — Full database schema, query patterns, migration approach
