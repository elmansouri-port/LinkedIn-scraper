"""
Email Testing Service - Business logic for email verification.
"""
import logging
import time
from typing import Dict, Any, List, Optional, Tuple

from core.email_tester import verify_email, verify_emails_batch, get_verification_summary
from core.database import (
    get_all_enriched_profiles,
    save_enriched_profile, get_connection
)

logger = logging.getLogger(__name__)


class EmailTestingService:
    """Service for verifying email addresses."""

    @staticmethod
    def test_single_email(email: str, method: str = 'smtp') -> Tuple[bool, str]:
        """Test a single email address."""
        return verify_email(email, method)

    @staticmethod
    def test_profile_emails(max_test: int = None, method: str = 'smtp',
                              only_unverified: bool = True,
                              db_path: str = None) -> Dict[str, Any]:
        """
        Test emails for enriched profiles.
        Args:
            max_test: Maximum number to test
            method: Verification method (dns/smtp)
            only_unverified: Only test emails not yet verified
            db_path: Database path
        Returns:
            Dict with results and statistics
        """
        logger.info(f"Starting email verification | method={method} max={max_test or 'all'}")

        # Get profiles with emails
        profiles = get_all_enriched_profiles(db_path)
        profiles_to_test = []

        for p in profiles:
            if not p.get('generated_email'):
                continue
            if only_unverified and p.get('email_verified') is not None:
                continue
            profiles_to_test.append(p)

        if not profiles_to_test:
            return {
                'success': True,
                'message': 'No emails to test',
                'tested': 0,
                'valid': 0,
                'invalid': 0,
            }

        # Prepare batch
        emails_batch = []
        for p in profiles_to_test:
            emails_batch.append({
                'email': p['generated_email'],
                'profile_url': p['profile_url'],
            })

        # Run verification
        results = verify_emails_batch(emails_batch, method=method, delay=1.0, max_emails=max_test)

        # Update database
        valid_count = 0
        invalid_count = 0
        conn = get_connection(db_path)
        cursor = conn.cursor()

        try:
            for r in results:
                valid = r['valid']
                reason = r['reason']
                profile_url = r['profile_url']
                email = r['email']

                if valid:
                    valid_count += 1
                else:
                    invalid_count += 1

                # Update enriched_profiles
                cursor.execute("""
                    UPDATE enriched_profiles
                    SET email_verified = ?, email_verified_at = CURRENT_TIMESTAMP,
                        email_verification_method = ?, email_verification_result = ?
                    WHERE profile_url = ?
                """, (valid, method, reason, profile_url))

            conn.commit()
        except Exception as e:
            logger.error(f"Error updating verification results: {e}")
        finally:
            conn.close()

        summary = get_verification_summary(results)

        logger.info(
            "Email verification complete | tested=%d valid=%d invalid=%d",
            len(results), valid_count, invalid_count,
        )

        return {
            'success': True,
            'message': f"Tested {len(results)} emails: {valid_count} valid, {invalid_count} invalid",
            'tested': len(results),
            'valid': valid_count,
            'invalid': invalid_count,
            'results': results,
            'summary': summary,
        }

    @staticmethod
    def test_email_list(emails: List[str], method: str = 'smtp') -> Dict[str, Any]:
        """Test a specific list of emails."""
        if not emails:
            return {'success': False, 'message': 'No emails provided'}

        logger.info(f"Testing {len(emails)} emails")

        batch = [{'email': e, 'profile_url': ''} for e in emails]
        results = verify_emails_batch(batch, method=method, delay=1.0)

        summary = get_verification_summary(results)

        return {
            'success': True,
            'message': f"Tested {len(results)} emails",
            'results': results,
            'summary': summary,
        }

    @staticmethod
    def get_verification_stats(db_path: str = None) -> Dict:
        """Get verification statistics from database."""
        conn = get_connection(db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT email_verified, COUNT(*) as count
                FROM enriched_profiles
                WHERE generated_email IS NOT NULL
                GROUP BY email_verified
            """)
            rows = cursor.fetchall()
            stats = {'verified_true': 0, 'verified_false': 0, 'not_tested': 0}
            for row in rows:
                if row[0] == 1:
                    stats['verified_true'] = row[1]
                elif row[0] == 0:
                    stats['verified_false'] = row[1]
                else:
                    stats['not_tested'] = row[1]
            return stats
        finally:
            conn.close()
