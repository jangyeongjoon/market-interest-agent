from typing import List

from .models import MarketRow


def sample_us_rows() -> List[MarketRow]:
    return [
        MarketRow("NVDA", "NVIDIA", "US", "Semiconductors", 142.83, 3.4, 238_000_000, 34_000_000_000, 24_500_000_000),
        MarketRow("AAPL", "Apple", "US", "Technology", 214.12, 1.2, 92_000_000, 19_700_000_000, 15_100_000_000),
        MarketRow("TSLA", "Tesla", "US", "EV", 186.55, 5.8, 104_000_000, 19_400_000_000, 11_200_000_000),
        MarketRow("AMD", "Advanced Micro Devices", "US", "Semiconductors", 164.10, 2.9, 78_000_000, 12_800_000_000, 8_600_000_000),
        MarketRow("PLTR", "Palantir", "US", "AI Software", 28.31, 7.1, 255_000_000, 7_200_000_000, 3_000_000_000),
        MarketRow("MSTR", "MicroStrategy", "US", "Crypto", 1550.20, 6.4, 4_100_000, 6_350_000_000, 3_700_000_000),
        MarketRow("META", "Meta Platforms", "US", "Communication Services", 512.18, 0.9, 11_500_000, 5_890_000_000, 5_400_000_000),
        MarketRow("AVGO", "Broadcom", "US", "Semiconductors", 1810.22, 1.8, 2_950_000, 5_340_000_000, 4_700_000_000),
    ]


def sample_kr_rows() -> List[MarketRow]:
    return [
        MarketRow("005930", "삼성전자", "KR", "반도체", 78_500, 1.7, 24_000_000, 1_884_000_000_000, 1_200_000_000_000),
        MarketRow("000660", "SK하이닉스", "KR", "반도체", 218_000, 4.2, 9_500_000, 2_071_000_000_000, 1_350_000_000_000),
        MarketRow("042660", "한화오션", "KR", "조선", 31_200, 6.5, 18_000_000, 561_600_000_000, 230_000_000_000),
        MarketRow("010120", "LS ELECTRIC", "KR", "전력기기", 192_300, 5.1, 2_100_000, 403_830_000_000, 170_000_000_000),
        MarketRow("196170", "알테오젠", "KR", "바이오", 285_000, 8.3, 1_350_000, 384_750_000_000, 141_000_000_000),
        MarketRow("064350", "현대로템", "KR", "방산", 42_700, 3.9, 7_100_000, 303_170_000_000, 220_000_000_000),
        MarketRow("352820", "하이브", "KR", "엔터", 228_500, -2.2, 1_050_000, 239_925_000_000, 98_000_000_000),
    ]

