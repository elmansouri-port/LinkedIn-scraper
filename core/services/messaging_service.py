"""
Messaging Service - Business logic for messaging operations
"""
from typing import Dict, Any
from actions.group_outreach import message_all_group_members


class MessagingService:
    """Service for LinkedIn messaging operations"""
    
    @staticmethod
    def send_group_messages(driver) -> Dict[str, Any]:
        """Send messages to all group members
        
        Args:
            driver: Selenium WebDriver instance
            
        Returns:
            dict: Results containing success status and message
        """
        try:
            message_all_group_members(driver)
            
            return {
                "success": True,
                "message": "Successfully sent messages to group members"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Error during messaging campaign: {str(e)}"
            }
