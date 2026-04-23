# インシデント: Auto AI Blog

- 発生日: 2026-04-24
- 対象会社: Auto AI Blog
- 対象ID: auto-ai-blog
- 異常コード: DAILY_POST_MISSING

## 現象
前日(2026-04-23)投稿が確認できない

## 影響範囲
公開サイトは到達可能だが、業務継続または品質に重大な異常あり

## 原因分類
WORKFLOW_NOT_RUNNING

## 原因要約
latest_run=completed/success/2026-04-22T03:02:04Z / latest_success=2026-04-22T03:02:04Z / latest_commit=2026-04-22T03:00:07Z / site_latest=unknown

## 推奨修正
workflow_dispatch で 1 回再実行

## 実施した修正
auto-ai-blog は dispatch 対象 workflow 未設定

## 修正結果
auto-ai-blog は dispatch 対象 workflow 未設定

## 次アクション
workflow_dispatch で 1 回再実行

## 原因
latest_run=completed/success/2026-04-22T03:02:04Z / latest_success=2026-04-22T03:02:04Z / latest_commit=2026-04-22T03:00:07Z / site_latest=unknown

## 関連 countermeasure

