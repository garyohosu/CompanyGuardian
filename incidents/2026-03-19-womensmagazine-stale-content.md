# インシデント: WomensMagazine

- 発生日: 2026-03-19
- 対象会社: WomensMagazine
- 対象ID: womens-magazine
- 異常コード: ACTION_FAILED, STALE_CONTENT, DAILY_POST_MISSING

## 現象
最新記事が 2026-03-16 で停止

## 影響範囲
公開サイトは到達可能だが、業務継続または品質に重大な異常あり

## 原因分類
WORKFLOW_FAILED

## 原因要約
latest_run=completed/failure/2026-03-18T02:32:01Z / latest_success=2026-03-16T02:50:13Z / latest_commit=2026-03-16T02:50:09Z / site_latest=2026-03-16 / repo_content_exists=False / failure_reason=generate::Generate articles=failure | generate::Install Jekyll=skipped | generate::Build site (sanity check)=skipped

## 推奨修正
workflow を 1 回 rerun

## 実施した修正
womens-magazine workflow を 1 回再実行 (auth=gh_cli)

## 修正結果
womens-magazine 再確認後も未解決: 最新記事が 2026-03-16 で停止

## 次アクション
workflow を 1 回 rerun

## 原因
latest_run=completed/failure/2026-03-18T02:32:01Z / latest_success=2026-03-16T02:50:13Z / latest_commit=2026-03-16T02:50:09Z / site_latest=2026-03-16 / repo_content_exists=False / failure_reason=generate::Generate articles=failure | generate::Install Jekyll=skipped | generate::Build site (sanity check)=skipped

## 関連 countermeasure

