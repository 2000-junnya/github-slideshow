# Probability Engine v1.0.1 設計レビュー（改善提案）

このメモは、提示された As-Is 設計書に対して **現実運用で効きやすい順** に改善候補を整理したものです。

## 1. 最優先で直すべき点

1. **EV判定式を控除込みの期待収益に統一**
   - 現状 `EV_lb = p_cons * o_post > 1` は「倍率」の判定で、実装と運用側で意味がズレやすい。
   - 推奨は `E[profit per 1] = p_cons * o_post - (1 - p_cons)` を使い、
     `> 0` を基準にすること。

2. **α（Trust Gate）の符号を再点検**
   - 現仕様では市場エントロピーが高いほど `alpha` が上がる（市場信頼↑）。
   - 多くの市場では「高エントロピー＝不確実性高い」場合があり、逆符号が合うケースが多い。
   - 最低限、`w_entropy` の符号を設定値で反転できるようにして A/B 比較可能にする。

3. **p_cons の信頼性を上げる（seedノイズ依存を脱却）**
   - 現在の不確実性は「Δへ足したガウスノイズ」の分散なので、
     モデル不確実性の代理としては弱い。
   - 当面はブートストラップ（レース単位再標本）や時系列CVで得た複数モデル分散へ移行する。

## 2. 数理面で改善効果が高い提案

4. **合成オッズは対数空間で重み付き統合**
   - 三連単 head 縮約は有効だが、券種追加時に単純平均すると歪みやすい。
   - `log p_synth = Σ_t λ_t log p_t`（λはデータ量と流動性に応じる）を基準にする。

5. **market impact を固定点で解く拡張余地を確保**
   - 現式は 1 回投入の近似として合理的。
   - ただし複数馬同時投票時は相互作用が出るため、将来的に
     「全ベット同時反映→post_odds再計算」の固定点反復を追加しやすい設計にする。

6. **容量制約 γ をレース流動性連動にする**
   - 固定 `gamma=0.005` だと過密レースでは保守的すぎ、過疎ではまだ強すぎる可能性。
   - `gamma(pool, mto)` の関数化（例: poolの対数増加で緩和）を推奨。

## 3. 評価設計（勝てる/壊れるの判定精度を上げる）

7. **DBバックテストをJSON版と同等指標へ**
   - ROIだけでなく Sortino/MDD/Hit率/Turnover を同時出力。
   - これだけで「高ROIだが高ドローダウン」等の事故検知が可能。

8. **時系列分割での安定性評価を標準化**
   - ランダム分割はリークしやすい。
   - 週・開催単位のウォークフォワードを標準レポートにする。

9. **キャリブレーション指標を追加**
   - Brier score、Logloss、ECE を入れ、
     `p_win` と `p_cons` が確率として正しいかを監視する。

## 4. 実装ロードマップ（最短）

- Phase 1（すぐ）
  - EV判定式の明確化
  - α係数符号のA/B可能化
  - DBバックテストへ Sortino/MDD 追加

- Phase 2（1〜2スプリント）
  - ΔをGBDT化
  - 複数券種合成（馬連/馬単/三連複）
  - 時系列CV + キャリブレーション

- Phase 3（運用前）
  - データ収集基盤の監視（欠損率・遅延・mto整合）
  - ドリフト検知（特徴量分布・回収率分布）

## 5. 全体コメント

提示された As-Is は、MVPとしてはかなり筋が良く、
特に「No Bet」「Impact反映」「容量制約」を最初から入れている点が強いです。

次の勝負どころは **ヒューリスティックの学習化** と **評価の時系列厳密化** の2点です。
ここを先に固めると、理論拡張（券種合成・階層モデル）を入れても性能評価がブレにくくなります。

## 6. Phase 1 実装チケット（1日単位 / 優先順位・完了条件つき）

> 前提: 既存MVPの挙動を壊さないため、各日で **実装 + 最低限の回帰確認** までを1チケットとして完了させる。

### Day 1（P0）EV判定式の定義統一とコード反映

- **目的**
  - 購入判定の期待値定義を「倍率判定」から「期待損益判定」に統一し、仕様と運用の解釈ズレをなくす。

- **作業内容**
  1. `decision` 層のEV計算を `E[profit per 1] = p_cons * o_post - (1 - p_cons)` に統一。
  2. 閾値を `> 0` 判定に変更し、変数名を `ev_lb_profit` 等へ更新（可読性確保）。
  3. `bets.json` / `inference_output.json` に出力するフィールド名・説明文を整合。
  4. README または設計メモに「旧式との違い」を1節追加。

- **完了条件（Definition of Done）**
  - 同一入力データで、EV判定が新定義で一貫して動く。
  - 出力JSONのフィールド説明と実装式が一致。
  - 最低1件、正/負EVケースを含むテスト（または固定サンプル検証）を追加。

---

### Day 2（P0）Trust Gate の A/B 可能化（`w_entropy` 符号切替）

- **目的**
  - `alpha` のエントロピー依存を仮説検証可能にし、固定思想を排除する。

- **作業内容**
  1. 設定（YAML or CLI）で `w_entropy` の符号反転を切替可能にする。
  2. ログ/出力に `alpha_config`（符号設定）を明示して実験追跡可能にする。
  3. `infer` / `backtest` の両経路で同一設定が使われるよう配線。
  4. 2パターン（+/-）での結果比較テンプレート（CSV/JSON）を用意。

- **完了条件（Definition of Done）**
  - 実行時オプションだけで `w_entropy` の符号を切替できる。
  - 出力ログから、どちらの設定で走ったか追跡可能。
  - 同一日付データで A/B の比較結果が保存される。

---

### Day 3（P1）DBバックテスト指標拡張（Sortino / MDD / Hit率 / Turnover）

- **目的**
  - ROI偏重を避け、リスク込みの評価を可能にする。

- **作業内容**
  1. `backtest-db` の出力へ Sortino/MDD を追加（JSON版と整合）。
  2. Hit率（的中レース比率）と Turnover（賭け回転率）を追加。
  3. 出力フォーマットを `db_backtest_output.json` に定義して固定化。
  4. 指標計算のゼロ除算/賭けなしケースを明示ハンドリング。

- **完了条件（Definition of Done）**
  - `backtest-db` の出力に 5 指標（ROI/Sortino/MDD/Hit率/Turnover）が揃う。
  - ベット無し日でも落ちずに `0` または `null` で一貫返却。
  - 指標計算の単体テスト（最低2ケース: 通常 / ベット無し）を追加。

---

### Day 4（P1）回帰確認と最小ドキュメント整備

- **目的**
  - Day1〜3変更の結合不整合を潰し、次スプリントへ安全に渡す。

- **作業内容**
  1. `demo` / `backtest` / `ingest→infer→backtest-db` を一通り再実行。
  2. 主要出力（predictions, bets, backtest report）の項目差分を確認。
  3. 「変更点サマリ」「既知の制約」「次フェーズ前提」を1ページ化。

- **完了条件（Definition of Done）**
  - 主要CLIがエラーなく完走。
  - 出力変更点がドキュメント化され、後続担当が迷わない。
  - PR本文に“互換性影響（Breaking/Non-breaking）”が明記される。

## 7. 実装順序の指針（最短で成果を出すため）

- **先に Day1→Day2 を完了**: 意思決定ロジックの中核（EVとGate）を先に確定。
- **次に Day3**: 変更の善し悪しを判定するための評価軸を拡張。
- **最後に Day4**: 回帰確認と知識の言語化で、次のPhase 2（GBDT化）へ接続。

この順序なら、最小4日で「ロジック定義の明確化 + 実験可能化 + 評価強化」まで到達できる。

## 8. Phase 1〜3 完遂プラン（全解決用 / 実装順に並べた確定チケット）

> ここでは「提案止まり」にしないため、Phase 1〜3 を **着手可能タスク + 完了判定 + 主要成果物** まで固定する。

### Sprint A（Phase 1を完全消化）

#### A-1（P0）EV判定ロジックの本実装
- 変更対象（想定）
  - `pe/decision/strategy.py`
  - `pe/decision/bankroll.py`
  - `pe/backtest/engine.py`
  - `pe/pipeline.py`
- 実装要件
  - EV下限を `ev_lb_profit = p_cons * o_post - (1 - p_cons)` に統一。
  - 判定条件を `ev_lb_profit > 0` に統一。
  - 旧フィールド（`ev_lb`）との互換性を保つ場合は `ev_lb_legacy` として明示。
- 完了判定
  - 推論/バックテスト/DBバックテストで同一式が使われる。
  - JSON出力のフィールド説明と式が一致。

#### A-2（P0）Trust Gate符号A/Bの実装
- 変更対象（想定）
  - `pe/models/trust_gate.py`
  - `configs/base.yaml`
  - `pe/cli.py`
- 実装要件
  - `w_entropy_mode: positive|negative|auto` を設定追加。
  - `auto` は当面 `positive` と同値で実装し、将来学習値で置換可能にする。
  - 推論出力に `alpha_meta` を追加（`w_entropy`, `mode`, `pool`, `entropy`, `class_code`）。
- 完了判定
  - CLI引数だけで `positive/negative` 切替可。
  - 同日同条件でA/B比較JSONを自動保存。

#### A-3（P1）DBバックテスト指標の拡張
- 変更対象（想定）
  - `pe/pipeline.py`
  - `pe/backtest/metrics.py`
- 実装要件
  - 出力指標を `roi, sortino, mdd, hit_rate, turnover` に拡張。
  - ベット無し日でクラッシュしない（`0` or `null` を仕様固定）。
- 完了判定
  - `backtest-db` の出力JSONが固定スキーマに準拠。

---

### Sprint B（Phase 2を完全消化）

#### B-1（P0）Edge Δ のGBDT化
- 変更対象（想定）
  - `pe/models/edge.py`（学習済みモデル推論器へ）
  - `pe/features/build.py`
  - `pe/cli.py`（train/eval サブコマンド追加）
- 実装要件
  - 目的変数を「1着ラベル」に固定し、学習データは時系列分割で作成。
  - 特徴量最小セット: `d_i`, market rank, odds dispersion, mto, class_code, pool。
  - 出力は `delta_hat` と `delta_unc`（fold分散）を保持。
- 完了判定
  - ヒューリスティックΔとの比較レポート（AUC/Brier/ROI）を生成。

#### B-2（P1）合成オッズの多券種統合
- 変更対象（想定）
  - `pe/features/synth_odds.py`
  - `pe/features/build.py`
- 実装要件
  - `trifecta`, `exacta`, `quinella`, `trio`（入手可能な券種のみ）に対応。
  - 統合式は `log p_synth = Σ λ_t log p_t` を採用。
  - `λ_t` は `coverage × liquidity` で正規化。
- 完了判定
  - 券種欠損時でも degrade graceful（利用可能券種だけで正規化）。

#### B-3（P0）時系列CV + キャリブレーション
- 変更対象（想定）
  - `pe/backtest/engine.py`
  - `pe/backtest/metrics.py`
  - `pe/models/ensemble.py`
- 実装要件
  - ウォークフォワード分割を標準化（例: 4fold rolling）。
  - 指標に `Brier`, `LogLoss`, `ECE` を追加。
  - `p_win` は isotonic/platt のどちらかで後段キャリブレーション可能に。
- 完了判定
  - CV結果で「事前→事後」キャリブレーション改善が確認できる。

---

### Sprint C（Phase 3を完全消化）

#### C-1（P0）データ品質監視（収集基盤）
- 変更対象（想定）
  - `pe/data/providers.py`
  - `pe/data/validator.py`
  - `pe/pipeline.py`
- 実装要件
  - 監視指標: 欠損率、遅延、minutes_to_off整合、pool/takeout欠落率。
  - 日次で `data_quality_report.json` を生成。
- 完了判定
  - しきい値超過時に warning を記録し、推論を fail-open/fail-close で選択可能。

#### C-2（P1）ドリフト検知
- 変更対象（想定）
  - `pe/backtest/metrics.py`
  - `pe/pipeline.py`
- 実装要件
  - 特徴量分布ドリフト: PSI または JS divergence。
  - 収益分布ドリフト: rolling ROI / hit_rate の変化点監視。
  - 週次 `drift_report.json` を生成。
- 完了判定
  - ドリフト検知時に `alpha` もしくはベット上限を保守側へ自動調整するフックを提供。

#### C-3（P1）運用ガードレール
- 変更対象（想定）
  - `pe/decision/nobet.py`
  - `pe/decision/strategy.py`
- 実装要件
  - 連敗時の自動スロットル、日次損失上限のハードストップ、異常時No-Bet全振り。
- 完了判定
  - 異常データ日・高ドリフト日に誤発注しないことをシナリオテストで確認。

## 9. 「全解決」の定義（Exit Criteria）

Phase 1〜3 を「完了」と見なすには、下記をすべて満たすこと。

1. 機能完了
   - 新CLI（必要分）が動作し、推論〜評価〜監視が一連で完走。
2. 評価完了
   - ROIだけでなく、Sortino/MDD/Brier/LogLoss/ECE を定期出力。
3. 運用完了
   - データ品質レポートとドリフトレポートが日次/週次で自動生成。
4. 安全完了
   - ガードレール（ハードストップ/No-Bet強制）が有効化できる。
5. 文書完了
   - 設計書と実装仕様が一致し、出力JSONのスキーマが固定化。

## 10. 依存関係と順序（詰まり防止）

- 先に A-1, A-2（意思決定中核）
- 次に A-3（評価軸）
- その後 B-1（学習化）
- B-2, B-3（頑健化と確率品質）
- 最後に C-1, C-2, C-3（運用安全化）

## 11. すぐ使える進行テンプレート（毎日の運用）

- 朝: 前日レポート確認（ROI/Sortino/MDD + 品質/ドリフト）
- 昼: 1チケット実装 + 単体テスト
- 夕: `demo/backtest/ingest→infer→backtest-db` の回帰確認
- 夜: 変更点・既知制約・翌日TODOを1ページ更新

この運用を固定すると、Phase 1〜3 を「提案」ではなく「実装完了」に着地させやすい。
