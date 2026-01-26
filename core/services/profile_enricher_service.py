"""
Profile Enricher Service
Service layer interface for profile enrichment functionality
"""
from scraper.profile_enricher import enrich_profiles


class ProfileEnricherService:
    """Service for enriching LinkedIn profiles with email addresses"""
    
    @staticmethod
    def enrich_profiles_from_csv(driver, csv_file_path, url_column_name='Profile URL', max_profiles=None):
        """
        Enrich LinkedIn profiles from CSV file
        
        Args:
            driver: Selenium WebDriver instance
            csv_file_path: Path to CSV file containing profile URLs
            url_column_name: Name of column containing LinkedIn URLs (default: 'Profile URL')
            max_profiles: Maximum number of profiles to process (None = all)
            
        Returns:
            Dictionary with results:
            {
                'success': bool,
                'message': str,
                'enriched_count': int,
                'failed_count': int,
                'output_file': str
            }
        """
        try:
            result = enrich_profiles(
                driver, 
                csv_file_path, 
                url_column_name,
                max_profiles
            )
            return result
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error during profile enrichment: {str(e)}',
                'enriched_count': 0,
                'failed_count': 0,
                'output_file': None
            }
