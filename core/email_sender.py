"""
Email Sender — SMTP with preset support, connection reuse, proper headers.
Supports plain-text + HTML, template variables, and file attachments.
"""
import smtplib
import ssl
import logging
import os
import uuid
import mimetypes
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.utils import formatdate, make_msgid
from typing import Dict, Optional, Tuple, List

logger = logging.getLogger(__name__)

SMTP_PRESETS = {
    'gmail': {
        'server': 'smtp.gmail.com', 'port': 587, 'use_tls': True,
        'description': 'Gmail (requires App Password)',
    },
    'outlook': {
        'server': 'smtp-mail.outlook.com', 'port': 587, 'use_tls': True,
        'description': 'Outlook.com / Hotmail',
    },
    'office365': {
        'server': 'smtp.office365.com', 'port': 587, 'use_tls': True,
        'description': 'Microsoft Office 365',
    },
    'yahoo': {
        'server': 'smtp.mail.yahoo.com', 'port': 587, 'use_tls': True,
        'description': 'Yahoo Mail',
    },
    'custom': {
        'server': '', 'port': 587, 'use_tls': True,
        'description': 'Custom SMTP server',
    },
}


def get_available_presets() -> List[str]:
    return list(SMTP_PRESETS.keys())


def get_preset_config(preset_name: str) -> Optional[Dict]:
    return SMTP_PRESETS.get(preset_name.lower())


class EmailSender:
    """
    SMTP email sender with connection reuse, proper headers, and attachment support.
    Use as a context manager to reuse the SMTP connection across a batch:

        with EmailSender.from_preset('gmail', user, pwd) as sender:
            for item in batch:
                sender.send_email(...)
    """

    def __init__(self, smtp_server: str, smtp_port: int,
                 username: str, password: str, use_tls: bool = True,
                 from_name: str = None):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.from_name = from_name
        self._server: Optional[smtplib.SMTP] = None

    @classmethod
    def from_preset(cls, preset_name: str, username: str, password: str,
                    from_name: str = None) -> "EmailSender":
        preset = SMTP_PRESETS.get(preset_name.lower())
        if not preset:
            raise ValueError(f"Unknown SMTP preset: {preset_name!r}. "
                             f"Valid: {list(SMTP_PRESETS)}")
        return cls(preset['server'], preset['port'], username, password,
                   preset['use_tls'], from_name)

    # ── Context manager (connection reuse) ───────────────

    def __enter__(self) -> "EmailSender":
        self._connect()
        return self

    def __exit__(self, *_):
        self._disconnect()

    def _connect(self):
        ctx = ssl.create_default_context()
        server = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=30)
        if self.use_tls:
            server.starttls(ctx)
        server.login(self.username, self.password)
        self._server = server
        logger.debug("SMTP connected to %s:%s", self.smtp_server, self.smtp_port)

    def _disconnect(self):
        if self._server:
            try:
                self._server.quit()
            except Exception:
                pass
            self._server = None

    def _reconnect_if_needed(self):
        """Reconnect if the persistent connection was dropped."""
        try:
            if self._server:
                self._server.noop()
        except Exception:
            logger.debug("SMTP connection lost, reconnecting")
            self._connect()

    # ── Template rendering ───────────────────────────────

    def render_template(self, template: str, data: Dict) -> str:
        from datetime import datetime
        variables = {
            '{first_name}':   str(data.get('first_name', '')),
            '{last_name}':    str(data.get('last_name', '')),
            '{full_name}':    str(data.get('full_name', '')),
            '{company}':      str(data.get('company', '')),
            '{title}':        str(data.get('title', '')),
            '{location}':     str(data.get('location', '')),
            '{email}':        str(data.get('email', '')),
            '{current_year}': str(datetime.now().year),
        }
        rendered = template
        for var, value in variables.items():
            rendered = rendered.replace(var, value)
        return rendered

    # ── Attachment helper ────────────────────────────────

    def _attach_file(self, msg: MIMEMultipart, file_path: str) -> bool:
        if not os.path.exists(file_path):
            logger.warning("Attachment not found: %s", file_path)
            return False
        try:
            filename = os.path.basename(file_path)
            mime_type, _ = mimetypes.guess_type(file_path)
            mime_type = mime_type or 'application/octet-stream'
            main_type, sub_type = mime_type.split('/', 1)
            with open(file_path, 'rb') as f:
                part = MIMEBase(main_type, sub_type)
                part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', 'attachment', filename=filename)
            part.add_header('Content-Type', mime_type, name=filename)
            msg.attach(part)
            return True
        except Exception as e:
            logger.error("Failed to attach %s: %s", file_path, e)
            return False

    # ── Core send ────────────────────────────────────────

    def send_email(self, to_email: str, subject: str,
                   body_text: str = None, body_html: str = None,
                   from_name: str = None, reply_to: str = None,
                   attachments: List[str] = None) -> Tuple[bool, str]:
        """
        Send a single email. Uses the persistent connection if available,
        otherwise opens a one-shot connection.
        """
        try:
            # Build MIME structure
            if body_html and body_text:
                content = MIMEMultipart('alternative')
                content.attach(MIMEText(body_text, 'plain', 'utf-8'))
                content.attach(MIMEText(body_html, 'html', 'utf-8'))
            elif body_html:
                content = MIMEMultipart('alternative')
                content.attach(MIMEText(body_html, 'html', 'utf-8'))
            else:
                content = MIMEText(body_text or '', 'plain', 'utf-8')

            if attachments:
                msg = MIMEMultipart('mixed')
                msg.attach(content)
                for path in attachments:
                    self._attach_file(msg, path)
            else:
                msg = content

            # Headers
            display_name = from_name or self.from_name or ""
            from_addr = (f"{display_name} <{self.username}>"
                         if display_name else self.username)
            msg['From'] = from_addr
            msg['To'] = to_email
            msg['Subject'] = subject
            msg['Date'] = formatdate(localtime=True)
            msg['Message-ID'] = make_msgid(domain=self.username.split('@')[-1])
            if reply_to:
                msg['Reply-To'] = reply_to

            # Send
            if self._server:
                self._reconnect_if_needed()
                self._server.send_message(msg)
            else:
                # One-shot connection
                ctx = ssl.create_default_context()
                with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=30) as server:
                    if self.use_tls:
                        server.starttls(ctx)
                    server.login(self.username, self.password)
                    server.send_message(msg)

            logger.info("Sent → %s", to_email)
            return True, "Sent"

        except smtplib.SMTPAuthenticationError:
            return False, "Authentication failed — check credentials or App Password"
        except smtplib.SMTPRecipientsRefused:
            return False, f"Recipient refused: {to_email}"
        except smtplib.SMTPException as e:
            return False, f"SMTP error: {e}"
        except Exception as e:
            return False, f"Unexpected error: {e}"

    def send_templated_email(self, to_email: str, subject_template: str,
                              body_text_template: str = None,
                              body_html_template: str = None,
                              template_data: Dict = None,
                              attachments: List[str] = None,
                              **kwargs) -> Tuple[bool, str]:
        data = template_data or {}
        subject   = self.render_template(subject_template, data)
        body_text = self.render_template(body_text_template, data) if body_text_template else None
        body_html = self.render_template(body_html_template, data) if body_html_template else None
        return self.send_email(to_email, subject, body_text, body_html,
                               attachments=attachments, **kwargs)
