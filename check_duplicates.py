#!/usr/bin/env python3
"""
カレンダー重複チェック確認スクリプト
"""

from google_calendar_manager import GoogleCalendarManager
from config_loader import config_loader

def check_duplicate_events():
    """各アカウントのカレンダーで重複イベントを確認"""

    # アカウント設定を取得
    accounts_config = config_loader.get_google_calendar_accounts_config()

    print("=== カレンダー重複チェック ===")

    for account_key, account_config in accounts_config.items():
        print(f'\n--- {account_config["name"]} ({account_key}) のカレンダーをチェック ---')

        manager = GoogleCalendarManager(
            credentials_file=account_config['credentials_file'],
            token_file=account_config['token_file']
        )

        if manager.authenticate():
            # 最近の「出勤」イベントを確認
            try:
                assert manager.service is not None, "Google Calendar service is not initialized"
                service = manager.service
                events_result = service.events().list(
                    calendarId=account_config['calendar_id'],
                    q='出勤',
                    timeMin='2025-11-01T00:00:00Z',
                    timeMax='2025-11-30T23:59:59Z',
                    singleEvents=True,
                    orderBy='startTime'
                ).execute()

                events = events_result.get('items', [])
                print(f'「出勤」イベント数: {len(events)}')

                # 日付ごとのイベント数をカウント
                date_count = {}
                for event in events:
                    start = event.get('start', {})
                    date = start.get('date', '不明')
                    if date != '不明':
                        if date not in date_count:
                            date_count[date] = []
                        date_count[date].append(event.get('summary', '不明'))

                # 重複がある日付を表示
                for date, titles in date_count.items():
                    if len(titles) > 1:
                        print(f'⚠ 重複検出 {date}: {len(titles)}件')
                        for title in titles:
                            print(f'    - {title}')
                    else:
                        print(f'✓ {date}: {titles[0]}')

            except Exception as e:
                print(f'エラー: {e}')
        else:
            print('認証失敗')

if __name__ == "__main__":
    check_duplicate_events()