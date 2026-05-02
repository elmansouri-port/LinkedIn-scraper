"""
Messaging Service - Business logic for messaging operations.
"""
import logging
from typing import Dict, Any

from actions.group_outreach import message_all_group_members

logger = logging.getLogger(__name__)


class MessagingService:
    """Service for LinkedIn messaging operations."""

    @staticmethod
    def send_group_messages(driver) -> Dict[str, Any]:
        """Send messages to all group members."""
        logger.info("Starting messaging campaign")

        try:
            message_all_group_members(driver)
            logger.success("Messaging campaign complete")
            return {
                "success": True,
                "message": "Successfully sent messages to group members",
            }
        except Exception as e:
            logger.error("Messaging campaign failed: %s", e, exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "message": f"Error during messaging campaign: {str(e)}",
            }
