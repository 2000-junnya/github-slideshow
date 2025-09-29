# GRRR Filing Research Toolkit

This repository contains a small command-line utility that collects recent SEC filings and earnings-call announcements for Gorilla Technology Group (ticker **GRRR**). The tool is a first step toward the personal investment workflow documented in [`docs/investment-tool-plan.md`](docs/investment-tool-plan.md).

## Prerequisites

- Python 3.10 or later
- `pip`
- (Recommended) a Python virtual environment so the dependencies stay isolated

## 1. Install dependencies

From the repository root run:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r tools/requirements.txt
```

The only required packages today are `requests` and `beautifulsoup4`.

## 2. Collect GRRR filings

Execute the CLI with your own SEC-compliant User-Agent string (the SEC expects a contact name and email):

```bash
python -m tools.grrr_tool.cli --limit 40 --save-json \
  --user-agent "Your Name you@example.com"
```

Key flags:

- `--limit`: number of recent filings to inspect (defaults to 100).
- `--save-json`: also writes the filing metadata to `data/grrr_filings.json`.
- `--download`: grabs the primary filing documents and any referenced press releases for later reading.

Output files are written to the `data/` directory:

```
data/
├── grrr_filings.csv
├── grrr_filings.json          # when --save-json is provided
├── grrr_earnings_calls.csv
├── filings/<accession>/...    # when --download is provided
└── earnings_calls/<accession>/raw.html  # when --download is provided
```

## 3. Running without SEC access

Some networks block outbound traffic to `https://data.sec.gov`. When live requests fail, the CLI automatically falls back to bundled samples stored in `tools/grrr_tool/samples/`. You will see a warning such as:

```
Failed to reach SEC (...). Using bundled sample data instead.
```

This still produces the CSV snapshots so you can explore the downstream workflow offline. To fetch the latest real filings, rerun the command from a network that can reach the SEC after providing an accurate User-Agent string.

## Next steps

The long-form roadmap, design ideas, and future automation milestones live in [`docs/investment-tool-plan.md`](docs/investment-tool-plan.md). Contributions or ideas to extend the pipeline (comparison views, UI experiments, etc.) are welcome—open an issue to discuss.
