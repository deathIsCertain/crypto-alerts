import html
import re

import requests

from .config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, OPENROUTER_MODEL

MAX_CONTENT_CHARS = 5000


def fetch_article_text(url):
    try:
        resp = requests.get(
            url, timeout=20, headers={"User-Agent": "Mozilla/5.0 (compatible; NewsBot/1.0)"}
        )
        resp.raise_for_status()
        text = re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>", " ", resp.text)
        text = re.sub(r"<[^>]+>", " ", text)
        text = html.unescape(re.sub(r"\s+", " ", text)).strip()
        return text[:MAX_CONTENT_CHARS]
    except Exception:
        return ""


def summarize_via_openrouter(full_text):
    if not OPENROUTER_API_KEY:
        return ""
    url = f"{OPENROUTER_BASE_URL}/chat/completions"
    prompt = (
        "You are an Indian stock market analyst. Summarize the following news article in 2-3 tight "
        "sentences for a daily email digest. Lead with the single most important fact for an "
        "investor (index movement, stock impact, earnings, regulation, IPO, etc.), then one "
        "supporting detail. Do not use markdown, emojis, or bullet lists.\n\n"
        f"{full_text}"
    )
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": "You write concise, useful stock news summaries. Only the summary, nothing else."},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 200,
        "temperature": 0.3,
    }
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=60)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return ""


def summarize_article(item):
    content = (item.get("content") or "").strip()
    if not content:
        content = (item.get("description") or "").strip()
    if not content:
        return item.get("title", "")
    full_text = f"{item.get('title', '')}\n\n{content}"
    return summarize_via_openrouter(full_text) or item.get("title", "")