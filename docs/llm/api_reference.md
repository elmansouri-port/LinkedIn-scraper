# API Reference

Base URL: `http://localhost:8000`

Authentication: `X-API-Key: {your-key}` header. Localhost requests bypass auth automatically.

All endpoints return JSON. Long-running operations return `{"job_id": "...", "status": "pending"}` immediately; poll `GET /api/jobs/{job_id}` for results.

---

## Health

### GET /api/health
No auth required. Used by launchers to confirm the server started.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-05-21T10:00:00Z",
  "version": "2.0.0"
}
```

---

## Jobs

### GET /api/jobs/{job_id}

Poll the status of a background job.

**Response:**
```json
{
  "job_id": "uuid",
  "type": "scrape_group",
  "status": "running",        // pending | running | completed | failed
  "progress": 45,             // 0–100
  "result": null,             // filled on completed
  "error": null,              // filled on failed
  "created_at": "2026-05-21T10:00:00"
}
```

---

## Scraping

### POST /api/scrape/group

Scrape LinkedIn group members.

**Request:**
```json
{
  "group_url": "https://www.linkedin.com/groups/1234/members/",
  "max_members": 100,          // null = unlimited
  "scraping_mode": "basic"     // "basic" | "detailed"
}
```

**Response:** Job response — poll for results.

---

### POST /api/scrape/search

Scrape LinkedIn search results.

**Request:**
```json
{
  "keywords": ["software engineer", "Paris"],
  "max_profiles": 50,
  "start_page": 1
}
```

**Response:** Job response.

---

### POST /api/scrape/google

Scrape LinkedIn profiles via Google search.

**Request:**
```json
{
  "keywords": ["CEO", "fintech", "France"],
  "oblig_keywords": ["LinkedIn"],   // must appear in result
  "max_profiles": 100,
  "max_pages": 10,
  "verbose": true
}
```

**Response:** Job response.

---

## Profiles

### GET /api/profiles

Unified profile list with search and pagination.

**Query params:**
- `page` (int, default 1)
- `per_page` (int, default 50)
- `search` (string) — filter by name, company, email
- `source` (string) — `"enriched"` | `"search"` | `""` (all)

**Response:**
```json
{
  "profiles": [{
    "id": 1,
    "source": "enriched",
    "name": "Alice Martin",
    "email": "alice.martin@company.com",
    "company": "Acme Corp",
    "title": "VP Sales",
    "location": "Paris",
    "profile_url": "https://linkedin.com/in/alice-martin"
  }],
  "total": 250,
  "page": 1,
  "per_page": 50
}
```

---

### GET /api/profiles/enriched

Enriched profiles only. Same query params as `/api/profiles`.

---

### GET /api/profiles/search

Search-result profiles (not yet enriched). Same query params.

---

### GET /api/profiles/{profile_id}

Single profile with full detail (experience, education, all email formats).

**Response:**
```json
{
  "id": 1,
  "source": "enriched",
  "name": "Alice Martin",
  "email": "alice.martin@company.com",
  "emails_json": ["alice.martin@acme.com", "amartin@acme.com"],
  "company": "Acme Corp",
  "title": "VP Sales",
  "about": "20 years in B2B sales...",
  "experience": [...],
  "education": [...],
  "domain": "acme.com",
  "profile_url": "https://linkedin.com/in/alice-martin"
}
```

---

### DELETE /api/profiles/{profile_id}

Delete a profile from the database.

**Response:** `{"success": true, "message": "Profile deleted"}`

---

### POST /api/enrich

Enrich profiles from a CSV file.

**Request:**
```json
{
  "csv_file_path": "/path/to/profiles.csv",
  "url_column": "Profile URL",
  "max_profiles": 50
}
```

**Response:** Job response.

---

### POST /api/enrich/db

Enrich profiles already in the database (from a previous scrape).

**Request:**
```json
{
  "max_profiles": 50,
  "profile_indices": [1, 2, 3],    // optional — specific IDs
  "range_start": 0,                 // optional — slice of all profiles
  "range_end": 100
}
```

**Response:** Job response.

---

### GET /api/export

Export all profiles to CSV.

**Response:** CSV file download.

---

### GET /api/stats

Database row counts.

**Response:**
```json
{
  "search_profiles": 1240,
  "enriched_profiles": 380,
  "email_campaigns": 4,
  "email_sends": 920,
  "email_accounts": 2
}
```

---

## Connections

### POST /api/connections/send

Send a single connection request.

**Request:**
```json
{
  "profile_url": "https://linkedin.com/in/alice-martin",
  "note_message": "Hi Alice, I'd like to connect.",
  "use_note": true
}
```

**Response:** Job response.

---

### POST /api/connections/mass-send

Send connection requests from a CSV file.

**Request:**
```json
{
  "csv_file_path": "/path/to/profiles.csv",
  "note_message": "Hi {first_name}, I'd love to connect.",
  "use_note": true
}
```

**Response:** Job response.

---

## Messaging

### POST /api/messages/group

Send messages to group members.

**Request:**
```json
{
  "group_data_file": "/path/to/group_members.csv"
}
```

**Response:** Job response.

---

## Authentication

### GET /api/auth/profiles

Detect Chrome/Chromium profiles installed on this machine.

**Response:**
```json
{
  "profiles": [
    {
      "name": "Work Profile",
      "dir": "Profile 1",
      "data_dir": "C:/Users/user/AppData/Local/Google/Chrome/User Data",
      "path": "C:/Users/user/AppData/Local/Google/Chrome/User Data/Profile 1"
    }
  ],
  "active_profile_dir": "Profile 1"
}
```

---

### GET /api/auth/status

Current authentication configuration.

**Response:**
```json
{
  "method": "browser_profile",     // "browser_profile" | "credentials" | "none"
  "profile_name": "Work Profile",
  "profile_dir": "Profile 1",
  "email": "user@example.com"
}
```

---

### POST /api/auth/profile

Save a Chrome profile selection for future sessions.

**Request:**
```json
{
  "profile_dir": "Profile 1",
  "profile_name": "Work Profile",
  "data_dir": "C:/Users/user/AppData/Local/Google/Chrome/User Data"
}
```

**Response:** `{"success": true, "message": "Profile saved"}`

---

### DELETE /api/auth/profile

Clear the saved profile — next session will use fresh profile or credentials.

**Response:** `{"success": true, "message": "Profile cleared"}`

---

## Email Campaigns

### GET /api/email/campaigns

List all campaigns.

**Response:**
```json
{
  "campaigns": [{
    "id": 1,
    "name": "Q2 Outreach",
    "subject": "Quick question, {first_name}",
    "status": "prepared",
    "stats": {
      "pending": 120,
      "sent": 45,
      "failed": 3
    },
    "scheduled_at": null,
    "send_days": "0,1,2,3,4",
    "send_time_start": "09:00",
    "send_time_end": "17:00",
    "emails_per_day": 20
  }]
}
```

---

### POST /api/email/campaigns

Create a campaign.

**Request:**
```json
{
  "name": "Q2 Outreach",
  "subject": "Quick question, {first_name}",
  "body_text": "Hi {first_name},\n\nI came across your profile at {company}...",
  "body_html": "<p>Hi {first_name},</p>...",   // optional
  "cv_path": "/path/to/cv.pdf",                 // optional
  "cover_letter_path": "/path/to/cl.pdf"        // optional
}
```

**Template variables:** `{first_name}`, `{last_name}`, `{full_name}`, `{email}`, `{company}`, `{title}`, `{location}`

**Response:**
```json
{"success": true, "message": "Campaign 'Q2 Outreach' created", "campaign_id": 1}
```

---

### GET /api/email/campaigns/{id}

Get campaign detail.

**Response:** Full campaign object.

---

### DELETE /api/email/campaigns/{id}

Delete a campaign and all its send records.

**Response:** `{"success": true, "message": "Campaign deleted"}`

---

### POST /api/email/campaigns/{id}/prepare

Build the email queue — matches campaign to enriched profiles.

**Response:**
```json
{"success": true, "message": "Prepared 145 emails", "count": 145}
```

---

### GET /api/email/campaigns/{id}/preview

Get a rendered preview with a sample profile's data substituted.

**Response:**
```json
{
  "subject": "Quick question, Alice",
  "body_text": "Hi Alice,\n\nI came across your profile at Acme Corp...",
  "body_html": "<p>Hi Alice,</p>..."
}
```

---

### GET /api/email/campaigns/{id}/sends

Paginated list of individual send records.

**Query params:** `page`, `per_page`, `status` (`pending` | `sent` | `failed`)

**Response:**
```json
{
  "sends": [{
    "id": 42,
    "email": "alice@acme.com",
    "first_name": "Alice",
    "company": "Acme Corp",
    "status": "sent",
    "sent_at": "2026-05-21T10:15:00",
    "error_message": null
  }],
  "total": 145,
  "page": 1
}
```

---

### POST /api/email/campaigns/{id}/send

Execute the campaign send.

**Request:**
```json
{
  "smtp_preset": "gmail",
  "username": "sender@gmail.com",
  "password": "app-password",
  "max_send": 50,              // optional — limit this run
  "only_verified": false,
  "use_saved_account": false,  // if true, ignores preset/username/password
  "account_id": null,          // specific saved account ID
  "from_name": "Alice Martin"  // optional sender display name
}
```

**Response:** Job response.

---

### POST /api/email/campaigns/{id}/test

Send a test email to verify the campaign renders correctly.

**Request:**
```json
{
  "to_email": "test@example.com",
  "smtp_preset": "gmail",
  "username": "sender@gmail.com",
  "password": "app-password",
  "use_saved_account": false,
  "account_id": null
}
```

**Response:** `{"success": true, "message": "Test email sent to test@example.com"}`

---

### POST /api/email/campaigns/{id}/retry

Retry all failed sends for a campaign.

**Request:** Same shape as `/send`.

**Response:** Job response.

---

### POST /api/email/campaigns/{id}/schedule

Set or update the campaign's schedule.

**Request:**
```json
{
  "scheduled_at": "2026-05-25T09:00:00",   // one-time send (optional)
  "send_days": "0,1,2,3,4",               // Mon–Fri (0=Mon, 6=Sun)
  "send_time_start": "09:00",
  "send_time_end": "17:00",
  "emails_per_day": 20,
  "use_account_rotation": true
}
```

**Response:** `{"success": true, "message": "Campaign scheduled"}`

---

## SMTP Accounts

### GET /api/email/accounts

List saved SMTP accounts.

**Query params:** `active_only` (bool, default false)

**Response:**
```json
{
  "accounts": [{
    "id": 1,
    "email": "sender@gmail.com",
    "smtp_preset": "gmail",
    "username": "sender@gmail.com",
    "daily_limit": 50,
    "daily_sent_today": 12,
    "is_active": true,
    "last_used_date": "2026-05-21"
  }]
}
```

---

### POST /api/email/accounts

Add a new SMTP account.

**Request:**
```json
{
  "email": "sender@gmail.com",
  "smtp_preset": "gmail",
  "username": "sender@gmail.com",
  "password": "app-password",
  "daily_limit": 50
}
```

**Response:** `{"success": true, "message": "Account added", "account_id": 1}`

---

### PATCH /api/email/accounts/{id}

Update account status or daily limit.

**Request:**
```json
{
  "is_active": false,    // optional
  "daily_limit": 100     // optional
}
```

**Response:** `{"success": true, "message": "Account updated"}`

---

### DELETE /api/email/accounts/{id}

Delete an SMTP account.

**Response:** `{"success": true, "message": "Account deleted"}`

---

### POST /api/email/accounts/reset

Reset `daily_sent_today` to 0 for all accounts.

**Response:** `{"success": true, "message": "Daily counts reset"}`

---

### POST /api/email/scheduler/run

Trigger the email scheduler immediately.

**Response:** Job response.

---

## Email Verification

### POST /api/email/verify

Validate email addresses.

**Request:**
```json
{
  "email": "alice@acme.com",   // single email, OR:
  "method": "dns",             // "dns" | "smtp"
  "max_test": 100              // limit when validating all profiles
}
```

**Response:** `{"success": true, "valid": true, "reason": "MX record found"}`

---

## CV Generation

### POST /api/cv/generate

Generate a CV from enriched profile data.

**Request:**
```json
{
  "profile_url": "https://linkedin.com/in/alice-martin",  // specific profile
  "generate_all": false                                    // true = all profiles
}
```

**Response:** Job response. Result contains path to generated PDF/LaTeX file.

---

## Backward-Compatible Endpoints

These flat endpoints exist for compatibility with older integrations. Prefer the resource-based endpoints above.

```
POST /api/email/send       Send a campaign (flat body including campaign_id)
POST /api/email/schedule   Schedule a campaign (flat body including campaign_id)
```
