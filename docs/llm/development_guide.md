# Development Guide

Practical instructions for common development tasks in this codebase.

---

## Running the Server Locally

```bash
# Activate the virtual environment
source venv/bin/activate        # Linux/macOS
venv\Scripts\activate           # Windows

# Run with auto-reload (development)
python -m uvicorn api.app:app --host 0.0.0.0 --port 8000 --reload

# Run production-style (as the launchers do)
python -m uvicorn api.app:app --host 0.0.0.0 --port 8000
```

The frontend is at `http://localhost:8000`. API docs at `http://localhost:8000/docs`.

---

## Adding a New API Endpoint

### Step 1 — Add to an existing router (most common)

Each feature has a router file in `api/routes/`. Open the relevant one.

```python
# In api/routes/email_routes.py (example)

class MyNewRequest(BaseModel):
    campaign_id: int
    some_option: str = "default"

@router.post("/campaigns/{campaign_id}/my-action", dependencies=[Depends(verify_api_key)])
async def my_action(campaign_id: int, req: MyNewRequest):
    result = EmailSendingService.do_something(campaign_id, req.some_option)
    if not result["success"]:
        raise HTTPException(400, result["message"])
    return result
```

### Step 2 — If it's a new feature domain, create a new router

```python
# api/routes/my_feature_routes.py
import logging
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from api.middleware.auth import verify_api_key

router = APIRouter(prefix="/my-feature", tags=["My Feature"])
logger = logging.getLogger(__name__)

@router.get("/items", dependencies=[Depends(verify_api_key)])
async def list_items():
    return {"items": []}
```

### Step 3 — Register in api/app.py

```python
from api.routes.my_feature_routes import router as my_feature_router
app.include_router(my_feature_router, prefix="/api")
# Results in: GET /api/my-feature/items
```

---

## Adding a Background Job

For operations that take more than ~2 seconds (any Selenium work):

```python
from api.dependencies import create_job, update_job
from fastapi import BackgroundTasks

@router.post("/long-operation", dependencies=[Depends(verify_api_key)])
async def long_operation(req: MyRequest, background_tasks: BackgroundTasks):
    job_id = create_job("my_operation")

    def task():
        try:
            update_job(job_id, status="running", progress=5)
            # ... setup driver ...
            driver, profile = DriverManager.setup_chrome_driver()
            try:
                update_job(job_id, status="running", progress=20)
                result = MyService.do_work(driver, req.param)
                update_job(job_id, status="completed", progress=100, result=result)
            finally:
                DriverManager.cleanup_driver(driver)
        except Exception as e:
            logger.error("Job failed: %s", e)
            update_job(job_id, status="failed", error=str(e))

    background_tasks.add_task(task)
    return {"job_id": job_id, "status": "pending", "message": "Job started"}
```

The frontend polls `GET /api/jobs/{job_id}`. Look at how `scraper_routes.py` handles this for a complete example.

---

## Adding a Database Table

All database work is centralized in `core/database.py`.

### Step 1 — Add CREATE TABLE to `init_db()`

```python
def init_db(db_path: str = None):
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    # ... existing tables ...
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS my_table (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            value TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_my_name ON my_table(name)")
    
    conn.commit()
    conn.close()
```

### Step 2 — Add query functions

```python
def save_my_record(name: str, value: str, db_path: str = None) -> int:
    conn = get_connection(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO my_table (name, value) VALUES (?, ?)",
            (name, value)
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()

def get_my_records(db_path: str = None) -> list:
    conn = get_connection(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM my_table ORDER BY created_at DESC")
        rows = cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
```

### Step 3 — Adding a column to an existing table

Use ALTER TABLE with error suppression (SQLite doesn't support IF NOT EXISTS for columns):

```python
# Inside init_db(), after the CREATE TABLE block:
try:
    cursor.execute("ALTER TABLE my_table ADD COLUMN new_column TEXT")
except sqlite3.OperationalError:
    pass  # column already exists
```

---

## Adding a New Service

Services live in `core/services/`. They are stateless — no `__init__`, just `@staticmethod` methods.

```python
# core/services/my_service.py
import logging
from typing import Dict, Any
from core.database import get_my_records, save_my_record

logger = logging.getLogger(__name__)


class MyService:

    @staticmethod
    def list_items(db_path: str = None) -> Dict[str, Any]:
        items = get_my_records(db_path)
        return {"success": True, "items": items, "count": len(items)}

    @staticmethod
    def create_item(name: str, value: str, db_path: str = None) -> Dict[str, Any]:
        try:
            item_id = save_my_record(name, value, db_path)
            return {"success": True, "message": f"Created '{name}'", "id": item_id}
        except Exception as e:
            logger.error("Failed to create item: %s", e)
            return {"success": False, "message": str(e)}
```

---

## Adding a Frontend Tab

### Step 1 — Add a tab button in index.html

Find the `<nav class="tab-nav">` section and add:

```html
<button class="tab" data-tab="my-tab">My Tab</button>
```

### Step 2 — Add the tab content panel

Find the existing tab panels (look for `<div class="tab-panel" id="tab-*">`):

```html
<div class="tab-panel" id="tab-my-tab">
    <div class="section">
        <h2 class="section-title">My Feature</h2>
        
        <form id="my-form">
            <div class="form-group">
                <label class="form-label">Name</label>
                <input class="form-control" id="my-name" type="text" required />
            </div>
            <button type="submit" class="btn btn--primary">Submit</button>
        </form>
        
        <div id="my-results" class="mt-1"></div>
    </div>
</div>
```

### Step 3 — Add JavaScript in app.js

```javascript
// Add a function
function initMyTab() {
    document.getElementById("my-form").addEventListener("submit", async e => {
        e.preventDefault();
        const name = document.getElementById("my-name").value.trim();
        if (!name) return showToast("Name is required", "error");

        try {
            const res  = await apiFetch(`${API_BASE}/api/my-feature/items`, "POST", { name });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
            showToast(data.message || "Created", "success");
            loadMyItems();
        } catch (err) {
            showToast(`Error: ${err.message}`, "error");
        }
    });

    loadMyItems();
}

async function loadMyItems() {
    const $list = document.getElementById("my-results");
    try {
        const res  = await apiFetch(`${API_BASE}/api/my-feature/items`);
        const data = await res.json();
        const items = data.items || [];
        if (!items.length) {
            $list.innerHTML = '<p style="color:var(--text-muted);">No items yet.</p>';
            return;
        }
        $list.innerHTML = items.map(item => `
            <div class="list-item">
                <strong>${esc(item.name)}</strong>
                <span>${esc(item.value || "")}</span>
            </div>
        `).join("");
    } catch {
        $list.innerHTML = '<p style="color:var(--text-muted);">Failed to load.</p>';
    }
}
```

### Step 4 — Wire up in DOMContentLoaded

Find `document.addEventListener("DOMContentLoaded", () => {` near the bottom of `app.js` and add:

```javascript
initMyTab();
```

If the tab should only load data when opened (not at startup):

```javascript
document.querySelectorAll('.tab[data-tab="my-tab"]').forEach(btn =>
    btn.addEventListener("click", loadMyItems)
);
```

---

## Adding CSS for a New Feature

Add new styles to `frontend/styles.css` **before** the `/* Responsive */` section at the end of the file. Follow the existing pattern:

```css
/* ── My Feature ─────────────────────────────────── */
.my-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1rem 1.25rem;
    margin-bottom: .75rem;
}
.my-card-title {
    font-weight: 600;
    color: var(--text);
}
.my-badge {
    padding: .12rem .5rem;
    border-radius: 20px;
    font-size: .72rem;
    background: rgba(88,166,255,.1);
    color: var(--accent);
}
```

Use existing CSS variables (`--surface`, `--border`, `--accent`, `--text`, `--text-muted`, `--radius`, etc.). Never hardcode colors.

---

## Adding a Configuration Variable

### Step 1 — Add to the appropriate class in `config/scraper_config.py`

```python
class MyFeatureConfig:
    MAX_ITEMS = int(os.getenv("MY_MAX_ITEMS", "100"))
    ITEM_DELAY = float(os.getenv("MY_ITEM_DELAY", "1.0"))
```

### Step 2 — Add to `.env.example`

```env
# =============================================================================
# MY FEATURE
# =============================================================================
MY_MAX_ITEMS=100          # Maximum items to process
MY_ITEM_DELAY=1.0         # Delay between items in seconds
```

### Step 3 — Use in your code

```python
from config.scraper_config import MyFeatureConfig

delay = MyFeatureConfig.ITEM_DELAY
```

---

## Adding a Selenium Component

When adding new LinkedIn page interactions, add to `components/`.

### Step 1 — Add selectors to `components/selectors.py`

```python
# In components/selectors.py
class MySelectors:
    MY_BUTTON = "//button[contains(@class, 'my-btn')]"
    MY_LIST_ITEM = "//li[contains(@class, 'my-item')]"
    MY_TEXT_FIELD = (By.CSS_SELECTOR, ".my-field input")
```

### Step 2 — Create the component file

```python
# components/my_section/my_component.py
import logging
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from components.selectors import MySelectors

logger = logging.getLogger(__name__)


def click_my_button(driver) -> bool:
    try:
        btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, MySelectors.MY_BUTTON))
        )
        btn.click()
        return True
    except Exception as e:
        logger.warning("Could not click my button: %s", e)
        return False
```

---

## Working with the Email System

The email system has a clear lifecycle. Always follow it in order:

```
1. create_campaign() → campaign_id
2. prepare_campaign_emails(campaign_id) → builds email_sends rows
3. preview_email(campaign_id) → verify rendered output
4. send_campaign(campaign_id, smtp_config) → sends pending emails
```

**Key files:**
- `core/email_sender.py` — SMTP logic, preset config
- `core/services/email_sending_service.py` — campaign business logic
- `core/services/email_scheduler.py` — scheduled sending
- `core/database.py` — `create_email_campaign`, `save_email_send`, `update_email_send_status`

**Template rendering** — variables like `{first_name}` are substituted per-email using Python's `.format_map()` with profile data. Add new variables to the profile data dict in `EmailSendingService.prepare_campaign_emails()`.

---

## Debugging Tips

### Check what SQL queries run
```python
# Temporary: add to get_connection() in core/database.py
conn.set_trace_callback(print)
```

### Check if a profile exists in the DB
```python
from core.database import get_connection
conn = get_connection()
rows = conn.execute("SELECT * FROM enriched_profiles LIMIT 5").fetchall()
for r in rows: print(dict(r))
```

### Check job status without the frontend
```bash
curl http://localhost:8000/api/jobs/your-job-id-here
```

### Watch the server log
```bash
tail -f data/logs/server.log   # Linux/macOS
```

### Test a single API call
```bash
# No auth needed from localhost
curl -X POST http://localhost:8000/api/email/accounts/reset

# With auth (for remote calls)
curl -H "X-API-Key: your-key" http://localhost:8000/api/stats
```

---

## Common Mistakes to Avoid

**SQL in routes** — all queries go in `core/database.py`.

**Hardcoded timeouts** — use `config/scraper_config.py` classes.

**XPath strings in services** — add to `components/selectors.py`.

**`webdriver.Chrome()` directly** — always use `DriverManager.setup_chrome_driver()`.

**Skipping `verify_api_key`** — add `dependencies=[Depends(verify_api_key)]` to every new route.

**`print()` in modules** — use `logging.getLogger(__name__)`.

**Mutable `BaseModel` defaults** — use `Optional[list] = None`, not `list = []`.

**Non-escaped user data in HTML** — always call `esc()` before inserting strings into HTML in `app.js`.
