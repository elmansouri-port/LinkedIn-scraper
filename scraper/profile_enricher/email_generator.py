"""
Email Generator for Profile Enricher
Formats professional email addresses based on names and domains
"""
import re
import unicodedata


def normalize_name_part(name):
    """
    Normalize a name part for email formatting
    - Convert to lowercase
    - Replace spaces with hyphens
    - Remove accents and special characters
    - Handle apostrophes and other punctuation
    
    Args:
        name: Name part to normalize (e.g., "El Mansouri")
        
    Returns:
        Normalized name (e.g., "el-mansouri")
        
    Examples:
        "El Mansouri" -> "el-mansouri"
        "O'Brien" -> "obrien"
        "François" -> "francois"
        "Jean-Pierre" -> "jean-pierre"
    """
    if not name:
        return ""
    
    # Convert to lowercase
    name = name.lower()
    
    # Remove accents (François -> francois)
    name = ''.join(
        char for char in unicodedata.normalize('NFD', name)
        if unicodedata.category(char) != 'Mn'
    )
    
    # Replace apostrophes and similar characters with nothing
    name = re.sub(r"['\u2019]", "", name)
    
    # Replace spaces with hyphens
    name = name.replace(' ', '-')
    
    # Remove any remaining special characters except hyphens
    name = re.sub(r'[^a-z0-9-]', '', name)
    
    # Remove consecutive hyphens
    name = re.sub(r'-+', '-', name)
    
    # Remove leading/trailing hyphens
    name = name.strip('-')
    
    return name


def generate_email(first_name, last_name, domain):
    """
    Generate professional email address
    Format: firstname.lastname@domain.com
    
    Args:
        first_name: Person's first name
        last_name: Person's last name
        domain: Company domain
        
    Returns:
        Formatted email address
        
    Examples:
        ("Youssef", "El Mansouri", "al-enterprise.com") -> "youssef.el-mansouri@al-enterprise.com"
        ("Jean-Pierre", "De La Cruz", "orange.fr") -> "jean-pierre.de-la-cruz@orange.fr"
    """
    if not first_name or not last_name or not domain:
        return None
    
    # Normalize names
    first = normalize_name_part(first_name)
    last = normalize_name_part(last_name)
    
    if not first or not last:
        return None
    
    # Ensure domain doesn't have http/https prefix
    domain = domain.replace('http://', '').replace('https://', '')
    domain = domain.strip('/')
    
    # Build email
    email = f"{first}.{last}@{domain}"
    
    return email


def generate_emails_for_profile(first_name, last_name, domains):
    """
    Generate all email addresses for a profile based on multiple domains
    
    Args:
        first_name: Person's first name
        last_name: Person's last name
        domains: List of company domains
        
    Returns:
        List of generated email addresses
    """
    emails = []
    
    for domain in domains:
        email = generate_email(first_name, last_name, domain)
        if email:
            emails.append(email)
    
    return emails


def validate_email_format(email):
    """
    Validate basic email format
    
    Args:
        email: Email address to validate
        
    Returns:
        Boolean indicating if email format is valid
    """
    if not email:
        return False
    
    # Basic email regex pattern
    pattern = r'^[a-z0-9.-]+@[a-z0-9.-]+\.[a-z]{2,}$'
    
    return bool(re.match(pattern, email))
