"""
Email Sending Service — campaign management, preparation, sending, and retry.
"""
import logging
import random
import time
import os
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from core.email_sender import EmailSender, SMTP_PRESETS, get_available_presets
from core.database import (
    create_email_campaign, get_email_campaign, get_all_email_campaigns,
    save_email_send, update_email_send_status, get_campaign_email_sends,
    get_email_send_stats, get_all_enriched_profiles, get_connection,
    get_email_accounts, update_account_usage, get_next_available_account,
)
from config.scraper_config import EmailConfig

logger = logging.getLogger(__name__)


class EmailSendingService:

    @staticmethod
    def get_smtp_presets() -> List[str]:
        return get_available_presets()

    @staticmethod
    def create_campaign(name: str, subject: str, body_text: str,
                        body_html: str = None, cv_path: str = None,
                        cover_letter_path: str = None,
                        db_path: str = None) -> Dict[str, Any]:
        conn = get_connection(db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO email_campaigns
                    (name, subject, body_template, body_template_html, cv_path, cover_letter_path)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (name, subject, body_text, body_html, cv_path, cover_letter_path))
            conn.commit()
            campaign_id = cursor.lastrowid
        except Exception as e:
            logger.error("Error creating campaign: %s", e)
            return {'success': False, 'message': "Failed to create campaign", 'campaign_id': None}
        finally:
            conn.close()

        if campaign_id:
            logger.info("Campaign created id=%d name=%s", campaign_id, name)
            return {'success': True, 'message': f"Campaign '{name}' created", 'campaign_id': campaign_id}
        return {'success': False, 'message': "Failed to create campaign", 'campaign_id': None}

    @staticmethod
    def get_campaign(campaign_id: int, db_path: str = None) -> Optional[Dict]:
        return get_email_campaign(campaign_id, db_path)

    @staticmethod
    def get_all_campaigns(db_path: str = None) -> List[Dict]:
        return get_all_email_campaigns(db_path)

    @staticmethod
    def get_campaign_stats(campaign_id: int = None, db_path: str = None) -> Dict:
        return get_email_send_stats(campaign_id, db_path)

    # ── Prepare ───────────────────────────────────────────

    @staticmethod
    def prepare_campaign_emails(campaign_id: int, db_path: str = None) -> int:
        """
        Create email_sends records from enriched profiles for this campaign.
        Skips profiles already queued. Returns number of new records created.
        """
        campaign = get_email_campaign(campaign_id, db_path)
        if not campaign:
            return 0

        # Join enriched profiles with search_profiles to get location
        conn = get_connection(db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT ep.*, sp.location, sp.title AS raw_title
                FROM enriched_profiles ep
                LEFT JOIN search_profiles sp ON ep.profile_url = sp.profile_url
                WHERE ep.enrichment_status = 'success' AND ep.generated_email IS NOT NULL
            """)
            profiles = [dict(r) for r in cursor.fetchall()]
        finally:
            conn.close()

        existing_sends = get_campaign_email_sends(campaign_id, db_path=db_path)
        existing_emails = {s['email'] for s in existing_sends}

        prepared = 0
        conn = get_connection(db_path)
        cursor = conn.cursor()
        try:
            for p in profiles:
                email = p.get('generated_email')
                if not email or email in existing_emails:
                    continue

                template_data = {
                    'first_name':   p.get('first_name', '') or '',
                    'last_name':    p.get('last_name', '') or '',
                    'full_name':    p.get('full_name', '') or '',
                    'company':      p.get('current_company', '') or '',
                    'title':        p.get('current_job_title', '') or p.get('raw_title', '') or '',
                    'location':     p.get('location', '') or '',
                    'email':        email,
                }

                subject   = campaign['subject']
                body_text = campaign['body_template']
                body_html = campaign.get('body_template_html')

                for var, value in template_data.items():
                    ph = '{' + var + '}'
                    subject   = subject.replace(ph, value)
                    body_text = body_text.replace(ph, value)
                    if body_html:
                        body_html = body_html.replace(ph, value)

                # Replace {current_year}
                year = str(datetime.now().year)
                subject   = subject.replace('{current_year}', year)
                body_text = body_text.replace('{current_year}', year)
                if body_html:
                    body_html = body_html.replace('{current_year}', year)

                cursor.execute("""
                    INSERT OR IGNORE INTO email_sends
                        (campaign_id, profile_url, email, first_name, last_name,
                         company, subject, body_text, body_html, custom_cv_path)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    campaign_id, p.get('profile_url', ''), email,
                    template_data['first_name'], template_data['last_name'],
                    template_data['company'], subject, body_text, body_html,
                    p.get('custom_cv_path')
                ))

                if cursor.rowcount > 0:
                    prepared += 1
                    existing_emails.add(email)

            conn.commit()
        except Exception as e:
            logger.error("Error preparing campaign emails: %s", e)
        finally:
            conn.close()

        logger.info("Prepared %d emails for campaign %d", prepared, campaign_id)
        return prepared

    # ── Send ─────────────────────────────────────────────

    @staticmethod
    def send_campaign(
        campaign_id: int,
        smtp_preset: str,
        username: str,
        password: str,
        max_send: int = None,
        min_delay: float = None,
        max_delay: float = None,
        only_verified: bool = False,
        from_name: str = None,
        db_path: str = None,
    ) -> Dict[str, Any]:
        """
        Send emails for a campaign.

        Auto-prepares email_sends records if none exist yet.
        only_verified=True: only send to emails where email_verified=1.
        only_verified=False (default): send to all pending (including untested).
        """
        campaign = get_email_campaign(campaign_id, db_path)
        if not campaign:
            return {'success': False, 'message': 'Campaign not found'}

        # Auto-prepare if no pending sends exist
        stats_before = get_email_send_stats(campaign_id, db_path)
        if stats_before.get('pending', 0) == 0:
            prepared = EmailSendingService.prepare_campaign_emails(campaign_id, db_path)
            logger.info("Auto-prepared %d emails for campaign %d", prepared, campaign_id)

        try:
            sender = EmailSender.from_preset(smtp_preset, username, password,
                                             from_name=from_name)
        except ValueError as e:
            return {'success': False, 'message': str(e)}

        # Resolve attachments
        attachments = []
        for path_key in ('cv_path', 'cover_letter_path'):
            p = campaign.get(path_key)
            if p and os.path.exists(p):
                attachments.append(p)
            elif p:
                logger.warning("Attachment not found: %s", p)

        # Fetch pending sends
        if only_verified:
            conn = get_connection(db_path)
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    SELECT es.* FROM email_sends es
                    JOIN enriched_profiles ep ON es.profile_url = ep.profile_url
                    WHERE es.campaign_id = ? AND es.status = 'pending'
                    AND ep.email_verified = 1
                """, (campaign_id,))
                sends = [dict(r) for r in cursor.fetchall()]
            finally:
                conn.close()
        else:
            sends = get_campaign_email_sends(campaign_id, status='pending', db_path=db_path)

        if not sends:
            return {'success': True, 'message': 'No pending emails to send', 'sent': 0, 'failed': 0}

        update_campaign_status(campaign_id, 'sending', db_path)

        sent_count = failed_count = 0
        sent_ids = []

        effective_min = min_delay if min_delay is not None else EmailConfig.MIN_DELAY
        effective_max = max_delay if max_delay is not None else EmailConfig.MAX_DELAY

        try:
            with sender:  # reuse SMTP connection across batch
                for i, send in enumerate(sends):
                    if max_send and sent_count >= max_send:
                        break

                    current_attachments = list(attachments)
                    if send.get('custom_cv_path') and os.path.exists(send['custom_cv_path']):
                        current_attachments.append(send['custom_cv_path'])

                    ok, msg = sender.send_email(
                        to_email=send['email'],
                        subject=send['subject'],
                        body_text=send['body_text'],
                        body_html=send['body_html'],
                        attachments=current_attachments or None,
                    )

                    if ok:
                        update_email_send_status(send['id'], 'sent', None, db_path)
                        sent_count += 1
                        sent_ids.append(send['id'])
                    else:
                        update_email_send_status(send['id'], 'failed', msg, db_path)
                        failed_count += 1
                        logger.warning("Send failed to %s: %s", send['email'], msg)

                    # Delay between sends (skip after last)
                    if i < len(sends) - 1 and (not max_send or sent_count < max_send):
                        delay = random.uniform(effective_min, effective_max)
                        logger.debug("Waiting %.1fs before next email", delay)
                        time.sleep(delay)

        except Exception as e:
            logger.error("Campaign send error: %s", e)
        finally:
            update_campaign_stats(campaign_id, sent_count, failed_count, db_path)
            remaining = len(sends) - sent_count - failed_count
            status = 'paused' if remaining > 0 else 'completed'
            update_campaign_status(campaign_id, status, db_path)

        logger.info("Campaign %d done | sent=%d failed=%d", campaign_id, sent_count, failed_count)
        return {
            'success': True,
            'message': f"{sent_count} sent, {failed_count} failed",
            'sent': sent_count,
            'failed': failed_count,
            'sent_ids': sent_ids,
        }

    @staticmethod
    def send_campaign_with_rotation(campaign_id: int, emails_per_day: int = 20, db_path: str = None) -> Dict[str, Any]:
        """Send a campaign using email account rotation. Spreads daily limit across all active accounts."""
        campaign = get_email_campaign(campaign_id, db_path)
        if not campaign:
            return {"success": False, "message": "Campaign not found"}

        # Auto-prepare if needed
        stats_before = get_email_send_stats(campaign_id, db_path)
        if stats_before.get('pending', 0) == 0:
            EmailSendingService.prepare_campaign_emails(campaign_id, db_path)

        # Check how many emails already sent today for this campaign
        today_sends = get_campaign_email_sends(campaign_id, status="sent", db_path=db_path)
        today_count = len([s for s in today_sends if s.get("sent_at", "").startswith(datetime.now().strftime("%Y-%m-%d"))])

        if today_count >= emails_per_day:
            return {"success": False, "message": f"Daily limit reached ({today_count}/{emails_per_day})"}

        remaining_today = emails_per_day - today_count
        accounts = get_email_accounts(active_only=True, db_path=db_path)
        if not accounts:
            return {"success": False, "message": "No active email accounts found"}

        emails_per_account = max(1, remaining_today // len(accounts))
        total_sent = 0
        total_failed = 0

        for account in accounts:
            if total_sent >= remaining_today:
                break

            account_today_limit = min(emails_per_account, account["daily_limit"] - account["daily_sent_today"])
            if account_today_limit <= 0:
                continue

            result = EmailSendingService.send_campaign(
                campaign_id=campaign_id,
                smtp_preset=account["smtp_preset"],
                username=account["username"],
                password=account["password"],
                max_send=account_today_limit,
                db_path=db_path
            )

            sent = result.get("sent", 0)
            failed = result.get("failed", 0)

            total_sent += sent
            total_failed += failed

            # Update account usage
            for _ in range(sent):
                update_account_usage(account["id"], db_path)

        return {
            "success": True,
            "message": f"Sent {total_sent} emails using {len(accounts)} accounts",
            "sent": total_sent,
            "failed": total_failed,
        }

    # ── Retry ────────────────────────────────────────────

    @staticmethod
    def retry_failed(campaign_id: int, smtp_preset: str, username: str, password: str,
                     max_send: int = None, from_name: str = None,
                     db_path: str = None) -> Dict[str, Any]:
        """Reset failed → pending, then re-send."""
        conn = get_connection(db_path)
        try:
            conn.execute(
                "UPDATE email_sends SET status='pending', error_message=NULL "
                "WHERE campaign_id=? AND status='failed'",
                (campaign_id,)
            )
            conn.commit()
        finally:
            conn.close()
        return EmailSendingService.send_campaign(
            campaign_id, smtp_preset, username, password,
            max_send=max_send, from_name=from_name, db_path=db_path,
        )

    # ── Preview ──────────────────────────────────────────

    @staticmethod
    def preview_email(campaign_id: int, sample_email: str = None,
                      db_path: str = None) -> Dict[str, Any]:
        """Preview rendered email using first enriched profile as sample data."""
        campaign = get_email_campaign(campaign_id, db_path)
        if not campaign:
            return {'success': False, 'message': 'Campaign not found'}

        conn = get_connection(db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT ep.*, sp.location, sp.title AS raw_title
                FROM enriched_profiles ep
                LEFT JOIN search_profiles sp ON ep.profile_url = sp.profile_url
                WHERE ep.enrichment_status = 'success'
                LIMIT 10
            """)
            profiles = [dict(r) for r in cursor.fetchall()]
        finally:
            conn.close()

        if not profiles:
            return {'success': False, 'message': 'No enriched profiles available for preview'}

        sample = profiles[0]
        if sample_email:
            for p in profiles:
                if p.get('generated_email') == sample_email:
                    sample = p
                    break

        template_data = {
            'first_name':   sample.get('first_name', '') or '',
            'last_name':    sample.get('last_name', '') or '',
            'full_name':    sample.get('full_name', '') or '',
            'company':      sample.get('current_company', '') or '',
            'title':        sample.get('current_job_title', '') or sample.get('raw_title', '') or '',
            'location':     sample.get('location', '') or '',
            'email':        sample.get('generated_email', '') or '',
        }

        subject   = campaign['subject']
        body_text = campaign['body_template']
        body_html = campaign.get('body_template_html')

        year = str(datetime.now().year)
        for var, value in template_data.items():
            ph = '{' + var + '}'
            subject   = subject.replace(ph, value)
            body_text = body_text.replace(ph, value)
            if body_html:
                body_html = body_html.replace(ph, value)
        subject   = subject.replace('{current_year}', year)
        body_text = body_text.replace('{current_year}', year)
        if body_html:
            body_html = body_html.replace('{current_year}', year)

        attachments = [p for p in [campaign.get('cv_path'), campaign.get('cover_letter_path')] if p]

        return {
            'success': True,
            'subject': subject,
            'body_text': body_text,
            'body_html': body_html,
            'attachments': attachments,
            'sample_profile': {
                'name':    sample.get('full_name', ''),
                'email':   sample.get('generated_email', ''),
                'company': sample.get('current_company', ''),
            },
        }
