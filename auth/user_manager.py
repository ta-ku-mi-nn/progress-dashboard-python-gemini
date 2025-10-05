# auth/user_manager.py

import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash

# このファイルの場所を基準に、プロジェクトルートにあるDBファイルを絶対パスで指定
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_FILE = os.path.join(os.path.dirname(BASE_DIR), 'progress.db')

def get_db_connection():
    """データベース接続を取得し、辞書形式で結果を返せるようにする"""
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def get_user(username):
    """ユーザー名でユーザー情報をデータベースから取得する"""
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()
    return user

def authenticate_user(username, password):
    """ユーザー名とパスワードをデータベースで検証する"""
    user = get_user(username)
    if user and check_password_hash(user['password'], password):
        return dict(user) # ログイン成功時は辞書として返す
    return None

def add_user(username, password, role='user', school=None):
    """新しいユーザーをデータベースに追加する"""
    if get_user(username):
        return False, "このユーザー名は既に使用されています。"

    conn = get_db_connection()
    try:
        conn.execute(
            'INSERT INTO users (username, password, role, school) VALUES (?, ?, ?, ?)',
            (username, generate_password_hash(password), role, school)
        )
        conn.commit()
        return True, "ユーザーが正常に作成されました。"
    except sqlite3.IntegrityError:
        return False, "このユーザー名は既に使用されています。"
    finally:
        conn.close()

def update_password(username, new_password):
    """指定されたユーザーのパスワードをデータベースで更新する"""
    if not get_user(username):
        return False, "ユーザーが見つかりません。"

    conn = get_db_connection()
    conn.execute(
        'UPDATE users SET password = ? WHERE username = ?',
        (generate_password_hash(new_password), username)
    )
    conn.commit()
    conn.close()
    return True, "パスワードが更新されました。"

def load_users():
    """すべてのユーザー情報をデータベースから読み込む（管理者ページ用）"""
    conn = get_db_connection()
    users_cursor = conn.execute('SELECT id, username, role, school FROM users ORDER BY username').fetchall()
    conn.close()
    # コールバックで扱いやすいように辞書のリストに変換
    return [dict(user) for user in users_cursor]