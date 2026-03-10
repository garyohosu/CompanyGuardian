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

を明確にしてほしい。また、必須セクションの正本は §11 の9項目でよいかも確定したい。

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

README 必須セクションの正本は、§11 の 9 項目を正式要件とする。

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
