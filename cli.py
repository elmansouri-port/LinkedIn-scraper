"""
LinkedIn Scraper CLI v2.0
Enhanced CLI with centralized configuration and logging.

Features:
- All actions use centralized config from config/scraper_config.py
- Consistent logging to console and files
- New features: Export to CSV, View statistics, Quick scrape mode
"""
import os
import sys

# Fix Windows console encoding for Unicode support
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, Exception):
        os.environ["PYTHONIOENCODING"] = "utf-8"

import logging
import time
from datetime import datetime

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.driver_manager import DriverManager
from core.services import ScraperService, ConnectionService, MessagingService, ProfileEnricherService
from core.services.email_testing_service import EmailTestingService
from core.services.email_sending_service import EmailSendingService
from scraper.group_scraper import get_scraping_mode
from config.scraper_config import (
    GoogleScraperConfig,
    GroupScraperConfig,
    ConnectionConfig,
    MessagingConfig,
    EmailConfig,
    DATA_DIR,
    LOGS_DIR,
    LINKEDIN_EMAIL,
    LINKEDIN_PASSWORD,
)
from utils.logger import init_logging, get_logger, SessionState


def print_banner():
    """Print CLI banner."""
    print("\n" + "=" * 60)
    print("  LINKEDIN SCRAPER CLI v2.0")
    print("  High-performance scraping with logging")
    print("=" * 60)


def get_max_members_input(default=None):
    """Get user input for maximum number of members to scrape."""
    default_str = f" [{default}]" if default else " [unlimited]"
    while True:
        max_input = input(f"   Max members to scrape{default_str}: ").strip()
        if not max_input:
            return default
        try:
            max_members = int(max_input)
            if max_members <= 0:
                print("   Please enter a positive number")
                continue
            return max_members
        except ValueError:
            print("   Please enter a valid number")


def get_user_action():
    """Prompt the user to choose an action."""
    while True:
        print("\nAVAILABLE ACTIONS:")
        print("-" * 40)
        print("  1. Scrape LinkedIn group members")
        print("  2. Send messages to group members")
        print("  3. Scrape profiles from LinkedIn search")
        print("  4. Send a single connection request")
        print("  5. Send mass connection requests from CSV")
        print("  6. Scrape LinkedIn profiles (Google search)")
        print("  7. Enrich profiles (visit, extract email)")
        print("-" * 40)
        print("  8. Export to CSV/Excel")
        print("  9. View scraping statistics")
        print("  10. Authentication setup")
        print("-" * 40)
        print("  11. Test email addresses")
        print("  12. Send emails (campaign)")
        print("  13. Generate CVs (AI-powered)")
        print("  14. Schedule campaigns")
        print("  15. Manage email accounts")
        print("  16. Run scheduler")
        print("-" * 40)
        print("  0. Exit")
        print("-" * 40)

        choice = input("Enter your choice: ").strip()
        if choice in ("0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16"):
            return choice
        print("Invalid choice")


def action_google_scraper(driver):
    """Action 6: Google LinkedIn Scraper."""
    logger = get_logger("cli.google_scraper")
    print("\nGOOGLE LINKEDIN SCRAPER")
    print("-" * 40)

    defaults = GoogleScraperConfig
    default_profiles = defaults.DEFAULT_MAX_PROFILES
    default_per_keyword = defaults.DEFAULT_PROFILES_PER_KEYWORD
    default_pages = defaults.DEFAULT_MAX_PAGES_PER_KEYWORD
    default_verbose = defaults.VERBOSE

    print("\nConfiguration:")
    keywords = input("   Keywords (comma-separated): ")
    oblig_keywords = input("   Obligatory keywords (space-separated): ")

    max_profiles_input = input(f"   Total profiles [{default_profiles}]: ").strip()
    max_profiles = int(max_profiles_input) if max_profiles_input else default_profiles

    per_keyword_input = input(f"   Profiles per keyword [{default_per_keyword}]: ").strip()
    max_per_keyword = int(per_keyword_input) if per_keyword_input else default_per_keyword

    print("\nAdvanced (Enter for defaults):")
    max_pages_input = input(f"   Max pages per keyword [{default_pages}]: ").strip()
    max_pages = int(max_pages_input) if max_pages_input else default_pages

    verbose_input = input(f"   Verbose logging? (y/n) [{'y' if default_verbose else 'n'}]: ").strip().lower()
    verbose = verbose_input != "n" if verbose_input else default_verbose

    logger.info(
        "Starting Google scraper | profiles=%d per_kw=%d pages=%d verbose=%s",
        max_profiles, max_per_keyword, max_pages, verbose,
    )

    result = ScraperService.scrape_google_linkedin_profiles(
        driver,
        keywords,
        oblig_keywords,
        max_profiles,
        max_per_keyword,
        3,
        max_pages,
        verbose,
    )

    if result["success"]:
        print(f"\n{result['message']}")
    else:
        print(f"\n{result['message']}")


def action_export_database():
    """Action 8: Export data to CSV or Excel — user-friendly multi-stage exporter."""
    logger = get_logger("cli.export")
    from core.export_manager import (
        EXPORT_PRESETS, get_preset_info, get_row_count,
        export_preset_to_csv, export_preset_to_excel,
    )
    from config.scraper_config import CSV_DIR

    print("\nEXPORT DATA")
    print("-" * 40)
    print("Choose what to export:\n")

    presets = get_preset_info()
    for i, p in enumerate(presets, 1):
        count = get_row_count(p["key"])
        print(f"  {i}. {p['label']} ({count} rows)")
        print(f"     {p['description']}")

    print()
    choice = input("Select (number): ").strip()
    try:
        preset_key = presets[int(choice) - 1]["key"]
    except (ValueError, IndexError):
        print("Invalid selection")
        return

    if get_row_count(preset_key) == 0:
        print("No data available for this export.")
        return

    print("\nExport format:")
    print("  1. CSV")
    print("  2. Excel (.xlsx)")
    fmt = input("Select (1/2): ").strip()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"{preset_key}_{timestamp}"

    if fmt == "2":
        output_path = os.path.join(CSV_DIR, f"{base_name}.xlsx")
        success = export_preset_to_excel(preset_key, output_path)
    else:
        output_path = os.path.join(CSV_DIR, f"{base_name}.csv")
        success = export_preset_to_csv(preset_key, output_path)

    if success:
        print(f"\nExported to: {output_path}")
        logger.info("Exported %s to %s", preset_key, output_path)
    else:
        print("\nExport failed. Check logs for details.")


def action_auth_setup(driver):
    """Action 10: Authentication setup — manage LinkedIn login methods."""
    logger = get_logger("cli.auth")
    from auth.auth_manager import AuthManager

    print("\nAUTHENTICATION SETUP")
    print("-" * 40)

    auth = AuthManager(LINKEDIN_EMAIL, LINKEDIN_PASSWORD)
    has_cookies = auth.has_saved_cookies()
    has_credentials = bool(auth.email and auth.password)

    from core.driver_manager import DriverManager

    # Show current profile selection
    active = DriverManager.get_active_profile_config()
    profile_status = f"{active['name']} ({active['prof_dir']})" if active else "Fresh profile (no cookies)"

    print(f"\nCurrent status:")
    print(f"  Saved cookies:  {'Yes' if has_cookies else 'No'}")
    print(f"  Credentials:    {'Set' if has_credentials else 'Not set'}")
    print(f"  Chrome profile: {profile_status}")

    print(f"\nOptions:")
    print(f"  1. Log in manually (browser — Google, Apple, etc.)")
    print(f"  2. Log in with email/password")
    print(f"  3. Clear saved cookies")
    print(f"  4. Set email/password")
    print(f"  5. Select Chrome profile (use existing browser session)")

    choice = input("\nSelect (1-5): ").strip()

    if choice == "1":
        print(f"\nOpening LinkedIn in browser...")
        success = auth.manual_login(driver)
        if success:
            logger.info("Manual login successful — cookies saved")
        else:
            logger.warning("Manual login timed out")

    elif choice == "2":
        print(f"\nAttempting credential login...")
        success = auth.login(driver, force_credentials=True)
        if success:
            logger.info("Credential login successful — cookies saved")
        else:
            logger.error("Credential login failed")

    elif choice == "3":
        auth.clear_cookies()
        logger.info("Cookies cleared")

    elif choice == "4":
        email = input(f"  Email [{auth.email or 'none'}]: ").strip() or auth.email
        password = input(f"  Password: ").strip()
        if email and password:
            auth.email = email
            auth.password = password
            # Test the credentials
            success = auth.login_with_credentials(driver)
            if success:
                logger.info("New credentials saved")
            else:
                logger.error("Credential login failed")
        else:
            print("Email and password are required.")

    elif choice == "5":
        print(f"\nScanning for browser profiles...")
        profiles = DriverManager.detect_profiles()
        if not profiles:
            print("No existing browser profiles found.")
            print("Tip: Log into LinkedIn in Chromium first, then re-run this option.")
            return

        print(f"\nAvailable profiles:\n")
        for i, prof in enumerate(profiles, 1):
            print(f"  {i}. {prof['name']} ({prof['dir']})")
        print(f"  0. Use fresh profile (no saved session)")

        sel = input(f"\nSelect profile (1-{len(profiles)}): ").strip()
        if sel == "0":
            DriverManager.clear_profile_choice()
            print("Profile selection cleared. Will use a fresh profile.")
            return

        try:
            idx = int(sel) - 1
            if 0 <= idx < len(profiles):
                prof = profiles[idx]
                DriverManager.save_profile_choice(prof["path"], prof["name"])
                print(f"\nSelected profile: {prof['name']} ({prof['dir']})")
                print("This profile will be used for all browser sessions.")
                logger.info("Profile selected: %s (%s)", prof["name"], prof["path"])
            else:
                print("Invalid selection.")
        except ValueError:
            print("Invalid selection.")

    else:
        print("Invalid choice.")


def action_view_statistics():
    """Action 9: View scraping statistics."""
    from core.database import get_stats
    from core.export_manager import get_preset_info, get_row_count
    from config.scraper_config import LOGS_DIR
    from pathlib import Path

    print("\nSCRAPING STATISTICS")
    print("-" * 40)

    stats = get_stats()
    total = sum(stats.values())

    print(f"\nDatabase records:")
    for table, count in stats.items():
        label = table.replace("_", " ").title()
        print(f"  {label}: {count}")
    print(f"  Total: {total}")

    print(f"\nReady to export:")
    for p in get_preset_info():
        count = get_row_count(p["key"])
        if count > 0:
            print(f"  {p['label']}: {count} rows")

    log_dir = Path(LOGS_DIR)
    log_files = list(log_dir.glob("*.log"))
    print(f"\nLog files: {len(log_files)}")


def action_test_emails():
    """Action 11: Test email addresses."""
    logger = get_logger("cli.email_testing")
    print("\nEMAIL VERIFICATION")
    print("-" * 40)

    print("\nVerification method:")
    print("  1. SMTP handshake (recommended - most accurate)")
    print("  2. DNS/MX check (faster, less accurate)")

    method_choice = input("\nSelect (1-2) [1]: ").strip() or "1"
    method = "smtp" if method_choice == "1" else "dns"

    print(f"\nOptions:")
    print("  1. Test all unverified emails")
    print("  2. Test sample (first N emails)")
    print("  3. Test specific email")

    option = input("\nSelect (1-3) [1]: ").strip() or "1"

    if option == "1":
        max_test = None
        only_unverified = True
    elif option == "2":
        try:
            max_test = int(input("  How many to test: ").strip())
        except ValueError:
            print("Invalid number")
            return
        only_unverified = True
    elif option == "3":
        email = input("  Email to test: ").strip()
        if not email:
            return
        result = EmailTestingService.test_single_email(email, method)
        print(f"\nResult: {'VALID' if result[0] else 'INVALID'}")
        print(f"Reason: {result[1]}")
        return
    else:
        print("Invalid choice")
        return

    logger.info("Starting email verification")
    print(f"\nVerifying emails using {method.upper()}...")

    result = EmailTestingService.test_profile_emails(
        max_test=max_test,
        method=method,
        only_unverified=only_unverified
    )

    if result['success']:
        print(f"\n{result['message']}")
        print(f"Valid: {result['valid']}")
        print(f"Invalid: {result['invalid']}")
    else:
        print(f"\nError: {result['message']}")


def action_send_emails():
    """Action 12: Send emails (campaign)."""
    logger = get_logger("cli.email_sending")
    print("\nEMAIL CAMPAIGN")
    print("-" * 40)

    # Show available SMTP presets
    presets = EmailSendingService.get_smtp_presets()
    print(f"\nAvailable SMTP presets:")
    for i, preset in enumerate(presets, 1):
        print(f"  {i}. {preset}")

    # Get or create campaign
    campaigns = EmailSendingService.get_all_campaigns()
    print(f"\nExisting campaigns:")
    if campaigns:
        for c in campaigns:
            print(f"  {c['id']}. {c['name']} - {c['status']}")
    else:
        print("  (none)")

    print(f"\nOptions:")
    print("  1. Create new campaign")
    print("  2. Use existing campaign")

    choice = input("\nSelect (1-2) [2]: ").strip() or "2"

    campaign_id = None

    if choice == "1":
        print("\nCreate New Campaign:")
        name = input("  Campaign name: ").strip()
        if not name:
            print("Campaign name required")
            return

        subject = input("  Subject (use {first_name}, {company}, etc.): ").strip()
        if not subject:
            subject = EmailConfig.DEFAULT_SUBJECT

        print("\n  Body (plain text):")
        print("  Variables: {first_name}, {last_name}, {company}, {email}")
        body_text = input("  Body: ").strip()
        if not body_text:
            body_text = EmailConfig.DEFAULT_BODY_TEXT

        print("\n  Body (HTML - optional, press Enter to skip):")
        body_html = input("  HTML Body: ").strip() or None

        # CV and Cover Letter attachments
        print("\n  Attachments (press Enter to skip):")
        cv_path = input("  CV file path (e.g., data/documents/cv/my_cv.pdf): ").strip()
        if cv_path and not os.path.exists(cv_path):
            print("  Warning: CV file not found, will continue without it")
            cv_path = None

        cover_letter_path = input("  Cover letter file path (e.g., data/documents/cover_letters/letter.pdf): ").strip()
        if cover_letter_path and not os.path.exists(cover_letter_path):
            print("  Warning: Cover letter not found, will continue without it")
            cover_letter_path = None

        result = EmailSendingService.create_campaign(
            name, subject, body_text, body_html, cv_path, cover_letter_path
        )

        if result['success']:
            campaign_id = result['campaign_id']
            print(f"\nCampaign created! ID: {campaign_id}")
        else:
            print(f"\nError: {result['message']}")
            return

    elif choice == "2":
        try:
            campaign_id = int(input("\n  Enter campaign ID: ").strip())
        except ValueError:
            print("Invalid ID")
            return

    # Prepare emails
    print("\nPreparing emails from enriched profiles...")
    prepared = EmailSendingService.prepare_campaign_emails(campaign_id)
    print(f"Prepared {prepared} emails for sending")

    if prepared == 0:
        print("No emails to send. Check your enriched profiles.")
        return

    # Preview
    preview = EmailSendingService.preview_email(campaign_id)
    if preview['success']:
        print(f"\nPreview:")
        print(f"  To: {preview['sample_profile']['name']}")
        print(f"  Email: {preview['sample_profile']['email']}")
        print(f"  Subject: {preview['subject']}")
        print(f"  Body preview: {preview['body_text'][:100]}...")
        if preview.get('attachments'):
            print(f"  Attachments:")
            for att in preview['attachments']:
                print(f"    - {os.path.basename(att)}")

    # SMTP Configuration
    print("\nSMTP Configuration:")
    preset_choice = input(f"  Preset (gmail/outlook/office365) [gmail]: ").strip() or "gmail"
    username = input(f"  Username (email): ").strip()
    password = input(f"  Password (app password): ").strip()

    if not username or not password:
        print("Username and password required")
        return

    # Sending options
    print("\nSending options:")
    only_verified = input("  Send only to verified emails? (y/n) [y]: ").strip().lower() or "y"
    only_verified = only_verified == "y"

    max_send_input = input("  Max emails to send (Enter for all): ").strip()
    max_send = int(max_send_input) if max_send_input else None

    # Confirm
    confirm = input(f"\nReady to send. Continue? (y/n) [y]: ").strip().lower() or "y"
    if confirm != "y":
        print("Cancelled.")
        return

    # Send
    print("\nSending emails...")
    result = EmailSendingService.send_campaign(
        campaign_id=campaign_id,
        smtp_preset=preset_choice,
        username=username,
        password=password,
        max_send=max_send,
        only_verified=only_verified
    )

    if result['success']:
        print(f"\n{result['message']}")
    else:
        print(f"\nError: {result['message']}")


def action_generate_cvs():
    """Action 13: Generate AI-powered CVs using Groq."""
    logger = get_logger("cli.generate_cvs")
    print("\nGENERATE CUSTOMIZED CVs (AI)")
    print("-" * 40)

    # Check if Groq is available
    try:
        from core.groq_service import GroqService
        from core.cv_generator import generate_cv_for_profile, compile_latex_to_pdf
        from core.database import get_profiles_without_cv, get_all_enriched_profiles
    except ImportError as e:
        print(f"Error: Required modules not found - {e}")
        return

    # Initialize Groq service
    try:
        groq = GroqService()
        print("Groq AI service initialized successfully")
    except Exception as e:
        print(f"Failed to initialize Groq service: {e}")
        print("Check your GROQ_API_KEY in .env file")
        return

    # Get profiles
    print("\nOptions:")
    print("  1. Generate CVs for profiles without CVs")
    print("  2. Generate CV for specific profile URL")

    choice = input("\nSelect (1/2): ").strip()

    if choice == "1":
        profiles = get_profiles_without_cv()
        if not profiles:
            print("All profiles already have CVs generated!")
            return
        print(f"\nFound {len(profiles)} profiles without CVs")
        confirm = input("Generate CVs for all? (y/n): ").strip().lower()
        if confirm != "y":
            print("Cancelled")
            return

        generated = 0
        failed = 0
        for i, profile in enumerate(profiles, 1):
            print(f"\n[{i}/{len(profiles)}] Processing {profile.get('full_name', 'Unknown')}...")
            try:
                cv_path = generate_cv_for_profile(
                    profile['profile_url'],
                    groq,
                    base_cv_path="templates/base_cv.tex",
                    output_dir="data/documents/generated_cvs",
                )
                print(f"  Generated: {cv_path}")

                # Try to compile to PDF
                try:
                    pdf_path = compile_latex_to_pdf(cv_path)
                    if pdf_path:
                        print(f"  Compiled: {pdf_path}")
                except Exception as pdf_err:
                    print(f"  PDF compilation skipped: {pdf_err}")

                generated += 1

                # Rate limit: 60 seconds between requests
                if i < len(profiles):
                    print(f"  Waiting 60s (rate limit)...")
                    time.sleep(60)

            except Exception as e:
                print(f"  Error: {e}")
                failed += 1

        print(f"\nCompleted: {generated} generated, {failed} failed")

    elif choice == "2":
        profile_url = input("\nProfile URL: ").strip()
        if not profile_url:
            print("No URL provided")
            return

        try:
            cv_path = generate_cv_for_profile(
                profile_url,
                groq,
                base_cv_path="templates/base_cv.tex",
                output_dir="data/documents/generated_cvs",
            )
            print(f"\nGenerated: {cv_path}")

            # Try to compile to PDF
            try:
                pdf_path = compile_latex_to_pdf(cv_path)
                if pdf_path:
                    print(f"Compiled to PDF: {pdf_path}")
            except Exception as pdf_err:
                print(f"PDF compilation skipped: {pdf_err}")
                print("Install MiKTeX to compile LaTeX to PDF")

        except Exception as e:
            print(f"Error: {e}")

    else:
        print("Invalid choice")

    logger.info("Action 13 completed")


def action_schedule_campaign():
    """Action 14: Schedule a campaign for later sending."""
    logger = get_logger("cli.schedule")
    print("\nSCHEDULE CAMPAIGN")
    print("-" * 40)

    from core.database import get_all_email_campaigns, get_email_campaign
    from core.services.email_scheduler import EmailScheduler

    campaigns = get_all_email_campaigns()
    if not campaigns:
        print("No campaigns found. Create one first (Action 12).")
        return

    print("\nAvailable campaigns:\n")
    for c in campaigns:
        status = c['status']
        scheduled = c.get('scheduled_at', 'Not scheduled')
        print(f"  {c['id']}. {c['name']} - {status}")
        print(f"     Scheduled: {scheduled}")

    campaign_id = input("\nCampaign ID to schedule: ").strip()
    try:
        campaign_id = int(campaign_id)
    except ValueError:
        print("Invalid ID")
        return

    campaign = get_email_campaign(campaign_id)
    if not campaign:
        print("Campaign not found")
        return

    print(f"\nScheduling campaign: {campaign['name']}")

    # Get schedule details
    print("\nSchedule options:")
    print("  1. Schedule for specific date/time")
    print("  2. Set recurring schedule (every X days)")

    choice = input("Select (1-2) [1]: ").strip() or "1"

    if choice == "1":
        scheduled_at = input("Schedule for (YYYY-MM-DD HH:MM:SS) [now + 1 hour]: ").strip()
        if not scheduled_at:
            from datetime import datetime, timedelta
            scheduled_at = (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
    else:
        # Recurring - just set the initial date, scheduler will handle recurring
        scheduled_at = input("Start date (YYYY-MM-DD HH:MM:SS): ").strip()

    # Day restrictions
    print("\nDay restrictions (default: skip weekends):")
    print("  0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun")
    send_days = input("Allowed days (comma-separated, e.g., 0,1,2,3,4) [from Mon-Fri]: ").strip()
    if not send_days:
        send_days = "0,1,2,3,4"

    # Time window
    send_time_start = input("Send window start (HH:MM) [09:00]: ").strip() or "09:00"
    send_time_end = input("Send window end (HH:MM) [17:00]: ").strip() or "17:00"

    # Emails per day
    emails_per_day = input("Max emails per day [20]: ").strip() or "20"
    try:
        emails_per_day = int(emails_per_day)
    except ValueError:
        emails_per_day = 20

    # Account rotation
    use_rotation = input("Use email account rotation? (y/n) [y]: ").strip().lower() or "y"
    use_rotation = use_rotation == "y"

    # Update campaign
    scheduler = EmailScheduler()
    result = scheduler.schedule_campaign(
        campaign_id=campaign_id,
        scheduled_at=scheduled_at,
        send_days=send_days,
        send_time_start=send_time_start,
        send_time_end=send_time_end,
        emails_per_day=emails_per_day,
        use_account_rotation=use_rotation,
    )

    if result:
        print(f"\nCampaign scheduled successfully!")
        print(f"  Scheduled for: {scheduled_at}")
        print(f"  Allowed days: {send_days}")
        print(f"  Send window: {send_time_start} - {send_time_end}")
        print(f"  Max per day: {emails_per_day}")
        print(f"  Account rotation: {'Yes' if use_rotation else 'No'}")
    else:
        print("\nFailed to schedule campaign")

    logger.info("Action 14 completed | campaign=%d", campaign_id)


def action_manage_email_accounts():
    """Action 15: Manage email accounts for rotation."""
    logger = get_logger("cli.email_accounts")
    print("\nMANAGE EMAIL ACCOUNTS")
    print("-" * 40)

    from core.database import get_email_accounts, add_email_account

    while True:
        print("\nOptions:")
        print("  1. List all accounts")
        print("  2. Add new account")
        print("  3. Remove account")
        print("  4. Toggle account active/inactive")
        print("  5. Reset daily counts")
        print("  0. Back")

        choice = input("\nSelect (0-5): ").strip()

        if choice == "0":
            break

        elif choice == "1":
            accounts = get_email_accounts(active_only=False)
            if not accounts:
                print("\nNo accounts configured.")
                continue

            print("\nConfigured accounts:\n")
            for acc in accounts:
                status = "Active" if acc['is_active'] else "Inactive"
                print(f"  ID: {acc['id']}")
                print(f"     Email: {acc['email']}")
                print(f"     SMTP: {acc['smtp_preset']}")
                print(f"     Daily limit: {acc['daily_limit']}")
                print(f"     Sent today: {acc['daily_sent_today']}")
                print(f"     Status: {status}")
                print()

        elif choice == "2":
            print("\nAdd new email account:")
            email = input("  Email: ").strip()
            smtp_preset = input("  SMTP preset (gmail/outlook/office365) [gmail]: ").strip() or "gmail"
            username = input("  Username: ").strip()
            password = input("  Password (app password): ").strip()
            daily_limit = input("  Daily limit [50]: ").strip() or "50"

            try:
                daily_limit = int(daily_limit)
            except ValueError:
                daily_limit = 50

            if not email or not username or not password:
                print("All fields are required")
                continue

            account_id = add_email_account(email, smtp_preset, username, password, daily_limit)
            if account_id:
                print(f"Account added successfully! ID: {account_id}")
            else:
                print("Failed to add account (might already exist)")

        elif choice == "3":
            accounts = get_email_accounts(active_only=False)
            if accounts:
                for acc in accounts:
                    print(f"  {acc['id']}. {acc['email']}")

                acc_id = input("\nAccount ID to remove: ").strip()
                try:
                    acc_id = int(acc_id)
                    from core.database import get_connection
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM email_accounts WHERE id = ?", (acc_id,))
                    conn.commit()
                    conn.close()
                    print("Account removed")
                except ValueError:
                    print("Invalid ID")
            else:
                print("No accounts to remove")

        elif choice == "4":
            accounts = get_email_accounts(active_only=False)
            if accounts:
                for acc in accounts:
                    status = "Active" if acc['is_active'] else "Inactive"
                    print(f"  {acc['id']}. {acc['email']} ({status})")

                acc_id = input("\nAccount ID to toggle: ").strip()
                try:
                    acc_id = int(acc_id)
                    from core.database import get_connection
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute("UPDATE email_accounts SET is_active = NOT is_active WHERE id = ?", (acc_id,))
                    conn.commit()
                    conn.close()
                    print("Account status toggled")
                except ValueError:
                    print("Invalid ID")

        elif choice == "5":
            from core.database import reset_daily_counts
            if reset_daily_counts():
                print("Daily counts reset successfully")
            else:
                print("Failed to reset daily counts")

    logger.info("Action 15 completed")


def action_run_scheduler():
    """Action 16: Run the email scheduler manually."""
    logger = get_logger("cli.scheduler")
    print("\nRUN EMAIL SCHEDULER")
    print("-" * 40)

    confirm = input("Run scheduler now? This will send due campaigns. (y/n): ").strip().lower()
    if confirm != "y":
        print("Cancelled")
        return

    from core.services.email_scheduler import run_scheduler
    try:
        results = run_scheduler()
        print(f"\nScheduler completed:")
        print(f"  Processed: {results.get('processed', 0)}")
        print(f"  Skipped: {results.get('skipped', 0)}")
        print(f"  Errors: {results.get('errors', 0)}")

        if results.get('details'):
            print("\nDetails:")
            for detail in results['details']:
                campaign_id = detail.get('campaign_id', '?')
                status = detail.get('status', 'unknown')
                reason = detail.get('reason', '')
                print(f"  Campaign {campaign_id}: {status} {reason}")

    except Exception as e:
        print(f"Error running scheduler: {e}")
        logger.error("Scheduler error: %s", e, exc_info=True)

    logger.info("Action 16 completed")


def _ensure_authenticated(driver, auth_manager):
    """Log in to LinkedIn if not already authenticated.

    First checks if already logged in (e.g. via browser profile),
    then tries: saved cookies → credentials → manual login.

    Returns:
        (bool, AuthManager): (success, auth_manager)
    """
    from auth.auth_manager import AuthManager

    if auth_manager is not None:
        return True, auth_manager

    auth_manager = AuthManager(LINKEDIN_EMAIL, LINKEDIN_PASSWORD)

    # Already logged in via browser profile? — skip all auth
    if auth_manager._verify_login(driver, timeout=3):
        return True, auth_manager

    # Try automatic login (cookies, then credentials)
    print("\nLogging in to LinkedIn...")
    logged_in = auth_manager.login(driver)

    if logged_in:
        print("Logged in successfully!")
        return True, auth_manager

    # Auto-login failed — offer manual login
    print("Automatic login failed.")
    use_manual = input("Log in manually in browser? (y/n): ").strip().lower()

    if use_manual == "y":
        print("Opening LinkedIn — please log in...")
        success = auth_manager.manual_login(driver)
        if success:
            print("Logged in successfully!")
            return True, auth_manager
        print("Manual login timed out.")

    return False, None


def main():
    """Main CLI entry point."""
    # Initialize logging system
    init_logging(level="INFO", console=True, file_output=True, log_dir="data/logs")
    logger = get_logger("cli")

    print_banner()
    logger.info("CLI started")

    driver = None
    temp_profile = None
    auth_manager = None

    # Actions that require LinkedIn auth
    _ACTIONS_NEEDING_AUTH = {"1", "2", "3", "4", "5", "7"}

    try:
        while True:
            action = get_user_action()

            # Exit
            if action == "0":
                print("\nGoodbye!")
                logger.info("CLI exited by user")
                break

            # Actions that don't need driver
            if action == "8":
                action_export_database()
                continue
            if action == "9":
                action_view_statistics()
                continue

            # Setup driver if not already done
            if driver is None:
                print("\nSetting up Chrome driver...")
                logger.info("Initializing Chrome driver")
                driver, temp_profile = DriverManager.setup_chrome_driver()

            # Authentication setup — doesn't need pre-auth
            if action == "10":
                action_auth_setup(driver)
                continue

            # Authenticate only if this action requires LinkedIn
            if action in _ACTIONS_NEEDING_AUTH:
                ok, auth_manager = _ensure_authenticated(driver, auth_manager)
                if not ok:
                    break

            # Execute action
            if action == "1":
                max_members = get_max_members_input()
                scraping_mode = get_scraping_mode()
                group_url = GroupScraperConfig.DEFAULT_GROUP_URL

                if not group_url:
                    group_url = input("   Group URL: ").strip()

                logger.info("Action 1: Group scrape | mode=%s max=%s", scraping_mode, max_members or "unlimited")
                print(f"Starting group scraping (mode={scraping_mode})...")

                result = ScraperService.scrape_group_members(
                    driver, group_url, max_members, scraping_mode
                )
                print(result["message"])

            elif action == "2":
                logger.info("Action 2: Messaging campaign")
                print("Starting messaging campaign...")
                result = MessagingService.send_group_messages(driver)
                print(result["message"])

            elif action == "3":
                keywords = input("   Search keywords: ")
                profnum_input = input("   Number of profiles: ")
                start_page_input = input("   Start page [1]: ").strip() or "1"

                try:
                    profnum = int(profnum_input)
                    start_page = int(start_page_input)
                except ValueError:
                    print("Invalid number entered")
                    continue

                logger.info("Action 3: Profile search | keywords='%s' max=%d", keywords, profnum)
                result = ScraperService.search_and_scrape_profiles(
                    driver, keywords, profnum, start_page
                )
                print(result["message"])

            elif action == "4":
                profile_url = input("   Profile URL: ")
                note = input("   Note (optional): ").strip() or None

                logger.info("Action 4: Single connection | url=%s", profile_url)
                result = ConnectionService.send_single_connection(driver, profile_url, note)
                print(result["message"])

            elif action == "5":
                csv_file = input("   CSV file path: ")
                note = input("   Note (optional): ").strip()

                logger.info("Action 5: Mass connections | csv=%s", csv_file)
                result = ConnectionService.send_mass_connections(
                    driver, csv_file, note, bool(note)
                )
                print(result["message"])

            elif action == "6":
                action_google_scraper(driver)

            elif action == "7":
                print("\nPROFILE ENRICHER")
                print("-" * 40)
                print("1. Enrich from CSV file")
                print("2. Enrich from already scraped profiles (database)")

                enrich_choice = input("\nSelect (1-2): ").strip()

                if enrich_choice == "2":
                    from core.database import get_search_profiles_not_enriched
                    profiles = get_search_profiles_not_enriched()

                    if not profiles:
                        print("\nNo unenriched scraped profiles found.")
                        print("Tip: Run Google scraper (action 6) first, or use CSV option.")
                        continue

                    print(f"\nAvailable scraped profiles ({len(profiles)} total):\n")
                    header = "   #  " + "Name".ljust(25) + " " + "Title".ljust(40) + " Company"
                    sep = "   " + "-"*3 + " " + "-"*25 + " " + "-"*40 + " " + "-"*30
                    print(header)
                    print(sep)
                    for i, p in enumerate(profiles, 1):
                        name = (p.get("name") or "?")[:24]
                        title = (p.get("title") or "?")[:39]
                        company = (p.get("company") or "")[:29]
                        print(f"   {i:2d}  {name:25s} {title:40s} {company}")

                    print(f"\nEnrich options:")
                    print("   a. All profiles")
                    print("   b. Specific indices (e.g. 1,3,5)")
                    print("   c. Range (e.g. 1-10)")

                    sel = input("\nSelect (a/b/c): ").strip().lower()

                    result = None
                    if sel == "a":
                        max_p = input("   Max profiles [all]: ").strip()
                        max_p = int(max_p) if max_p else None
                        result = ProfileEnricherService.enrich_profiles_from_db(
                            driver, max_profiles=max_p,
                        )
                    elif sel == "b":
                        indices = input("   Indices (comma-separated, e.g. 1,3,5): ").strip()
                        try:
                            idx_list = [int(x.strip()) for x in indices.split(",") if x.strip()]
                            result = ProfileEnricherService.enrich_profiles_from_db(
                                driver, profile_indices=idx_list,
                            )
                        except ValueError:
                            print("Invalid indices.")
                            continue
                    elif sel == "c":
                        range_str = input("   Range (e.g. 1-10): ").strip()
                        try:
                            parts = range_str.split("-")
                            start, end = int(parts[0]), int(parts[1])
                            result = ProfileEnricherService.enrich_profiles_from_db(
                                driver, profile_range=(start, end),
                            )
                        except (ValueError, IndexError):
                            print("Invalid range.")
                            continue
                    else:
                        print("Invalid choice.")
                        continue

                    if result and result["success"]:
                        print(f"\n{result['message']}")
                        print("Results saved to database")
                    elif result:
                        print(f"\n{result['message']}")

                else:
                    csv_file = input("   CSV file path: ")
                    url_column = input("   URL column name [Profile URL]: ").strip() or "Profile URL"
                    max_profiles_input = input("   Max profiles [all]: ").strip()
                    max_profiles = int(max_profiles_input) if max_profiles_input else None

                    logger.info("Action 7: Profile enrichment | csv=%s max=%s", csv_file, max_profiles or "all")
                    result = ProfileEnricherService.enrich_profiles_from_csv(
                        driver, csv_file, url_column, max_profiles
                    )

                    if result["success"]:
                        print(f"\n{result['message']}")
                        print("Results saved to database")
                    else:
                        print(f"\n{result['message']}")

            elif action == "11":
                action_test_emails()

            elif action == "12":
                action_send_emails()

            elif action == "13":
                action_generate_cvs()

            elif action == "14":
                action_schedule_campaign()

            elif action == "15":
                action_manage_email_accounts()

            elif action == "16":
                action_run_scheduler()

            print("\n" + "-" * 40)
            input("Press Enter to continue...")

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        logger.info("CLI interrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
        logger.error("Unexpected error: %s", e, exc_info=True)
    finally:
        if driver:
            print("\nCleaning up...")
            logger.info("Shutting down browser")
            time.sleep(2)
            DriverManager.cleanup_driver(driver, temp_profile)
            print("Done!")


if __name__ == "__main__":
    main()
