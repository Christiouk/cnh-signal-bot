"""
CNH Signal Bot — Pushover Notifier
=====================================
Sends rich push notifications to iOS/Android/Desktop via Pushover API.
Supports priority levels and supplementary URLs.
"""

import os
import requests
from typing import Optional

PUSHOVER_API_URL = "https://api.pushover.net/1/messages.json"

# Direction emoji mapping
DIRECTION_ICON = {
    "BUY":     "📈",
    "SELL":    "📉",
    "NEUTRAL": "➡️",
    "ERROR":   "⚠️",
}

STRENGTH_PRIORITY = {
    "STRONG":   1,   # High priority — bypasses quiet hours
    "MODERATE": 0,   # Normal priority
    "WEAK":    -1,   # Low priority — no sound
}

CONFIDENCE_LABEL = {
    "HIGH":   "🟢 HIGH",
    "MEDIUM": "🟡 MEDIUM",
    "LOW":    "🔴 LOW",
}


def send_signal_notification(
    signal: dict,
    pushover_token: str,
    pushover_user: str,
) -> bool:
    """
    Send a trading signal push notification via Pushover.
    Returns True if successful, False otherwise.
    """
    direction   = signal.get("direction", "NEUTRAL")
    strength    = signal.get("strength", "WEAK")
    confidence  = signal.get("confidence", "LOW")
    ticker      = signal.get("ticker", "")
    name        = signal.get("name", "")
    price       = signal.get("price", 0)
    stop_loss   = signal.get("stop_loss", 0)
    take_profit = signal.get("take_profit", 0)
    rsi         = signal.get("rsi", 0)
    macd        = signal.get("macd", "")
    bb          = signal.get("bb", "")
    sentiment   = signal.get("sentiment", "NEUTRAL")
    ai_summary  = signal.get("ai_summary", "")
    ai_risks    = signal.get("ai_risks", "")
    timestamp   = signal.get("timestamp", "")
    score       = signal.get("score", 0)
    volume_surge = signal.get("volume_surge", False)

    icon = DIRECTION_ICON.get(direction, "➡️")
    priority = STRENGTH_PRIORITY.get(strength, 0)
    conf_label = CONFIDENCE_LABEL.get(confidence, "🔴 LOW")

    # ── Title ─────────────────────────────────────────────────────────────────
    title = f"{icon} {direction} Signal — {ticker}"
    if strength == "STRONG":
        title = f"🔥 STRONG {direction} — {ticker}"

    # ── Message Body ──────────────────────────────────────────────────────────
    volume_line = "⚡ Volume Surge Detected\n" if volume_surge else ""

    message = (
        f"<b>{name}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💰 <b>Price:</b> {price}\n"
        f"🛑 <b>Stop-Loss:</b> {stop_loss}\n"
        f"🎯 <b>Take-Profit:</b> {take_profit}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📊 <b>Score:</b> {score}/7 indicators\n"
        f"📉 <b>RSI:</b> {rsi}\n"
        f"📈 <b>MACD:</b> {macd}\n"
        f"🎯 <b>Bollinger:</b> {bb} Band\n"
        f"🌍 <b>Sentiment:</b> {sentiment}\n"
        f"🤖 <b>AI Confidence:</b> {conf_label}\n"
        f"{volume_line}"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<b>Analysis:</b>\n{ai_summary}\n\n"
        f"<b>Risk:</b> {ai_risks}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<i>{timestamp}</i>"
    )

    # ── Pushover Request ──────────────────────────────────────────────────────
    payload = {
        "token":    pushover_token,
        "user":     pushover_user,
        "title":    title,
        "message":  message,
        "html":     1,
        "priority": priority,
        "sound":    "cashregister" if direction == "BUY" else ("falling" if direction == "SELL" else "none"),
    }

    # Emergency priority requires retry + expire
    if priority == 2:
        payload["retry"]  = 60
        payload["expire"] = 3600

    try:
        response = requests.post(PUSHOVER_API_URL, data=payload, timeout=10)
        result = response.json()
        if result.get("status") == 1:
            print(f"[NOTIFIER] ✅ Notification sent for {ticker}")
            return True
        else:
            print(f"[NOTIFIER] ❌ Pushover error: {result.get('errors', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"[NOTIFIER] ❌ Exception sending notification: {e}")
        return False


def send_system_alert(
    message: str,
    pushover_token: str,
    pushover_user: str,
    title: str = "CNH Signal Bot — System Alert"
) -> bool:
    """Send a system-level alert (errors, startup, shutdown)."""
    payload = {
        "token":    pushover_token,
        "user":     pushover_user,
        "title":    title,
        "message":  message,
        "priority": -1,
        "sound":    "none",
    }
    try:
        response = requests.post(PUSHOVER_API_URL, data=payload, timeout=10)
        return response.json().get("status") == 1
    except Exception:
        return False
