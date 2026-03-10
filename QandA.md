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
- `link_health` — トップページまたは指定領域から抽出した主要リンクに対して HTTP HEAD または GET を行い、4xx/5xx を異常とする。
- `github_actions` — 指定 repo の直近実行状態を確認する。判定ルールは Q6 に従う。
- `artifact` — `required_artifacts` に定義された成果物の存在を確認する。定義方法は Q5 に従う。
- `report_generated` — 当日の日報ファイルが所定パスに生成されていることを確認する。
- `config_valid` — `companies.yaml` など必須設定ファイルが YAML/Markdown として構文妥当であることを確認する。
- `self_status` — CompanyGuardian 自身の前回実行結果・自己監視状態・必須出力有無を確認する。

未知の種別が指定された場合は、警告を日報に記録してその項目のみスキップとする。全体実行は止めない。

---

## Q2. `required_paths` はサイト URL パスかリポジトリ内パスか

**該当箇所:** §9.4

**Answer:**

初期版では **(A) サイト URL 配下のパス** とする。
`site: https://example.com` に対して `required_paths: ["/about/", "/feed.xml"]` のように指定し、`<site><path>` を HTTP 確認する。

リポジトリ内ファイル確認は別概念なので混在させない。将来拡張する場合は以下を追加する。

- `required_paths` — サイト URL パス（初期版）
- `required_repo_paths` — リポジトリ内パス（将来拡張、初期版は未実装）

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
