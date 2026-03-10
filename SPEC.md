# SPEC.md

## 1. 文書情報

- プロジェクト名: CompanyGuardian
- 種別: バーチャルカンパニー群の監視・障害対応・日報・再発防止ナレッジ蓄積システム
- 目的: 複数のバーチャルカンパニーと親ポータルを毎日巡回し、異常を検知した場合は原因分析・対策・記録まで行う
- 想定運用環境: **Windows 11 + WSL2 上で動作する OpenClaw が cron 相当の定期実行を行う**
- リポジトリ名: `CompanyGuardian`

Google AdSense は収益化対象ページに導入すること。
導入方法はテンプレート、include、ビルド時注入、タグマネージャ等を許容し、CompanyGuardian の監視は script 文字列の完全一致では行わない。

各ページはCDNを使ったモダンでリッチでアニメーションを多用した外観のサイトとすること


---

## 2. 背景

ユーザーは複数のバーチャルカンパニーを GitHub リポジトリ、GitHub Actions、静的サイト公開、AI エージェント運用を組み合わせて管理している。
個別プロジェクトの数が増えたため、最低でも 1 日 1 回は全体状態を確認し、異常があれば原因と対策を整理し、結果を日報として残す仕組みが必要になった。

また、親ポータルおよび各バーチャルカンパニーは公開サイトとしての役割を持ち、**Google AdSense による広告収益化を前提とする**。
そのため CompanyGuardian は、単なる監視ツールではなく、公開継続性と広告掲載条件も含めて確認する統合運用リポジトリである。

CompanyGuardian は以下を行う。

- 親ポータルの監視
- 各バーチャルカンパニーの監視
- 自分自身の自己監視
- 異常の原因分析
- 対策実施
- 日報生成
- 再発防止策のナレッジ化
- Google AdSense 掲載前提条件の継続確認

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
- AdSense アカウントの申請・審査そのものの自動化
  - ただし掲載前提条件の監視は対象に含む

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
9. **Google AdSense 必須ページ・広告掲載前提条件を監視できる**
10. **日次投稿の存在確認を前日基準で判定できる**

---

## 5. 非ゴール

- 完全自律であらゆる障害を修復すること
- すべての障害原因を AI が 100% 正確に特定すること
- 外部 API の契約や権限設定まで自動変更すること
- ノーエラーを保証すること
- AdSense 審査結果そのものを保証すること

---

## 6. 基本コンセプト

CompanyGuardian は「監視」「解析」「対策」「記録」「再発防止」「収益維持確認」の 6 役を持つ。

### 6.1 監視
- サイト死活
- GitHub Actions 実行結果
- 必須成果物の有無
- 主要リンク整合性
- 自己監視
- AdSense 関連必須ページの有無

### 6.2 解析
- 異常内容の分類
- 原因候補の抽出
- 再現条件の確認
- 影響範囲の整理

### 6.3 対策
- 再実行可能なワークフローの再試行
- 設定不備の修正案整理
- リンク切れ是正案提示
- 生成漏れ補完案の提示
- AdSense 掲載漏れの検出と是正提案

### 6.4 記録
- インシデント記録
- 日報生成
- 対策履歴記録

### 6.5 再発防止
- 独自名を付けた countermeasure Markdown を保存
- README から参照可能にする
- 次回以降の運用フローに反映する

### 6.6 収益維持確認
- AdSense 関連ページ有無確認
- 広告スクリプト掲載前提条件確認
- 収益化対象ページの公開継続確認

---

## 7. 想定アーキテクチャ

```text
Windows 11 Host
   └─ WSL2
       └─ OpenClaw
           └─ cron / scheduler
               └─ CompanyGuardian Runner
                    ├─ companies/companies.yaml を読込
                    ├─ Root Portal を確認
                    ├─ Virtual Companies を順次確認
                    ├─ CompanyGuardian 自身を確認
                    ├─ incidents/ に個別記録出力
                    ├─ countermeasures/ に再発防止策出力
                    └─ reports/daily/YYYY-MM-DD.md に日報出力
```

---

## 8. 実行環境要件

### 8.1 ホスト環境
- Windows 11

### 8.2 Linux 実行環境
- WSL2
- Ubuntu 系ディストリビューションを推奨

### 8.3 スケジューラ
- OpenClaw が cron 相当機能または定期起動機構を用いて CompanyGuardian を日次実行する
- GitHub Actions は監視対象であり、**CompanyGuardian 自身の主たる定期実行基盤ではない**

### 8.4 実行方式
- OpenClaw からローカル CLI / Python スクリプトを呼び出して実行する
- 初期版の単一エントリポイントは `scripts/check_targets.py` とする
- `scripts/check_targets.py` が設定読込、全対象巡回、異常集約、incident / countermeasure / 日報生成、push の起点を担う
- `analyze_incident.py` / `apply_countermeasure.py` / `generate_daily_report.py` / `self_check.py` は `check_targets.py` から呼び出される内部モジュールとして扱う
- スクリプト間の主な受け渡しは Python オブジェクト / 戻り値とし、永続化が必要なものだけ Markdown に保存する
- 継続制御は Python 側で行い、1対象ごとに例外を吸収して残り対象の巡回を継続する
- 初期版の推奨 Python 実行環境は 3.11 以上、依存管理は `requirements.txt` を正式採用する
- 必要に応じて GitHub API を参照する
- 出力された Markdown はローカルリポジトリへ保存し、GitHub へ push する

---

## 9. ディレクトリ構成

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
└─ docs/
   └─ adsense_requirements.md
```

---

## 10. 設定ファイル仕様

### 10.1 ファイル名
`companies/companies.yaml`

### 10.2 目的
監視対象の追加・無効化を設定変更だけで行えるようにする。

### 10.3 必須項目

- `id`: 一意な識別子
- `name`: 表示名
- `kind`: `portal` / `virtual_company` / `guardian`
- `enabled`: true/false
- `checks`: 実行するチェック一覧

### 10.4 条件付き必須項目

- `site`: 公開サイトを持つ対象では必須
- `repo`: GitHub リポジトリを持つ対象では必須
- `workflow`: Actions 監視対象ワークフローがある場合に推奨
- `adsense_required`: 収益化対象なら必須
- `required_adsense_pages`: AdSense 前提ページ確認が必要なら必須

### 10.5 任意項目

- `required_keywords`: トップページにあるべき文字列一覧
- `required_paths`: 旧簡易記法。内部的に `required_artifacts` の `type: site_path` に変換する（後方互換用）
- `required_artifacts`: 成果物確認定義（`type: site_path` / `type: repo_path` / `type: workflow_artifact`）
- `required_repo_paths`: リポジトリ内必須パスの簡易記法。内部的に `required_artifacts` の `type: repo_path` に変換する。`required_artifacts` に `type: repo_path` が既にある場合はマージし重複を排除する
- `daily_post_strategy`: `daily_post_previous_day` で用いる探索戦略一覧（`site_path_pattern` / `feed_xml` / `sitemap_xml` / `index_page_keyword`）
- `daily_post_locator`: 前日投稿探索に使う locator 定義。`feed_url` / `sitemap_url` / `path_pattern` / `index_url` / `keyword_pattern` / `timezone` などを保持する mapping
- `link_targets`: `link_health` チェック時に明示確認するリンク URL 一覧
- `adsense_marker_keyword`: AdSense 実装痕跡を任意確認するキーワード
- `self_monitor`: 自己監視対象か
- `portal_visible`: 親ポータルからの導線確認対象か（省略時は `kind: virtual_company` かつ `site` 設定済みなら `true` 相当）
- `notes`: 補足説明

### 10.6 サンプル

```yaml
companies:
  - id: root-portal
    name: Root Portal
    kind: portal
    site: https://garyohosu.github.io/
    enabled: true
    adsense_required: true
    required_adsense_pages:
      - /privacy-policy/
      - /contact/
    checks:
      - site_http
      - top_page_keyword
      - link_health
      - adsense_pages

  - id: auto-ai-blog
    name: Auto AI Blog
    kind: virtual_company
    repo: garyohosu/auto-ai-blog
    site: https://hantani-portfolio.pages.dev/
    enabled: true
    portal_visible: true
    adsense_required: true
    required_artifacts:
      - type: site_path
        path: /index.html
      - type: site_path
        path: /feed.xml
    daily_post_strategy:
      - feed_xml
      - site_path_pattern
    daily_post_locator:
      feed_url: /feed.xml
      path_pattern: /posts/{yyyy}/{mm}/{dd}/
      timezone: Asia/Tokyo
    adsense_marker_keyword: adsbygoogle
    checks:
      - github_actions
      - site_http
      - artifact
      - daily_post_previous_day
      - adsense_pages

  - id: company-guardian
    name: CompanyGuardian
    kind: guardian
    repo: garyohosu/CompanyGuardian
    enabled: true
    self_monitor: true
    adsense_required: false
    checks:
      - github_actions
      - report_generated
      - config_valid
      - self_status
```

### 10.7 利用可能な `checks` 種別

| 種別 | 判定条件 |
|------|----------|
| `site_http` | HTTP GET で 2xx → 正常、3xx → 警告、4xx/5xx → 異常（`SITE_DOWN`） |
| `top_page_keyword` | `required_keywords` の全要素がトップページ本文に含まれる → 正常、1つでも欠落 → 異常（`KEYWORD_MISSING`） |
| `link_health` | 範囲限定型（詳細は §11.2 参照）。4xx/5xx → 異常（`LINK_BROKEN`） |
| `github_actions` | 直近1回の実行結果を確認。`success` → 正常、`failure` / `cancelled` / `timed_out` / `action_required` → 異常（`ACTION_FAILED`）、`in_progress` / `queued` / 履歴なし → 警告 |
| `artifact` | `required_artifacts` で定義された成果物の存在確認。初期版で実装必須なのは `type: site_path` のみ。`type: repo_path` / `type: workflow_artifact` は未サポートなら警告でスキップ可。`site_path` 未存在 → 異常（`ARTIFACT_MISSING`） |
| `daily_post_previous_day` | `daily_post_strategy` を上から順に評価し、最初に前日投稿ありと判定できた時点で正常。すべて失敗 → 異常（`DAILY_POST_MISSING`）。戦略未指定 → 警告 |
| `adsense_pages` | `required_adsense_pages` に列挙されたページが存在し到達可能か確認。1つでも欠落・到達不能 → 異常（`ADSENSE_PAGE_MISSING`）。`adsense_marker_keyword` を指定した場合のマーカー欠落は初期版では警告 |
| `report_generated` | 直近の定期実行分の日報ファイルが所定パスに存在する → 正常。定期実行時は前回定期実行分、手動実行時も直近の定期実行分を対象とする |
| `config_valid` | 必須設定ファイルが YAML/Markdown として構文妥当で、必須設定キーを満たす → 正常（`CONFIG_INVALID`） |
| `self_status` | CompanyGuardian 自身の前回実行結果、README 必須セクション（§12 の 12 項目）、自己監視要件、直近定期日報との整合を確認（`SELF_CHECK_FAILED`） |

未知の種別が指定された場合は、警告を日報に記録してその項目のみスキップする。全体実行は止めない。

### 10.8 `daily_post_previous_day` の探索戦略

- 会社ごとに 1 つ以上の探索戦略を定義できる
- 複数戦略を指定した場合は上から順に評価する
- 最初に「前日投稿あり」と判定できた時点で正常とする
- すべて失敗した場合は `DAILY_POST_MISSING`
- 戦略未指定の場合は `WARNING` とし、日報へ記録するが即 `ERROR` にはしない
- 日付判定は JST 前日基準とする
- 会社ごとの差は設定で吸収し、Python 側に会社名ベースの分岐を書かない

#### `daily_post_strategy` の許容値

| 戦略 | 内容 |
|------|------|
| `site_path_pattern` | 前日 JST の日付を埋め込んだ URL パターンで確認する。例: `/posts/{yyyy}/{mm}/{dd}/` |
| `feed_xml` | `feed.xml` を読み、前日 JST の公開日を持つ `item` / `entry` が 1 件以上あるか確認する |
| `sitemap_xml` | `sitemap.xml` を読み、前日 JST に対応する URL または更新日を持つエントリがあるか確認する |
| `index_page_keyword` | トップページまたは指定一覧ページに、前日投稿のタイトル・日付・slug などの識別子が含まれるか確認する |

#### 推奨順位

初期版の推奨順位は以下とする。

1. `feed_xml`
2. `sitemap_xml`
3. `site_path_pattern`
4. `index_page_keyword`

#### `daily_post_locator` 例

```yaml
daily_post_strategy:
  - feed_xml
  - site_path_pattern

daily_post_locator:
  feed_url: /feed.xml
  path_pattern: /posts/{yyyy}/{mm}/{dd}/
  timezone: Asia/Tokyo
```

### 10.9 `CheckStatus` の扱い

- `OK`: 正常
- `WARNING`: 要注意だが即障害とはしない
- `ERROR`: 異常
- 日報は `ok_count` / `warning_count` / `error_count` の 3 分類で集計する
- `WARNING` は `要対応一覧` に掲載するが、原則として incident は生成しない
- `ERROR` は原則として incident 生成対象とする
- 同一対象で複数の `WARNING` が継続し、運用上の対応が必要と判断された場合のみ任意で incident 化してよい

---

## 11. 機能要件

## 11.1 日次巡回

### 要件
- 1 日 1 回、全監視対象を順次確認する
- OpenClaw の cron 相当機構から起動される
- 手動実行も可能とする
- 途中失敗しても可能な限り残り対象の確認を継続する

### スケジュール
- OpenClaw の定期実行設定: **JST 06:00**（Linux cron 相当では `0 6 * * *` を JST で指定）
- 日付判定・日報ファイル名の基準日は **JST**
- 定期実行の出力先: `reports/daily/YYYY-MM-DD.md`

### 手動実行
- OpenClaw から直接スクリプトを CLI 呼び出しすることで手動実行可能とする
- 呼び出し例: `python scripts/check_targets.py --trigger manual`
- 手動実行の出力先: `reports/daily/YYYY-MM-DD_manual_XX.md`（`XX` は `01` からの連番）
- 初期版では既存日報への追記更新は行わない

### 入力
- `companies.yaml`

### 出力
- 実行ログ
- 日報 Markdown
- 必要に応じた incident / countermeasure Markdown

### 日次判定基準
- **GitHub Actions などの実行状態確認は当日基準**
- **デイリー投稿、日報、日次成果物の存在確認は前日基準**
- 日付判定は **JST** とする

### 例
- 2026-03-10 JST 06:00 実行時
  - GitHub Actions 成否: 2026-03-10 時点の最新実行を見る
  - デイリー投稿有無: 2026-03-09 分を見る
  - 日報有無: 2026-03-09 分を見る

---

## 11.2 親ポータル監視

### 対象
- `https://garyohosu.github.io/`

### チェック項目
- HTTP ステータス
- トップページ取得可否
- 想定キーワードの有無
- 主要リンクの健全性
- ポータルから主要会社リンクへ到達可能か
- AdSense 必須ページの有無

### `link_health` の対象範囲（portal）
- 同一オリジン内リンク
- `companies.yaml` に定義された `enabled: true` かつ `kind: virtual_company` の各 `site`
- 明示的に `link_targets` で指定されたリンク

### `link_health` の除外対象
- SNS リンク
- 広告・アフィリエイトリンク
- analytics スクリプト参照
- 外部 CDN
- 外部ブログ・ニュース記事リンク
- クエリ付きトラッキングリンク

### 主要会社リンク判定ルール
- 正本は `companies.yaml` の `enabled: true` かつ `kind: virtual_company` の各エントリ
- 各会社の `site` を期待リンク先として扱う
- 親ポータル HTML 内に、その URL または正規化後に同値なリンクが存在するか確認する
- リンクが存在し到達可能であれば正常
- `site` 未設定の会社は対象外
- `enabled: false` の会社は対象外
- `portal_visible: false` の会社は対象外

### 異常例
- 404 / 500
- トップページ内容欠損
- 主要リンク切れ
- 表示崩れを示唆する異常な HTML 欠落
- privacy policy / contact の欠落

---

## 11.3 各バーチャルカンパニー監視

### チェック項目
- GitHub Actions の直近実行成功/失敗
- 公開サイトの HTTP 応答
- 必須成果物の生成有無
- 必要に応じトップページキーワード確認
- 前日投稿探索戦略に基づく前日分のデイリー投稿有無
- AdSense 前提ページの有無

### 異常分類例
- `ACTION_FAILED`
- `SITE_DOWN`
- `ARTIFACT_MISSING`
- `KEYWORD_MISSING`
- `LINK_BROKEN`
- `DAILY_POST_MISSING`
- `ADSENSE_PAGE_MISSING`

---

## 11.4 自己監視

### 対象
- CompanyGuardian 自身

### チェック項目
- 直近実行結果
- 前回定期日報生成可否
- `companies.yaml` の妥当性
- README.md の必須セクション存在
- 自己監視結果が日報に記録されていること

### 重要ルール
- 自己異常は高優先度とする
- 自己異常発生時も、可能な範囲で他対象の確認を継続する
- 自己修復不可の場合、その旨を日報の先頭に記載する

---

## 11.5 インシデント記録

### 目的
異常検出時の事実・原因・対策・結果を個別記録として残す。

### 出力先
`incidents/YYYY-MM-DD-<target>-<slug>.md`

### 生成単位
- 初期版では **1対象1実行あたり1インシデント** を原則とする
- 同一対象で複数チェック失敗時は 1 ファイルに集約する

### slug 命名ルール
- slug は主たる異常区分を基準に決める
- 主たる異常の優先順位は以下とする
  1. `SITE_DOWN`
  2. `ACTION_FAILED`
  3. `ARTIFACT_MISSING`
  4. `DAILY_POST_MISSING`
  5. `ADSENSE_PAGE_MISSING`
  6. `KEYWORD_MISSING`
  7. `LINK_BROKEN`
  8. `UNKNOWN_ERROR`
- 例: `incidents/2026-03-10-auto-ai-blog-site-down.md`
- 原因が明らかに別系統なら分割してよいが、初期版の原則は対象単位で集約する

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

## 11.6 再発防止策の保存

### 目的
似た障害が再発した際に、過去対策を即座に参照できるようにする。

### 出力先
`countermeasures/CM-XXX_<Name>.md`

### 命名ルール
- 連番: `CM-001`, `CM-002` ...
- 独自名: 英単語または CamelCase 推奨

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

### 生成条件
- 毎回自動生成しない
- 再発可能性がある
- 既存 countermeasure と重複しない
- 単なる一時失敗ではない
- 原因または対策候補がある程度整理できている
- 運用ナレッジとして残す価値がある

### 重複判定と関連付け
- 初期版では `CountermeasureManager.should_create()` 相当の簡易判定で生成可否を決める
- `countermeasures/` のタイトルおよび発端障害を走査し、類似する既存 countermeasure があれば新規作成しない
- 新規作成時も既存流用時も、関連する countermeasure を incident に記録する

---

## 11.7 日報生成

### 目的
1 日の巡回結果を 1 ファイルに集約する。

### 出力先
- 定期実行: `reports/daily/YYYY-MM-DD.md`
- 手動実行: `reports/daily/YYYY-MM-DD_manual_XX.md`

### 必須項目
- 実行日時
- 実行主体
- 対象総数
- 正常件数（`ok_count`）
- 警告件数（`warning_count`）
- 異常件数（`error_count`）
- 要対応一覧（`WARNING` / `ERROR` を含む）
- 実施した対策一覧
- 新規 countermeasure 一覧
- 自己監視結果
- AdSense 関連異常一覧
- 総括

---

## 11.8 AdSense 前提条件監視

### 目的
広告収益化に必要な公開導線と必須ページが維持されているかを確認する。

### 対象
- `adsense_required: true` の対象

### チェック項目
- `required_adsense_pages` に列挙されたページの存在
- 広告掲載対象ページの公開状態
- 重大なリンク切れがないこと
- 必要に応じて `adsense_marker_keyword` による実装痕跡確認

### 初期版で必須とするページ例
- `/privacy-policy/`
- `/contact/`

### 備考
- AdSense の審査通過自体は保証対象外
- ただし審査や継続配信に不利となる基本要件の欠落は異常として記録する
- `adsense_pages` チェックは 2 層構成とする
  - 必須: 公開導線・必須ページの存在確認
  - 任意: `adsense_marker_keyword` による実装痕跡確認
- 初期版で監視対象にしないもの
  - `<script ... adsbygoogle.js ...>` の完全文字列一致
  - `ca-pub-...` の生値一致
  - AdSense 管理画面上の配信結果
  - 審査通過そのもの

---

## 12. README.md 要件

README.md には最低限以下を記載する。

1. CompanyGuardian の目的
2. 実行環境が Windows 11 + WSL2 + OpenClaw であること
3. OpenClaw の cron 相当機構で日次実行すること
4. 監視対象カテゴリ
5. 実行方法
6. 日報の保存先
7. インシデント記録の保存先
8. 再発防止策の保存先
9. 新しい会社の追加方法
10. CompanyGuardian 自身も監視対象であること
11. 障害時は `countermeasures/` を読めと明記すること
12. Google AdSense 必須要件を監視対象に含むこと

---

## 13. 運用フロー

### 13.1 通常フロー
1. OpenClaw cron 相当機構で起動
2. `companies.yaml` 読込
3. Root Portal を確認
4. 各バーチャルカンパニーを確認
5. CompanyGuardian 自身を確認
6. 異常があれば incident 作成
7. 必要なら countermeasure 作成
8. 日報作成
9. GitHub へ push
10. 終了

### 13.2 異常時フロー
1. 異常検出
2. 異常分類
3. 原因候補を整理
4. 可能なら低リスク自動対策実施
5. 成否確認
6. incident 記録
7. 再発防止策が必要なら countermeasure 追加
8. 日報に反映
9. GitHub へ push

---

## 14. 障害優先度

### High
- 親ポータルがダウン
- CompanyGuardian 自己監視失敗
- 公開不能
- GitHub Actions 継続失敗
- AdSense 必須ページ欠落

### Medium
- 一部リンク切れ
- 一部成果物不足
- キーワード欠落
- ページ部分表示不整合
- 前日分デイリー投稿欠落

### Low
- 備考情報不足
- 軽微な README 不整合
- 任意成果物不足

---

## 15. エラー分類コード

- `ACTION_FAILED`
- `SITE_DOWN`
- `SITE_DEGRADED`
- `ARTIFACT_MISSING`
- `KEYWORD_MISSING`
- `LINK_BROKEN`
- `CONFIG_INVALID`
- `SELF_CHECK_FAILED`
- `REPORT_MISSING`
- `DAILY_POST_MISSING`
- `ADSENSE_PAGE_MISSING`
- `UNKNOWN_ERROR`

---

## 16. 追加容易性要件

新しいバーチャルカンパニー追加時は、原則として以下のみで完了できること。

1. `companies.yaml` に1件追加
2. 必要なら `required_artifacts`、`required_adsense_pages`、`required_keywords` を最小設定追加

新規追加のたびに Python スクリプト側を修正しなくても動作することを目標とする。

---

## 17. 保守性要件

- 設定駆動で対象追加可能
- 出力ファイル命名規則が一定
- Markdown ベースで人間可読
- OpenClaw 上で長期運用しやすい
- 将来 Slack / Telegram 通知に拡張しやすい
- 将来 issue 起票や月報生成に拡張しやすい

---

## 18. セキュリティ・安全性

- 秘密情報はコードや Markdown に直書きしない
- GitHub Token 等はローカル secret 管理または環境変数で扱う
- 自動対策は破壊的変更を避ける
- 修復不能時は無理に続行せず、事実を日報へ記録する
- AdSense コードや検証用コードは平文ハードコードを避け、必要に応じテンプレート管理する

### 18.1 GitHub Token スコープ方針

| 操作 | トークン種別 | 必要権限 |
|------|-------------|----------|
| 他リポジトリの Actions 状態参照 | PAT / fine-grained token | Actions: Read, Contents: Read |
| ワークフロー再実行（workflow_dispatch） | PAT / fine-grained token | Actions: Write |
| コミット・プッシュ（出力 Markdown の保存） | PAT / fine-grained token | Contents: Write（CompanyGuardian リポジトリのみ） |

トークンは WSL2 環境の環境変数（例: `~/.bashrc` や OpenClaw の secret 管理機能）で管理し、スクリプトは `os.environ` 経由で参照する。コードへの直書きは禁止。

### 18.2 GitHub push 方針

- 主たる定期実行基盤は GitHub Actions ではなく OpenClaw（WSL2 cron）とする
- OpenClaw は `python scripts/check_targets.py` を起動し、その実行結果として出力 Markdown（日報・インシデント・再発防止策）を `git add → git commit → git push` する
- push 対象リポジトリ: `CompanyGuardian` リポジトリのみ
- 初期版では push 失敗時はエラーログを残してスクリプトを終了し、次回実行時に再 push を試みる運用とする（自動リトライは行わない）

---

## 19. 将来拡張

- Slack / Telegram 通知
- GitHub Issue 自動起票
- 月報・週報の自動生成
- 健康スコア算出
- 過去障害パターンに基づく対策推薦
- ポートフォリオサイトへの監視結果反映
- AdSense 収益状況の可視化連携

---

## 20. 受け入れ条件

以下を満たしたら初期版の仕様達成とみなす。

1. `companies.yaml` から複数対象を読める
2. Root Portal を監視できる
3. 各バーチャルカンパニーを監視できる
4. CompanyGuardian 自身を自己監視できる
5. 異常時に incident Markdown を生成できる
6. 再発防止策 Markdown を保存できる
7. 日報 Markdown を毎日 1 ファイル生成できる
8. README.md に `countermeasures/` を読む運用ルールを明記できる
9. OpenClaw の日次起動経路で実行できる
10. AdSense 必須ページ監視が動作する
11. 前日分デイリー投稿確認が動作する

---

## 21. 実装優先順位

### Phase 1
- 設定ファイル読込
- OpenClaw 日次起動
- サイト死活確認
- GitHub Actions 状態確認
- 前日分デイリー投稿確認
- 日報出力

### Phase 2
- incident 出力
- countermeasure 出力
- 自己監視強化
- AdSense 必須ページ確認

### Phase 3
- 自動対策の高度化
- 通知機能
- 健康スコアや月報生成
- AdSense 収益可視化連携

---

## 22. 補足

CompanyGuardian は「他社を見張るだけの監視役」ではなく、  
**自分自身も監視対象に含むバーチャルカンパニー**である。  
この自己監視性は本システムの中核要件であり、README と設定ファイルの両方に明示されなければならない。

また本システムは、**Windows 11 上の WSL2 内で OpenClaw が定期実行する運用**を前提とし、
**Google AdSense を必須要件として扱う公開サイト群の継続運用**を支えるものである。
