import argparse
import json
import os
import time

from crypto_bot.config import BASE_DIR
from crypto_bot.report import (
    alert_top_news,
    check_and_alert_price_moves,
    load_state,
    save_state,
    send_daily_report,
)
from crypto_bot.binance_client import BinanceClient

STATE_FILE = os.path.join(BASE_DIR, "state.json")
CI_STATE_FILE = os.getenv("CI_STATE_FILE", os.path.join(BASE_DIR, "ci_state.json"))


def main():
    parser = argparse.ArgumentParser(description="OpenClaw crypto alerts and daily report")
    parser.add_argument("--send-report", action="store_true", help="Send the daily HTML report via Gmail")
    parser.add_argument("--alert-news", type=int, metavar="N", help="Send top N news alerts to Telegram")
    parser.add_argument("--monitor", action="store_true", help="Run price-move monitor loop (sends alerts to Telegram)")
    parser.add_argument("--check-once", action="store_true", help="Run a single price-move check and exit (for scheduled tasks)")
    parser.add_argument("--ci-check", action="store_true", help="CI price-move check using committed state file (for GitHub Actions)")
    parser.add_argument("--ci-news", type=int, metavar="N", help="CI: send only NEW news headlines (deduplicated via committed state)")
    parser.add_argument("--scheduler", action="store_true", help="Run the blocking scheduler (daily report)")
    args = parser.parse_args()

    if args.send_report:
        result = send_daily_report()
        print(json.dumps(result, indent=2))
        return

    if args.alert_news is not None:
        alert_top_news(args.alert_news)
        return

    if args.ci_news is not None:
        from crypto_bot.news_fetcher import NewsFetcher
        from crypto_bot.summarizer import summarize_article
        from crypto_bot.telegram_alert import TelegramAlert

        state = load_state(CI_STATE_FILE)
        sent_titles = set(state.get("sent_news", []))
        news = NewsFetcher().get_news(limit=args.ci_news)
        bot = TelegramAlert()
        new_sent = []
        for item in news:
            if item["title"] in sent_titles:
                continue
            summary = summarize_article(item)
            bot.send_message(TelegramAlert.format_news_alert(item, summary))
            new_sent.append(item["title"])
        state["sent_news"] = list(sent_titles | set(new_sent))[-200:]
        save_state(CI_STATE_FILE, state)
        print(f"Sent {len(new_sent)} new news alerts")
        return

    if args.scheduler:
        from crypto_bot.scheduler import start_scheduler

        start_scheduler()
        return

    if args.ci_check:
        client = BinanceClient()
        state = load_state(CI_STATE_FILE)
        previous = state.get("last_snapshot")
        snapshot = client.get_market_snapshot()
        alerts = check_and_alert_price_moves(previous, snapshot)
        if alerts:
            print(f"Alerts triggered: {alerts}")
        save_state(CI_STATE_FILE, {"last_snapshot": snapshot, "last_checked": time.time()})
        return

    if args.check_once:
        client = BinanceClient()
        state = load_state(STATE_FILE)
        previous = state.get("last_snapshot")
        snapshot = client.get_market_snapshot()
        alerts = check_and_alert_price_moves(previous, snapshot)
        if alerts:
            print(f"Alerts triggered: {alerts}")
        save_state(STATE_FILE, {"last_snapshot": snapshot})
        return

    if args.monitor:
        client = BinanceClient()
        state = load_state(STATE_FILE)
        previous = state.get("last_snapshot")
        print("Monitoring price moves... (Ctrl+C to stop)")
        try:
            while True:
                snapshot = client.get_market_snapshot()
                alerts = check_and_alert_price_moves(previous, snapshot)
                if alerts:
                    print(f"Alerts triggered: {alerts}")
                previous = snapshot
                save_state(STATE_FILE, {"last_snapshot": previous})
                time.sleep(600)
        except KeyboardInterrupt:
            print("\nMonitor stopped.")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
