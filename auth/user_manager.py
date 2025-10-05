import json
import os
import threading
from werkzeug.security import generate_password_hash, check_password_hash
from config.settings import APP_CONFIG

# 設定ファイルからユーザーファイルのパスを取得
USERS_FILE = APP_CONFIG['data']['users_file']
# ファイルアクセスが同時に発生した場合のデータ破損を防ぐためのロック
LOCK = threading.Lock()

def load_users():
    """ユーザー情報をJSONファイルから読み込む"""
    with LOCK:
        if not os.path.exists(USERS_FILE):
            return {}
        try:
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            # ファイルが空または見つからない場合は空の辞書を返す
            return {}

def save_users(users):
    """ユーザー情報をJSONファイルに保存する"""
    with LOCK:
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(users, f, indent=2, ensure_ascii=False)

def get_user(username):
    """指定されたユーザー名のユーザー情報を取得する"""
    users = load_users()
    return users.get(username)

def authenticate_user(username, password):
    """ユーザー名とパスワードを検証して認証する"""
    user = get_user(username)
    # ユーザーが存在し、かつパスワードのハッシュが一致するか確認
    if user and check_password_hash(user['password'], password):
        return user
    return None

def add_user(username, password, role='user', school=None):
    """新しいユーザーを追加する"""
    users = load_users()
    if username in users:
        return False, "このユーザー名は既に使用されています。"
    
    users[username] = {
        'username': username,
        'password': generate_password_hash(password), # パスワードをハッシュ化
        'role': role,
        'school': school
    }
    save_users(users)
    return True, "ユーザーが正常に作成されました。"

def update_password(username, new_password):
    """指定されたユーザーのパスワードを更新する"""
    users = load_users()
    if username not in users:
        return False, "ユーザーが見つかりません。"
    
    users[username]['password'] = generate_password_hash(new_password)
    save_users(users)
    return True, "パスワードが更新されました。"