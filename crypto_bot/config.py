import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

COINS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
COIN_LABELS = {
    "BTCUSDT": "Bitcoin (BTC)",
    "ETHUSDT": "Ethereum (ETH)",
    "SOLUSDT": "Solana (SOL)",
}

BINANCE_BASE_URL = "https://api.binance.com/api/v3"
BINANCE_KLINES_URL = f"{BINANCE_BASE_URL}/ticker/24hr"

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

ALERT_PRICE_CHANGE_PCT = 5.0

GMAIL_CREDENTIALS_FILE = os.path.join(BASE_DIR, "credentials.json")
GMAIL_TOKEN_FILE = os.path.join(BASE_DIR, "token.json")
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
GMAIL_RECIPIENT = os.getenv("GMAIL_RECIPIENT", "")
GMAIL_EMAIL = os.getenv("GMAIL_EMAIL", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")

EMAIL_TEMPLATE_FILE = os.path.join(BASE_DIR, "email_template.html")

TIMEZONE = "Asia/Kolkata"
REPORT_HOUR = 8
REPORT_MINUTE = 0
