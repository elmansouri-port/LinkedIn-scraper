# LinkedIn Scraper — Full Pipeline Tool

A complete LinkedIn automation tool that finds profiles, enriches them with details, generates email addresses, and exports everything to clean spreadsheets anyone can use.

---

## For Non-Technical Users

### What This Tool Does

Imagine you want to build a contact list of **growth hackers in France**. Here's the full workflow:

**Step 1: Find People** — The tool searches Google for LinkedIn profiles matching your keywords (e.g., "growth hacker" + "France") and saves the results.

**Step 2: Enrich Profiles** — The tool visits each profile one by one and extracts: full name, about section, all work experiences, education, and current company.

**Step 3: Generate Emails** — Using the person's name and their current company's website, the tool generates likely email addresses (like `john.doe@company.com`).

**Step 4: Export** — You get a clean CSV or Excel file with all the data, ready to open in Excel or Google Sheets.

### The 3 Export Options

| Export | What It Contains | When to Use |
|--------|-----------------|-------------|
| **Search Profiles** | Name, title, company, location, search keyword | Just want a quick list of who was found |
| **Enriched Profiles (Basic)** | Name, about, all experiences, education, current role | Need full professional profiles |
| **Enriched + Emails (Full)** | Everything above + generated email addresses | Ready-to-use contact database |

### How to Get Started

1. Open a terminal and run: `python main.py`
2. Choose **10. Authentication setup** → log in once (via Google, Apple, or email)
3. Choose **6. Scrape LinkedIn profiles (Google search)** → enter keywords and country
4. Choose **7. Enrich profiles** → provide the CSV with URLs from step 3
5. Choose **8. Export to CSV/Excel** → pick what you want to export

That's it. No coding needed.

---

## For Technical Users

### Features

| Category | Feature | Description |
|----------|---------|-------------|
| **Scraping** | Group Members | Extract members from LinkedIn groups |
| | Profile Search | Search and scrape by keywords |
| | Google Search | Find profiles via Google (no LinkedIn login needed) |
| **Enrichment** | Profile Visit | Extract name, about, all experiences, education |
| | Domain Discovery | Google search for company websites |
| | Email Generation | 10 corporate email patterns with likelihood scoring |
| **Outreach** | Connection Requests | Single or mass connection with notes |
| | Group Messaging | Message group members |
| **Data** | Unified SQLite DB | Single `data/db/linkedin_scraper.db` for all data |
| | Export Presets | 3 pre-built exports: search, enriched, enriched+emails |
| | CSV & Excel | Export with human-readable column names, flattened JSON |
| **Auth** | Cookie-Based | Saves session cookies after first login |
| | Credential-Based | Email + password from `.env` |
| | Manual/OAuth | Browser login via Google/Apple, auto-captures cookies |
| **API** | FastAPI | RESTful API with background jobs |
| | Authenticated | API key header for all endpoints |

### Project Structure

```
LinkedIn-scraper/
├── api/                     # REST API layer (FastAPI)
│   ├── routes/              # API endpoints
│   ├── models/              # Request/Response schemas
│   └── app.py               # FastAPI application
├── auth/                    # Authentication manager
├── components/              # Reusable UI extraction components
│   ├── common/              # Navigation, scrolling, popups
│   ├── profile/             # name.py, about.py, experience.py, education.py
│   ├── search/              # Google selectors & utilities
│   └── selectors.py         # Centralized semantic selectors
├── config/                  # scraper_config.py, api_config.py
├── core/                    # Shared business logic
│   ├── services/            # Scraper, Connection, Messaging, Enricher services
│   ├── database.py          # Unified SQLite manager (5 tables)
│   ├── export_manager.py    # 3 export presets with formatting
│   └── driver_manager.py    # Chrome driver management
├── scraper/                 # Scraping implementations
│   ├── group_scraper.py
│   ├── smart_search_group.py
│   ├── google_search_profile_scraper.py
│   └── profile_enricher/    # Enrichment pipeline
│       ├── profile_scraper.py    # Visits profiles, extracts all data
│       ├── enricher.py           # Orchestrates the pipeline
│       ├── domain_finder.py      # Google search for company domains
│       ├── email_generator.py    # Corporate email pattern generation
│       └── csv_processor.py      # CSV input handling
├── utils/                   # Logging, session state
├── data/                    # Runtime data (gitignored)
│   ├── db/                  # SQLite databases
│   ├── csv/                 # Exported files
│   └── logs/                # Log files
├── cli.py                   # Main CLI (all actions)
├── main.py                  # Entry point (runs cli.py)
└── requirements.txt         # Python dependencies
```

### Installation

```bash
# Clone and enter
cd LinkedIn-scraper

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Create a `.env` file from the example:

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```env
# LinkedIn credentials (optional — you can also log in manually)
LINKEDIN_EMAIL=your@email.com
LINKEDIN_PASSWORD=yourpassword

# API key (change for production)
API_KEY=your-secure-api-key-here
```

### Usage — CLI

```bash
# Activate venv, then run
source .venv/bin/activate
python main.py
```

#### All Actions

| # | Action | Auth Required | Description |
|---|--------|:-------------:|-------------|
| 1 | Scrape group members | Yes | Extract members from a LinkedIn group |
| 2 | Message group members | Yes | Send messages to group members |
| 3 | Search profiles | Yes | Scrape LinkedIn search results by keyword |
| 4 | Send connection request | Yes | Single connection with optional note |
| 5 | Mass connections | Yes | Send connections from a CSV list |
| 6 | Google search scraper | No | Find profiles via Google (no login needed) |
| 7 | Enrich profiles | Yes | Visit profiles, extract data, generate emails |
| 8 | Export to CSV/Excel | No | 3 presets: search, enriched, enriched+emails |
| 9 | View statistics | No | Row counts and export-ready data summary |
| 10 | Auth setup | — | Log in, manage cookies, set credentials |

### Full Pipeline Example

```
┌─────────────────────────────────────────────────────────┐
│  1. Google Scraper (Action 6)                           │
│     Input: keywords="growth hacker", location="France"  │
│     Output: 200 profiles → search_profiles table        │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│  2. Export Search Profiles (Action 8)                   │
│     Output: data/csv/search_profiles_TIMESTAMP.csv       │
│     Columns: Profile URL, Name, Title, Company, ...     │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│  3. Enrich Profiles (Action 7)                          │
│     Input: CSV from step 2 (with Profile URL column)    │
│     For each profile: visit → extract name, about,      │
│       experiences, education → find company domain →    │
│       generate emails                                   │
│     Output: enriched_profiles table                     │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│  4. Export Full Data (Action 8)                         │
│     Options: CSV or Excel                                │
│     Columns: Name, About, Experiences, Education,       │
│       Company Website, Primary Email, All Email Variants │
└─────────────────────────────────────────────────────────┘
```

### Authentication

Three methods, all save cookies for reuse:

**1. Manual Login (Recommended)**
```
Action 10 → Option 1
```
Opens LinkedIn in browser. Log in however you want (Google, Apple, phone). Auto-detects login and saves cookies.

**2. Credentials**
```
Action 10 → Option 2
```
Uses email/password from `.env` or prompts you.

**3. Auto (Other Actions)**
When running any LinkedIn action, it tries: saved cookies → credentials → offers manual login if both fail.

### Data Storage

All data goes to a single SQLite database: `data/db/linkedin_scraper.db`

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `search_profiles` | Google scraper results | profile_url, name, title, company, search_keyword |
| `enriched_profiles` | Full profile data + emails | first_name, last_name, about, experiences (JSON), education (JSON), current_company, generated_email, all_email_variants |
| `group_members` | Group scrape results | profile_url, name, title, group_name |
| `connections` | Connection request history | profile_url, name, message_sent, status |
| `messages` | Message history | profile_url, name, message_text, status |

### Export System

The export manager (`core/export_manager.py`) provides 3 presets with:
- Human-readable column names (no database field names)
- Flattened JSON data (experiences and education as readable text)
- Clean formatting for non-technical users

**Experiences example:**
```
Growth Manager at Acme Corp (Jan 2023 - Present · 1 yr 6 mos) | Marketing Intern at Startup Inc (Jun 2022 - Dec 2022 · 7 mos)
```

**Education example:**
```
ENCG-SETTAT (Master's Degree, Accounting and Business/Management, 2008 – 2013)
```

**Email variants example:**
```
john.doe@company.com; john_doe@company.com; johndoe@company.com
```

### API Mode

```bash
# Start server
source .venv/bin/activate
python -m uvicorn api.app:app --reload --host 0.0.0.0 --port 8000
```

**Endpoints:**
- `POST /api/v1/scrape/google` — Google-based profile search
- `POST /api/v1/connections/send` — Send connection request
- `POST /api/v1/messages/group` — Send group messages
- `GET /health` — Health check

**Auth:** All endpoints require `X-API-Key` header.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Chrome driver error | Make sure Chrome is installed. Selenium auto-manages drivers. |
| Login failed | Run Action 10 → Option 3 (clear cookies) → Option 1 (manual login) |
| No data in export | Run the scraper/enricher first. Action 9 shows available data counts. |
| Excel export fails | `pip install openpyxl` (already in requirements.txt) |
| Enricher skips profiles | Already enriched profiles are auto-skipped. Clear DB or use different CSV. |

### Security

1. Never commit `.env`, `.auth/`, `data/`, or `.venv/`
2. Change the default API key before production
3. Use manual OAuth login instead of storing credentials
4. Cookies expire — re-authenticate periodically

### License

For educational purposes. Respect LinkedIn's Terms of Service and rate limits.

### Disclaimer

Use responsibly. Excessive automation may result in account restrictions.
