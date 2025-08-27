#!/usr/bin/env python3
"""
設定ファイルローダー
YAMLファイルと環境変数から設定を読み込む
"""

import os
import yaml
import logging
from typing import Dict, Any, Optional

class ConfigLoader:
    def __init__(self, config_file: str = "config.yaml"):
        """
        設定ローダーの初期化
        
        Args:
            config_file (str): 設定ファイルのパス
        """
        self.config_file = config_file
        self.config = {}
        self.load_config()
        
    def load_config(self):
        """
        YAMLファイルから設定を読み込む
        """
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = yaml.safe_load(f) or {}
                print(f"設定ファイルを読み込みました: {self.config_file}")
            else:
                print(f"設定ファイルが見つかりません: {self.config_file}")
                print("デフォルト設定を使用します")
                self.config = self.get_default_config()
        except Exception as e:
            print(f"設定ファイルの読み込みエラー: {e}")
            self.config = self.get_default_config()
    
    def get_default_config(self) -> Dict[str, Any]:
        """
        デフォルト設定を返す
        
        Returns:
            Dict[str, Any]: デフォルト設定
        """
        return {
            'openai': {
                'api_key': '',
                'api_base': '',
                'model': 'gpt-4o-mini'
            },
            'google_calendar': {
                'credentials_file': 'credentials.json',
                'token_file': 'token.json'
            },
            'workflow': {
                'event_title': '母出勤',
                'event_description': 'カレンダー画像から自動検出された勤務日',
                'dry_run': False,
                'monitor_path': ''
            },
            'logging': {
                'level': 'INFO',
                'format': '%(asctime)s - %(levelname)s - %(message)s'
            }
        }
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        設定値を取得（環境変数優先）
        
        Args:
            key_path (str): 設定キーのパス（ドット区切り）
            default (Any): デフォルト値
            
        Returns:
            Any: 設定値
        """
        keys = key_path.split('.')
        value = self.config
        
        # YAMLから値を取得
        try:
            for key in keys:
                value = value[key]
        except (KeyError, TypeError):
            value = default
        
        # 環境変数でオーバーライド
        env_key = key_path.upper().replace('.', '_')
        env_value = os.getenv(env_key)
        
        if env_value is not None:
            # 型変換
            if isinstance(value, bool):
                env_value = env_value.lower() in ('true', '1', 'yes')
            elif isinstance(value, int):
                try:
                    env_value = int(env_value)
                except ValueError:
                    pass
            elif isinstance(value, float):
                try:
                    env_value = float(env_value)
                except ValueError:
                    pass
            return env_value
        
        return value
    
    def get_openai_config(self) -> Dict[str, Any]:
        """
        OpenAI設定を取得
        
        Returns:
            Dict[str, Any]: OpenAI設定
        """
        return {
            'api_key': self.get('openai.api_key', ''),
            'api_base': self.get('openai.api_base', ''),
            'model': self.get('openai.model', 'gpt-4o-mini'),
            'max_image_size_kb': self.get('openai.max_image_size_kb', 256)
        }
    
    def get_google_calendar_config(self) -> Dict[str, str]:
        """
        Google Calendar設定を取得
        
        Returns:
            Dict[str, str]: Google Calendar設定
        """
        return {
            'credentials_file': self.get('google_calendar.credentials_file', 'credentials.json'),
            'token_file': self.get('google_calendar.token_file', 'token.json')
        }
    
    def get_workflow_config(self) -> Dict[str, Any]:
        """
        ワークフロー設定を取得
        
        Returns:
            Dict[str, Any]: ワークフロー設定
        """
        return {
            'event_title': self.get('workflow.event_title', '母出勤'),
            'event_description': self.get('workflow.event_description', 'カレンダー画像から自動検出された勤務日'),
            'dry_run': self.get('workflow.dry_run', False)
        }
    
    def get_logging_config(self) -> Dict[str, str]:
        """
        ログ設定を取得
        
        Returns:
            Dict[str, str]: ログ設定
        """
        return {
            'level': self.get('logging.level', 'INFO'),
            'format': self.get('logging.format', '%(asctime)s - %(levelname)s - %(message)s')
        }
    
    def setup_logging(self):
        """
        ログ設定を適用
        """
        log_config = self.get_logging_config()
        level = getattr(logging, log_config['level'].upper(), logging.INFO)
        format_str = log_config['format']
        
        logging.basicConfig(level=level, format=format_str)
        print(f"ログレベルを設定しました: {log_config['level']}")

# グローバル設定ローダーインスタンス
config_loader = ConfigLoader()
