# Antigravity Developer Instructions

This file serves as a customized guide and instruction set for future Gemini/Antigravity AI agent instances. It helps agents immediately navigate the project architecture, leverage the correct tools, and maintain consistency with the existing design decisions of this repository.

---

## 1. Agent Tool Guidelines & Command Context

* **OS Environment:** The current system is running **Windows**. 
* **Shell Environment:** Use standard **PowerShell** syntax for commands.
* **Running the Backend Server:**
  - Launch command: `python -m uvicorn api.app:app --host localhost --port 8000`
  - For development (with hot-reload): `python -m uvicorn api.app:app --host localhost --port 8000 --reload`
* **Local Workspace Verification:**
  - Database verification check: Check contents of `data/db/linkedin_scraper.db`.
  - Log verification check: Monitor `data/logs/` directory for system/run logs.

---

## 2. Core Architecture Cheat Sheet

Any agent working in this repository must strictly adhere to the following architectural separation:

```
                  ┌───────────────────────────────┐
                  │   FastAPI Endpoints (api/)    │
                  └───────────────┬───────────────┘
                                  │ Uses
                  ┌───────────────▼───────────────┐
                  │    Service Layer (core/services/)│
                  └───────────────┬───────────────┘
                                  │ Orchestrates
          ┌───────────────────────┴───────────────────────┐
          │                                               │
┌─────────▼──────────┐                         ┌──────────▼──────────┐
│ Scrapers & Selenium│                         │   Database Access   │
│ (scraper/ &        │                         │ (core/database.py)  │
│  components/)      │                         └─────────────────────┘
└────────────────────┘
```

* **Frontend:** Single-page vanilla JavaScript app at `frontend/index.html` + `frontend/app.js` + `frontend/styles.css`.
* **API Key Auth:** Enforced via `api/middleware/auth.py` and standard router headers. Note that requests originating from `localhost` bypass this security check.
* **Selenium Setup:** Never use `webdriver.Chrome()` directly. Must use `core.driver_manager.DriverManager.setup_chrome_driver()`.
* **Database Updates:** Writing SQL anywhere other than `core/database.py` is **STRICTLY PROHIBITED**.

---

## 3. Step-by-Step Task Blueprints

### A. Modifying Database Schema
1. Open [core/database.py](file:///c:/Users/Admin/Desktop/LinkedIn-scraper-new_structure/core/database.py).
2. Locate `init_db(db_path)`. Add the `CREATE TABLE` query or add new fields using an suppressed alter-table block:
   ```python
   try:
       cursor.execute("ALTER TABLE table_name ADD COLUMN column_name TYPE")
   except sqlite3.OperationalError:
       pass
   ```
3. Create corresponding query wrapper functions (CRUD) below the table schema.

### B. Creating New Scraping Features
1. Add element selectors/XPaths to `MySelectors` in [components/selectors.py](file:///c:/Users/Admin/Desktop/LinkedIn-scraper-new_structure/components/selectors.py).
2. Create interaction components in `components/` (layered based on LinkedIn's visual grid structure).
3. Orchestrate scraper logic inside the `scraper/` folder.
4. Set up matching settings/timeouts inside [config/scraper_config.py](file:///c:/Users/Admin/Desktop/LinkedIn-scraper-new_structure/config/scraper_config.py).

### C. Integrating New API Routers
1. Create a router inside `api/routes/` with standard authentication parameters:
   ```python
   from api.middleware.auth import verify_api_key
   router = APIRouter(prefix="/my-feature", tags=["My Feature"], dependencies=[Depends(verify_api_key)])
   ```
2. For long-running tasks, register a FastAPI `BackgroundTasks` thread and execute the job asynchronously, updating status using `create_job()` and `update_job()`.
3. Register the router inside `api/app.py` using `app.include_router(router, prefix="/api")`.

### D. Modifying the Web Dashboard
1. Edit HTML tags inside [frontend/index.html](file:///c:/Users/Admin/Desktop/LinkedIn-scraper-new_structure/frontend/index.html).
2. Implement backend fetches and data rendering inside [frontend/app.js](file:///c:/Users/Admin/Desktop/LinkedIn-scraper-new_structure/frontend/app.js). **IMPORTANT:** Always filter string interpolations through the `esc()` function before appending to template literals to avoid XSS injections.
3. Edit theme styles inside [frontend/styles.css](file:///c:/Users/Admin/Desktop/LinkedIn-scraper-new_structure/frontend/styles.css) using the defined global variable system.
