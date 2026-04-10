"""
CNH Signal Bot — SIGNALIX Portal Sender
=========================================
Sends trading signals directly to the SIGNALIX portal via its tRPC API.
The portal stores the signal in the database and displays it on the dashboard.

The tRPC endpoint accepts a JSON POST to:
  POST /api/trpc/bot.ingestSignal

Authentication: API key passed in the request body as `apiKey`.

v4.0 fields added:
  scoreMax, assetCategory, riskNote, hedgeSuggestion,
  entryLow, entryHigh, moderateEntryLow, moderateEntryHigh,
  riskyEntryLow, riskyEntryHigh, closeLow, closeHigh
"""

import os
import json
import requests
from typing import Optional


def send_signal_to_portal(signal: dict, portal_url: str, bot_api_key: str, scan_id: str = None) -> bool:
    """
    Send a trading signal to the SIGNALIX portal via tRPC.

    Args:
        signal:      The enriched signal dict from build_final_signal()
        portal_url:  Base URL of the SIGNALIX portal (e.g. https://signalix.cloud)
        bot_api_key: The BOT_API_KEY secret configured in the portal
        scan_id:     Optional UUID grouping signals from the same scan batch

    Returns:
        True if the signal was accepted, False otherwise.
    """
    endpoint = f"{portal_url.rstrip('/')}/api/trpc/bot.ingestSignal"

    # ─── Map bot signal fields to portal schema (v4.0) ───────────────────────
    payload = {
        "json": {
            # ── Auth ──────────────────────────────────────────────────────────
            "apiKey":      bot_api_key,

            # ── Core identity ─────────────────────────────────────────────────
            "ticker":      signal.get("ticker", ""),
            "assetName":   signal.get("name", signal.get("ticker", "")),
            "direction":   signal.get("direction", "BUY"),

            # ── Scoring ───────────────────────────────────────────────────────
            "score":       int(signal.get("score", 0)),
            "scoreMax":    int(signal.get("score_max", 8)),

            # ── Classification ────────────────────────────────────────────────
            "confidence":     signal.get("confidence", "LOW"),
            "sentiment":      signal.get("sentiment", "NEUTRAL"),
            "assetCategory":  signal.get("asset_category", ""),

            # ── Price levels ──────────────────────────────────────────────────
            "currentPrice": float(signal["price"])      if signal.get("price")       else None,
            "stopLoss":     float(signal["stop_loss"])  if signal.get("stop_loss")   else None,
            "targetPrice":  float(signal["take_profit"]) if signal.get("take_profit") else None,

            # ── Entry ranges (v4.0) ───────────────────────────────────────────
            "entryLow":          float(signal["entry_low"])          if signal.get("entry_low")          else None,
            "entryHigh":         float(signal["entry_high"])         if signal.get("entry_high")         else None,
            "moderateEntryLow":  float(signal["moderate_entry_low"]) if signal.get("moderate_entry_low") else None,
            "moderateEntryHigh": float(signal["moderate_entry_high"]) if signal.get("moderate_entry_high") else None,
            "riskyEntryLow":     float(signal["risky_entry_low"])    if signal.get("risky_entry_low")    else None,
            "riskyEntryHigh":    float(signal["risky_entry_high"])   if signal.get("risky_entry_high")   else None,
            "closeLow":          float(signal["close_low"])          if signal.get("close_low")          else None,
            "closeHigh":         float(signal["close_high"])         if signal.get("close_high")         else None,

            # ── AI analysis ───────────────────────────────────────────────────
            "aiSummary":       signal.get("ai_summary", ""),
            "riskNote":        signal.get("risk_note", ""),
            "hedgeSuggestion": signal.get("hedge_suggestion", ""),

            # ── Scan grouping ─────────────────────────────────────────────────
            "scanId": scan_id,

            # ── Technical indicators (JSON blob) ──────────────────────────────
            "indicators": {
                "rsi":             signal.get("rsi"),
                "macd":            signal.get("macd"),
                "bollinger":       signal.get("bb"),
                "volume_surge":    signal.get("volume_surge", False),
                "strength":        signal.get("strength", "WEAK"),
                "ai_risks":        signal.get("ai_risks", ""),
                "tf_4h_direction": signal.get("tf_4h_direction", "NEUTRAL"),
                "tf_4h_rsi":       signal.get("tf_4h_rsi"),
                "tf_confluence":   signal.get("tf_confluence", "NONE"),
            },
        }
    }

    # Remove None values from the top-level json object (optional fields)
    payload["json"] = {k: v for k, v in payload["json"].items() if v is not None}

    headers = {
        "Content-Type": "application/json",
        "Accept":       "application/json",
    }

    try:
        response = requests.post(
            endpoint,
            json=payload,
            headers=headers,
            timeout=15,
        )

        if response.status_code == 200:
            result = response.json()
            # tRPC wraps the result in {"result": {"data": {"json": ...}}}
            data = result.get("result", {}).get("data", {}).get("json", {})
            signal_id = data.get("id") or data.get("signalId")
            print(f"[PORTAL] ✅ Signal sent to SIGNALIX portal (ID: {signal_id})")
            return True
        else:
            print(f"[PORTAL] ❌ Portal returned HTTP {response.status_code}: {response.text[:300]}")
            return False

    except requests.exceptions.ConnectionError:
        print(f"[PORTAL] ❌ Could not connect to portal at {portal_url}")
        return False
    except requests.exceptions.Timeout:
        print(f"[PORTAL] ❌ Portal request timed out after 15s")
        return False
    except Exception as e:
        print(f"[PORTAL] ❌ Unexpected error sending to portal: {e}")
        return False


def test_portal_connection(portal_url: str, bot_api_key: str) -> bool:
    """
    Test the connection to the SIGNALIX portal by sending a minimal test signal.
    Returns True if the portal is reachable and the API key is valid.
    """
    print(f"[PORTAL] Testing connection to {portal_url}...")

    test_signal = {
        "ticker":      "TEST",
        "name":        "Connection Test",
        "direction":   "BUY",
        "score":       1,
        "score_max":   8,
        "confidence":  "LOW",
        "sentiment":   "NEUTRAL",
        "asset_category": "Equity",
        "price":       100.0,
        "ai_summary":  "This is an automated connection test from the CNH Signal Bot.",
        "risk_note":   "Test signal — no real risk assessment.",
        "hedge_suggestion": "N/A — test signal.",
    }

    result = send_signal_to_portal(test_signal, portal_url, bot_api_key)

    if result:
        print("[PORTAL] ✅ Portal connection successful — SIGNALIX is receiving signals.")
    else:
        print("[PORTAL] ❌ Portal connection failed. Check SIGNALIX_PORTAL_URL and BOT_API_KEY in .env")

    return result
