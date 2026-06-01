"""
Profile Enricher Service - Business logic for profile enrichment.
"""
import logging
import os
from typing import Any, Dict, List, Optional

from scraper.profile_enricher import enrich_profiles
from scraper.profile_enricher.enricher import ProfileEnricher
from core.database import get_search_profiles_not_enriched

logger = logging.getLogger(__name__)


class ProfileEnricherService:
    """Service for enriching LinkedIn profiles with email addresses."""

    @staticmethod
    def enrich_profiles_from_csv(
        driver,
        csv_file_path: str,
        url_column_name: str = "Profile URL",
        max_profiles: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Enrich LinkedIn profiles from CSV file."""
        if not csv_file_path:
            logger.error("csv_file_path is empty")
            return {
                "success": False,
                "message": "CSV file path is required",
                "enriched_count": 0,
                "failed_count": 0,
                "output_file": None,
            }

        if not os.path.exists(csv_file_path):
            logger.error("CSV file not found: %s", csv_file_path)
            return {
                "success": False,
                "message": f"CSV file not found: {csv_file_path}",
                "enriched_count": 0,
                "failed_count": 0,
                "output_file": None,
            }

        logger.info(
            "Starting profile enrichment | csv=%s column=%s max=%s",
            csv_file_path, url_column_name, max_profiles or "all",
        )

        try:
            result = enrich_profiles(driver, csv_file_path, url_column_name, max_profiles)
            stats = result.get("stats", {})
            enriched = stats.get("enriched", 0)
            failed = stats.get("failed", 0)
            logger.success(
                "Profile enrichment complete | enriched=%d failed=%d",
                enriched, failed,
            )
            return {
                "success": result.get("success", False),
                "message": result.get("message", ""),
                "enriched_count": enriched,
                "failed_count": failed,
                "output_file": None,
                "stats": stats,
            }
        except Exception as e:
            logger.error("Profile enrichment failed: %s", e, exc_info=True)
            return {
                "success": False,
                "message": f"Error during profile enrichment: {str(e)}",
                "enriched_count": 0,
                "failed_count": 0,
                "output_file": None,
            }

    @staticmethod
    def enrich_profiles_from_db(
        driver,
        profile_indices: Optional[List[int]] = None,
        profile_range: Optional[tuple] = None,
        max_profiles: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Enrich profiles from the search_profiles table.

        Args:
            driver: Selenium WebDriver
            profile_indices: Specific 1-based indices of profiles to enrich
            profile_range: (start, end) 1-based range
            max_profiles: Max profiles if enriching all

        Returns:
            Result dict
        """
        profiles = get_search_profiles_not_enriched()
        if not profiles:
            return {"success": False, "message": "No unenriched scraped profiles found."}

        if profile_range:
            start, end = profile_range
            profiles = profiles[start - 1 : end]

        elif profile_indices is not None:
            profiles = [profiles[i - 1] for i in profile_indices if 1 <= i <= len(profiles)]

        elif max_profiles:
            profiles = profiles[:max_profiles]

        urls = [p["profile_url"] for p in profiles]

        if not urls:
            return {"success": False, "message": "No profiles match the selection."}

        logger.info("Enriching %d profiles from database", len(urls))

        try:
            enricher = ProfileEnricher(driver, verbose=True, all_formats=True)
            result = enricher.enrich_from_urls(urls)
            stats = result.get("stats", {})
            return {
                "success": result.get("success", False),
                "message": result.get("message", ""),
                "enriched_count": stats.get("enriched", 0),
                "failed_count": stats.get("failed", 0),
                "stats": stats,
            }
        except Exception as e:
            logger.error("Profile enrichment from DB failed: %s", e, exc_info=True)
            return {
                "success": False,
                "message": f"Error: {str(e)}",
                "enriched_count": 0,
                "failed_count": 0,
            }
