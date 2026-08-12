import re
from html import unescape

import requests

from .config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, OPENROUTER_MODEL, SUMMARIZE_NEWS

INDIA_KEYWORDS = [
    "nifty",
    "sensex",
    "share market",
    "stock market",
    "india",
    "rupee",
    "sebi",
    "rbi",
    "reliance",
    "tcs",
    "infosys",
    "hdfc",
    "icici",
    "sbi",
    "ipo",
    "lakh",
    "crore",
    "sensex",
    "bse",
    "nse",
]

INDIAN_NEWS_FEEDS = [
    "https://www.moneycontrol.com/rss/businessmarket.xml",
    "https://timesofindia.indiatimes.com/rssfeeds/1898058.cms",
    "https://economictimes.indiatimes.com/rssfeeds/1977021501.cms",
    "https://news.google.com/rss/search?q=nifty+OR+sensex+OR+stock+market+india&hl=en-IN&gl=IN&ceid=IN:en",
]


def _strip_html(text):
    cleaned = re.sub(r"<[^>]+>", " ", text or "")
    cleaned = cleaned.replace("]]>", "").replace("<![CDATA[", "").strip()
    return unescape(re.sub(r"\s+", " ", cleaned)).strip()


class IndiaNewsFetcher:
    def __init__(self):
        self.session = requests.Session()

    @staticmethod
    def _is_relevant(title):
        low = title.lower()
        return any(kw in low for kw in INDIA_KEYWORDS)

    @staticmethod
    def _parse_rss(xml_text):
        items = []
        for m in re.finditer(r"<item>(.*?)</item>", xml_text, re.DOTALL):
            block = m.group(1)
            title_m = re.search(r"<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", block, re.DOTALL)
            link_m = re.search(r"<link>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</link>", block, re.DOTALL)
            desc_m = re.search(
                r"<description>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</description>", block, re.DOTALL
            )
            if not title_m:
                continue
            title = _strip_html(title_m.group(1))
            link = _strip_html(link_m.group(1)) if link_m else ""
            desc = _strip_html(desc_m.group(1)) if desc_m else ""
            if not title or not IndiaNewsFetcher._is_relevant(title):
                continue
            items.append({"title": title, "url": link, "description": desc})
        return items

    def get_news(self, limit=8):
        seen = set()
        news = []
        for url in INDIAN_NEWS_FEEDS:
            try:
                resp = self.session.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
                resp.raise_for_status()
                for item in self._parse_rss(resp.text):
                    if item["title"] in seen:
                        continue
                    seen.add(item["title"])
                    news.append(item)
            except Exception:
                continue
            if len(news) >= limit:
                break
        return news[:limit]

    @staticmethod
    def summarize(item):
        if not SUMMARIZE_NEWS:
            return item["title"]
        content = (item.get("description") or "").strip()
        if not content:
            return item["title"]
        prompt = (
            "Summarize this Indian stock market news in 2-3 tight sentences for a Telegram alert. "
            "Lead with the most important fact for an investor (index movement, stock impact, "
            "regulation, earnings, etc.). No markdown or emojis.\n\n"
            f"Headline: {item.get('title', '')}\n\n{content}"
        )
        try:
            resp = requests.post(
                f"{OPENROUTER_BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": OPENROUTER_MODEL,
                    "messages": [
                        {"role": "system", "content": "You write concise useful stock news summaries."},
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": 180,
                    "temperature": 0.3,
                },
                timeout=60,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception:
            return item["title"]