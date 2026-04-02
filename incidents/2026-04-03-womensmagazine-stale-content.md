# インシデント: WomensMagazine

- 発生日: 2026-04-03
- 対象会社: WomensMagazine
- 対象ID: womens-magazine
- 異常コード: STALE_CONTENT, DAILY_POST_MISSING

## 現象
最新記事が 2026-04-01 で停止

## 影響範囲
公開サイトは到達可能だが、業務継続または品質に重大な異常あり

## 原因分類
CONTENT_NOT_GENERATED

## 原因要約
latest_run=completed/success/2026-04-02T02:34:08Z / latest_success=2026-04-02T02:34:08Z / latest_commit=2026-04-01T02:10:00Z / site_latest=2026-04-01 / repo_content_exists=False

## 推奨修正
生成ロジックまたは入力不足を確認し、必要なら workflow を再実行

## 実施した修正
womens-magazine は高リスクまたは自動修正対象外のため原因解析のみ実施

## 修正結果
womens-magazine は高リスクまたは自動修正対象外のため原因解析のみ実施

## 次アクション
生成ロジックまたは入力不足を確認し、必要なら workflow を再実行

## 原因
latest_run=completed/success/2026-04-02T02:34:08Z / latest_success=2026-04-02T02:34:08Z / latest_commit=2026-04-01T02:10:00Z / site_latest=2026-04-01 / repo_content_exists=False

## 関連 countermeasure

