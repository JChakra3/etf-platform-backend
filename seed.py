"""
Seed ~19 real ETFs into the active Turso database.
Run AFTER setup_db.py:   python seed.py
"""
import asyncio, os
from datetime import datetime, UTC
from dotenv import load_dotenv
import libsql_client

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

NOW = datetime.now(UTC).isoformat()
AS_OF = "2025-06-30"

ETFS = [
    (
        "VFV","Vanguard S&P 500 Index ETF","Vanguard","TSX","CA","CAD","2012-11-02",
        "Equity","Stocks","Passive Index",None,"US",
        0,0,0,0,0, 0.0123,"Quarterly","Growth", 0.0009,0.0008,12400.0,
        4,4,3,1,1,1,3, 1,1,
        "US dividends held in a TFSA are subject to a 15% US withholding tax. Hold in RRSP to avoid this.",
        None,
        "VFV tracks the 500 largest US companies in Canadian dollars. It's the go-to for Canadians wanting S&P 500 exposure without currency conversion. One catch: US dividends inside a TFSA are taxed 15% at source — use your RRSP instead.",
        "sp500 s&p 500 us equity index passive large cap growth vanguard cad canadian",
        "https://www.vanguard.ca/en/advisor/products/products-group/etfs/VFV",
    ),
    (
        "XEQT","iShares Core Equity ETF Portfolio","BlackRock","TSX","CA","CAD","2019-08-07",
        "Equity","Stocks","Passive Index",None,"Global",
        0,0,0,0,0, 0.0155,"Quarterly","Growth", 0.0020,0.0018,5200.0,
        4,4,2,1,1,1,2, 1,1,
        "Foreign dividends in a TFSA may have a portion withheld at source.",
        None,
        "XEQT is a single-ticket 100% global equity portfolio holding thousands of stocks across Canada, the US, and international markets. Perfect for investors who want a complete equity portfolio in one ETF and don't need bonds yet.",
        "all equity global world diversified one ticket portfolio beginner simple blackrock ishares cad",
        "https://ca.ishares.com/product_info/fund/overview/XEQT",
    ),
    (
        "VEQT","Vanguard All-Equity ETF Portfolio","Vanguard","TSX","CA","CAD","2019-01-29",
        "Equity","Stocks","Passive Index",None,"Global",
        0,0,0,0,0, 0.0165,"Annual","Growth", 0.0024,0.0022,4800.0,
        4,4,2,1,1,1,2, 1,1,
        "Foreign dividends in a TFSA may face foreign withholding taxes.",
        None,
        "VEQT is Vanguard's one-fund global equity portfolio with a slight tilt towards Canadian stocks. Main trade-off vs XEQT: slightly higher Canadian exposure and dividends paid only once a year.",
        "all equity global world diversified one ticket couch potato beginner simple vanguard cad",
        "https://www.vanguard.ca/en/advisor/products/products-group/etfs/VEQT",
    ),
    (
        "CASH","Global X High Interest Savings ETF","Global X","TSX","CA","CAD","2019-04-17",
        "Cash","Cash","Active","Financial","Canada",
        0,0,0,0,0, 0.0482,"Monthly","Income", 0.0011,0.0010,3800.0,
        1,1,2,1,1,1,1, 1,1,
        None,None,
        "CASH parks your money in high-interest accounts at Canada's big banks, paying monthly interest that beats most savings accounts. Price stays at ~$50 and never fluctuates — it's an ETF version of a savings account, not a market investment.",
        "cash savings high interest hisa safe stable parking money bank account monthly income low risk",
        "https://horizonsetfs.com/ETF/CASH/",
    ),
    (
        "ZAG","BMO Aggregate Bond Index ETF","BMO","TSX","CA","CAD","2010-01-19",
        "Fixed Income","Bonds","Passive Index",None,"Canada",
        0,0,0,0,0, 0.0345,"Monthly","Income", 0.0009,0.0008,7200.0,
        2,2,2,1,1,2,1, 1,1,
        None,None,
        "ZAG holds a broad mix of Canadian government and corporate bonds, paying monthly distributions. It's the standard bond building block Canadians use to balance an equity portfolio — when stocks fall, bonds like ZAG often hold steady.",
        "bond bonds fixed income conservative safe balanced couch potato canadian government corporate bmo",
        "https://www.bmo.com/en/main/personal/investments/etfs/fund-details/?fundUrl=zag",
    ),
    (
        "XBB","iShares Core Canadian Universe Bond Index ETF","BlackRock","TSX","CA","CAD","2000-11-20",
        "Fixed Income","Bonds","Passive Index",None,"Canada",
        0,0,0,0,0, 0.0338,"Monthly","Income", 0.0010,0.0009,4100.0,
        2,2,2,1,1,2,1, 1,1,
        None,None,
        "XBB is one of Canada's oldest and most trusted bond ETFs, tracking the entire Canadian investment-grade bond universe. Virtually identical to ZAG — your choice mostly comes down to which brokerage offers the better commission.",
        "bond bonds fixed income conservative canadian universe blackrock ishares monthly income",
        "https://ca.ishares.com/product_info/fund/overview/XBB",
    ),
    (
        "XIU","iShares S&P/TSX 60 Index ETF","BlackRock","TSX","CA","CAD","1999-09-28",
        "Equity","Stocks","Passive Index",None,"Canada",
        0,0,0,0,0, 0.0268,"Quarterly","Balanced", 0.0018,0.0015,13700.0,
        3,3,3,1,1,1,1, 1,1,
        None,None,
        "XIU is Canada's oldest ETF, holding the 60 largest Canadian companies. Heavily concentrated in banks and energy — great for Canadian dividend income with no foreign withholding tax, but very little tech exposure.",
        "canada canadian tsx 60 banks energy dividend domestic large cap blackrock ishares",
        "https://ca.ishares.com/product_info/fund/overview/XIU",
    ),
    (
        "XEI","iShares S&P/TSX Composite High Dividend Index ETF","BlackRock","TSX","CA","CAD","2011-04-12",
        "Equity","Stocks","Dividend Growth",None,"Canada",
        0,0,0,0,0, 0.0510,"Monthly","Income", 0.0022,0.0020,1600.0,
        3,3,3,1,1,2,1, 1,1,
        None,
        "A small portion of distributions may be classified as Return of Capital, reducing your adjusted cost base and deferring some tax.",
        "XEI targets high-dividend Canadian stocks paying monthly. The yield is attractive but the portfolio is heavily weighted toward financials and energy — if Canadian banks or oil companies struggle, this ETF will feel it.",
        "high yield dividend income monthly canadian tsx banks energy financial sector",
        "https://ca.ishares.com/product_info/fund/overview/XEI",
    ),
    (
        "HMAX","Hamilton Canadian Financials Yield Maximizer ETF","Hamilton ETFs","TSX","CA","CAD","2022-12-01",
        "Equity","Stocks","Covered Call","Financial","Canada",
        1,0,0,0,0, 0.1350,"Monthly","Income", 0.0065,0.0055,800.0,
        3,3,4,1,2,2,1, 1,1,
        None,
        "A significant portion of HMAX distributions is Return of Capital. This is not income earned — it's your own money being returned, which reduces your cost base and creates a deferred capital gain.",
        "HMAX holds Canadian bank stocks and sells covered call options to boost the monthly payout to ~13%. Trade-off: when bank stocks rally, you miss most of the upside. Best for income-focused investors who are okay with capped growth.",
        "covered call high yield income monthly banks financials canadian yield maximizer hamilton roc",
        "https://hamiltonetfs.com/etf/hmax/",
    ),
    (
        "ZSP","BMO S&P 500 Index ETF","BMO","TSX","CA","CAD","2012-11-14",
        "Equity","Stocks","Passive Index",None,"US",
        0,0,0,0,0, 0.0118,"Quarterly","Growth", 0.0009,0.0008,9800.0,
        4,4,3,1,1,1,3, 1,1,
        "US dividends in a TFSA face 15% US withholding tax. Prefer RRSP for this ETF.",
        None,
        "ZSP is BMO's version of VFV — both track the S&P 500 in CAD at the same 0.09% MER. The choice is personal preference or brokerage. Neither is currency-hedged, so a stronger USD boosts returns; a weaker USD hurts.",
        "sp500 s&p 500 us equity index passive bmo cad canadian large cap",
        "https://www.bmo.com/en/main/personal/investments/etfs/fund-details/?fundUrl=zsp",
    ),
    (
        "VOO","Vanguard S&P 500 ETF","Vanguard","NYSE Arca","US","USD","2010-09-07",
        "Equity","Stocks","Passive Index",None,"US",
        0,0,0,0,0, 0.0130,"Quarterly","Growth", 0.0003,0.0003,1400000.0,
        4,4,3,1,1,1,1, 1,1,
        "Canadians buying VOO directly pay US withholding tax on dividends in a TFSA. Use VFV or ZSP (TSX-listed) for the same exposure in CAD.",
        None,
        "VOO is the gold standard S&P 500 ETF at just 0.03% MER — among the cheapest funds on earth. Holds 500 of America's largest companies. Canadians may prefer VFV to avoid withholding tax complexity.",
        "sp500 s&p 500 us equity index vanguard cheapest low fee large cap growth warren buffett",
        "https://investor.vanguard.com/investment-products/etfs/profile/voo",
    ),
    (
        "VTI","Vanguard Total Stock Market ETF","Vanguard","NYSE Arca","US","USD","2001-05-24",
        "Equity","Stocks","Passive Index",None,"US",
        0,0,0,0,0, 0.0125,"Quarterly","Growth", 0.0003,0.0003,560000.0,
        4,4,2,1,1,1,1, 1,1,
        "Canadian investors face US withholding tax on dividends held outside an RRSP.",
        None,
        "VTI goes broader than VOO — it holds over 3,600 US stocks including small and mid-cap companies. Historically returns are nearly identical to VOO, but you get slightly more diversification across the full US economy.",
        "total market us equity all cap small mid large vanguard index broad diversified",
        "https://investor.vanguard.com/investment-products/etfs/profile/vti",
    ),
    (
        "QQQ","Invesco QQQ Trust","Invesco","NASDAQ","US","USD","1999-03-10",
        "Equity","Stocks","Passive Index","Technology","US",
        0,0,0,0,0, 0.0060,"Quarterly","Growth", 0.0020,0.0020,350000.0,
        4,4,4,1,1,1,1, 1,1,
        "Canadian investors face US withholding tax on dividends held outside an RRSP.",
        None,
        "QQQ tracks the 100 largest non-financial NASDAQ companies — essentially a tech-heavy growth fund dominated by Apple, Microsoft, NVIDIA, and Amazon. Higher volatility than the S&P 500 but strong long-term performance.",
        "nasdaq 100 tech technology growth ai apple microsoft nvidia amazon aggressive invesco",
        "https://www.invesco.com/us/financial-products/etfs/product-detail?ticker=QQQ",
    ),
    (
        "AGG","iShares Core U.S. Aggregate Bond ETF","BlackRock","NYSE Arca","US","USD","2003-09-22",
        "Fixed Income","Bonds","Passive Index",None,"US",
        0,0,0,0,0, 0.0370,"Monthly","Income", 0.0003,0.0003,140000.0,
        2,2,1,1,1,2,1, 1,1,
        "Interest income from US bonds held in a TFSA may be subject to withholding tax.",
        None,
        "AGG is the benchmark US bond ETF holding thousands of US government and investment-grade corporate bonds. Pays monthly and serves as the defensive anchor in most US-based balanced portfolios.",
        "us bond aggregate fixed income government corporate conservative safe balanced monthly blackrock ishares",
        "https://www.ishares.com/us/products/239458/",
    ),
    (
        "SCHD","Schwab U.S. Dividend Equity ETF","Charles Schwab","NYSE Arca","US","USD","2011-10-20",
        "Equity","Stocks","Dividend Growth",None,"US",
        0,0,0,0,0, 0.0355,"Quarterly","Income", 0.0006,0.0006,85000.0,
        3,3,3,1,1,1,1, 1,1,
        "US dividends in a Canadian TFSA are subject to 15% withholding tax. Best held in an RRSP.",
        None,
        "SCHD combines solid dividend yield (~3.5%) with strong dividend growth, targeting blue-chip US companies that have grown payouts consistently. A favourite for RRSP income portfolios.",
        "dividend growth income us equity quality schwab blue chip value income rrsp retiree",
        "https://www.schwab.com/etfs/schwab-us-dividend-equity-etf",
    ),
    (
        "JEPI","JPMorgan Equity Premium Income ETF","JPMorgan","NYSE Arca","US","USD","2020-05-20",
        "Equity","Stocks","Covered Call",None,"US",
        1,0,0,0,0, 0.0720,"Monthly","Income", 0.0035,0.0035,50000.0,
        3,3,2,1,1,1,1, 1,1,
        "US distributions in a Canadian TFSA face 15% withholding tax. Use RRSP if possible.",
        "A portion of JEPI's monthly distributions may be classified as Return of Capital in some periods.",
        "JEPI targets monthly income around 7% by holding large-cap US stocks and selling equity-linked notes. You get income but sacrifice some upside when the market rallies sharply.",
        "covered call high yield monthly income us equity premium jpmorgan defensive low volatility",
        "https://am.jpmorgan.com/us/en/asset-management/adv/products/jpmorgan-equity-premium-income-etf-46641q332",
    ),
    (
        "SPY","SPDR S&P 500 ETF Trust","State Street","NYSE Arca","US","USD","1993-01-22",
        "Equity","Stocks","Passive Index",None,"US",
        0,0,0,0,0, 0.0128,"Quarterly","Growth", 0.000945,0.000945,800000.0,
        4,4,3,1,1,1,1, 1,1,
        "Canadian investors face US withholding tax on dividends held outside an RRSP.",
        None,
        "SPY was the world's first ETF, launched in 1993. It tracks the S&P 500 identically to VOO but charges slightly more. The most traded ETF on earth — massive liquidity makes it the top choice for active traders.",
        "sp500 s&p 500 first etf most traded liquid us equity state street spdr large cap",
        "https://www.ssga.com/us/en/institutional/etfs/funds/spdr-sp-500-etf-trust-spy",
    ),
    (
        "BND","Vanguard Total Bond Market ETF","Vanguard","NYSE Arca","US","USD","2007-04-03",
        "Fixed Income","Bonds","Passive Index",None,"US",
        0,0,0,0,0, 0.0358,"Monthly","Income", 0.0003,0.0003,145000.0,
        2,2,1,1,1,2,1, 1,1,
        "Interest income from US bonds held in a Canadian TFSA may be subject to withholding tax.",
        None,
        "BND covers the entire US investment-grade bond market — over 10,000 bonds — at 0.03% MER. The US-dollar equivalent of ZAG for Canadians investing in USD accounts. Pays monthly.",
        "total bond market us fixed income conservative safe government vanguard cheapest monthly",
        "https://investor.vanguard.com/investment-products/etfs/profile/bnd",
    ),
    (
        "QYLD","Global X NASDAQ 100 Covered Call ETF","Global X","NASDAQ","US","USD","2013-12-12",
        "Equity","Stocks","Covered Call","Technology","US",
        1,0,0,0,0, 0.1180,"Monthly","Income", 0.0060,0.0060,8500.0,
        3,3,4,1,1,1,1, 1,1,
        "US distributions in a Canadian TFSA face 15% withholding tax.",
        "A significant portion of QYLD distributions is Return of Capital. The NAV has declined over time — you are partly receiving your own money back.",
        "QYLD sells covered calls on the NASDAQ-100 to generate ~12% monthly yield. During tech bull markets you miss all the gains, and the NAV has slowly eroded. A large chunk of the payout is Return of Capital.",
        "covered call high yield monthly income nasdaq tech 12 percent yield roc capital erosion global x",
        "https://www.globalxetfs.com/funds/qyld/",
    ),
]

HOLDINGS = {
    "VFV":  [("AAPL","Apple Inc.",0.071,"Equity","US"),("MSFT","Microsoft Corp.",0.065,"Equity","US"),("NVDA","NVIDIA Corp.",0.060,"Equity","US"),("AMZN","Amazon.com Inc.",0.036,"Equity","US"),("META","Meta Platforms Inc.",0.025,"Equity","US")],
    "XEQT": [("VTI","Vanguard Total Stock Mkt",0.450,"ETF","US"),("XEF","iShares MSCI EAFE",0.240,"ETF","International"),("XIC","iShares Core S&P/TSX",0.250,"ETF","CA"),("XEB","iShares Core EM",0.060,"ETF","EM")],
    "VEQT": [("VUN","Vanguard US Total Mkt",0.420,"ETF","US"),("VCN","Vanguard FTSE Canada",0.300,"ETF","CA"),("VIU","Vanguard Intl Equity",0.220,"ETF","International"),("VEE","Vanguard EM",0.060,"ETF","EM")],
    "CASH": [("TD_CASH","TD High-Interest Account",0.350,"Cash","CA"),("BNS_CASH","Scotiabank Deposit",0.250,"Cash","CA"),("CIBC_CASH","CIBC Deposit",0.250,"Cash","CA"),("BMO_CASH","BMO Deposit",0.150,"Cash","CA")],
    "ZAG":  [("CAN_GOV","Canada Govt Bonds",0.480,"Bond","CA"),("PROV","Provincial Bonds",0.280,"Bond","CA"),("CORP","Corporate Bonds",0.240,"Bond","CA")],
    "XIU":  [("RY","Royal Bank of Canada",0.115,"Equity","CA"),("TD","Toronto-Dominion Bank",0.108,"Equity","CA"),("ENB","Enbridge Inc.",0.074,"Equity","CA"),("CNR","Canadian National Railway",0.058,"Equity","CA"),("BNS","Bank of Nova Scotia",0.056,"Equity","CA")],
    "XEI":  [("ENB","Enbridge Inc.",0.118,"Equity","CA"),("BCE","BCE Inc.",0.078,"Equity","CA"),("TRP","TC Energy Corp.",0.076,"Equity","CA"),("PPL","Pembina Pipeline",0.067,"Equity","CA"),("RY","Royal Bank of Canada",0.065,"Equity","CA")],
    "HMAX": [("RY","Royal Bank",0.200,"Equity","CA"),("TD","Toronto-Dominion",0.175,"Equity","CA"),("BNS","Bank of Nova Scotia",0.155,"Equity","CA"),("BMO","Bank of Montreal",0.145,"Equity","CA"),("CM","CIBC",0.130,"Equity","CA")],
    "VOO":  [("AAPL","Apple Inc.",0.071,"Equity","US"),("MSFT","Microsoft Corp.",0.065,"Equity","US"),("NVDA","NVIDIA Corp.",0.060,"Equity","US"),("AMZN","Amazon.com Inc.",0.036,"Equity","US"),("META","Meta Platforms",0.025,"Equity","US")],
    "VTI":  [("AAPL","Apple Inc.",0.062,"Equity","US"),("MSFT","Microsoft Corp.",0.057,"Equity","US"),("NVDA","NVIDIA Corp.",0.053,"Equity","US"),("AMZN","Amazon.com Inc.",0.032,"Equity","US"),("META","Meta Platforms",0.022,"Equity","US")],
    "QQQ":  [("AAPL","Apple Inc.",0.091,"Equity","US"),("MSFT","Microsoft Corp.",0.083,"Equity","US"),("NVDA","NVIDIA Corp.",0.082,"Equity","US"),("AMZN","Amazon.com Inc.",0.050,"Equity","US"),("META","Meta Platforms",0.047,"Equity","US")],
    "SCHD": [("AVGO","Broadcom Inc.",0.042,"Equity","US"),("ABBV","AbbVie Inc.",0.041,"Equity","US"),("CSCO","Cisco Systems",0.040,"Equity","US"),("HD","Home Depot",0.039,"Equity","US"),("PFE","Pfizer Inc.",0.038,"Equity","US")],
    "JEPI": [("MSFT","Microsoft Corp.",0.018,"Equity","US"),("AMZN","Amazon.com",0.017,"Equity","US"),("V","Visa Inc.",0.016,"Equity","US"),("MA","Mastercard",0.015,"Equity","US"),("UNH","UnitedHealth Group",0.014,"Equity","US")],
    "SPY":  [("AAPL","Apple Inc.",0.071,"Equity","US"),("MSFT","Microsoft Corp.",0.065,"Equity","US"),("NVDA","NVIDIA Corp.",0.060,"Equity","US"),("AMZN","Amazon.com Inc.",0.036,"Equity","US"),("META","Meta Platforms",0.025,"Equity","US")],
    "QYLD": [("AAPL","Apple Inc.",0.090,"Equity","US"),("MSFT","Microsoft Corp.",0.082,"Equity","US"),("NVDA","NVIDIA Corp.",0.081,"Equity","US"),("AMZN","Amazon.com",0.049,"Equity","US"),("META","Meta Platforms",0.046,"Equity","US")],
}

INSERT_ETF = """
INSERT OR REPLACE INTO etfs (
    ticker, name, provider, exchange, country, currency, inception_date,
    etf_category, asset_class, strategy_type, sector_focus, geographic_exposure,
    is_covered_call, is_leveraged, is_inverse, is_hedged, is_esg,
    distribution_yield, dividend_frequency, growth_or_income,
    mer, management_fee, aum_cad,
    risk_score, risk_asset_class, risk_concentration, risk_leverage, risk_liquidity, risk_credit, risk_currency,
    tfsa_eligible, rrsp_eligible,
    withholding_tax_note, roc_note, ai_summary, search_keywords, data_source_url,
    last_scraped_at, updated_at
) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
"""

INSERT_HOLDING = """
INSERT OR REPLACE INTO etf_holdings
  (etf_id, holding_ticker, holding_name, weight_pct, asset_type, country, as_of_date)
VALUES (?,?,?,?,?,?,?)
"""


async def main():
    client = libsql_client.create_client(
        url=os.environ["TURSO_URL"],
        auth_token=os.environ["TURSO_TOKEN"],
    )

    ok = 0
    for row in ETFS:
        ticker = row[0]
        try:
            await client.execute(INSERT_ETF, list(row) + [NOW, NOW])

            r = await client.execute(
                "SELECT id FROM etfs WHERE ticker = ?", [ticker]
            )
            etf_id = r.rows[0][0]

            for (ht, hn, wp, at, hc) in HOLDINGS.get(ticker, []):
                await client.execute(INSERT_HOLDING, [etf_id, ht, hn, wp, at, hc, AS_OF])

            print(f"  OK  {ticker:<8}  id={etf_id}")
            ok += 1
        except Exception as e:
            print(f"  ERR {ticker:<8}  {e}")

    await client.close()
    print(f"\nDone -- {ok}/{len(ETFS)} ETFs seeded.")

asyncio.run(main())
