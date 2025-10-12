# update_schema_for_changelog.py

import sqlite3
import os

RENDER_DATA_DIR = "/var/data"
if os.path.exists(RENDER_DATA_DIR):
    DB_DIR = RENDER_DATA_DIR
else:
    DB_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATABASE_FILE = os.path.join(DB_DIR, 'progress.db')

def create_changelog_table():
    """
    データベースに更新履歴を保存するためのテーブルを作成する。
    """
    print("--- 更新履歴テーブルの作成を開始 ---")
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS changelog (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version TEXT NOT NULL,
                release_date TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL
            )
        ''')
        print("  - 'changelog' テーブルを正常に作成または確認しました。")
        
        conn.commit()
        conn.close()
        print("--- テーブル作成完了 ---")

    except sqlite3.Error as e:
        print(f"\n[エラー] データベース操作中にエラーが発生しました: {e}")

if __name__ == '__main__':
    create_changelog_table()