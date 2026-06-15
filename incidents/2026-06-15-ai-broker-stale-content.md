# インシデント: AI-Broker

- 発生日: 2026-06-15
- 対象会社: AI-Broker
- 対象ID: ai-broker
- 異常コード: STALE_CONTENT, DAILY_POST_MISSING

## 現象
最新日次レポートが 2026-06-12 で停止

## 影響範囲
公開サイトは到達可能だが、業務継続または品質に重大な異常あり

## 原因分類
CONTENT_NOT_GENERATED

## 原因要約
latest_run=in_progress/None/2026-06-15T00:24:07Z / latest_success=2026-06-12T11:23:57Z / latest_commit=2026-06-15T00:29:03Z / site_latest=2026-06-12 / repo_content_exists=False

## 推奨修正
生成ロジックまたは入力不足を確認し、必要なら workflow を再実行

## 実施した修正
ai-broker は高リスクまたは自動修正対象外のため原因解析のみ実施

## 修正結果
ai-broker は高リスクまたは自動修正対象外のため原因解析のみ実施

## 次アクション
生成ロジックまたは入力不足を確認し、必要なら workflow を再実行

## 原因
latest_run=in_progress/None/2026-06-15T00:24:07Z / latest_success=2026-06-12T11:23:57Z / latest_commit=2026-06-15T00:29:03Z / site_latest=2026-06-12 / repo_content_exists=False

## 関連 countermeasure

