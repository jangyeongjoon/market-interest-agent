from collections import Counter, defaultdict
from typing import Dict, Iterable, List, Tuple
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

THEME_KEYWORDS = {
    "AI/반도체": ["ai", "nvidia", "chip", "semiconductor", "robotics", "megafab", "fab", "hbm"],
    "실적/밸류에이션": ["earnings", "valuation", "overvalu", "cheap", "target", "rebound", "outlook"],
    "모멘텀/트레이딩": ["rally", "rocketing", "momentum", "trading", "recovers", "falls", "slips"],
    "전기차/로보택시": ["tesla", "robotaxi", "spacex", "elon"],
    "클라우드/플랫폼": ["cloud", "aws", "e-commerce", "microsoft", "alphabet", "google"],
    "리스크/정책": ["risk", "lawsuit", "probe", "recall", "deadline", "disappointment"],
}

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
            headline_summary="뉴스 제목 요약을 만들 수 있는 관련 기사가 충분하지 않습니다.",
            summary=f"{reason} 가격 움직임은 뉴스보다 수급/기술적 요인일 가능성도 함께 봐야 합니다.",
            confidence="낮음",
            items=items,
        )

    clean_titles = [clean_title(item.title, item.source) for item in usable_items]
    titles = " ".join(title.lower() for title in clean_titles)
    positive_hits = [word for word in POSITIVE_WORDS if word.lower() in titles]
    negative_hits = [word for word in NEGATIVE_WORDS if word.lower() in titles]
    top_title = usable_items[0].title
    headline_summary = summarize_headlines(row, usable_items)

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
        headline_summary=headline_summary,
        summary=summary,
        confidence=confidence,
        items=usable_items,
    )


def interpret_all(rows: Iterable[MarketRow], news_by_symbol: Dict[str, List[NewsItem]]) -> Dict[str, NewsInterpretation]:
    return {row.symbol: interpret_news(row, news_by_symbol.get(row.symbol, [])) for row in rows}


def summarize_headlines(row: MarketRow, items: List[NewsItem]) -> str:
    themes = detect_themes(clean_titles(items))
    theme_text = ", ".join(themes[:3]) if themes else "개별 종목 이슈"
    titles = clean_titles(items[:3])
    joined_titles = " / ".join(titles)
    return (
        f"{row.name} 관련 뉴스는 {theme_text} 중심으로 묶입니다. "
        f"주요 헤드라인은 {joined_titles}입니다."
    )


def summarize_market_news(rows: Iterable[MarketRow], interpretations: Dict[str, NewsInterpretation]) -> List[str]:
    rows = list(rows)
    theme_counter: Counter[str] = Counter()
    direction_by_theme: Dict[str, List[str]] = defaultdict(list)
    high_confidence = []

    for row in rows:
        interpretation = interpretations.get(row.symbol)
        if not interpretation:
            continue
        themes = detect_themes(clean_titles(interpretation.items))
        for theme in themes:
            theme_counter[theme] += 1
            direction_by_theme[theme].append(interpretation.direction)
        if interpretation.confidence != "낮음":
            high_confidence.append(f"{row.name}({row.symbol})")

    bullets: List[str] = []
    for theme, count in theme_counter.most_common(5):
        directions = Counter(direction_by_theme[theme])
        direction_text = ", ".join(f"{name} {value}건" for name, value in directions.most_common())
        bullets.append(f"{theme}: {count}개 종목 뉴스에서 반복 확인됨 ({direction_text}).")

    if high_confidence:
        bullets.append(f"가격 방향과 뉴스 키워드가 비교적 잘 맞는 종목: {', '.join(high_confidence[:8])}.")
    if not bullets:
        bullets.append("공통으로 반복되는 뉴스 테마가 뚜렷하지 않습니다. 개별 종목별 뉴스와 수급을 함께 확인해야 합니다.")

    bullets.append("이 요약은 Google News RSS 제목 기반입니다. 기사 본문, 실적 원문, 공시 확인 전까지는 원인 확정으로 보지 않습니다.")
    return bullets


def clean_title(title: str, source: str) -> str:
    suffix = f" - {source}"
    if title.endswith(suffix):
        return title[: -len(suffix)]
    return title


def clean_titles(items: Iterable[NewsItem]) -> List[str]:
    return [clean_title(item.title, item.source) for item in items]


def detect_themes(titles: Iterable[str]) -> List[str]:
    text = " ".join(titles).lower()
    matches: List[Tuple[str, int]] = []
    for theme, keywords in THEME_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword in text)
        if score:
            matches.append((theme, score))
    matches.sort(key=lambda item: item[1], reverse=True)
    return [theme for theme, _score in matches]
