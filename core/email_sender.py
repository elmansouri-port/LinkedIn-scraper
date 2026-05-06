"""
Email Sender - Send emails via SMTP with support for Gmail, Hotmail, Outlook.
Supports both plain text and HTML emails with template variables.
Also supports file attachments (CV, cover letter, etc.)
"""
import smtplib
import ssl
import logging
import os
import mimetypes
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
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
    """Send emails via SMTP with template and attachment support."""

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
            raise ValueError("Unknown preset: %s" % preset_name)
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

    def attach_file(self, msg: MIMEMultipart, file_path: str) -> bool:
        """
        Attach a file to the email message.
        Returns True if successful.
        """
        if not os.path.exists(file_path):
            logger.warning("Attachment not found: %s", file_path)
            return False

        try:
            filename = os.path.basename(file_path)
            mime_type, _ = mimetypes.guess_type(file_path)
            if mime_type is None:
                mime_type = 'application/octet-stream'

            main_type, sub_type = mime_type.split('/', 1)

            with open(file_path, 'rb') as f:
                part = MIMEBase(main_type, sub_type)
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition',
                               'attachment', filename=filename)
                part.add_header('Content-Type', mime_type, name=filename)
                msg.attach(part)

            logger.info("Attached file: %s", filename)
            return True

        except Exception as e:
            logger.error("Failed to attach file %s: %s", file_path, e)
            return False

    def send_email(self, to_email: str, subject: str,
                   body_text: str = None, body_html: str = None,
                   from_name: str = None, reply_to: str = None,
                   attachments: List[str] = None) -> Tuple[bool, str]:
        """
        Send an email with optional attachments.
        Args:
            to_email: Recipient email address
            subject: Email subject
            body_text: Plain text body
            body_html: HTML body (if both provided, sends multipart)
            from_name: Display name for sender
            reply_to: Reply-to address
            attachments: List of file paths to attach
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

            # Convert to multipart if we have attachments
            if attachments:
                old_msg = msg
                msg = MIMEMultipart('mixed')
                msg.attach(old_msg)
                for file_path in attachments:
                    self.attach_file(msg, file_path)

            # Set headers
            from_addr = "%s <%s>" % (from_name, self.username) if from_name else self.username
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

            logger.info("Email sent successfully to %s", to_email)
            return True, "Email sent successfully"

        except smtplib.SMTPAuthenticationError:
            error = "SMTP Authentication failed. Check credentials."
            logger.error(error)
            return False, error
        except smtplib.SMTPException as e:
            error = "SMTP error: %s" % str(e)
            logger.error(error)
            return False, error
        except Exception as e:
            error = "Unexpected error: %s" % str(e)
            logger.error(error)
            return False, error

    def send_templated_email(self, to_email: str, subject_template: str,
                              body_text_template: str, body_html_template: str = None,
                              template_data: Dict = None, attachments: List[str] = None,
                              **kwargs) -> Tuple[bool, str]:
        """
        Send an email using templates with optional attachments.
        Args:
            to_email: Recipient email
            subject_template: Subject with variables
            body_text_template: Plain text body with variables
            body_html_template: HTML body with variables (optional)
            template_data: Dict with variable values
            attachments: List of file paths to attach
            **kwargs: Additional args for send_email
        """
        data = template_data or {}

        subject = self.render_template(subject_template, data)
        body_text = self.render_template(body_text_template, data) if body_text_template else None
        body_html = self.render_template(body_html_template, data) if body_html_template else None

        return self.send_email(to_email, subject, body_text, body_html,
                             attachments=attachments, **kwargs)
