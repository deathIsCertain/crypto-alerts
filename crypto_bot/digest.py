import datetime
import io
import json
import os
import re

import requests

from .config import (
    GMAIL_APP_PASSWORD,
    GMAIL_EMAIL,
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    OPENROUTER_MODEL,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHANNEL_ID,
)
from .gmail_sender import GmailSender
from .summarizer import summarize_article
from .telegram_alert import TelegramAlert

try:
    from jinja2 import Template
except ImportError:
    raise SystemExit("jinja2 is required. Install with: pip install jinja2")

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
except ImportError:
    raise SystemExit("reportlab is required. Install with: pip install reportlab")


def _load_json(path):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {}


def _save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f)


def pick_top3(articles):
    if len(articles) <= 3:
        return [(a["title"], a.get("url", ""), "Among the top stories today") for a in articles]
    if not OPENROUTER_API_KEY:
        return [(a["title"], a.get("url", ""), "") for a in articles[:3]]
    listing = "\n".join(f"{i}: {a['title']}" for i, a in enumerate(articles))
    prompt = (
        "Below is a numbered list of today's news headlines. Pick the 3 most impactful for a "
        "trader or investor. Reply with exactly 3 lines, each in the format:\n"
        "INDEX|one-line reason\n"
        "Use only indices from the list. No markdown, no bullets, no extra text.\n\n{listing}\n"
    ).format(listing=listing)
    try:
        resp = requests.post(
            f"{OPENROUTER_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": OPENROUTER_MODEL,
                "messages": [
                    {"role": "system", "content": "You pick the most impactful news. Reply in the exact format requested."},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 200,
                "temperature": 0.2,
            },
            timeout=60,
        )
        resp.raise_for_status()
        text = (resp.json()["choices"][0]["message"]["content"] or "").strip()
        picks = []
        for line in text.splitlines():
            for match in re.finditer(r"\b(\d+)\b\s*[|:.\-\s]?\s*(.*)", line.strip()):
                idx = int(match.group(1))
                reason = match.group(2).strip()
                if 0 <= idx < len(articles) and idx not in {p[2] for p in picks}:
                    picks.append((articles[idx]["title"], articles[idx].get("url", ""), reason, idx))
                    break
            if len(picks) >= 3:
                break
        if len(picks) >= 3:
            return [(t, u, r) for t, u, r, _ in picks[:3]]
    except Exception:
        pass
    return [(a["title"], a.get("url", ""), "") for a in articles[:3]]


def _render_daily_html(articles, top3, summaries_by_title, email_template_file):
    with open(email_template_file, "r", encoding="utf-8") as f:
        template = Template(f.read())
    now = datetime.datetime.now(datetime.timezone.utc).astimezone()
    report_date = now.strftime("%A, %B %d, %Y — %H:%M %Z")
    top_rows = [{"title": t, "url": u, "reason": r} for t, u, r in top3]
    news_rows = [
        {
            "title": a["title"],
            "url": a.get("url", ""),
            "summary": summaries_by_title.get(a["title"], a["title"]),
            "date": (a.get("captured_at") or "")[:10],
        }
        for a in articles
    ]
    return template.render(report_date=report_date, top3=top_rows, news=news_rows)


def send_daily_digest(state_file, email_template_file):
    state = _load_json(state_file)
    articles = state.get("articles", [])
    if not articles:
        return {"email_sent": False, "articles": 0}

    summaries = {}
    for a in articles:
        summaries[a["title"]] = summarize_article(a)

    top3 = pick_top3(articles)
    html = _render_daily_html(articles, top3, summaries, email_template_file)
    subject = f"Crypto News Digest — {datetime.date.today().strftime('%b %d, %Y')}"

    if not (GMAIL_EMAIL and GMAIL_APP_PASSWORD):
        raise RuntimeError("GMAIL_EMAIL and GMAIL_APP_PASSWORD are required")
    GmailSender().send_html_email(subject, html)

    archive = state.get("weekly_archive", [])
    for a in articles:
        archive.append(
            {
                "title": a["title"],
                "url": a.get("url", ""),
                "description": a.get("description", ""),
                "content": a.get("content", ""),
                "summary": summaries.get(a["title"], ""),
                "captured_at": a.get("captured_at", ""),
            }
        )
    state["weekly_archive"] = archive[-1500:]
    state["articles"] = []
    _save_json(state_file, state)
    return {"email_sent": True, "articles": len(articles)}


def _ff(style_name):
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            name = f"Custom{style_name}"
            pdfmetrics.registerFont(TTFont(name, path))
            return name
    return "Helvetica"


def _build_weekly_pdf(archive):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=1.5 * cm, leftMargin=1.5 * cm, topMargin=1.5 * cm, bottomMargin=1.5 * cm)
    styles = getSampleStyleSheet()
    font = _ff("Sans")
    title_style = ParagraphStyle("Title", fontName=font, fontSize=16, leading=20, textColor=colors.HexColor("#f7931a"))
    day_style = ParagraphStyle("Day", fontName=font, fontSize=13, leading=16, spaceBefore=10, spaceAfter=4, textColor=colors.HexColor("#1f9d55"))
    h_style = ParagraphStyle("H", fontName=font, fontSize=11, leading=14, spaceBefore=8, textColor=colors.HexColor("#58a6ff"))
    body_style = ParagraphStyle("Body", fontName=font, fontSize=9.5, leading=13, alignment=TA_LEFT)
    story = [Paragraph("Crypto Weekly News Archive", title_style)]
    story.append(Paragraph(datetime.datetime.now(datetime.timezone.utc).astimezone().strftime("%A, %B %d, %Y"), day_style))

    by_day = {}
    for a in archive:
        day = (a.get("captured_at") or "")[:10] or "Unknown"
        by_day.setdefault(day, []).append(a)

    for day in sorted(by_day, reverse=True):
        story.append(Paragraph(day, day_style))
        for a in by_day[day]:
            esc_title = a["title"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            story.append(Paragraph(esc_title, h_style))
            if a.get("summary"):
                esc_sum = a["summary"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                story.append(Paragraph(f"<b>Summary:</b> {esc_sum}", body_style))
            content = (a.get("content") or "").strip()
            if content:
                esc = content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                story.append(Paragraph(esc, body_style))
            if a.get("url"):
                story.append(Paragraph(f"Link: {a['url']}", body_style))
            story.append(Spacer(1, 6))
    doc.build(story)
    buf.seek(0)
    return buf.getvalue()


def send_weekly_pdf(state_file):
    state = _load_json(state_file)
    archive = state.get("weekly_archive", [])
    now = datetime.datetime.now(datetime.timezone.utc).astimezone()
    if now.strftime("%A") != "Sunday" or not archive:
        return {"pdf_sent": False, "articles": len(archive)}
    if not (TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL_ID):
        raise RuntimeError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL_ID are required")
    pdf_bytes = _build_weekly_pdf(archive)
    filename = f"crypto_weekly_{now.strftime('%Y-%m-%d')}.pdf"
    TelegramAlert().send_document(pdf_bytes, filename, f"Crypto News — past 7 days ({len(archive)} articles)")
    state["weekly_archive"] = []
    _save_json(state_file, state)
    return {"pdf_sent": True, "articles": len(archive)}