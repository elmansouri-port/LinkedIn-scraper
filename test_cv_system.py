"""
Test script to verify the CV generation system works.
Run: python test_cv_system.py
"""
import os
import sys
from dotenv import load_dotenv

# Load environment
load_dotenv()

print("Testing CV Generation System")
print("=" * 50)

# Test 1: Check GroqService
print("\n1. Testing GroqService...")
try:
    from core.groq_service import GroqService
    groq = GroqService()
    print("[OK] GroqService initialized")
    print(f"   Model: {groq.model}")
except Exception as e:
    print(f"[FAIL] GroqService failed: {e}")
    sys.exit(1)

# Test 2: Check database migrations
print("\n2. Testing database migrations...")
try:
    from core.database import get_connection, init_db
    init_db()
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Check enriched_profiles
    cursor.execute("PRAGMA table_info(enriched_profiles)")
    columns = [row[1] for row in cursor.fetchall()]
    assert "custom_cv_path" in columns, "custom_cv_path missing in enriched_profiles"
    print("[OK] enriched_profiles.custom_cv_path exists")
    
    # Check email_sends
    cursor.execute("PRAGMA table_info(email_sends)")
    columns = [row[1] for row in cursor.fetchall()]
    assert "custom_cv_path" in columns, "custom_cv_path missing in email_sends"
    print("[OK] email_sends.custom_cv_path exists")
    
    conn.close()
except Exception as e:
    print(f"[FAIL] Database migration failed: {e}")
    sys.exit(1)

# Test 3: Check template exists
print("\n3. Testing template...")
template_path = "templates/base_cv.tex"
if os.path.exists(template_path):
    print(f"[OK] Template exists: {template_path}")
else:
    print(f"[FAIL] Template not found: {template_path}")
    sys.exit(1)

# Test 4: Check CV generator
print("\n4. Testing CV generator...")
try:
    from core.cv_generator import generate_experiences_section, generate_education_section
    print("[OK] CV generator functions imported")
except Exception as e:
    print(f"[FAIL] CV generator import failed: {e}")
    sys.exit(1)

# Test 5: Test LaTeX generation (simple test)
print("\n5. Testing LaTeX generation...")
try:
    # Create a mock profile
    mock_profile = {
        "full_name": "John Doe",
        "current_company": "Acme Corp",
        "current_job_title": "Software Engineer",
        "about_text": "Experienced software engineer",
        "experiences": [
            {
                "title": "Software Engineer",
                "company": "Acme Corp",
                "dates": "2020-2023",
                "description": "Built scalable web applications"
            }
        ],
        "education": [
            {
                "school": "MIT",
                "degree": "BS",
                "field": "Computer Science"
            }
        ]
    }
    
    # Test experience generation
    experiences_latex = generate_experiences_section(mock_profile, groq)
    if "\\begin{itemize}" in experiences_latex:
        print("[OK] Experiences LaTeX generated")
    else:
        print("[FAIL] Experiences LaTeX invalid")
    
    # Test education generation
    education_latex = generate_education_section(mock_profile["education"])
    if "\\begin{itemize}" in education_latex:
        print("[OK] Education LaTeX generated")
    else:
        print("[FAIL] Education LaTeX invalid")
        
except Exception as e:
    print(f"[FAIL] LaTeX generation failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 50)
print("Tests completed!")
print("\nNote: Full CV generation requires a profile in the database.")
print("To test full flow:")
print("  1. Add a profile to enriched_profiles table")
print("  2. Run: python -c \"from core.cv_generator import generate_cv_for_profile; generate_cv_for_profile('profile_url', groq)\"")
