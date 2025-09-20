# カレンダー画像自動登録システム - 詳細セットアップマニュアル

## 📋 **概要**

このマニュアルでは、カレンダー画像自動登録システムの詳細なセットアップ手順を説明します。特に、最新の機能である**アカウント別Gmail通知**と**グローバル重複チェック**の設定方法を重点的に解説します。

## 🏗️ **システムアーキテクチャ**

### 主要コンポーネント
- **AI画像認識**: OpenAI GPT-4 Vision APIを使用した文字検出
- **Google Calendar連携**: 複数アカウント対応のイベント登録
- **Gmail通知**: アカウント別個別通知機能
- **OneDrive監視**: 自動ファイル検知と処理
- **重複チェック**: ファイルレベル + イベントレベルの重複防止

### 最新機能
1. **アカウント別Gmail通知**: 各カレンダーオーナー宛に個別通知
2. **グローバル重複チェック**: 複数アカウント間での重複イベント検知
3. **改善された認証管理**: アカウントごとの独立した認証

## 📦 **ステップ1: 環境準備**

### 1.1 Python環境の構築
```bash
# Python 3.8+ のインストール確認
python --version

# 仮想環境の作成（推奨）
python -m venv venv
venv\Scripts\activate  # Windows
```

### 1.2 プロジェクトの取得
```bash
# GitHubからクローン
git clone https://github.com/MiMicroAG/okaasama.git
cd okaasama

# またはZIPダウンロード後解凍
```

### 1.3 依存関係のインストール
```bash
pip install -r requirements.txt
```

## 🔧 **ステップ2: Google Cloud Platform設定**

### 2.1 プロジェクト作成
1. [Google Cloud Console](https://console.cloud.google.com/)にアクセス
2. **「新しいプロジェクト」**を作成
3. プロジェクト名: `calendar-auto-register`

### 2.2 API有効化
以下のAPIを有効化：
- **Google Calendar API**
- **Gmail API** （通知機能使用時）

### 2.3 OAuth同意画面設定
1. **「APIとサービス」→「OAuth同意画面」**
2. ユーザーの種類: **外部**
3. アプリ名: `カレンダー自動登録システム`
4. スコープ: Calendar API と Gmail API のスコープを追加

### 2.4 認証情報作成
1. **「APIとサービス」→「認証情報」**
2. **「+認証情報を作成」→「OAuth 2.0 クライアントID」**
3. アプリケーションの種類: **デスクトップアプリケーション**
4. **credentials.json** をダウンロード

## ⚙️ **ステップ3: 設定ファイル詳細設定**

### 3.1 基本設定ファイルの作成
```bash
copy config.yaml.sample config.yaml
```

### 3.2 OpenAI API設定
```yaml
openai:
  api_key: "sk-your-actual-openai-api-key"  # 必須
  api_base: ""  # 通常空でOK
  model: "gpt-4o-mini"  # 推奨モデル
  max_image_size_kb: 256  # 画像圧縮サイズ
```

### 3.3 Gmail通知設定（アカウント別通知対応）
```yaml
gmail:
  enabled: true  # Gmail通知を使用する場合
  credentials_file: "credentials.json"  # Calendar APIと同じ認証情報を使用可能
  token_file: "token_gmail.json"
  from_email: "your-email@gmail.com"  # Gmailアドレス
  default_recipient: "admin@example.com"  # フォールバック用
  default_subject: "お母様 勤務スケジュールを登録しました"
```

### 3.4 Google Calendar複数アカウント設定
```yaml
google_calendar:
  accounts:
    account1:
      enabled: true
      name: "jun"
      email: "jun@taxa.jp"  # ★ 重要: このアカウントのオーナー宛に通知
      credentials_file: "credentials.json"
      token_file: "token.json"
      calendar_id: "primary"

    account2:
      enabled: true
      name: "midori"
      email: "midori@taxa.jp"  # ★ 重要: このアカウントのオーナー宛に通知
      credentials_file: "credentials2.json"  # 別アカウント用
      token_file: "token2.json"
      calendar_id: "primary"

    account3:
      enabled: false  # 使用しないアカウントはfalse
      name: "sub-account"
      email: "sub@example.com"
      credentials_file: "credentials3.json"
      token_file: "token3.json"
      calendar_id: "primary"
```

## 🔐 **ステップ4: 認証設定**

### 4.1 認証ファイルの配置
```
プロジェクトフォルダ/
├── credentials.json          # Calendar API用（全アカウント共通可能）
├── credentials2.json         # account2用（別アカウントの場合）
├── config.yaml              # 設定ファイル
└── ...
```

### 4.2 初回認証実行
```bash
# Calendar API認証（account1用）
python -c "from google_calendar_manager import GoogleCalendarManager; mgr = GoogleCalendarManager(); mgr.authenticate()"

# account2の認証（別アカウントの場合）
python -c "from google_calendar_manager import GoogleCalendarManager; mgr = GoogleCalendarManager(credentials_file='credentials2.json', token_file='token2.json'); mgr.authenticate()"

# Gmail API認証（通知機能使用時）
python -c "from gmail_notifier import GmailNotifier; notifier = GmailNotifier(); print('Gmail認証完了')"
```

## 🎯 **ステップ5: 最新機能の詳細設定**

### 5.1 アカウント別Gmail通知の仕組み
- **自動個別通知**: 各アカウントのイベント登録完了時に、そのアカウントの`email`宛に通知
- **通知内容**: アカウント名、登録日数、成功/スキップ/エラーの詳細
- **フォールバック**: `email`が未設定の場合、`default_recipient`を使用

### 5.2 グローバル重複チェックの仕組み
- **ファイルレベル**: `processed_files.json`で処理済みファイルを追跡
- **イベントレベル**: 複数アカウント間で同じ日付・タイトルのイベントを検知
- **自動スキップ**: 重複検出時は全アカウントでイベント作成をスキップ

### 5.3 監視機能の設定
```yaml
workflow:
  monitor_path: "C:/Users/%USERNAME%/OneDrive/お母様カレンダー"
  dry_run: false
```

## 🧪 **ステップ6: テスト実行**

### 6.1 基本機能テスト
```bash
# ドライランテスト（実際の登録なし）
python integrated_workflow.py --dry-run
```

### 6.2 Gmail通知テスト
```bash
# 通知機能単体テスト
python test_gmail_notification.py
```

### 6.3 OneDrive監視テスト
```bash
# 監視機能テスト（1回のみ）
python onedrive_monitor.py --once
```

### 6.4 複数アカウントテスト
```bash
# 複数アカウントでの処理テスト
python integrated_workflow.py
```

## ⏰ **ステップ7: 自動実行設定**

### 7.1 Windowsタスクスケジューラー設定
1. **タスクスケジューラー**を開く
2. **「タスクの作成」**
3. 名前: `Calendar Auto Register`
4. **「トリガー」**タブ:
   - 新規作成 → 毎日 / 毎週 / 毎月
   - 開始: 希望の時間
5. **「操作」**タブ:
   - プログラム: `C:\Path\To\Project\run_monitor.bat`
   - 開始: `C:\Path\To\Project`
6. **「設定」**タブ:
   - チェック: 「ネットワーク接続時にのみ開始する」

### 7.2 バッチファイルの確認
`run_monitor.bat`の内容:
```batch
@echo off
chcp 65001 > nul
cd /d %~dp0
python onedrive_monitor.py --once
exit
```

## 🔍 **ステップ8: 詳細トラブルシューティング**

### 8.1 認証エラー
```bash
# トークンファイル削除して再認証
del token*.json

# 認証情報ファイルの確認
dir credentials*.json
```

### 8.2 アカウント別通知の問題
```bash
# 設定確認
python -c "from config_loader import config_loader; accounts = config_loader.get_google_calendar_accounts_config(); print('アカウント設定:', accounts)"
```

### 8.3 重複チェックの問題
```bash
# processed_files.jsonの確認
type お母様カレンダー\processed_files.json

# 手動クリア
python -c "import json; empty = {}; json.dump(empty, open('お母様カレンダー/processed_files.json', 'w', encoding='utf-8'), indent=2, ensure_ascii=False)"
```

### 8.4 ログ確認
```bash
# 詳細ログの確認
python integrated_workflow.py --dry-run > debug.log 2>&1
type debug.log
```

## 📊 **ステップ9: 運用監視**

### 9.1 ログファイルの確認
- 実行ログ: コンソール出力
- エラーログ: 必要に応じてファイル出力
- 処理履歴: `processed_files.json`

### 9.2 パフォーマンス監視
- 画像処理時間: 通常10-30秒
- API呼び出し回数: アカウント数 × 日付数
- メモリ使用量: 通常100-300MB

### 9.3 定期メンテナンス
- トークンファイルの有効期限確認（90日）
- `processed_files.json`の定期クリーンアップ
- ログファイルのローテーション

## 🎉 **セットアップ完了**

これで最新機能を含むカレンダー画像自動登録システムのセットアップが完了しました。

### 主な機能
- ✅ AI画像認識による自動日付検出
- ✅ 複数アカウント対応
- ✅ アカウント別Gmail通知
- ✅ グローバル重複チェック
- ✅ OneDrive自動監視
- ✅ Windowsタスクスケジューラー連携

### 次のステップ
1. テスト画像を配置して動作確認
2. タスクスケジューラーで自動実行設定
3. 定期的にログを確認して安定動作を確認

ご質問があれば、GitHub Issuesまでお問い合わせください。
