# Coding Rules for Claude Code

This file defines the strict architectural constraints, style rules, and development guidelines for this repository. Follow these rules on every edit to ensure the codebase remains clean, modular, and cross-platform.

---

## 1. Core Architectural Constraints

* **Strict MVC/Service Decoupling:**
  - Never place business logic directly in API routes. Use the service layer in `core/services/`.
  - Never run raw Selenium actions in services or routes. Use scraper scripts in `scraper/` and low-level component wrappers in `components/`.

* **Unified SQLite Access (`core/database.py`):**
  - **CRITICAL:** Do NOT write raw SQL queries, `sqlite3.connect()`, or execution blocks in routes, services, or scraper scripts.
  - All database queries, insertions, schema modifications, and updates must reside inside [core/database.py](file:///c:/Users/Admin/Desktop/LinkedIn-scraper-new_structure/core/database.py).
  - Always call helper functions defined in `core/database.py` to retrieve or persist data.

* **Background Task Execution:**
  - Any operation taking more than ~2 seconds (e.g., Selenium scraping, profile visiting, email testing, mass campaigning) MUST run in a background thread via FastAPI's `BackgroundTasks`.
  - Always call `create_job()` from [api/dependencies.py](file:///c:/Users/Admin/Desktop/LinkedIn-scraper-new_structure/api/dependencies.py) to generate a UUID-based `job_id`, launch the background thread, and return the `job_id` immediately to the client.
  - Inside the background thread, call `update_job(job_id, status="running", progress=...)` to broadcast progress, and `update_job(job_id, status="completed", result=...)` or `status="failed", error=...` upon termination.

---

## 2. Technical Implementation Guidelines

### Selenium Browser Automation
* Never initialize `webdriver.Chrome()` directly.
* Always launch Chrome through the centralized setup:
  ```python
  from core.driver_manager import DriverManager
  driver, profile_dir = DriverManager.setup_chrome_driver()
  try:
      # Perform interactions
  finally:
      DriverManager.cleanup_driver(driver)
  ```
* All XPaths and CSS selectors must be defined in [components/selectors.py](file:///c:/Users/Admin/Desktop/LinkedIn-scraper-new_structure/components/selectors.py). Do not hardcode selector strings inside component scripts or services.

### Configuration & Settings
* Do not hardcode timeouts, sleeps, limits, or SMTP parameters.
* All configuration must be defined inside classes in [config/scraper_config.py](file:///c:/Users/Admin/Desktop/LinkedIn-scraper-new_structure/config/scraper_config.py), loading values from environment variables via `os.getenv()`.
* Add fallback values to `.env.example` when adding a new setting.

### Logging
* Do not use `print()` statements for regular messages.
* Always initialize a standard python logger at the module level:
  ```python
  import logging
  logger = logging.getLogger(__name__)
  ```
* Use standard levels (`logger.info()`, `logger.warning()`, `logger.error()`).

### Cross-Platform Compliance
* The code must run seamlessly on Windows, macOS, and Linux.
* Never use hardcoded slashes for file paths. Always use `os.path.join()` or `pathlib.Path` objects.
* When executing subprocesses, handle command string variations (e.g., `shell=True` on Windows).

---

## 3. Frontend & UI Guidelines

* **Vanilla Frameworkless Javascript:**
  - The frontend is located in the `frontend/` directory and consists of a single HTML page (`index.html`), a monolithic CSS sheet (`styles.css`), and a single Javascript sheet (`app.js`).
  - Do not introduce build tools (npm, webpack, vite) or component frameworks (React, Vue) unless explicitly instructed.
* **API Calls:**
  - All communication with the FastAPI backend must go through the custom `apiFetch()` helper in `app.js`. This automatically injects safety headers and checks for authentication.
* **Security & Escaping:**
  - **CRITICAL:** Always wrap dynamic strings in the `esc()` escaping helper function before inserting them into HTML string templates to prevent Cross-Site Scripting (XSS).
  - Example: `<div>${esc(profile.name)}</div>`
