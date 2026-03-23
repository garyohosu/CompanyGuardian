# インシデント: AozoraDailyTranslations

- 発生日: 2026-03-24
- 対象会社: AozoraDailyTranslations
- 対象ID: aozora-daily-translations
- 異常コード: DAILY_POST_MISSING

## 現象
前日翻訳が 2026-03-23 分で欠落

## 影響範囲
公開サイトは到達可能だが、業務継続または品質に重大な異常あり

## 原因分類
WORKFLOW_NOT_RUNNING

## 原因要約
latest_run=completed/success/2026-03-20T00:00:55Z / latest_success=2026-03-20T00:00:55Z / latest_commit=2026-03-20T00:00:27Z / site_latest=2026-03-20

## 推奨修正
workflow_dispatch で 1 回再実行

## 実施した修正
aozora-daily-translations は dispatch 対象 workflow 未設定

## 修正結果
aozora-daily-translations は dispatch 対象 workflow 未設定

## 次アクション
workflow_dispatch で 1 回再実行

## 原因
latest_run=completed/success/2026-03-20T00:00:55Z / latest_success=2026-03-20T00:00:55Z / latest_commit=2026-03-20T00:00:27Z / site_latest=2026-03-20

## 関連 countermeasure

