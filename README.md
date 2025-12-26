# LinkedIn Scraper - CLI & API

A powerful LinkedIn scraping tool with both **Command-Line Interface (CLI)** and **RESTful API** capabilities.

## Features

- 🔍 **Group Member Scraping** - Extract member information from LinkedIn groups
- 🔎 **Profile Search** - Search and scrape LinkedIn profiles by keywords
- 🌐 **Google-Based Scraping** - Leverage Google search for LinkedIn profiles
- 🤝 **Connection Requests** - Send single or mass connection requests
- 💬 **Group Messaging** - Message all members of a group
- 🚀 **Dual Interface** - Use via CLI or REST API
- 📊 **CSV Export** - All data saved in CSV format
- 🔐 **Session Management** - Cookie-based authentication with auto-save

## Project Structure

```
linkkedIn_scraper/
├── api/                     # REST API layer
│   ├── routes/             # API endpoints
│   ├── models/             # Request/Response schemas
│   ├── middleware/         # Authentication & middleware
│   └── app.py              # FastAPI application
├── core/                    # Shared business logic
│   ├── services/           # Service layer
│   └── driver_manager.py   # Chrome driver management
├── actions/                 # Action implementations
├── auth/                    # Authentication logic
├── config/                  # Configuration files
├── scraper/                 # Scraping implementations
├── utils/                   # Utility functions
├── data/                    # Output data (CSV files)
├── cli.py                   # New CLI (recommended)
├── main.py                  # Legacy CLI (backward compatible)
└── requirements.txt         # Python dependencies
```

## Installation

1. **Clone the repository**
   ```bash
   cd linkkedIn_scraper
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Download ChromeDriver**
   - Download from https://chromedriver.chromium.org/
   - Place `chromedriver.exe` in the project root directory

4. **Configure LinkedIn credentials**
   - Update `config/settings.py` with your credentials (if needed)

## Usage

### CLI Mode

#### Using the New CLI (Recommended)
```bash
python cli.py
```

#### Using the Legacy CLI (Backward Compatible)
```bash
python main.py
```

Both CLIs offer the same 6 operations:
1. Scrape LinkedIn group members
2. Send messages to group members
3. Scrape profiles from LinkedIn search
4. Send a single connection request
5. Send mass connection requests from CSV
6. Scrape LinkedIn profiles using Google search

### API Mode

#### Start the API Server
```bash
python -m uvicorn api.app:app --reload --host 0.0.0.0 --port 8000
```

Or directly:
```bash
python api/app.py
```

#### Access API Documentation
Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

#### API Authentication
All API endpoints require an API key in the header:
```
X-API-Key: dev-api-key-change-in-production
```

⚠️ **Security Note**: Change the default API key in `config/api_config.py` or set the `API_KEY` environment variable.

#### Example API Requests

**1. Scrape Group Members**
```bash
curl -X POST "http://localhost:8000/api/v1/scrape/group" \
  -H "X-API-Key: dev-api-key-change-in-production" \
  -H "Content-Type: application/json" \
  -d '{
    "group_url": "https://www.linkedin.com/groups/12345/",
    "max_members": 100,
    "scraping_mode": "smart"
  }'
```

**2. Search Profiles**
```bash
curl -X POST "http://localhost:8000/api/v1/scrape/search" \
  -H "X-API-Key: dev-api-key-change-in-production" \
  -H "Content-Type: application/json" \
  -d '{
    "keywords": "technical recruiter",
    "max_profiles": 50,
    "start_page": 1
  }'
```

**3. Check Job Status**
```bash
curl -X GET "http://localhost:8000/api/v1/scrape/status/{job_id}" \
  -H "X-API-Key: dev-api-key-change-in-production"
```

**4. Send Connection Request**
```bash
curl -X POST "http://localhost:8000/api/v1/connections/send" \
  -H "X-API-Key: dev-api-key-change-in-production" \
  -H "Content-Type: application/json" \
  -d '{
    "profile_url": "https://www.linkedin.com/in/johndoe/",
    "note_message": "Hi, I'\''d like to connect!"
  }'
```

## API Endpoints

### Scraping
- `POST /api/v1/scrape/group` - Scrape group members
- `POST /api/v1/scrape/search` - Search and scrape profiles
- `POST /api/v1/scrape/google` - Google-based profile scraping
- `GET /api/v1/scrape/status/{job_id}` - Check scraping job status

### Connections
- `POST /api/v1/connections/send` - Send single connection
- `POST /api/v1/connections/mass-send` - Send mass connections
- `GET /api/v1/connections/status/{job_id}` - Check connection job status

### Messaging
- `POST /api/v1/messages/group` - Send group messages
- `GET /api/v1/messages/status/{job_id}` - Check messaging job status

### System
- `GET /health` - Health check
- `GET /` - API information

## Configuration

### API Configuration (`config/api_config.py`)
```python
# Server settings
HOST = "0.0.0.0"
PORT = 8000

# Security
API_KEY = "your-secure-api-key-here"

# Rate limiting
RATE_LIMIT_PER_MINUTE = 60
RATE_LIMIT_PER_HOUR = 1000
```

### Environment Variables
```bash
export API_HOST=0.0.0.0
export API_PORT=8000
export API_KEY=your-secure-key
export API_DEBUG=False
```

## Background Jobs

The API uses background tasks for long-running operations:
1. Request returns immediately with a `job_id`
2. Operation runs in the background
3. Check status using the `status/{job_id}` endpoint
4. Retrieve results when status is `completed`

## Data Output

All scraped data is saved in the `data/` directory as CSV files with timestamps.

## Troubleshooting

### ChromeDriver Issues
- Ensure ChromeDriver version matches your Chrome browser
- Check that `chromedriver.exe` is in the project root

### Login Issues
- Delete `cookies.pkl` to force fresh login
- Verify LinkedIn credentials in `config/settings.py`

### API Issues
- Check that the API key is correct
- Verify the server is running on the expected port
- Check logs for detailed error messages

## Security Best Practices

1. **Change the default API key** in production
2. **Use environment variables** for sensitive data
3. **Enable HTTPS** when deploying
4. **Implement rate limiting** to prevent abuse
5. **Monitor API usage** for anomalies

## Development

### Running in Development Mode
```bash
# CLI
python cli.py

# API with auto-reload
python -m uvicorn api.app:app --reload
```

### Project Architecture
- **Service Layer** (`core/services/`) - Business logic shared by CLI & API
- **API Layer** (`api/`) - REST API endpoints and models
- **Action Layer** (`actions/`) - LinkedIn automation actions
- **Scraper Layer** (`scraper/`) - Scraping implementations

## License

This tool is for educational purposes. Be respectful of LinkedIn's Terms of Service and rate limits.

## Disclaimer

Use this tool responsibly and in accordance with LinkedIn's Terms of Service. Excessive automation may result in account restrictions.
