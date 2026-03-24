"""
CNH Signal Bot — Main Orchestrator
=====================================
Coordinates the full pipeline:
1. Scans the watchlist using technical analysis
2. Filters signals above the minimum score threshold
3. Enriches qualifying signals with AI analysis
4. Sends push notifications via Pushover
5. Logs all signals to CSV for performance tracking
6. Runs on a schedule (configurable in config.py)

Usage:
    python3 main.py              # Run once immediately
    python3 main.py --schedule   # Run on schedule (07:30, 12:00, 16:30 UTC)
    python3 main.py --report     # Print performance report and exit
    python3 main.py --test       # Test notifications and connectivity
"""

import os
import sys
import time
import schedule
import argparse
from datetime import datetime
from dotenv import load_dotenv

from config import WATCHLIST, SIGNAL, SCHEDULE
from technical_analysis import analyse_ticker
from ai_agent import build_final_signal
from notifier import send_signal_notification, send_system_alert
from signal_logger import log_signal, print_performance_report
from portal_sender import send_signal_to_portal, test_portal_connection

# Load environment variables from .env file
load_dotenv()

PUSHOVER_TOKEN      = os.getenv("PUSHOVER_TOKEN", "")
PUSHOVER_USER       = os.getenv("PUSHOVER_USER", "")
OPENAI_API_KEY      = os.getenv("OPENAI_API_KEY", "")
SIGNALIX_PORTAL_URL = os.getenv("SIGNALIX_PORTAL_URL", "")
BOT_API_KEY         = os.getenv("BOT_API_KEY", "")


def validate_config():
    """Validate that all required environment variables are set."""
    missing = []
    if not PUSHOVER_TOKEN:
        missing.append("PUSHOVER_TOKEN")
    if not PUSHOVER_USER:
        missing.append("PUSHOVER_USER")
    if not OPENAI_API_KEY:
        missing.append("OPENAI_API_KEY")
    if missing:
        print(f"[ERROR] Missing environment variables: {', '.join(missing)}")
        print("[ERROR] Please configure your .env file. See .env.example for reference.")
        sys.exit(1)


def run_scan():
    """Execute a full market scan across all watchlist assets."""
    print(f"\n{'='*60}")
    print(f"  CNH SIGNAL BOT — Market Scan")
    print(f"  {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*60}")
    print(f"  Scanning {len(WATCHLIST)} assets...\n")

    signals_sent = 0
    min_score    = SIGNAL["min_score_to_notify"]

    for ticker, name in WATCHLIST.items():
        print(f"  [{ticker}] Analysing {name}...")

        # Step 1: Technical Analysis
        tech_result = analyse_ticker(ticker, name)

        if tech_result.error:
            print(f"  [{ticker}] ⚠️  Error: {tech_result.error}")
            continue

        print(f"  [{ticker}] Direction: {tech_result.direction} | Score: {tech_result.score}/7 | RSI: {tech_result.rsi}")

        # Step 2: Filter — only proceed if score meets threshold
        if tech_result.direction == "NEUTRAL" or tech_result.score < min_score:
            print(f"  [{ticker}] ⏭️  Score below threshold ({min_score}). Skipping.\n")
            continue

        # Step 3: AI Enrichment
        print(f"  [{ticker}] 🤖 Running AI analysis...")
        signal = build_final_signal(tech_result)

        # Step 4: Log the signal
        log_signal(signal)

        # Step 5a: Send to SIGNALIX Portal (dashboard + history)
        if SIGNALIX_PORTAL_URL and BOT_API_KEY:
            print(f"  [{ticker}] 🌐 Sending to SIGNALIX portal...")
            send_signal_to_portal(signal, SIGNALIX_PORTAL_URL, BOT_API_KEY)
        else:
            print(f"  [{ticker}] ⚠️  SIGNALIX portal not configured — skipping portal send.")

        # Step 5b: Send Pushover notification (mobile alert)
        print(f"  [{ticker}] 📲 Sending Pushover notification...")
        success = send_signal_notification(signal, PUSHOVER_TOKEN, PUSHOVER_USER)

        if success:
            signals_sent += 1

        print(f"  [{ticker}] ✅ Signal processed: {signal['direction']} | Confidence: {signal['confidence']}\n")

        # Small delay to avoid API rate limits
        time.sleep(2)

    print(f"{'='*60}")
    print(f"  Scan complete. {signals_sent} signal(s) sent.")
    print(f"{'='*60}\n")

    return signals_sent


def run_test():
    """Test connectivity and send a test notification."""
    print("[TEST] Validating configuration...")
    validate_config()

    print("[TEST] Sending test notification via Pushover...")
    success = send_system_alert(
        message=(
            "✅ CNH Signal Bot is online and configured correctly.\n\n"
            "The bot will scan European ETFs and indices at:\n"
            "• 07:30 UTC (before EU market open)\n"
            "• 12:00 UTC (midday)\n"
            "• 16:30 UTC (before EU market close)\n\n"
            "You will receive BUY/SELL signals when the AI detects "
            "strong opportunities in your watchlist."
        ),
        pushover_token=PUSHOVER_TOKEN,
        pushover_user=PUSHOVER_USER,
        title="CNH Signal Bot — System Online ✅"
    )

    if success:
        print("[TEST] ✅ Test notification sent successfully. Check your device.")
    else:
        print("[TEST] ❌ Failed to send test notification. Check your Pushover credentials.")

    # Test portal connection
    if SIGNALIX_PORTAL_URL and BOT_API_KEY:
        print("\n[TEST] Testing SIGNALIX portal connection...")
        test_portal_connection(SIGNALIX_PORTAL_URL, BOT_API_KEY)
    else:
        print("\n[TEST] ⚠️  SIGNALIX_PORTAL_URL or BOT_API_KEY not set — skipping portal test.")

    print("\n[TEST] Running a quick scan on 2 assets to verify the full pipeline...")
    test_watchlist = {
        "^STOXX50E": "Euro Stoxx 50 Index",
        "IWDA.AS":   "iShares Core MSCI World ETF",
    }

    for ticker, name in test_watchlist.items():
        print(f"\n[TEST] Analysing {name} ({ticker})...")
        result = analyse_ticker(ticker, name)
        if result.error:
            print(f"[TEST] ❌ Error: {result.error}")
        else:
            print(f"[TEST] ✅ Price: {result.price} | Direction: {result.direction} | Score: {result.score}/7 | RSI: {result.rsi}")

    print("\n[TEST] Pipeline test complete.")


def setup_schedule():
    """Configure the scheduler based on config.py SCHEDULE settings."""
    scan_times = SCHEDULE.get("scan_times", ["07:30", "12:00", "16:30"])
    for scan_time in scan_times:
        schedule.every().day.at(scan_time).do(run_scan)
        print(f"[SCHEDULER] Scan scheduled at {scan_time} UTC")

    print(f"\n[SCHEDULER] Bot is running. Press Ctrl+C to stop.\n")

    # Send startup notification
    send_system_alert(
        message=f"CNH Signal Bot started. Scans scheduled at: {', '.join(scan_times)} UTC",
        pushover_token=PUSHOVER_TOKEN,
        pushover_user=PUSHOVER_USER,
        title="CNH Signal Bot — Started 🚀"
    )

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CNH Signal Bot")
    parser.add_argument("--schedule", action="store_true", help="Run on schedule")
    parser.add_argument("--report",   action="store_true", help="Print performance report")
    parser.add_argument("--test",     action="store_true", help="Test connectivity")
    args = parser.parse_args()

    if args.report:
        print_performance_report()
        sys.exit(0)

    validate_config()

    if args.test:
        run_test()
    elif args.schedule:
        setup_schedule()
    else:
        # Single immediate scan
        run_scan()
