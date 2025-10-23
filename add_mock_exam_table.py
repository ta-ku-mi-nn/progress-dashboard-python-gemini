# add_mock_exam_table.py
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
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except psycopg2.Error as e:
        print(f"データベース接続エラー: {e}")
        exit()

def create_mock_exam_results_table(conn):
    """mock_exam_results テーブルを作成します（存在しない場合のみ）。"""
    print("--- mock_exam_results テーブルの作成（または確認）を開始 ---")
    try:
        with conn.cursor() as cur:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS mock_exam_results (
                    id SERIAL PRIMARY KEY,
                    student_id INTEGER NOT NULL,
                    result_type TEXT NOT NULL,          -- 自己採点 or 結果
                    mock_exam_name TEXT NOT NULL,       -- 模試の種類 (例: 共通テスト模試)
                    mock_exam_format TEXT NOT NULL,     -- 模試の形式 (例: マーク, 記述)
                    grade TEXT NOT NULL,                -- 学年 (例: 高3)
                    round TEXT NOT NULL,                -- 回数 (例: 第1回)
                    exam_date DATE,                     -- 受験日 (任意)
                    -- 記述科目
                    subject_kokugo_desc INTEGER,
                    subject_math_desc INTEGER,
                    subject_english_desc INTEGER,
                    subject_rika1_desc INTEGER,
                    subject_rika2_desc INTEGER,
                    subject_shakai1_desc INTEGER,
                    subject_shakai2_desc INTEGER,
                    -- マーク科目
                    subject_kokugo_mark INTEGER,
                    subject_math1a_mark INTEGER,
                    subject_math2bc_mark INTEGER,
                    subject_english_r_mark INTEGER,
                    subject_english_l_mark INTEGER,
                    subject_rika1_mark INTEGER,
                    subject_rika2_mark INTEGER,
                    subject_shakai1_mark INTEGER,
                    subject_shakai2_mark INTEGER,
                    subject_rika_kiso1_mark INTEGER,
                    subject_rika_kiso2_mark INTEGER,
                    subject_info_mark INTEGER,
                    -- 外部キー制約
                    FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE
                )
            ''')
        conn.commit()
        print("--- mock_exam_results テーブルの作成（または確認）完了 ---")
    except (Exception, psycopg2.Error) as e:
        print(f"[エラー] テーブル作成中にエラーが発生しました: {e}")
        conn.rollback() # エラー発生時はロールバック

if __name__ == '__main__':
    print("="*60)
    print("既存のデータベースに 'mock_exam_results' テーブルを追加します。")
    print(f"対象データベース: {DATABASE_URL.split('@')[-1] if DATABASE_URL else '未設定'}")
    print("この操作は既存のデータには影響しません。")
    print("="*60)

    connection = None
    try:
        connection = get_db_connection()
        create_mock_exam_results_table(connection)
        print("\n✅ テーブル追加処理が完了しました。")
    finally:
        if connection:
            connection.close()
            print("データベース接続を閉じました。")