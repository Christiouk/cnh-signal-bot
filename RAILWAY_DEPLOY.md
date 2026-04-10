# SIGNALIX Bot — Railway Deployment Guide

## Overview

This guide deploys the SIGNALIX Signal Bot to Railway.app for 24/7 automated operation.
The bot scans European ETFs and indices at 07:30, 12:00, and 16:30 UTC daily, sends signals
to the SIGNALIX portal dashboard, and pushes notifications to your Pushover app.

---

## Prerequisites

- Railway account at [railway.app](https://railway.app) (free tier is sufficient)
- GitHub account (the bot code must be in a private GitHub repository)
- Your credentials ready (see Environment Variables below)

---

## Step 1 — Push the Bot Code to GitHub

The bot code is already in a private GitHub repository: `cnh-signal-bot`

If you need to update it after changes:

```bash
cd /path/to/cnh_signal_bot
git add .
git commit -m "Update bot"
git push origin main
```

---

## Step 2 — Create a New Railway Project

1. Go to [railway.app](https://railway.app) and sign in.
2. Click **New Project** → **Deploy from GitHub repo**.
3. Select the `cnh-signal-bot` repository.
4. Railway will detect the `Dockerfile` automatically and begin the build.

---

## Step 3 — Configure Environment Variables

In your Railway project, go to **Variables** and add the following:

| Variable | Value | Description |
| :--- | :--- | :--- |
| `OPENAI_API_KEY` | `sk-proj-...` | Your OpenAI API key |
| `PUSHOVER_APP_TOKEN` | `...` | Your Pushover App Token (from pushover.net/apps) |
| `PUSHOVER_USER_KEY` | `u8akv2e1hzbqcxpm9hchpsurs7j6kk` | Your Pushover User Key |
| `SIGNALIX_PORTAL_URL` | `https://signalportal-ypjt69nw.manus.space` | Your SIGNALIX portal URL |
| `BOT_API_KEY` | `...` | The BOT_API_KEY from your SIGNALIX portal secrets |
| `TZ` | `Europe/London` | **Required** — sets the system timezone so the `schedule` library fires at London wall-clock time (BST in summer, GMT in winter) |

> **Important:** Never commit these values to GitHub. Railway's Variables panel is the secure place for secrets.

---

## Step 4 — Verify the Start Command

Railway reads `railway.toml` which already contains:

```toml
[build]
builder = "dockerfile"

[deploy]
startCommand = "python main.py --schedule"
restartPolicyType = "always"
```

This means the bot will:
- Start automatically when deployed
- Run scans at 09:00, 12:00, 13:30, 14:15, 16:30, 20:00, and 01:00 **London time** every day
- Restart automatically if it crashes

> **Timezone note:** The `TZ=Europe/London` variable ensures the bot fires at London wall-clock time. During BST (last Sunday March → last Sunday October) this is UTC+1; during GMT (winter) it is UTC+0. Railway does not set a timezone by default, so this variable is mandatory.

---

## Step 5 — Deploy and Monitor

1. After setting variables, click **Deploy** (or it may deploy automatically).
2. Watch the **Logs** tab — you should see:
   ```
   [SIGNALIX] Bot starting in SCHEDULE mode...
   [SIGNALIX] Scans scheduled at: 09:00, 12:00, 13:30, 14:15, 16:30, 20:00, 01:00 London time
   ```
3. The first scan will run at the next scheduled time.

---

## Monitoring

- **Railway Logs:** Real-time logs in the Railway dashboard.
- **Pushover:** You receive a notification when the bot starts and for every signal.
- **SIGNALIX Portal:** All signals appear in your dashboard at your portal URL.

---

## Costs

| Service | Cost |
| :--- | :--- |
| Railway Hobby Plan | $5/month (includes 500 hours — sufficient for always-on) |
| OpenAI API (GPT-4o-mini) | ~$10-15/month depending on usage |
| Pushover | $4.99 one-time (already paid) |
| **Total** | **~$15-20/month** |

---

## Troubleshooting

**Bot not sending signals:**
- Check Railway logs for errors
- Verify all environment variables are set correctly
- Test the portal connection: the bot logs `[PORTAL] ✅` or `[PORTAL] ❌`

**No Pushover notifications:**
- Ensure the Pushover app is installed and logged in on your device
- Verify `PUSHOVER_APP_TOKEN` and `PUSHOVER_USER_KEY` are correct

**Yahoo Finance errors:**
- Temporary — Yahoo Finance occasionally blocks requests
- The bot will retry on the next scheduled scan
