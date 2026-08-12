import requests

from .config import TELEGRAM_API_URL, TELEGRAM_CHANNEL_ID


class TelegramAlert:
    def __init__(self, channel_id=None):
        self.channel_id = channel_id or TELEGRAM_CHANNEL_ID

    def send_message(self, text, parse_mode="HTML"):
        if not self.channel_id:
            raise RuntimeError("TELEGRAM_CHANNEL_ID is not configured")
        url = f"{TELEGRAM_API_URL}/sendMessage"
        payload = {"chat_id": self.channel_id, "text": text, "parse_mode": parse_mode}
        resp = requests.post(url, json=payload, timeout=15)
        resp.raise_for_status()
        return resp.json()

    def send_document(self, file_bytes, filename, caption=""):
        if not self.channel_id:
            raise RuntimeError("TELEGRAM_CHANNEL_ID is not configured")
        url = f"{TELEGRAM_API_URL}/sendDocument"
        files = {"document": (filename, file_bytes, "application/pdf")}
        data = {"chat_id": self.channel_id}
        if caption:
            data["caption"] = caption
        resp = requests.post(url, files=files, data=data, timeout=60)
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def format_price_alert(label, symbol, price, change_pct, change_5d_pct, direction):
        arrow = "🟢" if change_pct >= 0 else "🔴"
        emoji = "📈" if direction == "up" else "📉"
        return (
            f"{emoji} <b>MAJOR MOVE</b>\n"
            f"{label} ({symbol})\n"
            f"Price: ₹{price:,.2f}\n"
            f"{arrow} Today: {change_pct:+.2f}%\n"
            f"5d: {change_5d_pct:+.2f}%\n"
        )

    @staticmethod
    def format_news_alert(item):
        return (
            f"📰 <b>INDIAN MARKET NEWS</b>\n"
            f"{item['title']}\n"
            f"<a href=\"{item.get('url', '#')}\">Read full article</a>\n"
        )