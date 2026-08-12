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
    def format_price_alert(symbol, label, last_price, change_24h, change_7d, direction):
        arrow = "🟢" if change_24h >= 0 else "🔴"
        emoji = "📈" if direction == "up" else "📉"
        return (
            f"{emoji} <b>MAJOR PRICE MOVE</b>\n"
            f"{label} ({symbol})\n"
            f"Price: ${last_price:,.2f}\n"
            f"{arrow} 24h: {change_24h:+.2f}%\n"
            f"7d: {change_7d:+.2f}%\n"
        )

    @staticmethod
    def format_news_alert(item):
        return (
            f"📰 <b>MAJOR NEWS</b>\n"
            f"{item['title']}\n"
            f"<a href=\"{item.get('url', '#')}\">Read full article</a>\n"
        )
