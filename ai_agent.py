"""
CNH Signal Bot — AI Agent (OpenAI)
=====================================
Uses OpenAI GPT to:
1. Fetch and analyse recent news sentiment for the asset.
2. Synthesise the technical analysis into a human-readable signal summary.
3. Assign a final confidence rating combining technicals + sentiment.
"""

import os
import feedparser
import requests
from openai import OpenAI
from datetime import datetime
from technical_analysis import TechnicalResult
from config import NEWS_FEEDS

# Initialise OpenAI client (uses OPENAI_API_KEY env var automatically)
client = OpenAI()

SYSTEM_PROMPT = """You are a senior quantitative analyst and portfolio manager specialising in 
European ETFs and equity indices. You provide concise, institutional-grade trading signal 
assessments. Your analysis is always:
- Factual and data-driven
- Risk-aware (always mention key risks)
- Actionable (clear BUY / SELL / NEUTRAL recommendation)
- Concise (max 4 sentences for the summary)
You never give financial advice. You generate signals for informational purposes only."""


def fetch_news_headlines(ticker: str, name: str, max_items: int = 8) -> list[str]:
    """Fetch recent news headlines relevant to the asset."""
    headlines = []

    # Try Yahoo Finance RSS for the specific ticker
    try:
        yf_url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
        feed = feedparser.parse(yf_url)
        for entry in feed.entries[:max_items]:
            headlines.append(entry.get("title", ""))
    except Exception:
        pass

    # Fallback: general European finance feeds
    if len(headlines) < 3:
        for feed_url in NEWS_FEEDS[:2]:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:3]:
                    title = entry.get("title", "")
                    if any(kw in title.lower() for kw in ["europe", "euro", "ftse", "dax", "etf", "index", "market"]):
                        headlines.append(title)
            except Exception:
                continue

    return headlines[:max_items]


def analyse_with_ai(result: TechnicalResult) -> dict:
    """
    Send technical data + news to the AI agent.
    Returns: { "sentiment": str, "confidence": str, "summary": str, "risks": str }
    """
    headlines = fetch_news_headlines(result.ticker, result.name)
    news_block = "\n".join(f"- {h}" for h in headlines) if headlines else "No recent headlines available."

    # Build the analysis prompt
    user_prompt = f"""
Analyse the following trading signal for {result.name} ({result.ticker}):

TECHNICAL INDICATORS:
- Current Price: {result.price}
- Signal Direction: {result.direction}
- Signal Score: {result.score}/7 indicators aligned
- Signal Strength: {result.strength}
- RSI (14): {result.rsi} → {result.indicators.get('rsi', 'N/A')}
- MACD: {result.macd_cross}
- Bollinger Bands: Price at {result.bb_position} band
- SMA Trend: {result.sma_trend}
- EMA Trend: {result.ema_trend}
- Volume: {result.indicators.get('volume', 'N/A')}
- ATR: {result.atr}
- Suggested Stop-Loss: {result.stop_loss}
- Suggested Take-Profit: {result.take_profit}

RECENT NEWS HEADLINES:
{news_block}

Based on this data, provide:
1. SENTIMENT: Overall market sentiment for this asset (BULLISH / BEARISH / NEUTRAL / MIXED)
2. CONFIDENCE: Your confidence in this signal (HIGH / MEDIUM / LOW) — considering both technicals and news
3. SUMMARY: A 2-3 sentence executive summary of why this signal is or isn't compelling
4. RISKS: One sentence on the main risk to this trade

Respond in this exact JSON format:
{{
  "sentiment": "BULLISH",
  "confidence": "MEDIUM",
  "summary": "...",
  "risks": "..."
}}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=300,
            response_format={"type": "json_object"}
        )
        import json
        content = response.choices[0].message.content
        data = json.loads(content)
        return {
            "sentiment":  data.get("sentiment",  "NEUTRAL"),
            "confidence": data.get("confidence", "LOW"),
            "summary":    data.get("summary",    "No summary available."),
            "risks":      data.get("risks",      "No specific risks identified."),
        }
    except Exception as e:
        return {
            "sentiment":  "NEUTRAL",
            "confidence": "LOW",
            "summary":    f"AI analysis unavailable: {str(e)}",
            "risks":      "Unable to assess risks at this time.",
        }


def build_final_signal(result: TechnicalResult) -> dict:
    """
    Combine technical analysis + AI sentiment into a final signal package.
    Returns a complete signal dict ready for notification and logging.
    """
    ai = analyse_with_ai(result)

    # Upgrade/downgrade strength based on AI confidence
    strength = result.strength
    if ai["confidence"] == "HIGH" and strength == "MODERATE":
        strength = "STRONG"
    elif ai["confidence"] == "LOW" and strength == "STRONG":
        strength = "MODERATE"

    return {
        "timestamp":    datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "ticker":       result.ticker,
        "name":         result.name,
        "direction":    result.direction,
        "score":        result.score,
        "strength":     strength,
        "price":        result.price,
        "stop_loss":    result.stop_loss,
        "take_profit":  result.take_profit,
        "rsi":          result.rsi,
        "macd":         result.macd_cross,
        "bb":           result.bb_position,
        "sma":          result.sma_trend,
        "atr":          result.atr,
        "volume_surge": result.volume_surge,
        "sentiment":    ai["sentiment"],
        "confidence":   ai["confidence"],
        "ai_summary":   ai["summary"],
        "ai_risks":     ai["risks"],
        "executed":     "",   # filled in later by user
        "result_pct":   "",   # filled in later by user
    }
