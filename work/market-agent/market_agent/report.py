from collections import defaultdict
from typing import Dict, Iterable, List, Optional, Tuple

from .models import MarketRow, NewsInterpretation, ReportContext
from .news import summarize_market_news
from .scoring import ranked_with_scores


def format_money(value: float, market: str) -> str:
    if market == "us":
        if value >= 1_000_000_000:
            return f"${value / 1_000_000_000:,.1f}B"
        return f"${value / 1_000_000:,.1f}M"
    if value >= 1_000_000_000_000:
        return f"{value / 1_000_000_000_000:,.2f}조원"
    return f"{value / 100_000_000:,.0f}억원"


def format_pct(value: float) -> str:
    return f"{value:+.2f}%"


def sector_summary(rows: Iterable[MarketRow], market: str) -> List[Tuple[str, int, float, float]]:
    grouped: Dict[str, List[MarketRow]] = defaultdict(list)
    for row in rows:
        grouped[row.sector].append(row)

    summary = []
    for sector, items in grouped.items():
        total_value = sum(item.traded_value for item in items)
        avg_change = sum(item.change_pct for item in items) / len(items)
        summary.append((sector, len(items), total_value, avg_change))
    return sorted(summary, key=lambda item: item[2], reverse=True)


def generate_report(
    context: ReportContext,
    rows: List[MarketRow],
    news_interpretations: Optional[Dict[str, NewsInterpretation]] = None,
) -> str:
    ranked = ranked_with_scores(rows)
    source_label = "샘플 데이터" if context.sample else "무료 API 데이터"

    lines = [
        f"# {context.market_label} 시장 관심 리포트",
        "",
        f"- 기준일: {context.report_date}",
        f"- 데이터: {source_label}",
        f"- 목적: 투자 아이디어 발굴",
        f"- 선별 기준: 거래대금 상위 {context.top_n}개",
        f"- 뉴스 해석: {'포함' if context.with_news else '미포함'}",
        "",
        "## 1. 시장 관심 요약",
        "",
    ]

    if not rows:
        lines += [
            "데이터가 없습니다. 휴장일이거나 데이터 소스에서 값을 받지 못했을 수 있습니다.",
            "",
        ]
        return "\n".join(lines)

    sectors = sector_summary(rows, context.market)
    top_sectors = sectors[:5]
    lines.append("오늘 거래대금이 집중된 섹터는 다음과 같습니다.")
    lines.append("")
    for sector, count, total_value, avg_change in top_sectors:
        lines.append(
            f"- {sector}: {count}개 종목, 거래대금 {format_money(total_value, context.market)}, 평균 등락률 {format_pct(avg_change)}"
        )

    lines += [
        "",
        "## 2. 거래대금 상위 종목",
        "",
        "| 순위 | 종목 | 섹터 | 등락률 | 거래대금 | 거래대금 변화 | 관심도 |",
        "|---:|---|---|---:|---:|---:|---:|",
    ]

    for rank, row, score in ranked:
        value_change = row.traded_value_change_pct
        value_change_text = "-" if value_change is None else format_pct(value_change)
        lines.append(
            f"| {rank} | {row.name} ({row.symbol}) | {row.sector} | {format_pct(row.change_pct)} | "
            f"{format_money(row.traded_value, context.market)} | {value_change_text} | {score:.1f} |"
        )

    lines += [
        "",
        "## 3. 투자 아이디어 후보",
        "",
    ]

    for rank, row, score in ranked[:10]:
        reason_parts = [
            f"거래대금 {rank}위",
            f"등락률 {format_pct(row.change_pct)}",
        ]
        value_change = row.traded_value_change_pct
        if value_change is not None:
            reason_parts.append(f"거래대금 변화 {format_pct(value_change)}")
        lines.append(f"- {row.name} ({row.symbol}): {', '.join(reason_parts)}")

    if context.with_news:
        lines += [
            "",
            "## 4. 포함 뉴스 전체 요약",
            "",
        ]
        interpretations = news_interpretations or {}
        for bullet in summarize_market_news([row for _rank, row, _score in ranked[:10]], interpretations):
            lines.append(f"- {bullet}")

        lines += [
            "",
            "## 5. 종목별 뉴스 요약 및 상승/하락 해석",
            "",
        ]
        for rank, row, score in ranked[:10]:
            interpretation = interpretations.get(row.symbol)
            if interpretation is None:
                lines.append(f"### {row.name} ({row.symbol})")
                lines.append("")
                lines.append("- 뉴스 요약: 뉴스가 수집되지 않았습니다.")
                lines.append("- 가격 해석: 뉴스가 수집되지 않았습니다.")
                lines.append("- 신뢰도: 낮음")
                lines.append("")
                continue
            lines.append(f"### {row.name} ({row.symbol})")
            lines.append("")
            lines.append(f"- 등락률: {format_pct(row.change_pct)}")
            lines.append(f"- 방향: {interpretation.direction}")
            lines.append(f"- 뉴스 요약: {interpretation.headline_summary}")
            lines.append(f"- 가격 해석: {interpretation.summary}")
            lines.append(f"- 신뢰도: {interpretation.confidence}")
            lines.append("- 포함 뉴스:")
            for item in interpretation.items[:3]:
                if item.link:
                    lines.append(f"  - [{item.title}]({item.link}) - {item.source}")
                else:
                    lines.append(f"  - {item.title} - {item.source}")
            lines.append("")

    lines += [
        "",
        f"## {6 if context.with_news else 4}. 다음 체크 포인트",
        "",
        "- 거래대금 상위 종목이 같은 섹터에 반복적으로 몰리는지 확인합니다.",
        "- 거래대금 증가와 가격 상승이 동시에 나타나는 종목을 우선 관찰합니다.",
        "- 거래대금은 크지만 가격이 약한 종목은 분산/매물 출회 가능성을 따로 점검합니다.",
        "- 뉴스 해석은 원인 확정이 아니라 가능한 촉매 후보로 해석합니다.",
        "- 다음 버전에서 공시, 외국인/기관 수급을 추가하면 아이디어 품질이 올라갑니다.",
        "",
        "_본 리포트는 투자 아이디어 발굴용이며 매수/매도 추천이 아닙니다._",
        "",
    ]

    return "\n".join(lines)
