# 米国株IR情報・財務分析ツール設計メモ

## 1. 目的
- 米国NASDAQに上場する **Gorilla Technology Group Inc. (ティッカー: GRRR)** を初期ターゲットとして、同社が提出・公開するIR資料を網羅的に収集。
- 20-F、6-K、Form F-3/424B など外国私募企業 (Foreign Private Issuer; FPI) 向けのフォームを中心に、補完的なプレスリリースや投資家向け資料も横断管理。
- BamSECのような差分表示や表抽出で「読む作業」を効率化。
- 決算説明会 (カンファレンスコール) の内容もテキスト化して戦略・ニュアンスを把握。

## 2. 全体アーキテクチャ
```
データ取得層 → データストレージ層 → 処理・分析層 → フロントエンド層
```
- **データ取得層**: SEC EDGAR API、NASDAQ/英国等の外国企業公開資料、企業IRサイト、決算説明会音声/書き起こし。
- **データストレージ層**: 原文保存 (S3 などオブジェクトストレージ) と構造化データ (PostgreSQL / DuckDB) の両方。
- **処理・分析層**: テキスト解析、表抽出、比較エンジン、要約生成。
- **フロントエンド層**: Webアプリ (Next.jsやReact) で差分・表・要約を表示。

## 3. データ取得
### 3.1 SEC EDGAR からの収集 (GRRR 向け)
1. [EDGAR Full-Text Search API](https://www.sec.gov/edgar/search/) で GRRR の CIK (0001908462) を取得してクエリを固定。
2. `submissions` エンドポイントから 20-F、6-K、F-3、424B3/424B5、Form 8-A12B など FPI 特有の提出書類を列挙。過去に SPAC 経由で提出された F-4、F-1、ファイリング補遺 (FWP、DEFA14A 等) も履歴として取り込む。
3. 6-K に添付される Exhibit (プレスリリース、投資家向けプレゼン、決算資料) を個別ファイルとして保存し、タグで分類。
4. Form 20-F の XBRL タクソノミーは IFRS ベースであるため、US-GAAP との差異を吸収するマッピングテーブルを用意。
5. 原文 (HTML, XBRL, PDF) をダウンロードし、言語 (英語/中国語など) をメタデータに保持。
6. メタデータ (提出日、報告対象期間、フォーム種別、アクセッション番号、URL) を DB に格納。
7. バッチ処理 + 定期クロール (Prefect/Airflow) を月次・四半期ベースで設定し、提出遅延を監視する。

### 3.2 プレスリリース・IRサイト
- Gorilla Technology Group の [Investor Relations サイト](https://www.gorilla-technology.com/investor-relations/) のニュース/イベント/プレゼン資料をスクレイピング対象に追加。
- RSS/Atom フィードがあれば購読。なければサイトマップ/HTML スクレイピング。
- Cloudflare 等で保護されている場合は Puppeteer/Playwright でヘッドレスブラウザを使用。
- 取得した資料をPDF→テキスト化 (pdfminer.six, Tesseract OCR for scanned)。
- NASDAQ のカレンダー、英国 Companies House、台湾/シンガポール等での追加開示があれば URL を控えて補完資料として取り込む。

### 3.3 その他の規制開示ソース
- GRRR は外国私募企業として NASDAQ 上場を維持しているため、米国以外の規制開示 (例: UK National Storage Mechanism、香港/台湾証券取引所の公告) もウォッチする。
- 主要ファイナンス取引に関する Form 6-K 添付資料 (Warrant Exercise、Private Placement) や Form 20-F/6-K 補完の `Press Release`、`Investor Presentation` をメタデータ付きで保存し、イベント種別 (資金調達、提携、ガイダンス更新) をタグ付け。
- SPAC 経由の上場経緯があるため、過去の Proxy Statement (DEFM14A/DEFA14A)、Form 425 をバックフィルし、経営陣コメントや財務予測の参照元として保持。
- 株主・所有構造の変化を追うために Schedule 13D/13G、Form 6-K の株式発行・買戻し関連資料、必要に応じて Form 12b-25 (提出遅延通知) も監視対象に含める。

### 3.4 決算説明会 (カンファレンスコール)
- **現状フェーズ**: まずは情報源と取得方法のリサーチに集中し、実装は後続タスクとして整理する。
- **収集計画の洗い出し**: 企業IRサイト、Seeking Alpha、外部ベンダーの入手経路を比較し、アクセス条件や費用を調査して優先度を決める。
- **文字起こし方針の策定**: Whisper や AWS Transcribe など候補ツールの精度・コストをベンチマークし、正式導入前にトライアルを実施する計画を立てる。
- **話者識別の要否評価**: CEO/CFO/アナリスト別に分けるかは利用シナリオを定義したうえで判断し、必要であればダイアライズ機能の要件をまとめる。
- **既存書き起こしの調査**: PDF/HTMLなど公開フォーマットの有無を調べ、利用ポリシーや自動取得の可否を一覧化した計画表を作る。

## 4. データストレージ設計
- **原文保存**: S3互換ストレージに資料ファイルを保存し、メタデータにキーを保持。
- **構造化DB**: PostgreSQL (RDS/自前) で以下のテーブルを定義。
  - `filings`: form type, period, filing date, accession number, URL, storage key。
  - `sections`: 各報告書のセクション (MD&A, Risk Factors 等) を抽出・紐付け。
  - `tables`: HTML/XBRLから抽出した表データ。
  - `transcripts`: 説明会書き起こし、発言者、タイムスタンプ。
- **検索インデックス**: OpenSearch/Elasticsearch で全文検索。ベクトル検索 (OpenSearch + embeddings) で類似セクション比較。

## 5. 処理・分析機能
### 5.1 セクション抽出と正規化
- HTML解析 (BeautifulSoup) でヘッダ構造を抽出。
- 20-F/6-K の XBRL は IFRS タクソノミーが中心となるため、`ifrs-full` の概念を US-GAAP にマッピングする変換レイヤーを用意して四半期比較の指標名称を統一。
- リスク要因や MD&A に相当する `Operating and Financial Review and Prospects` など FPI 固有のセクション見出しを辞書登録し、自然言語処理で章タイトルを正規化。
- Form 6-K に添付された PDF/プレゼン資料も OCR/HTML パースを行い、セクション単位で構造化。

### 5.2 差分表示
- 期間別に同一セクションを比較。20-F の年次比較と 6-K (半期/四半期) の横比較を切り替えられる UI を用意。
- テキスト差分: Git diff 風ハイライト (jsdiff)。IFRS 特有の表現 (`Operating Income`, `Loss for the year` など) に対応した差分辞書を整備。
- 表差分: IFRS 指標 (Total Comprehensive Income, Profit (Loss), Equity attributable to owners) のキー項目ごとに増減率、自動カラーリング。
- 財務ハイライト: 売上・EPS・調整 EBITDA・Gross Margin 等、GRRR が開示する KPI を XBRL/プレスリリース双方から抽出し、グラフ表示。
- 将来的には要約機能が成熟した段階で、`Risk Factors`/`Operating and Financial Review` の記述を四半期ごとに並べて要約差分を生成し、変更点をカード化して表示する。
- 決算説明会の文字起こし・要約パイプラインが整備できたら、各コールで言及された戦略・ガイダンス・経営者コメントをテーマ別に比較できるよう拡張する。

### 5.3 テーブル抽出
- XBRL → pandas でDataFrame化。
- PDF/HTML の表は camelot/tabula または `pandas.read_html`。
- 抽出結果を `tables` テーブルに保存し、タグ (Income Statement, Cash Flow, Segment 等) を付与。

### 5.4 決算説明会開催日の収集と管理
- LLM要約やキーフレーズ抽出は後回しにし、まずは決算説明会の開催日時データを整備する。
- 情報源: 企業IRサイトのイベントカレンダー、プレスリリース、Form 6-K (Item 99 のプレスリリース添付) などで開催日時を収集。必要に応じて NASDAQ の Earnings Calendar やサードパーティ (Seeking Alpha、Benzinga) のリスティングも照合する。
- 取得するメタデータ例: 開催日、開始時刻 (タイムゾーン)、決算種別 (Year-End, 1H, Q1/Q2 など)、開催形式 (電話/オンライン/対面)、関連IR資料のURL、添付されたプレゼン資料の有無。
- `earnings_calls` テーブル (例: `id`, `cik`, `ticker`, `fiscal_period`, `call_datetime`, `timezone`, `source_url`, `notes`, `language`) を用意し、履歴を羅列できるようにする。
- 過去分はCSV/Excelで公開されているイベントカレンダーや外部ベンダー (BamSEC, AlphaSense, Seeking Alpha) のエクスポートデータを取り込み、生データをそのまま保存する。

### 5.5 決算説明会生データの取得と表示
- 現段階では要約・感情分析・キーワード抽出は行わず、公開されている書き起こしや音声を生データのまま取り込む。
- 書き起こしがPDF/HTMLで提供されていればテキスト化後も整形せずに保存し、UIでは原文を段落順で表示する。
- 音声ファイルのみ入手できた場合は Whisper/AWS Transcribe で文字起こしするが、句読点や整形は最小限に留め、編集ログとともに保存する。
- UIの「決算説明会ビュー」では、開催日時ごとにタブ/リストで並べ、該当コールの原文テキストと音声ファイルへのリンクをそのまま提供する。
- 生データ表示時はメタデータ (日時、フォームタイプ、引用元URL) を併記し、フィルタリングは開催日や発言者で行うが要約カードは作成しない。

## 6. フロントエンドUI案
- **ダッシュボード**: 最新四半期のサマリー (売上、EPS、ガイダンス、主要トピック)。
- **差分ビュー**: セクションごとに旧/新ドキュメントの並列表示 + 差分ハイライト。
- **表ビュー**: 財務表をチャート化。CSVエクスポート、カスタム指標計算。
- **脚注/リスク要因ビュー**: リスク要因の追加・削除・更新をタグで表示。
- **決算説明会ビュー**: タイムライン表示と原文テキスト/音声リンクのリスト化。要約カードは作成せず、キーワードフィルタのみ提供。
- **検索/クエリ**: フリーキーワード検索 + フィルタ (期間、フォームタイプ、セクション)。

### 6.1 参考プロダクトから得られるUI/UXの示唆
- **AlphaSense**
  - グローバル検索バーを中心に据え、直近ヒットやセクションサジェストをドロップダウンで即時表示する点が秀逸。→ ヘッダー常駐検索 + サイドバーに「最近見たフィリング」「保存したタギング」「ピン留め検索」をまとめ、検索起点での回遊性を高める。FPI フォーム (20-F/6-K/Press Release) をワンクリックで切り替えられるトグルを配置。
  - 文書ビューの右ペインでノート・タグ付け・ハイライトを即時共有できる。→ 自分用ツールでは右側に「メモ」「次回見返すポイント」「タスク化 (フォローアップ)」カードを常駐させ、6-K の添付資料単位でメモスレッドを分けられるようにする。
  - 比較ビューでキーフレーズ差分を色分けしたアラートにしている。→ 差分ビューはアクセシビリティ対応カラー (WCAG AA) をベースに、追加=緑/削除=赤/要注意=黄色の3色に加え「注目ワード」バッジを表示し、視認性と意味を一貫させる。
- **BamSEC**
  - 左カラムにフォームタイプ＋年度のツリーを持たせ、任意の年度・フォームを素早く切り替えられる。→ 左サイドバーを「フォームタイプ → 年度 → 期間」で階層化し、`20-F`、`6-K`、`Press Release`、`Presentation` など GRRR に特有のカテゴリをプリセットして呼び出しを高速化する。
  - 財務表はデータとチャートをタブ切り替えで同居させている。→ 表ビューでもテーブル/グラフ/差分のタブを実装し、IFRS の表示科目 (Revenue, Gross Profit, Loss before income tax 等) を列テンプレートとして保持。コンパクトモードではタブをドロップダウン化してモバイル幅でも閲覧しやすくする。
  - リスク要因やMD&Aは段落ごとにバージョン差分を並べ、変更箇所をアイコンで示す。→ 「変更点サマリー」パネルをカード化し、「新規」「更新」「削除」に加えて `Operating Environment` や `Government Regulations` など FPI 特有のタグを選択できるようにし、自分向けレビューキューと連携させる。

### 6.2 画面レイアウト草案
- **グローバル構成**: 左サイドバー (ドキュメントツリー + フィルタ)、メインペイン (本文/グラフ)、右インスペクタ (メモ・タグ・差分サマリー) の3カラム。幅が足りない場合は右ペインをドロワー化。
- **ヘッダー**: 固定配置で検索バー、期間プリセット (最新Q, 前年Q, 過去5年など)、ビュー切り替えボタン (Doc / Diff / Tables / Notes)。
- **ダッシュボード**: KPIカード (売上, EPS, ガイダンス) とスパークライン、最新の重要リスク変更をカード表示。AlphaSense風に「関連ニュース」「アナリストコメント」を追加するスペースを将来的に確保。
- **差分ビュー**: 上部に期間トグル (例: 2023Q4 vs 2023Q3 vs 2022Q4)、メインは左右並列表示。変更箇所はスクロール連動シンク、右ペインで要約・メモ・タグ追加。
- **テーブルビュー**: 上部でステートメント種類 (IS/BS/CF/Segment) をタブ選択、中央に表、下部に差分グラフ。列カスタマイズをモーダルで行い、BamSEC同様に列固定と並び替えを即時反映。
- **脚注/リスク要因ビュー**: アコーディオンでセクションを開閉し、変更箇所にラベル。比較対象をプルダウンで選択、要約をカード表示。
- **決算説明会ビュー**: 左に開催日時タイムライン、中央に生の発言ログ、右にメタデータフィルタ (発言者・セクション・資料リンク)。AlphaSenseの Transcript Viewer を参考にしつつ、要約カードは配置しない。

### 6.3 インタラクション設計と操作感向上策
- **キーボードショートカット**: `Cmd/Ctrl + K` で全体検索、`[` `]` で前後文書、`d` で差分モード切替などを設定し、操作の手数を削減。
- **コンテキストメニュー**: テキスト選択時にポップオーバーで「ハイライト」「要約生成」「メモ追加」を表示し、ワンクリックで記録可能にする。
- **レイアウトプリセット保存**: 使い方に合わせて「財務重視」「リスク重視」「コール重視」のパネル構成を保存・切替できるようにする。
- **レスポンシブ対応**: 13インチノートPCでも閲覧できるよう、ブレークポイントでサイドバーをオフキャンバス化し、タブ/ドロップダウンでビューを切替。
- **アクセシビリティ**: カラーパレットは WCAG AA を意識し、ダークモードも提供。スクリーンリーダー用にセクションラベルとキーボードフォーカスを明示。
- **ユーザーテストの進め方**: 自身のワークフローを記録し、30分以内に目的の情報へ到達できたかを指標化。AlphaSense/BamSECでの操作と比較し、タスク完了時間やクリック数を測定する。

## 7. ワークフローと自動化
- Airflow/Dagster で以下をスケジュール。
  - SEC API クロール (日次)。
  - IRサイトスクレイピング (日次〜週次)。
  - 音声書き起こし (新規音声入手時)。
  - 差分・要約生成 (新規データ取得後)。
- 新規資料取得時にSlack/メール通知。

## 8. セキュリティ・法的配慮
- EDGARデータの利用規約に準拠 (User-Agent, リクエスト頻度管理)。
- 公開されているIR資料のみ収集。著作権に注意。
- 個人利用でもログイン認証を設け、APIキーやストレージ権限を安全に管理。

## 9. 技術スタック候補 (低コスト優先)
| 層 | 初期構成 (極力無料/低コスト) | 拡張時の選択肢 |
| --- | --- | --- |
| クロール | Python (Requests, BeautifulSoup, Playwright)。GitHub Actions の無料枠で定期実行 | Node.js (Puppeteer)、有料クローラープラットフォーム |
| ETL | cron + `python` スクリプト、または `Prefect` OSS | Apache Airflow, Dagster Cloud |
| ストレージ | ローカル/自宅NAS上の MinIO + DuckDB/SQLite。バックアップは Wasabi の無料トライアルを活用 | AWS S3、マネージド PostgreSQL |
| 検索 | PostgreSQL/SQLite FTS、Meilisearch OSS (単一コンテナ) | OpenSearch、Algolia |
| 分析 | pandas、Polars、JupyterLab (Docker 上で自己ホスト) | dbt、Spark |
| NLP/LLM | Whisper.cpp や Faster-Whisper をローカル GPU/CPU で実行。Hugging Face の無料推論エンドポイント | OpenAI API、Anthropic、Bedrock |
| フロントエンド | Next.js (TypeScript) + Tailwind CSS。Vercel Hobby プランや Cloudflare Pages の無料枠 | Chakra UI、MUI、商用UIライブラリ |
| インフラ | Docker Compose、Ansible。CI は GitHub Actions 無料枠 | Kubernetes、Terraform + AWS/GCP/Azure |

- 初期段階は「手元マシン or 低価格VPS + OSS」で固定費を抑え、運用が安定した段階でマネージドサービスへ段階的に移行する。
- 収集量が少ないうちは DuckDB/SQLite で十分だが、同時アクセスやデータ量が増えたら PostgreSQL へ移行する設計にしておく。
- LLM利用もまずはローカル Whisper とオープンウェイトの埋め込みモデルで検証し、必要な箇所だけ有料APIに切り替える方針とする。

## 10. MVPロードマップ (3ヶ月目安)
1. **月1**: CIK設定→EDGARから20-F/6-K自動取得、DB保存、XBRL→財務表抽出 (IFRS マッピング含む)。
2. **月2**: UI試作 (財務表表示、差分ビュー)、要約生成。
3. **月3**: 決算説明会書き起こし連携、キーワード分析、通知機能。

## 11. 将来的な拡張
- マルチ銘柄対応、ウォッチリスト機能。
- LLMでIR情報からQ&A自動生成。
- 競合比較 (Peer分析)、KPIトラッキング。
- API公開 (GraphQL/REST) で外部連携。

## 12. テストと開発環境の整備
- **ローカルセットアップ**
  1. Ruby 3.x 系と Bundler をインストール (`gem install bundler -v 2.4.19` など、`Gemfile.lock` を Bundler 2 系に更新すると互換性が保ちやすい)。
  2. `bundle config set --local path vendor/bundle` でローカルに依存関係を隔離。
  3. `bundle install` を実行して GitHub Pages + html-proofer の依存を取得。
     - 社内ネットワークやCIで rubygems.org へのアクセスが制限される場合は `bundle config set mirror.https://rubygems.org https://rubygems.pkg.github.com/<org>` のように社内ミラー/プロキシを指定する。
     - あるいは `vendor/cache` に `bundle package` で事前に依存関係を固めておき、CI では `bundle install --local` を使う。
- **テスト実行コマンド**
  - `script/cibuild` (もしくは `bundle exec script/cibuild`) を実行すると以下を自動化。
    - `bundle exec jekyll build --baseurl "."` で静的サイトをビルド。
    - `htmlproofer _site/index.html --empty-alt-ignore` でリンク切れや HTML の問題を検証。
  - 変更前に `bundle exec jekyll serve --livereload` でローカル確認すると UI 回帰を早期検知できる。
- **CI/CD 連携**
  - GitHub Actions 例:
    ```yaml
    jobs:
      test:
        runs-on: ubuntu-latest
        steps:
          - uses: actions/checkout@v4
          - uses: ruby/setup-ruby@v1
            with:
              ruby-version: '3.2'
              bundler-cache: true
          - run: bundle exec script/cibuild
    ```
  - `bundler-cache: true` を利用すると gem のダウンロード失敗リトライを避けられる。
- **トラブルシューティング**
  - Bundler が `403 Forbidden` で失敗する場合は、IP 制限・TLS 証明書・古い Bundler バージョンが原因のことが多い。
    - `gem install bundler -v 1.17.3` で `Gemfile.lock` に合わせるか、`bundle update --bundler` でロックファイル側を更新。
    - Proxy 経由で接続するなら `bundle config set https://rubygems.org/ username:password@proxy:port` を設定。
    - それでも失敗する場合は `curl https://rubygems.org -I` で疎通確認し、CI では `retry` ステップやミラーを活用する。

## 13. 初期実装サンプル
- `tools/grrr_tool` 以下に Python 製の最小インジェスト実装を追加。
  - `python -m tools.grrr_tool.cli --limit 40 --user-agent "Your Name you@example.com"` で最新の 20-F/6-K を取得し、`data/grrr_filings.csv` と `data/grrr_earnings_calls.csv` を生成。
  - Earnings Call を含む 6-K を検出した場合は、開催日時の推定と生データ (HTML/テキスト) を `data/earnings_calls/<accession>/raw.html` に保存。
  - `--download` オプションで一次資料 (Primary Document) も `data/filings/<accession>/` に取得。
- これにより、将来予定している差分ビュー/要約機能より前段の「資料収集」「生データ保管」フェーズをローカルで再現できる。
