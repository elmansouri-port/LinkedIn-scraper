"""
LinkedIn Scraper CLI v2.0
Enhanced CLI with centralized configuration and per-action logging.

Features:
- All actions use centralized config from config/scraper_config.py
- Each action creates its own log file in data/logs/
- New features: Export to CSV, View statistics, Quick scrape mode
"""
import os
import sys

# Fix Windows console encoding for Unicode/emoji support
if sys.platform == 'win32':
    try:
        # Use reconfigure() which is safer (Python 3.7+)
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except (AttributeError, Exception):
        # Fallback: set environment variable for subprocess
        os.environ['PYTHONIOENCODING'] = 'utf-8'

import time
from datetime import datetime

# Ensure imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.driver_manager import DriverManager
from core.services import ScraperService, ConnectionService, MessagingService, ProfileEnricherService
from scraper.group_scraper import get_scraping_mode

# Try to import config and logger
try:
    from config.scraper_config import (
        GoogleScraperConfig, GroupScraperConfig, 
        ConnectionConfig, MessagingConfig,
        DATA_DIR, LOGS_DIR
    )
    from utils.logger import ActionLogger, get_logger
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    print("⚠️ Config module not loaded, using defaults")


def print_banner():
    """Print CLI banner"""
    print("\n" + "=" * 60)
    print("  LINKEDIN SCRAPER CLI v2.0")
    print("  High-performance scraping with logging")
    print("=" * 60)


def get_max_members_input(default=None):
    """Get user input for maximum number of members to scrape"""
    default_str = f" [{default}]" if default else " [unlimited]"
    while True:
        max_input = input(f"   Max members to scrape{default_str}: ").strip()
        
        if not max_input:
            return default
        
        try:
            max_members = int(max_input)
            if max_members <= 0:
                print("   ⚠️ Please enter a positive number")
                continue
            return max_members
        except ValueError:
            print("   ⚠️ Please enter a valid number")


def get_user_action():
    """Prompt the user to choose an action."""
    while True:
        print("\n📋 AVAILABLE ACTIONS:")
        print("-" * 40)
        print("  1. Scrape LinkedIn group members")
        print("  2. Send messages to group members")
        print("  3. Scrape profiles from LinkedIn search")
        print("  4. Send a single connection request")
        print("  5. Send mass connection requests from CSV")
        print("  6. Scrape LinkedIn profiles (Google search)")
        print("  7. Enrich profiles from CSV (Extract emails)")
        print("-" * 40)
        print("  8. Export database to CSV")
        print("  9. View scraping statistics")
        print("  0. Exit")
        print("-" * 40)

        choice = input("Enter your choice: ").strip()
        if choice in ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"]:
            return choice
        
        print("⚠️ Invalid choice")


def action_google_scraper(driver):
    """Action 6: Google LinkedIn Scraper"""
    print("\n🔍 GOOGLE LINKEDIN SCRAPER")
    print("-" * 40)
    
    # Get configuration with defaults from config
    if CONFIG_AVAILABLE:
        defaults = GoogleScraperConfig
        default_profiles = defaults.DEFAULT_MAX_PROFILES
        default_per_keyword = defaults.DEFAULT_PROFILES_PER_KEYWORD
        default_pages = defaults.DEFAULT_MAX_PAGES_PER_KEYWORD
        default_verbose = defaults.VERBOSE
    else:
        default_profiles = 100
        default_per_keyword = 20
        default_pages = 10
        default_verbose = True
    
    print("\n📋 Configuration:")
    keywords = input("   Keywords (comma-separated): ")
    oblig_keywords = input("   Obligatory keywords (space-separated): ")
    
    max_profiles_input = input(f"   Total profiles [{default_profiles}]: ").strip()
    max_profiles = int(max_profiles_input) if max_profiles_input else default_profiles
    
    per_keyword_input = input(f"   Profiles per keyword [{default_per_keyword}]: ").strip()
    max_per_keyword = int(per_keyword_input) if per_keyword_input else default_per_keyword
    
    print("\n⚙️ Advanced (Enter for defaults):")
    max_pages_input = input(f"   Max pages per keyword [{default_pages}]: ").strip()
    max_pages = int(max_pages_input) if max_pages_input else default_pages
    
    verbose_input = input(f"   Verbose logging? (y/n) [{'y' if default_verbose else 'n'}]: ").strip().lower()
    verbose = verbose_input != 'n' if verbose_input else default_verbose
    
    print(f"\n🚀 Starting scraper (verbose={'ON' if verbose else 'OFF'})...")
    print(f"   📁 Logs will be saved to: data/logs/")
    
    result = ScraperService.scrape_google_linkedin_profiles(
        driver, keywords, oblig_keywords,
        max_profiles, max_per_keyword,
        3, max_pages, verbose
    )
    
    if result['success']:
        print(f"\n✅ {result['message']}")
    else:
        print(f"\n❌ {result['message']}")


def action_export_to_csv():
    """Action 8: Export database to CSV"""
    print("\n📤 EXPORT DATABASE TO CSV")
    print("-" * 40)
    
    import sqlite3
    import csv
    from pathlib import Path
    
    db_dir = Path("data/db")
    csv_dir = Path("data/csv")
    csv_dir.mkdir(parents=True, exist_ok=True)
    
    # List available databases
    db_files = list(db_dir.glob("*.db"))
    
    if not db_files:
        print("❌ No databases found in data/db/")
        return
    
    print("\nAvailable databases:")
    for i, db_file in enumerate(db_files, 1):
        # Get row count
        try:
            conn = sqlite3.connect(db_file)
            count = conn.execute("SELECT COUNT(*) FROM profiles").fetchone()[0]
            conn.close()
            print(f"  {i}. {db_file.name} ({count} profiles)")
        except:
            print(f"  {i}. {db_file.name}")
    
    choice = input("\nSelect database (number): ").strip()
    try:
        db_file = db_files[int(choice) - 1]
    except:
        print("❌ Invalid selection")
        return
    
    # Export to CSV
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_file = csv_dir / f"export_{db_file.stem}_{timestamp}.csv"
    
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM profiles")
    
    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()
    conn.close()
    
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        writer.writerows(rows)
    
    print(f"\n✅ Exported {len(rows)} profiles to: {csv_file}")


def action_view_statistics():
    """Action 9: View scraping statistics"""
    print("\n📊 SCRAPING STATISTICS")
    print("-" * 40)
    
    import sqlite3
    from pathlib import Path
    
    db_dir = Path("data/db")
    log_dir = Path("data/logs")
    
    # Count databases and profiles
    db_files = list(db_dir.glob("*.db"))
    total_profiles = 0
    
    for db_file in db_files:
        try:
            conn = sqlite3.connect(db_file)
            count = conn.execute("SELECT COUNT(*) FROM profiles").fetchone()[0]
            total_profiles += count
            conn.close()
        except:
            pass
    
    # Count log files
    log_files = list(log_dir.glob("*.log"))
    
    print(f"\n📁 Databases: {len(db_files)}")
    print(f"👤 Total profiles scraped: {total_profiles}")
    print(f"📝 Log files: {len(log_files)}")
    
    # Recent activity
    if db_files:
        print("\n📅 Recent databases:")
        sorted_dbs = sorted(db_files, key=lambda x: x.stat().st_mtime, reverse=True)[:5]
        for db in sorted_dbs:
            try:
                conn = sqlite3.connect(db)
                count = conn.execute("SELECT COUNT(*) FROM profiles").fetchone()[0]
                conn.close()
                mod_time = datetime.fromtimestamp(db.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
                print(f"   • {db.name} - {count} profiles ({mod_time})")
            except:
                print(f"   • {db.name}")


def main():
    """Main CLI entry point"""
    # Ensure directories exist
    os.makedirs("data/logs", exist_ok=True)
    os.makedirs("data/csv", exist_ok=True)
    os.makedirs("data/db", exist_ok=True)
    
    print_banner()
    
    driver = None
    temp_profile = None
    
    try:
        while True:
            action = get_user_action()
            
            # Exit
            if action == "0":
                print("\n👋 Goodbye!")
                break
            
            # Actions that don't need driver
            if action == "8":
                action_export_to_csv()
                continue
            
            if action == "9":
                action_view_statistics()
                continue
            
            # Setup driver if not already done
            if driver is None:
                print("\n🔧 Setting up Chrome driver...")
                driver, temp_profile = DriverManager.setup_chrome_driver()
                print("✅ Chrome driver ready!")
                
                # Login
                from auth.auth_manager import AuthManager
                from config import settings
                
                print("🔑 Logging in...")
                auth_manager = AuthManager(settings.LINKEDIN_EMAIL, settings.LINKEDIN_PASSWORD)
                logged_in = auth_manager.login(driver)
                
                if not logged_in:
                    print("❌ Login failed!")
                    break
                
                print("✅ Logged in successfully!")
            
            # Execute action
            if action == "1":
                # Group scraper
                from config.settings import GROUP_URL
                max_members = get_max_members_input()
                scraping_mode = get_scraping_mode()
                print(f"🚀 Starting group scraping...")
                
                result = ScraperService.scrape_group_members(
                    driver, GROUP_URL, max_members, scraping_mode
                )
                print(f"{'✅' if result['success'] else '❌'} {result['message']}")
                
            elif action == "2":
                # Messaging
                print("🚀 Starting messaging campaign...")
                result = MessagingService.send_group_messages(driver)
                print(f"{'✅' if result['success'] else '❌'} {result['message']}")
                
            elif action == "3":
                # LinkedIn search
                keywords = input("   Search keywords: ")
                profnum = input("   Number of profiles: ")
                start_page = input("   Start page [1]: ").strip() or "1"
                
                result = ScraperService.search_and_scrape_profiles(
                    driver, keywords, int(profnum), int(start_page)
                )
                print(f"{'✅' if result['success'] else '❌'} {result['message']}")
                
            elif action == "4":
                # Single connection
                profile_url = input("   Profile URL: ")
                note = input("   Note (optional): ").strip() or None
                
                result = ConnectionService.send_single_connection(driver, profile_url, note)
                print(f"{'✅' if result['success'] else '❌'} {result['message']}")
                
            elif action == "5":
                # Mass connections
                csv_file = input("   CSV file path: ")
                note = input("   Note (optional): ").strip()
                
                result = ConnectionService.send_mass_connections(
                    driver, csv_file, note, bool(note)
                )
                print(f"{'✅' if result['success'] else '❌'} {result['message']}")
                
            elif action == "6":
                # Google scraper
                action_google_scraper(driver)
                
            elif action == "7":
                # Profile enricher
                print("\n📧 PROFILE ENRICHER")
                csv_file = input("   CSV file path: ")
                url_column = input("   URL column name [Profile URL]: ").strip() or "Profile URL"
                max_profiles = input("   Max profiles [all]: ").strip()
                max_profiles = int(max_profiles) if max_profiles else None
                
                result = ProfileEnricherService.enrich_profiles_from_csv(
                    driver, csv_file, url_column, max_profiles
                )
                
                if result['success']:
                    print(f"\n✅ {result['message']}")
                    print(f"📁 Output: {result['output_file']}")
                else:
                    print(f"\n❌ {result['message']}")
            
            print("\n" + "-" * 40)
            input("Press Enter to continue...")
    
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if driver:
            print("\n🧹 Cleaning up...")
            time.sleep(2)
            DriverManager.cleanup_driver(driver, temp_profile)
            print("✅ Done!")


if __name__ == "__main__":
    main()
