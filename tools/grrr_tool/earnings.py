"""Extract earnings call metadata from SEC filings and IR sources."""

from __future__ import annotations

import csv
import json
import logging
import re
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional

import requests
from bs4 import BeautifulSoup

from .config import (
    DATA_DIR,
    DEFAULT_CIK,
    DOCUMENT_SAMPLES_DIR,
    EARNINGS_DIR,
    FILING_INDEX_SAMPLES_DIR,
    SEC_ARCHIVES_URL,
    UserAgent,
    ensure_data_dirs,
)
from .edgar import FilingRecord

LOGGER = logging.getLogger(__name__)

DATE_PATTERNS = [
    re.compile(
        r"(?P<month>January|February|March|April|May|June|July|August|September|October|November|December)\s+"
        r"(?P<day>\d{1,2}),\s+(?P<year>20\d{2})",
        re.IGNORECASE,
    ),
]
TIME_PATTERNS = [
    re.compile(
        r"(?P<hour>\d{1,2}):(?P<minute>\d{2})\s*(?P<ampm>a\.m\.|p\.m\.|AM|PM)",
        re.IGNORECASE,
    ),
]


@dataclass
class EarningsCall:
    accession_number: str
    cik: str
    filing_date: str
    form: str
    source_url: str
    call_datetime: Optional[str]
    timezone: Optional[str]
    notes: str

    def to_row(self) -> List[str]:
        return [
            self.accession_number,
            self.cik,
            self.filing_date,
            self.form,
            self.source_url,
            self.call_datetime or "",
            self.timezone or "",
            self.notes,
        ]


MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


def _sec_session(user_agent: Optional[UserAgent] = None) -> requests.Session:
    session = requests.Session()
    ua = user_agent or UserAgent()
    session.headers.update({"User-Agent": ua.as_header(), "Accept-Encoding": "gzip, deflate"})
    return session


def _filing_index_url(cik: str, accession_number: str) -> str:
    accession = accession_number.replace("-", "")
    return f"{SEC_ARCHIVES_URL}/edgar/data/{int(cik)}/{accession}/index.json"


def _extract_text_from_html(content: bytes) -> str:
    soup = BeautifulSoup(content, "html.parser")
    text = soup.get_text(separator="\n")
    return re.sub(r"\n{2,}", "\n", text)


def _parse_datetime(text: str) -> tuple[Optional[str], Optional[str], str]:
    call_datetime: Optional[str] = None
    timezone: Optional[str] = None
    notes: List[str] = []

    lower_text = text.lower()
    if "conference call" not in lower_text and "earnings call" not in lower_text:
        return call_datetime, timezone, ""

    for pattern in DATE_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        month = MONTHS[match.group("month").lower()]
        day = int(match.group("day"))
        year = int(match.group("year"))
        date_obj = datetime(year, month, day)
        call_datetime = date_obj.strftime("%Y-%m-%d")
        notes.append(f"Date: {date_obj.strftime('%B %d, %Y')}")
        break

    for pattern in TIME_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        hour = int(match.group("hour"))
        minute = int(match.group("minute"))
        ampm = match.group("ampm").lower()
        if ampm.startswith("p") and hour < 12:
            hour += 12
        if ampm.startswith("a") and hour == 12:
            hour = 0
        time_obj = f"{hour:02d}:{minute:02d}"
        if call_datetime:
            call_datetime = f"{call_datetime}T{time_obj}"
        else:
            call_datetime = time_obj
        notes.append(f"Time: {match.group(0)}")
        break

    timezone_match = re.search(r"(Eastern|ET|BST|GMT\+8|HKT)", text)
    if timezone_match:
        timezone = timezone_match.group(0)
        notes.append(f"Timezone: {timezone}")

    summary = " | ".join(notes)
    return call_datetime, timezone, summary


def extract_earnings_calls(
    filings: Iterable[FilingRecord],
    *,
    session: Optional[requests.Session] = None,
    user_agent: Optional[UserAgent] = None,
    limit: Optional[int] = None,
    delay_seconds: float = 0.2,
) -> List[EarningsCall]:
    ensure_data_dirs()
    sess = session or _sec_session(user_agent)
    calls: List[EarningsCall] = []

    for idx, filing in enumerate(filings):
        if limit is not None and idx >= limit:
            break
        if filing.form not in {"6-K", "20-F"}:
            continue

        index_url = _filing_index_url(filing.cik, filing.accession_number)
        index_fallback = (
            FILING_INDEX_SAMPLES_DIR / f"{filing.accession_number.replace('-', '')}.json"
        )
        LOGGER.info("Inspecting %s", index_url)
        try:
            response = sess.get(index_url, timeout=30)
            response.raise_for_status()
            index_payload = response.json()
        except requests.RequestException as exc:
            if index_fallback.exists():
                LOGGER.warning(
                    "Unable to fetch %s (%s). Using bundled sample index %s",
                    index_url,
                    exc,
                    index_fallback,
                )
                index_payload = json.loads(index_fallback.read_text(encoding="utf-8"))
            else:
                LOGGER.warning("Unable to fetch %s (%s)", index_url, exc)
                continue
        directory = index_payload.get("directory", {})
        items = directory.get("item", [])
        found = False

        for item in items:
            name = item.get("name", "")
            if not name.lower().endswith((".htm", ".html", ".txt")):
                continue
            document_url = f"{SEC_ARCHIVES_URL}/edgar/data/{int(filing.cik)}/{filing.accession_number.replace('-', '')}/{name}"
            LOGGER.debug("Downloading potential earnings call document %s", document_url)
            document_fallback = DOCUMENT_SAMPLES_DIR / name
            try:
                doc_resp = sess.get(document_url, timeout=30)
                doc_resp.raise_for_status()
                content = doc_resp.content
            except requests.RequestException as exc:
                if document_fallback.exists():
                    LOGGER.debug(
                        "Using bundled sample document %s for %s due to error: %s",
                        document_fallback,
                        document_url,
                        exc,
                    )
                    content = document_fallback.read_bytes()
                else:
                    LOGGER.debug("Skipping %s due to error: %s", document_url, exc)
                    continue
            text = _extract_text_from_html(content)
            call_datetime, timezone, notes = _parse_datetime(text)
            if call_datetime or "conference call" in text.lower():
                calls.append(
                    EarningsCall(
                        accession_number=filing.accession_number,
                        cik=filing.cik,
                        filing_date=filing.filing_date,
                        form=filing.form,
                        source_url=document_url,
                        call_datetime=call_datetime,
                        timezone=timezone,
                        notes=notes or "Conference call mentioned",
                    )
                )
                found = True
                break
            time.sleep(delay_seconds)
        if not found:
            LOGGER.debug("No conference call mention found for %s", filing.accession_number)
        time.sleep(delay_seconds)
    return calls


def write_calls_csv(calls: Iterable[EarningsCall], output_path: Path | None = None) -> Path:
    output_path = output_path or DATA_DIR / "grrr_earnings_calls.csv"
    ensure_data_dirs()
    with output_path.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(
            [
                "accession_number",
                "cik",
                "filing_date",
                "form",
                "source_url",
                "call_datetime",
                "timezone",
                "notes",
            ]
        )
        for call in calls:
            writer.writerow(call.to_row())
    return output_path


def save_raw_documents(calls: Iterable[EarningsCall], *, session: Optional[requests.Session] = None, user_agent: Optional[UserAgent] = None) -> List[Path]:
    ensure_data_dirs()
    sess = session or _sec_session(user_agent)
    saved_paths: List[Path] = []
    for call in calls:
        target_dir = EARNINGS_DIR / call.accession_number.replace("-", "")
        target_dir.mkdir(parents=True, exist_ok=True)
        LOGGER.info("Saving raw transcript/press release %s", call.source_url)
        response = sess.get(call.source_url, timeout=60)
        if response.status_code != 200:
            LOGGER.warning("Failed to download %s (status=%s)", call.source_url, response.status_code)
            continue
        suffix = Path(call.source_url).suffix or ".html"
        local_path = target_dir / f"raw{suffix}"
        local_path.write_bytes(response.content)
        saved_paths.append(local_path)
    return saved_paths
