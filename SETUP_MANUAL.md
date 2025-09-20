# 運用マニュアル（詳細版）

## 1. 概要
本システムは、OneDriveフォルダに追加されたカレンダー画像から「田」文字を検出し、Googleカレンダーに終日予定を自動登録します。複数アカウント対応、Gmail通知、重複防止・整理機能を備えています。

## 2. 日常運用フロー
- カレンダー画像を `お母様カレンダー/` に保存
- タスクスケジューラーが `run_monitor.bat` を起動
- 解析→登録→メール通知（オプション）
- `processed_files.json` に処理済みとして記録

## 3. ワンショット実行（推奨）
- `config.yaml` の `workflow.monitor_once: true` を推奨
- `run_monitor.bat` は `--once` を付与し、1回実行で終了します

## 4. タスクスケジューラー設定
- 全般: 「ユーザーがログオンしているかどうかにかかわらず実行」「隠し」ON
- 操作: `run_monitor.bat` を指定（開始フォルダ=プロジェクトルート）
- 設定: 「タスクが既に実行中の場合: 新しいインスタンスを開始しない」
- トリガー: 任意の時刻で1回。短い繰り返しは不要

## 5. 重複対策と整理
### 5.1 仕組み
- 終日予定は `end.date` を翌日（排他的）で作成
- 重複チェックは「東京時間の当日0:00〜翌0:00」をUTC変換して検索
- 同タイトル・同日の既存予定は新規作成をスキップ

### 5.2 整理ツール
- プレビュー:
```powershell
python .\scripts\cleanup_duplicates.py --title 出勤 --year 2025 --month 11
```
- 削除実行（保持は最初の1件）:
```powershell
python .\scripts\cleanup_duplicates.py --title 出勤 --year 2025 --month 11 --apply --keep-policy first
```
- アカウント絞り込み（例: jun）:
```powershell
python .\scripts\cleanup_duplicates.py --title 出勤 --year 2025 --month 11 --apply --account jun
```

## 6. processed_files.json の管理
- 再処理したい場合は全消去:
```powershell
python .\scripts\clear_processed_entry.py --all
```
- 個別ファイルを消す:
```powershell
python .\scripts\clear_processed_entry.py --file IMG_1799.jpg --file IMG_1921.jpeg
```

## 7. トラブルシュート
- 画像解析に失敗する: 破損画像を除去、`pillow-heif` 確認
- 認証で失敗する: `token*.json` を削除して再認証
- DOS窓が残る/頻繁に起動: 本書の4章設定と `monitor_once` を確認

## 8. 表示上の注意
- iPhoneで2アカウントを同時表示すると、同じ予定が2件に見えます。片方のカレンダー表示をOFFにすると1件表示になります。

以上
