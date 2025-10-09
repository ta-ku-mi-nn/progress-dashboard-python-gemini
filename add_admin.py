# add_admin_user.py

import sqlite3
import os
from werkzeug.security import generate_password_hash

# --- 設定 ---
# データベースファイル名
DATABASE_FILE = 'progress.db'
# 追加したい管理者アカウントの情報
ADMIN_USERNAME = 'osaka_user1'
ADMIN_PASSWORD = 'user'
ADMIN_ROLE = 'user'
ADMIN_SCHOOL = '大阪校' # 必要に応じて所属させたい校舎名に変更してください

def add_admin():
    """データベースに管理者アカウントを追加するスクリプト"""
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), DATABASE_FILE)

    if not os.path.exists(db_path):
        print(f"エラー: データベースファイル '{DATABASE_FILE}' が見つかりません。")
        return

    print(f"--- 管理者アカウント '{ADMIN_USERNAME}' の追加を開始します ---")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 既に同じユーザー名が存在するか確認
        cursor.execute("SELECT id FROM users WHERE username = ?", (ADMIN_USERNAME,))
        existing_user = cursor.fetchone()

        if existing_user:
            print(f"-> ユーザー名 '{ADMIN_USERNAME}' は既に存在するため、処理をスキップしました。")
        else:
            # ユーザーを挿入
            cursor.execute(
                'INSERT INTO users (username, password, role, school) VALUES (?, ?, ?, ?)',
                (ADMIN_USERNAME, generate_password_hash(ADMIN_PASSWORD), ADMIN_ROLE, ADMIN_SCHOOL)
            )
            conn.commit()
            print(f"-> ユーザー '{ADMIN_USERNAME}' を正常に追加しました。")
            print(f"   パスワードは '{ADMIN_PASSWORD}' です。")

    except sqlite3.Error as e:
        print(f"\n[エラー] データベース操作中にエラーが発生しました: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()
            print("--- 処理完了 ---")

if __name__ == '__main__':
    add_admin()