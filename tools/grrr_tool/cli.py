"""Command-line interface for GRRR data collection."""

from __future__ import annotations

import argparse
import logging
from typing import Optional

import requests

from .config import DEFAULT_CIK, UserAgent
from .edgar import download_filing_documents, fetch_recent_filings, save_json, write_filings_csv
from .earnings import extract_earnings_calls, save_raw_documents, write_calls_csv


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Collect SEC filings and earnings call data for GRRR.")
    parser.add_argument("--cik", default=DEFAULT_CIK, help="CIK to process (default: %(default)s)")
    parser.add_argument("--limit", type=int, default=100, help="Maximum number of filings to inspect")
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download primary documents for filings that mention conference calls.",
    )
    parser.add_argument(
        "--save-json",
        action="store_true",
        help="Also export filing metadata as JSON",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging verbosity",
    )
    parser.add_argument(
        "--user-agent",
        default=None,
        help="Override the SEC user agent header (format: 'Name email@example.com')",
    )
    return parser


def parse_user_agent(value: Optional[str]) -> Optional[UserAgent]:
    if not value:
        return None
    parts = value.split()
    if len(parts) < 2:
        raise ValueError("User agent must include a contact email.")
    return UserAgent(name=" ".join(parts[:-1]), email=parts[-1])


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(level=getattr(logging, args.log_level), format="%(levelname)s %(name)s: %(message)s")
    user_agent = parse_user_agent(args.user_agent)

    try:
        filings = fetch_recent_filings(cik=args.cik, limit=args.limit, user_agent=user_agent)
    except requests.RequestException as exc:  # pragma: no cover - network failure paths
        logging.error("Failed to fetch filings: %s", exc)
        return 2
    write_filings_csv(filings)
    if args.save_json:
        save_json(filings)

    try:
        earnings_calls = extract_earnings_calls(filings, user_agent=user_agent, limit=args.limit)
    except requests.RequestException as exc:  # pragma: no cover - network failure paths
        logging.error("Failed to extract earnings call data: %s", exc)
        earnings_calls = []
    write_calls_csv(earnings_calls)

    if args.download:
        download_filing_documents(filings, user_agent=user_agent)
        save_raw_documents(earnings_calls, user_agent=user_agent)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
