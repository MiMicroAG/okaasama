#!/usr/bin/env python3
"""Gmail通知モジュール
OAuth2（credentials + token）を使って Gmail API 経由で通知メールを送信する。

責務を小さなメソッドに分割し、ログを充実させる。
"""

import os
import logging
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.exceptions import RefreshError
from googleapiclient.discovery import build

from config_loader import config_loader


class GmailNotifier:
    """Gmail通知クラス（Gmail API + OAuth2）"""

    # トークンに合わせて gmail.send を使用（既存の token_gmail.json に合わせる）
    SCOPES = ['https://www.googleapis.com/auth/gmail.send']

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.config = config_loader.get_gmail_config()
        self.logger = logger or logging.getLogger(__name__)
        # 型を汎用化して外部ライブラリ由来の Credentials 型差分による静的エラーを避ける
        self.credentials: Optional[Any] = None

    def _validate_config(self) -> bool:
        missing = []
        for key in ('credentials_file', 'token_file', 'from_email'):
            if not self.config.get(key):
                missing.append(key)
        if missing:
            self.logger.error('Gmail設定に不足があります: %s', ','.join(missing))
            return False
        return True

    def _load_credentials(self) -> bool:
        """トークンをロードし、必要ならブラウザでの認証を行う。"""
        try:
            creds = None
            token_path = self.config['token_file']
            cred_path = self.config['credentials_file']

            if os.path.exists(token_path):
                creds = Credentials.from_authorized_user_file(token_path, self.SCOPES)

            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    self.logger.debug('トークンをリフレッシュします')
                    try:
                        creds.refresh(Request())
                    except RefreshError:
                        # スコープ不一致などでリフレッシュできない場合は再認証フローへ
                        self.logger.warning('トークンのリフレッシュに失敗しました（RefreshError）。再認証を試みます')
                        creds = None
                else:
                    if not os.path.exists(cred_path):
                        self.logger.error('認証情報ファイルが見つかりません: %s', cred_path)
                        return False
                    flow = InstalledAppFlow.from_client_secrets_file(cred_path, self.SCOPES)
                    creds = flow.run_local_server(port=0)

                # 保存（creds が None でないことを確認してから）
                if creds is not None:
                    with open(token_path, 'w', encoding='utf-8') as f:
                        f.write(creds.to_json())

            self.credentials = creds
            # 詳細ログ: 認証情報の状態を出力（token の有無、expired フラグなど）
            try:
                token_val = getattr(creds, 'token', None)
                expired = getattr(creds, 'expired', None)
                refresh_token = getattr(creds, 'refresh_token', None)
                self.logger.debug('Gmail credentials status: token=%s, expired=%s, refresh_token=%s', token_val, expired, bool(refresh_token))
            except Exception:
                # ここで例外が出ても処理を止めない
                self.logger.exception('Gmail credentials 状態のログ出力中に例外が発生しました')

            self.logger.info('Gmail OAuth2 認証済み（token=%s）', getattr(creds, 'token', None))
            return True

        except Exception:
            self.logger.exception('認証処理で例外が発生しました')
            return False

    def _build_message(self, to_email: str, subject: str, body: str) -> MIMEMultipart:
        msg = MIMEMultipart()
        msg['From'] = self.config['from_email']
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        return msg

    def _send_via_gmail_api(self, msg: MIMEMultipart) -> bool:
        try:
            # 送信前のデバッグ情報を出力
            try:
                creds = self.credentials
                self.logger.debug('Sending via Gmail API - credentials token=%s expired=%s', getattr(creds, 'token', None), getattr(creds, 'expired', None))
            except Exception:
                self.logger.exception('送信前の資格情報デバッグ出力で例外が発生しました')

            service = build('gmail', 'v1', credentials=self.credentials)
            raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
            result = service.users().messages().send(userId='me', body={'raw': raw}).execute()
            self.logger.info('Gmail API 送信成功 id=%s', result.get('id'))
            self.logger.debug('Gmail API send result: %s', result)
            return True
        except Exception:
            # 例外情報を詳細にログ出力して False を返す
            import traceback
            tb = traceback.format_exc()
            self.logger.error('Gmail API 送信に失敗しました: %s', tb)
            self.logger.exception('Gmail API 送信に失敗しました')
            return False

    def send_notification(self, to_email: str, subject: str, body: str) -> bool:
        """外部呼び出し用: メール送信を行う。"""
        try:
            if not self.config.get('enabled', 'False').lower() == 'true':
                self.logger.info('Gmail通知が無効化されているためスキップ')
                return True

            if not to_email:
                self.logger.warning('宛先メールアドレスが指定されていません。スキップします')
                return True

            if not self._validate_config():
                return False

            if not self.credentials or not getattr(self.credentials, 'valid', False) or not getattr(self.credentials, 'token', None):
                if not self._load_credentials():
                    return False

            msg = self._build_message(to_email, subject, body)
            # ログ: 送信予定の件名と本文（デバッグ・検証用）
            self.logger.info('send_notification: subject=%s', subject)
            # 本文は冗長になり得るため DEBUG でも出力可能だが、ここでは INFO として記録する
            self.logger.info('send_notification: body=\n%s', body)
            return self._send_via_gmail_api(msg)

        except Exception:
            self.logger.exception('send_notification の実行中に例外が発生しました')
            return False

    def send_completion_notification(self, account_name: str, email: str, processed_dates: List[str], result: Dict[str, Any]):
        """処理完了通知を作成して送信するヘルパー

        processed_dates が空の場合でも、result の中に日付情報が存在する可能性があるため、
        複数の候補領域（found_dates、workflow_result.found_dates、calendar_results）を順に検査して
        日付リストを組み立てます。
        """
        # 優先: 引数の processed_dates -> result['found_dates'] -> result['workflow_result']['found_dates'] -> calendar_results
        dates_list: List[str] = []
        if processed_dates:
            dates_list = processed_dates[:]
        else:
            if isinstance(result, dict):
                # 1) 直接 found_dates
                def _normalize_found_dates(raw_found):
                    out = []
                    if not raw_found:
                        return out
                    for item in raw_found:
                        # 文字列であればそのまま
                        if isinstance(item, str):
                            out.append(item)
                        # dict 形式で day を持つ場合、年/月 情報があれば ISO 形式に組み立てる
                        elif isinstance(item, dict):
                            day = item.get('day') or item.get('date')
                            if day is not None:
                                # 年月情報を探す
                                cal = None
                                if isinstance(result.get('calendar_info'), dict):
                                    cal = result.get('calendar_info')
                                elif isinstance(result.get('workflow_result'), dict) and isinstance(result['workflow_result'].get('calendar_info'), dict):
                                    cal = result['workflow_result'].get('calendar_info')

                                if isinstance(cal, dict):
                                    year = cal.get('detected_year') or cal.get('year')
                                    month = cal.get('detected_month') or cal.get('month')
                                    try:
                                        if year is not None and month is not None:
                                            out.append(f"{int(year):04d}-{int(month):02d}-{int(day):02d}")
                                        else:
                                            out.append(str(day))
                                    except Exception:
                                        out.append(str(day))
                                else:
                                    out.append(str(day))
                            else:
                                # fallback: stringify the dict
                                out.append(str(item))
                        else:
                            out.append(str(item))
                    return out

                if result.get('found_dates'):
                    dates_list = _normalize_found_dates(result.get('found_dates'))
                # 2) ネストされた workflow_result
                elif isinstance(result.get('workflow_result'), dict) and result['workflow_result'].get('found_dates'):
                    dates_list = _normalize_found_dates(result['workflow_result'].get('found_dates'))
                # 3) calendar_results に created として保存されている日付を抽出
                elif isinstance(result.get('calendar_results'), dict):
                    cr = result['calendar_results']
                    extracted = []
                    # calendar_results の形は二通りあり得る:
                    # - {date: {status: 'created', ...}}  (single account)
                    # - {account: {date: {status: 'created', ...}}} (multi account)
                    # それぞれに対応して created な日付を収集する
                    sample = next(iter(cr.values()), None)
                    if sample and isinstance(sample, dict) and any(isinstance(v, dict) and 'status' in v for v in sample.values() if isinstance(sample, dict)):
                        # nested per-account? fallthrough to account loop
                        pass
                    # Try flat mapping date->info
                    for k, v in cr.items():
                        if isinstance(v, dict) and v.get('status') == 'created':
                            extracted.append(str(k))
                        elif isinstance(v, dict):
                            # maybe nested per-account
                            for kk, vv in v.items():
                                if isinstance(vv, dict) and vv.get('status') == 'created':
                                    extracted.append(str(kk))
                    if extracted:
                        dates_list = sorted(list(set(extracted)))
                # normalize any remaining items to strings
                if dates_list:
                    dates_list = [str(d) for d in dates_list]
            # デバッグ: 抽出された日付リストをログに出力
            self.logger.debug('send_completion_notification: extracted dates_list=%s for account=%s', dates_list, account_name)

            # 結果が空なら「新しい画像なし」通知を送る
            if not dates_list:
                subject = f"カレンダー自動登録 - {account_name} - 新しい画像なし"
                body = f"""
カレンダー自動登録システム

アカウント: {account_name}
結果: 新しい画像ファイルはありませんでした

システムは正常に動作しています。
"""
                return self.send_notification(email, subject, body)

            # 日付が取得できた場合は処理完了メールを送る
            subject = f"カレンダー自動登録 - {account_name} - 処理完了"
            dates_text = "\n".join([f"  - {d}" for d in dates_list])
            body = f"""
カレンダー自動登録システム

アカウント: {account_name}
処理された日付:
{dates_text}

処理結果: {result.get('message', '完了')}

システムは正常に動作しています。
"""
            return self.send_notification(email, subject, body)
