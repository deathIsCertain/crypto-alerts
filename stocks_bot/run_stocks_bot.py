import argparse
import json
import os
import time

from stocks_bot.config import BASE_DIR
from stocks_bot.report import check_and_alert_price_moves, load_state, save_state, send_daily_report
from stocks_bot.yahoo_client import YahooClient

STATE_FILE = os.path.join(BASE_DIR, "state.json")
CI_STATE_FILE = os.getenv("CI_STATE_FILE", os.path.join(BASE_DIR, "ci_state.json"))
SYMBOLS = ["^NSEI", "^BSESN", "^CNXIT", "^CNXPHARMA", "^CNXFMCG", "^CNXAUTO", "^CNXMETAL", "^CNXENERGY", "^CNXINFRA", "^CNXREALTY", "^CNXMEDIA", "^CNXPSUBANK", "^CNXFIN"]


def main():
    parser = argparse.ArgumentParser(description="Indian stocks alerts and daily report")
    parser.add_argument("--send-report", action="store_true", help="Send the daily HTML report via Gmail")
    parser.add_argument("--ci-check", action="store_true", help="CI price-move check using committed state file")
    parser.add_argument("--ci-news", type=int, metavar="N", help="CI: send only NEW Indian market news (deduplicated)")
    parser.add_argument("--test-data", action="store_true", help="Print a market snapshot for debugging")
    args = parser.parse_args()

    if args.send_report:
        print(json.dumps(send_daily_report(), indent=2))
        return

    if args.test_data:
        client = YahooClient()
        snap = client.full_snapshot()
        print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "label"} for k, v in snap.items()}, indent=2))
        return

    if args.ci_check:
        client = YahooClient()
        state = load_state(CI_STATE_FILE)
        previous = state.get("last_snapshot")
        snapshot = client.get_market_snapshot(SYMBOLS)
        snapshot = {k: v for k, v in snapshot.items() if v}
        alerts = check_and_alert_price_moves(previous, snapshot)
        if alerts:
            print(f"Alerts triggered: {alerts}")
        state["last_snapshot"] = snapshot
        state["last_checked"] = time.time()
        save_state(CI_STATE_FILE, state)
        return

    if args.ci_news is not None:
        from stocks_bot.news_fetcher import IndiaNewsFetcher
        from stocks_bot.telegram_alert import TelegramAlert

        state = load_state(CI_STATE_FILE)
        sent_titles = set(state.get("sent_news", []))
        news = IndiaNewsFetcher().get_news(limit=args.ci_news)
        bot = TelegramAlert()
        new_sent = []
        for item in news:
            if item["title"] in sent_titles:
                continue
            summary = IndiaNewsFetcher.summarize(item)
            bot.send_message(TelegramAlert.format_news_alert(item, summary))
            new_sent.append(item["title"])
        state["sent_news"] = list(sent_titles | set(new_sent))[-200:]
        save_state(CI_STATE_FILE, state)
        print(f"Sent {len(new_sent)} new news alerts")
        return

    parser.print_help()


if __name__ == "__main__":
    main()