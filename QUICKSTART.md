# LinkedIn Scraper - Setup Complete!

## INSTALLATION

To install all dependencies, run:
```
pip install -r requirements.txt
```

Dependencies include:
- selenium (for web scraping)
- fastapi (for REST API)
- uvicorn (for API server)
- pydantic (for data validation)
- pandas (for data management)

## USAGE OPTIONS

### 1. CLI MODE (Command Line Interface):

New CLI (recommended):
```
python cli.py
```

Legacy CLI (backward compatible):
```
python main.py
```

### 2. API MODE (REST API Server):

Start the server:
```
python -m uvicorn api.app:app --reload
```

Or:
```
python api/app.py
```

Then access:
- API Docs (Swagger): http://localhost:8000/docs
- Alternative Docs: http://localhost:8000/redoc
- Health Check: http://localhost:8000/health

### 3. WEB MODE (Control Panel):

The project now includes a beautiful web interface for managing Google -> LinkedIn scraping.

Access:
- Open `frontend/index.html` in your browser (use Live Server for best results)
- Features: Real-time progress monitoring, results table, and CSV export.

## DOCUMENTATION

- README.md - Complete guide for CLI and API
- API_EXAMPLES.md - Detailed API usage examples

## API AUTHENTICATION

Default API Key: dev-api-key-change-in-production
**IMPORTANT:** Change this in production!
Configure in: config/api_config.py

## PROJECT STRUCTURE

```
api/          - REST API endpoints and models
core/         - Shared business logic
  services/   - Service layer (ScraperService, etc.)
actions/      - LinkedIn action implementations
scraper/      - Scraping logic
auth/         - Authentication handlers
utils/        - Utility functions
data/         - Output CSV files
```

## FEATURES

- Group member scraping
- Profile search & scraping
- Google-based LinkedIn scraping
- Single connection requests
- Mass connection requests
- Group messaging
- CLI interface (original + new)
- REST API with Swagger docs
- Background job processing
- API authentication

## EXAMPLE API REQUEST

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

## QUICK TEST

To test the API is working:
1. Install dependencies: `pip install -r requirements.txt`
2. Start server: `python -m uvicorn api.app:app --reload`
3. Visit: http://localhost:8000/health
4. Explore: http://localhost:8000/docs

## Ready to use!

Check README.md for detailed instructions.
