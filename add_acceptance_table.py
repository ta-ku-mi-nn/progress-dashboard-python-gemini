# add_acceptance_table.py
import os
import psycopg2
from dotenv import load_dotenv

# .envファイルを読み込んで環境変数を設定
load_dotenv()

# --- 設定 ---
DATABASE_URL = os.getenv('DATABASE_URL') # DATABASE_URL_EXTERNAL ではなく、Render内部のURLを使用

def get_db_connection():
    """PostgreSQLデータベース接続を取得します。"""
    if not DATABASE_URL:
        print("エラー: 環境変数 'DATABASE_URL' が設定されていません。")
        exit()
    return psycopg2.connect(DATABASE_URL)

def create_university_acceptance_table(conn):
    """university_acceptance テーブルを作成します（存在しない場合のみ）。"""
    print("--- university_acceptance テーブルの作成を開始 ---")
    try:
        with conn.cursor() as cur:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS university_acceptance (
                    id SERIAL PRIMARY KEY,
                    student_id INTEGER NOT NULL,
                    university_name TEXT NOT NULL,
                    faculty_name TEXT NOT NULL,
                    department_name TEXT,
                    exam_system TEXT,
                    result TEXT, -- '合格', '不合格', または NULL
                    FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE
                )
            ''')
        conn.commit()
        print("--- university_acceptance テーブルの作成（または確認）完了 ---")
    except (Exception, psycopg2.Error) as e:
        print(f"[エラー] テーブル作成中にエラーが発生しました: {e}")
        conn.rollback()

if __name__ == '__main__':
    connection = None
    try:
        connection = get_db_connection()
        create_university_acceptance_table(connection)
    finally:
        if connection:
            connection.close()