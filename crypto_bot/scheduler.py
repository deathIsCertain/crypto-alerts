from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from .config import REPORT_HOUR, REPORT_MINUTE, TIMEZONE
from .report import send_daily_report


def start_scheduler():
    scheduler = BlockingScheduler(timezone=TIMEZONE)
    scheduler.add_job(
        send_daily_report,
        trigger=CronTrigger(hour=REPORT_HOUR, minute=REPORT_MINUTE, timezone=TIMEZONE),
        id="daily_crypto_report",
        name="Daily crypto report to Gmail",
        misfire_grace_time=3600,
    )
    print(f"Scheduler started. Daily report scheduled at {REPORT_HOUR:02d}:{REPORT_MINUTE:02d} {TIMEZONE}")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("Scheduler stopped.")
