"""
Quick Start Guide - LinkedIn Scraper with API

This script helps you verify your installation and get started.
"""

print("="*60)
print("LinkedIn Scraper - API Integration Complete!")
print("="*60)

print("\n📦 INSTALLATION")
print("-" * 60)
print("To install all dependencies, run:")
print("  pip install -r requirements.txt")
print("\nDependencies include:")
print("  - selenium (for web scraping)")
print("  - fastapi (for REST API)")
print("  - uvicorn (for API server)")
print("  - pydantic (for data validation)")
print("  - pandas (for data management)")

print("\n🚀 USAGE OPTIONS")
print("-" * 60)

print("\n1. CLI MODE (Command Line Interface):")
print("   New CLI (recommended):")
print("     python cli.py")
print("\n   Legacy CLI (backward compatible):")
print("     python main.py")

print("\n2. API MODE (REST API Server):")
print("   Start the server:")
print("     python -m uvicorn api.app:app --reload")
print("\n   Or:")
print("     python api/app.py")
print("\n   Then access:")
print("     - API Docs (Swagger): http://localhost:8000/docs")
print("     - Alternative Docs: http://localhost:8000/redoc")
print("     - Health Check: http://localhost:8000/health")

print("\n📚 DOCUMENTATION")
print("-" * 60)
print("  - README.md - Complete guide for CLI and API")
print("  - API_EXAMPLES.md - Detailed API usage examples")

print("\n🔑 API AUTHENTICATION")
print("-" * 60)
print("  Default API Key: dev-api-key-change-in-production")
print("  ⚠️  IMPORTANT: Change this in production!")
print("  Configure in: config/api_config.py")

print("\n🏗️  PROJECT STRUCTURE")
print("-" * 60)
print("  api/          - REST API endpoints and models")
print("  core/         - Shared business logic")
print("    services/   - Service layer (ScraperService, etc.)")
print("  actions/      - LinkedIn action implementations")
print("  scraper/      - Scraping logic")
print("  auth/         - Authentication handlers")
print("  utils/        - Utility functions")
print("  data/         - Output CSV files")

print("\n✨ FEATURES")
print("-" * 60)
print("  ✓ Group member scraping")
print("  ✓ Profile search & scraping")
print("  ✓ Google-based LinkedIn scraping")
print("  ✓ Single connection requests")
print("  ✓ Mass connection requests")
print("  ✓ Group messaging")
print("  ✓ CLI interface (original + new)")
print("  ✓ REST API with Swagger docs")
print("  ✓ Background job processing")
print("  ✓ API authentication")

print("\n📝 EXAMPLE API REQUEST")
print("-" * 60)
print('''
curl -X POST "http://localhost:8000/api/v1/scrape/group" \\
  -H "X-API-Key: dev-api-key-change-in-production" \\
  -H "Content-Type: application/json" \\
  -d '{
    "group_url": "https://www.linkedin.com/groups/12345/",
    "max_members": 100,
    "scraping_mode": "smart"
  }'
''')

print("\n🎯 QUICK TEST")
print("-" * 60)
print("To test the API is working:")
print("  1. Install dependencies: pip install -r requirements.txt")
print("  2. Start server: python -m uvicorn api.app:app --reload")
print("  3. Visit: http://localhost:8000/health")
print("  4. Explore: http://localhost:8000/docs")

print("\n" + "="*60)
print("Ready to use! Check README.md for detailed instructions.")
print("="*60 + "\n")
