import json
import os

from jinja2 import Template

from .config import ALERT_PRICE_CHANGE_PCT, EMAIL_TEMPLATE_FILE, INDICES, INDICES_LABELS, SECTOR_INDICES, SECTOR_LABELS, ist_now
from .gmail_sender import GmailSender
from .news_fetcher import IndiaNewsFetcher
from .telegram_alert import TelegramAlert
from .yahoo_client import YahooClient


def _fmt(value):
    return f"{value:,.2f}"


def _row(sym, data):
    return {
        "label": INDICES_LABELS.get(sym, SECTOR_LABELS.get(sym, sym)),
        "price": _fmt(data["price"]),
        "change_pct": f"{data['change_pct']:+.2f}",
        "change_class": "up" if data["change_pct"] >= 0 else "down",
        "change_5d": f"{data['change_5d_pct']:+.2f}",
        "change5_class": "up" if data["change_5d_pct"] >= 0 else "down",
    }


def build_html_report(snapshot, news):
    indices_rows = [_row(s, snapshot[s]) for s in INDICES if s in snapshot]
    sector_rows = [_row(s, snapshot[s]) for s in SECTOR_INDICES if s in snapshot]
    with open(EMAIL_TEMPLATE_FILE, "r", encoding="utf-8") as f:
        template = Template(f.read())
    now = ist_now()
    report_date = now.strftime("%A, %B %d, %Y — %H:%M %Z")
    return template.render(
        report_date=report_date,
        indices=indices_rows,
        sectors=sector_rows,
        news=news,
    )


def send_daily_report():
    client = YahooClient()
    snapshot = client.full_snapshot()
    news = IndiaNewsFetcher().get_news(5)
    html = build_html_report(snapshot, news)
    subject = f"India Market Update — {ist_now().strftime('%b %d, %Y')}"
    GmailSender().send_html_email(subject, html)
    return {"subject": subject, "email_sent": True}


def check_and_alert_price_moves(previous_snapshot, current_snapshot):
    if not previous_snapshot:
        return []
    alerts = []
    bot = TelegramAlert()
    for sym, data in current_snapshot.items():
        prev = previous_snapshot.get(sym)
        if not prev or prev.get("price") == 0:
            continue
        move_pct = ((data["price"] - prev["price"]) / prev["price"]) * 100.0
        if abs(move_pct) >= ALERT_PRICE_CHANGE_PCT:
            direction = "up" if move_pct >= 0 else "down"
            label = INDICES_LABELS.get(sym, SECTOR_LABELS.get(sym, sym.replace(".NS", "")))
            msg = TelegramAlert.format_price_alert(label, sym, data["price"], data["change_pct"], data["change_5d_pct"], direction)
            bot.send_message(msg)
            alerts.append(sym)
    return alerts


def load_state(state_file):
    if os.path.exists(state_file):
        with open(state_file, "r") as f:
            return json.load(f)
    return {}


def save_state(state_file, state):
    with open(state_file, "w") as f:
        json.dump(state, f)