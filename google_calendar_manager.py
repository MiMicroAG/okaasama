#!/usr/bin/env python3
"""
Google Calendar APIを使用してスケジュールを管理するモジュール
"""

import datetime
from zoneinfo import ZoneInfo
import json
import os.path
from typing import Any, Dict, List, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config_loader import config_loader

class GoogleCalendarManager:
    def __init__(self, credentials_file: Optional[str] = None, token_file: Optional[str] = None, calendar_id: Optional[str] = None):
        """
        Google Calendar Manager の初期化
        
        Args:
            credentials_file (str): OAuth認証情報ファイルのパス
            token_file (str): アクセストークンファイルのパス
            calendar_id (str): カレンダーID（primaryまたはメールアドレス）
        """
        # 設定からファイルパスを取得
        calendar_config = config_loader.get_google_calendar_config()
        self.credentials_file = credentials_file or calendar_config['credentials_file']
        self.token_file = token_file or calendar_config['token_file']
        self.calendar_id = calendar_id or calendar_config.get('calendar_id', 'primary')
        
        # 必要なスコープ（カレンダーの読み書き権限）
        self.SCOPES = ['https://www.googleapis.com/auth/calendar']
        self.service: Optional[Any] = None
        
    def authenticate(self) -> bool:
        """
        Google Calendar APIの認証を行う
        
        Returns:
            bool: 認証成功の場合True
        """
        creds = None
        
        # トークンファイルが存在する場合、保存された認証情報を読み込む
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, self.SCOPES)
        
        # 有効な認証情報がない場合、ユーザーにログインを求める
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_file):
                    print(f"エラー: 認証情報ファイルが見つかりません: {self.credentials_file}")
                    print("Google Cloud Consoleで認証情報を作成し、credentials.jsonとして保存してください")
                    return False
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, self.SCOPES)
                creds = flow.run_local_server(port=0)
            
            # 次回のために認証情報を保存
            with open(self.token_file, 'w') as token:
                token.write(creds.to_json())
        
        try:
            self.service = build('calendar', 'v3', credentials=creds)
            print("Google Calendar APIの認証が完了しました")
            return True
        except Exception as e:
            print(f"Google Calendar API認証エラー: {e}")
            return False
    
    def create_all_day_event(self, date_str: str, title: str, description: str = "", skip_if_exists: bool = True, calendar_id: Optional[str] = None) -> Dict[str, Any]:
        """
        終日イベントを作成する（重複チェック付き）
        
        Args:
            date_str (str): 日付（YYYY-MM-DD形式）
            title (str): イベントのタイトル
            description (str): イベントの説明
            skip_if_exists (bool): 既存イベントがある場合に作成をスキップするかどうか
            calendar_id (str): カレンダーID（primaryまたはメールアドレス）
            
        Returns:
            Dict[str, Any]: 作成結果 {'status': 'created'|'skipped'|'error', 'event_id': str or None, 'message': str}
        """
        if not self.service:
            return {'status': 'error', 'event_id': None, 'message': 'Google Calendar APIが認証されていません'}
        
        # ここでself.serviceはNoneではないことが保証されている
        assert self.service is not None
        
        calendar_id = calendar_id or self.calendar_id
        
        try:
            # 重複チェック
            if skip_if_exists and self.check_existing_events(date_str, title, calendar_id):
                message = f"イベントが既に存在するためスキップ: {title} ({date_str})"
                print(f"⚠ {message}")
                return {'status': 'skipped', 'event_id': None, 'message': message}
            
            # 終日イベントの設定（Google Calendarの終日イベントは end.date が翌日（排他的））
            try:
                start_date = datetime.date.fromisoformat(date_str)
                end_date = start_date + datetime.timedelta(days=1)
                end_date_str = end_date.isoformat()
            except Exception:
                # フォールバック（フォーマット不正時は同日扱いだが通常は到達しない）
                end_date_str = date_str

            event = {
                'summary': title,
                'description': description,
                'start': {
                    'date': date_str,
                    'timeZone': 'Asia/Tokyo',
                },
                'end': {
                    'date': end_date_str,
                    'timeZone': 'Asia/Tokyo',
                },
                'reminders': {
                    'useDefault': False,
                    'overrides': [],  # リマインダーなし
                },
            }
            
            # イベントを作成
            event_result = self.service.events().insert(
                calendarId=calendar_id,
                body=event
            ).execute()
            
            message = f"イベントが作成されました: {title} ({date_str})"
            print(f"✓ {message}")
            print(f"イベントID: {event_result.get('id')}")
            return {'status': 'created', 'event_id': event_result.get('id'), 'message': message}
            
        except HttpError as error:
            message = f"Google Calendar APIエラー: {error}"
            print(f"✗ {message}")
            return {'status': 'error', 'event_id': None, 'message': message}
        except Exception as e:
            message = f"イベント作成エラー: {e}"
            print(f"✗ {message}")
            return {'status': 'error', 'event_id': None, 'message': message}
    
    def create_multiple_events(self, dates: List[str], title: str, description: str = "", skip_if_exists: bool = True, calendar_id: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """
        複数の日付に同じイベントを作成する（重複チェック付き）
        
        Args:
            dates (List[str]): 日付のリスト（YYYY-MM-DD形式）
            title (str): イベントのタイトル
            description (str): イベントの説明
            skip_if_exists (bool): 既存イベントがある場合に作成をスキップするかどうか
            calendar_id (str): カレンダーID（primaryまたはメールアドレス）
            
        Returns:
            Dict[str, Dict[str, Any]]: 各日付の作成結果
        """
        results = {}
        
        calendar_id = calendar_id or self.calendar_id
        
        print(f"複数のイベントを作成中: {title}")
        print(f"対象日数: {len(dates)}日")
        
        for date_str in dates:
            print(f"\n{date_str} にイベントを作成中...")
            result = self.create_all_day_event(date_str, title, description, skip_if_exists, calendar_id)
            results[date_str] = result
            
            if result['status'] == 'created':
                print(f"✓ {date_str}: 作成成功")
            elif result['status'] == 'skipped':
                print(f"⚠ {date_str}: スキップ（既に存在）")
            else:
                print(f"✗ {date_str}: 作成失敗 - {result['message']}")
        
        # 結果サマリー
        created_count = sum(1 for result in results.values() if result['status'] == 'created')
        skipped_count = sum(1 for result in results.values() if result['status'] == 'skipped')
        error_count = sum(1 for result in results.values() if result['status'] == 'error')
        
        print(f"\n=== 作成結果 ===")
        print(f"作成成功: {created_count}件")
        print(f"スキップ（重複）: {skipped_count}件")
        print(f"エラー: {error_count}件")
        print(f"合計: {len(dates)}件")
        
        if error_count > 0:
            print("エラーが発生した日付:")
            for date_str, result in results.items():
                if result['status'] == 'error':
                    print(f"- {date_str}: {result['message']}")
        
        return results
    
    def create_events_for_multiple_accounts(self, dates: List[str], title: str, description: str = "", skip_if_exists: bool = True) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """
        複数のGoogleアカウントのカレンダーにイベントを作成（グローバル重複チェック付き）
        
        Args:
            dates (List[str]): 日付のリスト（YYYY-MM-DD形式）
            title (str): イベントのタイトル
            description (str): イベントの説明
            skip_if_exists (bool): 既存イベントがある場合に作成をスキップするかどうか
            
        Returns:
            Dict[str, Dict[str, Dict[str, Any]]]: アカウントごとの各日付の作成結果
        """
        # 複数アカウント設定を取得
        accounts_config = config_loader.get_google_calendar_accounts_config()
        
        if not accounts_config:
            print("⚠ 有効なアカウントが見つかりません")
            print("config.yamlのaccounts設定でenabled: trueのアカウントがあるか確認してください")
            error_result = {'error': {'status': 'error', 'message': '有効なアカウントが見つかりません'}}
            return {'error_account': error_result}
        
        results = {}
        
        print(f"=== 複数アカウントにイベント登録を開始 ===")
        print(f"対象アカウント数: {len(accounts_config)}")
        print(f"対象日数: {len(dates)}")
        
        # グローバル重複チェック（全アカウントを横断してチェック）
        if skip_if_exists:
            print(f"\n--- グローバル重複チェック ---")
            dates_to_create = []
            
            for date_str in dates:
                existing_accounts = self.check_existing_events_across_accounts(date_str, title, accounts_config)
                if existing_accounts:
                    print(f"⚠ {date_str}: 既に存在するアカウント - {', '.join(existing_accounts)}")
                    # 重複がある場合は全アカウントでスキップ
                    for account_key in accounts_config.keys():
                        if account_key not in results:
                            results[account_key] = {}
                        results[account_key][date_str] = {
                            'status': 'skipped',
                            'event_id': None,
                            'message': f'他のアカウントで既に存在: {", ".join(existing_accounts)}'
                        }
                else:
                    print(f"✓ {date_str}: 新規作成可能")
                    dates_to_create.append(date_str)
        else:
            dates_to_create = dates
        
        # 重複がない日付のみ作成
        if dates_to_create:
            print(f"\n--- イベント作成 ---")
            for account_key, account_config in accounts_config.items():
                print(f"\n--- {account_config['name']} ({account_key}) のカレンダーに登録中 ---")
                
                # アカウントごとのマネージャーインスタンス作成
                manager = GoogleCalendarManager(
                    credentials_file=account_config['credentials_file'],
                    token_file=account_config['token_file']
                )
                
                if manager.authenticate():
                    # 重複がない日付のみ作成
                    account_results = manager.create_multiple_events(
                        dates_to_create, title, description, False, account_config['calendar_id']  # 個別チェックは不要
                    )
                    
                    # 既存の結果にマージ
                    if account_key not in results:
                        results[account_key] = {}
                    results[account_key].update(account_results)
                    
                    print(f"✓ {account_config['name']}: 登録完了")
                else:
                    # 認証失敗の場合
                    for date_str in dates_to_create:
                        if account_key not in results:
                            results[account_key] = {}
                        results[account_key][date_str] = {
                            'status': 'error',
                            'event_id': None,
                            'message': '認証失敗'
                        }
                    print(f"✗ {account_config['name']}: 認証失敗")
        else:
            print(f"\n--- イベント作成 ---")
            print("すべての日付で重複が検出されたため、作成をスキップします")
        
        # 全体サマリー
        print(f"\n=== 複数アカウント登録結果 ===")
        total_created = 0
        total_skipped = 0
        total_errors = 0
        
        for account_key, account_results in results.items():
            if isinstance(account_results, dict) and 'error' not in account_results:
                created_count = sum(1 for result in account_results.values() if result['status'] == 'created')
                skipped_count = sum(1 for result in account_results.values() if result['status'] == 'skipped')
                error_count = sum(1 for result in account_results.values() if result['status'] == 'error')
                
                total_created += created_count
                total_skipped += skipped_count
                total_errors += error_count
                
                print(f"{account_key}: 作成={created_count}, スキップ={skipped_count}, エラー={error_count}")
            else:
                total_errors += 1
                print(f"{account_key}: エラー")
        
        print(f"全体: 作成={total_created}, スキップ={total_skipped}, エラー={total_errors}")
        
        return results

    def check_existing_events(self, date_str: str, title: str, calendar_id: Optional[str] = None) -> bool:
        """
        指定日に同じタイトルのイベントが既に存在するかチェック
        
        Args:
            date_str (str): 日付（YYYY-MM-DD形式）
            title (str): イベントのタイトル
            calendar_id (str): カレンダーID（primaryまたはメールアドレス）
            
        Returns:
            bool: 既存イベントがある場合True
        """
        if not self.service:
            return False
        
        # ここでself.serviceはNoneではないことが保証されている
        assert self.service is not None
        
        calendar_id = calendar_id or self.calendar_id
        
        try:
            # 指定日の東京タイムの1日をUTCに変換して検索範囲を設定
            tz = ZoneInfo('Asia/Tokyo')
            target_date = datetime.date.fromisoformat(date_str)
            start_local = datetime.datetime.combine(target_date, datetime.time(0, 0, 0, tzinfo=tz))
            end_local = start_local + datetime.timedelta(days=1)
            time_min = start_local.astimezone(datetime.timezone.utc).isoformat().replace('+00:00', 'Z')
            time_max = end_local.astimezone(datetime.timezone.utc).isoformat().replace('+00:00', 'Z')

            # 指定日のイベント（開始が範囲内のもの）を取得
            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            # 同じタイトルのイベントがあるかチェック
            for event in events:
                if event.get('summary') != title:
                    continue

                # 念のため開始日が対象ローカル日付と一致するかも確認（終日/時刻あり双方対応）
                start = event.get('start', {})
                if 'date' in start:
                    # 終日イベント
                    if start.get('date') == date_str:
                        return True
                elif 'dateTime' in start:
                    # 時刻指定イベント
                    try:
                        dt = datetime.datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
                        dt_local = dt.astimezone(tz)
                        if dt_local.date().isoformat() == date_str:
                            return True
                    except Exception:
                        # 解析できない場合はタイトル一致のみで判断
                        return True
            
            return False
            
            return False
            
        except Exception as e:
            print(f"既存イベントチェックエラー: {e}")
            return False

    def check_existing_events_across_accounts(self, date_str: str, title: str, accounts_config: Dict) -> List[str]:
        """
        すべての有効アカウントで指定日のイベントが存在するかチェック
        
        Args:
            date_str (str): 日付（YYYY-MM-DD形式）
            title (str): イベントのタイトル
            accounts_config (Dict): アカウント設定
            
        Returns:
            List[str]: イベントが存在するアカウント名のリスト
        """
        existing_accounts = []
        
        for account_key, account_config in accounts_config.items():
            manager = GoogleCalendarManager(
                credentials_file=account_config['credentials_file'],
                token_file=account_config['token_file']
            )
            
            if manager.authenticate():
                if manager.check_existing_events(date_str, title, account_config['calendar_id']):
                    existing_accounts.append(account_config['name'])
        
        return existing_accounts

def main():
    """メイン関数 - テスト用"""
    # Google Calendar Managerを初期化
    calendar_manager = GoogleCalendarManager()
    
    # 認証を実行
    if not calendar_manager.authenticate():
        print("認証に失敗しました")
        return
    
    # テスト用の日付リストを読み込み
    dates_file = "/home/ubuntu/den_dates.txt"
    if os.path.exists(dates_file):
        with open(dates_file, 'r', encoding='utf-8') as f:
            dates = [line.strip() for line in f if line.strip()]
        
        print(f"読み込んだ日付: {len(dates)}件")
        for date_str in dates:
            print(f"- {date_str}")
        
        # 「母出勤」イベントを作成
        title = "母出勤"
        description = "カレンダー画像から自動検出された勤務日"
        
        results = calendar_manager.create_multiple_events(dates, title, description)
        
        # 結果をファイルに保存
        with open('/home/ubuntu/calendar_creation_results.json', 'w', encoding='utf-8') as f:
            json.dump({
                'title': title,
                'description': description,
                'dates': dates,
                'results': results,
                'creation_time': datetime.datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=2)
        
        print("\n結果を /home/ubuntu/calendar_creation_results.json に保存しました")
        
    else:
        print(f"エラー: 日付ファイルが見つかりません: {dates_file}")
        print("先にAI画像認識を実行してください")

if __name__ == "__main__":
    main()

