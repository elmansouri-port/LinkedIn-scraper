"""
Connection Service - Business logic for connection operations
"""
from typing import Dict, Any, Optional
from actions.connection_sender import send_connection
from actions.mass_connections_sender import run_mass_connections


class ConnectionService:
    """Service for LinkedIn connection operations"""
    
    @staticmethod
    def send_single_connection(driver, profile_url: str, 
                              note_message: Optional[str] = None) -> Dict[str, Any]:
        """Send a single connection request
        
        Args:
            driver: Selenium WebDriver instance
            profile_url: LinkedIn profile URL
            note_message: Optional personal note
            
        Returns:
            dict: Results containing success status and message
        """
        try:
            send_connection(driver, profile_url, note_message)
            
            return {
                "success": True,
                "profile_url": profile_url,
                "note_included": bool(note_message),
                "message": f"Successfully sent connection request to {profile_url}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "profile_url": profile_url,
                "message": f"Error sending connection request: {str(e)}"
            }
    
    @staticmethod
    def send_mass_connections(driver, csv_file_path: str, 
                             note_message: Optional[str] = None,
                             use_note: bool = False) -> Dict[str, Any]:
        """Send mass connection requests from CSV file
        
        Args:
            driver: Selenium WebDriver instance
            csv_file_path: Path to CSV file with profile URLs
            note_message: Optional personal note
            use_note: Whether to include the note
            
        Returns:
            dict: Results containing success status, count, and message
        """
        try:
            result = run_mass_connections(driver, csv_file_path, note_message, use_note)
            
            return {
                "success": True,
                "csv_file": csv_file_path,
                "note_included": use_note,
                "message": "Successfully processed mass connection requests"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "csv_file": csv_file_path,
                "message": f"Error during mass connection sending: {str(e)}"
            }
