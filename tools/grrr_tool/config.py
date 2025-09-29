"""Shared configuration constants for the GRRR data collection utilities."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


DEFAULT_CIK = "0001908462"
DEFAULT_TICKER = "GRRR"
SEC_BASE_URL = "https://data.sec.gov"
SEC_ARCHIVES_URL = "https://www.sec.gov/Archives"

PACKAGE_ROOT = Path(__file__).resolve().parent
SAMPLES_DIR = PACKAGE_ROOT / "samples"
FILING_INDEX_SAMPLES_DIR = SAMPLES_DIR / "filing_indexes"
DOCUMENT_SAMPLES_DIR = SAMPLES_DIR / "documents"

DATA_DIR = Path("data")
FILINGS_DIR = DATA_DIR / "filings"
EARNINGS_DIR = DATA_DIR / "earnings_calls"
SUBMISSIONS_SAMPLE_PATH = SAMPLES_DIR / "submissions_grrr.json"


@dataclass(frozen=True)
class UserAgent:
    """User-Agent header values recommended by the SEC."""

    name: str = "Junya"
    email: str = "junya20061227@gmail.com"

    def as_header(self) -> str:
        return f"{self.name} {self.email}"


def ensure_data_dirs() -> None:
    """Create directories needed for storing downloaded data."""

    FILINGS_DIR.mkdir(parents=True, exist_ok=True)
    EARNINGS_DIR.mkdir(parents=True, exist_ok=True)
