# カレンダー画像自動登録システム - セットアップマニュアル

## 📋 **概要**

このマニュアルでは、Windows PCでの「カレンダー画像自動登録システム」のセットアップ手順を詳しく説明します。

## 🛠️ **システム要件**

- **OS**: Windows 10/11
- **Python**: 3.8以上（推奨: 3.11以上）
- **メモリ**: 最低4GB以上
- **ストレージ**: 最低1GBの空き容量
- **インターネット接続**: Google API利用のため必須

## 📦 **ステップ1: Pythonのインストール**

### 1.1 Pythonのダウンロード
1. [Python公式サイト](https://www.python.org/downloads/)にアクセス
2. **最新のPython 3.x**（3.8以上）をダウンロード
3. **Windows installer (64-bit)**を選択

### 1.2 Pythonのインストール
1. ダウンロードしたインストーラーを実行
2. **「Add Python to PATH」**にチェックを入れる
3. **「Install Now」**を選択
4. インストール完了後、コマンドプロンプトで確認：
   ```cmd
   python --version
   pip --version
   ```

### 1.3 仮想環境の作成（推奨）
```cmd
# プロジェクトディレクトリに移動
cd C:\Path\To\Your\Project

# 仮想環境を作成
python -m venv venv

# 仮想環境を有効化
venv\Scripts\activate
```

## 📥 **ステップ2: プロジェクトのダウンロード**

### 2.1 GitHubからクローン
```cmd
# リポジトリをクローン
git clone https://github.com/MiMicroAG/okaasama.git
cd okaasama
```

### 2.2 またはZIPダウンロード
1. [GitHubリポジトリ](https://github.com/MiMicroAG/okaasama)にアクセス
2. **「Code」→「Download ZIP」**を選択
3. ダウンロードしたZIPファイルを解凍

## 🔧 **ステップ3: 依存関係のインストール**

### 3.1 必要なパッケージのインストール
```cmd
# 仮想環境が有効な状態で実行
pip install -r requirements.txt
```

### 3.2 インストールされる主なパッケージ
- **openai**: OpenAI API（画像認識）
- **google-api-python-client**: Google Calendar API
- **google-auth-oauthlib**: Google認証
- **Pillow**: 画像処理
- **pillow-heif**: HEIC画像対応
- **PyYAML**: 設定ファイル処理

### 3.3 インストール確認
```cmd
# 主要パッケージの確認
python -c "import openai, googleapiclient, PIL, yaml; print('✅ すべてのパッケージが正常にインストールされました')"
```

## ⚙️ **ステップ4: Google APIの設定**

### 4.1 Google Cloud Consoleの準備
1. [Google Cloud Console](https://console.cloud.google.com/)にアクセス
2. 新しいプロジェクトを作成、または既存プロジェクトを選択
3. **「APIとサービス」→「ライブラリ」**を開く

### 4.2 APIの有効化
以下のAPIを有効化：
- **Google Calendar API**
- **Gmail API**

### 4.3 OAuth 2.0 クライアントIDの作成
1. **「APIとサービス」→「認証情報」**を開く
2. **「+認証情報を作成」→「OAuth 2.0 クライアントID」**を選択
3. アプリケーションの種類: **デスクトップアプリケーション**
4. クライアントIDを作成し、**credentials.json**をダウンロード

### 4.4 認証ファイルの配置
ダウンロードした `credentials.json` をプロジェクトフォルダに配置：
```
プロジェクトフォルダ/
├── credentials.json    # ← ここに配置
├── config.yaml
└── ...
```

## 📝 **ステップ5: 設定ファイルの準備**

### 5.1 config.yamlの作成
```cmd
# サンプルファイルをコピー
copy config.yaml.sample config.yaml
```

### 5.2 設定ファイルの編集
`config.yaml` をテキストエディタで開いて編集：

#### 5.2.1 OpenAI API設定
```yaml
openai:
  api_key: "sk-your-openai-api-key-here"  # OpenAI APIキーを設定
  api_base: ""  # 通常は空でOK
  model: "gpt-4o-mini"  # 使用するモデル
  max_image_size_kb: 256  # 画像圧縮サイズ
```

#### 5.2.2 Gmail通知設定（オプション）
```yaml
gmail:
  enabled: true  # 通知を有効にする場合
  credentials_file: "credentials.json"
  token_file: "token_gmail.json"
  from_email: "your-email@gmail.com"  # 送信元メールアドレス
  default_recipient: "recipient@example.com"  # 通知先メールアドレス
  default_subject: "お母様 勤務スケジュールを登録しました"
```

#### 5.2.3 Google Calendar設定
```yaml
google_calendar:
  accounts:
    account1:
      enabled: true
      name: "メインアカウント"
      credentials_file: "credentials.json"
      token_file: "token.json"
      calendar_id: "primary"
```

### 5.3 環境変数の設定（オプション）
APIキーを環境変数で管理する場合：
```cmd
# システム環境変数を設定
setx OPENAI_API_KEY "your-api-key-here"
```

## 🔐 **ステップ6: 初回認証**

### 6.1 Google Calendar API認証
```cmd
# 初回実行時にブラウザ認証が発生
python integrated_workflow.py --dry-run
```

### 6.2 Gmail API認証（Gmail通知を使用する場合）
```cmd
# Gmail通知機能のテスト
python test_gmail_notification.py
```

### 6.3 認証ファイルの確認
認証成功後、以下のファイルが作成されます：
- `token.json` - Google Calendar APIトークン
- `token_gmail.json` - Gmail APIトークン（Gmail通知使用時）

## 🧪 **ステップ7: 動作確認**

### 7.1 テスト画像の準備
1. 監視フォルダ `お母様カレンダー/` にカレンダー画像を配置
2. 画像は「田」の文字が含まれるカレンダー画像を使用

### 7.2 ドライランテスト
```cmd
# カレンダー登録をスキップしてテスト
python integrated_workflow.py --dry-run
```

### 7.3 OneDrive監視テスト
```cmd
# 監視機能をテスト
python onedrive_monitor.py --once
```

### 7.4 Gmail通知テスト
```cmd
# Gmail通知機能の単体テスト
python test_gmail_notification.py
```

## ⏰ **ステップ8: Windowsタスクスケジューラーの設定**

### 8.1 タスクスケジューラーの起動
1. Windows検索で「タスクスケジューラー」を検索
2. 「タスクの作成」を選択

### 8.2 タスクの基本設定
- **名前**: カレンダー画像監視
- **説明**: OneDriveフォルダを監視してカレンダー登録を実行
- **セキュリティオプション**: 最高の特権で実行

### 8.3 トリガーの設定
- **新規**をクリック
- **毎日**を選択
- **開始**: 朝9:00（任意の時間）
- **詳細設定**: 有効にチェック

### 8.4 操作の設定
- **新規**をクリック
- **操作**: プログラムの開始
- **プログラム/スクリプト**: `C:\Path\To\Python\python.exe`
- **引数の追加**: `C:\Path\To\Project\onedrive_monitor.py --once`
- **開始**: `C:\Path\To\Project`

### 8.5 条件の設定
- **電源**: 「コンピューターがAC電源で動作している場合のみタスクを開始する」
- **ネットワーク**: 「ネットワーク接続時にのみ開始する」

### 8.6 設定の確認
- タスクを作成したら、右クリック→「実行」でテスト実行
- ログを確認して正常動作するかチェック

## 🔍 **ステップ9: トラブルシューティング**

### 9.1 Pythonが見つからない
```cmd
# PATHが通っていない場合
python --version

# フルパスで実行
C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python311\python.exe --version
```

### 9.2 パッケージインストールエラー
```cmd
# pipのアップグレード
python -m pip install --upgrade pip

# プロキシ環境の場合
pip install --proxy=http://proxy.example.com:8080 -r requirements.txt
```

### 9.3 Google認証エラー
```cmd
# トークンファイルを削除して再認証
del token.json
del token_gmail.json

# 再度実行
python integrated_workflow.py --dry-run
```

### 9.4 画像処理エラー
```cmd
# pillow-heifが正しくインストールされているか確認
python -c "import pillow_heif; print('pillow-heif OK')"

# 画像ファイルが破損していないか確認
python -c "from PIL import Image; Image.open('test.jpg'); print('画像OK')"
```

### 9.5 Gmail通知が送信されない
- `config.yaml` の `gmail.enabled` が `true` になっているか確認
- `token_gmail.json` が存在するか確認
- メールアドレスが正しく設定されているか確認

### 9.6 タスクスケジューラーが動作しない
- Pythonのフルパスが正しいか確認
- プロジェクトフォルダのパスが正しいか確認
- ログファイルを確認：`%TEMP%\Schedlgu.txt`

## 📚 **参考情報**

### ファイル構成
```
プロジェクトフォルダ/
├── ai_calendar_analyzer.py      # AI画像認識モジュール
├── google_calendar_manager.py   # Google Calendar API連携
├── gmail_notifier.py            # Gmail通知機能
├── integrated_workflow.py       # 統合ワークフロー
├── onedrive_monitor.py          # OneDriveフォルダ監視
├── config_loader.py             # 設定ファイルローダー
├── config.yaml                  # 設定ファイル（作成）
├── config.yaml.sample           # 設定ファイルサンプル
├── credentials.json             # Google API認証情報（ダウンロード）
├── token.json                   # Calendar APIトークン（自動生成）
├── token_gmail.json             # Gmail APIトークン（自動生成）
├── requirements.txt             # 依存関係
├── run_monitor.bat              # バッチファイル
└── お母様カレンダー/             # 監視対象フォルダ
    └── processed_files.json     # 処理済みファイル記録
```

### 環境変数
```cmd
# 設定可能な環境変数
OPENAI_API_KEY    # OpenAI APIキー
OPENAI_API_BASE   # OpenAI APIベースURL
```

### ログレベル設定
`config.yaml` でログレベルを変更可能：
```yaml
logging:
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR
```

## 🎯 **完了チェックリスト**

- [ ] Python 3.8以上がインストール済み
- [ ] 仮想環境が作成・有効化済み
- [ ] 必要なパッケージがインストール済み
- [ ] Google Cloud ConsoleでAPIが有効化済み
- [ ] credentials.jsonがダウンロード・配置済み
- [ ] config.yamlが適切に設定済み
- [ ] Google API認証が完了
- [ ] テスト実行が成功
- [ ] Windowsタスクスケジューラーが設定済み

すべてのチェックボックスにチェックが入れば、セットアップ完了です！ 🚀
