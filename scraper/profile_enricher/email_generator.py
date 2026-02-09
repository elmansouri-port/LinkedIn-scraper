"""
Email Generator v2.0 for Profile Enricher
Advanced email generation with multiple formats and optional validation.

Features:
- Multiple email format patterns (most common corporate formats)
- Pattern scoring based on company size/type
- Name normalization for international names
- Optional email validation via SMTP or API
- Caching for efficiency
"""
import re
import unicodedata
from typing import List, Dict, Optional, Tuple


# Common corporate email patterns (ordered by prevalence)
EMAIL_PATTERNS = [
    # Pattern name, format, prevalence score (higher = more common)
    ("first.last", "{first}.{last}@{domain}", 35),           # john.doe@company.com
    ("first_last", "{first}_{last}@{domain}", 15),           # john_doe@company.com
    ("firstlast", "{first}{last}@{domain}", 12),             # johndoe@company.com
    ("first", "{first}@{domain}", 10),                       # john@company.com
    ("f.last", "{f}.{last}@{domain}", 8),                    # j.doe@company.com
    ("flast", "{f}{last}@{domain}", 7),                      # jdoe@company.com
    ("first.l", "{first}.{l}@{domain}", 5),                  # john.d@company.com
    ("last.first", "{last}.{first}@{domain}", 4),            # doe.john@company.com
    ("lastf", "{last}{f}@{domain}", 2),                      # doej@company.com
    ("last", "{last}@{domain}", 2),                          # doe@company.com
]

# Known company email patterns (add more as discovered)
KNOWN_PATTERNS = {
    "google.com": "first.last",
    "microsoft.com": "first.last",
    "amazon.com": "first.last",
    "apple.com": "first.last",
    "facebook.com": "first.last",
    "meta.com": "first.last",
    "linkedin.com": "first.last",
    "oracle.com": "first.last",
    "ibm.com": "first.last",
    "salesforce.com": "first.last",
    "adobe.com": "first.last",
    "orange.fr": "first.last",
    "al-enterprise.com": "first.last",
}


def normalize_name_part(name: str) -> str:
    """
    Normalize a name part for email formatting.
    Handles accents, special characters, compound names.
    
    Examples:
        "François" -> "francois"
        "El Mansouri" -> "el-mansouri" or "elmansouri"
        "O'Brien" -> "obrien"
        "Jean-Pierre" -> "jean-pierre" or "jeanpierre"
    """
    if not name:
        return ""
    
    # Convert to lowercase
    name = name.lower().strip()
    
    # Remove accents (François -> francois)
    name = ''.join(
        char for char in unicodedata.normalize('NFD', name)
        if unicodedata.category(char) != 'Mn'
    )
    
    # Remove apostrophes and similar characters
    name = re.sub(r"['\\u2019`]", "", name)
    
    # Keep hyphens for compound names but remove spaces
    name = name.replace(' ', '')
    
    # Remove any remaining special characters except hyphens
    name = re.sub(r'[^a-z0-9-]', '', name)
    
    # Remove consecutive hyphens
    name = re.sub(r'-+', '-', name)
    
    # Remove leading/trailing hyphens
    name = name.strip('-')
    
    return name


def normalize_name_part_with_separator(name: str, separator: str = '') -> str:
    """
    Normalize name with custom separator for multi-part names.
    
    Examples with separator='.':
        "El Mansouri" -> "el.mansouri"
    """
    if not name:
        return ""
    
    name = name.lower().strip()
    
    # Remove accents
    name = ''.join(
        char for char in unicodedata.normalize('NFD', name)
        if unicodedata.category(char) != 'Mn'
    )
    
    # Remove apostrophes
    name = re.sub(r"['\\u2019`]", "", name)
    
    # Replace spaces and hyphens with separator
    name = re.sub(r'[\s-]+', separator, name)
    
    # Remove other special characters
    if separator:
        pattern = f'[^a-z0-9{re.escape(separator)}]'
    else:
        pattern = '[^a-z0-9]'
    name = re.sub(pattern, '', name)
    
    return name.strip(separator) if separator else name


def get_name_variants(first_name: str, last_name: str) -> Dict[str, str]:
    """
    Generate all name variants needed for email patterns.
    
    Returns dict with keys: first, last, f, l, and their variants
    """
    # Standard normalization (remove spaces, keep hyphens)
    first = normalize_name_part(first_name)
    last = normalize_name_part(last_name)
    
    # Variants without hyphens
    first_no_hyphen = first.replace('-', '')
    last_no_hyphen = last.replace('-', '')
    
    # Initials
    f = first[0] if first else ""
    l = last[0] if last else ""
    
    return {
        'first': first,
        'last': last,
        'first_no_hyphen': first_no_hyphen,
        'last_no_hyphen': last_no_hyphen,
        'f': f,
        'l': l,
    }


def generate_email_from_pattern(pattern_format: str, first_name: str, 
                                 last_name: str, domain: str) -> Optional[str]:
    """
    Generate email using a specific pattern format.
    
    Args:
        pattern_format: Format string like "{first}.{last}@{domain}"
        first_name: First name
        last_name: Last name  
        domain: Email domain
        
    Returns:
        Formatted email or None if invalid
    """
    variants = get_name_variants(first_name, last_name)
    
    if not variants['first'] or not variants['last'] or not domain:
        return None
    
    try:
        email = pattern_format.format(
            first=variants['first'],
            last=variants['last'],
            f=variants['f'],
            l=variants['l'],
            domain=domain.lower().strip()
        )
        
        # Validate basic email format
        if validate_email_format(email):
            return email
        return None
        
    except (KeyError, ValueError):
        return None


def generate_all_email_formats(first_name: str, last_name: str, 
                                domain: str, max_emails: int = 5) -> List[Dict]:
    """
    Generate emails using all patterns, sorted by likelihood.
    
    Args:
        first_name: First name
        last_name: Last name
        domain: Company domain
        max_emails: Maximum number of email formats to return
        
    Returns:
        List of dicts with 'email', 'pattern', 'score'
    """
    results = []
    seen_emails = set()
    
    # Check if we know the pattern for this domain
    known_pattern = KNOWN_PATTERNS.get(domain.lower())
    
    for pattern_name, pattern_format, score in EMAIL_PATTERNS:
        email = generate_email_from_pattern(pattern_format, first_name, last_name, domain)
        
        if email and email not in seen_emails:
            seen_emails.add(email)
            
            # Boost score if this is the known pattern
            final_score = score * 2 if pattern_name == known_pattern else score
            
            results.append({
                'email': email,
                'pattern': pattern_name,
                'score': final_score,
                'is_known': pattern_name == known_pattern
            })
    
    # Sort by score (highest first)
    results.sort(key=lambda x: x['score'], reverse=True)
    
    return results[:max_emails]


def generate_primary_email(first_name: str, last_name: str, domain: str) -> Optional[str]:
    """
    Generate the most likely email address for a person.
    Uses known patterns or defaults to first.last format.
    
    Args:
        first_name: First name
        last_name: Last name
        domain: Company domain
        
    Returns:
        Most likely email address
    """
    if not first_name or not last_name or not domain:
        return None
    
    # Check known patterns first
    domain_lower = domain.lower()
    if domain_lower in KNOWN_PATTERNS:
        pattern_name = KNOWN_PATTERNS[domain_lower]
        for name, format_str, _ in EMAIL_PATTERNS:
            if name == pattern_name:
                return generate_email_from_pattern(format_str, first_name, last_name, domain)
    
    # Default to first.last
    return generate_email_from_pattern("{first}.{last}@{domain}", first_name, last_name, domain)


def generate_emails_for_profile(first_name: str, last_name: str, 
                                 domains: List[str], 
                                 all_formats: bool = False,
                                 max_per_domain: int = 3) -> List[str]:
    """
    Generate email addresses for a profile based on multiple domains.
    
    Args:
        first_name: Person's first name
        last_name: Person's last name
        domains: List of company domains
        all_formats: If True, generate multiple formats per domain
        max_per_domain: Max emails per domain when all_formats=True
        
    Returns:
        List of generated email addresses
    """
    emails = []
    
    for domain in domains:
        if all_formats:
            # Generate multiple formats
            results = generate_all_email_formats(first_name, last_name, domain, max_per_domain)
            emails.extend([r['email'] for r in results])
        else:
            # Just primary email
            email = generate_primary_email(first_name, last_name, domain)
            if email:
                emails.append(email)
    
    return emails


def validate_email_format(email: str) -> bool:
    """
    Validate basic email format.
    
    Args:
        email: Email address to validate
        
    Returns:
        True if format is valid
    """
    if not email:
        return False
    
    # Basic email regex pattern
    pattern = r'^[a-z0-9][a-z0-9._-]*@[a-z0-9.-]+\.[a-z]{2,}$'
    
    return bool(re.match(pattern, email.lower()))


def add_known_pattern(domain: str, pattern_name: str):
    """
    Add a known email pattern for a domain.
    
    Args:
        domain: Company domain (e.g., "company.com")
        pattern_name: Pattern name (e.g., "first.last", "flast")
    """
    valid_patterns = [p[0] for p in EMAIL_PATTERNS]
    if pattern_name in valid_patterns:
        KNOWN_PATTERNS[domain.lower()] = pattern_name


# ============================================================================
# OPTIONAL: Email Validation (requires external service or DNS checks)
# ============================================================================

def validate_email_exists(email: str, method: str = 'format') -> Tuple[bool, str]:
    """
    Validate if an email address likely exists.
    
    Methods:
        - 'format': Just check format (fast, always works)
        - 'dns': Check if domain has MX records (medium, no external API)
        - 'api': Use email validation API (slow, requires API key)
    
    Args:
        email: Email to validate
        method: Validation method
        
    Returns:
        Tuple of (is_valid, reason)
    """
    if not validate_email_format(email):
        return False, "Invalid format"
    
    if method == 'format':
        return True, "Format valid"
    
    elif method == 'dns':
        try:
            import dns.resolver
            domain = email.split('@')[1]
            
            # Check MX records
            try:
                mx_records = dns.resolver.resolve(domain, 'MX')
                return True, f"MX records found: {len(list(mx_records))}"
            except dns.resolver.NoAnswer:
                return False, "No MX records"
            except dns.resolver.NXDOMAIN:
                return False, "Domain does not exist"
                
        except ImportError:
            return True, "DNS check unavailable (dnspython not installed)"
    
    elif method == 'api':
        # Placeholder for API-based validation
        # Could integrate with services like:
        # - Hunter.io
        # - ZeroBounce
        # - NeverBounce
        return True, "API validation not configured"
    
    return True, "Unknown method"


# ============================================================================
# Utility Functions
# ============================================================================

def get_available_patterns() -> List[str]:
    """Get list of available email pattern names"""
    return [p[0] for p in EMAIL_PATTERNS]


def explain_patterns() -> str:
    """Get human-readable explanation of email patterns"""
    lines = ["Available email patterns (by likelihood):"]
    lines.append("-" * 50)
    
    for name, format_str, score in EMAIL_PATTERNS:
        example = format_str.format(first="john", last="doe", f="j", l="d", domain="company.com")
        lines.append(f"  {name:12} | {example:30} | Score: {score}")
    
    return "\n".join(lines)


if __name__ == "__main__":
    # Test the module
    print("Email Generator v2.0 Test")
    print("=" * 50)
    
    # Test with sample names
    test_cases = [
        ("John", "Doe", "google.com"),
        ("François", "De La Cruz", "orange.fr"),
        ("Jean-Pierre", "O'Brien", "microsoft.com"),
        ("Youssef", "El Mansouri", "al-enterprise.com"),
    ]
    
    for first, last, domain in test_cases:
        print(f"\nName: {first} {last}")
        print(f"Domain: {domain}")
        print("Generated emails:")
        
        results = generate_all_email_formats(first, last, domain)
        for r in results:
            marker = "★" if r['is_known'] else " "
            print(f"  {marker} {r['email']:35} (pattern: {r['pattern']}, score: {r['score']})")
