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

---

## 使い方（日本語ガイド）

### 前提条件

- Python 3.10 以上がインストールされていること
- `pip` が利用できること
- （推奨）仮想環境を利用して依存関係を分離すること

### 1. 依存パッケージのセットアップ

リポジトリのルートディレクトリで以下を実行します。

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r tools/requirements.txt
```

現在必要なのは `requests` と `beautifulsoup4` だけです。

### 2. GRRR の提出書類を取得する

SEC が推奨するユーザーエージェント文字列（氏名と連絡先メールアドレスを含む）を指定して CLI を実行します。

```bash
python -m tools.grrr_tool.cli --limit 40 --save-json \
  --user-agent "あなたの名前 your@example.com"
```

主なオプション:

- `--limit` : 取得する最新提出書類の件数（既定値は 100）
- `--save-json` : メタデータを `data/grrr_filings.json` に保存します
- `--download` : 本文 HTML や添付資料をダウンロードします

出力は `data/` フォルダに保存されます。

```
data/
├── grrr_filings.csv
├── grrr_filings.json          # --save-json 指定時
├── grrr_earnings_calls.csv
├── filings/<accession>/...    # --download 指定時
└── earnings_calls/<accession>/raw.html  # --download 指定時
```

### 3. SEC へアクセスできない場合

ネットワーク設定によって `https://data.sec.gov` へのアクセスが遮断されると、CLI は自動的に `tools/grrr_tool/samples/` に同梱されているサンプルデータを利用します。その際は以下のような警告が表示されます。

```
Failed to reach SEC (...). Using bundled sample data instead.
```

サンプルデータでも CSV 出力は生成されるため、オフラインでワークフローを試すことができます。最新の実データが必要な場合は、SEC にアクセスできる環境で正しいユーザーエージェントを指定して再実行してください。

## Next steps

The long-form roadmap, design ideas, and future automation milestones live in [`docs/investment-tool-plan.md`](docs/investment-tool-plan.md). Contributions or ideas to extend the pipeline (comparison views, UI experiments, etc.) are welcome—open an issue to discuss.
