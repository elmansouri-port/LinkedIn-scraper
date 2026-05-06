"""
Email Tester - Verify email addresses using DNS and SMTP handshake.
No external API required.
"""
import dns.resolver
import smtplib
import re
import logging
import time
from typing import Tuple, Optional, List, Dict

logger = logging.getLogger(__name__)


def validate_email_format(email: str) -> bool:
    """Validate basic email format."""
    if not email:
        return False
    pattern = r'^[a-zA-Z0-9][a-zA-Z0-9._-]*@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def check_mx_records(domain: str) -> Tuple[bool, str]:
    """
    Check if domain has valid MX records.
    Returns: (has_mx, message)
    """
    try:
        mx_records = dns.resolver.resolve(domain, 'MX')
        mx_list = list(mx_records)
        if mx_list:
            return True, f"MX records found: {len(mx_list)}"
        return False, "No MX records found"
    except dns.resolver.NoAnswer:
        return False, "No MX records (NoAnswer)"
    except dns.resolver.NXDOMAIN:
        return False, "Domain does not exist"
    except dns.resolver.NoNameservers:
        return False, "No nameservers for domain"
    except Exception as e:
        return False, f"DNS error: {str(e)}"


def smtp_handshake(email: str, timeout: int = 10) -> Tuple[bool, str]:
    """
    Perform SMTP handshake to verify if mailbox exists.
    Does NOT actually send an email.
    Returns: (is_valid, message)
    """
    try:
        domain = email.split('@')[1]

        # Get MX record
        mx_records = dns.resolver.resolve(domain, 'MX')
        mx_hosts = [(r.preference, str(r.exchange)) for r in mx_records]
        mx_hosts.sort()

        if not mx_hosts:
            return False, "No MX hosts found"

        # Try each MX host
        for _, mx_host in mx_hosts:
            try:
                server = smtplib.SMTP(timeout=timeout)
                server.set_debuglevel(0)

                # Connect to server
                server.connect(mx_host)
                server.helo()

                # Mail from
                server.mail('test@example.com')

                # Rcpt to (this checks if mailbox exists)
                code, msg = server.rcpt(email)
                server.quit()

                if code == 250:
                    return True, "Mailbox exists (SMTP 250)"
                elif code == 550:
                    return False, "Mailbox does not exist (550)"
                elif code == 551:
                    return False, "User not local (551)"
                elif code == 552:
                    return False, "Storage exceeded (552)"
                elif code == 553:
                    return False, "Mailbox name not allowed (553)"
                else:
                    return False, f"Unknown response: {code} {msg}"

            except smtplib.SMTPException as e:
                continue
            except Exception as e:
                continue

        return False, "Could not connect to any MX host"

    except dns.resolver.NXDOMAIN:
        return False, "Domain does not exist"
    except Exception as e:
        return False, f"SMTP error: {str(e)}"


def verify_email(email: str, method: str = 'smtp') -> Tuple[bool, str]:
    """
    Verify an email address.
    Methods:
        - 'format': Just check format
        - 'dns': Check MX records only
        - 'smtp': Full SMTP handshake (recommended)
    Returns: (is_valid, reason)
    """
    if not validate_email_format(email):
        return False, "Invalid email format"

    domain = email.split('@')[1]

    if method == 'format':
        return True, "Format valid"

    elif method == 'dns':
        return check_mx_records(domain)

    elif method == 'smtp':
        # First check MX records
        has_mx, mx_msg = check_mx_records(domain)
        if not has_mx:
            return False, f"DNS: {mx_msg}"

        # Then SMTP handshake
        return smtp_handshake(email)

    return False, "Unknown method"


def verify_emails_batch(emails: List[Dict], method: str = 'smtp',
                        delay: float = 1.0, max_emails: int = None) -> List[Dict]:
    """
    Verify a batch of emails with rate limiting.
    Args:
        emails: List of dicts with 'email' and optional 'profile_url'
        method: Verification method
        delay: Delay between checks in seconds
        max_emails: Maximum number to verify
    Returns:
        List of result dicts with 'email', 'valid', 'reason', 'profile_url'
    """
    results = []
    count = 0

    for item in emails:
        if max_emails and count >= max_emails:
            break

        email = item.get('email')
        if not email:
            continue

        logger.info(f"Verifying: {email}")
        valid, reason = verify_email(email, method)

        results.append({
            'email': email,
            'profile_url': item.get('profile_url', ''),
            'valid': valid,
            'reason': reason,
            'method': method,
        })

        count += 1

        if count < len(emails):
            time.sleep(delay)

    return results


def get_verification_summary(results: List[Dict]) -> Dict:
    """Get summary statistics from verification results."""
    total = len(results)
    valid = sum(1 for r in results if r['valid'])
    invalid = total - valid

    return {
        'total': total,
        'valid': valid,
        'invalid': invalid,
        'validity_rate': (valid / total * 100) if total > 0 else 0,
    }
