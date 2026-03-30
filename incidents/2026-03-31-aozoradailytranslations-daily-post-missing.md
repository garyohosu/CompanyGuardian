# インシデント: AozoraDailyTranslations

- 発生日: 2026-03-31
- 対象会社: AozoraDailyTranslations
- 対象ID: aozora-daily-translations
- 異常コード: DAILY_POST_MISSING

## 現象
前日翻訳が 2026-03-30 分で欠落

## 影響範囲
公開サイトは到達可能だが、業務継続または品質に重大な異常あり

## 原因分類
SITE_CONFIG_MISMATCH

## 原因要約
latest_run=completed/success/2026-03-30T02:03:15Z / latest_success=2026-03-30T02:03:15Z / latest_commit=2026-03-30T02:02:30Z / site_latest=2026-03-29

## 推奨修正
CompanyGuardian の latest post 判定設定を見直す

## 実施した修正
aozora-daily-translations は高リスクまたは自動修正対象外のため原因解析のみ実施

## 修正結果
aozora-daily-translations は高リスクまたは自動修正対象外のため原因解析のみ実施

## 次アクション
CompanyGuardian の latest post 判定設定を見直す

## 原因
latest_run=completed/success/2026-03-30T02:03:15Z / latest_success=2026-03-30T02:03:15Z / latest_commit=2026-03-30T02:02:30Z / site_latest=2026-03-29

## 関連 countermeasure

