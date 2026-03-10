# インシデント: AozoraDailyTranslations

- 発生日: 2026-03-10
- 対象会社: AozoraDailyTranslations
- 対象ID: aozora-daily-translations
- 異常コード: DUPLICATE_CONTENT, ADSENSE_PAGE_MISSING

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
aozora-daily-translations は GITHUB_TOKEN 未設定のため自動修正スキップ

## 修正結果
aozora-daily-translations は GITHUB_TOKEN 未設定のため自動修正スキップ

## 次アクション
当日生成物を再取得して再 publish

## 原因
duplicate_fields=title / latest_repo_exists=False / previous_repo_exists=True / latest_title=The God Agni / previous_title=The God Agni

## 関連 countermeasure

