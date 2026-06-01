"""
CSV Processor for Profile Enricher
Handles reading input CSV and saving enriched data
"""
import csv
import os
from datetime import datetime


def read_profiles_csv(file_path, url_column_name='Profile URL'):
    """
    Read LinkedIn profile URLs from CSV file
    
    Args:
        file_path: Path to input CSV file
        url_column_name: Name of column containing profile URLs
        
    Returns:
        List of dictionaries with profile data
    """
    profiles = []
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"CSV file not found: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        # Validate column exists
        if url_column_name not in reader.fieldnames:
            available_columns = ', '.join(reader.fieldnames)
            raise ValueError(
                f"Column '{url_column_name}' not found in CSV. "
                f"Available columns: {available_columns}"
            )
        
        for row in reader:
            profile_url = row.get(url_column_name, '').strip()
            if profile_url:
                profiles.append({
                    'url': profile_url,
                    'original_data': row
                })
    
    return profiles


def create_output_file(input_filename):
    """
    Create timestamped output CSV file path
    
    Args:
        input_filename: Original input file name
        
    Returns:
        Path to output CSV file
    """
    # Ensure data/csv directory exists
    output_dir = "data/csv"
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Extract base filename without extension
    base_name = os.path.splitext(os.path.basename(input_filename))[0]
    
    # Create output filename
    output_filename = f"{base_name}_enriched_{timestamp}.csv"
    output_path = os.path.join(output_dir, output_filename)
    
    return output_path


def save_enriched_profile(output_file, profile_data, is_first=False):
    """
    Save enriched profile data to CSV file (incremental save)
    
    Args:
        output_file: Path to output CSV file
        profile_data: Dictionary containing enriched profile data
        is_first: Whether this is the first row (creates file with headers)
    """
    fieldnames = [
        'Profile URL',
        'First Name',
        'Last Name',
        'Full Name',
        'Companies',
        'Domains',
        'Generated Emails',
        'Status',
        'Error Message'
    ]
    
    mode = 'w' if is_first else 'a'
    
    with open(output_file, mode, newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        if is_first:
            writer.writeheader()
        
        # Prepare row data
        row = {
            'Profile URL': profile_data.get('url', ''),
            'First Name': profile_data.get('first_name', ''),
            'Last Name': profile_data.get('last_name', ''),
            'Full Name': profile_data.get('full_name', ''),
            'Companies': '; '.join(profile_data.get('companies', [])),
            'Domains': '; '.join(profile_data.get('domains', [])),
            'Generated Emails': '; '.join(profile_data.get('emails', [])),
            'Status': profile_data.get('status', 'Unknown'),
            'Error Message': profile_data.get('error', '')
        }
        
        writer.writerow(row)
    
    print(f"💾 Saved: {profile_data.get('full_name', 'Unknown')}")


def load_enriched_profiles(output_file):
    """
    Load previously enriched profiles to avoid re-processing
    
    Args:
        output_file: Path to output CSV file
        
    Returns:
        Set of profile URLs that have been processed
    """
    if not os.path.exists(output_file):
        return set()
    
    processed_urls = set()
    
    with open(output_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            url = row.get('Profile URL', '').strip()
            if url:
                processed_urls.add(url)
    
    return processed_urls
