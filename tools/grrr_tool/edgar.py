"""Helpers for downloading SEC filing metadata and documents for GRRR."""

from __future__ import annotations

import csv
import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, List, Optional

import requests

from .config import (
    DATA_DIR,
    DEFAULT_CIK,
    FILINGS_DIR,
    SEC_ARCHIVES_URL,
    SEC_BASE_URL,
    SUBMISSIONS_SAMPLE_PATH,
    UserAgent,
    ensure_data_dirs,
)

LOGGER = logging.getLogger(__name__)


@dataclass
class FilingRecord:
    """Structured data describing a single SEC filing."""

    accession_number: str
    cik: str
    form: str
    filing_date: str
    report_date: str
    film_number: str
    items: str
    primary_document: str
    primary_doc_description: str
    url: str

    def to_row(self) -> List[str]:
        return [
            self.accession_number,
            self.cik,
            self.form,
            self.filing_date,
            self.report_date,
            self.film_number,
            self.items,
            self.primary_document,
            self.primary_doc_description,
            self.url,
        ]


def _sec_session(user_agent: Optional[UserAgent] = None) -> requests.Session:
    session = requests.Session()
    ua = user_agent or UserAgent()
    session.headers.update({"User-Agent": ua.as_header(), "Accept-Encoding": "gzip, deflate"})
    return session


def _accession_to_path(accession_number: str, cik: str) -> Path:
    clean_cik = str(int(cik)).zfill(10)
    accession = accession_number.replace("-", "")
    return Path("edgar") / clean_cik / accession


def fetch_recent_filings(
    *,
    cik: str = DEFAULT_CIK,
    limit: int = 200,
    session: Optional[requests.Session] = None,
    user_agent: Optional[UserAgent] = None,
    fallback_path: Optional[Path] = SUBMISSIONS_SAMPLE_PATH,
) -> List[FilingRecord]:
    """Fetch the most recent filings for the provided CIK."""

    ensure_data_dirs()

    sess = session or _sec_session(user_agent)
    submissions_url = f"{SEC_BASE_URL}/submissions/CIK{int(cik):010d}.json"
    LOGGER.info("Fetching submissions: %s", submissions_url)

    try:
        response = sess.get(submissions_url, timeout=30)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        if fallback_path and fallback_path.exists():
            LOGGER.warning(
                "Failed to reach SEC (%s). Using bundled sample data: %s",
                exc,
                fallback_path,
            )
            payload = json.loads(fallback_path.read_text(encoding="utf-8"))
        else:
            raise

    filings = payload.get("filings", {}).get("recent", {})
    rows = []
    total = min(limit, len(filings.get("accessionNumber", [])))
    for idx in range(total):
        accession = filings["accessionNumber"][idx]
        row = FilingRecord(
            accession_number=accession,
            cik=str(int(cik)).zfill(10),
            form=filings.get("form", [""])[idx],
            filing_date=filings.get("filingDate", [""])[idx],
            report_date=filings.get("reportDate", [""])[idx],
            film_number=filings.get("filmNumber", [""])[idx],
            items=filings.get("items", [""])[idx],
            primary_document=filings.get("primaryDocument", [""])[idx],
            primary_doc_description=filings.get("primaryDocDescription", [""])[idx],
            url=f"{SEC_ARCHIVES_URL}/edgar/data/{int(cik)}/{accession.replace('-', '')}/{filings.get('primaryDocument', [''])[idx]}",
        )
        rows.append(row)
    return rows


def write_filings_csv(records: Iterable[FilingRecord], output_path: Path | None = None) -> Path:
    output_path = output_path or DATA_DIR / "grrr_filings.csv"
    ensure_data_dirs()
    fieldnames = [
        "accession_number",
        "cik",
        "form",
        "filing_date",
        "report_date",
        "film_number",
        "items",
        "primary_document",
        "primary_doc_description",
        "url",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(fieldnames)
        for record in records:
            writer.writerow(record.to_row())
    return output_path


def download_filing_documents(
    records: Iterable[FilingRecord],
    *,
    session: Optional[requests.Session] = None,
    user_agent: Optional[UserAgent] = None,
    delay_seconds: float = 0.2,
    max_bytes: int = 25 * 1024 * 1024,
) -> List[Path]:
    """Download filing primary documents to the local data directory."""

    ensure_data_dirs()

    sess = session or _sec_session(user_agent)
    saved_paths: List[Path] = []
    for record in records:
        if not record.primary_document:
            continue
        target_dir = FILINGS_DIR / record.accession_number.replace("-", "")
        target_dir.mkdir(parents=True, exist_ok=True)
        url = record.url
        LOGGER.info("Downloading %s", url)
        response = sess.get(url, timeout=60)
        response.raise_for_status()
        if len(response.content) > max_bytes:
            LOGGER.warning(
                "Skipping %s because it exceeds %s bytes (size=%s)",
                record.primary_document,
                max_bytes,
                len(response.content),
            )
            continue
        local_path = target_dir / record.primary_document
        local_path.write_bytes(response.content)
        saved_paths.append(local_path)
        time.sleep(delay_seconds)
    return saved_paths


def load_cached_filings(path: Path | None = None) -> Iterator[FilingRecord]:
    path = path or DATA_DIR / "grrr_filings.csv"
    if not path.exists():
        return iter(())
    with path.open("r", encoding="utf-8", newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            yield FilingRecord(
                accession_number=row["accession_number"],
                cik=row["cik"],
                form=row["form"],
                filing_date=row["filing_date"],
                report_date=row["report_date"],
                film_number=row["film_number"],
                items=row["items"],
                primary_document=row["primary_document"],
                primary_doc_description=row["primary_doc_description"],
                url=row["url"],
            )


def save_json(records: Iterable[FilingRecord], output_path: Path | None = None) -> Path:
    output_path = output_path or DATA_DIR / "grrr_filings.json"
    ensure_data_dirs()
    with output_path.open("w", encoding="utf-8") as outfile:
        json.dump([record.__dict__ for record in records], outfile, ensure_ascii=False, indent=2)
    return output_path
