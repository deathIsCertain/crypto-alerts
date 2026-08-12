import smtplib
from email.message import EmailMessage

from .config import GMAIL_APP_PASSWORD, GMAIL_EMAIL, GMAIL_RECIPIENT

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587


class GmailSender:
    def __init__(self):
        if not GMAIL_EMAIL or not GMAIL_APP_PASSWORD:
            raise RuntimeError("GMAIL_EMAIL and GMAIL_APP_PASSWORD are required")

    def send_html_email(self, subject, html_body, to=None):
        to = to or GMAIL_RECIPIENT
        if not to:
            raise RuntimeError("GMAIL_RECIPIENT is not configured")
        message = EmailMessage()
        message["To"] = to
        message["From"] = GMAIL_EMAIL
        message["Subject"] = subject
        message.add_alternative(html_body, subtype="html")
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(GMAIL_EMAIL, GMAIL_APP_PASSWORD)
            server.send_message(message, from_addr=GMAIL_EMAIL, to_addrs=to)