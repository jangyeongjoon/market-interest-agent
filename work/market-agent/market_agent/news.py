from typing import Dict, Iterable, List
from urllib.parse import quote_plus
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from .models import MarketRow, NewsInterpretation, NewsItem


POSITIVE_WORDS = [
    "beat",
    "beats",
    "surge",
    "rally",
    "raises",
    "upgrade",
    "growth",
    "record",
    "deal",
    "launch",
    "wins",
    "buy",
    "strong",
    "outperform",
    "호실적",
    "상승",
    "급등",
    "수주",
    "증가",
    "상향",
]

NEGATIVE_WORDS = [
    "miss",
    "falls",
    "drop",
    "downgrade",
    "probe",
    "lawsuit",
    "recall",
    "weak",
    "sell",
    "risk",
    "cut",
    "slump",
    "하락",
    "급락",
    "부진",
    "소송",
    "리콜",
    "하향",
]


def fetch_google_news(query: str, *, language: str, region: str, limit: int) -> List[NewsItem]:
    encoded = quote_plus(query)
    url = f"https://news.google.com/rss/search?q={encoded}&hl={language}&gl={region}&ceid={region}:{language.split('-')[0]}"
    request = Request(url, headers={"User-Agent": "market-interest-agent/0.1"})
    with urlopen(request, timeout=10) as response:
        payload = response.read()

    root = ElementTree.fromstring(payload)
    items: List[NewsItem] = []
    for item in root.findall("./channel/item")[:limit]:
        title = item.findtext("title", default="").strip()
        link = item.findtext("link", default="").strip()
        published = item.findtext("pubDate", default="").strip()
        source_el = item.find("source")
        source = source_el.text.strip() if source_el is not None and source_el.text else "Google News"
        if title:
            items.append(NewsItem(title=title, source=source, link=link, published=published))
    return items


def collect_news(rows: Iterable[MarketRow], market: str, limit_per_symbol: int) -> Dict[str, List[NewsItem]]:
    language = "ko-KR" if market == "kr" else "en-US"
    region = "KR" if market == "kr" else "US"
    result: Dict[str, List[NewsItem]] = {}
    for row in rows:
        query = build_query(row, market)
        try:
            result[row.symbol] = fetch_google_news(query, language=language, region=region, limit=limit_per_symbol)
        except Exception as exc:
            result[row.symbol] = [
                NewsItem(
                    title=f"뉴스 조회 실패: {type(exc).__name__}",
                    source="system",
                    link="",
                )
            ]
    return result


def build_query(row: MarketRow, market: str) -> str:
    if market == "kr":
        return f'"{row.name}" 주식 OR "{row.name}" 증시'
    return f'"{row.name}" OR {row.symbol} stock'


def interpret_news(row: MarketRow, items: List[NewsItem]) -> NewsInterpretation:
    usable_items = [item for item in items if item.source != "system"]
    system_error = next((item.title for item in items if item.source == "system"), None)
    direction = "상승" if row.change_pct > 0 else "하락" if row.change_pct < 0 else "보합"

    if not usable_items:
        reason = system_error or "관련 뉴스가 충분히 수집되지 않았습니다."
        return NewsInterpretation(
            symbol=row.symbol,
            direction=direction,
            summary=f"{reason} 가격 움직임은 뉴스보다 수급/기술적 요인일 가능성도 함께 봐야 합니다.",
            confidence="낮음",
            items=items,
        )

    titles = " ".join(item.title.lower() for item in usable_items)
    positive_hits = [word for word in POSITIVE_WORDS if word.lower() in titles]
    negative_hits = [word for word in NEGATIVE_WORDS if word.lower() in titles]
    top_title = usable_items[0].title

    if row.change_pct > 0 and positive_hits:
        summary = f"주가 상승과 함께 긍정 키워드({', '.join(positive_hits[:3])})가 포함된 뉴스가 확인됩니다. 대표 뉴스는 '{top_title}'입니다."
        confidence = "중간"
    elif row.change_pct < 0 and negative_hits:
        summary = f"주가 하락과 함께 부정 키워드({', '.join(negative_hits[:3])})가 포함된 뉴스가 확인됩니다. 대표 뉴스는 '{top_title}'입니다."
        confidence = "중간"
    elif row.change_pct > 0:
        summary = f"주가는 상승했지만 뉴스 제목만으로 직접적인 긍정 촉매는 강하게 확인되지 않습니다. 대표 뉴스는 '{top_title}'입니다."
        confidence = "낮음"
    elif row.change_pct < 0:
        summary = f"주가는 하락했지만 뉴스 제목만으로 직접적인 부정 촉매는 강하게 확인되지 않습니다. 대표 뉴스는 '{top_title}'입니다."
        confidence = "낮음"
    else:
        summary = f"가격은 보합권이며 뉴스는 관심 배경 확인용으로 보는 것이 적절합니다. 대표 뉴스는 '{top_title}'입니다."
        confidence = "낮음"

    return NewsInterpretation(
        symbol=row.symbol,
        direction=direction,
        summary=summary,
        confidence=confidence,
        items=usable_items,
    )


def interpret_all(rows: Iterable[MarketRow], news_by_symbol: Dict[str, List[NewsItem]]) -> Dict[str, NewsInterpretation]:
    return {row.symbol: interpret_news(row, news_by_symbol.get(row.symbol, [])) for row in rows}
