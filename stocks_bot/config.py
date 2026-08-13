import datetime
import os
from dotenv import load_dotenv
from zoneinfo import ZoneInfo

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

YAHOO_BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart"

INDICES = ["^NSEI", "^BSESN"]
INDICES_LABELS = {
    "^NSEI": "NIFTY 50",
    "^BSESN": "SENSEX",
}

SECTOR_INDICES = [
    "^CNXIT",
    "^CNXPHARMA",
    "^CNXFMCG",
    "^CNXAUTO",
    "^CNXMETAL",
    "^CNXENERGY",
    "^CNXINFRA",
    "^CNXREALTY",
    "^CNXMEDIA",
    "^CNXPSUBANK",
    "^CNXFIN",
]
SECTOR_LABELS = {
    "^CNXIT": "NIFTY IT",
    "^CNXPHARMA": "NIFTY Pharma",
    "^CNXFMCG": "NIFTY FMCG",
    "^CNXAUTO": "NIFTY Auto",
    "^CNXMETAL": "NIFTY Metal",
    "^CNXENERGY": "NIFTY Energy",
    "^CNXINFRA": "NIFTY Infra",
    "^CNXREALTY": "NIFTY Realty",
    "^CNXMEDIA": "NIFTY Media",
    "^CNXPSUBANK": "NIFTY PSU Bank",
    "^CNXFIN": "NIFTY Financial Services",
}

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/free")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
SUMMARIZE_NEWS = os.getenv("SUMMARIZE_NEWS", "true").lower() in ("1", "true", "yes")

ALERT_PRICE_CHANGE_PCT = 3.0

GMAIL_EMAIL = os.getenv("GMAIL_EMAIL", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
GMAIL_RECIPIENT = os.getenv("GMAIL_RECIPIENT", "")

EMAIL_TEMPLATE_FILE = os.path.join(BASE_DIR, "email_template.html")

TIMEZONE = "Asia/Kolkata"
REPORT_HOUR = 8
REPORT_MINUTE = 30


def ist_now():
    return datetime.datetime.now(ZoneInfo(TIMEZONE))