# add_eiken_table.py
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

def get_db_connection():
    if not DATABASE_URL:
        print("エラー: 環境変数 'DATABASE_URL' が設定されていません。")
        exit()
    return psycopg2.connect(DATABASE_URL)

def create_eiken_results_table(conn):
    print("--- eiken_results テーブルの作成を開始 ---")
    try:
        with conn.cursor() as cur:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS eiken_results (
                    id SERIAL PRIMARY KEY,
                    student_id INTEGER NOT NULL,
                    grade TEXT NOT NULL,
                    cse_score INTEGER,
                    exam_date DATE,
                    result TEXT, -- 合格/不合格/一次合格など
                    UNIQUE(student_id, grade), -- 同じ生徒の同じ級は最新のみ保持する場合（要件に応じて調整）
                    FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE
                )
            ''')
        conn.commit()
        print("--- eiken_results テーブルの作成完了 ---")
    except (Exception, psycopg2.Error) as e:
        print(f"[エラー] テーブル作成中にエラーが発生しました: {e}")
        conn.rollback()

if __name__ == '__main__':
    connection = None
    try:
        connection = get_db_connection()
        create_eiken_results_table(connection)
    finally:
        if connection:
            connection.close()