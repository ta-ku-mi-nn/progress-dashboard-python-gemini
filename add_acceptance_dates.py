# add_acceptance_dates.py
import os
import psycopg2
from dotenv import load_dotenv

# .envファイルを読み込んで環境変数を設定
load_dotenv()

# --- 設定 ---
DATABASE_URL = os.getenv('DATABASE_URL') # Render内部のURLを使用

def get_db_connection():
    """PostgreSQLデータベース接続を取得します。"""
    if not DATABASE_URL:
        print("エラー: 環境変数 'DATABASE_URL' が設定されていません。")
        exit()
    return psycopg2.connect(DATABASE_URL)

def add_date_columns_to_acceptance(conn):
    """university_acceptance テーブルに exam_date と announcement_date 列を追加します（存在しない場合のみ）。"""
    print("--- university_acceptance テーブルへの列追加を開始 ---")
    try:
        with conn.cursor() as cur:
            # exam_date 列を追加 (存在しない場合のみ)
            cur.execute('''
                ALTER TABLE university_acceptance
                ADD COLUMN IF NOT EXISTS exam_date TEXT;
            ''')
            print("  - exam_date 列を追加（または確認）しました。")

            # announcement_date 列を追加 (存在しない場合のみ)
            cur.execute('''
                ALTER TABLE university_acceptance
                ADD COLUMN IF NOT EXISTS announcement_date TEXT;
            ''')
            print("  - announcement_date 列を追加（または確認）しました。")
        conn.commit()
        print("--- 列の追加（または確認）完了 ---")
    except (Exception, psycopg2.Error) as e:
        print(f"[エラー] 列追加中にエラーが発生しました: {e}")
        conn.rollback()

if __name__ == '__main__':
    connection = None
    try:
        connection = get_db_connection()
        add_date_columns_to_acceptance(connection)
    finally:
        if connection:
            connection.close()