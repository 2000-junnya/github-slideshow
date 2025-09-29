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

### Troubleshooting dependency installation

- **`pip` cannot reach PyPI (e.g. 403/407 errors)** – your network may be behind a proxy. Re-run the install with your proxy settings, for example `pip install --proxy http://USER:PASSWORD@HOST:PORT -r tools/requirements.txt`.
- **Corporate firewalls that block PyPI entirely** – download the wheels from another network and copy them into this repository, then run `pip install --no-index --find-links ./wheelhouse -r tools/requirements.txt`.
- **Virtual environment already exists** – remove the `.venv` folder (`rm -rf .venv`) and recreate it if activation fails.

## 2. Collect GRRR filings

Execute the CLI with your own SEC-compliant User-Agent string (the SEC expects a contact name and email). The SEC generally prefers ASCII characters, so provide your name in romaji (roman letters). The example below uses the contact email you shared (`junya20061227@gmail.com`):

```bash
python -m tools.grrr_tool.cli --limit 40 --save-json \
  --user-agent "Junya YourSurname junya20061227@gmail.com"
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

#### インストールでエラーになる場合

- **PyPI にアクセスできず 403 や 407 が表示される**: プロキシ経由が必要な可能性があります。`pip install --proxy http://USER:PASSWORD@HOST:PORT -r tools/requirements.txt` のようにプロキシ設定を指定してください。
- **社内ネットワークで PyPI への通信が遮断されている**: 別ネットワークでホイールファイルを取得し、リポジトリ内にコピーしてから `pip install --no-index --find-links ./wheelhouse -r tools/requirements.txt` を実行します。
- **仮想環境のアクティベートに失敗する**: `.venv` フォルダを削除して (`rm -rf .venv`)、再度仮想環境を作り直してください。

### 2. GRRR の提出書類を取得する

SEC が推奨するユーザーエージェント文字列（氏名と連絡先メールアドレスを含む）を指定して CLI を実行します。SEC では ASCII 文字の利用が推奨されるため、氏名はローマ字で入力してください。以下の例では、共有いただいたメールアドレス `junya20061227@gmail.com` を使用しています。

```bash
python -m tools.grrr_tool.cli --limit 40 --save-json \
  --user-agent "Junya あなたの苗字 junya20061227@gmail.com"
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
