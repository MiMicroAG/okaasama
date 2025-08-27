#!/usr/bin/env python3
"""
Google Calendar APIを使用してスケジュールを管理するモジュール
"""

import datetime
import os.path
from typing import List, Dict, Optional
import json

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from config_loader import config_loader

class GoogleCalendarManager:
    def __init__(self, credentials_file: Optional[str] = None, token_file: Optional[str] = None):
        """
        Google Calendar Manager の初期化
        
        Args:
            credentials_file (str): OAuth認証情報ファイルのパス
            token_file (str): アクセストークンファイルのパス
        """
        # 設定からファイルパスを取得
        calendar_config = config_loader.get_google_calendar_config()
        self.credentials_file = credentials_file or calendar_config['credentials_file']
        self.token_file = token_file or calendar_config['token_file']
        
        # 必要なスコープ（カレンダーの読み書き権限）
        self.SCOPES = ['https://www.googleapis.com/auth/calendar']
        self.service = None
        
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
    
    def create_all_day_event(self, date_str: str, title: str, description: str = "") -> bool:
        """
        終日イベントを作成する
        
        Args:
            date_str (str): 日付（YYYY-MM-DD形式）
            title (str): イベントのタイトル
            description (str): イベントの説明
            
        Returns:
            bool: 作成成功の場合True
        """
        if not self.service:
            print("エラー: Google Calendar APIが認証されていません")
            return False
        
        try:
            # 終日イベントの設定
            event = {
                'summary': title,
                'description': description,
                'start': {
                    'date': date_str,
                    'timeZone': 'Asia/Tokyo',
                },
                'end': {
                    'date': date_str,
                    'timeZone': 'Asia/Tokyo',
                },
                'reminders': {
                    'useDefault': False,
                    'overrides': [],  # リマインダーなし
                },
            }
            
            # イベントを作成
            event_result = self.service.events().insert(
                calendarId='primary',
                body=event
            ).execute()
            
            print(f"イベントが作成されました: {title} ({date_str})")
            print(f"イベントID: {event_result.get('id')}")
            return True
            
        except HttpError as error:
            print(f"Google Calendar APIエラー: {error}")
            return False
        except Exception as e:
            print(f"イベント作成エラー: {e}")
            return False
    
    def create_multiple_events(self, dates: List[str], title: str, description: str = "") -> Dict[str, bool]:
        """
        複数の日付に同じイベントを作成する
        
        Args:
            dates (List[str]): 日付のリスト（YYYY-MM-DD形式）
            title (str): イベントのタイトル
            description (str): イベントの説明
            
        Returns:
            Dict[str, bool]: 各日付の作成結果
        """
        results = {}
        
        print(f"複数のイベントを作成中: {title}")
        print(f"対象日数: {len(dates)}日")
        
        for date_str in dates:
            print(f"\n{date_str} にイベントを作成中...")
            success = self.create_all_day_event(date_str, title, description)
            results[date_str] = success
            
            if success:
                print(f"✓ {date_str}: 作成成功")
            else:
                print(f"✗ {date_str}: 作成失敗")
        
        # 結果サマリー
        success_count = sum(1 for success in results.values() if success)
        print(f"\n=== 作成結果 ===")
        print(f"成功: {success_count}/{len(dates)}件")
        
        if success_count < len(dates):
            print("失敗した日付:")
            for date_str, success in results.items():
                if not success:
                    print(f"- {date_str}")
        
        return results
    
    def check_existing_events(self, date_str: str, title: str) -> bool:
        """
        指定日に同じタイトルのイベントが既に存在するかチェック
        
        Args:
            date_str (str): 日付（YYYY-MM-DD形式）
            title (str): イベントのタイトル
            
        Returns:
            bool: 既存イベントがある場合True
        """
        if not self.service:
            return False
        
        try:
            # 指定日のイベントを取得
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=f"{date_str}T00:00:00Z",
                timeMax=f"{date_str}T23:59:59Z",
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            # 同じタイトルのイベントがあるかチェック
            for event in events:
                if event.get('summary') == title:
                    return True
            
            return False
            
        except Exception as e:
            print(f"既存イベントチェックエラー: {e}")
            return False

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

