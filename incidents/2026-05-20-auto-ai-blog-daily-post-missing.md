# インシデント: Auto AI Blog

- 発生日: 2026-05-20
- 対象会社: Auto AI Blog
- 対象ID: auto-ai-blog
- 異常コード: DAILY_POST_MISSING

## 現象
前日(2026-05-19)投稿が確認できない

## 影響範囲
公開サイトは到達可能だが、業務継続または品質に重大な異常あり

## 原因分類
SITE_CONFIG_MISMATCH

## 原因要約
latest_run=completed/success/2026-05-19T00:00:01Z / latest_success=2026-05-19T00:00:01Z / latest_commit=2026-05-18T23:57:54Z / site_latest=unknown

## 推奨修正
CompanyGuardian の latest post 判定設定を見直す

## 実施した修正
auto-ai-blog は高リスクまたは自動修正対象外のため原因解析のみ実施

## 修正結果
auto-ai-blog は高リスクまたは自動修正対象外のため原因解析のみ実施

## 次アクション
CompanyGuardian の latest post 判定設定を見直す

## 原因
latest_run=completed/success/2026-05-19T00:00:01Z / latest_success=2026-05-19T00:00:01Z / latest_commit=2026-05-18T23:57:54Z / site_latest=unknown

## 関連 countermeasure

