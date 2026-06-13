from typing import List, Tuple

from .models import MarketRow


def attention_score(row: MarketRow, rank: int, total: int) -> float:
    rank_score = max(0.0, 100.0 * (1.0 - ((rank - 1) / max(total, 1))))
    value_change = row.traded_value_change_pct
    value_change_score = min(max(value_change or 0.0, 0.0), 200.0) / 2.0
    price_score = min(max(row.change_pct, -20.0), 20.0) + 20.0
    return (rank_score * 0.50) + (value_change_score * 0.35) + (price_score * 0.15)


def ranked_with_scores(rows: List[MarketRow]) -> List[Tuple[int, MarketRow, float]]:
    total = len(rows)
    return [(index, row, attention_score(row, index, total)) for index, row in enumerate(rows, start=1)]

