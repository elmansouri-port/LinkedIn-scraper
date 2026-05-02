"""
Connection Service - Business logic for connection operations.
"""
import logging
from typing import Dict, Any, Optional

from actions.connection_sender import send_connection
from actions.mass_connections_sender import run_mass_connections

logger = logging.getLogger(__name__)


class ConnectionService:
    """Service for LinkedIn connection operations."""

    @staticmethod
    def send_single_connection(
        driver,
        profile_url: str,
        note_message: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a single connection request."""
        if not profile_url:
            logger.error("profile_url is empty")
            return {
                "success": False,
                "error": "profile_url is required",
                "message": "Profile URL is required",
            }

        logger.info(
            "Sending connection request | url=%s note=%s",
            profile_url, bool(note_message),
        )

        try:
            send_connection(driver, profile_url, note_message)
            logger.success("Connection request sent | url=%s", profile_url)
            return {
                "success": True,
                "profile_url": profile_url,
                "note_included": bool(note_message),
                "message": f"Successfully sent connection request to {profile_url}",
            }
        except Exception as e:
            logger.error("Failed to send connection: %s", e, exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "profile_url": profile_url,
                "message": f"Error sending connection request: {str(e)}",
            }

    @staticmethod
    def send_mass_connections(
        driver,
        csv_file_path: str,
        note_message: Optional[str] = None,
        use_note: bool = False,
    ) -> Dict[str, Any]:
        """Send mass connection requests from CSV file."""
        if not csv_file_path:
            logger.error("csv_file_path is empty")
            return {
                "success": False,
                "error": "csv_file_path is required",
                "message": "CSV file path is required",
            }

        logger.info(
            "Starting mass connections | csv=%s note=%s",
            csv_file_path, use_note,
        )

        try:
            result = run_mass_connections(driver, csv_file_path, note_message, use_note)
            logger.success("Mass connections complete | csv=%s", csv_file_path)
            return {
                "success": True,
                "csv_file": csv_file_path,
                "note_included": use_note,
                "message": "Successfully processed mass connection requests",
            }
        except Exception as e:
            logger.error("Mass connections failed: %s", e, exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "csv_file": csv_file_path,
                "message": f"Error during mass connection sending: {str(e)}",
            }
