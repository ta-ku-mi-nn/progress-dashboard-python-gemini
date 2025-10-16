# config/settings.py
import os
from dotenv import load_dotenv

load_dotenv() # .envファイルから環境変数を読み込む

APP_CONFIG = {
    'server': {
        'secret_key': os.getenv('SECRET_KEY', 'your-secret-key-change-this-in-production'),
        'host': '0.0.0.0',
        'port': int(os.getenv('PORT', 8051)),
        'debug': os.getenv('DASH_DEBUG_MODE', 'False').lower() in ('true', '1', 't')
    },
    'browser': {
        'auto_open': False
    },
    'data': {
        # DATABASE_URLを環境変数から取得
        'database_url': os.getenv('DATABASE_URL', 'postgresql://user:password@localhost:5432/mydatabase'),
        'users_file': 'users.json' # この行はPostgreSQL移行後は不要になる可能性があります
    }
}