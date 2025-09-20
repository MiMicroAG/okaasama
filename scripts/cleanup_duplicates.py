#!/usr/bin/env python3
"""
Googleカレンダー重複イベント整理スクリプト

対象: 指定月の同一タイトル（例: 出勤）の同日重複を検出し、
プレビュー後に --apply 指定時のみ重複分を削除します（各アカウントのカレンダー内で実施）。
"""

import argparse
import datetime
import sys
import os
from typing import Dict, List, Tuple, Optional
from zoneinfo import ZoneInfo

# 親ディレクトリをモジュール検索パスに追加
SCRIPT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from googleapiclient.errors import HttpError

from google_calendar_manager import GoogleCalendarManager
from config_loader import config_loader


def to_utc_range_for_tokyo_day(start_local: datetime.datetime, end_local: datetime.datetime) -> Tuple[str, str]:
    """
    東京時間のローカル日時範囲をUTC ISO文字列へ変換
    APIの timeMin/timeMax（ISO 8601, Z）を返す
    """
    time_min = start_local.astimezone(datetime.timezone.utc).isoformat().replace('+00:00', 'Z')
    time_max = end_local.astimezone(datetime.timezone.utc).isoformat().replace('+00:00', 'Z')
    return time_min, time_max


def list_month_events_for_title(manager: GoogleCalendarManager, calendar_id: str, year: int, month: int, title: str) -> List[Dict]:
    tz = ZoneInfo('Asia/Tokyo')
    start_date = datetime.date(year, month, 1)
    # 翌月1日
    if month == 12:
        next_month = datetime.date(year + 1, 1, 1)
    else:
        next_month = datetime.date(year, month + 1, 1)

    start_local = datetime.datetime.combine(start_date, datetime.time(0, 0, 0, tzinfo=tz))
    end_local = datetime.datetime.combine(next_month, datetime.time(0, 0, 0, tzinfo=tz))
    time_min, time_max = to_utc_range_for_tokyo_day(start_local, end_local)

    events: List[Dict] = []
    page_token: Optional[str] = None
    while True:
        resp = manager.service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime',
            pageToken=page_token,
        ).execute()
        items = resp.get('items', [])
        # タイトル一致のみフィルタ
        items = [e for e in items if e.get('summary') == title]
        events.extend(items)
        page_token = resp.get('nextPageToken')
        if not page_token:
            break
    return events


def group_by_tokyo_date(events: List[Dict]) -> Dict[str, List[Dict]]:
    tz = ZoneInfo('Asia/Tokyo')
    grouped: Dict[str, List[Dict]] = {}
    for e in events:
        start = e.get('start', {})
        if 'date' in start:  # 終日
            date_key = start['date']
        else:
            dt = start.get('dateTime')
            if not dt:
                continue
            try:
                # fromisoformatはZに非対応のため置換
                dt_utc = datetime.datetime.fromisoformat(dt.replace('Z', '+00:00'))
                dt_local = dt_utc.astimezone(tz)
                date_key = dt_local.date().isoformat()
            except Exception:
                continue

        grouped.setdefault(date_key, []).append(e)
    return grouped


def select_keep_event(events_same_day: List[Dict], keep_policy: str) -> Dict:
    """同日イベントの中から残す1件を選択"""
    # created があればそれを優先
    def sort_key(e: Dict):
        created = e.get('created')
        start = e.get('start', {})
        start_dt = None
        if 'dateTime' in start:
            try:
                start_dt = datetime.datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
            except Exception:
                start_dt = None
        return (
            created or '',
            start_dt or datetime.datetime.min.replace(tzinfo=datetime.timezone.utc),
            e.get('id', '')
        )

    sorted_events = sorted(events_same_day, key=sort_key)
    return sorted_events[0] if keep_policy == 'first' else sorted_events[-1]


def cleanup_duplicates(year: int, month: int, title: str, apply_changes: bool, keep_policy: str, account_filter: Optional[str]):
    accounts = config_loader.get_google_calendar_accounts_config()
    if not accounts:
        print('有効なアカウントが見つかりません。config.yaml を確認してください。')
        return

    for key, acc in accounts.items():
        if account_filter and account_filter not in (key, acc.get('name')):
            continue

        print(f"\n=== アカウント: {acc['name']} ({key}) ===")
        manager = GoogleCalendarManager(
            credentials_file=acc['credentials_file'],
            token_file=acc['token_file']
        )
        if not manager.authenticate():
            print('認証に失敗しました。スキップします。')
            continue

        try:
            events = list_month_events_for_title(manager, acc['calendar_id'], year, month, title)
            grouped = group_by_tokyo_date(events)

            dup_total = 0
            del_total = 0
            for date_key, evs in sorted(grouped.items()):
                if len(evs) <= 1:
                    continue
                dup_total += len(evs) - 1
                keep = select_keep_event(evs, keep_policy)
                keep_id = keep.get('id')
                delete_list = [e for e in evs if e.get('id') != keep_id]

                print(f"\n⚠ 重複: {date_key} 件数={len(evs)} 保持={keep_id}")
                for e in delete_list:
                    print(f"  削除候補: id={e.get('id')} summary={e.get('summary')}")

                if apply_changes:
                    for e in delete_list:
                        try:
                            manager.service.events().delete(calendarId=acc['calendar_id'], eventId=e['id']).execute()
                            del_total += 1
                        except HttpError as he:
                            print(f"  削除失敗 id={e.get('id')} error={he}")
                else:
                    # プレビューのみ
                    pass

            if apply_changes:
                print(f"\n→ 削除合計: {del_total} 件（{acc['name']}）")
            else:
                print(f"\n→ プレビュー: 重複候補 合計 {dup_total} 件（{acc['name']}） --apply で削除します")

        except HttpError as he:
            print(f"APIエラー: {he}")


def main():
    parser = argparse.ArgumentParser(description='Googleカレンダー重複イベント整理')
    parser.add_argument('--title', default='出勤', help='対象タイトル（完全一致）')
    parser.add_argument('--year', type=int, default=2025, help='対象年（例: 2025）')
    parser.add_argument('--month', type=int, default=11, help='対象月（1-12）')
    parser.add_argument('--apply', action='store_true', help='実際に削除を実行する（指定しない場合はプレビューのみ）')
    parser.add_argument('--keep-policy', choices=['first', 'last'], default='first', help='保持するイベントの選択ポリシー')
    parser.add_argument('--account', help='対象アカウントキーまたは名前で絞り込み（任意）')
    args = parser.parse_args()

    print('Googleカレンダー重複イベント整理')
    print('================================')
    print(f"対象: {args.year}-{args.month:02d} タイトル='{args.title}'")
    print(f"動作: {'削除を実行' if args.apply else 'プレビューのみ'}（keep={args.keep_policy}）")
    if args.account:
        print(f"アカウント絞り込み: {args.account}")

    cleanup_duplicates(args.year, args.month, args.title, args.apply, args.keep_policy, args.account)


if __name__ == '__main__':
    main()
