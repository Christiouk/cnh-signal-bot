"""
CNH Signal Bot — AI Agent
==========================
Generates institutional-grade trading signal summaries using:

  PRIMARY:  Groq API (llama-3.3-70b-versatile) — free tier, very fast, no quota issues
  FALLBACK: Rule-based summary generator — always works, no external API required

Groq is OpenAI-API-compatible, so the openai Python package is used as the client.
Set GROQ_API_KEY in Railway environment variables.
Get a free key at: https://console.groq.com (free tier: 14,400 requests/day)

If GROQ_API_KEY is not set, the bot falls back to the rule-based engine automatically.
"""

import os
import json
import feedparser
from openai import OpenAI
from datetime import datetime
from technical_analysis import TechnicalResult
from config import NEWS_FEEDS

# ─── Groq client (OpenAI-compatible API) ──────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

groq_client = None
if GROQ_API_KEY:
    groq_client = OpenAI(
        api_key=GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1",
    )
    print("[AI] Using Groq (llama-3.3-70b-versatile) for AI analysis.")
else:
    print("[AI] GROQ_API_KEY not set — using rule-based fallback for AI summaries.")

SYSTEM_PROMPT = """You are a senior quantitative analyst and portfolio manager specialising in 
European ETFs, equity indices, commodities, and equities. You provide concise, institutional-grade 
trading signal assessments. Your analysis is always:
- Factual and data-driven
- Risk-aware (always mention key risks)
- Actionable (clear BUY / SELL / NEUTRAL recommendation)
- Concise (max 3 sentences for the summary)
You never give financial advice. You generate signals for informational purposes only.
Always respond with valid JSON only — no markdown, no extra text."""


def fetch_news_headlines(ticker: str, name: str, max_items: int = 6) -> list:
    """Fetch recent news headlines relevant to the asset."""
    headlines = []
    try:
        yf_url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
        feed = feedparser.parse(yf_url)
        for entry in feed.entries[:max_items]:
            headlines.append(entry.get("title", ""))
    except Exception:
        pass
    if len(headlines) < 3:
        keywords = ["europe", "euro", "ftse", "dax", "etf", "index", "market", "oil", "nasdaq", "s&p"]
        for feed_url in NEWS_FEEDS[:2]:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:4]:
                    title = entry.get("title", "")
                    if any(kw in title.lower() for kw in keywords):
                        headlines.append(title)
            except Exception:
                continue
    return headlines[:max_items]


def rule_based_analysis(result: TechnicalResult) -> dict:
    """Generate a structured signal summary using pure rule-based logic. No external API required."""
    direction = result.direction
    score = result.score
    rsi = result.rsi or 50

    sentiment = "BULLISH" if direction == "BUY" else ("BEARISH" if direction == "SELL" else "NEUTRAL")
    confidence = "HIGH" if score >= 6 else ("MEDIUM" if score >= 4 else "LOW")

    rsi_note = ""
    try:
        rsi_val = float(rsi)
        if rsi_val < 30:
            rsi_note = "RSI is oversold, suggesting potential reversal upside. "
        elif rsi_val > 70:
            rsi_note = "RSI is overbought, suggesting potential reversal downside. "
        elif direction == "BUY" and rsi_val < 50:
            rsi_note = "RSI has room to run higher before reaching overbought territory. "
        elif direction == "SELL" and rsi_val > 50:
            rsi_note = "RSI has room to fall before reaching oversold territory. "
    except (ValueError, TypeError):
        pass

    macd_note = ""
    if result.macd_cross == "bullish crossover":
        macd_note = "MACD shows a bullish crossover, confirming upward momentum. "
    elif result.macd_cross == "bearish crossover":
        macd_note = "MACD shows a bearish crossover, confirming downward momentum. "

    summary = (
        f"{result.name} ({result.ticker}) is showing a {direction} signal with {score}/7 "
        f"technical indicators aligned. {rsi_note}{macd_note}"
        f"Price is at the {result.bb_position} Bollinger Band with {result.sma_trend} trend on the SMA."
    ).strip()

    if direction == "BUY":
        risk = f"Key risk: a break below the stop-loss at {result.stop_loss} would invalidate the bullish setup."
    elif direction == "SELL":
        risk = f"Key risk: a recovery above {result.stop_loss} would invalidate the bearish setup."
    else:
        risk = "Signal is weak — low conviction. Wait for stronger confirmation before entering."

    return {"sentiment": sentiment, "confidence": confidence, "summary": summary, "risks": risk}


def analyse_with_groq(result: TechnicalResult) -> dict:
    """Send technical data + news to Groq. Falls back to rule-based if unavailable."""
    if not groq_client:
        return rule_based_analysis(result)

    headlines = fetch_news_headlines(result.ticker, result.name)
    news_block = "\n".join(f"- {h}" for h in headlines) if headlines else "No recent headlines available."

    user_prompt = f"""
Analyse the following trading signal for {result.name} ({result.ticker}):

TECHNICAL INDICATORS:
- Current Price: {result.price}
- Signal Direction: {result.direction}
- Signal Score: {result.score}/8 indicators aligned (includes 4h confluence)
- Signal Strength: {result.strength}
- RSI (14, daily): {result.rsi}
- MACD: {result.macd_cross}
- Bollinger Bands: Price at {result.bb_position} band
- SMA Trend: {result.sma_trend}
- EMA Trend: {result.ema_trend}
- ATR: {result.atr}
- Suggested Stop-Loss: {result.stop_loss}
- Suggested Take-Profit: {result.take_profit}
- 4H Timeframe Direction: {result.tf_4h_direction} (RSI: {result.tf_4h_rsi})
- Timeframe Confluence: {result.tf_confluence} (AGREE = both daily+4h aligned, DISAGREE = conflicting)

RECENT NEWS HEADLINES:
{news_block}

Respond ONLY with this JSON (no markdown, no extra text):
{{
  "sentiment": "BULLISH",
  "confidence": "MEDIUM",
  "summary": "2-3 sentence executive summary.",
  "risks": "One sentence on the main risk."
}}
"""

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=350,
        )
        content = response.choices[0].message.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()
        data = json.loads(content)
        return {
            "sentiment":  data.get("sentiment",  "NEUTRAL"),
            "confidence": data.get("confidence", "LOW"),
            "summary":    data.get("summary",    "No summary available."),
            "risks":      data.get("risks",      "No specific risks identified."),
        }
    except json.JSONDecodeError as e:
        print(f"[AI] Groq returned invalid JSON: {e} — using rule-based fallback.")
        return rule_based_analysis(result)
    except Exception as e:
        print(f"[AI] Groq error: {e} — using rule-based fallback.")
        return rule_based_analysis(result)


def analyse_with_ai(result: TechnicalResult) -> dict:
    """Primary entry point. Tries Groq first; falls back to rule-based if unavailable."""
    return analyse_with_groq(result)


def _build_risk_note(result: TechnicalResult, ai_risks: str) -> str:
    """
    Build a concise risk note combining AI-generated risks with
    key technical context (confluence, RSI extremes, volume).
    """
    parts = []
    if ai_risks and ai_risks != "No specific risks identified.":
        parts.append(ai_risks)
    if result.tf_confluence == "DISAGREE":
        parts.append("4H and daily timeframes are conflicting — reduce position size.")
    if result.rsi > 75:
        parts.append(f"RSI at {result.rsi:.1f} — overbought territory, risk of short-term reversal.")
    elif result.rsi < 25:
        parts.append(f"RSI at {result.rsi:.1f} — oversold territory, risk of short-term bounce.")
    if not parts:
        if result.direction == "BUY":
            parts.append(f"Monitor stop-loss at {result.stop_loss} for invalidation of bullish thesis.")
        elif result.direction == "SELL":
            parts.append(f"Monitor stop-loss at {result.stop_loss} for invalidation of bearish thesis.")
    return " ".join(parts)


def _build_hedge_suggestion(result: TechnicalResult) -> str:
    """
    Generate a simple hedge suggestion based on asset category and direction.
    """
    cat = result.asset_category
    direction = result.direction

    if cat == "Index":
        if direction == "BUY":
            return "Consider protective puts on the index or a short position in a correlated inverse ETF as a hedge."
        else:
            return "Consider a long position in a defensive sector ETF (e.g. utilities, healthcare) as a partial hedge."
    elif cat == "ETF":
        if direction == "BUY":
            return "Consider a small allocation to a short-duration bond ETF to hedge equity downside."
        else:
            return "Consider a long position in a broad market ETF to hedge concentrated short exposure."
    elif cat == "Commodity":
        if direction == "BUY":
            return "Consider a correlated commodity producer equity as a leveraged hedge (e.g. oil major for crude signals)."
        else:
            return "Consider a long position in consumer discretionary equities that benefit from lower commodity prices."
    elif cat == "FX":
        if direction == "BUY":
            return "Consider a small position in the counter-currency as a partial hedge against FX reversal."
        else:
            return "Consider a long position in the base currency as a directional hedge."
    elif cat == "Crypto":
        if direction == "BUY":
            return "Consider a stablecoin allocation (USDC/USDT) as a partial hedge against crypto volatility."
        else:
            return "Consider a long position in Bitcoin dominance as a relative hedge within the crypto space."
    else:  # Equity
        if direction == "BUY":
            return "Consider a protective put option or a short position in a sector peer as a hedge."
        else:
            return "Consider a long position in a sector ETF to hedge single-stock short exposure."


def build_final_signal(result: TechnicalResult) -> dict:
    """Combine technical analysis + AI sentiment into a final signal package."""
    ai = analyse_with_ai(result)

    strength = result.strength
    if ai["confidence"] == "HIGH" and strength == "MODERATE":
        strength = "STRONG"
    elif ai["confidence"] == "LOW" and strength == "STRONG":
        strength = "MODERATE"

    risk_note       = _build_risk_note(result, ai.get("risks", ""))
    hedge_suggestion = _build_hedge_suggestion(result)

    return {
        "timestamp":       datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "ticker":          result.ticker,
        "name":            result.name,
        "direction":       result.direction,
        "score":           result.score,
        "score_max":       8,   # max score with 4H confluence bonus
        "strength":        strength,
        "price":           result.price,
        "stop_loss":       result.stop_loss,
        "take_profit":     result.take_profit,
        "rsi":             result.rsi,
        "macd":            result.macd_cross,
        "bb":              result.bb_position,
        "sma":             result.sma_trend,
        "atr":             result.atr,
        "volume_surge":    result.volume_surge,
        "sentiment":       ai["sentiment"],
        "confidence":      ai["confidence"],
        "ai_summary":      ai["summary"],
        "ai_risks":        ai["risks"],
        # 4h confluence fields
        "tf_4h_direction": result.tf_4h_direction,
        "tf_4h_rsi":       result.tf_4h_rsi,
        "tf_confluence":   result.tf_confluence,
        # v4.0 new fields
        "asset_category":       result.asset_category,
        "risk_note":            risk_note,
        "hedge_suggestion":     hedge_suggestion,
        "entry_low":            result.entry_low,
        "entry_high":           result.entry_high,
        "moderate_entry_low":   result.moderate_entry_low,
        "moderate_entry_high":  result.moderate_entry_high,
        "risky_entry_low":      result.risky_entry_low,
        "risky_entry_high":     result.risky_entry_high,
        "close_low":            result.close_low,
        "close_high":           result.close_high,
        "executed":        "",
        "result_pct":      "",
    }
