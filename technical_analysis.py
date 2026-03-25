"""
CNH Signal Bot — Technical Analysis Engine
============================================
Computes RSI, MACD, Bollinger Bands, SMA/EMA, ATR, and Volume
for a given ticker using yfinance + ta library.

Dual-timeframe analysis:
  - Primary: daily candles (1d) — trend direction and score
  - Secondary: 4-hour candles (4h) — intraday confluence check
  - Confluence bonus: +1 if both timeframes agree on direction
  - Divergence penalty: -1 if timeframes disagree
Returns a structured TechnicalResult with score and metadata.
"""

import yfinance as yf
import pandas as pd
import ta
from dataclasses import dataclass, field
from typing import Optional
from config import ANALYSIS, SIGNAL


@dataclass
class TechnicalResult:
    ticker:        str
    name:          str
    price:         float
    direction:     str          # "BUY", "SELL", "NEUTRAL"
    score:         int          # number of aligned indicators (0–8 with confluence bonus)
    strength:      str          # "WEAK", "MODERATE", "STRONG"
    rsi:           float        = 0.0
    macd_cross:    str          = "NEUTRAL"   # "BULLISH", "BEARISH", "NEUTRAL"
    bb_position:   str          = "MIDDLE"    # "LOWER", "MIDDLE", "UPPER"
    sma_trend:     str          = "NEUTRAL"   # "BULLISH", "BEARISH", "NEUTRAL"
    ema_trend:     str          = "NEUTRAL"
    volume_surge:  bool         = False
    atr:           float        = 0.0
    stop_loss:     float        = 0.0
    take_profit:   float        = 0.0
    indicators:    dict         = field(default_factory=dict)
    # Dual-timeframe fields
    tf_4h_direction: str        = "NEUTRAL"   # direction from 4h candles
    tf_4h_rsi:       float      = 0.0
    tf_confluence:   str        = "NONE"      # "AGREE", "DISAGREE", "NONE"
    error:         Optional[str] = None


def fetch_data(ticker: str, period: str, interval: str) -> Optional[pd.DataFrame]:
    """Download OHLCV data from Yahoo Finance."""
    try:
        df = yf.download(ticker, period=period, interval=interval,
                         auto_adjust=True, progress=False)
        if df.empty or len(df) < 30:
            return None
        # Flatten MultiIndex columns if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.dropna(inplace=True)
        return df
    except Exception:
        return None


def compute_indicators(df: pd.DataFrame) -> dict:
    """Compute all technical indicators and return as dict."""
    cfg = ANALYSIS
    ind = {}

    close  = df["Close"]
    high   = df["High"]
    low    = df["Low"]
    volume = df["Volume"]

    # ── RSI ──────────────────────────────────────────────────────────────────
    rsi_ind = ta.momentum.RSIIndicator(close=close, window=cfg["rsi_period"])
    ind["rsi"] = float(rsi_ind.rsi().iloc[-1])

    # ── MACD ─────────────────────────────────────────────────────────────────
    macd_ind = ta.trend.MACD(
        close=close,
        window_fast=cfg["macd_fast"],
        window_slow=cfg["macd_slow"],
        window_sign=cfg["macd_signal"]
    )
    ind["macd"]           = float(macd_ind.macd().iloc[-1])
    ind["macd_signal"]    = float(macd_ind.macd_signal().iloc[-1])
    ind["macd_hist"]      = float(macd_ind.macd_diff().iloc[-1])
    ind["macd_hist_prev"] = float(macd_ind.macd_diff().iloc[-2])

    # ── Bollinger Bands ───────────────────────────────────────────────────────
    bb_ind = ta.volatility.BollingerBands(
        close=close,
        window=cfg["bb_period"],
        window_dev=cfg["bb_std"]
    )
    ind["bb_upper"] = float(bb_ind.bollinger_hband().iloc[-1])
    ind["bb_lower"] = float(bb_ind.bollinger_lband().iloc[-1])
    ind["bb_mid"]   = float(bb_ind.bollinger_mavg().iloc[-1])
    ind["bb_pct"]   = float(bb_ind.bollinger_pband().iloc[-1])  # 0=lower, 1=upper

    # ── Simple Moving Averages ────────────────────────────────────────────────
    ind["sma_short"] = float(ta.trend.SMAIndicator(close=close, window=cfg["sma_short"]).sma_indicator().iloc[-1])
    ind["sma_long"]  = float(ta.trend.SMAIndicator(close=close, window=cfg["sma_long"]).sma_indicator().iloc[-1])

    # ── Exponential Moving Averages ───────────────────────────────────────────
    ind["ema_short"] = float(ta.trend.EMAIndicator(close=close, window=cfg["ema_short"]).ema_indicator().iloc[-1])
    ind["ema_long"]  = float(ta.trend.EMAIndicator(close=close, window=cfg["ema_long"]).ema_indicator().iloc[-1])

    # ── ATR (Average True Range) ──────────────────────────────────────────────
    atr_ind = ta.volatility.AverageTrueRange(high=high, low=low, close=close, window=cfg["atr_period"])
    ind["atr"] = float(atr_ind.average_true_range().iloc[-1])

    # ── Volume ────────────────────────────────────────────────────────────────
    ind["volume"]       = float(volume.iloc[-1])
    ind["volume_avg"]   = float(volume.rolling(window=cfg["volume_avg_period"]).mean().iloc[-1])
    ind["volume_ratio"] = ind["volume"] / ind["volume_avg"] if ind["volume_avg"] > 0 else 1.0

    # ── Current Price ─────────────────────────────────────────────────────────
    ind["price"] = float(close.iloc[-1])

    return ind


def score_signal(ind: dict) -> tuple:
    """
    Score the signal based on aligned indicators.
    Returns (direction, score, signal_details).
    """
    cfg_a = ANALYSIS
    bullish_count = 0
    bearish_count = 0
    details = {}

    # ── RSI ───────────────────────────────────────────────────────────────────
    if ind["rsi"] < cfg_a["rsi_oversold"]:
        bullish_count += 1
        details["rsi"] = f"OVERSOLD ({ind['rsi']:.1f})"
    elif ind["rsi"] > cfg_a["rsi_overbought"]:
        bearish_count += 1
        details["rsi"] = f"OVERBOUGHT ({ind['rsi']:.1f})"
    else:
        details["rsi"] = f"NEUTRAL ({ind['rsi']:.1f})"

    # ── MACD ──────────────────────────────────────────────────────────────────
    if ind["macd"] > ind["macd_signal"] and ind["macd_hist"] > ind["macd_hist_prev"]:
        bullish_count += 1
        details["macd"] = "BULLISH CROSSOVER"
    elif ind["macd"] < ind["macd_signal"] and ind["macd_hist"] < ind["macd_hist_prev"]:
        bearish_count += 1
        details["macd"] = "BEARISH CROSSOVER"
    else:
        details["macd"] = "MACD BELOW SIGNAL"

    # ── Bollinger Bands ───────────────────────────────────────────────────────
    if ind["bb_pct"] < 0.1:
        bullish_count += 1
        details["bb"] = f"NEAR LOWER BAND ({ind['bb_pct']:.2f})"
    elif ind["bb_pct"] > 0.9:
        bearish_count += 1
        details["bb"] = f"NEAR UPPER BAND ({ind['bb_pct']:.2f})"
    else:
        details["bb"] = f"MID BAND ({ind['bb_pct']:.2f})"

    # ── SMA Trend ─────────────────────────────────────────────────────────────
    if ind["sma_short"] > ind["sma_long"]:
        bullish_count += 1
        details["sma"] = f"BULLISH (SMA{cfg_a['sma_short']} > SMA{cfg_a['sma_long']})"
    else:
        bearish_count += 1
        details["sma"] = f"BEARISH (SMA{cfg_a['sma_short']} < SMA{cfg_a['sma_long']})"

    # ── EMA Trend ─────────────────────────────────────────────────────────────
    if ind["ema_short"] > ind["ema_long"]:
        bullish_count += 1
        details["ema"] = f"BULLISH (EMA{cfg_a['ema_short']} > EMA{cfg_a['ema_long']})"
    else:
        bearish_count += 1
        details["ema"] = f"BEARISH (EMA{cfg_a['ema_short']} < EMA{cfg_a['ema_long']})"

    # ── Price vs SMA50 ────────────────────────────────────────────────────────
    if ind["price"] > ind["sma_long"]:
        bullish_count += 1
        details["price_vs_sma50"] = "PRICE ABOVE SMA50"
    else:
        bearish_count += 1
        details["price_vs_sma50"] = "PRICE BELOW SMA50"

    # ── Volume Surge ──────────────────────────────────────────────────────────
    if ind["volume_ratio"] > 1.5:
        details["volume"] = f"HIGH VOLUME ({ind['volume_ratio']:.1f}x avg)"
        # Volume amplifies the dominant direction
        if bullish_count > bearish_count:
            bullish_count += 1
        elif bearish_count > bullish_count:
            bearish_count += 1
    else:
        details["volume"] = f"NORMAL VOLUME ({ind['volume_ratio']:.1f}x avg)"

    # ── Final Direction ───────────────────────────────────────────────────────
    bullish_count = int(bullish_count)
    bearish_count = int(bearish_count)
    if bullish_count > bearish_count:
        direction = "BUY"
        score = bullish_count
    elif bearish_count > bullish_count:
        direction = "SELL"
        score = bearish_count
    else:
        direction = "NEUTRAL"
        score = 0

    return direction, score, details


def get_4h_direction(ticker: str) -> tuple:
    """
    Fetch 4-hour candles and return (direction, rsi).
    Uses a simplified scoring: RSI + MACD + EMA crossover.
    Returns ("BUY"/"SELL"/"NEUTRAL", rsi_value).
    Falls back to ("NEUTRAL", 50.0) on any error.
    """
    try:
        # 4h candles: 60 days of data gives ~360 candles (enough for all indicators)
        df = fetch_data(ticker, period="60d", interval="4h")
        if df is None or len(df) < 30:
            return "NEUTRAL", 50.0

        cfg = ANALYSIS
        close = df["Close"]
        bull = 0
        bear = 0

        # RSI
        rsi_val = float(ta.momentum.RSIIndicator(close=close, window=cfg["rsi_period"]).rsi().iloc[-1])
        if rsi_val < cfg["rsi_oversold"]:
            bull += 1
        elif rsi_val > cfg["rsi_overbought"]:
            bear += 1

        # MACD
        macd_ind = ta.trend.MACD(close=close, window_fast=cfg["macd_fast"],
                                  window_slow=cfg["macd_slow"], window_sign=cfg["macd_signal"])
        macd_val  = float(macd_ind.macd().iloc[-1])
        macd_sig  = float(macd_ind.macd_signal().iloc[-1])
        macd_hist = float(macd_ind.macd_diff().iloc[-1])
        macd_prev = float(macd_ind.macd_diff().iloc[-2])
        if macd_val > macd_sig and macd_hist > macd_prev:
            bull += 1
        elif macd_val < macd_sig and macd_hist < macd_prev:
            bear += 1

        # EMA crossover
        ema_s = float(ta.trend.EMAIndicator(close=close, window=cfg["ema_short"]).ema_indicator().iloc[-1])
        ema_l = float(ta.trend.EMAIndicator(close=close, window=cfg["ema_long"]).ema_indicator().iloc[-1])
        if ema_s > ema_l:
            bull += 1
        else:
            bear += 1

        if bull > bear:
            return "BUY", rsi_val
        elif bear > bull:
            return "SELL", rsi_val
        else:
            return "NEUTRAL", rsi_val

    except Exception:
        return "NEUTRAL", 50.0


def analyse_ticker(ticker: str, name: str) -> TechnicalResult:
    """
    Full dual-timeframe technical analysis pipeline for a single ticker.
    Primary: daily candles. Secondary: 4h candles for confluence.
    """
    cfg_a = ANALYSIS
    cfg_s = SIGNAL

    # ── Primary: Daily Analysis ───────────────────────────────────────────────
    df = fetch_data(ticker, cfg_a["data_period"], cfg_a["data_interval"])
    if df is None:
        return TechnicalResult(
            ticker=ticker, name=name, price=0.0,
            direction="ERROR", score=0, strength="NONE",
            error=f"Failed to fetch daily data for {ticker}"
        )

    try:
        ind = compute_indicators(df)
    except Exception as e:
        return TechnicalResult(
            ticker=ticker, name=name, price=0.0,
            direction="ERROR", score=0, strength="NONE",
            error=str(e)
        )

    direction, score, details = score_signal(ind)

    # ── Secondary: 4h Confluence ──────────────────────────────────────────────
    tf_4h_dir, tf_4h_rsi = get_4h_direction(ticker)
    tf_confluence = "NONE"

    if direction != "NEUTRAL" and tf_4h_dir != "NEUTRAL":
        if direction == tf_4h_dir:
            # Both timeframes agree — boost score
            score = min(score + 1, 8)
            tf_confluence = "AGREE"
        else:
            # Timeframes diverge — reduce score (conflicting signal)
            score = max(score - 1, 0)
            tf_confluence = "DISAGREE"

    details["tf_4h"] = f"4H: {tf_4h_dir} (RSI {tf_4h_rsi:.1f}) | Confluence: {tf_confluence}"

    # ── Strength Classification ───────────────────────────────────────────────
    if score >= cfg_s["strong_signal_score"]:
        strength = "STRONG"
    elif score >= cfg_s["min_score_to_notify"]:
        strength = "MODERATE"
    else:
        strength = "WEAK"

    # ── Stop Loss & Take Profit ───────────────────────────────────────────────
    price = ind["price"]
    atr   = ind["atr"]
    if direction == "BUY":
        stop_loss   = round(price - (atr * cfg_s["stop_loss_atr_mult"]), 4)
        take_profit = round(price + (atr * cfg_s["take_profit_atr_mult"]), 4)
    elif direction == "SELL":
        stop_loss   = round(price + (atr * cfg_s["stop_loss_atr_mult"]), 4)
        take_profit = round(price - (atr * cfg_s["take_profit_atr_mult"]), 4)
    else:
        stop_loss   = 0.0
        take_profit = 0.0

    # ── MACD Cross Label ──────────────────────────────────────────────────────
    macd_cross = details.get("macd", "NEUTRAL")

    # ── Bollinger Position ────────────────────────────────────────────────────
    if ind["bb_pct"] < 0.2:
        bb_pos = "LOWER"
    elif ind["bb_pct"] > 0.8:
        bb_pos = "UPPER"
    else:
        bb_pos = "MIDDLE"

    return TechnicalResult(
        ticker         = ticker,
        name           = name,
        price          = round(price, 4),
        direction      = direction,
        score          = score,
        strength       = strength,
        rsi            = round(ind["rsi"], 2),
        macd_cross     = macd_cross,
        bb_position    = bb_pos,
        sma_trend      = details.get("sma", "NEUTRAL"),
        ema_trend      = details.get("ema", "NEUTRAL"),
        volume_surge   = ind["volume_ratio"] > 1.5,
        atr            = round(atr, 4),
        stop_loss      = stop_loss,
        take_profit    = take_profit,
        indicators     = {**ind, **details},
        tf_4h_direction = tf_4h_dir,
        tf_4h_rsi      = round(tf_4h_rsi, 2),
        tf_confluence  = tf_confluence,
    )
