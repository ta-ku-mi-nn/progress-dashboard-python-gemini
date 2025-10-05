"""
ア# ファイルパス設定
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(BASE_DIR, 'route-subject-text-time.csv')
JSON_PATH = os.path.join(BASE_DIR, 'progress_data.json')
BULK_BUTTONS_PATH = os.path.join(BASE_DIR, 'bulk_buttons.json')

# データソース設定
USE_JSON = True  # True: JSON形式を使用, False: CSV形式を使用
DATA_PATH = JSON_PATH if USE_JSON else CSV_PATH

# デフォルト値
DEFAULT_STUDENT = 'デフォルト生徒'設定ファイル
"""

import os

# ファイルパス設定
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
CSV_PATH = os.path.join(BASE_DIR, 'route-subject-text-time.csv')
BULK_BUTTONS_PATH = os.path.join(BASE_DIR, 'bulk_buttons.json')

# デフォルト値
DEFAULT_STUDENT = 'デフォルト生徒'

# アプリケーション設定
APP_CONFIG = {
    'host': '127.0.0.1',
    'port': 8051,
    'debug_mode': True,
    'auto_open_browser': True
}

# CSV列名設定
CSV_COLUMNS = {
    'route_level': 'ルートレベル',
    'subject': '科目',
    'book_name': '参考書名',
    'time': '所要時間',
    'plan': '予定',
    'done': '達成済',
    'progress_ratio': '達成割合',
    'student': '生徒',
    'username': 'ユーザー名',
    'campus': '校舎'
}

# データ型設定
CSV_DTYPES = {
    '達成割合': 'str'
}

# 現在のユーザーを取得する関数
def get_current_user():
    """認証システムから現在のユーザー情報を取得"""
    try:
        # 認証システムが利用可能な場合
        from flask import session
        if 'user' in session:
            user_data = session['user']
            return {
                'username': user_data.get('username', ''),
                'campus': user_data.get('campus', ''),
                'role': user_data.get('role', 'user')
            }
    except (ImportError, RuntimeError):
        # Flaskコンテキスト外の場合はフォールバック
        pass
    
    # フォールバック: CSVから最初のユーザーを取得
    try:
        from data.processor import load_csv_data
        from utils import get_unique_students
        df = load_csv_data()
        users = get_unique_students(df)
        username = users[0] if len(users) > 0 else DEFAULT_STUDENT
        return {
            'username': username,
            'campus': '',
            'role': 'user'
        }
    except (ImportError, FileNotFoundError, ValueError, TypeError):
        return {
            'username': DEFAULT_STUDENT,
            'campus': '',
            'role': 'user'
        }

# 現在のユーザー（初期化時に設定）
current_user = None