# インシデント: Auto AI Blog

- 発生日: 2026-07-19
- 対象会社: Auto AI Blog
- 対象ID: auto-ai-blog
- 異常コード: STALE_CONTENT

## 現象
最新記事が 2026-07-11 で停止

## 影響範囲
公開サイトは到達可能だが、業務継続または品質に重大な異常あり

## 原因分類
SITE_CONFIG_MISMATCH

## 原因要約
latest_run=completed/success/2026-07-18T03:02:34Z / latest_success=2026-07-18T03:02:34Z / latest_commit=2026-07-18T03:00:34Z / site_latest=2026-07-11

## 推奨修正
CompanyGuardian の latest post 判定設定を見直す

## 実施した修正
auto-ai-blog は高リスクまたは自動修正対象外のため原因解析のみ実施

## 修正結果
auto-ai-blog は高リスクまたは自動修正対象外のため原因解析のみ実施

## 次アクション
CompanyGuardian の latest post 判定設定を見直す

## 原因
latest_run=completed/success/2026-07-18T03:02:34Z / latest_success=2026-07-18T03:02:34Z / latest_commit=2026-07-18T03:00:34Z / site_latest=2026-07-11

## 関連 countermeasure

