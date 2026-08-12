import html
import re

import requests

from .config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, OPENROUTER_MODEL, SUMMARIZE_NEWS

MAX_CONTENT_CHARS = 5000
SUMMARY_PROMPT = (
    "You are a crypto news analyst. Summarize the following news article in 2-3 tight sentences "
    "for a Telegram alert. Lead with the single most important fact for a crypto trader "
    "(price impact, regulation, adoption, hack, etc.), then one supporting detail. "
    "Do not use markdown, emojis, or bullet lists. Article:\n\n{content}"
)


def _fetch_article_text(url):
    try:
        resp = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        text = re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>", " ", resp.text)
        text = re.sub(r"<[^>]+>", " ", text)
        text = html.unescape(re.sub(r"\s+", " ", text)).strip()
        return text[:MAX_CONTENT_CHARS]
    except Exception:
        return ""


def _summarize_via_openrouter(title, content):
    if not OPENROUTER_API_KEY:
        return ""
    url = f"{OPENROUTER_BASE_URL}/chat/completions"
    messages = [
        {"role": "system", "content": "You write concise, useful news summaries. Only the summary, nothing else."},
        {"role": "user", "content": SUMMARY_PROMPT.format(content=f"{title}\n\n{content}")},
    ]
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": messages,
        "max_tokens": 180,
        "temperature": 0.3,
    }
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=60)
        resp.raise_for_status()
        summary = resp.json()["choices"][0]["message"]["content"].strip()
        return summary
    except Exception:
        return ""


def fetch_article_text(url):
    return _fetch_article_text(url)


def summarize_article(item):
    if not SUMMARIZE_NEWS:
        return item["title"]
    content = _fetch_article_text(item.get("url", ""))
    if not content:
        content = (item.get("description") or "").strip()
    if not content:
        return item["title"]
    summary = _summarize_via_openrouter(item.get("title", ""), content)
    return summary or item["title"]