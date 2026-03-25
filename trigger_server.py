"""
CNH Signal Bot — HTTP Trigger Server
======================================
A minimal Flask server that runs alongside the scheduler.
Exposes a single endpoint:

  POST /trigger
  Authorization: Bearer <TRIGGER_TOKEN>

When called, it fires run_scan() immediately in a background thread.
This is what RAILWAY_TRIGGER_URL points to.

Usage (started automatically by main.py --schedule):
  The server binds to PORT (default 8080) so Railway can route HTTP traffic to it.
  Set TRIGGER_TOKEN in Railway env vars for security.
"""

import os
import threading
from flask import Flask, request, jsonify

trigger_app = Flask(__name__)

# The shared scan function — injected by main.py at startup
_scan_fn = None
_portal_url = ""
_bot_api_key = ""
_scan_lock = threading.Lock()
_is_scanning = False

TRIGGER_TOKEN = os.getenv("TRIGGER_TOKEN", "")


def init_trigger_server(scan_fn, portal_url: str = "", bot_api_key: str = ""):
    """Inject the scan function so the HTTP handler can call it."""
    global _scan_fn, _portal_url, _bot_api_key
    _scan_fn = scan_fn
    _portal_url = portal_url
    _bot_api_key = bot_api_key


@trigger_app.route("/trigger", methods=["POST"])
def trigger_scan():
    global _is_scanning

    # ── Auth check ──────────────────────────────────────────────────────────────
    if TRIGGER_TOKEN:
        auth_header = request.headers.get("Authorization", "")
        token = auth_header.replace("Bearer ", "").strip()
        if token != TRIGGER_TOKEN:
            return jsonify({"success": False, "error": "Unauthorized"}), 401

    if _scan_fn is None:
        return jsonify({"success": False, "error": "Scan function not initialised"}), 500

    # ── Prevent concurrent scans ────────────────────────────────────────────────
    if _is_scanning:
        return jsonify({"success": False, "error": "Scan already in progress"}), 409

    trigger_id = request.json.get("triggerId") if request.is_json else None

    def _run():
        global _is_scanning
        _is_scanning = True
        try:
            print(f"[TRIGGER] 🚀 Manual scan triggered via HTTP (trigger_id={trigger_id})")
            signals_found = _scan_fn()

            # Report completion back to the portal
            if _portal_url and _bot_api_key and trigger_id:
                try:
                    import requests as req
                    import json
                    payload = {"json": {"apiKey": _bot_api_key, "triggerId": trigger_id, "signalsFound": signals_found or 0}}
                    req.post(
                        f"{_portal_url.rstrip('/')}/api/trpc/scan.completeTrigger",
                        json=payload,
                        timeout=10,
                    )
                    print(f"[TRIGGER] ✅ Reported {signals_found} signal(s) to portal (trigger_id={trigger_id})")
                except Exception as e:
                    print(f"[TRIGGER] ⚠️  Could not report completion to portal: {e}")
        finally:
            _is_scanning = False

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    return jsonify({"success": True, "message": "Scan started", "triggerId": trigger_id}), 202


@trigger_app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "scanning": _is_scanning}), 200


def start_trigger_server(port: int = 8080):
    """Start the Flask trigger server in a background daemon thread."""
    def _serve():
        trigger_app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

    thread = threading.Thread(target=_serve, daemon=True)
    thread.start()
    print(f"[TRIGGER] HTTP trigger server listening on port {port}")
    print(f"[TRIGGER] Endpoint: POST /trigger  (set RAILWAY_TRIGGER_URL to https://<your-railway-domain>/trigger)")
    if not TRIGGER_TOKEN:
        print(f"[TRIGGER] ⚠️  TRIGGER_TOKEN not set — endpoint is unprotected. Add it to Railway env vars.")
