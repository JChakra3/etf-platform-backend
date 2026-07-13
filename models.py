from pydantic import BaseModel, Field
from typing import Optional


class ETFSummary(BaseModel):
    id: int
    ticker: str
    name: str
    provider: str
    country: str
    currency: str
    etf_category: str
    asset_class: str
    strategy_type: str
    sector_focus: Optional[str] = None
    geographic_exposure: str
    is_covered_call: bool
    is_leveraged: bool
    is_inverse: bool
    is_hedged: bool
    distribution_yield: Optional[float] = None
    dividend_frequency: Optional[str] = None
    growth_or_income: Optional[str] = None
    mer: Optional[float] = None
    aum_cad: Optional[float] = None
    risk_score: Optional[int] = None


class ETFHolding(BaseModel):
    holding_ticker: str
    holding_name: str
    weight_pct: float
    asset_type: Optional[str] = None
    country: Optional[str] = None
    as_of_date: str


class ETFDetail(ETFSummary):
    exchange: str
    inception_date: Optional[str] = None
    management_fee: Optional[float] = None
    is_esg: bool = False
    tfsa_eligible: bool = True
    rrsp_eligible: bool = True
    withholding_tax_note: Optional[str] = None
    roc_note: Optional[str] = None
    ai_summary: Optional[str] = None
    risk_asset_class: Optional[int] = None
    risk_concentration: Optional[int] = None
    risk_leverage: Optional[int] = None
    risk_liquidity: Optional[int] = None
    risk_credit: Optional[int] = None
    risk_currency: Optional[int] = None
    last_scraped_at: str
    holdings: list[ETFHolding] = []


class SearchResponse(BaseModel):
    results: list[ETFSummary]
    total: int
    page: int
    page_size: int
