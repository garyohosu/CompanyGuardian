# インシデント: AozoraDailyTranslations

- 発生日: 2026-03-11
- 対象会社: AozoraDailyTranslations
- 対象ID: aozora-daily-translations
- 異常コード: DAILY_POST_MISSING, DUPLICATE_CONTENT, ADSENSE_PAGE_MISSING

## 現象
2026-03-08 と 2026-03-09 の投稿内容が重複

## 影響範囲
公開サイトは到達可能だが、業務継続または品質に重大な異常あり

## 原因分類
PUBLISH_REUSED

## 原因要約
duplicate_fields=title / latest_repo_exists=False / previous_repo_exists=True / latest_title=The God Agni / previous_title=The God Agni

## 推奨修正
当日生成物を再取得して再 publish

## 実施した修正
aozora-daily-translations deploy workflow を 1 回再実行 (auth=gh_cli)

## 修正結果
aozora-daily-translations 再確認後も未解決: 2026-03-08 と 2026-03-09 の投稿内容が重複

## 次アクション
当日生成物を再取得して再 publish

## 原因
duplicate_fields=title / latest_repo_exists=False / previous_repo_exists=True / latest_title=The God Agni / previous_title=The God Agni

## 関連 countermeasure

