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


def build_final_signal(result: TechnicalResult) -> dict:
    """Combine technical analysis + AI sentiment into a final signal package."""
    ai = analyse_with_ai(result)

    strength = result.strength
    if ai["confidence"] == "HIGH" and strength == "MODERATE":
        strength = "STRONG"
    elif ai["confidence"] == "LOW" and strength == "STRONG":
        strength = "MODERATE"

    return {
        "timestamp":       datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "ticker":          result.ticker,
        "name":            result.name,
        "direction":       result.direction,
        "score":           result.score,
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
        "executed":        "",
        "result_pct":      "",
    }
