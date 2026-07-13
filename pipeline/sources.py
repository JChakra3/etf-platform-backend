"""
Registry of scrape sources for every ETF.
Uses Yahoo Finance ETF pages — publicly accessible, no bot blocking.
"""

ETF_SOURCES: dict[str, dict] = {
    "VFV":  {"url": "https://finance.yahoo.com/quote/VFV.TO/",          "aum_currency": "CAD"},
    "XEQT": {"url": "https://finance.yahoo.com/quote/XEQT.TO/",         "aum_currency": "CAD"},
    "VEQT": {"url": "https://finance.yahoo.com/quote/VEQT.TO/",         "aum_currency": "CAD"},
    "CASH": {"url": "https://finance.yahoo.com/quote/CASH.TO/",          "aum_currency": "CAD"},
    "ZAG":  {"url": "https://finance.yahoo.com/quote/ZAG.TO/",          "aum_currency": "CAD"},
    "XBB":  {"url": "https://finance.yahoo.com/quote/XBB.TO/",          "aum_currency": "CAD"},
    "XIU":  {"url": "https://finance.yahoo.com/quote/XIU.TO/",          "aum_currency": "CAD"},
    "XEI":  {"url": "https://finance.yahoo.com/quote/XEI.TO/",          "aum_currency": "CAD"},
    "HMAX": {"url": "https://finance.yahoo.com/quote/HMAX.TO/",         "aum_currency": "CAD"},
    "ZSP":  {"url": "https://finance.yahoo.com/quote/ZSP.TO/",          "aum_currency": "CAD"},
    "VOO":  {"url": "https://finance.yahoo.com/quote/VOO/",             "aum_currency": "USD"},
    "VTI":  {"url": "https://finance.yahoo.com/quote/VTI/",             "aum_currency": "USD"},
    "QQQ":  {"url": "https://finance.yahoo.com/quote/QQQ/",             "aum_currency": "USD"},
    "AGG":  {"url": "https://finance.yahoo.com/quote/AGG/",             "aum_currency": "USD"},
    "SCHD": {"url": "https://finance.yahoo.com/quote/SCHD/",            "aum_currency": "USD"},
    "JEPI": {"url": "https://finance.yahoo.com/quote/JEPI/",            "aum_currency": "USD"},
    "SPY":  {"url": "https://finance.yahoo.com/quote/SPY/",             "aum_currency": "USD"},
    "BND":  {"url": "https://finance.yahoo.com/quote/BND/",             "aum_currency": "USD"},
    "QYLD": {"url": "https://finance.yahoo.com/quote/QYLD/",            "aum_currency": "USD"},
}
