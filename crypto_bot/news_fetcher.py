import os
import re
from html import unescape

import requests

from .config import COINS

RELEVANT_KEYWORDS = [
    "bitcoin",
    "btc",
    "ethereum",
    "eth",
    "solana",
    "sol",
    "crypto",
    "cryptocurrency",
    "cryptocurrencies",
    "blockchain",
    "stablecoin",
    "defi",
    "token",
    "altcoin",
    "exchange",
    "sec",
    "regulation",
    "federal reserve",
    "fed ",
    "halving",
    "mining",
]


def _strip_html(text):
    return unescape(re.sub(r"<[^>]+>", "", text or "")).strip()


class NewsFetcher:
    def __init__(self):
        self.session = requests.Session()
        self.cryptopanic_key = os.getenv("CRYPTOPANIC_API_KEY", "")

    def get_fear_greed(self):
        try:
            url = "https://api.alternative.me/fng/"
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()["data"][0]
            return {
                "value": data["value"],
                "classification": data["value_classification"],
            }
        except Exception:
            return {"value": "N/A", "classification": "N/A"}

    def get_btc_onchain(self):
        try:
            url = "https://mempool.space/api/blocks/tip/height"
            block_height = self.session.get(url, timeout=15).text
            url = "https://mempool.space/api/v1/fees/recommended"
            fees = self.session.get(url, timeout=15).json()
            return {
                "block_height": block_height,
                "fastest_fee_sat": fees.get("fastestFee", "N/A"),
            }
        except Exception:
            return {"block_height": "N/A", "fastest_fee_sat": "N/A"}

    @staticmethod
    def _is_relevant(title):
        low = title.lower()
        return any(kw in low for kw in RELEVANT_KEYWORDS)

    @staticmethod
    def _parse_rss(xml_text):
        items = []
        for m in re.finditer(r"<item>(.*?)</item>", xml_text, re.DOTALL):
            block = m.group(1)
            title_m = re.search(r"<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", block, re.DOTALL)
            link_m = re.search(r"<link>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</link>", block, re.DOTALL)
            pub_m = re.search(
                r"<pubDate>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</pubDate>", block, re.DOTALL
            )
            desc_m = re.search(
                r"<description>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</description>", block, re.DOTALL
            )
            if not title_m:
                continue
            title = _strip_html(title_m.group(1))
            link = _strip_html(link_m.group(1)) if link_m else ""
            pub = _strip_html(pub_m.group(1)) if pub_m else ""
            desc = _strip_html(desc_m.group(1)) if desc_m else ""
            if not title or not NewsFetcher._is_relevant(title):
                continue
            items.append({"title": title, "url": link, "published_at": pub, "description": desc})
        return items

    def _fetch_rss(self, url):
        resp = self.session.get(url, timeout=15)
        resp.raise_for_status()
        return self._parse_rss(resp.text)

    def _get_rss_news(self, limit=8):
        feeds = [
            "https://www.coindesk.com/arc/outboundfeeds/rss/",
            "https://cointelegraph.com/rss",
            "https://news.google.com/rss/search?q=bitcoin%20OR%20ethereum%20OR%20solana&hl=en-US&gl=US&ceid=US:en",
        ]
        seen = set()
        news = []
        for url in feeds:
            try:
                for item in self._fetch_rss(url):
                    if item["title"] in seen:
                        continue
                    seen.add(item["title"])
                    news.append(item)
            except Exception:
                continue
            if len(news) >= limit:
                break
        return news[:limit]

    def _get_cryptopanic_news(self, limit=8):
        try:
            symbols = ",".join(coin.replace("USDT", "") for coin in COINS)
            url = "https://cryptopanic.com/api/v1/posts/"
            params = {
                "auth_token": self.cryptopanic_key,
                "currencies": symbols,
                "kind": "news",
                "filter": "hot",
                "public": "true",
                "limit": limit,
            }
            resp = self.session.get(url, params=params, timeout=15)
            resp.raise_for_status()
            posts = resp.json().get("results", [])
            return [
                {
                    "title": post.get("title", ""),
                    "url": post.get("url", ""),
                    "source": post.get("source", {}).get("title", ""),
                    "published_at": post.get("published_at", ""),
                }
                for post in posts
                if post.get("title")
            ]
        except Exception:
            return []

    def get_news(self, limit=8):
        news = self._get_cryptopanic_news(limit) if self.cryptopanic_key else []
        if len(news) < limit:
            rss_news = self._get_rss_news(limit)
            seen_titles = {n["title"] for n in news}
            news.extend(n for n in rss_news if n["title"] not in seen_titles)
        return news[:limit]

    def get_aggregated(self):
        return {
            "fear_greed": self.get_fear_greed(),
            "btc_onchain": self.get_btc_onchain(),
            "news": self.get_news(),
        }
