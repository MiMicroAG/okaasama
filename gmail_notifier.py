#!/usr/bin/env python3
"""
Gmail通知を送るためのユーティリティ
"""

import base64
import os
from typing import Any, Dict, List, Optional

from email.mime.text import MIMEText

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from config_loader import config_loader


class GmailNotifier:
    def __init__(self,
                 credentials_file: Optional[str] = None,
                 token_file: Optional[str] = None,
                 from_email: Optional[str] = None,
                 enabled: Optional[bool] = None):
        """
        Gmail Notifier 初期化

        Args:
            credentials_file: OAuth2 クライアントシークレットファイル
            token_file: Gmail API トークンファイル
            from_email: 送信元メールアドレス
            enabled: 通知機能の有効/無効
        """
        gmail_config = config_loader.get_gmail_config()
        # 設定の値を優先して上書き可能にする
        self.credentials_file = (credentials_file or
                               gmail_config.get('credentials_file',
                                               'credentials_gmail.json'))
        self.token_file = (token_file or
                          gmail_config.get('token_file', 'token_gmail.json'))
        self.from_email = from_email or gmail_config.get('from_email', '')
        enabled_str = (str(enabled) if enabled is not None else
                      str(gmail_config.get('enabled', 'False')))
        self.enabled = enabled_str.lower() in ('true', '1', 'yes')
        
        # デフォルト値を取得
        self.default_recipient = gmail_config.get('default_recipient', '')
        self.default_subject = gmail_config.get('default_subject', 'カレンダー自動登録通知')

                # Gmail 送信スコープ
        self.SCOPES = ['https://www.googleapis.com/auth/gmail.send']
        self.service: Optional[Any] = None

    def authenticate(self) -> bool:
        """Gmail API の認証を行う"""
        if not self.enabled:
            print('Gmail通知は無効です（config.yaml の gmail.enabled を参照）')
            return False

        creds = None
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, self.SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f"Gmailトークンのリフレッシュに失敗: {e}")
                    creds = None
            if not creds or not creds.valid:
                if not os.path.exists(self.credentials_file):
                    print(f"エラー: Gmail認証情報ファイルが見つかりません: {self.credentials_file}")
                    return False
                flow = (InstalledAppFlow.
                       from_client_secrets_file(self.credentials_file,
                                               self.SCOPES))
                creds = flow.run_local_server(port=0)
            # 保存
            with open(self.token_file, 'w', encoding='utf-8') as f:
                f.write(creds.to_json())

        try:
            self.service = build('gmail', 'v1', credentials=creds)
            print('Gmail API の認証が完了しました')
            return True
        except Exception as e:
            print(f"Gmail API認証エラー: {e}")
            return False

    @staticmethod
    def _create_message(to: str, subject: str, body_text: str) -> Dict[str, Any]:
        msg = MIMEText(body_text, _charset='utf-8')
        msg['to'] = to
        msg['subject'] = subject
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode('utf-8')
        return {'raw': raw}

    def send(self, to: Optional[str] = None,
             subject: Optional[str] = None,
             body_text: str = "") -> Optional[str]:
        """プレーンテキストメールを送信"""
        if not self.enabled:
            print('Gmail通知は無効です。送信をスキップします。')
            return None
        
        # デフォルト値を使用
        to = to or self.default_recipient
        subject = subject or self.default_subject
        
        if not to:
            print('宛先メールアドレスが指定されていません。')
            return None
            
        if not subject:
            print('件名が指定されていません。')
            return None
            
        if not self.service and not self.authenticate():
            return None
        
        # ここでself.serviceはNoneではないことが保証されている
        assert self.service is not None
        
        try:
            message = self._create_message(to, subject, body_text)
            sent = (self.service.users().messages()
                   .send(userId='me', body=message).execute())
            message_id = sent.get('id')
            print(f"Gmail送信に成功しました (ID: {message_id}) 対象: {to}")
            return message_id
        except Exception as e:
            print(f"Gmail送信エラー: {e}")
            return None

    def send_completion_notification(self,
                                     account_name: str,
                                     to_email: Optional[str] = None,
                                     dates: Optional[List[str]] = None,
                                     summary: Optional[Dict[str, Any]] = None
                                     ) -> Optional[str]:
        """
        スケジュール登録の完了サマリーを送信

        Args:
            account_name: 対象アカウント表示名
            to_email: 宛先メールアドレス（指定がない場合はデフォルトを使用）
            dates: 対象日付のリスト
            summary: サマリー情報（message, calendar_results など）
        """
        # デフォルト値を使用
        to_email = to_email or self.default_recipient
        subject = self.default_subject
        
        if not to_email:
            print('宛先メールアドレスが指定されていません。')
            return None
            
        subject = f"{subject}: {account_name}"

        message_lines: List[str] = []
        message_lines.append(f"アカウント: {account_name}")
        message_lines.append(f"対象日数: {len(dates) if dates else 0}")

        # summary の message を優先表示
        summary_message = (summary.get('message')
                          if summary and isinstance(summary, dict)
                          else None)
        if summary_message:
            message_lines.append(summary_message)

        # 詳細（任意）
        results = (summary.get('calendar_results')
                  if isinstance(summary, dict) else None)
        if isinstance(results, dict) and results:
            message_lines.append("\n詳細:")
            for date_str, r in results.items():
                status = (r.get('status')
                         if isinstance(r, dict) else str(r))
                message_lines.append(f"- {date_str}: {status}")

        body = "\n".join(message_lines)
        return self.send(to_email, subject, body)

