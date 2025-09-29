# GRRR Data Collection Utilities

This directory contains a minimal Python implementation that automates the first
phase of the investment tool roadmap: collecting filing metadata from the SEC
and surfacing potential earnings call dates for Gorilla Technology Group
(GRRR).

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r tools/requirements.txt
```

## Usage

```bash
python -m tools.grrr_tool.cli --limit 40 --save-json --download \
  --user-agent "Your Name you@example.com"
```

The command performs the following steps:

1. Fetch the latest SEC submissions for the configured CIK (defaults to
   `0001908462`).
2. Store filing metadata in `data/grrr_filings.csv` (and `grrr_filings.json`
   when `--save-json` is passed).
3. Inspect 6-K/20-F documents for conference call announcements and save the
   extracted schedule information to `data/grrr_earnings_calls.csv`.
4. Optionally download the primary filing documents and raw press releases that
   reference the earnings call (`--download`).

Each request is issued with an SEC-compliant User-Agent header—remember to pass
an accurate contact string via `--user-agent` when running the tool yourself.

## Outputs

```
data/
├── earnings_calls/
│   └── <accession number>/raw.html  # Optional raw transcript/press release
├── filings/
│   └── <accession number>/primary-document.htm  # Optional filing downloads
├── grrr_earnings_calls.csv
└── grrr_filings.csv
```

The CSV files are append-only snapshots; rerunning the tool overwrites them with
fresh data so you can commit snapshots or feed them into downstream processing.

## Troubleshooting

- **HTTP 403 / proxy errors** – The SEC blocks anonymous scraping and some
  restricted networks intercept outbound HTTPS calls. When a live request fails
  the CLI now falls back to bundled sample submissions, index manifests, and
  filing excerpts so you can exercise the pipeline offline. The warning will
  look like `Failed to reach SEC (...). Using bundled sample data`. To fetch the
  real filings instead, supply a valid User-Agent ("Name email@example.com") and
  run the command from a network that allows outbound access to
  `https://data.sec.gov`.
- **Missing output files** – The tool only writes CSV/JSON files after it has
  filing rows to persist. Use `--limit` to increase the number of filings that
  are inspected if the sample payload feels too small for testing.
