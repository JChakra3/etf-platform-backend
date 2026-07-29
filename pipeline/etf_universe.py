"""
Static ETF universe — used as fallback when Yahoo screener is unavailable.
Covers major Canadian and US ETFs across all asset classes.
"""

ETF_UNIVERSE = [
    # ── US Broad Market ──────────────────────────────────────────────────────
    {"ticker": "VTI",  "currency": "USD", "country": "US"},
    {"ticker": "VOO",  "currency": "USD", "country": "US"},
    {"ticker": "SPY",  "currency": "USD", "country": "US"},
    {"ticker": "IVV",  "currency": "USD", "country": "US"},
    {"ticker": "QQQ",  "currency": "USD", "country": "US"},
    {"ticker": "SCHB", "currency": "USD", "country": "US"},
    {"ticker": "ITOT", "currency": "USD", "country": "US"},
    {"ticker": "VXF",  "currency": "USD", "country": "US"},
    {"ticker": "IJH",  "currency": "USD", "country": "US"},
    {"ticker": "IJR",  "currency": "USD", "country": "US"},

    # ── US Dividend / Income ─────────────────────────────────────────────────
    {"ticker": "SCHD", "currency": "USD", "country": "US"},
    {"ticker": "VYM",  "currency": "USD", "country": "US"},
    {"ticker": "DVY",  "currency": "USD", "country": "US"},
    {"ticker": "DGRO", "currency": "USD", "country": "US"},
    {"ticker": "HDV",  "currency": "USD", "country": "US"},
    {"ticker": "NOBL", "currency": "USD", "country": "US"},
    {"ticker": "SDY",  "currency": "USD", "country": "US"},

    # ── US Covered Call / Income ─────────────────────────────────────────────
    {"ticker": "JEPI", "currency": "USD", "country": "US"},
    {"ticker": "JEPQ", "currency": "USD", "country": "US"},
    {"ticker": "QYLD", "currency": "USD", "country": "US"},
    {"ticker": "XYLD", "currency": "USD", "country": "US"},
    {"ticker": "RYLD", "currency": "USD", "country": "US"},
    {"ticker": "DIVO", "currency": "USD", "country": "US"},

    # ── US Bonds ─────────────────────────────────────────────────────────────
    {"ticker": "BND",  "currency": "USD", "country": "US"},
    {"ticker": "AGG",  "currency": "USD", "country": "US"},
    {"ticker": "LQD",  "currency": "USD", "country": "US"},
    {"ticker": "TLT",  "currency": "USD", "country": "US"},
    {"ticker": "SHY",  "currency": "USD", "country": "US"},
    {"ticker": "IEF",  "currency": "USD", "country": "US"},
    {"ticker": "VCIT", "currency": "USD", "country": "US"},
    {"ticker": "VCSH", "currency": "USD", "country": "US"},
    {"ticker": "HYG",  "currency": "USD", "country": "US"},
    {"ticker": "JNK",  "currency": "USD", "country": "US"},
    {"ticker": "BNDX", "currency": "USD", "country": "US"},
    {"ticker": "VGIT", "currency": "USD", "country": "US"},
    {"ticker": "VGLT", "currency": "USD", "country": "US"},
    {"ticker": "BSV",  "currency": "USD", "country": "US"},

    # ── US Sector ────────────────────────────────────────────────────────────
    {"ticker": "XLK",  "currency": "USD", "country": "US"},
    {"ticker": "XLF",  "currency": "USD", "country": "US"},
    {"ticker": "XLV",  "currency": "USD", "country": "US"},
    {"ticker": "XLE",  "currency": "USD", "country": "US"},
    {"ticker": "XLY",  "currency": "USD", "country": "US"},
    {"ticker": "XLP",  "currency": "USD", "country": "US"},
    {"ticker": "XLI",  "currency": "USD", "country": "US"},
    {"ticker": "XLU",  "currency": "USD", "country": "US"},
    {"ticker": "XLB",  "currency": "USD", "country": "US"},
    {"ticker": "XLRE", "currency": "USD", "country": "US"},
    {"ticker": "XLC",  "currency": "USD", "country": "US"},
    {"ticker": "VGT",  "currency": "USD", "country": "US"},
    {"ticker": "VHT",  "currency": "USD", "country": "US"},
    {"ticker": "VDE",  "currency": "USD", "country": "US"},
    {"ticker": "VFH",  "currency": "USD", "country": "US"},
    {"ticker": "VNQ",  "currency": "USD", "country": "US"},
    {"ticker": "ARKK", "currency": "USD", "country": "US"},

    # ── US International / Global ─────────────────────────────────────────────
    {"ticker": "VEA",  "currency": "USD", "country": "US"},
    {"ticker": "VWO",  "currency": "USD", "country": "US"},
    {"ticker": "EFA",  "currency": "USD", "country": "US"},
    {"ticker": "EEM",  "currency": "USD", "country": "US"},
    {"ticker": "IEFA", "currency": "USD", "country": "US"},
    {"ticker": "IEMG", "currency": "USD", "country": "US"},
    {"ticker": "VT",   "currency": "USD", "country": "US"},
    {"ticker": "ACWI", "currency": "USD", "country": "US"},
    {"ticker": "VEU",  "currency": "USD", "country": "US"},

    # ── US Commodities / Gold ─────────────────────────────────────────────────
    {"ticker": "GLD",  "currency": "USD", "country": "US"},
    {"ticker": "IAU",  "currency": "USD", "country": "US"},
    {"ticker": "SLV",  "currency": "USD", "country": "US"},
    {"ticker": "PDBC", "currency": "USD", "country": "US"},
    {"ticker": "DJP",  "currency": "USD", "country": "US"},
    {"ticker": "GSG",  "currency": "USD", "country": "US"},

    # ── US Leveraged ─────────────────────────────────────────────────────────
    {"ticker": "TQQQ", "currency": "USD", "country": "US"},
    {"ticker": "UPRO", "currency": "USD", "country": "US"},
    {"ticker": "SOXL", "currency": "USD", "country": "US"},
    {"ticker": "TECL", "currency": "USD", "country": "US"},
    {"ticker": "SPXL", "currency": "USD", "country": "US"},

    # ── Canadian Broad Market ─────────────────────────────────────────────────
    {"ticker": "XIU",  "currency": "CAD", "country": "CA"},
    {"ticker": "XIC",  "currency": "CAD", "country": "CA"},
    {"ticker": "VCN",  "currency": "CAD", "country": "CA"},
    {"ticker": "ZCN",  "currency": "CAD", "country": "CA"},
    {"ticker": "HXT",  "currency": "CAD", "country": "CA"},

    # ── Canadian All-in-One / Balanced ────────────────────────────────────────
    {"ticker": "XEQT", "currency": "CAD", "country": "CA"},
    {"ticker": "VEQT", "currency": "CAD", "country": "CA"},
    {"ticker": "XGRO", "currency": "CAD", "country": "CA"},
    {"ticker": "VGRO", "currency": "CAD", "country": "CA"},
    {"ticker": "XBAL", "currency": "CAD", "country": "CA"},
    {"ticker": "VBAL", "currency": "CAD", "country": "CA"},
    {"ticker": "XCNS", "currency": "CAD", "country": "CA"},
    {"ticker": "VCONS","currency": "CAD", "country": "CA"},
    {"ticker": "ZGRO", "currency": "CAD", "country": "CA"},
    {"ticker": "ZBAL", "currency": "CAD", "country": "CA"},

    # ── Canadian S&P 500 Exposure ─────────────────────────────────────────────
    {"ticker": "VFV",  "currency": "CAD", "country": "CA"},
    {"ticker": "ZSP",  "currency": "CAD", "country": "CA"},
    {"ticker": "XSP",  "currency": "CAD", "country": "CA"},
    {"ticker": "VSP",  "currency": "CAD", "country": "CA"},
    {"ticker": "HXS",  "currency": "CAD", "country": "CA"},

    # ── Canadian Dividend / Income ─────────────────────────────────────────────
    {"ticker": "XEI",  "currency": "CAD", "country": "CA"},
    {"ticker": "CDZ",  "currency": "CAD", "country": "CA"},
    {"ticker": "XDV",  "currency": "CAD", "country": "CA"},
    {"ticker": "VDY",  "currency": "CAD", "country": "CA"},
    {"ticker": "ZDV",  "currency": "CAD", "country": "CA"},
    {"ticker": "PDC",  "currency": "CAD", "country": "CA"},

    # ── Canadian Covered Call ─────────────────────────────────────────────────
    {"ticker": "HMAX", "currency": "CAD", "country": "CA"},
    {"ticker": "TMAX", "currency": "CAD", "country": "CA"},
    {"ticker": "EMAX", "currency": "CAD", "country": "CA"},
    {"ticker": "UMAX", "currency": "CAD", "country": "CA"},
    {"ticker": "ZWEN", "currency": "CAD", "country": "CA"},
    {"ticker": "ZCPB", "currency": "CAD", "country": "CA"},
    {"ticker": "HYLD", "currency": "CAD", "country": "CA"},
    {"ticker": "HDIV", "currency": "CAD", "country": "CA"},
    {"ticker": "SDIV", "currency": "CAD", "country": "CA"},

    # ── Canadian Bonds ────────────────────────────────────────────────────────
    {"ticker": "ZAG",  "currency": "CAD", "country": "CA"},
    {"ticker": "XBB",  "currency": "CAD", "country": "CA"},
    {"ticker": "VAB",  "currency": "CAD", "country": "CA"},
    {"ticker": "ZSB",  "currency": "CAD", "country": "CA"},
    {"ticker": "XSB",  "currency": "CAD", "country": "CA"},
    {"ticker": "VSB",  "currency": "CAD", "country": "CA"},
    {"ticker": "ZLB",  "currency": "CAD", "country": "CA"},
    {"ticker": "XLB",  "currency": "CAD", "country": "CA"},
    {"ticker": "ZDB",  "currency": "CAD", "country": "CA"},
    {"ticker": "HYI",  "currency": "CAD", "country": "CA"},
    {"ticker": "CASH", "currency": "CAD", "country": "CA"},
    {"ticker": "CSAV", "currency": "CAD", "country": "CA"},
    {"ticker": "HSAV", "currency": "CAD", "country": "CA"},

    # ── Canadian International ────────────────────────────────────────────────
    {"ticker": "XEF",  "currency": "CAD", "country": "CA"},
    {"ticker": "VIU",  "currency": "CAD", "country": "CA"},
    {"ticker": "ZEM",  "currency": "CAD", "country": "CA"},
    {"ticker": "XEC",  "currency": "CAD", "country": "CA"},
    {"ticker": "ZDM",  "currency": "CAD", "country": "CA"},

    # ── Canadian Sector ───────────────────────────────────────────────────────
    {"ticker": "XFN",  "currency": "CAD", "country": "CA"},
    {"ticker": "XIT",  "currency": "CAD", "country": "CA"},
    {"ticker": "XRE",  "currency": "CAD", "country": "CA"},
    {"ticker": "XEG",  "currency": "CAD", "country": "CA"},
    {"ticker": "ZEB",  "currency": "CAD", "country": "CA"},
    {"ticker": "ZUT",  "currency": "CAD", "country": "CA"},
    {"ticker": "ZRE",  "currency": "CAD", "country": "CA"},

    # ── Canadian Gold / Commodities ───────────────────────────────────────────
    {"ticker": "CGL",  "currency": "CAD", "country": "CA"},
    {"ticker": "MNT",  "currency": "CAD", "country": "CA"},
    {"ticker": "SVR",  "currency": "CAD", "country": "CA"},
    {"ticker": "HUG",  "currency": "CAD", "country": "CA"},
]
