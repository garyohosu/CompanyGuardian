# CompanyGuardian

CompanyGuardian は、親ポータルと複数のバーチャルカンパニーを毎日巡回し、異常検知、記録、再発防止策の蓄積まで行う監視リポジトリです。

## 目的

親ポータル、各バーチャルカンパニー、CompanyGuardian 自身を継続監視し、障害時に incident / countermeasure / 日報を残します。

## 実行環境

Windows 11 + WSL2 上で動作する OpenClaw を前提とします。Python 3.11 以上を推奨します。

## 定期実行

OpenClaw の cron 相当機構から日次実行します。主たる起動コマンドは `python scripts/check_targets.py` です。

## 監視対象

- 親ポータル
- 各バーチャルカンパニー
- CompanyGuardian 自身

監視対象一覧の正本は `companies/companies.yaml` です。

## 実行方法

定期実行:

```bash
python scripts/check_targets.py
```

手動実行:

```bash
python scripts/check_targets.py --trigger manual
```

## 日報

日報は `reports/daily/` に Markdown で保存します。手動再実行時は `YYYY-MM-DD_manual_XX.md` を生成します。

## インシデント

インシデント記録は `incidents/` に保存します。1 対象 1 実行あたり 1 ファイルを原則とします。

## 再発防止策

再発防止策は `countermeasures/` に保存します。既存事例を確認しながら運用知識を蓄積します。

## 会社の追加方法

新しい会社を追加するときは `companies/companies.yaml` にエントリを追加します。公開導線や GitHub repo は参考元ですが、監視対象の正本は `companies.yaml` です。

## 自己監視

CompanyGuardian 自身も監視対象です。`report_generated`、`config_valid`、`self_status` などで自己状態を確認します。

## 障害時対応

障害が出たら、まず `countermeasures/` を参照してください。既知パターンがあれば同じ運用で復旧し、必要に応じて新しい countermeasure を追加します。

## AdSense

Google AdSense の必須要件は監視対象に含みます。`/privacy-policy/` と `/contact/` の存在、収益化対象ページの公開継続、必要に応じたマーカー確認を行います。
