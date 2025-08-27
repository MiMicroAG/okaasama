# カレンダー画像自動登録システム

## 概要

このシステムは、カレンダーの写真から特定の文字（「田」）を自動検出し、該当する日付をGoogleカレンダーに終日スケジュールとして自動登録するワークフローです。複数画像の同時処理に対応し、Windowsのファイルエクスプローラーで簡単に画像を選択できます。

## 主な機能

### 1. AI画像認識による文字検出
- OpenAI GPT-4oを使用した高精度な画像解析（高性能モデル）
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

### 3. 統合ワークフロー
- 画像解析からカレンダー登録まで完全自動化
- エラーハンドリング機能（リトライ処理付き）
- ドライランモード対応
- 詳細なログ出力
- Windowsファイルエクスプローラー統合

## システム構成

```
カレンダー画像自動登録システム/
├── ai_calendar_analyzer.py      # AI画像認識モジュール
├── google_calendar_manager.py   # Google Calendar API連携モジュール
├── integrated_workflow.py       # 統合ワークフロー
├── config_loader.py             # 設定ファイルローダー
├── config.yaml                  # 設定ファイル
├── requirements.txt             # 依存関係定義ファイル
├── setup_instructions.md        # セットアップ手順書
├── README.md                    # このファイル
└── 実行結果/
    ├── ai_analysis_results.json     # AI解析結果
    ├── den_dates.txt               # 検出された日付リスト
    └── workflow_results_*.json     # ワークフロー実行結果
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

### コマンドライン引数

- `--dry-run`: テストモード（実際のカレンダー登録を行わず、検出結果のみ表示）

### 設定ファイル

システムの動作は `config.yaml` で設定できます：

```yaml
openai:
  api_key: "your-openai-api-key"
  api_base: ""
  model: "gpt-4o"
  max_image_size_kb: 256  # 画像圧縮時の最大ファイルサイズ（KB）

google_calendar:
  credentials_file: "credentials.json"
  token_file: "token.json"

workflow:
  event_title: "カレンダーイベント"
  event_description: "画像から検出した日付"
  target_year: null  # nullの場合は当年
  target_month: null  # nullの場合は当月
  dry_run: false
```

### 環境変数での設定

環境変数で設定を上書きできます：

```bash
export OPENAI_API_KEY="your-key"
export GOOGLE_CALENDAR_CREDENTIALS_PATH="path/to/credentials.json"
export WORKFLOW_TARGET_YEAR=2024
export WORKFLOW_TARGET_MONTH=12
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
- **モデル**: OpenAI GPT-4o-mini
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

