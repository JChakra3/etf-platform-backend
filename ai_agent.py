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


def _mer_sentence(mer) -> str | None:
    if mer is None: return None
    pct = mer * 100
    if pct < 0.10: return f"Its annual fee is {pct:.3f} percent, which is exceptionally low and means fees take almost nothing from your returns."
    if pct < 0.25: return f"Its annual fee is {pct:.2f} percent, which is very low and well below the industry average of around 0.5 percent."
    if pct < 0.50: return f"Its annual fee is {pct:.2f} percent, which is below the industry average and makes it a cost-efficient choice."
    if pct < 0.90: return f"Its annual fee is {pct:.2f} percent, which is near the industry average and reasonable for the strategy it offers."
    return f"Its annual fee is {pct:.2f} percent, which is above average, so the higher cost should be weighed against what the fund offers."

def _yield_sentence(yld, aum) -> str | None:
    if yld is None and aum is None: return None
    parts = []
    if yld is not None:
        pct = yld * 100
        if pct == 0:
            parts.append("It pays no regular distributions so all returns come from price growth")
        elif pct < 1.0:
            parts.append(f"Its distribution yield is {pct:.2f} percent, which is minimal and reflects a focus on growth over income")
        elif pct < 3.0:
            parts.append(f"It pays a modest yield of {pct:.2f} percent, offering a small income stream alongside growth")
        elif pct < 6.0:
            parts.append(f"Its distribution yield of {pct:.2f} percent provides meaningful income for investors seeking regular payouts")
        else:
            parts.append(f"Its high distribution yield of {pct:.2f} percent makes it primarily an income-generating fund")
    if aum is not None:
        if aum > 10_000:
            parts.append(f"and with over {aum/1000:.0f} billion CAD in assets it is one of the largest and most liquid ETFs available")
        elif aum > 1_000:
            parts.append(f"and its {aum/1000:.1f} billion CAD in assets gives it strong liquidity")
        elif aum > 100:
            parts.append(f"and its {aum:.0f} million CAD in assets provides reasonable liquidity for most investors")
        else:
            parts.append(f"though its smaller size of {aum:.0f} million CAD means liquidity may be more limited")
    return ", ".join(parts) + "." if parts else None


def _clean_overview(text: str) -> str:
    """Strip any lines that look like leaked prompt instructions."""
    bad_keywords = ["sentence", "plain text", "no markdown", "rule:", "fact:", "output only",
                    "no bullet", "no asterisk", "no special", "no label", "sign-off", "intro"]
    lines = text.strip().splitlines()
    clean = [l for l in lines if not any(kw in l.lower() for kw in bad_keywords)]
    return " ".join(l.strip() for l in clean if l.strip())


async def generate_overview(etf: dict) -> str:
    """Generate a data-driven plain-English overview for an ETF detail page."""
    ticker    = etf.get('ticker', '')
    name      = etf.get('name', '')
    provider  = etf.get('provider', '')
    asset     = etf.get('asset_class', '')
    strategy  = etf.get('strategy_type', '')
    geo       = etf.get('geographic_exposure', '')
    covered   = etf.get('is_covered_call', False)
    leveraged = etf.get('is_leveraged', False)

    flags = []
    if covered:  flags.append("uses covered call options to boost income, which can limit upside in strong markets")
    if leveraged: flags.append("uses leverage to amplify returns, which also amplifies losses and increases risk significantly")

    # Pre-build data sentences — skip any where data is missing
    mer_sentence   = _mer_sentence(etf.get('mer'))
    yield_sentence = _yield_sentence(etf.get('distribution_yield'), etf.get('aum_cad'))

    data_lines = []
    if mer_sentence:   data_lines.append(f"- Fee fact: {mer_sentence}")
    if yield_sentence: data_lines.append(f"- Yield/size fact: {yield_sentence}")
    if flags:          data_lines.append(f"- Special note: {'; '.join(flags)}")
    data_block = "\n".join(data_lines) if data_lines else "- No additional data available"

    prompt = f"""Write 3 complete sentences about {ticker} ({name}) for a Canadian retail investor. Plain text only, no symbols or formatting.

1. What {ticker} tracks or holds and its investment strategy.
2. What type of investor it suits and what goal it serves.
3. Work these facts naturally into one sentence: {data_block}

Return only the 3 sentences. Each must end with a period."""

    response = _CLIENT.models.generate_content(
        model=_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.1, max_output_tokens=1000),
    )
    return _clean_overview(response.text)


def generate_search_tags(etf: dict) -> str:
    """Generate comma-separated search tags from ETF data (no Gemini — pure logic)."""
    tags: set[str] = set()

    ticker   = (etf.get("ticker")         or "").upper()
    name     = (etf.get("name")           or "").lower()
    country  = (etf.get("country")        or "").upper()
    currency = (etf.get("currency")       or "").upper()
    exchange = (etf.get("exchange")       or "").upper()
    asset    = (etf.get("asset_class")    or "").lower()
    strategy = (etf.get("strategy_type")  or "").lower()
    sector   = (etf.get("sector_focus")   or "").lower()
    goi      = (etf.get("growth_or_income") or "").lower()

    # ── Exchange ──────────────────────────────────────────────────────────────
    if "NASDAQ" in exchange or "NASDAQ" in name.upper():
        tags.update(["nasdaq", "nasdaq-100"])
    if "NYSE" in exchange:
        tags.add("nyse")
    if "TSX" in exchange or "TO" in exchange or country == "CA":
        tags.update(["tsx", "toronto stock exchange"])

    # ── Country / Currency ────────────────────────────────────────────────────
    if country == "CA":
        tags.update(["canada", "canadian", "cad"])
    elif country == "US":
        tags.update(["us", "american", "united states", "usa"])
    if currency == "CAD":
        tags.add("cad")
    if currency == "USD":
        tags.add("usd")

    # ── Asset class ───────────────────────────────────────────────────────────
    if any(w in asset for w in ["bond", "fixed"]):
        tags.update(["bonds", "bond", "fixed income", "fixed-income", "safe", "conservative"])
    if any(w in asset for w in ["stock", "equit"]):
        tags.update(["stocks", "equities", "equity"])
    if "gold" in asset:
        tags.update(["gold", "commodity", "commodities", "precious metals"])
    if "real estate" in asset or "reit" in asset:
        tags.update(["real estate", "reit", "property"])
    if "commodit" in asset:
        tags.update(["commodity", "commodities"])

    # ── Strategy flags ────────────────────────────────────────────────────────
    if etf.get("is_covered_call"):
        tags.update(["covered call", "covered-call", "options", "enhanced yield", "income", "monthly income"])
    if etf.get("is_leveraged"):
        tags.update(["leveraged", "2x", "3x", "aggressive", "high risk"])
    if etf.get("is_hedged"):
        tags.update(["hedged", "cad hedged", "currency hedged"])
    if "sector" in strategy:
        tags.add("sector")
    if "index" in strategy or "passive" in strategy:
        tags.update(["index", "passive"])

    # ── Yield profile ─────────────────────────────────────────────────────────
    yld = etf.get("distribution_yield")
    if yld is not None:
        pct = yld * 100
        if pct >= 5:
            tags.update(["high yield", "income", "dividend", "monthly income"])
        elif pct >= 2:
            tags.update(["dividend", "income", "moderate yield"])
        elif 0 < pct < 1:
            tags.update(["low yield", "growth"])
        elif pct == 0:
            tags.update(["low yield", "growth", "no dividend"])

    # ── MER / cost ────────────────────────────────────────────────────────────
    mer = etf.get("mer")
    if mer is not None:
        pct = mer * 100
        if pct < 0.20:
            tags.update(["cheap", "low fee", "low mer", "low cost", "low expense"])
        elif pct > 0.80:
            tags.add("expensive")

    # ── Growth or income label ────────────────────────────────────────────────
    if "growth" in goi:
        tags.add("growth")
    if "income" in goi:
        tags.add("income")

    # ── Theme detection from fund name / sector_focus ─────────────────────────
    combined = name + " " + sector
    theme_map = [
        # Indexes / benchmarks
        (["nasdaq", "nasdaq-100"],                               ["nasdaq", "nasdaq-100", "tech"]),
        (["s&p 500", "sp500", "s&p500", "s & p 500"],           ["sp500", "s&p 500", "index", "large cap"]),
        (["dow jones", "djia"],                                  ["dow jones", "blue chip", "large cap"]),
        (["russell 2000", "russell2000"],                        ["russell 2000", "small cap"]),
        (["ftse"],                                               ["ftse", "international"]),
        (["msci"],                                               ["msci", "international"]),
        (["tsx composite", "tsx 60", "s&p/tsx"],                 ["tsx composite", "tsx 60", "canadian"]),
        (["wilshire"],                                           ["total market", "index"]),
        # Sectors
        (["technology", "tech", "innovation"],                   ["tech", "technology", "sector"]),
        (["semiconductor", "chip"],                              ["semiconductors", "tech", "sector"]),
        (["cloud", "software"],                                  ["cloud", "tech", "sector"]),
        (["artificial intelligence", "ai "],                     ["artificial intelligence", "ai", "tech", "sector"]),
        (["clean energy", "renewable", "solar", "wind"],         ["clean energy", "solar", "renewable", "sector"]),
        (["electric vehicle", "ev "],                            ["electric vehicles", "ev", "sector"]),
        (["cannabis", "marijuana"],                              ["cannabis", "sector"]),
        (["health", "biotech", "pharma", "medical"],             ["healthcare", "biotech", "health", "sector"]),
        (["energy", "oil", "gas", "petroleum"],                  ["energy", "oil", "sector"]),
        (["financial", "bank", "banking"],                       ["financials", "banks", "sector"]),
        (["utility", "utilities"],                               ["utilities", "sector"]),
        (["real estate", "reit", "property"],                    ["real estate", "reit", "sector"]),
        (["consumer staples", "staples"],                        ["consumer staples", "defensive", "sector"]),
        (["consumer discretionary", "discretionary"],            ["consumer discretionary", "sector"]),
        (["industrial"],                                         ["industrials", "sector"]),
        (["material", "metal", "mining"],                        ["materials", "mining", "sector"]),
        (["aerospace", "defence", "defense"],                    ["aerospace", "defence", "sector"]),
        (["water", "infrastructure"],                            ["infrastructure", "sector"]),
        (["communication", "telecom", "media"],                  ["communications", "telecom", "sector"]),
        # Commodities
        (["gold", "bullion"],                                    ["gold", "commodities", "precious metals"]),
        (["silver"],                                             ["silver", "commodities", "precious metals"]),
        (["commodity", "commodities", "oil", "natural resource"], ["commodities", "natural resources"]),
        # Geography
        (["emerging", "developing"],                             ["emerging markets", "international"]),
        (["international", "global", "world", "all world"],      ["international", "global"]),
        (["europe", "european"],                                 ["europe", "international"]),
        (["asia", "pacific", "apac"],                            ["asia", "international"]),
        (["japan", "japanese"],                                  ["japan", "asia", "international"]),
        (["china", "chinese"],                                   ["china", "asia", "emerging markets"]),
        (["india", "indian"],                                    ["india", "asia", "emerging markets"]),
        (["latin america"],                                      ["latin america", "emerging markets"]),
        (["developed market"],                                   ["developed markets", "international"]),
        # Income / payout
        (["dividend", "yield"],                                  ["dividend", "income"]),
        (["monthly"],                                            ["monthly dividend", "monthly income", "income"]),
        (["quarterly"],                                          ["quarterly dividend", "income"]),
        (["distribution", "cash flow"],                          ["distribution", "income", "cash flow"]),
        (["passive income"],                                     ["passive income", "income"]),
        # Style / strategy
        (["value", "value fund"],                                ["value", "value stocks"]),
        (["growth stock", "growth fund"],                        ["growth stocks", "growth"]),
        (["momentum"],                                           ["momentum", "factor"]),
        (["small cap", "small-cap"],                             ["small cap", "small-cap"]),
        (["mid cap", "mid-cap"],                                 ["mid cap", "mid-cap"]),
        (["large cap", "large-cap", "blue chip"],                ["large cap", "blue chip"]),
        (["equal weight", "equal-weight"],                       ["equal weight"]),
        (["esg", "socially responsible", "sustainable", "responsible investing"], ["esg", "sustainable", "socially responsible"]),
        (["low volatility", "minimum volatility", "min vol"],    ["low volatility", "defensive", "conservative"]),
        (["defensive"],                                          ["defensive", "conservative"]),
        (["safe haven"],                                         ["safe haven", "conservative", "safe"]),
        (["factor", "smart beta"],                               ["factor", "smart beta"]),
        # Bonds (more granular)
        (["treasury", "government bond", "govt bond"],           ["treasury", "government bond", "bonds", "safe"]),
        (["corporate bond"],                                     ["corporate bond", "bonds"]),
        (["aggregate bond", "total bond"],                       ["aggregate bond", "total bond", "bonds"]),
        (["short term", "short-term bond"],                      ["short term", "bonds"]),
        (["long term", "long-term bond"],                        ["long term", "bonds"]),
        (["ultra short"],                                        ["ultra short", "bonds", "safe"]),
        (["high yield bond", "junk bond"],                       ["high yield bond", "junk bond", "bonds"]),
        (["investment grade"],                                   ["investment grade", "bonds"]),
        # Providers
        (["vanguard"],                                           ["vanguard"]),
        (["blackrock", "ishares", "i shares"],                   ["blackrock", "ishares"]),
        (["bmo"],                                                ["bmo"]),
        (["horizons", "hxt", "hxs"],                            ["horizons"]),
        (["mackenzie"],                                          ["mackenzie"]),
        (["fidelity"],                                           ["fidelity"]),
        (["invesco"],                                            ["invesco"]),
        (["spdr", "state street"],                               ["spdr", "state street"]),
        (["ark ", "ark invest"],                                 ["ark", "innovation", "growth"]),
        (["ci financial", "ci etf"],                             ["ci"]),
        # Savings / cash
        (["savings", "hisa", "high interest", "cash"],           ["savings", "hisa", "cash", "safe"]),
        # Account types
        (["tfsa"],                                               ["tfsa"]),
        (["rrsp"],                                               ["rrsp"]),
        (["fhsa"],                                               ["fhsa"]),
        (["resp"],                                               ["resp"]),
        # Investor profile
        (["beginner", "starter", "simple", "easy"],              ["beginner", "simple", "starter"]),
        (["retirement", "pension"],                              ["retirement", "long term"]),
        (["total market", "broad market"],                       ["total market", "broad market", "index", "passive"]),
        # Covered call / all-in-one
        (["covered call", "covered-call"],                       ["covered call", "income", "options"]),
        (["all-in-one", "all in one", "balanced"],               ["all-in-one", "balanced", "diversified"]),
    ]
    for keywords, add_tags in theme_map:
        if any(kw in combined for kw in keywords):
            tags.update(add_tags)

    # ── Known tickers — extra tags not derivable from name alone ─────────────
    if ticker in {"XEQT","VEQT","XGRO","VGRO","XBAL","VBAL","XCNS","VCONS","ZGRO","ZBAL"}:
        tags.update(["all-in-one", "balanced", "diversified", "passive", "beginner"])
    if ticker in {"QQQ","TQQQ","QYLD","XYLD","JEPQ"}:
        tags.update(["nasdaq", "nasdaq-100", "tech"])
    if ticker in {"VTI","VOO","SPY","IVV","SCHB","ITOT","VFV","ZSP","XSP","VSP","HXS"}:
        tags.update(["total market", "broad market", "index", "passive", "beginner", "sp500"])
    if ticker in {"ARKK"}:
        tags.update(["ark", "innovation", "growth", "aggressive", "speculative"])
    if ticker in {"GLD","IAU","CGL","MNT","HUG"}:
        tags.update(["gold", "precious metals", "commodities", "safe haven"])
    if ticker in {"SLV","SVR"}:
        tags.update(["silver", "precious metals", "commodities"])
    if ticker in {"HYG","JNK","HYI","HYLD"}:
        tags.update(["high yield bond", "junk bond", "bonds", "income"])
    if ticker in {"TLT","VGLT"}:
        tags.update(["long term", "treasury", "government bond", "bonds"])
    if ticker in {"SHY","BSV","VSB","XSB","ZSB"}:
        tags.update(["short term", "ultra short", "bonds", "safe"])
    if ticker in {"CASH","CSAV","HSAV"}:
        tags.update(["savings", "hisa", "cash", "safe", "ultra short"])
    if ticker in {"XIU","XIC","VCN","ZCN","HXT"}:
        tags.update(["tsx composite", "tsx 60", "canadian", "broad market"])
    if ticker in {"SCHD","VYM","DVY","XEI","VDY","CDZ","XDV","ZDV"}:
        tags.update(["dividend", "income", "dividend growth"])
    if ticker in {"XLK","VGT","XIT"}:
        tags.update(["tech", "technology", "semiconductors", "sector"])
    if ticker in {"XLV","VHT"}:
        tags.update(["healthcare", "biotech", "sector"])
    if ticker in {"XLE","VDE","XEG"}:
        tags.update(["energy", "oil", "sector"])
    if ticker in {"XLF","VFH","XFN","ZEB"}:
        tags.update(["financials", "banks", "sector"])
    if ticker in {"VNQ","XLRE","XRE","ZRE"}:
        tags.update(["real estate", "reit", "sector"])
    if ticker in {"SOXL","TECL","TQQQ","UPRO","SPXL"}:
        tags.update(["leveraged", "3x", "aggressive", "speculative", "high risk"])

    return ",".join(sorted(tags))


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
