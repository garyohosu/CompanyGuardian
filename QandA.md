# QandA.md — 仕様レビュー時の不明点

SPEC.md のレビューで生じた質問を記録します。

---

## Q1. `checks` に指定できる全種別が未定義

**該当箇所:** §9.3、§9.5

サンプル YAML には `site_http` / `top_page_keyword` / `link_health` / `github_actions` / `artifact` / `report_generated` / `config_valid` / `self_status` が登場するが、仕様書にはこれらの完全なリストがない。

- 利用可能なチェック種別をすべて列挙し、各々の判定条件を定義してほしい。
- 未知の種別が指定された場合は警告・スキップのどちらか？

**Answer:**

利用可能な checks は初期版では以下に限定する。

- `site_http` — 対象 site に HTTP GET を行い、2xx を正常とする。3xx は警告、4xx/5xx は異常。
- `top_page_keyword` — 対象トップページ本文に `required_keywords` の全要素が含まれることを確認する。1つでも欠けたら異常。
- `link_health` — 範囲限定型とし、`portal` は同一オリジン内リンク + `enabled: true` な各 `virtual_company.site` + `link_targets`、`virtual_company` は同一オリジン内の主要導線のみを確認する。4xx/5xx は異常。
- `github_actions` — 指定 repo の直近実行状態を確認する。判定ルールは Q6 に従う。
- `artifact` — `required_artifacts` に定義された成果物の存在を確認する。定義方法は Q5 に従う。
- `report_generated` — 直近の完了対象日の日報ファイルが所定パスに生成されていることを確認する。定期実行時は前回定期実行分、手動実行時は直近の定期実行分を確認対象とする。
- `config_valid` — `companies.yaml` など必須設定ファイルが YAML/Markdown として構文妥当で、必須設定キーを満たすことを確認する。
- `self_status` — CompanyGuardian 自身の前回実行結果、README 必須セクション、自己監視要件、日報整合性を確認する。

未知の種別が指定された場合は、警告を日報に記録してその項目のみスキップとする。全体実行は止めない。

---

## Q2. `required_paths` はサイト URL パスかリポジトリ内パスか

**該当箇所:** §9.4

**Answer:**

初期版では `required_paths` は **後方互換の簡易記法** とする。
`site: https://example.com` に対して `required_paths: ["/about/", "/feed.xml"]` のように指定した場合、内部では `required_artifacts` の `type: site_path` に正規化して扱う。

新規定義は `required_artifacts` に統一する。リポジトリ内ファイル確認や workflow artifact 確認は `required_artifacts` の `type` で表現し、`required_paths` には追加しない。

---

## Q3. `auto-ai-blog` のサイト URL が Cloudflare Pages になっている

**該当箇所:** §9.5 サンプル

**Answer:**

ある。各バーチャルカンパニーは GitHub Pages 以外のホスティングも許容する。CompanyGuardian は「ホスティング方式」と「ソース管理」を分離して扱う。

- 公開先: GitHub Pages / Cloudflare Pages / その他静的ホスティングを許容
- ソース管理・CI: GitHub リポジトリと GitHub Actions を利用可能

`github_actions` チェックと Cloudflare Pages などの `site_http` チェックの組み合わせは問題ない。将来 GitHub Actions を使わない会社もあり得るため、`checks` は会社ごとに選択可能とする。

---

## Q4. CompanyGuardian 自身の `site` が仮 URL のまま

**該当箇所:** §9.5 サンプル

**Answer:**

初期版では CompanyGuardian は GitHub Pages を必須としない。`site` は任意項目とし、公開ページを持たない場合は `site_http` を設定しない。

- 公開ページを持つ場合 — `site` を実 URL に設定し、必要に応じ `site_http` を有効化する
- 公開ページを持たない場合 — `site` は省略可とし、`github_actions` / `report_generated` / `config_valid` / `self_status` のみで自己監視する

サンプルの `https://example.github.io/CompanyGuardian/` は仮値なので、正式仕様では削除または任意扱いに変更する。

---

## Q5. 「必須成果物（artifact）」の定義が不明

**該当箇所:** §10.3、§6.1

**Answer:**

`artifact` チェックは GitHub Actions の Artifacts に限定しない。会社ごとに `required_artifacts` 配列で定義する。各要素は以下のいずれかの `type` を持つ。

- `type: site_path` — 公開サイト上の必須パス（例: `/index.html`, `/posts/`, `/feed.xml`）
- `type: repo_path` — リポジトリ内必須ファイル（例: `README.md`, `data/latest.json`）
- `type: workflow_artifact` — GitHub Actions 実行物（例: `site-build`, `daily-report`）

初期版で最優先なのは `site_path`。`repo_path` と `workflow_artifact` は将来拡張対象として仕様上定義しておく。

---

## Q6. GitHub Actions「直近実行」の判定基準が不明

**該当箇所:** §10.3

**Answer:**

初期版では以下で統一する。

- 参照対象は **最新1回**
- `workflow` が指定されている場合はそのワークフローのみ
- `workflow` 未指定の場合は、そのリポジトリの最新実行1回
- `success` なら正常
- `failure` / `cancelled` / `timed_out` / `action_required` は異常
- `in_progress` / `queued` は警告
- 実行履歴が一度も存在しない場合は警告（定期実行が本来あるべき会社では異常扱いにしてもよい）

安全な初期実装として `workflow` は明示指定させることを推奨する。

---

## Q7. countermeasure の CM 番号は自動採番か手動管理か

**該当箇所:** §10.6

**Answer:**

初期版では **自動採番** とする。`countermeasures/` 配下を走査し、最大番号 + 1 を採番する。

並行実行時の重複を避けるための初期版前提:

- 日次実行は原則1ジョブのみ
- 同時手動実行は避ける

厳密な排他制御が必要になった場合は、将来以下のいずれかに拡張する。

- GitHub Actions の `concurrency` を使う
- 採番用メタファイルを導入する
- UUID + 論理番号の併用にする

---

## Q8. 「可能なら自動対策実施」の具体的な範囲が不明

**該当箇所:** §12.2、§6.3

**Answer:**

初期版の自動対策は **非破壊・低リスク操作に限定** する。

自動実施してよいもの:

- GitHub Actions の再確認・再解析
- 一時的失敗に対する再試行
- `workflow_dispatch` による安全な再実行
- 日報・incident・countermeasure の生成

提案までに留めるもの（人間確認前提）:

- 設定ファイル修正
- コミット・プッシュ
- HTML 修正・リンク書き換え
- Secrets や権限設定変更

初期版は **完全自動修復ではなく、低リスク再試行 + 修正提案** が基本。

---

## Q9. GitHub Token のスコープ要件が未定義

**該当箇所:** §18、§10.3

**Answer:**

- 同一リポジトリ内のみ見る場合は `GITHUB_TOKEN`
- 他リポジトリを監視する場合は必要最小限権限の PAT または fine-grained token を使用

必要権限の目安:

| 操作 | 必要権限 |
|------|----------|
| Actions 状態参照 | Actions: Read |
| Contents 参照 | Contents: Read |
| ワークフロー再実行 | Actions: Write |
| コミット・プッシュ | Contents: Write |

初期版では安全性のため、他リポジトリ監視は Read 中心、再実行は必要時のみ許可とする。コミット・プッシュ自動化はスコープ外寄りにしておくのが無難。

---

## Q10. スケジュール実行の時刻・タイムゾーンが未定義

**該当箇所:** §10.1、§8（`daily-guardian.yml`）

**Answer:**

運用基準は **JST** とする。日報ファイル名 `YYYY-MM-DD` も JST 基準で決める。

- 実行頻度: 1日1回
- 実行時刻: JST 06:00
- GitHub Actions cron: `0 21 * * *`（UTC 21:00 = JST 06:00）

手動実行（`workflow_dispatch`）について:

- 日報を生成する
- 同日複数回実行した場合、初期版では **別ファイル** を生成する
  - 定期実行: `reports/daily/2026-03-10.md`
  - 手動再実行: `reports/daily/2026-03-10_manual_01.md`

---

## Q11. `report_generated` の判定タイミングが自己監視フローと矛盾している

**該当箇所:** §9.4.2、§10.1、§10.4、§12.1

`report_generated` は「当日の日報ファイルが所定パスに存在する」ことを正常条件としている。一方で通常フローでは、

1. CompanyGuardian 自身を確認
2. 異常があれば incident / countermeasure を作成
3. 最後に日報作成

の順になっており、自己監視時点では当日の日報が未生成のため常に失敗する解釈になる。

- `report_generated` は「前回実行分の日報」を見る想定か
- あるいは自己監視を日報生成後に再実行する想定か
- それとも仮日報を先に生成してから自己監視する想定か

のいずれかを明確にしてほしい。

**Answer:**

`report_generated` は **当日分ではなく、直近の完了対象日の日報を確認するチェック** とする。

初期版では以下で固定する。

- 定期実行時
  - `github_actions` の確認対象: 当日実行分
  - `report_generated` の確認対象: 前回定期実行分の日報
- 手動実行時
  - `report_generated` は直近の定期実行分の日報を確認対象とする

これにより、自己監視時点で当日の日報がまだ未生成でも矛盾しない。

さらに、デイリー投稿の有無を確認する系チェックも **前日基準** とする。理由は、当日分はまだ生成・公開されていない可能性があるためである。

正式ルール:

- Action のチェックは当日基準
- デイリー投稿・日報・日次成果物の存在確認は前日基準
- JST で日付を判定する

例:

- `2026-03-10 JST 06:00` 実行時
  - GitHub Actions 成否: `2026-03-10` 時点の最新実行を見る
  - デイリー投稿有無: `2026-03-09` 分を見る
  - 日報有無: `2026-03-09` 分を見る

---

## Q12. `link_health` のチェック対象リンク範囲が未定義

**該当箇所:** §9.4.2、§10.2

`link_health` は「抽出したリンク」に対して HTTP HEAD/GET するとあるが、どこまでを対象にするかが不明。

- 同一オリジンの内部リンクのみか
- 親ポータルから各会社サイトへのリンクだけを対象にするのか
- 外部 SNS / 広告 / analytics などのリンクも含めるのか

が未定義のため、実装によってはチェック件数が爆発したり、外部要因で誤検知が増える。

**Answer:**

初期版の `link_health` は **範囲限定型** とし、無制限クロールは行わない。

対象範囲は以下。

- 親ポータル（`kind: portal`）
  - 同一オリジン内リンク
  - `companies.yaml` に定義された `enabled: true` の各 `virtual_company.site`
  - 明示的に `link_targets` で指定されたリンク
- 各バーチャルカンパニー（`kind: virtual_company`）
  - 同一オリジン内リンクのみ
  - トップページから直接到達できる主要導線のみ
  - 深さは 1 まで

除外対象:

- SNS
- 広告
- analytics
- 外部 CDN
- 外部ブログやニュース記事リンク
- クエリ付きトラッキングリンク全般

つまり、初期版では **内部リンク健全性確認 + 親ポータルから各会社への導線確認** を目的とし、外部依存リンクは原則除外する。

---

## Q13. `required_paths` と `required_artifacts` の役割が重複している

**該当箇所:** §9.4、§9.4.1、§10.3

`required_paths` は「サイト URL 配下の必須パス一覧」、`required_artifacts` の `type: site_path` も同じく公開サイト上の必須パスを表している。初期版でどちらを正として実装すべきかが分からない。

- `required_paths` は簡易記法として残すのか
- `required_artifacts` に一本化するのか
- 両方を許容するなら優先順位や併用ルールはどうするのか

を決めてほしい。

**Answer:**

初期版では `required_artifacts` を正とし、`required_paths` は **後方互換の簡易記法** とする。

正式方針:

- 新規定義は `required_artifacts` に統一する
- `required_paths` は初期版では読み取り対応してよいが、内部では `required_artifacts` の `type: site_path` に正規化して扱う
- 両方が指定された場合はマージする
- 重複パスは排除する

変換ルール:

```yaml
required_paths:
  - /feed.xml
  - /index.html
```

は内部的に以下と同義とする。

```yaml
required_artifacts:
  - type: site_path
    path: /feed.xml
  - type: site_path
    path: /index.html
```

これにより、初期版の実装互換性を保ちつつ、将来は `required_artifacts` へ一本化できる。

---

## Q14. 日報ファイル名ルールが節ごとに一致していない

**該当箇所:** §10.1、§10.7、§15.1

§10.1 では同日複数回実行時に `2026-03-10_manual_01.md` のような別ファイルを生成するとある。一方で §10.7 と §15.1 では出力先・ファイル名を `reports/daily/YYYY-MM-DD.md` とだけ定義している。

- 定期実行だけが `YYYY-MM-DD.md` 固定なのか
- 手動実行は常に別命名なのか
- 追記更新で 1 ファイルに集約する選択肢はないのか

の正式ルールを一本化してほしい。

**Answer:**

正式ルールを以下に一本化する。

- 定期実行
  - 出力先: `reports/daily/YYYY-MM-DD.md`
  - 対象日は JST 基準
  - 1日1回の定期実行は、その日付の固定ファイル名を使用する
- 手動実行
  - 出力先: `reports/daily/YYYY-MM-DD_manual_XX.md`
  - `XX` は `01` からの連番
  - 同日中に複数回手動実行した場合は連番を増やす
- 追記更新
  - 初期版では採用しない
  - 理由: 実行履歴の分離、競合回避、障害解析容易化のため

したがって、ファイル名規則は次で確定する。

- 定期実行: `YYYY-MM-DD.md`
- 手動実行: `YYYY-MM-DD_manual_01.md`, `YYYY-MM-DD_manual_02.md`, ...

---

## Q15. README 必須セクション確認をどのチェックが担当するか不明

**該当箇所:** §9.4.2、§10.4、§11

自己監視のチェック項目には「README.md の必須セクション存在」が含まれているが、`checks` 一覧には README 専用のチェック種別が存在しない。

- `config_valid` の責務に含めるのか
- `self_status` の一部として扱うのか
- 新しいチェック種別を追加するのか

を明確にしてほしい。また、必須セクションの正本が何項目かも確定したい。

**Answer:**

README 必須セクション確認は `self_status` の責務とする。`config_valid` は設定ファイルや Markdown の構文妥当性のみを担当し、内容要件までは見ない。

責務分離は以下。

- `config_valid`
  - YAML 構文妥当性
  - Markdown ファイル存在
  - 必須設定キーの有無
- `self_status`
  - README 必須セクション存在
  - 自己監視対象としての必要条件充足
  - 前回実行結果や日報整合性確認

README 必須セクションの正本は、`SPEC.md` §12 の 12 項目を正式要件とする。

---

## Q16. 親ポータルから「主要会社リンクへ到達可能」の判定元データが不明

**該当箇所:** §10.2、§9.5

親ポータル監視には「ポータルから主要会社リンクへ到達可能か」が含まれているが、何をもって「主要会社リンク」とするかが定義されていない。

- `companies.yaml` の `enabled: true` な各 `virtual_company.site` を正とするのか
- ポータル側 HTML に埋め込まれたリンク一覧を正とするのか
- 一部会社だけを対象にした allowlist を別途持つのか

が不明なため、「会社リンク漏れ」を検知すべきかどうかの判定基準が定まらない。

**Answer:**

正本は `companies.yaml` の `enabled: true` かつ `kind: virtual_company` の各エントリとする。

判定ルール:

- `companies.yaml` から監視対象会社一覧を取得する
- 各会社の `site` を期待リンク先として扱う
- 親ポータル HTML 内に、その URL または正規化後に同値なリンクが存在するか確認する
- リンクが存在し、到達可能であれば正常
- 会社が `enabled: true` なのに親ポータルにリンクが存在しない場合は異常とする

補助ルール:

- `site` 未設定の会社はこの判定対象外
- `enabled: false` の会社は対象外
- 将来、親ポータル非掲載会社を許容したい場合は `portal_visible: false` を追加可能とする

つまり、ポータル側 HTML が正本ではなく、`companies.yaml` が正本。親ポータルはその設定を満たしているかを検証される立場になる。

---

## Q17. スクリプト群の呼び出し構造・エントリポイントが不明

**該当箇所:** §8（ディレクトリ構成）、§12

`scripts/` 配下に以下が列挙されている。

- `check_targets.py`
- `analyze_incident.py`
- `generate_daily_report.py`
- `apply_countermeasure.py`
- `self_check.py`

しかし、これらが独立した CLI ツールなのか、単一エントリポイント（例: `main.py` や `runner.py`）から呼び出されるモジュールなのかが不明。

- GitHub Actions ワークフロー（`daily-guardian.yml`）はどのスクリプトを直接呼ぶのか？
- スクリプト間の結果受け渡しは、戻り値・ファイル・環境変数のどれか？
- 途中失敗時に `continue-on-error` で継続するのは GitHub Actions 側の設定か、Python 側の try/except か？

**Answer:**

初期版では **単一エントリポイント方式** とする。OpenClaw から直接起動するのは `scripts/check_targets.py` のみとし、他スクリプトは内部モジュールとして扱う。`sequence.md` の手動実行例 `python scripts/check_targets.py --trigger manual` を正本とする。

正式方針:

- OpenClaw cron 相当機構が直接呼ぶのは `scripts/check_targets.py`
- `check_targets.py` が orchestration を担当する
- 他スクリプトは `check_targets.py` から呼び出す

各スクリプトの責務:

- `check_targets.py`
  - 設定読込
  - 全対象巡回
  - 異常集約
  - incident / countermeasure / 日報生成の起点
  - push 起点
- `analyze_incident.py`
  - 異常分類
  - 原因候補整理
- `apply_countermeasure.py`
  - 低リスク自動対策の実行または提案生成
- `generate_daily_report.py`
  - 日報生成
- `self_check.py`
  - guardian 専用追加自己監視

結果受け渡し:

- スクリプト間の主な受け渡しは Python オブジェクト / 戻り値
- 永続化が必要なものだけ Markdown に保存する
- 環境変数経由の受け渡しは最小限とする

失敗時継続:

- 継続制御は Python 側で行う
- 1対象ごとに例外を吸収し、残り対象の巡回を継続する
- OpenClaw 側は単にエントリポイントを起動するだけとする

---

## Q18. 同一対象で複数チェックが失敗した場合のインシデント生成数が不明

**該当箇所:** §10.5、§12.2

例えば `auto-ai-blog` で `github_actions` と `site_http` の両方が失敗した場合、

- インシデントファイルは **1件**（対象まとめ）か **2件**（チェック種別ごと）か？
- slug の命名はチェック種別ごとに変わるのか、対象名だけで決まるのか？

**Answer:**

初期版では **1対象1実行あたり1インシデントファイル** を原則とする。同一対象で複数チェックが失敗しても、まずは対象単位で集約して 1 件にまとめる。`sequence.md` の「同一対象の複数失敗は1ファイルに集約」を正式ルールとする。

ルール:

- 例: `auto-ai-blog` で `github_actions` と `site_http` が両方失敗
- incident は 1 件
- 本文中に複数失敗項目を列挙する

slug 命名:

- slug は **主たる異常区分** を基準に決める
- 主たる異常の優先順位は以下とする
  1. `SITE_DOWN`
  2. `ACTION_FAILED`
  3. `ARTIFACT_MISSING`
  4. `DAILY_POST_MISSING`
  5. `ADSENSE_PAGE_MISSING`
  6. `KEYWORD_MISSING`
  7. `LINK_BROKEN`
  8. `UNKNOWN_ERROR`

例:

- `incidents/2026-03-10-auto-ai-blog-site-down.md`

例外:

- 原因が明らかに別系統なら分割してよい
- ただし初期版の原則は **まとめる** とする

---

## Q19. countermeasure を生成する条件・基準が不明

**該当箇所:** §10.6、§12.2

§12.2 では「再発防止策が必要なら countermeasure 追加」とあるが、「必要」の判断基準が定義されていない。

- 異常が発生すれば毎回 countermeasure を生成するのか？
- 初回発生のみ生成し、既存 CM と重複する場合はスキップするのか？
- 人間が判断して手動追加する運用なのか、自動生成するのか？

**Answer:**

countermeasure は **毎回自動生成しない**。`class.md` の `CountermeasureManager.should_create()` に合わせ、条件判定を通過した場合のみ生成する。

生成条件:

- 異常が再発可能性を持つ
- 既存 countermeasure に明確に対応するものがない
- 単なる一時失敗ではない
- 原因または対策候補がある程度整理できた
- 運用ナレッジとして残す価値がある

生成しない例:

- 一時的 timeout
- 一時的 502
- 原因不明で知識化の価値が低いもの
- 既存 CM をそのまま流用できるもの

生成する例:

- GitHub Actions の再発パターン
- 親ポータルから会社リンクが欠落
- AdSense 必須ページ欠落
- 前日投稿判定設定ミス
- `companies.yaml` の設定不足

既存 CM との重複判定:

- 初期版では簡易方式とする
- `countermeasures/` のタイトル / 発端障害を走査する
- 類似があれば新規作成せず既存参照にする
- 新規作成時も既存流用時も `related_countermeasure` を incident に記録する

---

## Q20. GitHub Actions ワークフロー `daily-guardian.yml` の具体的な job/step 構成が不明

**該当箇所:** §8、§10.1、§18.1

- ジョブ数は 1 つか複数か（チェック並列化の有無）
- Python 実行環境のバージョン・依存パッケージ管理方法（`requirements.txt` / `pyproject.toml` 等）
- 出力ファイル（日報・インシデント等）の git commit・push は自動で行うのか、それとも Actions の成果物（artifact）としてアップロードするだけか？

**Answer:**

現行仕様では実行基盤は GitHub Actions ではなく、**Windows 11 + WSL2 上の OpenClaw cron が主** である。したがって `daily-guardian.yml` は正本ではなく、あっても補助用途に留める。正式な日次実行フローは `sequence.md` と `usecase.md` の OpenClaw 起動を採用する。

正式方針:

- 主たる定期実行基盤: OpenClaw（WSL2 cron）
- 起動コマンド: `python scripts/check_targets.py`
- 手動実行: `python scripts/check_targets.py --trigger manual`

OpenClaw 側の論理 step:

1. CompanyGuardian リポジトリを最新化
2. Python 仮想環境を有効化
3. `scripts/check_targets.py` を実行
4. 生成された Markdown を `git add / commit / push`
5. push 失敗時はローカルログに記録し次回再試行

Python 実行環境:

- WSL2 Ubuntu 系
- Python 3.11 以上を推奨
- 依存管理は初期版では `requirements.txt` を正式採用

出力ファイルの扱い:

- `reports/daily/`
- `incidents/`
- `countermeasures/`

に生成された Markdown は、artifact upload ではなく **git commit / push** を正式採用する。このシステムの本質は「監視結果を履歴としてリポジトリに残すこと」なので、ここは push 前提で固定する。

---

## Q21. `self_check.py` と `check_targets.py` の責務分担が不明

**該当箇所:** §8、§10.3、§10.4

`self_check.py` と `check_targets.py` の両方が存在するが、自己監視（CompanyGuardian 自身のチェック）はどちらが担当するのか。

- `check_targets.py` が `kind: guardian` のエントリも含めて一律処理するのか
- `self_check.py` が guardian 専用の追加ロジックを持つのか
- `self_check.py` は `check_targets.py` の後に呼ばれるのか、それとも中から呼ばれるのか

**Answer:**

`check_targets.py` が **全体の司令塔**、`self_check.py` が **guardian 専用追加ロジック** を担当する。`class.md` の `CompanyGuardianRunner` が全体制御し、`SelfStatusChecker` が guardian 特有の確認を持つ構成に合わせて固定する。

責務分担:

- `check_targets.py`
  - 全対象を巡回する
  - `kind: portal / virtual_company / guardian` を共通枠組みで処理する
  - 各対象の基本チェックを実行する
  - 結果を集約する
- `self_check.py`
  - `kind: guardian` のうち CompanyGuardian 固有の追加自己監視を行う
  - `report_generated`
  - README 必須セクション確認
  - 直近定期日報との整合
  - 自己監視状態の整合確認
  - などを担当する

呼び出し順:

1. `check_targets.py` が `kind: guardian` を検出
2. 共通チェックを実行
3. `self_check.py` を呼び出す
4. 結果を統合する

つまり、`self_check.py` は単独起動の主役ではなく、guardian 用の専門ユニット。親分は `check_targets.py` とする。

---

## Q22. `daily_post_previous_day` の探索方法が未定義

**該当箇所:** `SPEC.md` §10.7、§11.1、§11.3、`sequence.md`

`daily_post_previous_day` は「前日分の日次投稿ページまたは成果物が存在するか確認」と定義されているが、会社ごとに前日投稿をどう見つけるかが仕様化されていない。

- URL の命名規則（例: `/posts/2026-03-09/`）で見るのか
- `feed.xml` / sitemap / トップページ一覧から前日記事を探すのか
- `required_artifacts` を日付付きテンプレートで指定するのか
- 会社ごとに別ルールを `companies.yaml` へ持てるのか

この定義がないと、会社ごとに実装を分岐させるしかなくなり、設定追加だけで新規会社を登録できるという要件と衝突する。

**Answer:**

`daily_post_previous_day` は、**会社ごとに設定可能な探索戦略を持つチェック** とする。初期版ではコードに会社名ベースの分岐をベタ書きせず、`companies.yaml` に探索方式を定義する。

追加設定項目:

- `daily_post_strategy`
- `daily_post_locator`

`daily_post_strategy` の許容値:

- `site_path_pattern`
- `feed_xml`
- `sitemap_xml`
- `index_page_keyword`

正式ルール:

- 会社ごとに 1 つ以上の探索戦略を定義できる
- 複数戦略を指定した場合は上から順に評価する
- 最初に「前日投稿あり」と判定できた時点で正常とする
- すべて失敗した場合は `DAILY_POST_MISSING`
- 戦略未指定の場合は `WARNING` とし、日報に記録するが即 `ERROR` にはしない
- 日付判定は JST 前日基準とする
- 会社ごとの差は設定で吸収し、Python 側に会社名ベースの分岐を書かない

各戦略の定義:

- `site_path_pattern` — 前日 JST の日付を埋め込んだ URL パターンで確認する。例: `/posts/{yyyy}/{mm}/{dd}/`
- `feed_xml` — `feed.xml` を読み、前日 JST の公開日を持つ `item` / `entry` が 1 件以上あるか確認する
- `sitemap_xml` — `sitemap.xml` を読み、前日 JST に対応する URL または更新日を持つエントリがあるか確認する
- `index_page_keyword` — トップページまたは指定一覧ページに、前日投稿のタイトル・日付・slug などの識別子が含まれるか確認する

推奨順位:

1. `feed_xml`
2. `sitemap_xml`
3. `site_path_pattern`
4. `index_page_keyword`

追加する `companies.yaml` 例:

```yaml
daily_post_strategy:
  - feed_xml
  - site_path_pattern

daily_post_locator:
  feed_url: /feed.xml
  path_pattern: /posts/{yyyy}/{mm}/{dd}/
  timezone: Asia/Tokyo
```

`sequence.md` の「前日分デイリー投稿パス確認」は、正式には「前日投稿探索戦略に基づく確認」に読み替える。

---

## Q23. `WARNING` の扱いが日報集計・incident 生成で未定義

**該当箇所:** `SPEC.md` §10.7、§11.5、§11.7、`class.md`

仕様上は `github_actions` の `in_progress` / `queued` / 履歴なしや `site_http` の 3xx が警告になり得るが、警告をどう扱うかが定義されていない。

- 日報の `対象総数` / `正常件数` / `異常件数` に `WARNING` をどう集計するのか
- `WARNING` でも incident を生成するのか
- 優先度表（High / Medium / Low）に `WARNING` をどう対応付けるのか
- `要対応一覧` に警告を含めるのか

`CheckStatus.WARNING` はクラス図に存在する一方、日報必須項目には警告件数の置き場がないため、集計ルールを明確化してほしい。

**Answer:**

`CheckStatus.WARNING` は、**正常でも異常でもない中間状態** とする。クラス図の `OK` / `WARNING` / `ERROR` に合わせ、日報・incident の扱いを以下で固定する。

正式ルール:

- `OK`: 正常
- `WARNING`: 要注意だが即障害とはしない
- `ERROR`: 異常

日報集計:

- 日報必須項目は `対象総数` / `ok_count` / `warning_count` / `error_count` / `要対応一覧` とする
- 現行の「正常件数・異常件数」だけではなく、`warning_count` を必須項目に追加する

incident 生成ルール:

- `ERROR`: 原則 incident 作成対象
- `WARNING`: 原則 incident は作成しない
- ただし同一対象で複数 `WARNING` が重なり、運用上の対応が必要と判断された場合は任意で incident 化してよい

要対応一覧:

- `WARNING` は `要対応一覧` に載せる。severity は `warning`
- `ERROR` も `要対応一覧` に載せる。severity は `error`

countermeasure 生成:

- `WARNING` 単独では原則生成しない
- 同一 `WARNING` が継続・反復し、運用知識として価値がある場合のみ生成対象とする

例:

- `github_actions = in_progress` → `WARNING`。incident は作らないが、日報の `要対応一覧` には載せる
- workflow history not found → 原則 `WARNING`。何日も続く場合は incident 化を検討する

---

## Q24. AdSense スニペットの管理方法と監視範囲が不明

**該当箇所:** `SPEC.md` §1、§11.8、§18

文書冒頭では AdSense の script タグをそのまま記載し「各ページに入れておくこと」とある一方、§11.8 では「必要に応じて AdSense スニペット存在確認用キーワード検査」となっており、§18 では AdSense コードの平文ハードコードを避けるとしている。

- CompanyGuardian が監視するのは「必須ページの存在」だけか、「AdSense スニペットの埋め込み有無」まで含むのか
- スニペット確認を行う場合、全ページ対象かトップページなど代表ページのみか
- 判定は完全一致の script タグ比較か、`ca-pub-...` のようなキーワード確認か
- 文書中の script タグは実装必須値なのか、参考例なのか

監視対象と設定方法が決まっていないと、実装の厳しさと誤検知率が大きく変わる。

**Answer:**

AdSense 監視は、**広告配信の継続に必要な公開要件の確認** に限定する。生の script タグ文字列一致を必須条件にはしない。

初期版で監視対象にするもの:

- `required_adsense_pages` の存在
  - `/privacy-policy/`
  - `/contact/`
- 収益化対象ページの公開状態
- 重大な内部リンク切れがないこと
- 必要に応じて、AdSense 実装済みを示す抽象的なキーワードまたはテンプレートマーカーの存在確認

初期版で監視対象にしないもの:

- 生の `<script ... adsbygoogle.js ...>` 完全文字列一致
- `ca-pub-...` の生値一致
- AdSense 管理画面上の配信結果
- 審査通過そのもの

正式仕様:

- `adsense_pages` チェックは 2 層に分ける
  - 必須: 公開導線・必須ページの存在確認
  - 任意: `adsense_marker_keyword` による実装痕跡確認
- 追加設定項目は `adsense_marker_keyword`
  - 例: `adsbygoogle`, `adsense-enabled`, `google-ads-slot`
- 必須ページ欠落は `ERROR`（`ADSENSE_PAGE_MISSING`）
- マーカー欠落は初期版では `WARNING`
- script 文字列そのものは監視条件にしない

これにより、「AdSense 必須」「監視対象はある」「でも client ID を仕様書にベタ書き必須にはしない」を両立させる。

---

## Q25. `artifact` の初期版サポート範囲が文書間で一致していない

**該当箇所:** `SPEC.md` §10.5、§10.7、`sequence.md`、`usecase.md`、`QandA.md` Q5

`SPEC.md` では `required_artifacts` に `site_path` / `repo_path` / `workflow_artifact` を定義しているが、図では `artifact` が公開サイト上のパス確認としてのみ表現されている。また Q5 では `repo_path` と `workflow_artifact` を将来拡張寄りに説明しており、初期版の実装範囲が読み取れない。

- 初期版で必須なのは `site_path` のみか、3 種すべてか
- `repo_path` はローカル clone を見るのか GitHub Contents API を見るのか
- `workflow_artifact` は Actions artifact API を叩くのか、成果物名だけを論理的に扱うのか
- 受け入れ条件で `artifact` 動作確認が必要な型はどれか

ここが曖昧だと、チェック実装の難易度と必要な認証権限が大きく変わる。

**Answer:**

`artifact` は仕様上 `site_path` / `repo_path` / `workflow_artifact` を定義するが、**初期版の実装必須範囲は `site_path` のみ** とする。`repo_path` と `workflow_artifact` は、仕様定義済みだが実装は将来拡張と位置付ける。

正式方針:

- 仕様レベルでは 3 種を保持する
  - `site_path`
  - `repo_path`
  - `workflow_artifact`
- 初期版の受け入れ条件に入れるのは `site_path` の存在確認のみ
- `repo_path` と `workflow_artifact` は、パース可能であればよい
- 未実装なら `WARNING` を返してスキップしてよい

判定ルール:

- `site_path`
  - 実装必須
  - 未存在なら `ERROR`（`ARTIFACT_MISSING`）
- `repo_path`
  - 初期版では任意実装
  - 未サポートなら `WARNING`
- `workflow_artifact`
  - 初期版では任意実装
  - 未サポートなら `WARNING`

日報上の扱い:

- 未サポート型を指定していた場合は、「設定はあるが初期版未サポート」として warning に載せる
- `site_path` 欠落は error に載せる

仕様追記文:

- 「初期版で実装必須の artifact は `type: site_path` のみとする」
- 「`type: repo_path` および `type: workflow_artifact` は将来拡張対象とし、指定されていても初期版では warning 扱いでスキップ可能とする」

これにより、`SPEC.md` の定義と `sequence.md` / `usecase.md` の表現を両立できる。図は初期版の実装範囲だけを描いている、と解釈できるようになる。

---

## Q26. `ConfigLoader.load()` と `validate()` の責務境界が不明

**該当箇所:** `class.md` の `ConfigLoader`、`tests/test_config_loader.py`

クラス図では `ConfigLoader` が「load + validate」を持ち、テスト冒頭コメントでも「必須フィールドの検証を行う」とある。一方、テストケースは `id` や `kind` が欠けた YAML でも `load()` 自体は通し、その後 `validate()` が `False` を返す前提になっている。

- `load()` は「構文解析と型変換のみ」を担当し、必須項目エラーは `validate()` に集約する想定か
- それとも `load()` の時点で必須項目欠落を例外にすべきか
- `kind` や `checks` の未知値も `load()` で弾くのか、`validate()` / 実行時警告に回すのか

ここが未確定だと、例外設計とテスト粒度がぶれる。

---

## Q27. `top_page_keyword` 実行時に `required_keywords` が空の場合の正式挙動が不明

**該当箇所:** `SPEC.md` §10.7、`tests/test_checkers.py`

仕様では `top_page_keyword` は「`required_keywords` の全要素が含まれることを確認」とあるが、`required_keywords` が空配列のときの扱いが書かれていない。テストケースも `OK` / `WARNING` のどちらでも通る書き方になっている。

- 空配列は「検査対象なし」として `WARNING` にするのか
- 空配列でも全要素充足とみなし `OK` にするのか
- そもそも `top_page_keyword` を設定しているのに `required_keywords` が空なら設定不備として `CONFIG_INVALID` にするのか

正式ルールを決めたい。

---

## Q28. `daily_post_previous_day` の locator 不備をどう判定するかが不明

**該当箇所:** `SPEC.md` §10.8、`tests/test_checkers.py`

`daily_post_previous_day` は戦略ベースになったが、各戦略に必要な locator 値が欠けていた場合の扱いが定義されていない。

例:

- `feed_xml` なのに `feed_url` がない
- `site_path_pattern` なのに `path_pattern` がない
- `index_page_keyword` なのに `index_url` や `keyword_pattern` がない
- `timezone` 未指定時に既定値を使うのか

確認したい点:

- locator 不備は `WARNING` でその戦略だけスキップか
- `ERROR` / `CONFIG_INVALID` として対象全体を失敗にするのか
- 複数戦略のうち 1 つだけ設定不備でも、残り戦略が成功すれば `OK` にしてよいのか

---

## Q29. `report_generated` の初回定期実行時の扱いが不明

**該当箇所:** `SPEC.md` §10.7、§11.1、`tests/test_checkers.py`

`report_generated` は「前回定期実行分の日報」を確認する前提になったが、導入初日や初回定期実行では比較対象の日報が存在しない。

- 初回だけは `WARNING` に留めるのか
- 常に `ERROR`（`REPORT_MISSING`）にするのか
- 初回判定用の猶予条件や bootstrap フラグを設けるのか

このルールがないと、初回導入時に自己監視が必ず失敗する可能性がある。

---

## Q30. 日報の集計単位が「対象」なのか「チェック結果」なのか不明

**該当箇所:** `SPEC.md` §10.9、§11.7、`class.md`、`tests/test_daily_report_generator.py`

日報必須項目に `対象総数` / `ok_count` / `warning_count` / `error_count` があるが、テストケースは `CheckResult` 件数ベースで集計する前提になっている。一方、文言上は「対象総数」なので会社数ベースにも読める。

- `total_count` は会社数か、全 `CheckResult` 件数か
- `ok_count` / `warning_count` / `error_count` は対象単位の最終ステータス件数か、チェック件数か
- `要対応一覧` は対象ごとに 1 行へ集約するのか、失敗したチェックごとに列挙するのか

ここが決まらないと、日報生成テストの期待値が定まらない。

---

## Q31. `config_valid` が確認すべき Markdown ファイルの範囲が不明

**該当箇所:** `SPEC.md` §10.7、§11.4、`tests/test_checkers.py`

`config_valid` は「必須設定ファイルが YAML/Markdown として構文妥当」とされているが、どの Markdown を対象に含めるかが明確でない。現行テストは `companies.yaml` しか見ていない。

- `README.md` は `config_valid` の対象か、それとも `self_status` だけで見るのか
- `SPEC.md` / `QandA.md` / `usecase.md` / `class.md` / `sequence.md` も必須ファイルとして検証対象に入るのか
- Markdown は「存在確認のみ」か、「見出し構造など最低限の内容妥当性」まで見るのか

自己監視と設定妥当性確認の責務分担を固めたい。

---

## Q32. 「既存バーチャルカンパニー」の棚卸し元データが不明

**該当箇所:** `SPEC.md` §3.1、§10.2、`QandA.md` Q16

今回のレビューでは、公開ポートフォリオ上には 10 件のバーチャルカンパニーが並んでおり、`companies.yaml` も同じ 10 件を持っている。一方、GitHub 公開リポジトリ一覧には `writer2` など、`companies.yaml` に未登録の候補も存在する。

- 初期登録・棚卸し時の正本は `companies.yaml` / 親ポータル / ポートフォリオページ / GitHub リポジトリ一覧のどれか
- 「既存バーチャルカンパニー」に含める判定基準は、公開導線の有無なのか、リポジトリの存在なのか、運用中フラグなのか
- 公開 repo はあるがポートフォリオ未掲載のもの（例: `writer2`）を監視対象に含めるのか

ここが未定だと、「全件追加できているか」の判定自体が揺れる。

**Answer:**

初期版における監視対象の正本は `companies.yaml` とする。親ポータル、ポートフォリオページ、GitHub リポジトリ一覧は照合元・発見元ではあるが、監視対象の正式一覧そのものではない。

正式ルール:

- 監視対象の正本: `companies.yaml`
- 公開導線の照合元: 親ポータル / ポートフォリオページ
- 候補発見用の参考元: GitHub 公開リポジトリ一覧

判定基準:

- 「既存バーチャルカンパニー」に含める条件は、初期版では以下のいずれかを満たし、かつ `companies.yaml` に登録されているものとする
- 運用中として扱う意思がある
- 公開サイトまたは監視対象 repo を持つ
- `enabled: true` または将来監視候補として明示されている

重要な考え方:

- GitHub に repo があるだけでは、即監視対象にはしない
- 親ポータルに載っているだけでも、正本登録なしでは正式監視対象にしない
- 最終的に CompanyGuardian が見るのは `companies.yaml` とする

`writer2` の扱い:

- `writer2` のように GitHub 上には存在しても `companies.yaml` にないものは、初期版では **未登録候補** とする
- 自動的に既存会社扱いにはしない

補助運用:

- 将来の棚卸しを楽にするため、差分確認用に以下のレポートを出してよい
- `companies.yaml` にあるがポートフォリオにない
- ポートフォリオにあるが `companies.yaml` にない
- GitHub repo にあるが `companies.yaml` にない

ただし、これらは **発見レポート** であり、正式な監視対象追加ではない。

---

## Q33. 会社 URL の「正規化後に同値」の範囲が不明

**該当箇所:** `SPEC.md` §10.2、`QandA.md` Q16

Q16 では、親ポータル上のリンク確認は「`companies.yaml` の URL または正規化後に同値なら可」とされている。しかし、何を同値とみなすかが未定義。

今回の実データでも、以下の差分がある。

- `https://garyohosu.github.io/AI-Broker/` と `https://garyohosu.github.io/ai-broker/`
- `https://garyohosu.github.io/WebGame/` と `https://garyohosu.github.io/webgame/`
- `https://garyohosu.github.io/Writer/` と `https://garyohosu.github.io/writer/`
- `https://garyohosu.github.io/OpenClaw-Blog/` と `https://garyohosu.github.io/OpenClawBlog/`
- `https://hantani-portfolio.pages.dev/` と `https://garyohosu.github.io/auto-ai-blog/`

確認したい点:

- パスの大文字小文字差だけなら同値とみなしてよいか
- `index.html` の有無、末尾 `/` の有無は同値か
- ホスト自体が変わっている場合（Cloudflare Pages → GitHub Pages、独自/別ドメイン移転）は同値扱いにできるか
- 同値でない場合、親ポータル不整合として `LINK_BROKEN` にするのか、設定更新待ちとして `WARNING` にするのか

この基準がないと、実運用で「設定ずれ」と「本当のリンク欠落」を切り分けられない。

**Answer:**

初期版では URL 同値判定を **保守的な正規化** に限定する。つまり、表記ゆれは吸収するが、ホスト変更や大きなパス変更は同値とみなさない。

同値とみなしてよいもの:

- スキーム差
- `http` と `https`
- ただし最終的な到達先が同じであること
- 末尾スラッシュの有無
- `/writer` と `/writer/`
- `index.html` の有無
- `/writer/` と `/writer/index.html`
- ホスト名の大小文字差
- パスの大文字小文字差のみ
- 例: `/AI-Broker/` と `/ai-broker/`
- ただし実到達先が同一であることを条件にする

同値とみなさないもの:

- ホストが異なる
- `hantani-portfolio.pages.dev` と `garyohosu.github.io`
- パス名自体が別物
- `/OpenClaw-Blog/` と `/OpenClawBlog/`
- 別サービス別サイトへの移転
- クエリ文字列違いで実体が変わるもの

判定ルール:

- 軽微な表記ゆれだけなら正常
- ホスト違い・別名パスは原則として設定不整合候補とする

ステータス:

- 親ポータルに記載された URL が、`companies.yaml` と保守的正規化で一致しない場合は、まず `WARNING` とする
- 区分は `PORTAL_LINK_MISMATCH` のような warning 系でよい
- 実際にリンク先が 404 / 到達不可なら `ERROR`（`LINK_BROKEN`）

理由:

- ここを即 `ERROR` にすると、「移転したが設定更新忘れ」と「本当にリンクが壊れている」が区別できない
- だから初期版では、同値ではないが到達する場合は `WARNING`、到達もしない場合は `ERROR` で切り分ける

補足:

- `hantani-portfolio.pages.dev` と `garyohosu.github.io/auto-ai-blog/` のようなホスト違いは、初期版では同値扱いしない
- これは「移転先更新が必要な別 URL」とみなす
- ホスト違い・別名パスは原則同値とみなさず、到達可能なら warning、到達不能なら error とする

---

## Q34. 外部ホスティングまたは非公開リポジトリ会社の `github_actions` 要件が不明

**該当箇所:** `SPEC.md` §10.3、§10.4、`QandA.md` Q3、Q6

公開ポートフォリオ上では `MagicBoxAI` が `https://garyo.sakura.ne.jp/magicboxai/` に公開されている一方、GitHub 公開リポジトリ一覧には `MagicBoxAI` が見当たらない。現行設定では `repo: garyohosu/MagicBoxAI` と `github_actions` チェックが入っている。

- 外部ホスティング会社で、GitHub repo が private または非公開一覧に出ない場合でも `github_actions` を必須にするのか
- private repo を監視する前提なら、`repo` 設定だけでよいのか、それとも `visibility` や `auth_required` のような明示フラグが必要か
- GitHub Actions を使わない会社は `site_http` のみで正常運用とみなしてよいか

ここを決めないと、会社追加時に「repo 不達が設定不備なのか、意図した private 運用なのか」が判定できない。

**Answer:**

初期版では、`github_actions` は全会社の必須要件ではない。会社ごとに `checks` で選択する **任意チェック** とする。

正式ルール:

- `github_actions` を使う会社は、`checks` に `github_actions` を入れる
- GitHub Actions を使わない会社は、`checks` に入れなければよい
- 外部ホスティング会社でも、GitHub Actions を使っていれば監視可能
- 外部ホスティング会社で GitHub Actions を使わないなら、`site_http` などだけで正常運用とみなしてよい

private repo の扱い:

- private repo を監視対象に含めること自体は許容する
- ただし、その場合は認証前提であることを設定に明示する

追加設定項目:

- `repo_visibility`
- `public`
- `private`
- `unknown`
- `github_auth_required`
- `true`
- `false`

判定ルール:

- `checks` に `github_actions` がない場合は、repo 到達不能でも異常にしない
- `checks` に `github_actions` がある場合は、`repo` は必須
- private repo の場合は認証情報が必要
- private repo で認証がない場合、初期版では `WARNING`
- 区分は `GITHUB_AUTH_REQUIRED`
- public repo のはずなのに存在確認できない場合は `ERROR` 候補
- GitHub Actions 非採用会社は、`site_http` / `artifact` / `daily_post_previous_day` 等だけで正常運用可

`MagicBoxAI` のようなケース:

- 公開先が `sakura.ne.jp`
- GitHub 公開 repo が見当たらない
- でも運用上は存在している
- この場合、初期版では `checks` から `github_actions` を外す
- または `repo_visibility: private` と `github_auth_required: true` を明示する

正式方針:

- 「GitHub にあるはず」ではなく、「その会社が何で運用されているかを `companies.yaml` に書く」
- CompanyGuardian は推理ゲームではなく、設定された運用形態を検証する仕組みにする

この 3 問を踏まえた追加ルール:

- 監視対象一覧の正本は `companies.yaml` とする
- 親ポータル、ポートフォリオ、GitHub repo 一覧は照合・発見用の参考元とする
- 軽微な表記ゆれは正規化で吸収する
- ホスト違い・別名パスは原則同値とみなさず、到達可能なら warning、到達不能なら error とする
- `github_actions` は会社ごとの任意チェックとし、全会社必須ではない
- private repo / 外部ホスティングは設定で明示する
