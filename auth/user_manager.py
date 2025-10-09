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

# ★★★ ここから修正 ★★★
def update_user(user_id, username, role, school):
    """ユーザー情報を更新する（パスワードは変更しない）"""
    conn = get_db_connection()
    try:
        # 編集対象以外のユーザーでユーザー名が重複していないかチェック
        existing_user = conn.execute(
            'SELECT id FROM users WHERE username = ? AND id != ?', (username, user_id)
        ).fetchone()
        if existing_user:
            return False, "このユーザー名は既に使用されています。"

        conn.execute(
            'UPDATE users SET username = ?, role = ?, school = ? WHERE id = ?',
            (username, role, school, user_id)
        )
        conn.commit()
        return True, "ユーザー情報が更新されました。"
    except sqlite3.Error as e:
        return False, f"更新中にエラーが発生しました: {e}"
    finally:
        conn.close()

def delete_user(user_id):
    """指定されたIDのユーザーを削除する"""
    conn = get_db_connection()
    try:
        # ユーザーを削除する前に、関連する生徒の担当情報をクリアする必要がある場合など、
        # アプリケーションの仕様に応じて事前処理を追加する
        conn.execute('DELETE FROM student_instructors WHERE user_id = ?', (user_id,))
        conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
        conn.commit()
        return True, "ユーザーが正常に削除されました。"
    except sqlite3.Error as e:
        return False, f"削除中にエラーが発生しました: {e}"
    finally:
        conn.close()
# ★★★ ここまで修正 ★★★