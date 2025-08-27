# カレンダー画像自動登録システム

## 概要

このシステムは、カレンダーの写真から特定の文字（「田」）を自動検出し、該当する日付をGoogleカレンダーに終日スケジュールとして自動登録するワークフローです。複数画像の同時処理に対応し、Windowsのファイルエクスプローラーで簡単に画像を選択できます。

## 主な機能

### 1. AI画像認識による文字検出
- ChatGPT-4o-miniを使用した高精度な画像解析
- 画像自動圧縮機能（256KB以内に最適化）
- 年月情報自動読み取り機能（カレンダー中央上部の年月を検出）
- 手書き文字にも対応
- 確信度付きで結果を出力（high/medium対応、lowは除外）
- 「田」文字の検出に特化
- 複数画像の一括処理（バッチ処理対応）

### 2. Google Calendar API連携
- 終日イベントとして自動登録
- リマインダーなしで設定
- 重複チェック機能
- 複数日付の一括登録

### 4. OneDrive自動監視機能（NEW!）
- 指定フォルダを定期的に監視
- 新しい画像ファイルが追加されると自動処理
- 処理済みファイルの追跡
- Windowsタスクスケジューラー連携
- 重複登録防止機能

## システム構成

```
カレンダー画像自動登録システム/
├── ai_calendar_analyzer.py      # AI画像認識モジュール
├── google_calendar_manager.py   # Google Calendar API連携モジュール
├── integrated_workflow.py       # 統合ワークフロー
├── onedrive_monitor.py          # OneDriveフォルダ監視スクリプト
├── config_loader.py             # 設定ファイルローダー
├── config.yaml                  # 設定ファイル
├── run_monitor.bat              # 監視スクリプト実行バッチファイル
├── requirements.txt             # 依存関係定義ファイル
├── setup_instructions.md        # セットアップ手順書
├── README.md                    # このファイル
└── 実行結果/
    ├── ai_analysis_results.json     # AI解析結果
    ├── den_dates.txt               # 検出された日付リスト
    ├── workflow_results_*.json     # ワークフロー実行結果
    └── processed_files.json        # 処理済みファイル追跡ログ
```

## 使用方法

### 基本的な使用方法

```bash
# 統合ワークフロー（推奨）- 画像選択ダイアログが開きます
python integrated_workflow.py

# ドライランモード（テスト用）- 実際のカレンダー登録は行いません
python integrated_workflow.py --dry-run

# AI画像認識のみ実行 - 複数画像を選択して解析
python ai_calendar_analyzer.py
```

### 統合ワークフローの実行手順

1. **スクリプト実行**
   ```bash
   python integrated_workflow.py
   ```

2. **画像ファイル選択**
   - Windowsファイルエクスプローラーが開きます
   - 解析したいカレンダー画像を複数選択（Ctrlキーで複数選択可能）
   - 対応フォーマット: JPG, PNG, BMP, GIF

3. **自動処理**
   - 選択された画像から「田」文字をAIが自動検出
   - 検出された日付をGoogleカレンダーに終日イベントとして登録
   - 設定は `config.yaml` ファイルから読み込まれ、環境変数で上書き可能

### OneDrive自動監視機能

OneDrive上の指定フォルダを定期的に監視し、新しい画像ファイルが追加されると自動で処理を行う機能です。

#### 設定方法

1. **config.yamlに監視フォルダを設定**
   ```yaml
   workflow:
     monitor_path: "C:/Users/ユーザー名/OneDrive/監視フォルダ"
   ```

2. **監視スクリプト実行**
   ```bash
   # 初回チェックのみ
   python onedrive_monitor.py

   # 連続監視モード（Ctrl+Cで停止）
   python onedrive_monitor.py
   ```

3. **Windowsタスクスケジューラーでの定期実行**
   ```bash
   # バッチファイルを使用
   run_monitor.bat
   ```

#### Windowsタスクスケジューラー設定

1. **タスクスケジューラーを開く**
   - Windows検索で「タスクスケジューラー」を検索
   - 「タスクスケジューラー」を開く

2. **新しいタスクを作成**
   - 「操作」→「タスクの作成」
   - 名前: 「カレンダー画像監視」
   - 「最上位の特権で実行する」をチェック

3. **トリガーを設定**
   - 「トリガー」タブ→「新規」
   - 開始: 「ログオン時」
   - または「毎日」などで定期実行を設定

4. **操作を設定**
   - 「操作」タブ→「新規」
   - 操作: 「プログラムの開始」
   - プログラム/スクリプト: `C:\Users\ユーザー名\Develop\work\okaasama\run_monitor.bat`
   - 開始: プロジェクトフォルダのパス

5. **完了**
   - 「OK」をクリックして保存

#### 監視機能の特徴

- **自動検知**: 新しい画像ファイル（JPG, PNG, BMP, GIF）を自動検知
- **重複防止**: 処理済みファイルを追跡し、重複処理を防止
- **ログ記録**: 処理結果を `processed_files.json` に保存
- **エラーハンドリング**: 処理エラー時も継続監視
- **柔軟な間隔**: チェック間隔をカスタマイズ可能（デフォルト5分）

### 設定ファイル

システムの動作は `config.yaml` で設定できます：

```yaml
openai:
  api_key: "your-openai-api-key"  # 環境変数 OPENAI_API_KEY を使用
  api_base: ""  # 環境変数 OPENAI_API_BASE を使用（オプション）
  model: "gpt-4o-mini"  # 使用するモデル
  max_image_size_kb: 256  # 画像圧縮時の最大ファイルサイズ（KB）

google_calendar:
  credentials_file: "credentials.json"
  token_file: "token.json"

workflow:
  event_title: "母出勤"  # 登録するイベントのタイトル
  event_description: "カレンダー画像から自動検出された勤務日"  # イベントの説明
  dry_run: false  # ドライランモード（デフォルト: false）
  monitor_path: "C:/Users/ユーザー名/OneDrive/監視フォルダ"  # OneDrive監視フォルダのパス（オプション）
```

### 環境変数での設定

環境変数で設定を上書きできます：

```bash
export OPENAI_API_KEY="your-openai-api-key"
export OPENAI_API_BASE="your-api-base-url"  # オプション
export GOOGLE_CALENDAR_CREDENTIALS_PATH="path/to/credentials.json"
export WORKFLOW_MONITOR_PATH="C:/Users/ユーザー名/OneDrive/監視フォルダ"  # オプション
```

## 実行結果例

### 検出された日付（2025年9月）

| 日付 | 曜日 | 確信度 | 説明 |
|------|------|--------|------|
| 9月1日 | 月曜日 | 高 | 日付の右上に手書きで「田」と明確に見える |
| 9月2日 | 火曜日 | 高 | 日付の右上に手書きで「田」と明確に見える |
| 9月5日 | 金曜日 | 高 | 日付の右上に手書きで「田」と明確に見える |
| 9月6日 | 土曜日 | 中 | 「田」に似た文字で、「由」や「甲」に近いが判読可能 |
| 9月11日 | 木曜日 | 中 | 手書き文字はやや崩れているが「田」らしい枠組みが見える |
| 9月15日 | 月曜日 | 高 | 日付部分に「田」の字が明確に見える |
| 9月16日 | 火曜日 | 中 | 「田」か「由」に似た文字が薄く書かれている |
| 9月17日 | 水曜日 | 高 | 日付の右上に手書きで「田」と明確に見える |
| 9月20日 | 土曜日 | 高 | 「田」の文字が日付に隣接してはっきり書かれている |
| 9月22日 | 月曜日 | 高 | 日付横に「田」が明確に書かれている |
| 9月24日 | 水曜日 | 高 | 日付の横に濃く「田」が書かれている |
| 9月29日 | 月曜日 | 高 | 日付横に「田」と判別可能な漢字が書かれている |

**合計: 12日間**

### パフォーマンス

- **実行時間**: 約9.2秒
- **検出精度**: 高確信度8日、中確信度4日
- **成功率**: 100%（ドライランモード）

## セットアップ

### 1. 必要なライブラリのインストール

```bash
pip install -r requirements.txt
```

または個別にインストール:

```bash
pip install openai google-api-python-client google-auth-httplib2 google-auth-oauthlib tenacity
```

### 2. Google Calendar API の設定

詳細は `setup_instructions.md` を参照してください。

1. Google Cloud Console でプロジェクトを作成
2. Google Calendar API を有効化
3. OAuth 同意画面を設定
4. 認証情報を作成し、`credentials.json` として保存

### 3. 設定ファイルの準備

`config.yaml` ファイルを編集して、以下の設定を行ってください：

```yaml
openai:
  api_key: ""  # OpenAI APIキー（環境変数 OPENAI_API_KEY が優先）
  api_base: ""  # OpenAI APIベースURL（環境変数 OPENAI_API_BASE が優先）
  model: "gpt-4o-mini"  # 使用するモデル

google_calendar:
  credentials_file: "credentials.json"  # OAuth認証情報ファイル
  token_file: "token.json"  # アクセストークンファイル

workflow:
  event_title: "母出勤"  # 登録するイベントのタイトル
  event_description: "カレンダー画像から自動検出された勤務日"  # イベントの説明
  target_year: 2025  # 対象年
  target_month: 9  # 対象月
  dry_run: false  # ドライランモード（デフォルト: false）

logging:
  level: "INFO"  # ログレベル（DEBUG, INFO, WARNING, ERROR）
  format: "%(asctime)s - %(levelname)s - %(message)s"  # ログフォーマット
```

**注意**: 環境変数が設定されている場合は、YAMLファイルよりも環境変数が優先されます。

## 技術仕様

### AI画像認識
- **モデル**: OpenAI GPT-4.1-mini
- **入力**: JPEG/PNG画像（base64エンコード）
- **出力**: JSON形式の解析結果
- **対応文字**: 「田」（手書き・印刷問わず）
- **リトライ処理**: ネットワークエラー時の自動リトライ（最大3回）

### Google Calendar API
- **API バージョン**: v3
- **認証方式**: OAuth 2.0
- **スコープ**: `https://www.googleapis.com/auth/calendar`
- **イベント形式**: 終日イベント
- **タイムゾーン**: Asia/Tokyo

### システム要件
- **Python**: 3.11以上
- **OS**: Windows 10/11（ファイルエクスプローラー統合）
- **インターネット接続**: 必須（AI API、Google API使用のため）

## エラーハンドリング

システムは以下のエラーに対して適切に対処します：

- 画像ファイルが見つからない
- AI画像認識の失敗（リトライ処理付き）
- Google Calendar API認証の失敗
- ネットワーク接続エラー（自動リトライ）
- 権限不足エラー
- JSON解析エラー（フォールバック処理）
- レート制限エラー（リトライ処理）

## セキュリティ

- 認証情報（`credentials.json`, `token.json`）は機密情報として扱う
- APIキーの適切な管理
- 最小権限の原則に従ったスコープ設定

## 今後の拡張可能性

1. **他の文字への対応**: 「田」以外の文字や記号の検出
2. **複数月対応**: 年間カレンダーの一括処理
3. **Web UI**: ブラウザベースのインターフェース
4. **スケジュール管理**: 既存イベントの更新・削除機能
5. **通知機能**: 登録完了時のメール通知

## ライセンス

このシステムは教育・個人利用目的で開発されました。商用利用の場合は、使用するAPIの利用規約を確認してください。

## サポート

システムに関する質問や問題がある場合は、以下のファイルを確認してください：

- `setup_instructions.md`: セットアップ手順
- ログファイル: 実行時に出力される詳細なログ
- 結果ファイル: JSON形式の実行結果

