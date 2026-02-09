"""
Profile Enricher v2.0
Optimized profile enrichment with multiple email formats and faster processing.

Features:
- Multiple email format generation (top 3-5 patterns)
- Persistent domain caching
- Reduced delays for faster processing
- Better error handling and progress tracking
- Per-action logging
"""
import time
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional

# Add parent path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from .csv_processor import (
    read_profiles_csv, 
    create_output_file, 
    save_enriched_profile,
)
from .profile_scraper import scrape_profile_data
from .domain_finder import search_multiple_companies, load_cache
from .email_generator import (
    generate_emails_for_profile,
    generate_all_email_formats,
    generate_primary_email
)

# Try to import logger
try:
    from utils.logger import ActionLogger
    LOGGER_AVAILABLE = True
except ImportError:
    LOGGER_AVAILABLE = False


class ProfileEnricher:
    """
    Profile Enricher v2.0 - Extracts emails from LinkedIn profiles.
    
    Workflow:
    1. Read CSV with LinkedIn profile URLs
    2. Visit each profile to extract name and companies
    3. Search Google for company domains (with caching)
    4. Generate email addresses using multiple patterns
    5. Save enriched data to output CSV
    """
    
    def __init__(self, driver, verbose: bool = True, all_formats: bool = True):
        """
        Initialize enricher.
        
        Args:
            driver: Selenium WebDriver
            verbose: Enable detailed logging
            all_formats: Generate multiple email formats (vs just primary)
        """
        self.driver = driver
        self.verbose = verbose
        self.all_formats = all_formats
        
        # Initialize logger
        if LOGGER_AVAILABLE and verbose:
            self.logger = ActionLogger(
                "profile_enricher",
                "data/logs",
                console_output=True,
                file_output=True,
                verbose=verbose
            )
        else:
            self.logger = None
        
        # Statistics
        self.stats = {
            'total': 0,
            'enriched': 0,
            'failed': 0,
            'no_companies': 0,
            'no_domains': 0,
            'emails_generated': 0
        }
        
        # Load domain cache
        load_cache()
    
    def log(self, message: str, level: str = "info"):
        """Log message"""
        if self.logger:
            getattr(self.logger, level)(message)
        elif self.verbose or level in ["error", "warning", "success"]:
            print(message)
    
    def process_profile(self, profile_url: str, index: int, total: int) -> Dict:
        """
        Process a single profile.
        
        Args:
            profile_url: LinkedIn profile URL
            index: Current index (1-based)
            total: Total profiles
            
        Returns:
            Enriched data dictionary
        """
        self.log(f"\n[{index}/{total}] Processing...", "info")
        self.log(f"URL: {profile_url}", "debug")
        
        enriched_data = {
            'url': profile_url,
            'first_name': '',
            'last_name': '',
            'full_name': '',
            'companies': [],
            'domains': [],
            'emails': [],
            'all_emails': [],  # All format variations
            'status': 'Failed',
            'error': ''
        }
        
        try:
            # Step 1: Scrape LinkedIn profile
            self.log("  📋 Extracting profile data...", "debug")
            profile_data = scrape_profile_data(self.driver, profile_url)
            
            enriched_data['first_name'] = profile_data.get('first_name', '')
            enriched_data['last_name'] = profile_data.get('last_name', '')
            enriched_data['full_name'] = profile_data.get('full_name', '')
            enriched_data['companies'] = profile_data.get('companies', [])
            
            self.log(f"  Name: {enriched_data['full_name']}", "info")
            self.log(f"  Companies: {len(enriched_data['companies'])}", "debug")
            
            if not enriched_data['companies']:
                self.log("  ⚠️ No companies found", "warning")
                enriched_data['status'] = 'No Companies'
                enriched_data['error'] = 'No companies in experience section'
                self.stats['no_companies'] += 1
                return enriched_data
            
            # Step 2: Search for company domains
            self.log("  🔍 Searching domains...", "debug")
            company_domains = search_multiple_companies(
                self.driver, 
                enriched_data['companies'],
                delay=1.0  # Reduced delay
            )
            
            domains = list(company_domains.values())
            enriched_data['domains'] = domains
            
            if not domains:
                self.log("  ⚠️ No domains found", "warning")
                enriched_data['status'] = 'No Domains'
                enriched_data['error'] = 'Could not find company domains'
                self.stats['no_domains'] += 1
                return enriched_data
            
            self.log(f"  Domains: {domains}", "debug")
            
            # Step 3: Generate email addresses
            self.log("  📧 Generating emails...", "debug")
            
            # Primary emails (one per domain)
            primary_emails = generate_emails_for_profile(
                enriched_data['first_name'],
                enriched_data['last_name'],
                domains,
                all_formats=False
            )
            enriched_data['emails'] = primary_emails
            
            # All format variations (if enabled)
            if self.all_formats:
                all_emails = []
                for domain in domains:
                    variations = generate_all_email_formats(
                        enriched_data['first_name'],
                        enriched_data['last_name'],
                        domain,
                        max_emails=3
                    )
                    all_emails.extend([v['email'] for v in variations])
                enriched_data['all_emails'] = all_emails
            
            # Log generated emails
            for email in primary_emails:
                self.log(f"  ✓ {email}", "success")
            
            self.stats['emails_generated'] += len(primary_emails)
            enriched_data['status'] = 'Success'
            self.stats['enriched'] += 1
            
            return enriched_data
            
        except Exception as e:
            self.log(f"  ❌ Error: {e}", "error")
            enriched_data['status'] = 'Error'
            enriched_data['error'] = str(e)
            self.stats['failed'] += 1
            return enriched_data
    
    def enrich_from_csv(self, csv_file_path: str, url_column: str = 'Profile URL',
                        max_profiles: Optional[int] = None) -> Dict:
        """
        Enrich profiles from a CSV file.
        
        Args:
            csv_file_path: Path to input CSV
            url_column: Column name with LinkedIn URLs
            max_profiles: Maximum profiles to process (None = all)
            
        Returns:
            Results dictionary
        """
        start_time = datetime.now()
        
        self.log("=" * 50, "info")
        self.log("PROFILE ENRICHER v2.0", "info")
        self.log("=" * 50, "info")
        
        try:
            # Read input CSV
            self.log(f"Reading: {csv_file_path}", "info")
            profiles = read_profiles_csv(csv_file_path, url_column)
            
            if not profiles:
                return {
                    'success': False,
                    'message': 'No profiles found in CSV',
                    'output_file': None
                }
            
            self.log(f"Found {len(profiles)} profiles", "info")
            
            # Limit if specified
            if max_profiles:
                profiles = profiles[:max_profiles]
                self.log(f"Processing first {max_profiles}", "info")
            
            self.stats['total'] = len(profiles)
            
            # Create output file
            output_file = create_output_file(csv_file_path)
            self.log(f"Output: {output_file}", "info")
            self.log("-" * 50, "info")
            
            # Process each profile
            for i, profile in enumerate(profiles):
                enriched = self.process_profile(profile['url'], i + 1, len(profiles))
                
                # Save incrementally
                save_enriched_profile(output_file, enriched, is_first=(i == 0))
                
                # Delay between profiles
                if i < len(profiles) - 1:
                    time.sleep(2)  # Reduced from 5
            
            # Summary
            duration = datetime.now() - start_time
            
            self.log("=" * 50, "info")
            self.log(f"COMPLETED in {duration}", "success")
            self.log("=" * 50, "info")
            
            if self.logger:
                self.logger.log_stats({
                    'Total profiles': self.stats['total'],
                    'Enriched': self.stats['enriched'],
                    'Failed': self.stats['failed'],
                    'No companies': self.stats['no_companies'],
                    'No domains': self.stats['no_domains'],
                    'Emails generated': self.stats['emails_generated']
                })
                self.logger.close()
            
            return {
                'success': True,
                'message': f"Enriched {self.stats['enriched']}/{self.stats['total']} profiles",
                'output_file': output_file,
                'stats': self.stats
            }
            
        except Exception as e:
            self.log(f"Fatal error: {e}", "error")
            if self.logger:
                self.logger.close()
            
            return {
                'success': False,
                'message': f"Error: {e}",
                'output_file': None
            }


def enrich_profiles(driver, csv_file_path: str, url_column_name: str = 'Profile URL',
                    max_profiles: Optional[int] = None, verbose: bool = True,
                    all_formats: bool = True) -> Dict:
    """
    Main entry point for profile enrichment (backward compatible).
    
    Args:
        driver: Selenium WebDriver
        csv_file_path: Path to input CSV
        url_column_name: Column with LinkedIn URLs
        max_profiles: Max profiles to process
        verbose: Enable detailed logging
        all_formats: Generate multiple email formats
        
    Returns:
        Results dictionary
    """
    enricher = ProfileEnricher(driver, verbose=verbose, all_formats=all_formats)
    return enricher.enrich_from_csv(csv_file_path, url_column_name, max_profiles)
