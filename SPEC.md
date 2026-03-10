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
- `site`: 対象サイト URL
- `enabled`: true/false
- `checks`: 実行するチェック一覧

### 9.4 任意項目

- `repo`: GitHub リポジトリ名
- `workflow`: GitHub Actions ワークフロー名
- `required_keywords`: トップページにあるべき文字列一覧
- `required_paths`: 存在確認したいパス一覧
- `self_monitor`: 自己監視対象か
- `notes`: 補足説明

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
    site: https://hantani-portfolio.pages.dev/
    enabled: true
    checks:
      - github_actions
      - site_http
      - artifact

  - id: company-guardian
    name: CompanyGuardian
    kind: guardian
    repo: garyohosu/CompanyGuardian
    site: https://example.github.io/CompanyGuardian/
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

### 入力
- `companies.yaml`

### 出力
- 実行ログ
- 日報 Markdown
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

### 異常例
- 404 / 500
- トップページ内容欠損
- 主要リンク切れ
- 表示崩れを示唆する異常な HTML 欠落

---

## 10.3 各バーチャルカンパニー監視

### チェック項目
- GitHub Actions の直近実行成功/失敗
- 公開サイトの HTTP 応答
- 必須成果物の生成有無
- 必要に応じトップページキーワード確認

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
- 当日の日報生成可否
- `companies.yaml` の妥当性
- README.md の必須セクション存在
- 自己監視結果が日報に記録されていること

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

---

## 10.7 日報生成

### 目的
1 日の巡回結果を 1 ファイルに集約する。

### 出力先
`reports/daily/YYYY-MM-DD.md`

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
4. 可能なら自動対策実施
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
- ファイル名: `YYYY-MM-DD.md`

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
7. 日報 Markdown を毎日 1 ファイル生成できる
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
