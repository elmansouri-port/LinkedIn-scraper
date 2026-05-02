"""
Profile Enricher v3.0
Enriches LinkedIn profiles with name, about, current company, domain, and generated emails.

Storage: SQLite database (core/database.py)
Input: CSV file with profile URLs
Output: enriched_profiles table + optional CSV/Excel export

Workflow:
1. Read profile URLs from CSV
2. Visit each profile → extract name, about, current company + title
3. Search Google for company domain
4. Generate email addresses using patterns
5. Save to SQLite enriched_profiles table
"""
import time
import csv
import os
from datetime import datetime
from typing import Dict, List, Optional

from .profile_scraper import scrape_profile_data
from .domain_finder import search_multiple_companies, load_cache
from .email_generator import (
    generate_emails_for_profile,
    generate_all_email_formats,
    generate_primary_email,
)
from core.database import save_enriched_profile, get_enriched_profile_urls

try:
    from utils.logger import ActionLogger
    LOGGER_AVAILABLE = True
except ImportError:
    LOGGER_AVAILABLE = False


class ProfileEnricher:
    """
    Profile Enricher v3.0 — SQLite-backed enrichment pipeline.
    """

    def __init__(self, driver, verbose: bool = True, all_formats: bool = True):
        self.driver = driver
        self.verbose = verbose
        self.all_formats = all_formats

        if LOGGER_AVAILABLE and verbose:
            self.logger = ActionLogger(
                "profile_enricher", "data/logs",
                console_output=True, file_output=True, verbose=verbose,
            )
        else:
            self.logger = None

        self.stats = {
            "total": 0,
            "enriched": 0,
            "failed": 0,
            "no_company": 0,
            "no_domain": 0,
            "emails_generated": 0,
            "skipped_already_enriched": 0,
        }

        load_cache()

    def log(self, message: str, level: str = "info"):
        if self.logger:
            getattr(self.logger, level)(message)
        elif self.verbose or level in ("error", "warning", "success"):
            print(message)

    def process_profile(self, profile_url: str, index: int, total: int) -> Dict:
        """Process a single profile and save to database."""
        self.log(f"\n[{index}/{total}] Processing...", "info")

        try:
            # Step 1: Scrape LinkedIn profile
            self.log("  Extracting profile data...", "debug")
            profile_data = scrape_profile_data(self.driver, profile_url)

            first_name = profile_data.get("first_name", "")
            last_name = profile_data.get("last_name", "")
            full_name = profile_data.get("full_name", "")
            about_text = profile_data.get("about", "")
            experiences = profile_data.get("experiences", [])
            education = profile_data.get("education", [])
            current_company = profile_data.get("current_company", "")
            current_job_title = profile_data.get("current_job_title", "")

            self.log(f"  Name: {full_name}", "info")
            self.log(f"  Current: {current_job_title} at {current_company}", "info")
            self.log(f"  Experiences: %d", len(experiences), "info")
            if education:
                self.log(f"  Education: %d", len(education), "info")

            if not current_company:
                self.log("  No current company found", "warning")
                save_enriched_profile(
                    profile_url=profile_url,
                    first_name=first_name, last_name=last_name, full_name=full_name,
                    about_text=about_text,
                    experiences=experiences, education=education,
                    status="no_company",
                    error_message="No current company in experience section",
                )
                self.stats["no_company"] += 1
                return {"status": "no_company", "url": profile_url}

            # Step 2: Search for company domain
            self.log(f"  Searching domain for '{current_company}'...", "debug")
            company_domains = search_multiple_companies(
                self.driver, [current_company], delay=1.0,
            )
            domain = list(company_domains.values())[0] if company_domains else None

            if not domain:
                self.log("  No domain found", "warning")
                save_enriched_profile(
                    profile_url=profile_url,
                    first_name=first_name, last_name=last_name, full_name=full_name,
                    about_text=about_text,
                    experiences=experiences, education=education,
                    current_company=current_company, current_job_title=current_job_title,
                    status="no_domain",
                    error_message="Could not find company domain",
                )
                self.stats["no_domain"] += 1
                return {"status": "no_domain", "url": profile_url}

            self.log(f"  Domain: {domain}", "info")

            # Step 3: Generate email addresses
            self.log("  Generating emails...", "debug")

            primary_email = generate_primary_email(first_name, last_name, domain)
            primary_email = primary_email or ""

            all_variants = []
            if self.all_formats:
                variations = generate_all_email_formats(first_name, last_name, domain, max_emails=5)
                all_variants = [v["email"] for v in variations]

            if primary_email:
                self.log(f"  Primary: {primary_email}", "success")
                self.stats["emails_generated"] += 1

            # Step 4: Save to database
            save_enriched_profile(
                profile_url=profile_url,
                first_name=first_name, last_name=last_name, full_name=full_name,
                about_text=about_text,
                experiences=experiences, education=education,
                current_company=current_company, current_job_title=current_job_title,
                current_company_domain=domain,
                generated_email=primary_email,
                all_email_variants=all_variants if all_variants else None,
                status="success",
            )

            self.stats["enriched"] += 1
            return {"status": "success", "url": profile_url, "email": primary_email}

        except Exception as e:
            self.log(f"  Error: {e}", "error")
            save_enriched_profile(
                profile_url=profile_url,
                status="error", error_message=str(e),
            )
            self.stats["failed"] += 1
            return {"status": "error", "url": profile_url, "error": str(e)}

    def read_profile_urls_from_csv(self, csv_file_path: str, url_column: str) -> List[str]:
        """Read profile URLs from a CSV file."""
        if not os.path.exists(csv_file_path):
            raise FileNotFoundError(f"CSV file not found: {csv_file_path}")

        urls = []
        with open(csv_file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if url_column not in reader.fieldnames:
                available = ", ".join(reader.fieldnames)
                raise ValueError(
                    f"Column '{url_column}' not found. Available: {available}"
                )
            for row in reader:
                url = row.get(url_column, "").strip()
                if url:
                    urls.append(url)
        return urls

    def enrich_from_csv(self, csv_file_path: str, url_column: str = "Profile URL",
                        max_profiles: Optional[int] = None) -> Dict:
        """Enrich profiles from CSV, store in SQLite."""
        start_time = datetime.now()

        self.log("=" * 50, "info")
        self.log("PROFILE ENRICHER v3.0 (SQLite)", "info")
        self.log("=" * 50, "info")

        try:
            # Read URLs
            self.log(f"Reading: {csv_file_path}", "info")
            urls = self.read_profile_urls_from_csv(csv_file_path, url_column)
            if not urls:
                return {"success": False, "message": "No profile URLs found in CSV"}

            self.log(f"Found {len(urls)} profiles", "info")

            # Skip already enriched
            enriched_urls = get_enriched_profile_urls()
            original_count = len(urls)
            urls = [u for u in urls if u not in enriched_urls]
            skipped = original_count - len(urls)
            self.stats["skipped_already_enriched"] = skipped
            if skipped > 0:
                self.log(f"Skipping {skipped} already enriched profiles", "info")

            if max_profiles:
                urls = urls[:max_profiles]
                self.log(f"Processing {len(urls)} profiles", "info")

            self.stats["total"] = len(urls)
            self.log("-" * 50, "info")

            # Process each profile
            for i, url in enumerate(urls):
                result = self.process_profile(url, i + 1, len(urls))
                if i < len(urls) - 1:
                    time.sleep(2)

            # Summary
            duration = datetime.now() - start_time
            duration_str = str(duration).split(".")[0]

            self.log("=" * 50, "info")
            self.log(f"COMPLETED in {duration_str}", "success")
            self.log("=" * 50, "info")
            self.log("  Enriched: %d", self.stats["enriched"])
            self.log("  Failed: %d", self.stats["failed"])
            self.log("  No company: %d", self.stats["no_company"])
            self.log("  No domain: %d", self.stats["no_domain"])
            self.log("  Emails generated: %d", self.stats["emails_generated"])

            if self.logger:
                self.logger.close()

            return {
                "success": True,
                "message": f"Enriched {self.stats['enriched']}/{self.stats['total']} profiles",
                "stats": self.stats,
            }

        except Exception as e:
            self.log(f"Fatal error: {e}", "error")
            if self.logger:
                self.logger.close()
            return {"success": False, "message": f"Error: {e}"}


def enrich_profiles(driver, csv_file_path: str, url_column_name: str = "Profile URL",
                    max_profiles: Optional[int] = None, verbose: bool = True,
                    all_formats: bool = True) -> Dict:
    """Main entry point (backward compatible)."""
    enricher = ProfileEnricher(driver, verbose=verbose, all_formats=all_formats)
    return enricher.enrich_from_csv(csv_file_path, url_column_name, max_profiles)
