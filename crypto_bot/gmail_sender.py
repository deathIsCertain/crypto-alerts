import base64
import os
import smtplib
from email.message import EmailMessage

from .config import GMAIL_RECIPIENT

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError

    from .config import GMAIL_CREDENTIALS_FILE, GMAIL_SCOPES, GMAIL_TOKEN_FILE

    _GOOGLE_IMPORT_OK = True
except ImportError:
    _GOOGLE_IMPORT_OK = False

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587


class GmailSender:
    def __init__(self):
        self.smtp_user = os.getenv("GMAIL_EMAIL", "")
        self.smtp_app_password = os.getenv("GMAIL_APP_PASSWORD", "")
        if self.smtp_user and self.smtp_app_password:
            self.mode = "smtp"
        elif _GOOGLE_IMPORT_OK:
            self.mode = "oauth"
            self.creds = self._get_credentials()
            self.service = build("gmail", "v1", credentials=self.creds)
        else:
            raise RuntimeError(
                "No Gmail credentials configured. Set GMAIL_EMAIL + GMAIL_APP_PASSWORD, "
                "or install google libraries + credentials.json for OAuth."
            )

    def _get_credentials(self):
        creds = None
        if os.path.exists(GMAIL_TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(GMAIL_TOKEN_FILE, GMAIL_SCOPES)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            self._save_token(creds)
        if not creds:
            if not os.path.exists(GMAIL_CREDENTIALS_FILE):
                raise RuntimeError(
                    "credentials.json not found. Set up Google Cloud Gmail API OAuth first."
                )
            flow = InstalledAppFlow.from_client_secrets_file(GMAIL_CREDENTIALS_FILE, GMAIL_SCOPES)
            creds = flow.run_local_server(port=0)
            self._save_token(creds)
        return creds

    @staticmethod
    def _save_token(creds):
        with open(GMAIL_TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

    def _send_smtp(self, message, to):
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(self.smtp_user, self.smtp_app_password)
            server.send_message(message, from_addr=self.smtp_user, to_addrs=to)

    def _send_oauth(self, message):
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        try:
            self.service.users().messages().send(userId="me", body={"raw": raw}).execute()
        except HttpError as e:
            raise RuntimeError(f"Failed to send email: {e}") from e

    def send_html_email(self, subject, html_body, to=None):
        to = to or GMAIL_RECIPIENT
        if not to:
            raise RuntimeError("GMAIL_RECIPIENT is not configured")
        message = EmailMessage()
        message["To"] = to
        message["From"] = self.smtp_user or "me"
        message["Subject"] = subject
        message.add_alternative(html_body, subtype="html")
        if self.mode == "smtp":
            self._send_smtp(message, to)
        else:
            self._send_oauth(message)
