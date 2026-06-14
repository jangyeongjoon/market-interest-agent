from typing import Dict, Iterable, List, Optional

from .models import MarketRow, ValuationMetrics


def collect_valuations(
    rows: Iterable[MarketRow],
    market: str,
    report_date: str,
    sample: bool,
) -> Dict[str, ValuationMetrics]:
    rows = list(rows)
    if sample:
        return sample_valuations(rows)
    if market == "us":
        return collect_us_valuations(rows)
    if market == "kr":
        return collect_kr_valuations(rows, report_date)
    return {}


def collect_us_valuations(rows: Iterable[MarketRow]) -> Dict[str, ValuationMetrics]:
    try:
        import yfinance as yf
    except ImportError:
        return {}

    valuations: Dict[str, ValuationMetrics] = {}
    for row in rows:
        try:
            info = yf.Ticker(row.symbol).get_info()
        except Exception as exc:
            valuations[row.symbol] = ValuationMetrics(
                symbol=row.symbol,
                summary=f"밸류에이션 조회 실패: {type(exc).__name__}",
                source="yfinance",
            )
            continue

        dividend_yield = number_or_none(info.get("dividendYield"))
        if dividend_yield is not None and dividend_yield < 1:
            dividend_yield *= 100
        profit_margin = pct_from_ratio(info.get("profitMargins"))
        roe = pct_from_ratio(info.get("returnOnEquity"))
        metrics = ValuationMetrics(
            symbol=row.symbol,
            market_cap=number_or_none(info.get("marketCap")),
            trailing_pe=number_or_none(info.get("trailingPE")),
            forward_pe=number_or_none(info.get("forwardPE")),
            price_to_book=number_or_none(info.get("priceToBook")),
            ev_to_sales=number_or_none(info.get("enterpriseToRevenue")),
            ev_to_ebitda=number_or_none(info.get("enterpriseToEbitda")),
            eps=number_or_none(info.get("trailingEps")),
            profit_margin_pct=profit_margin,
            roe_pct=roe,
            dividend_yield_pct=dividend_yield,
            target_mean_price=number_or_none(info.get("targetMeanPrice")),
            recommendation=info.get("recommendationKey"),
            source="yfinance",
        )
        valuations[row.symbol] = with_summary(row, metrics)
    return valuations


def collect_kr_valuations(rows: Iterable[MarketRow], report_date: str) -> Dict[str, ValuationMetrics]:
    try:
        from pykrx import stock
    except ImportError:
        return {}

    yyyymmdd = report_date.replace("-", "")
    valuations: Dict[str, ValuationMetrics] = {}
    try:
        fundamentals = stock.get_market_fundamental_by_ticker(yyyymmdd, market="ALL")
    except Exception as exc:
        return {
            row.symbol: ValuationMetrics(
                symbol=row.symbol,
                summary=f"밸류에이션 조회 실패: {type(exc).__name__}",
                source="pykrx",
            )
            for row in rows
        }

    for row in rows:
        if row.symbol not in fundamentals.index:
            valuations[row.symbol] = ValuationMetrics(symbol=row.symbol, source="pykrx")
            continue
        item = fundamentals.loc[row.symbol]
        metrics = ValuationMetrics(
            symbol=row.symbol,
            trailing_pe=number_or_none(item.get("PER")),
            price_to_book=number_or_none(item.get("PBR")),
            eps=number_or_none(item.get("EPS")),
            dividend_yield_pct=number_or_none(item.get("DIV")),
            source="pykrx",
        )
        valuations[row.symbol] = with_summary(row, metrics)
    return valuations


def sample_valuations(rows: List[MarketRow]) -> Dict[str, ValuationMetrics]:
    defaults = {
        "NVDA": ValuationMetrics("NVDA", trailing_pe=48.0, forward_pe=32.0, price_to_book=35.0, ev_to_sales=26.0, profit_margin_pct=55.0, roe_pct=72.0, summary="", source="sample"),
        "AAPL": ValuationMetrics("AAPL", trailing_pe=29.0, forward_pe=25.0, price_to_book=38.0, ev_to_sales=7.5, profit_margin_pct=24.0, roe_pct=150.0, summary="", source="sample"),
        "TSLA": ValuationMetrics("TSLA", trailing_pe=65.0, forward_pe=55.0, price_to_book=9.0, ev_to_sales=6.0, profit_margin_pct=8.0, roe_pct=12.0, summary="", source="sample"),
        "AMD": ValuationMetrics("AMD", trailing_pe=120.0, forward_pe=34.0, price_to_book=4.5, ev_to_sales=8.0, profit_margin_pct=4.0, roe_pct=3.0, summary="", source="sample"),
        "PLTR": ValuationMetrics("PLTR", trailing_pe=90.0, forward_pe=70.0, price_to_book=16.0, ev_to_sales=25.0, profit_margin_pct=18.0, roe_pct=10.0, summary="", source="sample"),
        "005930": ValuationMetrics("005930", trailing_pe=18.0, price_to_book=1.5, eps=4200.0, dividend_yield_pct=1.8, summary="", source="sample"),
        "000660": ValuationMetrics("000660", trailing_pe=24.0, price_to_book=2.2, eps=9100.0, dividend_yield_pct=0.8, summary="", source="sample"),
    }
    return {row.symbol: with_summary(row, defaults.get(row.symbol, ValuationMetrics(row.symbol, source="sample"))) for row in rows}


def with_summary(row: MarketRow, metrics: ValuationMetrics) -> ValuationMetrics:
    summary = summarize_valuation(row, metrics)
    return ValuationMetrics(
        symbol=metrics.symbol,
        market_cap=metrics.market_cap,
        trailing_pe=metrics.trailing_pe,
        forward_pe=metrics.forward_pe,
        price_to_book=metrics.price_to_book,
        ev_to_sales=metrics.ev_to_sales,
        ev_to_ebitda=metrics.ev_to_ebitda,
        eps=metrics.eps,
        profit_margin_pct=metrics.profit_margin_pct,
        roe_pct=metrics.roe_pct,
        dividend_yield_pct=metrics.dividend_yield_pct,
        target_mean_price=metrics.target_mean_price,
        recommendation=metrics.recommendation,
        summary=summary,
        source=metrics.source,
    )


def summarize_valuation(row: MarketRow, metrics: ValuationMetrics) -> str:
    pe = metrics.forward_pe or metrics.trailing_pe
    pb = metrics.price_to_book
    margin = metrics.profit_margin_pct

    if pe is None and pb is None:
        return "핵심 밸류에이션 지표가 부족해 상대평가가 어렵습니다."

    notes: List[str] = []
    if pe is not None:
        if pe >= 45:
            notes.append("PER 기준 성장 기대가 많이 반영된 구간")
        elif pe <= 15 and pe > 0:
            notes.append("PER 기준 저평가 후보")
        else:
            notes.append("PER 기준 중립 구간")
    if pb is not None:
        if pb >= 10:
            notes.append("PBR 부담이 큰 편")
        elif pb <= 2 and pb > 0:
            notes.append("PBR 부담은 낮은 편")
    if margin is not None and margin >= 25:
        notes.append("수익성은 높은 편")
    elif margin is not None and margin <= 5:
        notes.append("수익성 확인 필요")

    if row.change_pct > 0 and pe is not None and pe >= 45:
        notes.append("상승 추격 전 실적 성장 확인 필요")
    elif row.change_pct < 0 and pe is not None and pe <= 15 and pe > 0:
        notes.append("하락 시 저가 매수 후보로 재점검 가능")

    return ", ".join(notes) + "."


def number_or_none(value: object) -> Optional[float]:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number:
        return None
    return number


def pct_from_ratio(value: object) -> Optional[float]:
    number = number_or_none(value)
    if number is None:
        return None
    return number * 100 if abs(number) <= 1 else number
