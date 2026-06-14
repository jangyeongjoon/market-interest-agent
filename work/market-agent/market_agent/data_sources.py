from datetime import datetime, timedelta
from typing import Dict, Iterable, List

from .models import MarketRow
from .sample_data import sample_kr_rows, sample_us_rows


def fetch_market_rows(market: str, report_date: str, config: Dict, sample: bool) -> List[MarketRow]:
    if sample:
        return sample_us_rows() if market == "us" else sample_kr_rows()
    if market == "us":
        return fetch_us_rows(report_date, config)
    if market == "kr":
        return fetch_kr_rows(report_date, config)
    raise ValueError(f"Unsupported market: {market}")


def fetch_us_rows(report_date: str, config: Dict) -> List[MarketRow]:
    try:
        import yfinance as yf
    except ImportError as exc:
        raise RuntimeError("yfinance is not installed. Run with --sample or install requirements.txt.") from exc

    tickers = config["us"]["universe"]["tickers"]
    sector_map = config["us"].get("sector_map", {})
    date = datetime.strptime(report_date, "%Y-%m-%d").date()
    start = date - timedelta(days=7)
    end = date + timedelta(days=1)
    rows: List[MarketRow] = []

    for ticker in tickers:
        hist = yf.download(ticker, start=start.isoformat(), end=end.isoformat(), progress=False, auto_adjust=False)
        if hist.empty:
            continue
        hist = hist.dropna()
        if hist.empty:
            continue
        current = hist.iloc[-1]
        previous = hist.iloc[-2] if len(hist) > 1 else None
        close = numeric_cell(current, "Close")
        volume = numeric_cell(current, "Volume")
        prev_close = numeric_cell(previous, "Close") if previous is not None else close
        traded_value_prev = (
            numeric_cell(previous, "Close") * numeric_cell(previous, "Volume") if previous is not None else None
        )
        rows.append(
            MarketRow(
                symbol=ticker,
                name=ticker,
                market="US",
                sector=sector_map.get(ticker, "Unknown"),
                close=close,
                change_pct=((close / prev_close) - 1.0) * 100.0 if prev_close else 0.0,
                volume=volume,
                traded_value=close * volume,
                traded_value_prev=traded_value_prev,
            )
        )
    return rows


def fetch_kr_rows(report_date: str, config: Dict) -> List[MarketRow]:
    try:
        from pykrx import stock
    except ImportError as exc:
        raise RuntimeError("pykrx is not installed. Run with --sample or install requirements.txt.") from exc

    yyyymmdd = report_date.replace("-", "")
    rows: List[MarketRow] = []
    for market_name in config["kr"]["market_names"]:
        df = stock.get_market_ohlcv_by_ticker(yyyymmdd, market=market_name)
        if df.empty:
            continue
        for symbol, row in df.iterrows():
            name = stock.get_market_ticker_name(symbol)
            close = float(row["종가"])
            volume = float(row["거래량"])
            traded_value = float(row.get("거래대금", close * volume))
            open_price = float(row["시가"]) if row["시가"] else close
            change_pct = ((close / open_price) - 1.0) * 100.0 if open_price else 0.0
            rows.append(
                MarketRow(
                    symbol=symbol,
                    name=name,
                    market=market_name,
                    sector="미분류",
                    close=close,
                    change_pct=change_pct,
                    volume=volume,
                    traded_value=traded_value,
                )
            )
    return rows


def top_by_traded_value(rows: Iterable[MarketRow], top_n: int) -> List[MarketRow]:
    return sorted(rows, key=lambda row: row.traded_value, reverse=True)[:top_n]


def numeric_cell(row, column: str) -> float:
    value = row[column]
    if hasattr(value, "iloc"):
        value = value.iloc[0]
    return float(value)
