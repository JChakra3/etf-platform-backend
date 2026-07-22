"""
AI agent logic: conversational ETF assistant powered by Gemini.
Uses the DB as context — searches for relevant ETFs based on the conversation,
then passes structured data to Gemini alongside the full chat history.
"""
import os
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

_CLIENT = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
_MODEL = "gemini-3.5-flash"

_SYSTEM_PROMPT = """You are an expert ETF research assistant for a Canadian-focused retail investing platform.

HOW TO ANSWER:
Step 1 - Check the ETF Database Context appended to the user's message. These are real ETFs from our platform with live data (MER, yield, AUM, exchange, price).
Step 2 - Use the database ETFs as your primary examples. Mention their real ticker, what they track, their MER, and yield.
Step 3 - Supplement with your own ETF knowledge for any well-known ETFs not in the database (VFV, XIU, ZAG, VAB, QQQ, SPY, etc.). Note if they may not be on our platform.
Step 4 - Combine both into a clear, complete answer that directly addresses the user's question.

ALWAYS name specific ETF tickers. Never give a vague answer. If asked about any ETF category, list at least 3-5 real ETFs with their tickers, what index they track, approximate MER, and typical yield range. Use real numbers from the database when available; use your training knowledge otherwise.

FORMATTING:
- Plain text only. No markdown, no asterisks, no bold, no # headings.
- One short intro sentence, then a numbered list of ETFs, then a brief closing explanation.
- Each ETF entry: "1. TICKER - Name (what it tracks). MER: X%. Yield: ~X%. Suited for: [investor type]."

BOUNDARIES:
- Never say "you should buy X" or make a direct personal recommendation.
- Always end with: This is for informational purposes only and is not financial advice. Please consult a financial advisor."""


def _format_etf_context(etfs: list[dict]) -> str:
    if not etfs:
        return "No specific ETF data found for this query."
    lines = []
    for e in etfs[:8]:
        lines.append(
            f"- {e.get('ticker')} | {e.get('name')} | {e.get('provider')} | "
            f"MER: {e.get('mer')}% | Yield: {e.get('distribution_yield')}% | "
            f"AUM: ${e.get('aum_cad')}M CAD | Exchange: {e.get('exchange')} | "
            f"Asset Class: {e.get('asset_class')} | Strategy: {e.get('strategy_type')} | "
            f"Currency: {e.get('currency')} | Country: {e.get('country')} | "
            f"Price: {e.get('price')} | Risk Score: {e.get('risk_score')}/5 | "
            f"Covered Call: {e.get('is_covered_call')} | Leveraged: {e.get('is_leveraged')}"
        )
    return "\n".join(lines)


async def chat(messages: list[dict], db_fetch) -> str:
    """
    messages: list of {role: 'user'|'assistant', content: str}
    db_fetch: async callable(sql, params) -> list[dict]
    """
    recent_text = " ".join(m["content"] for m in messages[-3:]).lower()
    etfs = await _fetch_relevant_etfs(recent_text, db_fetch)
    context_block = _format_etf_context(etfs)

    # Build contents as plain dicts (same pattern as pipeline/extract.py)
    contents = []
    for m in messages[:-1]:
        role = "user" if m["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": m["content"]}]})

    last_content = messages[-1]["content"]
    augmented = f"{last_content}\n\n[ETF Database Context]\n{context_block}"
    contents.append({"role": "user", "parts": [{"text": augmented}]})

    # If only one message, generate_content accepts a plain string
    if len(contents) == 1:
        prompt = f"{_SYSTEM_PROMPT}\n\n{augmented}"
        response = _CLIENT.models.generate_content(
            model=_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.4, max_output_tokens=3000),
        )
    else:
        response = _CLIENT.models.generate_content(
            model=_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=_SYSTEM_PROMPT,
                temperature=0.4,
                max_output_tokens=3000,
            ),
        )
    return response.text


async def generate_overview(etf: dict) -> str:
    """Generate a data-driven plain-English overview for an ETF detail page."""
    mer = etf.get('mer')
    yld = etf.get('distribution_yield')
    aum = etf.get('aum_cad')
    risk = etf.get('risk_score')

    # Give context benchmarks so Gemini can make meaningful comparisons
    mer_context = ""
    if mer is not None:
        if mer < 0.001:
            mer_context = f"MER of {mer*100:.3f}% — exceptionally low, among the cheapest ETFs available, meaning nearly all returns go to the investor"
        elif mer < 0.005:
            mer_context = f"MER of {mer*100:.2f}% — very low cost, well below the industry average of ~0.5%"
        elif mer < 0.01:
            mer_context = f"MER of {mer*100:.2f}% — low cost, below the industry average"
        elif mer < 0.02:
            mer_context = f"MER of {mer*100:.2f}% — moderate cost, near the industry average"
        else:
            mer_context = f"MER of {mer*100:.2f}% — above average cost, which will meaningfully drag on long-term returns"

    yld_context = ""
    if yld is not None:
        if yld == 0:
            yld_context = "pays no distributions — all returns come from price appreciation"
        elif yld < 0.01:
            yld_context = f"very low yield of {yld*100:.2f}% — oriented toward growth rather than income"
        elif yld < 0.03:
            yld_context = f"modest yield of {yld*100:.2f}% — a small income component alongside growth"
        elif yld < 0.06:
            yld_context = f"solid yield of {yld*100:.2f}% — meaningful income for investors"
        else:
            yld_context = f"high yield of {yld*100:.2f}% — primarily an income-focused fund"

    aum_context = ""
    if aum is not None:
        if aum > 10000:
            aum_context = f"${aum/1000:.1f}B CAD AUM — very large, highly liquid fund"
        elif aum > 1000:
            aum_context = f"${aum/1000:.1f}B CAD AUM — large, liquid fund"
        elif aum > 100:
            aum_context = f"${aum:.0f}M CAD AUM — mid-sized fund with reasonable liquidity"
        else:
            aum_context = f"${aum:.0f}M CAD AUM — smaller fund, liquidity may be limited"

    prompt = f"""Write a 4-5 sentence plain-English overview of this ETF for a retail Canadian investor.

Use the data insights below to make specific observations about this ETF — comment on whether the MER is notable, what the yield means for investors, and how the fund size affects liquidity. Be direct and informative, as if a knowledgeable friend is explaining it. Do not use bullet points or markdown. Do not start with the ticker name.

ETF Facts:
- Ticker: {etf.get('ticker')}
- Name: {etf.get('name')}
- Provider: {etf.get('provider')}
- Asset Class: {etf.get('asset_class')}
- Strategy: {etf.get('strategy_type')}
- Geographic Exposure: {etf.get('geographic_exposure')}
- Exchange: {etf.get('exchange')}
- Covered Call: {etf.get('is_covered_call')}
- Leveraged: {etf.get('is_leveraged')}
- Risk Score: {risk}/5
- Prior AI Summary: {etf.get('ai_summary')}

Data Insights (use these in your overview):
- {mer_context or 'MER not available'}
- {yld_context or 'Yield not available'}
- {aum_context or 'AUM not available'}
"""
    response = _CLIENT.models.generate_content(
        model=_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.3, max_output_tokens=400),
    )
    return response.text.strip()


async def _fetch_relevant_etfs(query_text: str, db_fetch) -> list[dict]:
    """Intent-aware ETF lookup from the DB."""
    import re
    q = query_text.lower()
    rows = []
    existing: set[str] = set()

    def _merge(new_rows):
        for r in new_rows:
            if r["ticker"] not in existing:
                existing.add(r["ticker"])
                rows.append(r)

    # 1. Specific tickers mentioned by the user
    tickers = re.findall(r'\b([A-Z]{2,5})\b', query_text.upper())
    if tickers:
        placeholders = ",".join("?" for _ in tickers[:6])
        _merge(await db_fetch(
            f"SELECT * FROM etfs WHERE ticker IN ({placeholders})",
            tickers[:6],
        ))

    # 2. Intent-based queries — translate natural language to SQL filters
    intents = []

    if any(w in q for w in ["low yield", "low distribution", "growth", "growth etf", "simple", "broad market", "index", "safe"]):
        intents.append(("distribution_yield ASC", "growth_or_income = 'Growth' OR asset_class = 'Stocks'"))

    if any(w in q for w in ["high yield", "income", "dividend", "monthly", "distribution"]):
        intents.append(("distribution_yield DESC", "distribution_yield > 0"))

    if any(w in q for w in ["bond", "fixed income", "safe", "low risk", "conservative"]):
        intents.append(("aum_cad DESC", "asset_class = 'Bonds'"))

    if any(w in q for w in ["covered call", "option", "enhanced yield"]):
        intents.append(("distribution_yield DESC", "is_covered_call = 1"))

    if any(w in q for w in ["leverage", "leveraged", "2x", "3x"]):
        intents.append(("aum_cad DESC", "is_leveraged = 1"))

    if any(w in q for w in ["sector", "tech", "technology", "health", "energy", "financial"]):
        intents.append(("aum_cad DESC", "strategy_type = 'Sector'"))

    if any(w in q for w in ["canadian", "canada", "tsx", "canadian market"]):
        intents.append(("aum_cad DESC", "country = 'CA'"))

    if any(w in q for w in ["us ", "american", "s&p", "nasdaq", "nyse", "united states"]):
        intents.append(("aum_cad DESC", "country = 'US'"))

    if any(w in q for w in ["cheap", "low mer", "low fee", "low cost", "low expense"]):
        intents.append(("mer ASC", "mer IS NOT NULL AND mer > 0"))

    if any(w in q for w in ["gold", "commodity", "commodities", "oil", "real estate", "reit"]):
        intents.append(("aum_cad DESC", "asset_class IN ('Gold', 'Commodities', 'Real Estate')"))

    for order, where in intents:
        _merge(await db_fetch(
            f"SELECT * FROM etfs WHERE {where} AND aum_cad IS NOT NULL ORDER BY {order} LIMIT 8",
            [],
        ))

    # 3. Fallback: top ETFs by AUM if nothing matched
    if not rows:
        _merge(await db_fetch(
            "SELECT * FROM etfs WHERE aum_cad IS NOT NULL ORDER BY aum_cad DESC LIMIT 12", []
        ))

    return rows[:15]
