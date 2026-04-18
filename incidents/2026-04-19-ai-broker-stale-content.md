# インシデント: AI-Broker

- 発生日: 2026-04-19
- 対象会社: AI-Broker
- 対象ID: ai-broker
- 異常コード: STALE_CONTENT, DAILY_POST_MISSING

## 現象
最新日次レポートが 2026-04-17 で停止

## 影響範囲
公開サイトは到達可能だが、業務継続または品質に重大な異常あり

## 原因分類
WORKFLOW_NOT_RUNNING

## 原因要約
latest_run=completed/success/2026-04-17T09:01:49Z / latest_success=2026-04-17T09:01:49Z / latest_commit=2026-04-18T12:42:02Z / site_latest=2026-04-17 / repo_content_exists=False

## 推奨修正
workflow_dispatch で 1 回再実行

## 実施した修正
ai-broker workflow_dispatch を 1 回実行 (auth=gh_cli)

## 修正結果
ai-broker 再確認後も未解決: 最新日次レポートが 2026-04-17 で停止

## 次アクション
workflow_dispatch で 1 回再実行

## 原因
latest_run=completed/success/2026-04-17T09:01:49Z / latest_success=2026-04-17T09:01:49Z / latest_commit=2026-04-18T12:42:02Z / site_latest=2026-04-17 / repo_content_exists=False

## 関連 countermeasure

