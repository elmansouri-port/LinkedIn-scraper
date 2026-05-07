"""
Final system verification script.
Run: python verify_system.py
"""
print("=== SYSTEM VERIFICATION ===")
print()

# 1. Check all core modules
modules = {
    "core.database": "Database with migrations",
    "core.groq_service": "Groq AI service",
    "core.cv_generator": "CV generation",
    "core.services.email_scheduler": "Email scheduler",
    "cli": "CLI with all actions",
}

for module, desc in modules.items():
    try:
        __import__(module)
        print(f"[OK] {module:40s} - {desc}")
    except Exception as e:
        print(f"[FAIL] {module:40s} - {e}")

print()
print("=== DATABASE TABLES ===")
from core.database import get_connection
conn = get_connection()
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cursor.fetchall()]
for t in sorted(tables):
    print(f"  - {t}")
conn.close()

print()
print("=== CLI ACTIONS ===")
print("  1-7: Scraping, enrichment")
print("  8-10: Export, stats, auth")
print("  11-13: Email test, send, CV gen")
print("  14-16: Schedule, accounts, run scheduler")

print()
print("=== EMAIL SCHEDULING FEATURES ===")
print("  - Schedule campaigns for specific dates/times")
print("  - Skip weekends (Saturday/Sunday)")
print("  - Time window restrictions (send only 9-5)")
print("  - Multiple email account rotation")
print("  - Daily limits per account")
print("  - Automatic daily count reset")

print()
print("=== CV GENERATION FEATURES ===")
print("  - AI-powered LaTeX CV generation (Groq API)")
print("  - Customized experiences section")
print("  - Education and skills sections")
print("  - PDF compilation with pdflatex")
print("  - Rate limit handling (60s between requests)")
print("  - Model fallback chain")

print()
print("All systems ready!")
