"""
Scraper Service - Business logic for scraping operations.
"""
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

import pandas as pd

from scraper.group_scraper import scraper
from actions.search_profiles import search_connections
from scraper.google_search_profile_scraper import GoogleLinkedInProfileScraper

logger = logging.getLogger(__name__)


class ScraperService:
    """Service for all scraping operations."""

    @staticmethod
    def scrape_group_members(
        driver,
        group_url: str,
        max_members: Optional[int] = None,
        scraping_mode: str = "smart",
    ) -> Dict[str, Any]:
        """Scrape LinkedIn group members."""
        if not group_url:
            logger.error("group_url is empty")
            return {
                "success": False,
                "error": "group_url is required",
                "message": "Group URL is required",
            }

        logger.info(
            "Starting group scrape | url=%s max_members=%s mode=%s",
            group_url, max_members, scraping_mode,
        )

        try:
            total_scraped = scraper(driver, group_url, max_members, scraping_mode)
            logger.success("Group scrape complete | scraped=%d", total_scraped)
            return {
                "success": True,
                "total_scraped": total_scraped,
                "scraping_mode": scraping_mode,
                "max_members": max_members,
                "message": f"Successfully scraped {total_scraped} members",
            }
        except Exception as e:
            logger.error("Group scrape failed: %s", e, exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "message": f"Error during group scraping: {str(e)}",
            }

    @staticmethod
    def search_and_scrape_profiles(
        driver, keywords: str, max_profiles: int, start_page: int = 1
    ) -> Dict[str, Any]:
        """Search and scrape LinkedIn profiles."""
        if max_profiles <= 0:
            logger.error("max_profiles must be positive, got %d", max_profiles)
            return {
                "success": False,
                "error": "max_profiles must be positive",
                "message": "max_profiles must be a positive integer",
            }

        logger.info(
            "Starting profile search | keywords='%s' max_profiles=%d start_page=%d",
            keywords, max_profiles, start_page,
        )

        try:
            result = search_connections(driver, keywords, max_profiles, start_page)
            actual_count = result.get("total", max_profiles) if isinstance(result, dict) else max_profiles
            logger.success("Profile search complete | profiles=%d", actual_count)
            return {
                "success": True,
                "keywords": keywords,
                "profiles_scraped": actual_count,
                "start_page": start_page,
                "message": f"Successfully scraped {actual_count} profiles for '{keywords}'",
            }
        except Exception as e:
            logger.error("Profile search failed: %s", e, exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "message": f"Error during profile search: {str(e)}",
            }

    @staticmethod
    def scrape_google_linkedin_profiles(
        driver,
        keywords: str,
        oblig_keywords: str,
        max_profiles: int,
        max_profiles_per_keyword: int,
        duplicate_threshold: int = 3,
        max_pages_per_keyword: int = 10,
        verbose: bool = True,
    ) -> Dict[str, Any]:
        """Scrape LinkedIn profiles using Google search."""
        logger.info(
            "Starting Google-based scrape | keywords='%s' oblig='%s' max=%d per_kw=%d",
            keywords, oblig_keywords, max_profiles, max_profiles_per_keyword,
        )

        try:
            result = GoogleLinkedInProfileScraper.scrape_google_linkedin_profiles(
                driver,
                keywords,
                oblig_keywords,
                max_profiles,
                max_profiles_per_keyword,
                duplicate_threshold,
                max_pages_per_keyword,
                verbose,
            )

            saved = result.get("profiles_saved", 0)
            if result.get("success"):
                logger.success("Google scrape complete | profiles=%d", saved)
            else:
                logger.warning("Google scrape finished with issues | profiles=%d", saved)

            return {
                "success": result.get("success", False),
                "keywords": keywords,
                "oblig_keywords": oblig_keywords,
                "max_profiles": max_profiles,
                "max_profiles_per_keyword": max_profiles_per_keyword,
                "profiles_saved": saved,
                "profiles": result.get("profiles", []),
                "stats": result.get("stats", {}),
                "db_path": result.get("db_path"),
                "message": f"Scraped {saved} profiles using Google search",
            }
        except Exception as e:
            logger.error("Google-based scrape failed: %s", e, exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "message": f"Error during Google-based scraping: {str(e)}",
            }

    @staticmethod
    def get_latest_scraped_data(data_type: str = "group") -> Optional[List[Dict]]:
        """Get the latest scraped data from CSV files."""
        try:
            csv_dir = Path("data/csv")
            if not csv_dir.exists():
                logger.debug("No data directory found")
                return None

            csv_files = list(csv_dir.glob("*.csv"))
            if not csv_files:
                logger.debug("No CSV files found")
                return None

            latest_file = max(csv_files, key=lambda f: f.stat().st_mtime)
            logger.debug("Reading latest CSV: %s", latest_file.name)

            df = pd.read_csv(latest_file)
            return df.to_dict("records")
        except Exception as e:
            logger.error("Error reading scraped data: %s", e)
            return None
