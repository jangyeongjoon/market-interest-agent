from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class MarketRow:
    symbol: str
    name: str
    market: str
    sector: str
    close: float
    change_pct: float
    volume: float
    traded_value: float
    traded_value_prev: Optional[float] = None

    @property
    def traded_value_change_pct(self) -> Optional[float]:
        if not self.traded_value_prev or self.traded_value_prev <= 0:
            return None
        return (self.traded_value / self.traded_value_prev - 1.0) * 100.0


@dataclass(frozen=True)
class ReportContext:
    market: str
    market_label: str
    report_date: str
    top_n: int
    sample: bool
    with_news: bool = False


@dataclass(frozen=True)
class NewsItem:
    title: str
    source: str
    link: str
    published: str = ""


@dataclass(frozen=True)
class NewsInterpretation:
    symbol: str
    direction: str
    headline_summary: str
    summary: str
    confidence: str
    items: List[NewsItem]
