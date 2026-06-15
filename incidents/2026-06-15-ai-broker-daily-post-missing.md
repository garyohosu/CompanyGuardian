# インシデント: AI-Broker

- 発生日: 2026-06-15
- 対象会社: AI-Broker
- 対象ID: ai-broker
- 異常コード: DAILY_POST_MISSING

## 現象
前日の日次レポートが 2026-06-14 分で欠落

## 影響範囲
公開サイトは到達可能だが、業務継続または品質に重大な異常あり

## 原因分類
CONTENT_NOT_DEPLOYED

## 原因要約
latest_run=completed/success/2026-06-15T00:35:58Z / latest_success=2026-06-15T00:35:58Z / latest_commit=2026-06-15T00:40:08Z / site_latest=2026-06-15 / repo_content_exists=True

## 推奨修正
deploy workflow を 1 回再実行

## 実施した修正
ai-broker deploy workflow を 1 回再実行 (auth=gh_cli)

## 修正結果
ai-broker 再確認で DAILY_POST_MISSING 解消を確認

## 次アクション


## 原因
latest_run=completed/success/2026-06-15T00:35:58Z / latest_success=2026-06-15T00:35:58Z / latest_commit=2026-06-15T00:40:08Z / site_latest=2026-06-15 / repo_content_exists=True

## 関連 countermeasure

