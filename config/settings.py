#!/usr/bin/env python3
"""
アプリケーション全体の設定ファイル
"""

APP_CONFIG = {
    'server': {
        'secret_key': 'your-secret-key-change-this-in-production',
        'host': '127.0.0.1',
        'port': 8051,
        'debug': True
    },
    'browser': {
        'auto_open': True
    },
    'data': {
        'json_file': 'route-subject-text-time_new.json',
        'users_file': 'users.json'
    }
}