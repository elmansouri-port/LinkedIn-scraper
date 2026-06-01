# Database Reference

All data is stored in a single SQLite file: `data/db/linkedin_scraper.db`

**Access:** Always through `core/database.py`. Never write SQL in routes or services.

**Connection:** WAL mode enabled for concurrent reads. Foreign keys enforced.

```python
from core.database import get_connection

conn = get_connection()          # uses default DB path
conn = get_connection(db_path)   # custom path (tests, etc.)
```

---

## Tables

### search_profiles

Profiles found by scraping (group members, search results, Google results). Not yet enriched.

```sql
CREATE TABLE search_profiles (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_url     TEXT UNIQUE NOT NULL,
    name            TEXT,
    title           TEXT,
    company         TEXT,
    location        TEXT,
    description     TEXT,
    search_keyword  TEXT,
    all_keywords    TEXT,       -- JSON array of all keywords that matched
    scraped_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

**Indexes:** `profile_url` (unique), `search_keyword`

---

### enriched_profiles

Profiles that have been visited and had their data extracted.

```sql
CREATE TABLE enriched_profiles (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_url     TEXT UNIQUE NOT NULL,
    name            TEXT,
    email           TEXT,               -- primary/best-guess email
    emails_json     TEXT,               -- JSON array of all generated emails
    company         TEXT,
    title           TEXT,
    location        TEXT,
    about           TEXT,
    experience_json TEXT,               -- JSON array of {title, company, dates}
    education_json  TEXT,               -- JSON array of {school, degree, dates}
    domain          TEXT,               -- company domain found via Google
    enriched_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

**Indexes:** `profile_url` (unique), `email`, `company`

---

### email_campaigns

Campaign definitions. A campaign is a template (subject + body) linked to a batch of sends.

```sql
CREATE TABLE email_campaigns (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    name                  TEXT NOT NULL,
    subject               TEXT NOT NULL,
    body_template         TEXT,                    -- plain text with {variables}
    body_template_html    TEXT,                    -- HTML version (optional)
    cv_path               TEXT,                    -- path to CV attachment
    cover_letter_path     TEXT,                    -- path to cover letter attachment
    status                TEXT DEFAULT 'draft',    -- draft | prepared | sending | completed
    total_prepared        INTEGER DEFAULT 0,
    total_sent            INTEGER DEFAULT 0,
    total_failed          INTEGER DEFAULT 0,

    -- Scheduling
    scheduled_at          TIMESTAMP,               -- one-time send time
    send_days             TEXT DEFAULT '0,1,2,3,4', -- Mon-Fri (0=Mon)
    send_time_start       TEXT DEFAULT '09:00',
    send_time_end         TEXT DEFAULT '17:00',
    emails_per_day        INTEGER DEFAULT 20,
    use_account_rotation  BOOLEAN DEFAULT 0,

    created_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

**Status flow:** `draft` → `prepared` → `sending` → `completed`

---

### email_sends

Individual email records within a campaign. One row per (campaign, recipient).

```sql
CREATE TABLE email_sends (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id     INTEGER NOT NULL REFERENCES email_campaigns(id),
    profile_id      INTEGER,                -- enriched_profiles.id (nullable)
    email           TEXT NOT NULL,
    first_name      TEXT,
    last_name       TEXT,
    company         TEXT,
    status          TEXT DEFAULT 'pending', -- pending | sent | failed
    sent_at         TIMESTAMP,
    error_message   TEXT,
    custom_cv_path  TEXT,                   -- per-recipient CV override
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

**Indexes:** `campaign_id`, `status`, `email`

---

### email_accounts

SMTP accounts for sending campaigns.

```sql
CREATE TABLE email_accounts (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    email            TEXT UNIQUE NOT NULL,
    smtp_preset      TEXT NOT NULL,     -- gmail | outlook | office365 | yahoo | custom
    username         TEXT NOT NULL,
    password         TEXT NOT NULL,     -- stored in plain text in local SQLite
    daily_limit      INTEGER DEFAULT 50,
    daily_sent_today INTEGER DEFAULT 0,
    last_used_date   TEXT,              -- YYYY-MM-DD — reset trigger
    is_active        BOOLEAN DEFAULT 1,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

**Note:** Passwords are stored in plain text in the local SQLite file. This is intentional — the tool runs locally, the DB is not exposed. If adding multi-user or remote access, add encryption.

---

## Query Function Reference

All functions in `core/database.py`. Common signature: `(args..., db_path=None)` where `db_path=None` uses the default database.

### Profile Functions

```python
# Save a profile from scraping
save_search_profile(profile_url, name, title, company, location,
                    description, keyword, all_keywords, db_path=None) -> bool

# Get all search profiles (not yet enriched)
get_all_search_profiles(db_path=None) -> list[dict]

# Save an enriched profile (upsert by profile_url)
save_enriched_profile(profile_url, name, email, emails_json,
                      company, title, location, about,
                      experience_json, education_json, domain, db_path=None) -> bool

# Get all enriched profiles
get_all_enriched_profiles(db_path=None) -> list[dict]

# Unified paginated view (both tables)
get_unified_profiles(page=1, per_page=50, search="", source="", db_path=None) -> dict
    # Returns: {"profiles": [...], "total": n, "page": p, "per_page": pp}

# Single profile by ID (searches both tables)
get_profile_by_id(profile_id, db_path=None) -> dict | None

# Delete a profile
delete_profile_by_id(profile_id, source, db_path=None) -> bool

# Stats
get_stats(db_path=None) -> dict
    # Returns: {"search_profiles": n, "enriched_profiles": n, ...}
```

### Campaign Functions

```python
# Create a new campaign
create_email_campaign(name, subject, body_text, body_html=None,
                      cv_path=None, cover_letter_path=None, db_path=None) -> dict
    # Returns: {"success": bool, "campaign_id": int, "message": str}

# Get one campaign by ID
get_email_campaign(campaign_id, db_path=None) -> dict | None

# Get all campaigns
get_all_email_campaigns(db_path=None) -> list[dict]

# Update campaign stats (total_sent, total_failed, etc.)
update_campaign_stats(campaign_id, sent=0, failed=0, db_path=None)

# Update status
update_campaign_status(campaign_id, status, db_path=None)
    # status: "draft" | "prepared" | "sending" | "completed"

# Update scheduling fields
update_campaign_schedule(campaign_id, scheduled_at=None, send_days=None,
                         send_time_start=None, send_time_end=None,
                         emails_per_day=None, use_account_rotation=None, db_path=None)
```

### Email Send Functions

```python
# Create a pending send record
save_email_send(campaign_id, email, first_name="", last_name="",
                company="", profile_id=None, db_path=None) -> int
    # Returns: new send record ID

# Update a send record after attempt
update_email_send_status(send_id, status, error_message=None, db_path=None)
    # status: "sent" | "failed"

# Get sends for a campaign (paginated)
get_campaign_email_sends(campaign_id, status="", page=1, per_page=50, db_path=None) -> dict

# Get aggregate stats for a campaign (or all campaigns)
get_email_send_stats(campaign_id=None, db_path=None) -> dict
    # Returns: {"pending": n, "sent": n, "failed": n}
```

### Account Functions

```python
# Get all accounts
get_email_accounts(active_only=False, db_path=None) -> list[dict]

# Add a new account
add_email_account(email, smtp_preset, username, password,
                  daily_limit=50, db_path=None) -> dict

# Increment daily sent counter
increment_account_daily_sent(account_id, db_path=None)

# Reset all accounts' daily_sent_today to 0
reset_daily_counts(db_path=None)
```

---

## Query Patterns

### Always use context-managed connections

```python
def my_query(db_path=None):
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT ...")
        rows = cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
```

`get_connection()` sets `row_factory = sqlite3.Row`, so you can access columns by name: `row["name"]`. Convert to `dict` before returning so callers get a plain Python dict.

### Upsert pattern (used for profiles)

```python
cursor.execute("""
    INSERT INTO enriched_profiles (profile_url, name, email, ...)
    VALUES (?, ?, ?, ...)
    ON CONFLICT(profile_url) DO UPDATE SET
        name = excluded.name,
        email = excluded.email
""", (url, name, email, ...))
```

### JSON storage for arrays

```python
import json

# Save
experience_json = json.dumps(experience_list)
cursor.execute("UPDATE ... SET experience_json=?", (experience_json,))

# Load
row = cursor.fetchone()
experience = json.loads(row["experience_json"] or "[]")
```

### Adding a column to existing table

SQLite doesn't support `ADD COLUMN IF NOT EXISTS`, so use try/except:

```python
try:
    cursor.execute("ALTER TABLE my_table ADD COLUMN new_col TEXT")
except sqlite3.OperationalError:
    pass  # column already exists — normal on subsequent startups
```

Always do this inside `init_db()` so it runs on startup.

---

## Database Migrations

There is no migration framework. Schema changes work as follows:

1. New tables: add `CREATE TABLE IF NOT EXISTS` to `init_db()` — safe to run multiple times
2. New columns: add `ALTER TABLE ... ADD COLUMN` with try/except in `init_db()` — safe to run multiple times
3. Removed columns: SQLite doesn't support `DROP COLUMN` before SQLite 3.35. If needed, use table recreation (rare)
4. Data migrations: write a one-time script in `utils/` or `scripts/`, not inside `init_db()`

`init_db()` is called on every server startup from `api/app.py`'s lifespan handler. It must be idempotent.

---

## Database File Location

```python
from config.scraper_config import DB_DIR

DB_NAME = "linkedin_scraper.db"
DB_PATH = os.path.join(DB_DIR, DB_NAME)  # data/db/linkedin_scraper.db
```

`DB_DIR` is `BASE_DIR / "data" / "db"` where `BASE_DIR` is the project root (resolved relative to `config/scraper_config.py`). The directory is created at import time if it doesn't exist.

To use a different database (tests, separate projects):
```python
result = get_my_records(db_path="/tmp/test.db")
```

---

## Backup

The database is a single file. Back it up with:

```bash
# Linux/macOS
cp data/db/linkedin_scraper.db data/db/backup_$(date +%Y%m%d).db

# Windows PowerShell
Copy-Item data\db\linkedin_scraper.db "data\db\backup_$(Get-Date -Format yyyyMMdd).db"
```

For live backups while the server is running, use SQLite's `.backup` API or `sqlite3` CLI:

```bash
sqlite3 data/db/linkedin_scraper.db ".backup data/db/backup.db"
```
