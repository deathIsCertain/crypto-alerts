import datetime
import json
import os

from .binance_client import BinanceClient
from .config import ALERT_PRICE_CHANGE_PCT, COINS, COIN_LABELS, EMAIL_TEMPLATE_FILE
from .gmail_sender import GmailSender
from .news_fetcher import NewsFetcher
from .telegram_alert import TelegramAlert

try:
    from jinja2 import Template
except ImportError:
    raise SystemExit("jinja2 is required. Install with: pip install jinja2")


def _fmt_price(value):
    return f"{value:,.2f}"


def build_html_report(snapshot, market_data):
    coins = []
    for symbol, data in snapshot.items():
        coins.append(
            {
                "label": COIN_LABELS.get(symbol, symbol),
                "price": _fmt_price(data["last_price"]),
                "change_24h": f"{data['price_change_pct']:+.2f}",
                "change_24h_class": "up" if data["price_change_pct"] >= 0 else "down",
                "change_7d": f"{data['change_7d_pct']:+.2f}",
                "change_7d_class": "up" if data["change_7d_pct"] >= 0 else "down",
                "high": _fmt_price(data["high_price"]),
                "low": _fmt_price(data["low_price"]),
            }
        )
    with open(EMAIL_TEMPLATE_FILE, "r", encoding="utf-8") as f:
        template = Template(f.read())
    now = datetime.datetime.now(datetime.timezone.utc).astimezone()
    report_date = now.strftime("%A, %B %d, %Y — %H:%M %Z")
    return template.render(
        report_date=report_date,
        coins=coins,
        fear_greed=market_data["fear_greed"],
        btc_onchain=market_data["btc_onchain"],
        news=market_data["news"],
    )


def send_daily_report():
    client = BinanceClient()
    fetcher = NewsFetcher()
    snapshot = client.get_market_snapshot()
    market_data = fetcher.get_aggregated()
    html = build_html_report(snapshot, market_data)
    subject = f"Daily Crypto Update — {datetime.date.today().strftime('%b %d, %Y')}"
    sender = GmailSender()
    sender.send_html_email(subject, html)
    return {"subject": subject, "email_sent": True}


def check_and_alert_price_moves(previous_snapshot, current_snapshot):
    if not previous_snapshot:
        return []
    alerts = []
    bot = TelegramAlert()
    for symbol, data in current_snapshot.items():
        prev = previous_snapshot.get(symbol)
        if not prev:
            continue
        prev_price = prev["last_price"]
        if prev_price == 0:
            continue
        move_pct = ((data["last_price"] - prev_price) / prev_price) * 100.0
        if abs(move_pct) >= ALERT_PRICE_CHANGE_PCT:
            direction = "up" if move_pct >= 0 else "down"
            msg = TelegramAlert.format_price_alert(
                symbol,
                COIN_LABELS.get(symbol, symbol),
                data["last_price"],
                data["price_change_pct"],
                data["change_7d_pct"],
                direction,
            )
            bot.send_message(msg)
            alerts.append(symbol)
    return alerts


def alert_top_news(news_limit=5):
    fetcher = NewsFetcher()
    news = fetcher.get_news(limit=news_limit)
    bot = TelegramAlert()
    sent = []
    for item in news:
        bot.send_message(TelegramAlert.format_news_alert(item))
        sent.append(item["title"])
    return sent


def load_state(state_file):
    if os.path.exists(state_file):
        with open(state_file, "r") as f:
            return json.load(f)
    return {}


def save_state(state_file, state):
    with open(state_file, "w") as f:
        json.dump(state, f)
