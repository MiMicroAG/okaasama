#!/usr/bin/env python3
"""
AI画像認識を使用してカレンダーから「田」文字を検出するモジュール
"""

import openai
import base64
import datetime
from typing import List, Dict, Optional
import json
import os
import re
import logging
import tkinter as tk
from tkinter import filedialog
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from config_loader import config_loader
from PIL import Image, ImageEnhance, ImageFilter
import io

# HEIC対応を追加
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
    HEIC_SUPPORTED = True
except ImportError:
    HEIC_SUPPORTED = False
    print("警告: pillow-heifがインストールされていないため、HEICファイルはサポートされません")

class AICalendarAnalyzer:
    def __init__(self):
        """AI カレンダー解析クラスの初期化"""
        # 設定を読み込み
        openai_config = config_loader.get_openai_config()
        
        # OpenAIクライアントを初期化
        self.client = openai.OpenAI(
            api_key=openai_config['api_key'] or os.getenv('OPENAI_API_KEY'),
            base_url=openai_config['api_base'] or os.getenv('OPENAI_API_BASE')
        )
        self.model = openai_config['model']
        self.max_image_size_kb = openai_config['max_image_size_kb']
        self.analysis_result = ""
        self.found_dates = []
        
        # ログ設定を適用
        config_loader.setup_logging()
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        
    def encode_image(self, image_path: str) -> str:
        """
        画像をbase64エンコードする（前処理付き、256KB以内に圧縮）
        
        Args:
            image_path (str): 画像ファイルのパス
            
        Returns:
            str: base64エンコードされた画像データ
        """
        max_file_size_kb = self.max_image_size_kb  # 設定から取得
        max_file_size_bytes = max_file_size_kb * 1024
        
        # 画像を開いて前処理
        with Image.open(image_path) as img:
            # 元のファイルサイズを取得
            original_size_bytes = os.path.getsize(image_path)
            original_size_kb = original_size_bytes / 1024
            print(f"📁 元画像サイズ: {original_size_kb:.1f}KB")
            
            # RGBモードに変換
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # 画像サイズを最適化（最大2048x2048に制限）
            max_size = 2048
            if max(img.size) > max_size:
                ratio = max_size / max(img.size)
                new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            # コントラストを強調
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.2)  # コントラストを20%上げる
            
            # シャープネスを強調
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(1.1)  # シャープネスを10%上げる
            
            # ファイルサイズが256KB以内に収まるように圧縮
            quality = 95  # 初期品質
            min_quality = 30  # 最低品質
            size_reduction_step = 0.8  # サイズ削減ステップ
            
            while quality >= min_quality:
                buffer = io.BytesIO()
                img.save(buffer, format='JPEG', quality=quality, optimize=True)
                buffer_size = buffer.tell()
                
                if buffer_size <= max_file_size_bytes:
                    print(f"✓ 画像圧縮完了: {buffer_size/1024:.1f}KB (品質: {quality})")
                    buffer.seek(0)
                    return base64.b64encode(buffer.getvalue()).decode('utf-8')
                
                # 品質を下げる
                quality -= 5
                if quality < min_quality:
                    break
            
            # 品質だけでは収まらない場合、解像度を下げる
            print(f"⚠ 品質調整だけでは収まらないため、解像度を調整します")
            original_size = img.size
            current_size = list(original_size)
            
            while current_size[0] > 800 and current_size[1] > 600:  # 最低サイズ
                current_size = [int(s * size_reduction_step) for s in current_size]
                img_resized = img.resize(current_size, Image.Resampling.LANCZOS)
                
                # 最低品質で試す
                buffer = io.BytesIO()
                img_resized.save(buffer, format='JPEG', quality=min_quality, optimize=True)
                buffer_size = buffer.tell()
                
                if buffer_size <= max_file_size_bytes:
                    print(f"✓ 解像度調整後圧縮完了: {buffer_size/1024:.1f}KB ({current_size[0]}x{current_size[1]})")
                    buffer.seek(0)
                    return base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            # 最終手段: 最低品質・最低解像度で保存
            final_size = (800, 600)
            img_final = img.resize(final_size, Image.Resampling.LANCZOS)
            buffer = io.BytesIO()
            img_final.save(buffer, format='JPEG', quality=min_quality, optimize=True)
            buffer_size = buffer.tell()
            
            print(f"✓ 最終圧縮完了: {buffer_size/1024:.1f}KB (800x600, 品質{min_quality})")
            buffer.seek(0)
            return base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((openai.APIError, openai.APIConnectionError, openai.RateLimitError))
    )
    def analyze_calendar_image(self, image_path: str) -> str:
        """
        AI画像認識でカレンダーを解析する
        
        Args:
            image_path (str): カレンダー画像のパス
            
        Returns:
            str: AI解析結果
        """
        try:
            # 画像をbase64エンコード
            base64_image = self.encode_image(image_path)
            
            print(f"AI画像認識でカレンダーを解析中...")
            
            # OpenAI Vision APIに送信
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": """この画像はカレンダーの画像です。画像から正確に読み取った年月情報を優先してください。

あなたは専門的な文字認識AIです。以下の作業を高い精度で行ってください：

【重要】まず、カレンダーの年月情報を正確に読み取ってください：

【年月情報の読み取り手順】
1. カレンダーの中央上部または上部中央を探す
2. 大きな文字や目立つ位置にある数字を探す
3. 月の情報：通常「8月」「9月」などの形式（日本語）
4. 年の情報：通常「2025年」などの形式（西暦）
5. 月の数字の右側または下側に年の数字がある場合が多い
6. ヘッダー部分やタイトル部分に年月が記載されていることが多い

【年月が見つからない場合】
- 画像全体をくまなく確認
- 角や端の部分も確認
- 小さな文字や薄い文字も見逃さない
- 画像が切れている場合は、表示されている範囲で判断

【年月のフォーマット例】
- 「2025年8月」
- 「2025年 8月」
- 「2025年8月」
- 「2025年8月度」
- 「2025年8月カレンダー」

【文字認識のガイドライン】
1. 「田」という漢字を正確に特定してください
2. 「田」の特徴：
   - 田の中央に「十」のような十字の線がある
   - 上下左右に四角い枠がある
   - 上下左右に四角い枠は交差している場合も、欠落している場合も、間が空いている場合もある
   - 全体として「田」の形をしている

【確認手順】
1. カレンダーの各日付セルを1つずつ確認
2. 各セルに手書き文字があるか確認
3. 文字の形状を詳細に分析
4. 「田」の特徴に合致するか判断
5. 確信度を以下の基準で評価：
   - high: 明らかに「田」の形をしている
   - medium: 「田」に似ているが、多少の曖昧さがある
   - low: 「田」の可能性があるが、不明瞭
【出力形式】
以下のJSON形式で回答してください：

{
  "calendar_info": {
    "detected_year": 読み取れた年（数字のみ）,
    "detected_month": 読み取れた月（数字のみ）,
    "year_month_text": "画像から読み取った年月のテキスト（例: 2025年8月）",
    "detection_confidence": "year_month_detection_confidence",
    "location": "年月情報の位置（例: 中央上部、右上など）"
  },
  "found_dates": [
    {
      "day": 日付の数字（1-31）,
      "confidence": "high/medium/low",
      "description": "見つかった文字の詳細な説明",
      "location": "日付セルの位置の説明（例：左上、中央など）"
    }
  ],
  "analysis": {
    "total_cells_checked": 確認したセルの総数,
    "search_character": "田",
    "search_method": "手書き文字の形状分析",
    "confidence_threshold": "medium以上を検出対象",
    "detected_year_month": "読み取れた年月情報",
    "notes": "年月情報の読み取り結果や特記事項"
  }
}

【重要】
- 年月情報が検出できなかった場合は、found_datesを空の配列にしてください
- 日付は画像から読み取った年月の範囲内で検出してください
- 前月または翌月の薄い文字の日付セルは処理対象から除外してください
- 背景がグレーで文字が白抜きになっている日付セルは除外してください
- メインのカレンダー年月の日付のみを対象とします
- 手書き文字のみを対象（印刷文字は無視）
- 確信度がlowも含める
- 複数の「田」文字がある場合はすべて検出"""
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_completion_tokens=2000
            )
            
            result = response.choices[0].message.content
            if result is None:
                result = ""
            self.analysis_result = result
            print(f"AI解析結果:\n{result}")
            
            return result
            
        except openai.RateLimitError as e:
            print(f"OpenAIレート制限エラー: {e}")
            return ""
        except openai.APIConnectionError as e:
            print(f"OpenAI接続エラー: {e}")
            return ""
        except openai.APIError as e:
            print(f"OpenAI APIエラー: {e}")
            return ""
        except Exception as e:
            print(f"AI画像認識で予期しないエラーが発生しました: {e}")
            import traceback
            traceback.print_exc()
            return ""
    
    def extract_dates_from_analysis(self, analysis_text: str) -> List[str]:
        """
        AI解析結果から日付を抽出する
        
        Args:
            analysis_text (str): AI解析結果のテキスト
            
        Returns:
            List[str]: 日付のリスト（YYYY-MM-DD形式）
        """
        found_dates = []
        detected_year = None
        detected_month = None
        
        try:
            # JSON形式の回答を解析
            json_match = re.search(r'\{.*\}', analysis_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                data = json.loads(json_str)
                
                # 年月情報の処理
                if 'calendar_info' in data:
                    calendar_info = data['calendar_info']
                    detected_year = calendar_info.get('detected_year')
                    detected_month = calendar_info.get('detected_month')
                    year_month_text = calendar_info.get('year_month_text', '')
                    
                    print(f"📅 年月情報検出: {year_month_text}")
                    if detected_year and detected_month:
                        print(f"  検出年: {detected_year}年, 検出月: {detected_month}月")
                        print(f"  位置: {calendar_info.get('location', '不明')}")
                        print(f"  確信度: {calendar_info.get('detection_confidence', '不明')}")
                    else:
                        print("  ⚠ 年月情報を読み取れませんでした")
                        print("  年月情報が検出できなかったため、日付を登録しません")
                        return []  # 年月が検出できなかった場合は空リストを返す
                
                # yearとmonthを確定
                current_year = detected_year
                current_month = detected_month
                assert isinstance(current_year, int)
                assert isinstance(current_month, int)
                
                if 'found_dates' in data:
                    for item in data['found_dates']:
                        day = item.get('day')
                        confidence = item.get('confidence', 'low')
                        location = item.get('location', '')
                        
                        # 確信度がmedium以上の場合のみ採用（high/mediumのみ）
                        if confidence in ['high', 'medium'] and day and 1 <= day <= 31:
                            # 月の日数チェックと前月翌月の除外
                            try:
                                date_obj = datetime.date(current_year, current_month, day)
                                
                                # locationから月情報を抽出してチェック
                                month_in_location = None
                                if '月' in location:
                                    # 「8月28日」「9月1日」などのパターンを抽出
                                    month_match = re.search(r'(\d{1,2})月\d{1,2}日', location)
                                    if month_match:
                                        month_in_location = int(month_match.group(1))
                                
                                # locationに月が記載されていて、detected_monthと一致しない場合は除外
                                if month_in_location is not None and month_in_location != current_month:
                                    print(f"⚠ 翌月/前月の日付を除外: {month_in_location}月{day}日 (メインは{current_month}月)")
                                    continue
                                
                                # 背景がグレーや白抜きなどのスタイルチェック
                                if any(keyword in location.lower() for keyword in ['グレー', '白抜き', '薄い', 'grey', 'whiteout', 'faint']):
                                    print(f"⚠ グレー背景/白抜き文字の日付を除外: {day}日 (位置: {location})")
                                    continue
                                
                                found_dates.append(date_obj.isoformat())
                                print(f"✓ AI検出: {current_year}年{current_month}月{day}日 - 確信度: {confidence}")
                                print(f"  説明: {item.get('description', 'N/A')}")
                            except ValueError:
                                # 無効な日付（例: 2月30日など）はスキップ
                                print(f"⚠ 無効な日付をスキップ: {current_year}年{current_month}月{day}日")
            
        except (json.JSONDecodeError, KeyError, ValueError, TypeError) as e:
            logging.error(f"JSON解析エラー: {e} - 入力テキスト: {analysis_text[:200]}...")
            
            # JSONが失敗した場合も、年月情報が検出できなかったら日付を抽出しない
            if not detected_year or not detected_month:
                print("  ⚠ 年月情報が検出できなかったため、日付を登録しません")
                return []
            
            # current_year/current_monthを設定
            current_year = detected_year
            current_month = detected_month
            
            # 「田」という文字の近くにある数字を探す
            print("フォールバック: テキストから日付を抽出中...")
            pattern = r'(\d{1,2})(?:\D*田|\D*[\(\[]\D*田\D*[\)\]])'
            matches = re.findall(pattern, analysis_text, re.IGNORECASE)
            
            for match in matches:
                try:
                    day = int(match)
                    if 1 <= day <= 31:
                        try:
                            date_obj = datetime.date(current_year, current_month, day)  # type: ignore  # type: ignore
                            date_str = date_obj.isoformat()
                            if date_str not in found_dates:
                                found_dates.append(date_str)
                                print(f"✓ フォールバック検出: {current_year}年{current_month}月{day}日")
                        except ValueError:
                            continue
                except ValueError:
                    continue
        
        except Exception as e:
            logging.error(f"予期しないエラーが発生: {e}")
            import traceback
            traceback.print_exc()
        
        self.found_dates = found_dates
        return found_dates
    
    def save_results(self, output_path: str):
        """
        結果をJSONファイルに保存する
        
        Args:
            output_path (str): 出力ファイルのパス
        """
        results = {
            'analysis_result': self.analysis_result,
            'found_dates': self.found_dates,
            'analysis_time': datetime.datetime.now().isoformat()
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"結果を {output_path} に保存しました")

def main():
    """メイン関数 - テスト用"""
    print("AIカレンダー画像解析システム")
    print("使用方法: カレンダー画像を選択してください")
    
    # tkinterのルートウィンドウを作成（非表示）
    root = tk.Tk()
    root.withdraw()  # ウィンドウを非表示
    
    # ファイルダイアログで画像を選択
    filetypes = [
        ("画像ファイル", "*.jpg *.jpeg *.png *.bmp *.gif"),
        ("JPEGファイル", "*.jpg *.jpeg"),
        ("PNGファイル", "*.png"),
        ("すべてのファイル", "*.*")
    ]
    
    try:
        image_paths = filedialog.askopenfilenames(
            title="カレンダー画像を選択してください（複数可）",
            filetypes=filetypes
        )
        
        if not image_paths:
            print("画像ファイルが選択されませんでした")
            return
            
    except Exception as e:
        print(f"ファイル選択でエラーが発生しました: {e}")
        return
    
    analyzer = AICalendarAnalyzer()
    
    # 設定からワークフロー設定を取得
    workflow_config = config_loader.get_workflow_config()
    
    print(f"選択された画像ファイル: {len(image_paths)}個")
    for path in image_paths:
        print(f"  - {path}")
    
    all_found_dates = set()  # 重複を避けるためsetを使用
    
    # 各画像を順次処理
    for i, image_path in enumerate(image_paths, 1):
        print(f"\n=== 画像 {i}/{len(image_paths)}: {os.path.basename(image_path)} ===")
        
        if not os.path.exists(image_path):
            print(f"エラー: 画像ファイルが見つかりません: {image_path}")
            continue
        
        print("AI画像認識によるカレンダー解析開始...")
        
        # AI画像認識を実行
        analysis_result = analyzer.analyze_calendar_image(image_path)
        
        if analysis_result:
            # 日付を抽出
            found_dates = analyzer.extract_dates_from_analysis(analysis_result)
            
            # 見つかった日付を統合
            for date_str in found_dates:
                all_found_dates.add(date_str)
        else:
            print("AI解析に失敗しました")
    
    # 統合結果を表示
    found_dates_list = sorted(list(all_found_dates))
    print(f"\n{'='*60}")
    print("統合検索結果")
    print(f"{'='*60}")
    
    if found_dates_list:
        print(f"「田」が書かれた日付: {len(found_dates_list)}件")
        for date_str in found_dates_list:
            date_obj = datetime.datetime.fromisoformat(date_str).date()
            print(f"- {date_obj.strftime('%Y年%m月%d日 (%A)')}")
        
        # 結果をファイルに保存（最初の画像のディレクトリに）
        if image_paths:
            output_dir = os.path.dirname(image_paths[0])
            results_path = os.path.join(output_dir, f"batch_ai_analysis_results.json")
            dates_path = os.path.join(output_dir, f"batch_den_dates.txt")
            
            analyzer.save_results(results_path)
            
            with open(dates_path, 'w', encoding='utf-8') as f:
                for date_str in found_dates_list:
                    f.write(f"{date_str}\n")
            print(f"日付リストを {dates_path} に保存しました")
        
    else:
        print("「田」が書かれた日付は見つかりませんでした")

if __name__ == "__main__":
    main()

