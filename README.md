# カレンダー画像自動登録システム

## 概要

このシステムは、カレンダーの写真から特定の文字（「田」）を自動検出し、該当する日付をGoogleカレンダーに終日スケジュールとして自動登録するワークフローです。OneDriveの監視フォルダと連携して自動実行できます。

## 主要変更点（最新）
- HEIC形式の画像をサポート（`pillow-heif`）
- マルチアカウント対応（`google_calendar.accounts` で `enabled` 制御）
- **Gmail通知機能**: 登録結果をメールで通知
- **重複登録対策の強化**:
  - Tokyo日界に合わせたUTC検索で既存イベント検出を厳密化
  - 終日イベントの `end.date` を翌日（排他的）に統一
  - 既存イベントは確実にスキップ
- **重複整理ツールの追加**: `scripts/cleanup_duplicates.py`（プレビュー/削除）、`scripts/clear_processed_entry.py`
- **スケジューラ向けワンショット実行**: `workflow.monitor_once: true` で常に1回で終了
- `run_monitor.bat` を同梱（UTF-8、`--once` 指定、終了コード反映）
- `monitor_path` で環境変数展開対応（例: `%USERNAME%`）

## 内容（ファイル構成）
```
カレンダー画像自動登録システム/
├── ai_calendar_analyzer.py      # AI画像認識モジュール（HEIC対応）
├── google_calendar_manager.py   # Google Calendar API連携モジュール（マルチアカウント）
├── gmail_notifier.py            # Gmail通知機能モジュール
├── integrated_workflow.py       # 統合ワークフロー
├── onedrive_monitor.py          # OneDriveフォルダ監視スクリプト（--once/連続監視対応）
├── config_loader.py             # 設定ファイルローダー（環境変数展開対応）
├── config.yaml                  # 設定ファイル（例を参照）
├── config.yaml.sample           # 設定ファイルサンプル
├── run_monitor.bat              # 監視スクリプト実行バッチ（タスクスケジューラー用）
├── test_gmail_notification.py   # Gmail通知機能テストスクリプト
├── requirements.txt             # 依存関係
├── scripts/                     # ユーティリティスクリプト
│   ├── cleanup_duplicates.py    # 重複イベントの検出/削除（--applyで実行）
│   └── clear_processed_entry.py # processed_files.json のエントリ削除
└── お母様カレンダー/             # テスト用画像等
    └── processed_files.json     # 監視で処理済みファイルを記録
```

## 依存関係
requirements.txt に主要ライブラリを列挙しています。主なもの:
- openai
- google-api-python-client
- google-auth-oauthlib
- tenacity
- Pillow
- pillow-heif  ← HEIC対応に必要
  （標準ライブラリの `email` を使用。追加インストール不要）

## 設定（`config.yaml` の要点）
- `openai`：OpenAI APIキーなど
- `gmail`：Gmail通知機能の設定
  - `enabled`: Gmail通知の有効/無効
  - `credentials_file`: Gmail API認証情報ファイル
  - `token_file`: Gmail APIトークンファイル
  - `from_email`: 送信元メールアドレス
  - `default_recipient`: デフォルト宛先メールアドレス
  - `default_subject`: デフォルト件名
- `google_calendar.accounts`：複数アカウント定義（例は最大4アカウント）
  - 各アカウントに `enabled: true/false` を設定して使用するアカウントを制御
  - 例:

```yaml
gmail:
  enabled: true
  credentials_file: "credentials.json"
  token_file: "token_gmail.json"
  from_email: "your-email@gmail.com"
  default_recipient: "recipient@example.com"
  default_subject: "お母様 勤務スケジュールを登録しました"

google_calendar:
  accounts:
    account1:
      enabled: false
      name: "jun"
      credentials_file: "credentials.json"
      token_file: "token.json"
      calendar_id: "primary"

    account2:
      enabled: true
      name: "midori"
      credentials_file: "credentials2.json"
      token_file: "token2.json"
      calendar_id: "primary"
```

- `workflow.monitor_path`：OneDrive監視フォルダ
  - `%USERNAME%` やその他の環境変数を使用可能（`config_loader` が `os.path.expandvars` で展開）
  - 例: `C:/Users/%USERNAME%/OneDrive/Develop/work/okaasama/お母様カレンダー`

- `workflow.dry_run`: テスト用に実際のカレンダー登録をスキップするモード

## Gmail通知機能
- スケジュール登録完了時に自動でメール通知を送信
- `gmail_notifier.py` がGmail APIを使用して通知メールを送信
- メール内容にはアカウント名、対象日数、登録結果の詳細が含まれます
- テスト用スクリプト `test_gmail_notification.py` で動作確認可能

## マルチアカウント動作
- `config_loader.get_google_calendar_accounts_config()` は `enabled: true` のアカウントのみを返します。
- ワークフローは有効なアカウント数に基づいて自動で「シングル」または「マルチ」モードを選択します。
  - 有効アカウントが1件: そのアカウントの `credentials_file` / `token_file` を使って登録
  - 複数件: 全ての有効アカウントに対して登録処理を試行

## OneDrive監視（`onedrive_monitor.py`）
- 実行オプション:
  - `--once` : 1回チェックして終了（タスクスケジューラー向け）
  - オプション無し: 連続監視
- 設定での制御: `config.yaml` の `workflow.monitor_once: true` で、オプション無しでもワンショット終了
- タスクスケジューラーは `run_monitor.bat` を起動（UTF-8/`--once` 指定済み、終了コード返却）

### タスクスケジューラーの推奨設定
- 全般: 「ユーザーがログオンしているかどうかにかかわらず実行」「隠し」ON
- 設定: 「タスクが既に実行中の場合: 新しいインスタンスを開始しない」
- トリガー: 任意の時刻で1回（短い間隔の繰り返しは不要）

## processed_files.json の役割
- 処理済みファイル（MD5ハッシュ）をキーに、処理日時・処理結果・ファイルパスを保存します。
- これにより同じファイルを再処理せず、重複登録を防止します。

## 追加情報・今後の改善
- より細かいログ出力や通知（メール/Slack）連携の追加
- 文字検出アルゴリズムの拡張（「田」以外の記号や手法）
- Web UIによる運用管理

---

## 重複整理ツールの使い方（例: 2025年11月「出勤」）

プレビュー（削除なし）:

```powershell
python .\scripts\cleanup_duplicates.py --title 出勤 --year 2025 --month 11
```

削除実行（保持は最初の1件）:

```powershell
python .\scripts\cleanup_duplicates.py --title 出勤 --year 2025 --month 11 --apply --keep-policy first
```

アカウント絞り込み（例: jun のみ）:

```powershell
python .\scripts\cleanup_duplicates.py --title 出勤 --year 2025 --month 11 --apply --account jun
```

処理済みフラグをクリア（再処理したいとき）:

```powershell
python .\scripts\clear_processed_entry.py --all
```

---

**セットアップ手順の詳細については `SETUP.md` を参照してください。**

