"""
Pydantic schemas that Gemini must return.
Strict types prevent "five" instead of 5.0 from reaching Turso.
"""
from pydantic import BaseModel, Field


class ScrapedHolding(BaseModel):
    holding_ticker: str | None = Field(default=None, description="Ticker symbol of the holding, e.g. AAPL. Null if not shown on page.")
    holding_name: str = Field(description="Full company name, e.g. Apple Inc.")
    weight_pct: float = Field(description="Portfolio weight as a decimal, e.g. 0.071 for 7.1%")
    asset_type: str = Field(description="One of: Equity, Bond, ETF, Cash, Other")
    country: str = Field(description="Two-letter country code, e.g. US, CA")


class ScrapedETF(BaseModel):
    distribution_yield: float | None = Field(
        default=None,
        description=(
            "Annual distribution yield as a decimal. "
            "Convert percentage to decimal: 1.23% → 0.0123. "
            "Return null if not found."
        ),
    )
    mer: float | None = Field(
        default=None,
        description=(
            "Management expense ratio as a decimal. "
            "Convert percentage to decimal: 0.09% → 0.0009. "
            "Return null if not found."
        ),
    )
    management_fee: float | None = Field(
        default=None,
        description=(
            "Management fee (before taxes/expenses) as a decimal. "
            "Return null if not found or same as MER."
        ),
    )
    aum_millions: float | None = Field(
        default=None,
        description=(
            "Assets under management expressed in MILLIONS of the fund's native currency. "
            "Examples: $1.4B → 1400.0,  $560M → 560.0,  $1.4T → 1400000.0. "
            "Return null if not found."
        ),
    )
    holdings: list[ScrapedHolding] = Field(
        default_factory=list,
        description=(
            "Top holdings list (up to 10). "
            "Weight must be a decimal fraction (0.071 not 7.1). "
            "Return empty list if holdings table not found."
        ),
    )
