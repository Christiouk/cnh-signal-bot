"""
CNH Signal Bot — Dynamic Watchlist Fetcher
==========================================
Fetches the enabled watchlist from the SIGNALIX portal at scan time.
Falls back to the static WATCHLIST in config.py if the portal is unreachable.

The portal exposes a tRPC query:
  GET /api/trpc/watchlist.listEnabled?input={"json":{"apiKey":"<BOT_API_KEY>"}}

Returns a list of { ticker, name, category, enabled } objects.
"""

import os
import json
import requests
from typing import Optional
from config import WATCHLIST  # static fallback


def fetch_watchlist_from_portal(
    portal_url: str,
    bot_api_key: str,
    timeout: int = 10,
) -> Optional[dict[str, str]]:
    """
    Fetch the enabled watchlist from the SIGNALIX portal.

    Returns:
        dict mapping ticker → name for all enabled items, or None on failure.
    """
    if not portal_url or not bot_api_key:
        return None

    # tRPC GET query — input must be URL-encoded JSON
    input_param = json.dumps({"json": {"apiKey": bot_api_key}})
    endpoint = f"{portal_url.rstrip('/')}/api/trpc/watchlist.listEnabled"

    try:
        response = requests.get(
            endpoint,
            params={"input": input_param},
            headers={"Accept": "application/json"},
            timeout=timeout,
        )

        if response.status_code != 200:
            print(f"[WATCHLIST] ⚠️  Portal returned HTTP {response.status_code} — using static fallback.")
            return None

        data = response.json()
        # tRPC wraps: {"result": {"data": {"json": [...]}}}
        items = data.get("result", {}).get("data", {}).get("json", [])

        if not isinstance(items, list) or len(items) == 0:
            print("[WATCHLIST] ⚠️  Portal returned empty watchlist — using static fallback.")
            return None

        watchlist = {item["ticker"]: item["name"] for item in items if item.get("enabled", True)}
        print(f"[WATCHLIST] ✅ Loaded {len(watchlist)} assets from portal.")
        return watchlist

    except requests.exceptions.ConnectionError:
        print(f"[WATCHLIST] ⚠️  Could not connect to portal — using static fallback.")
        return None
    except requests.exceptions.Timeout:
        print(f"[WATCHLIST] ⚠️  Portal request timed out — using static fallback.")
        return None
    except Exception as e:
        print(f"[WATCHLIST] ⚠️  Unexpected error fetching watchlist: {e} — using static fallback.")
        return None


def get_watchlist(portal_url: str = "", bot_api_key: str = "") -> dict[str, str]:
    """
    Primary entry point. Tries the portal first, falls back to config.py.

    Args:
        portal_url:  SIGNALIX_PORTAL_URL env var value
        bot_api_key: BOT_API_KEY env var value

    Returns:
        dict mapping ticker → name (always non-empty)
    """
    if portal_url and bot_api_key:
        dynamic = fetch_watchlist_from_portal(portal_url, bot_api_key)
        if dynamic:
            return dynamic

    print(f"[WATCHLIST] 📋 Using static watchlist from config.py ({len(WATCHLIST)} assets).")
    return WATCHLIST
