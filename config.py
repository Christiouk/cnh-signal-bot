"""
CNH Signal Bot — Configuration
================================
Watchlist of trading assets — indices, ETFs, Oil & Gas, and equities.
All tickers are Yahoo Finance compatible.
"""

# ─── WATCHLIST ────────────────────────────────────────────────────────────────
# Format: { "ticker": "Human-readable name" }

WATCHLIST = {
    # ── Core Indices (Primary Focus) ──────────────────────────────────────────
    "^GDAXI":    "DAX 40 Index (Germany)",
    "^FTSE":     "FTSE 100 Index (UK)",
    "^GSPC":     "S&P 500 Index (US)",
    "^NDX":      "NASDAQ-100 Index (US Tech)",
    "^STOXX50E": "Euro Stoxx 50 Index",
    "^FCHI":     "CAC 40 Index (France)",

    # ── Index ETFs (Tradeable via Trading 212) ────────────────────────────────
    "CSPX.L":   "iShares Core S&P 500 ETF (LSE)",
    "EQQQ.L":   "Invesco NASDAQ-100 ETF (LSE)",
    "EXW1.DE":  "iShares Core EURO STOXX 50 ETF (XETRA)",
    "VWRL.L":   "Vanguard FTSE All-World ETF (LSE)",

    # ── Oil & Gas ─────────────────────────────────────────────────────────────
    "CL=F":     "Crude Oil WTI Futures",
    "BZ=F":     "Brent Crude Oil Futures",
    "BP.L":     "BP plc (LSE)",
    "SHEL.L":   "Shell plc (LSE)",
    "XOM":      "ExxonMobil (NYSE)",

    # ── High-Conviction Equities ──────────────────────────────────────────────
    "MARA":     "Marathon Digital Holdings (NASDAQ)",
    "PONY":     "Pony AI (NASDAQ)",
}

# ─── ANALYSIS PARAMETERS ─────────────────────────────────────────────────────
ANALYSIS = {
    "rsi_period":          14,
    "rsi_oversold":        30,
    "rsi_overbought":      70,
    "macd_fast":           12,
    "macd_slow":           26,
    "macd_signal":         9,
    "bb_period":           20,
    "bb_std":              2,
    "sma_short":           20,
    "sma_long":            50,
    "ema_short":           12,
    "ema_long":            26,
    "atr_period":          14,
    "volume_avg_period":   20,
    "data_period":         "6mo",   # yfinance period for historical data
    "data_interval":       "1d",    # daily candles
}

# ─── SIGNAL THRESHOLDS ───────────────────────────────────────────────────────
SIGNAL = {
    "min_score_to_notify": 3,        # minimum number of bullish/bearish indicators aligned
    "strong_signal_score": 5,        # score to classify as STRONG signal
    "stop_loss_atr_mult":  1.5,      # stop-loss = entry - (ATR * multiplier)
    "take_profit_atr_mult": 2.5,     # take-profit = entry + (ATR * multiplier)
}

# ─── SCHEDULE ────────────────────────────────────────────────────────────────
# All times are LONDON TIME (Europe/London = GMT in winter, BST = GMT+1 in summer).
# The `schedule` library uses local system time, so Railway MUST have TZ=Europe/London set.
#
# Session slots (London time):
#   09:00 — EU market open       (DAX, FTSE, Eurostoxx open)
#   12:00 — Mid-session check    (EU lunch, pre-US positioning)
#   13:30 — US market open       (NYSE/NASDAQ open)
#   14:15 — Post-US-open check   (momentum confirmation)
#   16:30 — EU market close      (DAX, FTSE close)
#   20:00 — US afternoon session (pre-US close positioning)
#   01:00 — Asia session open    (overnight signals)
SCHEDULE = {
    "scan_times": ["09:00", "12:00", "13:30", "14:15", "16:30", "20:00", "01:00"],
    "timezone":   "Europe/London",
    # IMPORTANT: Set TZ=Europe/London in Railway environment variables so the
    # `schedule` library fires at the correct London wall-clock time.
}

# ─── NEWS FEEDS (RSS) ────────────────────────────────────────────────────────
NEWS_FEEDS = [
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=^STOXX50E&region=US&lang=en-US",
    "https://www.ft.com/rss/home/europe",
    "https://feeds.reuters.com/reuters/businessNews",
    "https://www.investing.com/rss/news_301.rss",
]

# ─── LOGGING ─────────────────────────────────────────────────────────────────
LOG_FILE    = "logs/signals.csv"
LOG_COLUMNS = [
    "timestamp", "ticker", "name", "direction", "score",
    "strength", "price", "stop_loss", "take_profit",
    "rsi", "macd_signal", "bb_position", "sma_trend",
    "ai_summary", "executed", "result_pct"
]
