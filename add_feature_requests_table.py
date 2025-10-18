# add_feature_requests_table.py

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
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except psycopg2.Error as e:
        print(f"データベース接続エラー: {e}")
        exit()

def create_feature_requests_table(conn):
    """feature_requests テーブルを作成します（存在しない場合のみ）。"""
    print("--- feature_requests テーブルの作成（または確認）を開始 ---")
    try:
        with conn.cursor() as cur:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS feature_requests (
                    id SERIAL PRIMARY KEY,
                    reporter_username TEXT NOT NULL,
                    report_date TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT '未対応', -- '未対応', '検討中', '対応済', '見送り'
                    resolution_message TEXT
                )
            ''')
        conn.commit()
        print("--- feature_requests テーブルの作成（または確認）完了 ---")
    except (Exception, psycopg2.Error) as e:
        print(f"[エラー] テーブル作成中にエラーが発生しました: {e}")
        conn.rollback() # エラー発生時はロールバック

if __name__ == '__main__':
    print("="*60)
    print("既存のデータベースに 'feature_requests' テーブルを追加します。")
    print(f"対象データベース: {DATABASE_URL.split('@')[-1] if DATABASE_URL else '未設定'}")
    print("この操作は既存のデータには影響しません。")
    print("="*60)

    connection = None
    try:
        connection = get_db_connection()
        create_feature_requests_table(connection)
        print("\n✅ テーブル追加処理が完了しました。")
    finally:
        if connection:
            connection.close()
            print("データベース接続を閉じました。")