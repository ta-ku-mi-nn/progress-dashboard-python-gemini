# config/settings.py
import os  # osをインポート

APP_CONFIG = {
    'server': {
        'secret_key': 'your-secret-key-change-this-in-production',
        'host': '0.0.0.0',  # 外部からのアクセスを許可するために '0.0.0.0' に変更
        'port': int(os.getenv('PORT', 8051)), # Renderが指定するポート番号を読み込む
        'debug': False  # 本番環境ではFalseに設定
    },
    'browser': {
        'auto_open': False # サーバー上でブラウザが自動で開かないようにする
    },
    'data': {
        'json_file': 'route-subject-text-time_new.json',
        'users_file': 'users.json'
    }
}