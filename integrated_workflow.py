#!/usr/bin/env python3
"""
カレンダー画像解析からGoogleカレンダー登録までの統合ワークフロー
"""

import sys
import os
import datetime
import json
from typing import List, Dict, Optional
import tkinter as tk
from tkinter import filedialog

from ai_calendar_analyzer import AICalendarAnalyzer
from google_calendar_manager import GoogleCalendarManager
from gmail_notifier import GmailNotifier
from config_loader import config_loader

class IntegratedCalendarWorkflow:
    def __init__(self):
        """統合ワークフローの初期化"""
        self.ai_analyzer = AICalendarAnalyzer()
        self.calendar_manager = GoogleCalendarManager()
        self.workflow_results = {}

    def run_complete_workflow(self,
                            image_paths: List[str],
                            event_title: Optional[str] = None,
                            event_description: Optional[str] = None,
                            dry_run: Optional[bool] = None) -> Dict:
        """
        完全なワークフローを実行する

        Args:
            image_paths (List[str]): カレンダー画像のパスリスト
            event_title (Optional[str]): 登録するイベントのタイトル
            event_description (Optional[str]): イベントの説明
            dry_run (Optional[bool]): True の場合、実際の登録は行わない（テスト用）

        Returns:
            Dict: ワークフローの実行結果
        """
        # 設定からデフォルト値を取得
        workflow_config = config_loader.get_workflow_config()
        event_title = event_title or workflow_config['event_title'] or "カレンダーイベント"
        event_description = event_description or workflow_config['event_description'] or "画像から検出した日付"
        dry_run = dry_run if dry_run is not None else workflow_config['dry_run']
        
        # 有効なアカウント数を取得してマルチアカウント判定
        enabled_accounts = config_loader.get_google_calendar_accounts_config()
        is_multi_account = len(enabled_accounts) > 1
        
        print(f"デバッグ: 有効アカウント数 = {len(enabled_accounts)}")
        print(f"デバッグ: マルチアカウントモード = {is_multi_account}")
        print(f"デバッグ: workflow_config = {workflow_config}")
        
        # 型保証: Noneでないことを確認
        assert event_title is not None
        assert event_description is not None
        
        print("=" * 60)
        print("カレンダー画像自動登録ワークフロー開始")
        print("=" * 60)

        workflow_start_time = datetime.datetime.now()

        # ステップ1: 画像の存在確認
        print(f"\n【ステップ1】画像ファイルの確認")
        for image_path in image_paths:
            if not os.path.exists(image_path):
                error_msg = f"エラー: 画像ファイルが見つかりません: {image_path}"
                print(error_msg)
                return {"success": False, "error": error_msg}

        print(f"✓ 画像ファイル確認完了: {len(image_paths)}ファイル")
        for image_path in image_paths:
            print(f"  - {image_path}")

        # ステップ2: AI画像認識による「田」文字検出
        print(f"\n【ステップ2】AI画像認識による文字検出")
        print(f"検索文字: 「田」")

        all_found_dates = set()  # 重複を避けるためsetを使用
        all_analysis_results = []

        for i, image_path in enumerate(image_paths, 1):
            print(f"\n画像 {i}/{len(image_paths)}: {os.path.basename(image_path)}")
            try:
                analysis_result = self.ai_analyzer.analyze_calendar_image(
                    image_path
                )

                if not analysis_result:
                    error_msg = f"画像 {image_path} のAI画像認識に失敗しました"
                    print(f"✗ {error_msg}")
                    return {"success": False, "error": error_msg}

                all_analysis_results.append(analysis_result)
                print("✓ AI画像認識完了")

                # 日付の抽出
                found_dates = self.ai_analyzer.extract_dates_from_analysis(
                    analysis_result
                )

                for date_str in found_dates:
                    all_found_dates.add(date_str)

            except Exception as e:
                error_msg = f"画像 {image_path} の処理でエラーが発生: {e}"
                print(f"✗ {error_msg}")
                return {"success": False, "error": error_msg}

        found_dates = sorted(list(all_found_dates))  # ソートしてリストに変換

        if not found_dates:
            warning_msg = "「田」文字が書かれた日付が見つかりませんでした"
            print(f"⚠ {warning_msg}")
            return {"success": True, "warning": warning_msg, "dates_found": 0}

        print(f"\n✓ 全画像の日付抽出完了: {len(found_dates)}件")
        for date_str in found_dates:
            date_obj = datetime.datetime.fromisoformat(date_str).date()
            print(f"  - {date_obj.strftime('%Y年%m月%d日 (%A)')}")

        # ステップ3: Google Calendar API認証
        print(f"\n【ステップ3】Google Calendar API認証")

        if dry_run:
            print("⚠ ドライランモード: 実際の認証はスキップします")
            auth_success = True
        else:
            try:
                auth_success = self.calendar_manager.authenticate()
                if auth_success:
                    print("✓ Google Calendar API認証完了")
                else:
                    error_msg = "Google Calendar API認証に失敗しました"
                    print(f"✗ {error_msg}")
                    return {"success": False, "error": error_msg}

            except Exception as e:
                error_msg = f"認証でエラーが発生: {e}"
                print(f"✗ {error_msg}")
                return {"success": False, "error": error_msg}

        # ステップ4: カレンダーイベント登録
        print(f"\n【ステップ4】Googleカレンダーへのイベント登録")
        print(f"イベントタイトル: {event_title}")
        print(f"イベント説明: {event_description}")
        print(f"登録対象: {len(found_dates)}日")

        if dry_run:
            print("⚠ ドライランモード: 実際の登録はスキップします")
            calendar_results = {date: {'status': 'created', 'event_id': None, 'message': 'ドライランモード'} for date in found_dates}
            success_count = len(found_dates)
        else:
            try:
                if is_multi_account:
                    print("🔄 複数アカウントにイベントを登録します")
                    calendar_results = self.calendar_manager.create_events_for_multiple_accounts(
                        found_dates, event_title, event_description
                    )
                    # 複数アカウントの結果を集計
                    success_count = 0
                    for account_results in calendar_results.values():
                        if isinstance(account_results, dict) and 'error' not in account_results:
                            success_count += sum(1 for result in account_results.values() if result['status'] == 'created')
                else:
                    # シングルアカウントモード: 有効なアカウントの設定を使用
                    if enabled_accounts:
                        single_account_key = list(enabled_accounts.keys())[0]
                        single_account_config = enabled_accounts[single_account_key]
                        print(f"🔄 シングルアカウント ({single_account_config['name']}) にイベントを登録します")
                        single_manager = GoogleCalendarManager(
                            credentials_file=single_account_config['credentials_file'],
                            token_file=single_account_config['token_file'],
                            calendar_id=single_account_config['calendar_id']
                        )
                        if single_manager.authenticate():
                            calendar_results = single_manager.create_multiple_events(
                                found_dates, event_title, event_description
                            )
                        else:
                            calendar_results = {date: {'status': 'error', 'event_id': None, 'message': '認証失敗'} for date in found_dates}
                    else:
                        # フォールバック（通常発生しない）
                        if self.calendar_manager.authenticate():
                            calendar_results = self.calendar_manager.create_multiple_events(
                                found_dates, event_title, event_description
                            )
                        else:
                            calendar_results = {date: {'status': 'error', 'event_id': None, 'message': '認証失敗'} for date in found_dates}
                    success_count = sum(1 for result in calendar_results.values() if result['status'] == 'created')

                if success_count > 0:
                    print(f"✓ カレンダー登録完了: {success_count}/{len(found_dates)}件成功")
                else:
                    error_msg = "すべてのイベント登録に失敗しました"
                    print(f"✗ {error_msg}")
                    return {"success": False, "error": error_msg}

            except Exception as e:
                error_msg = f"カレンダー登録でエラーが発生: {e}"
                print(f"✗ {error_msg}")
                return {"success": False, "error": error_msg}
        # スケジュール登録後のメール通知
        try:
            gmail_notifier = GmailNotifier()
            for account_key, account_config in enabled_accounts.items():
                # アカウント設定からメールアドレスを取得、なければデフォルトを使用
                email = account_config.get('email') or gmail_notifier.default_recipient
                if not email:
                    print(f"⚠ アカウント {account_config['name']} のメールアドレスが設定されていないため、通知をスキップします")
                    continue
                if is_multi_account:
                    account_results = calendar_results.get(account_key, {})
                else:
                    account_results = calendar_results
                created_count = sum(1 for r in account_results.values() if r.get('status') == 'created')
                skipped_count = sum(1 for r in account_results.values() if r.get('status') == 'skipped')
                error_count = sum(1 for r in account_results.values() if r.get('status') == 'error')
                message = f"作成={created_count}件, スキップ={skipped_count}件, エラー={error_count}件"
                dates_for_account = list(account_results.keys())
                gmail_notifier.send_completion_notification(
                    account_config['name'],
                    email,
                    dates_for_account,
                    {'message': message, 'calendar_results': account_results}
                )
        except Exception as e:
            print(f"Gmail通知でエラーが発生: {e}")

        # ワークフロー完了
        workflow_end_time = datetime.datetime.now()
        execution_time = (workflow_end_time - workflow_start_time).total_seconds()

        print(f"\n" + "=" * 60)
        print("ワークフロー完了")
        print("=" * 60)
        print(f"実行時間: {execution_time:.2f}秒")
        print(f"検出日数: {len(found_dates)}日")
        print(f"登録成功: {success_count}日")

        if success_count < len(found_dates):
            print(f"登録失敗: {len(found_dates) - success_count}日")

        # 結果をまとめる
        workflow_results = {
            "success": True,
            "execution_time": execution_time,
            "image_paths": image_paths,
            "event_title": event_title,
            "event_description": event_description,
            "dry_run": dry_run,
            "ai_analysis_results": all_analysis_results,
            "found_dates": found_dates,
            "dates_count": len(found_dates),
            "calendar_results": calendar_results,
            "success_count": success_count,
            "workflow_start_time": workflow_start_time.isoformat(),
            "workflow_end_time": workflow_end_time.isoformat()
        }

        self.workflow_results = workflow_results
        return workflow_results

    def save_workflow_results(self, output_path: str):
        """
        ワークフロー結果をファイルに保存

        Args:
            output_path (str): 出力ファイルのパス
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.workflow_results, f, ensure_ascii=False, indent=2)
        print(f"ワークフロー結果を {output_path} に保存しました")

def main():
    """メイン関数"""
    print("カレンダー画像自動登録システム")
    print("使用方法: python integrated_workflow.py [--dry-run]")
    print("画像ファイルはダイアログから選択してください")

    # ドライランオプションの確認
    dry_run = "--dry-run" in sys.argv
    if dry_run:
        print("⚠ ドライランモード: 実際のカレンダー登録は行いません")

    # tkinterのルートウィンドウを作成（非表示）
    root = tk.Tk()
    root.withdraw()  # ウィンドウを非表示

    # ファイルダイアログで複数画像を選択
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

        print(f"選択された画像ファイル: {len(image_paths)}個")
        for path in image_paths:
            print(f"  - {path}")

    except Exception as e:
        print(f"ファイル選択でエラーが発生しました: {e}")
        return

    # ワークフローを実行
    workflow = IntegratedCalendarWorkflow()

    try:
        results = workflow.run_complete_workflow(
            image_paths=list(image_paths),
            dry_run=dry_run
        )

        # 結果を保存
        output_file = f"workflow_results_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        workflow.save_workflow_results(output_file)

        # 終了コード
        if results.get("success"):
            print("\\n🎉 ワークフローが正常に完了しました！")
            sys.exit(0)
        else:
            print(f"\\n❌ ワークフローでエラーが発生しました: {results.get('error')}")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\\n⚠ ユーザーによって中断されました")
        sys.exit(1)
    except Exception as e:
        print(f"\\n❌ 予期しないエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
