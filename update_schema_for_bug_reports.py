# update_schema_for_bug_reports.py

import sqlite3
import os

# RenderのDiskマウントパス（/var/data）が存在すればそちらを使用
RENDER_DATA_DIR = "/var/data"
if os.path.exists(RENDER_DATA_DIR):
    # 本番環境（Render）用のパス
    DB_DIR = RENDER_DATA_DIR
else:
    # ローカル開発環境用のパス (プロジェクトのルートディレクトリを指す)
    # このファイルの2階層上がプロジェクトルート
    DB_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATABASE_FILE = os.path.join(DB_DIR, 'progress.db')

def create_bug_reports_table():
    """
    データベースに不具合報告を保存するためのテーブルを作成する。
    """
    print("--- 不具合報告テーブルの作成を開始 ---")
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bug_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reporter_username TEXT NOT NULL,
                report_date TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT '未対応', -- '未対応', '対応中', '対応済'
                resolution_message TEXT
            )
        ''')
        print("  - 'bug_reports' テーブルを正常に作成または確認しました。")
        
        conn.commit()
        conn.close()
        print("--- テーブル作成完了 ---")

    except sqlite3.Error as e:
        print(f"\n[エラー] データベース操作中にエラーが発生しました: {e}")

if __name__ == '__main__':
    create_bug_reports_table()