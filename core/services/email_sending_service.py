"""
Email Sending Service - Business logic for sending campaign emails.
"""
import logging
import time
import os
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from core.email_sender import EmailSender, SMTP_PRESETS, get_available_presets
from core.database import (
    create_email_campaign, get_email_campaign, get_all_email_campaigns,
    update_campaign_stats, update_campaign_status,
    save_email_send, update_email_send_status, get_campaign_email_sends,
    get_email_send_stats, get_all_enriched_profiles, get_connection
)
from config.scraper_config import EmailConfig

logger = logging.getLogger(__name__)


class EmailSendingService:
    """Service for managing email campaigns and sending."""

    @staticmethod
    def get_smtp_presets() -> List[str]:
        """Get available SMTP presets."""
        return get_available_presets()

    @staticmethod
    def create_campaign(name: str, subject: str, body_text: str,
                        body_html: str = None, cv_path: str = None,
                        cover_letter_path: str = None, db_path: str = None) -> Dict[str, Any]:
        """Create a new email campaign."""
        logger.info("Creating email campaign: %s", name)

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
            return {
                'success': False,
                'message': "Failed to create campaign",
                'campaign_id': None,
            }
        finally:
            conn.close()

        if campaign_id:
            logger.success("Campaign created with ID: %d", campaign_id)
            return {
                'success': True,
                'message': "Campaign '%s' created successfully" % name,
                'campaign_id': campaign_id,
            }
        return {
            'success': False,
            'message': "Failed to create campaign",
            'campaign_id': None,
        }

    @staticmethod
    def get_campaign(campaign_id: int, db_path: str = None) -> Optional[Dict]:
        """Get a campaign by ID."""
        return get_email_campaign(campaign_id, db_path)

    @staticmethod
    def get_all_campaigns(db_path: str = None) -> List[Dict]:
        """Get all campaigns."""
        return get_all_email_campaigns(db_path)

    @staticmethod
    def get_campaign_stats(campaign_id: int = None, db_path: str = None) -> Dict:
        """Get send statistics."""
        return get_email_send_stats(campaign_id, db_path)

    @staticmethod
    def prepare_campaign_emails(campaign_id: int, db_path: str = None) -> int:
        """
        Prepare email sends for a campaign from enriched profiles.
        Returns number of emails prepared.
        """
        campaign = get_email_campaign(campaign_id, db_path)
        if not campaign:
            return 0

        profiles = get_all_enriched_profiles(db_path)
        existing_sends = get_campaign_email_sends(campaign_id, db_path)
        existing_emails = {s['email'] for s in existing_sends}

        prepared = 0
        conn = get_connection(db_path)
        cursor = conn.cursor()

        try:
            for p in profiles:
                email = p.get('generated_email')
                if not email:
                    continue
                if email in existing_emails:
                    continue

                template_data = {
                    'first_name': p.get('first_name', ''),
                    'last_name': p.get('last_name', ''),
                    'full_name': p.get('full_name', ''),
                    'company': p.get('current_company', ''),
                    'email': email,
                }

                subject = campaign['subject']
                body_text = campaign['body_template']
                body_html = campaign.get('body_template_html')

                for var, value in template_data.items():
                    placeholder = '{' + var + '}'
                    subject = subject.replace(placeholder, str(value))
                    body_text = body_text.replace(placeholder, str(value))
                    if body_html:
                        body_html = body_html.replace(placeholder, str(value))

                cursor.execute("""
                    INSERT OR IGNORE INTO email_sends
                        (campaign_id, profile_url, email, first_name, last_name,
                         company, subject, body_text, body_html)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    campaign_id, p.get('profile_url', ''), email,
                    p.get('first_name', ''), p.get('last_name', ''),
                    p.get('current_company', ''), subject, body_text, body_html
                ))

                if cursor.rowcount > 0:
                    prepared += 1

            conn.commit()
        except Exception as e:
            logger.error("Error preparing campaign emails: %s", e)
        finally:
            conn.close()

        logger.info("Prepared %d emails for campaign %d", prepared, campaign_id)
        return prepared

    @staticmethod
    def send_campaign(
        campaign_id: int,
        smtp_preset: str,
        username: str,
        password: str,
        max_send: int = None,
        min_delay: float = None,
        max_delay: float = None,
        only_verified: bool = True,
        db_path: str = None
    ) -> Dict[str, Any]:
        """
        Send emails for a campaign.
        Args:
            campaign_id: Campaign to send
            smtp_preset: SMTP preset name (gmail/outlook/etc.)
            username: SMTP username
            password: SMTP password
            max_send: Max emails to send (None = all)
            min_delay: Min delay between emails
            max_delay: Max delay between emails
            only_verified: Only send to verified emails
        """
        logger.info("Sending campaign %d via %s", campaign_id, smtp_preset)

        campaign = get_email_campaign(campaign_id, db_path)
        if not campaign:
            return {'success': False, 'message': 'Campaign not found'}

        try:
            sender = EmailSender.from_preset(smtp_preset, username, password)
        except ValueError as e:
            return {'success': False, 'message': str(e)}

        # Get attachments from campaign
        attachments = []
        cv_path = campaign.get('cv_path')
        cover_letter_path = campaign.get('cover_letter_path')

        if cv_path and os.path.exists(cv_path):
            attachments.append(cv_path)
            logger.info("Attaching CV: %s", cv_path)
        elif cv_path:
            logger.warning("CV not found: %s", cv_path)

        if cover_letter_path and os.path.exists(cover_letter_path):
            attachments.append(cover_letter_path)
            logger.info("Attaching cover letter: %s", cover_letter_path)
        elif cover_letter_path:
            logger.warning("Cover letter not found: %s", cover_letter_path)

        # Get pending emails
        if only_verified:
            conn = get_connection(db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT es.* FROM email_sends es
                JOIN enriched_profiles ep ON es.profile_url = ep.profile_url
                WHERE es.campaign_id = ? AND es.status = 'pending'
                AND (ep.email_verified = 1 OR ep.email_verified IS NULL)
            """, (campaign_id,))
            sends = [dict(row) for row in cursor.fetchall()]
            conn.close()
        else:
            sends = get_campaign_email_sends(campaign_id, status='pending', db_path=db_path)

        if not sends:
            return {
                'success': True,
                'message': 'No pending emails to send',
                'sent': 0,
                'failed': 0,
            }

        update_campaign_status(campaign_id, 'sending', db_path)

        sent_count = 0
        failed_count = 0
        sent_ids = []

        try:
            for i, send in enumerate(sends):
                if max_send and sent_count >= max_send:
                    break

                email = send['email']
                subject = send['subject']
                body_text = send['body_text']
                body_html = send['body_html']

                logger.info("Sending %d/%d: %s", i+1, len(sends), email)

                success, message = sender.send_email(
                    to_email=email,
                    subject=subject,
                    body_text=body_text,
                    body_html=body_html,
                    attachments=attachments if attachments else None,
                )

                if success:
                    update_email_send_status(send['id'], 'sent', None, db_path)
                    sent_count += 1
                    sent_ids.append(send['id'])
                else:
                    update_email_send_status(send['id'], 'failed', message, db_path)
                    failed_count += 1

                if i < len(sends) - 1:
                    delay = EmailConfig.MIN_DELAY if min_delay is None else min_delay
                    if max_delay and min_delay is None:
                        delay = (EmailConfig.MIN_DELAY + EmailConfig.MAX_DELAY) / 2
                    logger.debug("Waiting %ds before next email", delay)
                    time.sleep(delay)

        except Exception as e:
            logger.error("Campaign send error: %s", e)
        finally:
            update_campaign_stats(campaign_id, sent_count, failed_count, db_path)
            remaining = len(sends) - sent_count - failed_count
            if remaining > 0:
                update_campaign_status(campaign_id, 'paused', db_path)
            else:
                update_campaign_status(campaign_id, 'completed', db_path)

        logger.success(
            "Campaign %d complete | sent=%d failed=%d",
            campaign_id, sent_count, failed_count
        )

        return {
            'success': True,
            'message': "Campaign sent: %d successful, %d failed" % (sent_count, failed_count),
            'sent': sent_count,
            'failed': failed_count,
            'sent_ids': sent_ids,
        }

    @staticmethod
    def preview_email(campaign_id: int, sample_email: str = None,
                      db_path: str = None) -> Dict[str, Any]:
        """Preview rendered email for a campaign."""
        campaign = get_email_campaign(campaign_id, db_path)
        if not campaign:
            return {'success': False, 'message': 'Campaign not found'}

        profiles = get_all_enriched_profiles(db_path)
        if not profiles:
            return {'success': False, 'message': 'No profiles available'}

        sample = profiles[0]
        if sample_email:
            for p in profiles:
                if p.get('generated_email') == sample_email:
                    sample = p
                    break

        template_data = {
            'first_name': sample.get('first_name', ''),
            'last_name': sample.get('last_name', ''),
            'full_name': sample.get('full_name', ''),
            'company': sample.get('current_company', ''),
            'email': sample.get('generated_email', ''),
        }

        subject = campaign['subject']
        body_text = campaign['body_template']
        body_html = campaign.get('body_template_html')

        for var, value in template_data.items():
            placeholder = '{' + var + '}'
            subject = subject.replace(placeholder, str(value))
            body_text = body_text.replace(placeholder, str(value))
            if body_html:
                body_html = body_html.replace(placeholder, str(value))

        attachments = []
        cv_path = campaign.get('cv_path')
        cover_letter_path = campaign.get('cover_letter_path')
        if cv_path:
            attachments.append(cv_path)
        if cover_letter_path:
            attachments.append(cover_letter_path)

        return {
            'success': True,
            'subject': subject,
            'body_text': body_text,
            'body_html': body_html,
            'attachments': attachments,
            'sample_profile': {
                'name': sample.get('full_name', ''),
                'email': sample.get('generated_email', ''),
                'company': sample.get('current_company', ''),
            }
        }
