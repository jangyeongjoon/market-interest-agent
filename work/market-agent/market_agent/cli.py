import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .config import default_config_path, load_config, project_root
from .data_sources import fetch_market_rows, top_by_traded_value
from .models import ReportContext
from .report import generate_report


KST = timezone(timedelta(hours=9))


def default_report_date() -> str:
    return datetime.now(KST).date().isoformat()


def market_label(market: str) -> str:
    return "미국장" if market == "us" else "한국장"


def build_report(args: argparse.Namespace) -> Path:
    config = load_config(args.config)
    top_n = int(config["reports"]["top_n"])
    report_date = args.date or default_report_date()
    rows = fetch_market_rows(args.market, report_date, config, args.sample)
    top_rows = top_by_traded_value(rows, top_n)
    context = ReportContext(
        market=args.market,
        market_label=market_label(args.market),
        report_date=report_date,
        top_n=top_n,
        sample=args.sample,
    )
    report = generate_report(context, top_rows)

    output_root = project_root() / config["reports"]["output_dir"] / args.market
    output_root.mkdir(parents=True, exist_ok=True)
    output_path = output_root / f"{report_date}.md"
    output_path.write_text(report, encoding="utf-8")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate market interest reports.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    report_parser = subparsers.add_parser("report", help="Generate a market report.")
    report_parser.add_argument("--market", choices=["us", "kr"], required=True)
    report_parser.add_argument("--date", help="Report date in YYYY-MM-DD format.")
    report_parser.add_argument("--sample", action="store_true", help="Use built-in sample data.")
    report_parser.add_argument("--config", type=Path, default=default_config_path())

    args = parser.parse_args()
    if args.command == "report":
        output_path = build_report(args)
        print(output_path)


if __name__ == "__main__":
    main()

