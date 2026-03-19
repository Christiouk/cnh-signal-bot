"""
CNH Signal Bot — Signal Logger
================================
Records all generated signals to a CSV file for performance tracking.
Allows the user to later mark signals as executed and record the result.
"""

import os
import csv
import json
from datetime import datetime
from config import LOG_FILE, LOG_COLUMNS


def ensure_log_file():
    """Create the log file with headers if it doesn't exist."""
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=LOG_COLUMNS)
            writer.writeheader()
        print(f"[LOGGER] Log file created: {LOG_FILE}")


def log_signal(signal: dict):
    """Append a signal to the CSV log."""
    ensure_log_file()
    row = {col: signal.get(col, "") for col in LOG_COLUMNS}
    # Flatten ai_summary into the log
    row["ai_summary"] = signal.get("ai_summary", "")
    with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=LOG_COLUMNS)
        writer.writerow(row)
    print(f"[LOGGER] ✅ Signal logged: {signal.get('ticker')} {signal.get('direction')} @ {signal.get('price')}")


def get_performance_summary() -> dict:
    """
    Read the log file and compute performance statistics.
    Returns a summary dict with win rate, avg return, etc.
    """
    ensure_log_file()
    signals = []
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            signals.append(row)

    if not signals:
        return {"total": 0, "executed": 0, "win_rate": 0, "avg_return": 0}

    executed = [s for s in signals if s.get("executed", "").upper() == "YES"]
    results  = []
    for s in executed:
        try:
            pct = float(s.get("result_pct", "0").replace("%", ""))
            results.append(pct)
        except (ValueError, AttributeError):
            pass

    wins     = [r for r in results if r > 0]
    win_rate = (len(wins) / len(results) * 100) if results else 0
    avg_ret  = (sum(results) / len(results)) if results else 0

    return {
        "total":     len(signals),
        "executed":  len(executed),
        "with_result": len(results),
        "wins":      len(wins),
        "losses":    len(results) - len(wins),
        "win_rate":  round(win_rate, 1),
        "avg_return": round(avg_ret, 2),
    }


def print_performance_report():
    """Print a formatted performance report to the console."""
    stats = get_performance_summary()
    print("\n" + "="*50)
    print("  CNH SIGNAL BOT — PERFORMANCE REPORT")
    print("="*50)
    print(f"  Total Signals Generated : {stats['total']}")
    print(f"  Signals Executed        : {stats['executed']}")
    print(f"  Signals with Result     : {stats['with_result']}")
    print(f"  Wins                    : {stats['wins']}")
    print(f"  Losses                  : {stats['losses']}")
    print(f"  Win Rate                : {stats['win_rate']}%")
    print(f"  Avg Return per Trade    : {stats['avg_return']}%")
    print("="*50 + "\n")
