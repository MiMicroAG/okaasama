#!/usr/bin/env python3
"""
OneDriveフォルダ監視スクリプト
指定フォルダに新しい画像が追加されたら、カレンダー自動登録ワークフローを実行する
"""

import os
import time
import logging
import json
from datetime import datetime, timedelta
from typing import List, Set, Dict, Optional, Any
from pathlib import Path
import hashlib

from integrated_workflow import IntegratedCalendarWorkflow
from config_loader import config_loader
from gmail_notifier import GmailNotifier

class OneDriveFolderMonitor:
    """OneDriveフォルダ監視クラス"""

    def __init__(self, monitor_path: str, processed_log_path: Optional[str] = None):
        """
        初期化

        Args:
            monitor_path (str): 監視対象フォルダのパス
            processed_log_path (str): 処理済みファイルログのパス
        """
        self.monitor_path = Path(monitor_path)
        self.processed_log_path = Path(processed_log_path) if processed_log_path else self.monitor_path / "processed_files.json"

        # 監視対象ファイル拡張子
        self.image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.heic'}

        # ワークフローインスタンス
        self.workflow = IntegratedCalendarWorkflow()

        # ログ設定
        config_loader.setup_logging()
        self.logger = logging.getLogger(__name__)

        # 処理済みファイルの追跡
        self.processed_files = self._load_processed_files()

    def _load_processed_files(self) -> Dict[str, dict]:
        """処理済みファイルログを読み込む"""
        if not self.processed_log_path.exists():
            return {}

        try:
            with open(self.processed_log_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            self.logger.warning(f"処理済みファイルログの読み込みに失敗: {self.processed_log_path}")
            return {}

    def _save_processed_files(self):
        """処理済みファイルログを保存"""
        try:
            self.processed_log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.processed_log_path, 'w', encoding='utf-8') as f:
                json.dump(self.processed_files, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"処理済みファイルログの保存に失敗: {e}")

    def _get_file_hash(self, file_path: Path) -> str:
        """ファイルのハッシュ値を計算"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception as e:
            self.logger.error(f"ファイルハッシュ計算エラー: {file_path} - {e}")
            return ""

    def _is_image_file(self, file_path: Path) -> bool:
        """画像ファイルかどうかを判定"""
        return file_path.suffix.lower() in self.image_extensions

    def _get_unprocessed_images(self) -> List[Path]:
        """未処理の画像ファイルを取得"""
        if not self.monitor_path.exists():
            self.logger.error(f"監視フォルダが存在しません: {self.monitor_path}")
            return []

        unprocessed_images = []

        try:
            for file_path in self.monitor_path.rglob('*'):
                if not file_path.is_file() or not self._is_image_file(file_path):
                    continue

                file_hash = self._get_file_hash(file_path)
                if not file_hash:
                    continue

                # 処理済みかチェック
                if file_hash in self.processed_files:
                    continue

                unprocessed_images.append(file_path)

        except Exception as e:
            self.logger.error(f"未処理画像ファイル取得エラー: {e}")

        return unprocessed_images

    def _mark_file_processed(self, file_path: Path, result: Dict):
        """ファイルを処理済みとしてマーク"""
        file_hash = self._get_file_hash(file_path)
        if file_hash:
            self.processed_files[file_hash] = {
                'file_path': str(file_path),
                'file_name': file_path.name,
                'processed_at': datetime.now().isoformat(),
                'result': result
            }
            self._save_processed_files()

    def process_new_images(self, notify_account: Optional[str] = None) -> Dict:
        """
        新しい画像ファイルを処理

        Returns:
            Dict: 処理結果
        """
        self.logger.info("新しい画像ファイルのチェックを開始")

        unprocessed_images = self._get_unprocessed_images()

        if not unprocessed_images:
            self.logger.info("新しい画像ファイルはありません")
            return {
                'success': True,
                'message': '新しい画像ファイルはありません',
                'processed_count': 0,
                'images': []
            }

        self.logger.info(f"新しい画像ファイル {len(unprocessed_images)} 個を検出")

        # 画像パスを文字列に変換
        image_paths = [str(path) for path in unprocessed_images]

        try:
            # ワークフロー実行
            result = self.workflow.run_complete_workflow(
                image_paths=image_paths,
                dry_run=False  # 自動実行時は常に本番モード
            )

            # 処理済みとしてマーク
            for image_path in unprocessed_images:
                self._mark_file_processed(image_path, result)

            self.logger.info(f"画像処理完了: {len(unprocessed_images)} 個")

            # メール通知送信（必要なら特定アカウントのみに制限）
            self._send_completion_notifications(result, notify_account=notify_account)

            return {
                'success': True,
                'message': f'新しい画像ファイル {len(unprocessed_images)} 個を処理しました',
                'processed_count': len(unprocessed_images),
                'images': [str(path) for path in unprocessed_images],
                'workflow_result': result
            }

        except Exception as e:
            error_msg = f"画像処理エラー: {e}"
            self.logger.error(error_msg)
            return {
                'success': False,
                'message': error_msg,
                'processed_count': 0,
                'images': [],
                'error': str(e)
            }

    def _send_completion_notifications(self, result: Dict[str, Any], notify_account: Optional[str] = None):
        """
        処理完了通知を送信
        
        Args:
            result (Dict[str, Any]): 処理結果
        """
        try:
            # ワークフローの戻り値は、直接 'found_dates' を持つフラットな構造か、
            # 'workflow_result' キーでネストされた構造のいずれかになり得る。
            # どちらにも対応するため、両方をチェックして日付リストを取得する。
            if isinstance(result, dict) and 'workflow_result' in result and isinstance(result['workflow_result'], dict):
                workflow_result = result['workflow_result']
            else:
                workflow_result = result if isinstance(result, dict) else {}

            found_dates = workflow_result.get('found_dates', []) or []

            # 有効なアカウントを取得
            enabled_accounts = config_loader.get_google_calendar_accounts_config()

            # notify_account が指定されていれば、それ以外は通知対象外にする
            if notify_account:
                enabled_accounts = {k: v for k, v in enabled_accounts.items() if k == notify_account}

            # Gmail通知インスタンス
            notifier = GmailNotifier()

            # 各アカウントに通知送信
            for account_key, account_config in enabled_accounts.items():
                email = account_config.get('email', '')
                account_name = account_config.get('name', account_key)

                if email:
                    success = notifier.send_completion_notification(
                        account_name=account_name,
                        email=email,
                        processed_dates=found_dates,
                        result=result
                    )
                    if success:
                        self.logger.info(f"通知メール送信成功: {account_name} ({email})")
                    else:
                        self.logger.error(f"通知メール送信失敗: {account_name} ({email})")

        except Exception as e:
            self.logger.exception(f"通知送信エラー: {e}")

    def run_continuous_monitoring(self, interval_seconds: int = 300):
        """
        連続監視モード

        Args:
            interval_seconds (int): チェック間隔（秒）
        """
        self.logger.info(f"OneDriveフォルダ監視を開始: {self.monitor_path}")
        self.logger.info(f"チェック間隔: {interval_seconds}秒")

        try:
            while True:
                result = self.process_new_images()

                if result['processed_count'] > 0:
                    self.logger.info(f"処理完了: {result['message']}")

                time.sleep(interval_seconds)

        except KeyboardInterrupt:
            self.logger.info("監視を停止しました")
        except Exception as e:
            self.logger.error(f"監視エラー: {e}")
        """
        連続監視モード

        Args:
            interval_seconds (int): チェック間隔（秒）
        """
        self.logger.info(f"OneDriveフォルダ監視を開始: {self.monitor_path}")
        self.logger.info(f"チェック間隔: {interval_seconds}秒")

        try:
            while True:
                result = self.process_new_images()

                if result['processed_count'] > 0:
                    self.logger.info(f"処理完了: {result['message']}")

                time.sleep(interval_seconds)

        except KeyboardInterrupt:
            self.logger.info("監視を停止しました")
        except Exception as e:
            self.logger.error(f"監視エラー: {e}")

def main():
    """メイン関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='OneDriveフォルダ監視システム')
    parser.add_argument('--once', action='store_true', help='1回だけチェックして終了')
    parser.add_argument('--notify-account', type=str, default=None, help='通知を送るアカウントキーを指定（例: account1）')
    args = parser.parse_args()
    
    print("OneDriveフォルダ監視システム")
    print("=" * 50)

    # 設定から監視フォルダを取得
    try:
        config = config_loader.get_workflow_config()
        monitor_path = config.get('monitor_path', '')

        if not monitor_path:
            print("設定ファイルに monitor_path が指定されていません")
            print("config.yamlに以下の設定を追加してください:")
            print("monitor_path: 'C:/Users/ユーザー名/OneDrive/監視フォルダ'")
            return

        print(f"監視対象フォルダ: {monitor_path}")

        # 監視インスタンス作成
        monitor = OneDriveFolderMonitor(monitor_path)

        # 初回チェック
        print("\n初回チェックを実行...")
        result = monitor.process_new_images(notify_account=args.notify_account)

        if result['success']:
            print(f"✅ {result['message']}")
        else:
            print(f"❌ {result['message']}")

        # --onceオプションが指定された場合、終了
        if args.once:
            print("\n1回チェック完了。終了します。")
            return

        # 連続監視を開始
        print(f"\n連続監視を開始します...")
        print("Ctrl+Cで停止できます")
        monitor.run_continuous_monitoring()

    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
