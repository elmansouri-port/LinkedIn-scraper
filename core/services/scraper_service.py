"""
Scraper Service - Business logic for scraping operations
"""
from typing import Optional, Dict, Any, List
from scraper.group_scraper import scraper, get_scraping_mode
from actions.search_profiles import search_connections
from scraper.google_search_profile_scraper import GoogleLinkedInProfileScraper
import pandas as pd
import os


class ScraperService:
    """Service for all scraping operations"""
    
    @staticmethod
    def scrape_group_members(driver, group_url: str, max_members: Optional[int] = None, 
                            scraping_mode: str = "smart") -> Dict[str, Any]:
        """Scrape LinkedIn group members
        
        Args:
            driver: Selenium WebDriver instance
            group_url: URL of the LinkedIn group
            max_members: Maximum number of members to scrape (None for unlimited)
            scraping_mode: Scraping mode ('smart' or other)
            
        Returns:
            dict: Results containing total_scraped, status, and data_file path
        """
        try:
            total_scraped = scraper(driver, group_url, max_members, scraping_mode)
            
            return {
                "success": True,
                "total_scraped": total_scraped,
                "scraping_mode": scraping_mode,
                "max_members": max_members,
                "message": f"Successfully scraped {total_scraped} members"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Error during group scraping: {str(e)}"
            }
    
    @staticmethod
    def search_and_scrape_profiles(driver, keywords: str, max_profiles: int, 
                                   start_page: int = 1) -> Dict[str, Any]:
        """Search and scrape LinkedIn profiles
        
        Args:
            driver: Selenium WebDriver instance
            keywords: Search keywords
            max_profiles: Maximum number of profiles to scrape
            start_page: Starting page number
            
        Returns:
            dict: Results containing profiles_scraped, status, and data
        """
        try:
            result = search_connections(driver, keywords, max_profiles, start_page)
            
            return {
                "success": True,
                "keywords": keywords,
                "profiles_scraped": max_profiles,
                "start_page": start_page,
                "message": f"Successfully scraped profiles for '{keywords}'"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Error during profile search: {str(e)}"
            }
    
    @staticmethod
    def scrape_google_linkedin_profiles(driver, keywords: str, oblig_keywords: str,
                                        max_profiles: int, 
                                        max_profiles_per_keyword: int,
                                        duplicate_threshold: int = 3,
                                        max_pages_per_keyword: int = 10,
                                        verbose: bool = True) -> Dict[str, Any]:
        """Scrape LinkedIn profiles using Google search
        
        Args:
            driver: Selenium WebDriver instance
            keywords: Search keywords (comma-separated)
            oblig_keywords: Obligatory keywords (space-separated)
            max_profiles: Maximum total profiles to scrape
            max_profiles_per_keyword: Maximum profiles per keyword
            duplicate_threshold: (deprecated) - now uses ratio-based detection
            max_pages_per_keyword: Maximum pages to scrape per keyword (default: 10)
            verbose: Enable detailed logging (default: True)
            
        Returns:
            dict: Full result dict with profiles, stats, and metadata
        """
        try:
            result = GoogleLinkedInProfileScraper.scrape_google_linkedin_profiles(
                driver, keywords, oblig_keywords, max_profiles, max_profiles_per_keyword,
                duplicate_threshold, max_pages_per_keyword, verbose
            )
            
            # The scraper now returns a full dict — pass it through
            return {
                "success": result.get('success', False),
                "keywords": keywords,
                "oblig_keywords": oblig_keywords,
                "max_profiles": max_profiles,
                "max_profiles_per_keyword": max_profiles_per_keyword,
                "profiles_saved": result.get('profiles_saved', 0),
                "profiles": result.get('profiles', []),
                "stats": result.get('stats', {}),
                "db_path": result.get('db_path'),
                "message": f"Scraped {result.get('profiles_saved', 0)} profiles using Google search"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Error during Google-based scraping: {str(e)}"
            }
    
    @staticmethod
    def get_latest_scraped_data(data_type: str = "group") -> Optional[List[Dict]]:
        """Get the latest scraped data from CSV files
        
        Args:
            data_type: Type of data to retrieve ('group', 'search', 'google')
            
        Returns:
            list: List of dictionaries containing scraped data, or None if not found
        """
        try:
            data_dir = "./data"
            if not os.path.exists(data_dir):
                return None
            
            # Find the most recent CSV file based on data_type
            csv_files = [f for f in os.listdir(data_dir) if f.endswith('.csv')]
            if not csv_files:
                return None
            
            # Get the most recent file
            latest_file = max([os.path.join(data_dir, f) for f in csv_files], 
                            key=os.path.getctime)
            
            df = pd.read_csv(latest_file)
            return df.to_dict('records')
        except Exception as e:
            print(f"Error reading scraped data: {e}")
            return None
