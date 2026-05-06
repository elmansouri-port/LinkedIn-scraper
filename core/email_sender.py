"""
Email Sender - Send emails via SMTP with support for Gmail, Hotmail, Outlook.
Supports both plain text and HTML emails with template variables.
"""
import smtplib
import ssl
import logging
import time
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Optional, Tuple, List
from datetime import datetime

logger = logging.getLogger(__name__)


# SMTP Presets for common providers
SMTP_PRESETS = {
    'gmail': {
        'server': 'smtp.gmail.com',
        'port': 587,
        'use_tls': True,
        'description': 'Gmail (requires App Password)'
    },
    'outlook': {
        'server': 'smtp-mail.outlook.com',
        'port': 587,
        'use_tls': True,
        'description': 'Outlook.com / Hotmail'
    },
    'office365': {
        'server': 'smtp.office365.com',
        'port': 587,
        'use_tls': True,
        'description': 'Microsoft Office 365'
    },
    'yahoo': {
        'server': 'smtp.mail.yahoo.com',
        'port': 587,
        'use_tls': True,
        'description': 'Yahoo Mail'
    },
}


def get_available_presets() -> List[str]:
    """Get list of available SMTP presets."""
    return list(SMTP_PRESETS.keys())


def get_preset_config(preset_name: str) -> Optional[Dict]:
    """Get SMTP configuration for a preset."""
    return SMTP_PRESETS.get(preset_name.lower())


class EmailSender:
    """Send emails via SMTP with template support."""

    def __init__(self, smtp_server: str, smtp_port: int,
                 username: str, password: str, use_tls: bool = True):
        """Initialize email sender."""
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.use_tls = use_tls

    @classmethod
    def from_preset(cls, preset_name: str, username: str, password: str):
        """Create EmailSender from a preset configuration."""
        preset = SMTP_PRESETS.get(preset_name.lower())
        if not preset:
            raise ValueError(f"Unknown preset: {preset_name}")
        return cls(
            smtp_server=preset['server'],
            smtp_port=preset['port'],
            username=username,
            password=password,
            use_tls=preset['use_tls']
        )

    def render_template(self, template: str, data: Dict) -> str:
        """
        Render a template with variables.
        Variables: {first_name}, {last_name}, {full_name}, {company}, {email}
        """
        rendered = template
        variables = {
            '{first_name}': data.get('first_name', ''),
            '{last_name}': data.get('last_name', ''),
            '{full_name}': data.get('full_name', ''),
            '{company}': data.get('company', ''),
            '{email}': data.get('email', ''),
            '{current_year}': str(datetime.now().year),
        }

        for var, value in variables.items():
            rendered = rendered.replace(var, value)

        return rendered

    def send_email(self, to_email: str, subject: str,
                   body_text: str = None, body_html: str = None,
                   from_name: str = None, reply_to: str = None) -> Tuple[bool, str]:
        """
        Send an email.
        Args:
            to_email: Recipient email address
            subject: Email subject
            body_text: Plain text body
            body_html: HTML body (if both provided, sends multipart)
            from_name: Display name for sender
            reply_to: Reply-to address
        Returns:
            (success, message)
        """
        try:
            # Create message
            if body_html and body_text:
                msg = MIMEMultipart('alternative')
                msg.attach(MIMEText(body_text, 'plain', 'utf-8'))
                msg.attach(MIMEText(body_html, 'html', 'utf-8'))
            elif body_html:
                msg = MIMEText(body_html, 'html', 'utf-8')
            else:
                msg = MIMEText(body_text or '', 'plain', 'utf-8')

            # Set headers
            from_addr = f"{from_name} <{self.username}>" if from_name else self.username
            msg['From'] = from_addr
            msg['To'] = to_email
            msg['Subject'] = subject

            if reply_to:
                msg['Reply-To'] = reply_to

            # Connect and send
            if self.use_tls:
                context = ssl.create_default_context()
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                server.starttls(context=context)
            else:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)

            server.login(self.username, self.password)
            server.send_message(msg)
            server.quit()

            logger.info(f"Email sent successfully to {to_email}")
            return True, "Email sent successfully"

        except smtplib.SMTPAuthenticationError:
            error = "SMTP Authentication failed. Check credentials."
            logger.error(error)
            return False, error
        except smtplib.SMTPException as e:
            error = f"SMTP error: {str(e)}"
            logger.error(error)
            return False, error
        except Exception as e:
            error = f"Unexpected error: {str(e)}"
            logger.error(error)
            return False, error

    def send_templated_email(self, to_email: str, subject_template: str,
                             body_text_template: str, body_html_template: str = None,
                             template_data: Dict = None, **kwargs) -> Tuple[bool, str]:
        """
        Send an email using templates.
        Args:
            to_email: Recipient email
            subject_template: Subject with variables
            body_text_template: Plain text body with variables
            body_html_template: HTML body with variables (optional)
            template_data: Dict with variable values
            **kwargs: Additional args for send_email
        """
        data = template_data or {}

        subject = self.render_template(subject_template, data)
        body_text = self.render_template(body_text_template, data) if body_text_template else None
        body_html = self.render_template(body_html_template, data) if body_html_template else None

        return self.send_email(to_email, subject, body_text, body_html, **kwargs)
