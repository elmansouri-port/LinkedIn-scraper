"""
Export Manager — clean, user-friendly data exports from the unified database.

Provides 3 export presets:
  1. Search Profiles      — raw profiles from Google scraper
  2. Enriched Profiles    — visited profiles with full details
  3. Enriched + Emails    — enriched profiles with generated emails

Exports to CSV or Excel with human-readable column names and flattened data.
"""
import csv
import json
import os
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


# ===================================================================
# DATA TRANSFORMERS
# ===================================================================

def _format_experiences(raw: Optional[str]) -> str:
    """Convert experiences JSON array to readable string."""
    if not raw:
        return ""
    try:
        data = json.loads(raw)
        if not isinstance(data, list):
            return str(data)
        parts = []
        for exp in data:
            title = exp.get("title", "")
            company = exp.get("company", "")
            dates = exp.get("dates", "")
            line = f"{title} at {company}".strip()
            if dates:
                line += f" ({dates})"
            if line:
                parts.append(line)
        return " | ".join(parts)
    except (json.JSONDecodeError, TypeError):
        return str(raw)


def _format_education(raw: Optional[str]) -> str:
    """Convert education JSON array to readable string."""
    if not raw:
        return ""
    try:
        data = json.loads(raw)
        if not isinstance(data, list):
            return str(data)
        parts = []
        for edu in data:
            school = edu.get("school", "")
            degree = edu.get("degree", "")
            field = edu.get("field", "")
            dates = edu.get("dates", "")
            line = f"{school}".strip()
            detail = f"{degree} — {field}".strip(" —")
            if detail:
                line += f" ({detail}"
                if dates:
                    line += f", {dates}"
                line += ")"
            if line:
                parts.append(line)
        return " | ".join(parts)
    except (json.JSONDecodeError, TypeError):
        return str(raw)


def _format_email_variants(raw: Optional[str]) -> str:
    """Convert email variants JSON array to semicolon-separated string."""
    if not raw:
        return ""
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return "; ".join(data)
        return str(data)
    except (json.JSONDecodeError, TypeError):
        return str(raw)


# ===================================================================
# EXPORT PRESETS
# ===================================================================

EXPORT_PRESETS = {
    "search": {
        "label": "Search Profiles",
        "description": "Profiles found via Google search — name, title, company, location",
        "query": """
            SELECT profile_url, name, title, company, location,
                   search_keyword, scraped_at
            FROM search_profiles ORDER BY id
        """,
        "columns": {
            "profile_url": "Profile URL",
            "name": "Name",
            "title": "Title",
            "company": "Company",
            "location": "Location",
            "search_keyword": "Search Keyword",
            "scraped_at": "Scraped At",
        },
        "transformers": {},
    },
    "enriched": {
        "label": "Enriched Profiles (Basic)",
        "description": "Profiles with name, about, experience, and education details",
        "query": """
            SELECT profile_url, first_name, last_name, full_name,
                   about_text, experiences, education,
                   current_company, current_job_title,
                   enrichment_status, enriched_at
            FROM enriched_profiles WHERE enrichment_status = 'success'
            ORDER BY id
        """,
        "columns": {
            "profile_url": "Profile URL",
            "first_name": "First Name",
            "last_name": "Last Name",
            "full_name": "Full Name",
            "about_text": "About",
            "current_company": "Current Company",
            "current_job_title": "Current Job Title",
            "experiences": "All Experiences",
            "education": "Education",
            "enriched_at": "Enriched At",
        },
        "transformers": {
            "experiences": _format_experiences,
            "education": _format_education,
        },
    },
    "enriched_emails": {
        "label": "Enriched Profiles + Emails (Full)",
        "description": "Complete profiles with generated email addresses",
        "query": """
            SELECT profile_url, first_name, last_name, full_name,
                   about_text, experiences, education,
                   current_company, current_job_title,
                   current_company_domain, generated_email, all_email_variants,
                   enriched_at
            FROM enriched_profiles WHERE enrichment_status = 'success'
            ORDER BY id
        """,
        "columns": {
            "profile_url": "Profile URL",
            "first_name": "First Name",
            "last_name": "Last Name",
            "full_name": "Full Name",
            "about_text": "About",
            "current_company": "Current Company",
            "current_job_title": "Current Job Title",
            "current_company_domain": "Company Website",
            "generated_email": "Primary Email",
            "all_email_variants": "All Email Variants",
            "experiences": "All Experiences",
            "education": "Education",
            "enriched_at": "Enriched At",
        },
        "transformers": {
            "experiences": _format_experiences,
            "education": _format_education,
            "all_email_variants": _format_email_variants,
        },
    },
}


# ===================================================================
# EXPORT FUNCTIONS
# ===================================================================

def _get_rows(db_path: str, query: str) -> List[Dict]:
    """Execute query and return rows as list of dicts."""
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute(query)
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def _transform_row(row: Dict, preset: Dict) -> Dict:
    """Apply column renaming and data transformers to a row."""
    columns = preset["columns"]
    transformers = preset.get("transformers", {})
    result = {}

    for col_key, display_name in columns.items():
        raw_value = row.get(col_key, "")
        if col_key in transformers:
            value = transformers[col_key](raw_value)
        elif isinstance(raw_value, str) and raw_value.startswith(("[", "{")):
            try:
                parsed = json.loads(raw_value)
                if isinstance(parsed, list):
                    value = "; ".join(str(x) for x in parsed)
                else:
                    value = str(parsed)
            except (json.JSONDecodeError, TypeError):
                value = raw_value
        else:
            value = raw_value
        result[display_name] = value if value is not None else ""

    return result


def export_preset_to_csv(preset_key: str, output_path: str, db_path: str = None) -> bool:
    """Export a preset to CSV."""
    from core.database import DB_PATH

    preset = EXPORT_PRESETS.get(preset_key)
    if not preset:
        logger.error("Unknown export preset: %s", preset_key)
        return False

    db = db_path or DB_PATH
    if not os.path.exists(db):
        logger.error("Database not found: %s", db)
        return False

    rows = _get_rows(db, preset["query"])
    if not rows:
        logger.warning("No data to export for preset: %s", preset_key)
        return False

    transformed = [_transform_row(row, preset) for row in rows]
    fieldnames = list(preset["columns"].values())

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(transformed)

    logger.info("Exported %d rows to %s", len(transformed), output_path)
    return True


def export_preset_to_excel(preset_key: str, output_path: str, db_path: str = None) -> bool:
    """Export a preset to Excel (.xlsx) with auto-sized columns."""
    try:
        import openpyxl
    except ImportError:
        logger.error("openpyxl not installed. Run: pip install openpyxl")
        return False

    from core.database import DB_PATH

    preset = EXPORT_PRESETS.get(preset_key)
    if not preset:
        logger.error("Unknown export preset: %s", preset_key)
        return False

    db = db_path or DB_PATH
    if not os.path.exists(db):
        logger.error("Database not found: %s", db)
        return False

    rows = _get_rows(db, preset["query"])
    if not rows:
        logger.warning("No data to export for preset: %s", preset_key)
        return False

    transformed = [_transform_row(row, preset) for row in rows]
    fieldnames = list(preset["columns"].values())

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = preset["label"][:31]

    # Header
    ws.append(fieldnames)

    # Data rows
    for row in transformed:
        ws.append([row.get(col, "") for col in fieldnames])

    # Auto-size columns
    for col_cells in ws.columns:
        max_len = 0
        col_letter = col_cells[0].column_letter
        for cell in col_cells:
            if cell.value:
                max_len = max(max_len, min(len(str(cell.value)), 50))
        ws.column_dimensions[col_letter].width = max_len + 2

    wb.save(output_path)
    logger.info("Exported %d rows to %s", len(transformed), output_path)
    return True


# ===================================================================
# UTILITY FUNCTIONS
# ===================================================================

def get_preset_info() -> List[Dict]:
    """Get info about all export presets."""
    return [
        {"key": key, "label": p["label"], "description": p["description"]}
        for key, p in EXPORT_PRESETS.items()
    ]


def get_row_count(preset_key: str, db_path: str = None) -> int:
    """Get number of rows for a preset."""
    from core.database import DB_PATH
    import sqlite3

    preset = EXPORT_PRESETS.get(preset_key)
    if not preset:
        return 0

    db = db_path or DB_PATH
    if not os.path.exists(db):
        return 0

    conn = sqlite3.connect(db)
    try:
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM ({preset['query']})")
        return cursor.fetchone()[0]
    except Exception:
        return 0
    finally:
        conn.close()
