"""
Profile Enricher Main Orchestration
Coordinates the entire profile enrichment workflow
"""
import time
import logging
from .csv_processor import (
    read_profiles_csv, 
    create_output_file, 
    save_enriched_profile,
    load_enriched_profiles
)
from .profile_scraper import scrape_profile_data
from .domain_finder import search_multiple_companies
from .email_generator import generate_emails_for_profile


def enrich_profiles(driver, csv_file_path, url_column_name='Profile URL', max_profiles=None):
    """
    Main entry point for profile enrichment
    
    Workflow:
    1. Read CSV file with profile URLs
    2. For each profile:
       - Visit LinkedIn profile
       - Extract name and companies
       - Search Google for company domains
       - Generate email addresses
       - Save enriched data
    3. Handle errors gracefully
    
    Args:
        driver: Selenium WebDriver instance
        csv_file_path: Path to input CSV file
        url_column_name: Column name containing LinkedIn URLs
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
    print("=" * 60)
    print("🚀 PROFILE ENRICHER - Starting")
    print("=" * 60)
    
    enriched_count = 0
    failed_count = 0
    output_file = None
    
    try:
        # Step 1: Read input CSV
        print(f"\n📂 Reading input CSV: {csv_file_path}")
        profiles = read_profiles_csv(csv_file_path, url_column_name)
        print(f"✓ Found {len(profiles)} profiles to enrich")
        
        if not profiles:
            return {
                'success': False,
                'message': 'No profiles found in CSV file',
                'enriched_count': 0,
                'failed_count': 0,
                'output_file': None
            }
        
        # Limit profiles if specified
        if max_profiles:
            profiles = profiles[:max_profiles]
            print(f"📊 Processing first {max_profiles} profiles")
        
        # Step 2: Create output file
        output_file = create_output_file(csv_file_path)
        print(f"📝 Output file: {output_file}")
        
        # Step 3: Process each profile
        for i, profile in enumerate(profiles):
            print(f"\n{'=' * 60}")
            print(f"[{i+1}/{len(profiles)}] Processing profile")
            print(f"{'=' * 60}")
            
            profile_url = profile['url']
            print(f"🔗 URL: {profile_url}")
            
            enriched_data = {
                'url': profile_url,
                'first_name': '',
                'last_name': '',
                'full_name': '',
                'companies': [],
                'domains': [],
                'emails': [],
                'status': 'Failed',
                'error': ''
            }
            
            try:
                # 3.1: Scrape LinkedIn profile
                print("\n📋 Step 1: Extracting profile data from LinkedIn...")
                profile_data = scrape_profile_data(driver, profile_url)
                
                enriched_data['first_name'] = profile_data.get('first_name', '')
                enriched_data['last_name'] = profile_data.get('last_name', '')
                enriched_data['full_name'] = profile_data.get('full_name', '')
                enriched_data['companies'] = profile_data.get('companies', [])
                
                print(f"✓ Name: {enriched_data['full_name']}")
                print(f"✓ Companies found: {len(enriched_data['companies'])}")
                
                if not enriched_data['companies']:
                    print("⚠️ No companies found in experience section")
                    enriched_data['status'] = 'No Companies'
                    enriched_data['error'] = 'No companies found in experience section'
                else:
                    # 3.2: Search for company domains
                    print("\n🔍 Step 2: Searching for company domains on Google...")
                    company_domains = search_multiple_companies(driver, enriched_data['companies'])
                    
                    # Extract just the domains
                    domains = [domain for domain in company_domains.values() if domain]
                    enriched_data['domains'] = domains
                    
                    print(f"\n✓ Domains found: {len(domains)}")
                    for company, domain in company_domains.items():
                        if domain:
                            print(f"  • {company} → {domain}")
                    
                    # 3.3: Generate email addresses
                    if domains:
                        print("\n📧 Step 3: Generating email addresses...")
                        emails = generate_emails_for_profile(
                            enriched_data['first_name'],
                            enriched_data['last_name'],
                            domains
                        )
                        enriched_data['emails'] = emails
                        
                        print(f"✓ Generated {len(emails)} email addresses:")
                        for email in emails:
                            print(f"  • {email}")
                        
                        enriched_data['status'] = 'Success'
                    else:
                        print("⚠️ No domains found, cannot generate emails")
                        enriched_data['status'] = 'No Domains'
                        enriched_data['error'] = 'Could not find company domains'
                
                enriched_count += 1
                
            except Exception as e:
                error_msg = str(e)
                print(f"\n❌ Error processing profile: {error_msg}")
                enriched_data['status'] = 'Error'
                enriched_data['error'] = error_msg
                failed_count += 1
            
            # Save to CSV (incremental)
            is_first = (i == 0)
            save_enriched_profile(output_file, enriched_data, is_first=is_first)
            
            # Add delay between profiles to avoid rate limiting
            if i < len(profiles) - 1:
                delay = 5
                print(f"\n⏸️  Waiting {delay}s before next profile...")
                time.sleep(delay)
        
        # Final summary
        print("\n" + "=" * 60)
        print("✅ ENRICHMENT COMPLETE")
        print("=" * 60)
        print(f"✓ Successfully enriched: {enriched_count}")
        print(f"✗ Failed: {failed_count}")
        print(f"📁 Output saved to: {output_file}")
        
        return {
            'success': True,
            'message': f'Enriched {enriched_count} profiles ({failed_count} failed)',
            'enriched_count': enriched_count,
            'failed_count': failed_count,
            'output_file': output_file
        }
        
    except Exception as e:
        error_msg = f"Fatal error during enrichment: {str(e)}"
        print(f"\n❌ {error_msg}")
        
        return {
            'success': False,
            'message': error_msg,
            'enriched_count': enriched_count,
            'failed_count': failed_count,
            'output_file': output_file
        }
