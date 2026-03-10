# SPEC.md

## 1. 文書情報

- プロジェクト名: CompanyGuardian
- 種別: バーチャルカンパニー群の監視・障害対応・日報・再発防止ナレッジ蓄積システム
- 目的: 複数のバーチャルカンパニーと親ポータルを毎日巡回し、異常を検知した場合は原因分析・対策・記録まで行う
- 想定運用環境: GitHub Actions を中心とした日次実行
- リポジトリ名: `CompanyGuardian`

---

## 2. 背景

ユーザーは複数のバーチャルカンパニーを GitHub Pages / GitHub Actions / AI エージェントで運用している。  
個別プロジェクトの数が増えたため、最低でも 1 日 1 回は全体状態を確認し、異常があれば原因と対策を整理し、結果を日報として残す仕組みが必要になった。

CompanyGuardian は単なる監視ツールではなく、以下を行う統合運用リポジトリである。

- 親ポータルの監視
- 各バーチャルカンパニーの監視
- 自分自身の自己監視
- 異常の原因分析
- 対策実施
- 日報生成
- 再発防止策のナレッジ化

---

## 3. スコープ

### 3.1 対象

本システムは以下を対象とする。

1. 親ポータル
   - `https://garyohosu.github.io/`
2. 各バーチャルカンパニー
   - Auto AI Blog
   - MagicBoxAI
   - AITecBlog
   - AI-Broker
   - WebGame
   - WomensMagazine
   - AozoraDailyTranslations
   - WorldClassicsJP
   - Writer
   - OpenClaw Blog
3. 監視役自身
   - CompanyGuardian

### 3.2 目的外

以下は初期スコープ外とする。

- 本番サーバーへの直接ログイン操作
- 人手承認を要する外部有料サービス変更
- GitHub 以外の CI/CD への広範対応
- 高度な障害予測 AI モデルの実装
- Slack / Telegram / Email 通知の本格実装
  - 将来拡張候補とする

---

## 4. ゴール

CompanyGuardian は、毎日 1 回以上の自動巡回で次を実現する。

1. 監視対象一覧を設定ファイルから読み込める
2. 新しいバーチャルカンパニーを設定追加だけで登録できる
3. 親ポータル・個別会社・自分自身を同じ仕組みで巡回できる
4. 異常を検出したら結果を記録できる
5. 原因・対策・結果を日報に残せる
6. 再発防止策を独自名付き Markdown として保存できる
7. README.md に運用ルールと参照先を明記できる
8. CompanyGuardian 自身の失敗も検知対象に含める

---

## 5. 非ゴール

- 完全自律であらゆる障害を修復すること
- すべての障害原因を AI が 100% 正確に特定すること
- 外部 API の契約や権限設定まで自動変更すること
- ノーエラーを保証すること

---

## 6. 基本コンセプト

CompanyGuardian は「監視」「解析」「対策」「記録」「再発防止」の 5 役を持つ。

### 6.1 監視
- サイト死活
- GitHub Actions 実行結果
- 必須成果物の有無
- 主要リンク整合性
- 自己監視

### 6.2 解析
- 異常内容の分類
- 原因候補の抽出
- 再現条件の確認
- 影響範囲の整理

### 6.3 対策
- 再実行可能なワークフローの再試行
- 設定不備の修正案整理
- リンク切れ是正
- 生成漏れ補完案の提示

### 6.4 記録
- インシデント記録
- 日報生成
- 対策履歴記録

### 6.5 再発防止
- 独自名を付けた countermeasure Markdown を保存
- README から参照可能にする
- 次回以降の運用フローに反映する

---

## 7. 想定アーキテクチャ

```text
GitHub Actions (daily schedule / manual dispatch)
        |
        v
CompanyGuardian Runner
        |
        +-- companies/companies.yaml を読込
        |
        +-- Root Portal を確認
        +-- Virtual Companies を順次確認
        +-- CompanyGuardian 自身を確認
        |
        +-- incidents/ に個別記録出力
        +-- countermeasures/ に再発防止策出力
        +-- reports/daily/YYYY-MM-DD.md に日報出力
```

---

## 8. ディレクトリ構成

```text
CompanyGuardian/
├─ README.md
├─ SPEC.md
├─ companies/
│  └─ companies.yaml
├─ reports/
│  └─ daily/
│     └─ YYYY-MM-DD.md
├─ incidents/
│  └─ YYYY-MM-DD-<target>-<slug>.md
├─ countermeasures/
│  └─ CM-XXX_<Name>.md
├─ scripts/
│  ├─ check_targets.py
│  ├─ analyze_incident.py
│  ├─ generate_daily_report.py
│  ├─ apply_countermeasure.py
│  └─ self_check.py
├─ templates/
│  ├─ daily_report_template.md
│  ├─ incident_template.md
│  └─ countermeasure_template.md
└─ .github/
   └─ workflows/
      └─ daily-guardian.yml
```

---

## 9. 設定ファイル仕様

### 9.1 ファイル名
`companies/companies.yaml`

### 9.2 目的
監視対象の追加・無効化を設定変更だけで行えるようにする。

### 9.3 必須項目

- `id`: 一意な識別子
- `name`: 表示名
- `kind`: `portal` / `virtual_company` / `guardian`
- `enabled`: true/false
- `checks`: 実行するチェック一覧

### 9.4 任意項目

- `site`: 対象サイト URL（公開ページを持たない場合は省略可）
- `repo`: GitHub リポジトリ名
- `workflow`: GitHub Actions ワークフロー名（`github_actions` チェック時は明示推奨）
- `required_keywords`: トップページにあるべき文字列一覧（`top_page_keyword` チェック時に使用）
- `required_paths`: 公開サイト上の必須パス簡易記法（後方互換用）。内部では `required_artifacts` の `type: site_path` に正規化する
- `required_artifacts`: 必須成果物の定義一覧（`artifact` チェック時に使用。新規定義は原則こちらを使用）
- `link_targets`: `link_health` チェック時に明示確認するリンク URL 一覧
- `self_monitor`: 自己監視対象か
- `notes`: 補足説明

### 9.4.1 `required_artifacts` の形式

各要素は `type` フィールドで種別を指定する。

| type | 意味 | 例 |
|------|------|----|
| `site_path` | 公開サイト上の必須パス（初期版対応） | `/index.html`, `/feed.xml` |
| `repo_path` | リポジトリ内必須ファイル（将来拡張） | `README.md`, `data/latest.json` |
| `workflow_artifact` | GitHub Actions 実行物（将来拡張） | `site-build` |

初期版では `required_artifacts` を正とする。
`required_paths` は後方互換の簡易記法として許容し、内部では `type: site_path` に正規化して扱う。
両方が指定された場合はマージし、重複パスは排除する。

### 9.4.2 利用可能な `checks` 種別

| 種別 | 判定条件 |
|------|----------|
| `site_http` | HTTP GET で 2xx → 正常、3xx → 警告、4xx/5xx → 異常 |
| `top_page_keyword` | `required_keywords` の全要素がトップページ本文に含まれる → 正常、1つでも欠落 → 異常 |
| `link_health` | 範囲限定型。`portal` は同一オリジン内リンク + `enabled: true` な各 `virtual_company.site` + `link_targets`、`virtual_company` は同一オリジン内の主要導線のみ（深さ1）。4xx/5xx → 異常 |
| `github_actions` | 直近1回の実行結果を確認（判定詳細は §10.3 参照） |
| `artifact` | `required_artifacts` で定義された成果物の存在確認 |
| `report_generated` | 直近の完了対象日の日報ファイルが所定パスに存在する → 正常（定期実行時は前回定期実行分、手動実行時は直近の定期実行分） |
| `config_valid` | 必須設定ファイルが YAML/Markdown として構文妥当で、必須設定キーを満たす → 正常 |
| `self_status` | CompanyGuardian 自身の前回実行結果、README 必須セクション、自己監視要件、直近定期日報との整合を確認 |

未知の種別が指定された場合は、警告を日報に記録してその項目のみスキップする。全体実行は止めない。
日次判定基準は §10.1 に従い、Action の実行状態確認は当日基準、日報・日次成果物の存在確認は前日基準とする。

### 9.5 サンプル

```yaml
companies:
  - id: root-portal
    name: Root Portal
    kind: portal
    site: https://garyohosu.github.io/
    enabled: true
    checks:
      - site_http
      - top_page_keyword
      - link_health

  - id: auto-ai-blog
    name: Auto AI Blog
    kind: virtual_company
    repo: garyohosu/auto-ai-blog
    site: https://hantani-portfolio.pages.dev/   # Cloudflare Pages（GitHub Pages 以外も許容）
    workflow: deploy.yml
    enabled: true
    checks:
      - github_actions
      - site_http
      - artifact
    required_artifacts:
      - type: site_path
        path: /index.html

  - id: company-guardian
    name: CompanyGuardian
    kind: guardian
    repo: garyohosu/CompanyGuardian
    # site は公開ページを持たない場合は省略可
    enabled: true
    self_monitor: true
    checks:
      - github_actions
      - report_generated
      - config_valid
      - self_status
```

---

## 10. 機能要件

## 10.1 日次巡回

### 要件
- 1 日 1 回、全監視対象を順次確認する
- 手動実行も可能とする
- 途中失敗しても可能な限り残り対象の確認を継続する

### スケジュール
- cron: `0 21 * * *`（UTC 21:00 = JST 06:00）
- 日付判定と日報ファイル名の基準日は **JST** とする
- 手動実行（`workflow_dispatch`）時も日報を生成する
- 定期実行の出力先は `reports/daily/YYYY-MM-DD.md`
- 手動実行の出力先は `reports/daily/YYYY-MM-DD_manual_XX.md`（`XX` は `01` からの連番）
- 初期版では既存日報への追記更新は行わない

### 日次判定基準
- GitHub Actions などの実行状態確認は当日基準
- デイリー投稿、日報、日次成果物の存在確認は前日基準
- 例: `2026-03-10 JST 06:00` 実行時は、Actions は `2026-03-10` 時点の最新実行、日報や日次成果物は `2026-03-09` 分を確認する

### 入力
- `companies.yaml`

### 出力
- 実行ログ
- 日報 Markdown（定期実行: `reports/daily/YYYY-MM-DD.md` / 手動実行: `reports/daily/YYYY-MM-DD_manual_XX.md`、JST 基準）
- 必要に応じた incident / countermeasure Markdown

---

## 10.2 親ポータル監視

### 対象
- `https://garyohosu.github.io/`

### チェック項目
- HTTP ステータス
- トップページ取得可否
- 想定キーワードの有無
- 主要リンクの健全性
- ポータルから主要会社リンクへ到達可能か

### `link_health` の対象範囲
- 同一オリジン内リンク
- `companies.yaml` に定義された `enabled: true` かつ `kind: virtual_company` の各 `site`
- 明示的に `link_targets` で指定されたリンク

### 除外対象
- SNS
- 広告
- analytics
- 外部 CDN
- 外部ブログやニュース記事リンク
- クエリ付きトラッキングリンク

### 主要会社リンク判定ルール
- 正本は `companies.yaml` の `enabled: true` かつ `kind: virtual_company` の各エントリとする
- 各会社の `site` を期待リンク先として扱う
- 親ポータル HTML 内に、その URL または正規化後に同値なリンクが存在するか確認する
- リンクが存在し、到達可能であれば正常
- `site` 未設定の会社は対象外
- `enabled: false` の会社は対象外
- 将来、親ポータル非掲載会社を許容したい場合は `portal_visible: false` の追加で拡張する

### 異常例
- 404 / 500
- トップページ内容欠損
- 主要リンク切れ
- 表示崩れを示唆する異常な HTML 欠落

---

## 10.3 各バーチャルカンパニー監視

### チェック項目
- GitHub Actions の直近実行成功/失敗
- 公開サイトの HTTP 応答（ホスティング方式を問わない）
- 必須成果物の生成有無（`required_artifacts` で定義。`required_paths` は内部的に `type: site_path` へ正規化する）
- 必要に応じトップページキーワード確認

日次判定基準は §10.1 に従う。

### GitHub Actions 判定ルール
- 参照対象: `workflow` で指定したワークフローの**最新1回**（未指定の場合はリポジトリの最新1回）
- `success` → 正常
- `failure` / `cancelled` / `timed_out` / `action_required` → 異常（`ACTION_FAILED`）
- `in_progress` / `queued` → 警告
- 実行履歴が存在しない → 警告

### 異常分類例
- `ACTION_FAILED`
- `SITE_DOWN`
- `ARTIFACT_MISSING`
- `KEYWORD_MISSING`
- `LINK_BROKEN`

---

## 10.4 自己監視

### 対象
- CompanyGuardian 自身

### チェック項目
- 前回スケジュール実行成功
- 直近の定期実行分の日報存在
- `companies.yaml` の妥当性
- README.md の必須セクション存在（§11 の 9 項目）
- 前回の自己監視結果が直近の定期日報に記録されていること

### 判定補足
- `report_generated` は当日分ではなく、直近の定期実行分の日報を確認する
- 手動実行時も `report_generated` の確認対象は直近の定期実行分とする
- `config_valid` は YAML/Markdown の構文妥当性、ファイル存在、必須設定キーの有無を確認する
- README 必須セクション存在や自己監視要件の充足確認は `self_status` が担当する

### 重要ルール
- 自己異常は高優先度とする
- 自己異常発生時も、可能な範囲で他対象の確認を継続する
- 自己修復不可の場合、その旨を日報の先頭に記載する

---

## 10.5 インシデント記録

### 目的
異常検出時の事実・原因・対策・結果を個別記録として残す。

### 出力先
`incidents/YYYY-MM-DD-<target>-<slug>.md`

### 必須項目
- 発生日
- 対象名
- 異常区分
- 現象
- 影響範囲
- 原因
- 応急対策
- 恒久対策候補
- 結果
- 関連 countermeasure

---

## 10.6 再発防止策の保存

### 目的
似た障害が再発した際に、過去対策を即座に参照できるようにする。

### 出力先
`countermeasures/CM-XXX_<Name>.md`

### 命名ルール
- 連番: `CM-001`, `CM-002` ...（スクリプトが `countermeasures/` 配下を走査して自動採番）
- 独自名: 英単語または CamelCase 推奨
- 並行実行時の重複を避けるため、日次実行は原則1ジョブのみとする

### 命名例
- `CM-001_GhostRetry.md`
- `CM-002_SilentRollback.md`
- `CM-003_BrokenLinkGuard.md`
- `CM-004_ActionRevive.md`
- `CM-005_PublishShield.md`

### 必須項目
- 対策ID
- 対策名
- 発端となった障害
- 適用条件
- 手順
- 確認方法
- 効果
- 注意点

---

## 10.7 日報生成

### 目的
1 回の巡回結果を 1 ファイルに集約する。

### 出力先
- 定期実行: `reports/daily/YYYY-MM-DD.md`
- 手動実行: `reports/daily/YYYY-MM-DD_manual_XX.md`
- 初期版では既存ファイルへの追記更新は行わない

### 必須項目
- 実行日時
- 対象総数
- 正常件数
- 異常件数
- 要対応一覧
- 実施した対策一覧
- 新規 countermeasure 一覧
- 自己監視結果
- 総括

### 望ましい性質
- 人が読んで状況把握しやすい
- 後で時系列追跡しやすい
- README から参照しやすい

---

## 11. README.md 要件

README.md には最低限以下を記載する。

1. CompanyGuardian の目的
2. 監視対象カテゴリ
3. 実行方法
4. 日報の保存先
5. インシデント記録の保存先
6. 再発防止策の保存先
7. 新しい会社の追加方法
8. CompanyGuardian 自身も監視対象であること
9. 障害時は `countermeasures/` を読めと明記すること

### 記載例
- 障害対応時は `countermeasures/` 配下の Markdown を参照すること
- 新規の再発防止策を追加した場合は、README の参照ルールに従って保存すること

---

## 12. 運用フロー

### 12.1 通常フロー
1. scheduler で起動
2. `companies.yaml` 読込
3. Root Portal を確認
4. 各バーチャルカンパニーを確認
5. CompanyGuardian 自身を確認
6. 異常があれば incident 作成
7. 必要なら countermeasure 作成
8. 日報作成
9. 終了

### 12.2 異常時フロー
1. 異常検出
2. 異常分類
3. 原因候補を整理
4. 自動対策実施（**非破壊・低リスク操作に限定**）
   - GitHub Actions の再確認・`workflow_dispatch` による再実行
   - 日報・incident・countermeasure の生成
   - ※ 設定ファイル修正・コミット・プッシュ・HTML 修正は提案のみ（人間確認前提）
5. 成否確認
6. incident 記録
7. 再発防止策が必要なら countermeasure 追加
8. 日報に反映

---

## 13. 障害優先度

### High
- 親ポータルがダウン
- CompanyGuardian 自己監視失敗
- 公開不能
- GitHub Actions 継続失敗

### Medium
- 一部リンク切れ
- 一部成果物不足
- キーワード欠落
- ページ部分表示不整合

### Low
- 備考情報不足
- 軽微な README 不整合
- 任意成果物不足

---

## 14. エラー分類コード

- `ACTION_FAILED`
- `SITE_DOWN`
- `SITE_DEGRADED`
- `ARTIFACT_MISSING`
- `KEYWORD_MISSING`
- `LINK_BROKEN`
- `CONFIG_INVALID`
- `SELF_CHECK_FAILED`
- `REPORT_MISSING`
- `UNKNOWN_ERROR`

---

## 15. データ仕様

### 15.1 日報ファイル
- UTF-8
- Markdown
- 定期実行のファイル名: `YYYY-MM-DD.md`
- 手動実行のファイル名: `YYYY-MM-DD_manual_XX.md`
- 日付は JST 基準

### 15.2 インシデント
- UTF-8
- Markdown
- 1 障害 1 ファイル

### 15.3 再発防止策
- UTF-8
- Markdown
- 識別可能な一意ファイル名

---

## 16. 追加容易性要件

新しいバーチャルカンパニー追加時は、原則として以下のみで完了できること。

1. `companies.yaml` に1件追加
2. 必要なら `required_keywords` など最小設定追加

新規追加のたびに Python スクリプト側を修正しなくても動作することを目標とする。

---

## 17. 保守性要件

- 設定駆動で対象追加可能
- 出力ファイル命名規則が一定
- Markdown ベースで人間可読
- 将来 Slack / Telegram 通知に拡張しやすい
- 将来 issue 起票や月報生成に拡張しやすい

---

## 18. セキュリティ・安全性

- 秘密情報はコードや Markdown に直書きしない
- GitHub Token 等は Actions secrets で扱う
- 自動対策は破壊的変更を避ける
- 修復不能時は無理に続行せず、事実を日報へ記録する

### 18.1 GitHub Token スコープ方針

| 操作 | トークン種別 | 必要権限 |
|------|-------------|----------|
| 同一リポジトリ内操作 | `GITHUB_TOKEN` | デフォルトで可 |
| 他リポジトリの Actions 状態参照 | PAT / fine-grained token | Actions: Read, Contents: Read |
| ワークフロー再実行 | PAT / fine-grained token | Actions: Write |
| コミット・プッシュ（将来拡張） | PAT / fine-grained token | Contents: Write |

初期版では他リポジトリ監視は Read 中心とし、コミット・プッシュの自動化はスコープ外とする。

---

## 19. 将来拡張

- Slack / Telegram 通知
- GitHub Issue 自動起票
- 月報・週報の自動生成
- 健康スコア算出
- 過去障害パターンに基づく対策推薦
- ポートフォリオサイトへの監視結果反映

---

## 20. 受け入れ条件

以下を満たしたら初期版の仕様達成とみなす。

1. `companies.yaml` から複数対象を読める
2. Root Portal を監視できる
3. 各バーチャルカンパニーを監視できる
4. CompanyGuardian 自身を自己監視できる
5. 異常時に incident Markdown を生成できる
6. 再発防止策 Markdown を保存できる
7. 定期実行で日報 Markdown を毎日 1 ファイル生成でき、手動実行では追加ファイルを生成できる
8. README.md に `countermeasures/` を読む運用ルールを明記できる

---

## 21. 実装優先順位

### Phase 1
- 設定ファイル読込
- 日次巡回
- サイト死活確認
- GitHub Actions 状態確認
- 日報出力

### Phase 2
- incident 出力
- countermeasure 出力
- 自己監視強化

### Phase 3
- 自動対策の高度化
- 通知機能
- 健康スコアや月報生成

---

## 22. 補足

CompanyGuardian は「他社を見張るだけの監視役」ではなく、  
**自分自身も監視対象に含むバーチャルカンパニー**である。  
この自己監視性は本システムの中核要件であり、README と設定ファイルの両方に明示されなければならない。
