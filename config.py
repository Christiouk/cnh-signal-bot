"""
CNH Signal Bot — Configuration
================================
Watchlist of European ETFs and Indices.
All tickers are Yahoo Finance compatible.
"""

# ─── WATCHLIST ────────────────────────────────────────────────────────────────
# Format: { "ticker": "Human-readable name" }

WATCHLIST = {
    # ── Pan-European Broad Market ETFs ────────────────────────────────────────
    "VWRL.L":   "Vanguard FTSE All-World ETF (LSE)",
    "IWDA.AS":  "iShares Core MSCI World ETF (Euronext Amsterdam)",
    "CSPX.L":   "iShares Core S&P 500 ETF (LSE)",
    "VUSA.L":   "Vanguard S&P 500 ETF (LSE)",
    "EQQQ.L":   "Invesco NASDAQ-100 ETF (LSE)",

    # ── European Equity ETFs ──────────────────────────────────────────────────
    "EXW1.DE":  "iShares Core EURO STOXX 50 ETF (XETRA)",
    "MEUD.PA":  "Lyxor Core MSCI Europe ETF (Euronext Paris)",
    "VEUR.AS":  "Vanguard FTSE Developed Europe ETF (Euronext Amsterdam)",
    "EZU":      "iShares MSCI Eurozone ETF (NYSE)",

    # ── European Indices (for reference / sentiment) ──────────────────────────
    "^STOXX50E": "Euro Stoxx 50 Index",
    "^FTSE":     "FTSE 100 Index (UK)",
    "^GDAXI":    "DAX 40 Index (Germany)",
    "^FCHI":     "CAC 40 Index (France)",
    "^IBEX":     "IBEX 35 Index (Spain)",
    "^PSI20":    "PSI 20 Index (Portugal)",

    # ── Sector ETFs (European focus) ─────────────────────────────────────────
    "IQQH.DE":  "iShares Global Clean Energy ETF (XETRA)",
    "SXLK.SW":  "SPDR MSCI Europe Technology ETF (SIX Swiss)",
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
SCHEDULE = {
    "scan_times": ["09:00", "12:30", "13:30", "18:00", "20:00"],  # UTC — EU open | pre-US open | US open | EU close | pre-US close
    "timezone":   "Europe/London",
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
