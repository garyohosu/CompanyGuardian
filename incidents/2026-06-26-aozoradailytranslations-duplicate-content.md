# インシデント: AozoraDailyTranslations

- 発生日: 2026-06-26
- 対象会社: AozoraDailyTranslations
- 対象ID: aozora-daily-translations
- 異常コード: DUPLICATE_CONTENT

## 現象
2026-06-23 と 2026-06-25 の投稿内容が重複

## 影響範囲
公開サイトは到達可能だが、業務継続または品質に重大な異常あり

## 原因分類
SELECTION_LOGIC_BROKEN

## 原因要約
duplicate_fields=title / latest_repo_exists=True / previous_repo_exists=True / latest_title=Immersed in Popular Fiction / previous_title=Immersed in Popular Fiction

## 推奨修正
作品選択ロジックを確認し、必要なら手動対応

## 実施した修正
aozora-daily-translations は高リスクまたは自動修正対象外のため原因解析のみ実施

## 修正結果
aozora-daily-translations は高リスクまたは自動修正対象外のため原因解析のみ実施

## 次アクション
作品選択ロジックを確認し、必要なら手動対応

## 原因
duplicate_fields=title / latest_repo_exists=True / previous_repo_exists=True / latest_title=Immersed in Popular Fiction / previous_title=Immersed in Popular Fiction

## 関連 countermeasure
CM-006
