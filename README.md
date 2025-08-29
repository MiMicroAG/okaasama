# カレンダー画像自動登録システム

## 概要

このシステムは、カレンダーの写真から特定の文字（「田」）を自動検出し、該当する日付をGoogleカレンダーに終日スケジュールとして自動登録するワークフローです。OneDriveの監視フォルダと連携して自動実行できます。

## 主要変更点（このリポジトリの現在の状態）
- HEIC形式の画像をサポート（`pillow-heif` を利用）
- マルチアカウント対応（`config.yaml` の `google_calendar.accounts` に個別の `enabled` フラグ）
- **Gmail通知機能の追加**: スケジュール登録完了時に自動メール通知
- OneDrive監視機能の改善：バッチ起動時は1回実行して終了（`--once`）、タスクスケジューラー向けに `run_monitor.bat` を更新
- `monitor_path` に環境変数（例: `%USERNAME%`）を使えるように変更
- 生成結果や処理済みファイルは `processed_files.json` に保存され、重複処理を防止

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
├── requirements.txt             # 依存関係（pillow-heif, Gmail API対応）
├── scripts/                     # ユーティリティスクリプト
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
- email.mime.text  ← Gmail通知機能に必要

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
  - オプション無し: 連続監視（デフォルト）
- `run_monitor.bat` はタスクスケジューラー用に `--once` を渡すように更新され、バッチ内で UTF-8 (chcp 65001) を設定します。

## processed_files.json の役割
- 処理済みファイル（MD5ハッシュ）をキーに、処理日時・処理結果・ファイルパスを保存します。
- これにより同じファイルを再処理せず、重複登録を防止します。

## 追加情報・今後の改善
- より細かいログ出力や通知（メール/Slack）連携の追加
- 文字検出アルゴリズムの拡張（「田」以外の記号や手法）
- Web UIによる運用管理

---

**セットアップ手順の詳細については `SETUP.md` を参照してください。**

