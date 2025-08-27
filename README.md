# カレンダー画像自動登録システム

## 概要

このシステムは、カレンダーの写真から特定の文字（「田」）を自動検出し、該当する日付をGoogleカレンダーに終日スケジュールとして自動登録するワークフローです。複数画像の同時処理に対応し、Windowsのファイルエクスプローラーで簡単に画像を選択できます。

## 主な機能

### 1. AI画像認識による文字検出
- ChatGPT-4o-miniを使用した高精度な画像解析
# カレンダー画像自動登録システム

## 概要

カレンダーの写真から手書きや印刷の記号（例：「田」）を自動検出し、検出した日付をGoogleカレンダーへ終日イベントとして登録するワークフローです。

OneDrive上のフォルダを監視して自動処理する運用を想定し、マルチアカウント、HEIC対応、Gmail通知など実運用を意識した機能を備えています。

## 主な機能

- AI画像認識による手書き・印刷文字の検出（OpenAI API）
- 画像圧縮（最大サイズを設定可能）
- 終日イベントの自動登録（Google Calendar API）
- マルチアカウント対応（`config.yaml` の `google_calendar.accounts`）
- OneDriveフォルダ監視（`onedrive_monitor.py`）と `--once` モード
- HEIC画像対応（`pillow-heif` を用いて PIL に統合）
- Gmail 通知（OAuth2 クレデンシャル + token を使用、Gmail API 経由）
- 重複処理防止（`processed_files.json`）

## 主なファイル

```
okaasama/
├── ai_calendar_analyzer.py       # 画像解析（HEIC対応）
├── google_calendar_manager.py    # Google Calendar API 操作
├── integrated_workflow.py        # 画像→解析→登録の統合フロー
├── onedrive_monitor.py           # OneDrive 監視スクリプト（--once をサポート）
├── gmail_notifier.py             # Gmail 通知（OAuth2 + Gmail API）
├── config_loader.py              # 設定ローダー（環境変数展開、accounts 対応）
├── config.yaml                   # 設定ファイルテンプレート
├── token*.json / credentials*.json# OAuth トークン・クレデンシャル
├── processed_files.json          # 処理済みファイルの追跡
├── test_gmail_send.py            # Gmail 通知テスト
├── test_send_email.py            # ローカル SMTP デバッグ用（任意）
├── run_monitor.bat               # タスクスケジューラーで利用するバッチ
└── requirements.txt
```

## クイックスタート

1. 依存関係をインストール:

```powershell
pip install -r requirements.txt
```

2. `config.yaml` を編集して、OneDrive の監視フォルダや Google/Gmail の設定を入力します。

3. Google API 用のクレデンシャルを用意:
    - Google Cloud Console でプロジェクト作成 → Calendar API と Gmail API を有効化
    - OAuth 同意画面の設定 → OAuth クライアントを作成
    - `credentials.json`（または `credentials_<account>.json`）をプロジェクトに配置

4. Gmail 通知の設定:
    - `config.yaml` の `gmail.credentials_file` と `gmail.token_file` を設定
    - 初回実行時にブラウザで OAuth 同意が必要（token が生成されます）

5. 動作確認: One-shot 実行

```powershell
& C:/Users/taxa/AppData/Local/Programs/Python/Python313/python.exe c:/Users/taxa/OneDrive/Develop/work/okaasama/onedrive_monitor.py --once

# または統合ワークフローを手動実行
& C:/Users/taxa/AppData/Local/Programs/Python/Python313/python.exe c:/Users/taxa/OneDrive/Develop/work/okaasama/integrated_workflow.py
```

## 設定例（`config.yaml`）

```yaml
openai:
   api_key: ""  # 環境変数 OPENAI_API_KEY でも可
   api_base: ""
   model: "gpt-4o-mini"
   max_image_size_kb: 256

google_calendar:
   accounts:
      account1:
         enabled: true
         name: "jun"
         credentials_file: "credentials.json"
         token_file: "token.json"
         calendar_id: "primary"
         email: "jun@taxa.jp"

      account2:
         enabled: true
         name: "midori"
         credentials_file: "credentials2.json"
         token_file: "token2.json"
         calendar_id: "primary"
         email: "midori@taxa.jp"

gmail:
   enabled: true
   credentials_file: "credentials_gmail.json"
   token_file: "token_gmail.json"
   from_email: "your-gmail@gmail.com"

workflow:
   event_title: "出勤"
   event_description: "カレンダー画像から自動検出された勤務日"
   dry_run: false
   monitor_path: "C:/Users/%USERNAME%/OneDrive/Develop/work/okaasama/お母様カレンダー"

logging:
   level: "INFO"
   format: "%(asctime)s - %(levelname)s - %(message)s"
```

## テスト

- Gmail 通知の単体テスト:

```powershell
& C:/Users/taxa/AppData/Local/Programs/Python/Python313/python.exe c:/Users/taxa/OneDrive/Develop/work/okaasama/test_gmail_send.py
```

- ローカル SMTP デバッグ（オプション）:

```powershell
# 別ウィンドウでデバッグSMTPサーバを起動
python -m smtpd -c DebuggingServer -n localhost:1025
# 別ターミナルで test_send_email.py を実行
& C:/Users/taxa/AppData/Local/Programs/Python/Python313/python.exe c:/Users/taxa/OneDrive/Develop/work/okaasama/test_send_email.py
```

## トラブルシュート

- Pylance で `setup_logging` の警告が出る場合は `config_loader.py` を最新にする（本リポジトリでは修正済み）
- Gmail 認証で `invalid_scope` が出る場合は `config.yaml` の `gmail.credentials_file` と `gmail.token_file` を確認し、`SCOPES` がトークンと一致しているかを確認してください
- HEIC が読み込めない場合は `pillow-heif` をインストールしていることを確認してください

## 開発ノート

- マルチアカウントは `config.yaml` の `google_calendar.accounts` 内の `enabled: true` フラグで自動検出されます
- 既存の `multi_account_enabled` フラグは廃止し、enabled アカウント数で自動判定します
- `processed_files.json` を削除/変更すると既存の重複チェック挙動が変わります。バックアップしてください

## ライセンス

個人利用・教育目的での使用を想定しています。商用利用の場合は各APIの利用規約を確認してください。

## サポート

問題がある場合は、以下を確認してください：

- `setup_instructions.md`: セットアップ手順
- ログファイル: 実行時に出力される詳細なログ
- 結果ファイル: JSON 形式の実行結果
  dry_run: false  # ドライランモード（デフォルト: false）

