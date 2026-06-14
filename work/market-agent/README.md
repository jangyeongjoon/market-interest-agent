# Market Interest Agent

Free-first stock market report agent for investment idea discovery.

## Scope

- 07:00 KST: U.S. market report after the U.S. session closes.
- 19:00 KST: Korean market report after the Korean session closes.
- Screening target: top 50 names by traded value.
- First signal: traded value and traded value change.
- Valuation check: PER, forward PER(선행 PER), PBR, EV multiples, margins, ROE, target-price gap when available.
- Output: Korean Markdown report.

## Data Sources

The first implementation is intentionally free-first:

- U.S.: `yfinance`
- Korea: `pykrx`

Valuation metrics are collected from the same free sources. Missing fields are shown as `-` because free data coverage varies by market and ticker.

If those packages are not installed, the CLI can generate a sample report with built-in mock data so the report pipeline can be tested immediately.

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Generate Reports

Sample U.S. report:

```bash
python3 -m market_agent.cli report --market us --date 2026-06-12 --sample
```

Sample Korea report:

```bash
python3 -m market_agent.cli report --market kr --date 2026-06-12 --sample
```

Real data, after installing dependencies:

```bash
python3 -m market_agent.cli report --market us
python3 -m market_agent.cli report --market kr
```

Add news-based interpretation:

```bash
python3 -m market_agent.cli report --market us --with-news
python3 -m market_agent.cli report --market kr --with-news
```

The news interpretation uses Google News RSS. It should be treated as a catalyst hypothesis, not a confirmed reason for price movement.

Reports are written under `reports/us/` and `reports/kr/`. The default configuration is stored in `config/markets.json`.

## Suggested Schedule

Use local cron, launchd, GitHub Actions, or Codex automations later.

```text
0 7 * * 2-6  cd /path/to/market-agent && .venv/bin/python -m market_agent.cli report --market us
0 19 * * 1-5 cd /path/to/market-agent && .venv/bin/python -m market_agent.cli report --market kr
```

The weekday ranges are intentionally approximate. The agent also writes a clear message when no data is available for the requested date.
