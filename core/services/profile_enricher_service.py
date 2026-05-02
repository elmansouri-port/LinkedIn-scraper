"""
Profile Enricher Service - Business logic for profile enrichment.
"""
import logging
import os
from typing import Any, Dict, Optional

from scraper.profile_enricher import enrich_profiles

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
