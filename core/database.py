"""
Unified SQLite Database Manager
Single database file for all scraping data: profiles, enriched profiles, connections, messages.
"""
import sqlite3
import os
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from config.scraper_config import DB_DIR

logger = logging.getLogger(__name__)

DB_NAME = "linkedin_scraper.db"
DB_PATH = os.path.join(DB_DIR, DB_NAME)


def get_connection(db_path: str = None) -> sqlite3.Connection:
    """Get a database connection with row factory and WAL mode."""
    path = db_path or DB_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(db_path: str = None):
    """Create all tables if they don't exist."""
    conn = get_connection(db_path)
    cursor = conn.cursor()

    # ------------------------------------------------------------------
    # Google-scraper profiles (raw search results)
    # ------------------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS search_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_url TEXT UNIQUE NOT NULL,
            name TEXT,
            title TEXT,
            company TEXT,
            location TEXT,
            description TEXT,
            search_keyword TEXT,
            all_keywords TEXT,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_search_url ON search_profiles(profile_url)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_search_keyword ON search_profiles(search_keyword)"
    )

    # ------------------------------------------------------------------
    # Enriched profiles (visited + email generated)
    # ------------------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS enriched_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_url TEXT UNIQUE NOT NULL,
            first_name TEXT,
            last_name TEXT,
            full_name TEXT,
            about_text TEXT,
            experiences TEXT,
            education TEXT,
            current_company TEXT,
            current_job_title TEXT,
            current_company_domain TEXT,
            generated_email TEXT,
            all_email_variants TEXT,
            enrichment_status TEXT DEFAULT 'pending',
            error_message TEXT,
            enriched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_enriched_url ON enriched_profiles(profile_url)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_enriched_company ON enriched_profiles(current_company)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_enriched_status ON enriched_profiles(enrichment_status)"
    )

    # Add experiences column if it doesn't exist (migration for existing databases)
    try:
        cursor.execute("ALTER TABLE enriched_profiles ADD COLUMN experiences TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists

    # Add education column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE enriched_profiles ADD COLUMN education TEXT")
    except sqlite3.OperationalError:
        pass

    # Add email verification columns if they don't exist
    try:
        cursor.execute("ALTER TABLE enriched_profiles ADD COLUMN email_verified BOOLEAN DEFAULT NULL")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE enriched_profiles ADD COLUMN email_verified_at TIMESTAMP NULL")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE enriched_profiles ADD COLUMN email_verification_method TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE enriched_profiles ADD COLUMN email_verification_result TEXT")
    except sqlite3.OperationalError:
        pass

    # Add custom CV path column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE enriched_profiles ADD COLUMN custom_cv_path TEXT")
    except sqlite3.OperationalError:
        pass

        # ------------------------------------------------------------------
    # EMAIL CAMPAIGNS
    # ------------------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS email_campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            subject TEXT NOT NULL,
            body_template TEXT NOT NULL,
            body_template_html TEXT,
            cv_path TEXT,
            cover_letter_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'draft',
            total_sent INTEGER DEFAULT 0,
            total_failed INTEGER DEFAULT 0
        )
    """)
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_campaign_status ON email_campaigns(status)"
    )

    # Add CV and cover letter columns if they don't exist
    try:
        cursor.execute("ALTER TABLE email_campaigns ADD COLUMN cv_path TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE email_campaigns ADD COLUMN cover_letter_path TEXT")
    except sqlite3.OperationalError:
        pass

    # ------------------------------------------------------------------
    # EMAIL SENDS (track individual email sends)
    # ------------------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS email_sends (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id INTEGER NOT NULL,
            profile_url TEXT NOT NULL,
            email TEXT NOT NULL,
            first_name TEXT,
            last_name TEXT,
            company TEXT,
            subject TEXT,
            body_text TEXT,
            body_html TEXT,
            status TEXT DEFAULT 'pending',
            error_message TEXT,
            sent_at TIMESTAMP NULL,
            opened_at TIMESTAMP NULL,
            clicked_at TIMESTAMP NULL,
            custom_cv_path TEXT,
            FOREIGN KEY (campaign_id) REFERENCES email_campaigns(id)
        )
    """)
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_send_campaign ON email_sends(campaign_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_send_status ON email_sends(status)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_send_email ON email_sends(email)"
    )

    # Add custom_cv_path column to email_sends if it doesn't exist
    try:
        cursor.execute("ALTER TABLE email_sends ADD COLUMN custom_cv_path TEXT")
    except sqlite3.OperationalError:
        pass

    # ------------------------------------------------------------------
    # Group-scraper members
    # ------------------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS group_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_url TEXT UNIQUE NOT NULL,
            name TEXT,
            title TEXT,
            location TEXT,
            group_name TEXT,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_group_url ON group_members(profile_url)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_group_name ON group_members(group_name)"
    )

    # ------------------------------------------------------------------
    # Connection requests
    # ------------------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS connections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_url TEXT UNIQUE NOT NULL,
            name TEXT,
            message_sent TEXT,
            status TEXT DEFAULT 'pending',
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_conn_url ON connections(profile_url)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_conn_status ON connections(status)"
    )

    # ------------------------------------------------------------------
    # Messages
    # ------------------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_url TEXT NOT NULL,
            name TEXT,
            message_text TEXT,
            status TEXT DEFAULT 'pending',
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_msg_url ON messages(profile_url)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_msg_status ON messages(status)"
    )

    # ------------------------------------------------------------------
    # EMAIL ACCOUNTS (for rotating sending accounts)
    # ------------------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS email_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            smtp_preset TEXT NOT NULL,
            username TEXT NOT NULL,
            password TEXT NOT NULL,
            daily_limit INTEGER DEFAULT 50,
            daily_sent_today INTEGER DEFAULT 0,
            last_used_date TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_email_accounts_active ON email_accounts(is_active)"
    )

    # Add scheduling fields to email_campaigns if they don't exist
    try:
        cursor.execute("ALTER TABLE email_campaigns ADD COLUMN scheduled_at TIMESTAMP NULL")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE email_campaigns ADD COLUMN send_days TEXT DEFAULT '0,1,2,3,4'")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE email_campaigns ADD COLUMN send_time_start TEXT DEFAULT '09:00'")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE email_campaigns ADD COLUMN send_time_end TEXT DEFAULT '17:00'")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE email_campaigns ADD COLUMN emails_per_day INTEGER DEFAULT 20")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE email_campaigns ADD COLUMN use_account_rotation BOOLEAN DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()
    logger.info("Database initialized: %s", DB_PATH)


# ===================================================================
# SEARCH PROFILES (from Google scraper)
# ===================================================================

def save_search_profile(profile_url: str, name: str = "", title: str = "",
                        company: str = "", location: str = "", description: str = "",
                        search_keyword: str = "", all_keywords: str = "",
                        db_path: str = None) -> bool:
    """Insert or ignore a search profile. Returns True if inserted."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT OR IGNORE INTO search_profiles
                (profile_url, name, title, company, location, description, search_keyword, all_keywords)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (profile_url, name, title, company, location, description, search_keyword, all_keywords))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        logger.error("Error saving search profile: %s", e)
        return False
    finally:
        conn.close()


def save_search_profiles_batch(profiles: list, db_path: str = None) -> tuple:
    """Batch insert search profiles. Returns (saved, duplicates)."""
    saved = 0
    duplicates = 0
    conn = get_connection(db_path)
    cursor = conn.cursor()
    try:
        for p in profiles:
            cursor.execute("""
                INSERT OR IGNORE INTO search_profiles
                    (profile_url, name, title, company, location, description, search_keyword, all_keywords)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                p.get("profile_url", ""),
                p.get("name", ""),
                p.get("title", ""),
                p.get("company", ""),
                p.get("location", ""),
                p.get("description", ""),
                p.get("search_keyword", ""),
                p.get("all_keywords", ""),
            ))
            if cursor.rowcount > 0:
                saved += 1
            else:
                duplicates += 1
        conn.commit()
    except Exception as e:
        logger.error("Error batch saving search profiles: %s", e)
    finally:
        conn.close()
    return saved, duplicates


def get_all_search_profiles(db_path: str = None) -> list:
    """Get all search profiles."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM search_profiles ORDER BY id")
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_search_profiles_not_enriched(db_path: str = None) -> list:
    """Get search profiles that haven't been enriched yet."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT sp.* FROM search_profiles sp
            LEFT JOIN enriched_profiles ep ON sp.profile_url = ep.profile_url
            WHERE ep.profile_url IS NULL
            ORDER BY sp.id
        """)
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_search_profile_urls(db_path: str = None) -> set:
    """Get all unique profile URLs from search_profiles."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT profile_url FROM search_profiles")
        return {row[0] for row in cursor.fetchall()}
    finally:
        conn.close()


# ===================================================================
# ENRICHED PROFILES
# ===================================================================

def save_enriched_profile(profile_url: str, first_name: str = "", last_name: str = "",
                          full_name: str = "", about_text: str = "",
                          experiences: list = None, education: list = None,
                          current_company: str = "", current_job_title: str = "",
                          current_company_domain: str = "",
                          generated_email: str = "", all_email_variants: list = None,
                          status: str = "success", error_message: str = "",
                          db_path: str = None) -> bool:
    """Insert or update an enriched profile."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO enriched_profiles
                (profile_url, first_name, last_name, full_name, about_text, experiences, education,
                 current_company, current_job_title, current_company_domain,
                 generated_email, all_email_variants, enrichment_status, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(profile_url) DO UPDATE SET
                first_name=excluded.first_name,
                last_name=excluded.last_name,
                full_name=excluded.full_name,
                about_text=excluded.about_text,
                experiences=excluded.experiences,
                education=excluded.education,
                current_company=excluded.current_company,
                current_job_title=excluded.current_job_title,
                current_company_domain=excluded.current_company_domain,
                generated_email=excluded.generated_email,
                all_email_variants=excluded.all_email_variants,
                enrichment_status=excluded.enrichment_status,
                error_message=excluded.error_message,
                enriched_at=CURRENT_TIMESTAMP
        """, (
            profile_url, first_name, last_name, full_name, about_text,
            json.dumps(experiences) if experiences else None,
            json.dumps(education) if education else None,
            current_company, current_job_title, current_company_domain,
            generated_email,
            json.dumps(all_email_variants) if all_email_variants else None,
            status, error_message,
        ))
        conn.commit()
        return True
    except Exception as e:
        logger.error("Error saving enriched profile: %s", e)
        return False
    finally:
        conn.close()


def get_all_enriched_profiles(db_path: str = None) -> list:
    """Get all enriched profiles."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM enriched_profiles ORDER BY id")
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_enriched_profile_urls(db_path: str = None) -> set:
    """Get all enriched profile URLs (for resume)."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT profile_url FROM enriched_profiles WHERE enrichment_status='success'")
        return {row[0] for row in cursor.fetchall()}
    finally:
        conn.close()


def update_profile_cv(profile_url: str, cv_path: str, db_path: str = None) -> bool:
    """Update the custom_cv_path for an enriched profile."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE enriched_profiles
            SET custom_cv_path = ?
            WHERE profile_url = ?
        """, (cv_path, profile_url))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        logger.error("Error updating profile CV path: %s", e)
        return False
    finally:
        conn.close()


def get_profiles_without_cv(db_path: str = None) -> list:
    """Get enriched profiles that don't have a custom CV yet."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT * FROM enriched_profiles
            WHERE enrichment_status='success'
            AND (custom_cv_path IS NULL OR custom_cv_path = '')
        """)
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


# ===================================================================
# GROUP MEMBERS
# ===================================================================

def save_group_member(profile_url: str, name: str = "", title: str = "",
                      location: str = "", group_name: str = "",
                      db_path: str = None) -> bool:
    """Insert or ignore a group member."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT OR IGNORE INTO group_members (profile_url, name, title, location, group_name)
            VALUES (?, ?, ?, ?, ?)
        """, (profile_url, name, title, location, group_name))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        logger.error("Error saving group member: %s", e)
        return False
    finally:
        conn.close()


def get_all_group_members(db_path: str = None) -> list:
    """Get all group members."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM group_members ORDER BY id")
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


# ===================================================================
# CONNECTIONS
# ===================================================================

def save_connection(profile_url: str, name: str = "", message_sent: str = "",
                    status: str = "pending", db_path: str = None) -> bool:
    """Insert or ignore a connection record."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT OR IGNORE INTO connections (profile_url, name, message_sent, status)
            VALUES (?, ?, ?, ?)
        """, (profile_url, name, message_sent, status))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        logger.error("Error saving connection: %s", e)
        return False
    finally:
        conn.close()


def get_all_connections(db_path: str = None) -> list:
    """Get all connections."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM connections ORDER BY id")
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


# ===================================================================
# MESSAGES
# ===================================================================

def save_message(profile_url: str, name: str = "", message_text: str = "",
                 status: str = "pending", db_path: str = None) -> bool:
    """Insert a message record."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO messages (profile_url, name, message_text, status)
            VALUES (?, ?, ?, ?)
        """, (profile_url, name, message_text, status))
        conn.commit()
        return True
    except Exception as e:
        logger.error("Error saving message: %s", e)
        return False
    finally:
        conn.close()


def get_all_messages(db_path: str = None) -> list:
    """Get all messages."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM messages ORDER BY id")
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


# ===================================================================
# EMAIL CAMPAIGNS
# ===================================================================

def create_email_campaign(name: str, subject: str, body_template: str,
                         body_template_html: str = None, cv_path: str = None,
                         cover_letter_path: str = None, db_path: str = None) -> int:
    """Create a new email campaign. Returns campaign ID."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO email_campaigns
                (name, subject, body_template, body_template_html, cv_path, cover_letter_path)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name, subject, body_template, body_template_html, cv_path, cover_letter_path))
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        logger.error("Error creating email campaign: %s", e)
        return None
    finally:
        conn.close()


def get_email_campaign(campaign_id: int, db_path: str = None) -> dict:
    """Get a single email campaign by ID."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM email_campaigns WHERE id = ?", (campaign_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_all_email_campaigns(db_path: str = None) -> list:
    """Get all email campaigns."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM email_campaigns ORDER BY id DESC")
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def update_campaign_stats(campaign_id: int, sent: int = 0, failed: int = 0,
                          db_path: str = None) -> bool:
    """Update campaign send statistics."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE email_campaigns
            SET total_sent = total_sent + ?, total_failed = total_failed + ?
            WHERE id = ?
        """, (sent, failed, campaign_id))
        conn.commit()
        return True
    except Exception as e:
        logger.error("Error updating campaign stats: %s", e)
        return False
    finally:
        conn.close()


def update_campaign_status(campaign_id: int, status: str, db_path: str = None) -> bool:
    """Update campaign status."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE email_campaigns SET status = ? WHERE id = ?", (status, campaign_id))
        conn.commit()
        return True
    except Exception as e:
        logger.error("Error updating campaign status: %s", e)
        return False
    finally:
        conn.close()


# ===================================================================
# EMAIL SENDS
# ===================================================================

def save_email_send(campaign_id: int, profile_url: str, email: str,
                    first_name: str = "", last_name: str = "", company: str = "",
                    subject: str = "", body_text: str = "", body_html: str = "",
                    custom_cv_path: str = "", db_path: str = None) -> int:
    """Save an email send record. Returns send ID."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO email_sends
                (campaign_id, profile_url, email, first_name, last_name, company,
                 subject, body_text, body_html, custom_cv_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (campaign_id, profile_url, email, first_name, last_name, company,
               subject, body_text, body_html, custom_cv_path))
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        logger.error("Error saving email send: %s", e)
        return None
    finally:
        conn.close()


def update_email_send_status(send_id: int, status: str, error_message: str = None,
                             db_path: str = None) -> bool:
    """Update email send status."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    try:
        if status == 'sent':
            cursor.execute("""
                UPDATE email_sends SET status = ?, sent_at = CURRENT_TIMESTAMP, error_message = ?
                WHERE id = ?
            """, (status, error_message, send_id))
        else:
            cursor.execute("""
                UPDATE email_sends SET status = ?, error_message = ?
                WHERE id = ?
            """, (status, error_message, send_id))
        conn.commit()
        return True
    except Exception as e:
        logger.error("Error updating email send status: %s", e)
        return False
    finally:
        conn.close()


def get_campaign_email_sends(campaign_id: int, status: str = None,
                               db_path: str = None) -> list:
    """Get all email sends for a campaign, optionally filtered by status."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    try:
        if status:
            cursor.execute("""
                SELECT * FROM email_sends
                WHERE campaign_id = ? AND status = ?
                ORDER BY id
            """, (campaign_id, status))
        else:
            cursor.execute("""
                SELECT * FROM email_sends
                WHERE campaign_id = ?
                ORDER BY id
            """, (campaign_id,))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_email_send_stats(campaign_id: int = None, db_path: str = None) -> dict:
    """Get email send statistics, optionally for a specific campaign."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    try:
        if campaign_id:
            cursor.execute("""
                SELECT status, COUNT(*) as count
                FROM email_sends
                WHERE campaign_id = ?
                GROUP BY status
            """, (campaign_id,))
        else:
            cursor.execute("""
                SELECT status, COUNT(*) as count
                FROM email_sends
                GROUP BY status
            """)
        return {row[0]: row[1] for row in cursor.fetchall()}
    finally:
        conn.close()


# ===================================================================
# UNIFIED PROFILES VIEW
# ===================================================================

def get_unified_profiles(limit: int = 50, offset: int = 0,
                          search: str = "", status_filter: str = "",
                          db_path: str = None) -> dict:
    """Paginated unified view: search_profiles LEFT JOIN enriched + connections."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    try:
        conditions = []
        params = []
        if search:
            conditions.append(
                "(sp.name LIKE ? OR sp.title LIKE ? OR sp.company LIKE ? OR sp.location LIKE ?"
                " OR ep.full_name LIKE ? OR ep.current_company LIKE ?)"
            )
            s = f"%{search}%"
            params.extend([s, s, s, s, s, s])
        if status_filter == "enriched":
            conditions.append("ep.profile_url IS NOT NULL AND ep.enrichment_status = 'success'")
        elif status_filter == "not_enriched":
            conditions.append("ep.profile_url IS NULL")
        elif status_filter == "has_email":
            conditions.append("ep.generated_email IS NOT NULL AND ep.generated_email != ''")
        elif status_filter == "connected":
            conditions.append("c.profile_url IS NOT NULL")

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        cursor.execute(f"""
            SELECT COUNT(*) FROM search_profiles sp
            LEFT JOIN enriched_profiles ep ON sp.profile_url = ep.profile_url
            LEFT JOIN connections c ON sp.profile_url = c.profile_url
            {where}
        """, params)
        total = cursor.fetchone()[0]

        cursor.execute(f"""
            SELECT
                sp.id, sp.profile_url, sp.name, sp.title, sp.company, sp.location,
                sp.description, sp.search_keyword, sp.scraped_at,
                ep.full_name, ep.first_name, ep.last_name,
                ep.current_job_title, ep.current_company, ep.current_company_domain,
                ep.generated_email, ep.all_email_variants,
                ep.enrichment_status, ep.enriched_at,
                ep.about_text, ep.experiences, ep.education,
                c.status AS connection_status, c.sent_at AS connection_sent_at
            FROM search_profiles sp
            LEFT JOIN enriched_profiles ep ON sp.profile_url = ep.profile_url
            LEFT JOIN connections c ON sp.profile_url = c.profile_url
            {where}
            ORDER BY sp.id DESC
            LIMIT ? OFFSET ?
        """, params + [limit, offset])

        rows = [dict(row) for row in cursor.fetchall()]
        return {"profiles": rows, "total": total}
    finally:
        conn.close()


def get_profile_by_id(profile_id: int, db_path: str = None) -> dict:
    """Get a single unified profile by search_profiles.id."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT
                sp.id, sp.profile_url, sp.name, sp.title, sp.company, sp.location,
                sp.description, sp.search_keyword, sp.scraped_at,
                ep.full_name, ep.first_name, ep.last_name,
                ep.current_job_title, ep.current_company, ep.current_company_domain,
                ep.generated_email, ep.all_email_variants,
                ep.enrichment_status, ep.enriched_at,
                ep.about_text, ep.experiences, ep.education,
                c.status AS connection_status, c.sent_at AS connection_sent_at
            FROM search_profiles sp
            LEFT JOIN enriched_profiles ep ON sp.profile_url = ep.profile_url
            LEFT JOIN connections c ON sp.profile_url = c.profile_url
            WHERE sp.id = ?
        """, (profile_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def delete_profile_by_id(profile_id: int, db_path: str = None) -> bool:
    """Delete a profile and its enriched data by search_profiles.id."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT profile_url FROM search_profiles WHERE id = ?", (profile_id,))
        row = cursor.fetchone()
        if not row:
            return False
        url = row[0]
        cursor.execute("DELETE FROM enriched_profiles WHERE profile_url = ?", (url,))
        cursor.execute("DELETE FROM search_profiles WHERE id = ?", (profile_id,))
        conn.commit()
        return True
    except Exception as e:
        logger.error("Error deleting profile %s: %s", profile_id, e)
        return False
    finally:
        conn.close()


# ===================================================================
# EXPORT (delegated to export_manager)
# ===================================================================
# See core/export_manager.py for user-friendly export presets:
#   - export_preset_to_csv()
#   - export_preset_to_excel()
#   - get_preset_info()
#   - get_row_count()
# ===================================================================


def get_stats(db_path: str = None) -> dict:
    """Get row counts for all tables."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    tables = ["search_profiles", "enriched_profiles", "group_members",
              "connections", "messages", "email_campaigns", "email_sends"]
    stats = {}
    try:
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            stats[table] = cursor.fetchone()[0]
    except sqlite3.OperationalError:
        pass
    finally:
        conn.close()
    return stats


# ===================================================================
# EMAIL ACCOUNTS (for rotating sending accounts)
# ===================================================================

def add_email_account(email: str, smtp_preset: str, username: str, password: str,
                     daily_limit: int = 50, db_path: str = None) -> int:
    """Add a new email account for sending. Returns account ID."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT OR REPLACE INTO email_accounts
                (email, smtp_preset, username, password, daily_limit)
            VALUES (?, ?, ?, ?, ?)
        """, (email, smtp_preset, username, password, daily_limit))
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        logger.error("Error adding email account: %s", e)
        return None
    finally:
        conn.close()


def get_email_accounts(active_only: bool = True, db_path: str = None) -> list:
    """Get all email accounts, optionally filtering by active status."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    try:
        if active_only:
            cursor.execute("SELECT * FROM email_accounts WHERE is_active = 1 ORDER BY last_used_date ASC")
        else:
            cursor.execute("SELECT * FROM email_accounts ORDER BY last_used_date ASC")
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_next_available_account(db_path: str = None) -> dict:
    """Get the next available email account based on daily limits."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        cursor.execute("""
            SELECT * FROM email_accounts
            WHERE is_active = 1
            AND (last_used_date IS NULL OR last_used_date != ?)
            ORDER BY last_used_date ASC NULLS FIRST
        """, (today,))
        account = cursor.fetchone()
        if account:
            return dict(account)

        # If all used today, find one with least sent
        cursor.execute("""
            SELECT * FROM email_accounts
            WHERE is_active = 1 AND daily_sent_today < daily_limit
            ORDER BY daily_sent_today ASC
        """)
        account = cursor.fetchone()
        return dict(account) if account else None
    finally:
        conn.close()


def update_account_usage(account_id: int, db_path: str = None) -> bool:
    """Update account usage after sending an email."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        cursor.execute("""
            UPDATE email_accounts
            SET daily_sent_today = daily_sent_today + 1,
                last_used_date = ?
            WHERE id = ?
        """, (today, account_id))
        conn.commit()
        return True
    except Exception as e:
        logger.error("Error updating account usage: %s", e)
        return False
    finally:
        conn.close()


def reset_daily_counts(db_path: str = None) -> bool:
    """Reset daily_sent_today for all accounts (call daily)."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE email_accounts SET daily_sent_today = 0")
        conn.commit()
        return True
    except Exception as e:
        logger.error("Error resetting daily counts: %s", e)
        return False
    finally:
        conn.close()


# ===================================================================
# CAMPAIGN SCHEDULING
# ===================================================================

def update_campaign_schedule(campaign_id: int, scheduled_at: str = None,
                            send_days: str = None, send_time_start: str = None,
                            send_time_end: str = None, emails_per_day: int = None,
                            use_account_rotation: bool = None, db_path: str = None) -> bool:
    """Update campaign scheduling settings."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    try:
        updates = []
        params = []

        if scheduled_at is not None:
            updates.append("scheduled_at = ?")
            params.append(scheduled_at)
        if send_days is not None:
            updates.append("send_days = ?")
            params.append(send_days)
        if send_time_start is not None:
            updates.append("send_time_start = ?")
            params.append(send_time_start)
        if send_time_end is not None:
            updates.append("send_time_end = ?")
            params.append(send_time_end)
        if emails_per_day is not None:
            updates.append("emails_per_day = ?")
            params.append(emails_per_day)
        if use_account_rotation is not None:
            updates.append("use_account_rotation = ?")
            params.append(1 if use_account_rotation else 0)

        if not updates:
            return False

        params.append(campaign_id)
        query = f"UPDATE email_campaigns SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(query, params)
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        logger.error("Error updating campaign schedule: %s", e)
        return False
    finally:
        conn.close()


def get_due_campaigns(db_path: str = None) -> list:
    """Get campaigns that are scheduled and due to be sent."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            SELECT * FROM email_campaigns
            WHERE status = 'scheduled'
            AND scheduled_at <= ?
        """, (now,))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


# Auto-initialize on import
init_db()
