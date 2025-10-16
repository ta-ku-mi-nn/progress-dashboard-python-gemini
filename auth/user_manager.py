# auth/user_manager.py

import psycopg2
from psycopg2.extras import DictCursor
from werkzeug.security import generate_password_hash, check_password_hash
from config.settings import APP_CONFIG

DATABASE_URL = APP_CONFIG['data']['database_url']

def get_db_connection():
    """PostgreSQLデータベース接続を取得します。"""
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def get_user(username):
    """ユーザー名でユーザー情報をデータベースから取得する"""
    conn = get_db_connection()
    user = None
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute('SELECT * FROM users WHERE username = %s', (username,))
            user = cur.fetchone()
    except psycopg2.Error as e:
        print(f"データベースエラー (get_user): {e}")
    finally:
        if conn:
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
        with conn.cursor() as cur:
            cur.execute(
                'INSERT INTO users (username, password, role, school) VALUES (%s, %s, %s, %s)',
                (username, generate_password_hash(password), role, school)
            )
        conn.commit()
        return True, "ユーザーが正常に作成されました。"
    except psycopg2.IntegrityError:
        conn.rollback()
        return False, "このユーザー名は既に使用されています。"
    except psycopg2.Error as e:
        conn.rollback()
        print(f"データベースエラー (add_user): {e}")
        return False, "ユーザー作成中にエラーが発生しました。"
    finally:
        if conn:
            conn.close()

def update_password(username, new_password):
    """指定されたユーザーのパスワードをデータベースで更新する"""
    if not get_user(username):
        return False, "ユーザーが見つかりません。"

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'UPDATE users SET password = %s WHERE username = %s',
                (generate_password_hash(new_password), username)
            )
        conn.commit()
        return True, "パスワードが更新されました。"
    except psycopg2.Error as e:
        conn.rollback()
        print(f"データベースエラー (update_password): {e}")
        return False, "パスワード更新中にエラーが発生しました。"
    finally:
        if conn:
            conn.close()

def load_users():
    """すべてのユーザー情報をデータベースから読み込む（管理者ページ用）"""
    conn = get_db_connection()
    users = []
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute('SELECT id, username, role, school FROM users ORDER BY username')
            users_cursor = cur.fetchall()
            users = [dict(user) for user in users_cursor]
    except psycopg2.Error as e:
        print(f"データベースエラー (load_users): {e}")
    finally:
        if conn:
            conn.close()
    return users

def update_user(user_id, username, role, school):
    """ユーザー情報を更新する（パスワードは変更しない）"""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            # 編集対象以外のユーザーでユーザー名が重複していないかチェック
            cur.execute(
                'SELECT id FROM users WHERE username = %s AND id != %s', (username, user_id)
            )
            existing_user = cur.fetchone()
            if existing_user:
                return False, "このユーザー名は既に使用されています。"

            cur.execute(
                'UPDATE users SET username = %s, role = %s, school = %s WHERE id = %s',
                (username, role, school, user_id)
            )
        conn.commit()
        return True, "ユーザー情報が更新されました。"
    except psycopg2.Error as e:
        conn.rollback()
        print(f"データベースエラー (update_user): {e}")
        return False, f"更新中にエラーが発生しました: {e}"
    finally:
        if conn:
            conn.close()

def delete_user(user_id):
    """指定されたIDのユーザーを削除する"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # アプリケーションの仕様に応じて事前処理を追加する
            cur.execute('DELETE FROM student_instructors WHERE user_id = %s', (user_id,))
            cur.execute('DELETE FROM users WHERE id = %s', (user_id,))
        conn.commit()
        return True, "ユーザーが正常に削除されました。"
    except psycopg2.Error as e:
        conn.rollback()
        print(f"データベースエラー (delete_user): {e}")
        return False, f"削除中にエラーが発生しました: {e}"
    finally:
        if conn:
            conn.close()