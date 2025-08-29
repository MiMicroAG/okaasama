#!/usr/bin/env python3
"""
Gmail通知機能のテストスクリプト
"""

from gmail_notifier import GmailNotifier

def test_gmail_notification():
    """Gmail通知機能をテストする"""

    # GmailNotifierの初期化
    notifier = GmailNotifier()

    if not notifier.enabled:
        print("Gmail通知機能が無効です。config.yamlでenabledをtrueに設定してください。")
        return

    # サンプルデータの作成
    account_name = "jun"
    dates = ["2025-08-25", "2025-08-26", "2025-08-27"]

    # サマリー情報の作成
    summary = {
        "message": "勤務スケジュールの自動登録が完了しました。",
        "calendar_results": {
            "2025-08-25": {"status": "登録成功"},
            "2025-08-26": {"status": "登録成功"},
            "2025-08-27": {"status": "登録成功"}
        }
    }

    print("サンプルメールを送信します...")
    print(f"宛先: {notifier.default_recipient}")
    print(f"件名: {notifier.default_subject}: {account_name}")
    print("本文:")
    print(f"アカウント: {account_name}")
    print(f"対象日数: {len(dates)}")
    print(summary["message"])
    print("\n詳細:")
    for date, result in summary["calendar_results"].items():
        print(f"- {date}: {result['status']}")

    # メール送信
    result = notifier.send_completion_notification(
        account_name=account_name,
        dates=dates,
        summary=summary
    )

    if result:
        print(f"\n✅ メール送信に成功しました！ (メッセージID: {result})")
    else:
        print("\n❌ メール送信に失敗しました。")

if __name__ == "__main__":
    test_gmail_notification()
