# Crypto & Stock Alerts

Automated cryptocurrency and Indian stock market alerts, daily reports, news digests, and weekly PDF archives — orchestrated entirely by GitHub Actions and run on a scheduled cron basis. No server is needed; every job runs in a fresh Ubuntu runner.

Two independent "bots" live in the same repo:

| Bot | Package | Domain | Market data | News sources |
|-----|---------|--------|-------------|--------------|
| Crypto | `crypto_bot/` | BTC / ETH / SOL | Binance | CryptoPanic + CoinDesk / CoinTelegraph / Google News RSS |
| Stocks | `stocks_bot/` | NIFTY 50, SENSEX + 11 sector indices | Yahoo Finance | Moneycontrol / TOI / Economic Times / Google News RSS |

---

## What it delivers

- **Daily HTML report email** — market snapshot (prices, 24h/7d change, high/low) + sentiment/on-chain data (crypto) or index/sector table (stocks).
- **News digests** — collected headlines are summarized by an LLM (OpenRouter), the top-3 "most impactful" are picked, and a styled HTML email is sent; top-3 reasoning included.
- **Price-move alerts** — Telegram message when a coin/index moves more than a threshold (5% crypto, 3% stocks) since the last check (runs every 15 minutes).
- **News alerts** — Telegram messages for each new relevant headline (crypto twice daily, stocks every 6h).
- **Weekly PDF** — every Sunday, the past 7 days of collected articles (with LLM summaries) are rendered into a PDF and posted to Telegram.

---

## Architecture

```
GitHub Actions (cron / workflow_dispatch)
    │
    ├── crypto workflows                stocks workflows
    │   ├─ Price Monitor (every 15m)    ├─ India Stocks Price Monitor (every 15m)
    │   ├─ News Alerts (2×/day)         ├─ India Stocks News Alerts (every 6h)
    │   ├─ Daily Crypto Report (08:00)  ├─ India Stocks Daily Report (08:30)
    │   └─ Crypto News Digest (06:00)   └─ India Stocks News Digest (21:00)
    │
    ▼
run_crypto_bot.py / run_stocks_bot.py  (argparse CLI entry points)
    │
    ├── Market clients    BinanceClient / YahooClient   (fetch prices)
    ├── News fetchers     NewsFetcher / IndiaNewsFetcher (RSS + CryptoPanic)
    ├── LLM summarizer    summarizer.py (OpenRouter chat completions)
    ├── Notifiers         TelegramAlert, GmailSender (SMTP/OAuth)
    └── State             JSON state files committed back to the repo
```

All times above are **IST** (Asia/Kolkata). Cron expressions in the workflows are written in **UTC** (e.g. the 06:00 IST digest is `30 0 * * *`). Email timestamps/subjects are computed with the `ist_now()` helper so they always show IST.

---

## Directory layout

```
.
├── .github/workflows/          # 8 GitHub Actions workflows (4 per bot)
├── crypto_bot/                 # Crypto bot (Python package)
│   ├── run_crypto_bot.py       # CLI entry point
│   ├── config.py               # env config, constants, ist_now() helper
│   ├── binance_client.py       # Binance market data (24h ticker, klines)
│   ├── news_fetcher.py         # CryptoPanic + RSS, keyword relevance filter
│   ├── summarizer.py           # fetch article text + OpenRouter summarization
│   ├── digest.py               # daily digest email + weekly PDF
│   ├── report.py               # daily report email, price-move alerts, state I/O
│   ├── gmail_sender.py         # Gmail SMTP (with OAuth fallback)
│   ├── telegram_alert.py       # Telegram sendMessage / sendDocument
│   ├── scheduler.py            # optional local APScheduler runner
│   ├── email_template.html     # daily report Jinja2 template
│   ├── digest_email_template.html  # digest Jinja2 template
│   ├── requirements.txt
│   └── .env.example
├── stocks_bot/                 # Stocks bot (mirrors the crypto structure)
│   ├── run_stocks_bot.py
│   ├── config.py
│   ├── yahoo_client.py         # Yahoo Finance quotes (NIFTY/SENSEX/sectors)
│   ├── news_fetcher.py         # Indian market RSS feeds
│   ├── summarizer.py
│   ├── digest.py
│   ├── report.py
│   ├── gmail_sender.py
│   ├── telegram_alert.py
│   ├── email_template.html
│   ├── digest_email_template.html
│   ├── requirements.txt
│   └── .env.example
├── ci_state.json               # Crypto shared CI state (prices + news)
├── stocks_ci_state.json        # Stocks shared CI state
├── stocks_news_state.json      # Stocks news/digest state
├── stocks_price_state.json     # Stocks price monitor state
└── .gitignore
```

---

## Data flow, end to end

### 1. Price monitoring (every 15 min)
1. Workflow checks out the repo (so the latest committed state is present).
2. `--ci-check` fetches a market snapshot:
   - Crypto: `BinanceClient.get_market_snapshot()` → last price, 24h %, high/low, volume, 7d % (computed from 30 daily klines). Fails over between the public `api.binance.com` and `data-api.binance.vision`.
   - Stocks: `YahooClient.get_market_snapshot()` → price, change %, 5d %, open/high/low, prev close for NIFTY 50, SENSEX and 11 sector indices.
3. `check_and_alert_price_moves(previous, current)` compares against the stored `last_snapshot`; if any symbol moved ≥ threshold (5% crypto / 3% stocks), a Telegram message is sent (`format_price_alert`).
4. The new snapshot + `last_checked` timestamp are written back to the state JSON and **committed to the repo** (with a pull-rebase-push retry loop to survive concurrent workflow pushes).

### 2. News collection & Telegram alerts
1. `--ci-news N` fetches the latest headlines:
   - Crypto: CryptoPanic API (if `CRYPTOPANIC_API_KEY` set) + CoinDesk/CoinTelegraph/Google News RSS, filtered by `RELEVANT_KEYWORDS` (bitcoin, eth, sec, regulation, …).
   - Stocks: Moneycontrol / TOI / Economic Times / Google News RSS, filtered by `INDIA_KEYWORDS` (nifty, sensex, ipo, reliance, …).
2. Titles already in `sent_news` (last 200) or in the current `articles` queue are skipped (dedup).
3. Each new item's article text is fetched (`fetch_article_text`, first 5000 chars) and stored in `articles` (capped at 500); a Telegram alert with the headline + link is posted.
4. State is saved and committed.

### 3. Daily report (crypto 08:00 IST, stocks 08:30 IST)
1. `--send-report` builds a fresh snapshot plus:
   - Crypto: Fear & Greed index (`alternative.me`) and BTC on-chain data (block height + recommended fees from `mempool.space`), plus the latest news.
   - Stocks: index + sector table.
2. Jinja2 renders `email_template.html` with `report_date` set from `ist_now()` (IST).
3. `GmailSender.send_html_email()` sends via Gmail SMTP (app password) to `GMAIL_RECIPIENT`. Crypto's sender falls back to the Gmail API (OAuth) if SMTP env vars are absent.

### 4. Daily digest (crypto 06:00 IST, stocks 21:00 IST)
1. `--send-digest` loads the `articles` accumulated since the last digest.
2. Each article is summarized by OpenRouter (`summarizer.summarize_article`), 2–3 sentences, trader-focused.
3. `pick_top3` asks the LLM to choose the 3 most impactful headlines with a one-line reason each.
4. `digest_email_template.html` is rendered with the top-3 and full news list + summaries.
5. Email is sent, then the articles are moved into `weekly_archive` (capped at 1500) and the pending queue is cleared; state is committed.

### 5. Weekly PDF (Sunday only, via the same digest workflow)
1. `--send-weekly-pdf` checks `ist_now().strftime("%A") == "Sunday"`; if not, it no-ops.
2. `reportlab` builds a PDF from `weekly_archive`: title page, day-grouped articles, each with headline, LLM summary, full content and link.
3. PDF is uploaded to the Telegram channel (`sendDocument`), then `weekly_archive` is cleared and committed.

---

## GitHub Actions workflows

| Workflow | Schedule (UTC) | IST | Runs |
|----------|----------------|-----|------|
| Price Monitor | `*/15 * * * *` | every 15 min | `--ci-check` |
| India Stocks Price Monitor | `*/15 * * * *` | every 15 min | `--ci-check` |
| News Alerts | `0 1 * * *`, `0 13 * * *` | 06:30, 18:30 | `--ci-news 5` |
| India Stocks News Alerts | `30 */6 * * *` | 06:00, 12:00, 18:00, 00:00 | `--ci-news 5` |
| Daily Crypto Report | `30 2 * * *` | 08:00 | `--send-report` |
| India Stocks Daily Report | `0 3 * * *` | 08:30 | `--send-report` |
| Crypto News Digest | `30 0 * * *` | 06:00 | `--send-digest`, `--send-weekly-pdf` |
| India Stocks News Digest | `30 15 * * *` | 21:00 | `--send-digest`, `--send-weekly-pdf` |

Every workflow that mutates state (`Price Monitor`, `News Alerts`, digests) ends with a **"Commit updated state (with retry)"** step: it stages the state JSON, commits, and pushes with a `git pull --rebase --autostash` retry loop (3 attempts) to tolerate concurrent runs. All workflows accept `workflow_dispatch` for manual runs.

---

## Secrets (GitHub repository secrets)

| Secret | Used for |
|--------|----------|
| `TELEGRAM_BOT_TOKEN` | Telegram bot for alerts + weekly PDF |
| `TELEGRAM_CHANNEL_ID` | Telegram channel/user to post to |
| `GMAIL_EMAIL` | Gmail sender address (SMTP login + `From`) |
| `GMAIL_APP_PASSWORD` | 16-char Gmail app password (SMTP) |
| `GMAIL_RECIPIENT` | Email recipient for reports/digests |
| `OPENROUTER_API_KEY` | LLM summarization + top-3 selection |
| `CRYPTOPANIC_API_KEY` | (optional) crypto news source |

`GMAIL_EMAIL`, `GMAIL_APP_PASSWORD` and `GMAIL_RECIPIENT` are shared by both bots. Secrets are injected only as workflow `env`, never stored in the repo. `.env` files are gitignored; `.env.example` documents the variables for local runs.

---

## Local usage

```bash
# Crypto
pip install -r crypto_bot/requirements.txt
cp crypto_bot/.env.example crypto_bot/.env   # fill in values
python -m crypto_bot.run_crypto_bot --send-report      # daily report
python -m crypto_bot.run_crypto_bot --send-digest      # news digest
python -m crypto_bot.run_crypto_bot --ci-news 5        # collect + Telegram news
python -m crypto_bot.run_crypto_bot --ci-check         # price-move check
python -m crypto_bot.run_crypto_bot --scheduler        # local scheduler loop

# Stocks
pip install -r stocks_bot/requirements.txt
python -m stocks_bot.run_stocks_bot --send-report
python -m stocks_bot.run_stocks_bot --send-digest
python -m stocks_bot.run_stocks_bot --ci-news 5
python -m stocks_bot.run_stocks_bot --ci-check
python -m stocks_bot.run_stocks_bot --test-data        # debug snapshot
```

State files default to `crypto_bot/state.json` / `stocks_bot/state.json` locally; on CI they are redirected via the `CI_STATE_FILE` env var to the committed JSON files in the repo root.

---

## Configuration

Key constants live in `config.py` for each bot:

- Crypto: coins (`BTCUSDT`, `ETHUSDT`, `SOLUSDT`), price-alert threshold `ALERT_PRICE_CHANGE_PCT = 5.0`, `OPENROUTER_MODEL = "openrouter/free"`, `SUMMARIZE_NEWS`.
- Stocks: indices + sector list, threshold `3.0`, same OpenRouter model setting.
- Both: `TIMEZONE = "Asia/Kolkata"`, report time (`REPORT_HOUR`/`REPORT_MINUTE`).

All timezone-sensitive code paths use `ist_now()` (from `config.py`) so dates and timestamps in subjects, email bodies, and PDFs are always IST regardless of runner timezone.

---

## Design notes

- **Stateless runners, stateful repo**: nothing persists between GitHub Actions runs, so the JSON state files are the source of truth and are committed back after every mutating job. This is why workflows run on `ubuntu-latest` with the repo freshly checked out.
- **Dedup via committed state**: `sent_news` (last 200 titles) prevents re-alerting the same headline; `articles` (last 500) feeds the digest and weekly PDF.
- **LLM calls are best-effort**: summarization/top-3 failures fall back to the headline; OpenRouter 429 rate limits trigger a single 30s retry.
- **Resilient push**: concurrent workflows can race on the state file; the retry loop (`pull --rebase --autostash` up to 3×) resolves this.
- **Email deliverability**: crypto-subject emails are more prone to Gmail's spam filter; check Spam/Promotions if a digest/report appears missing even when workflows report `email_sent: true`.