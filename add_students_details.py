# add_student_details.py
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
        # SSLモードを 'require' に設定 (Renderの要件に合わせて)
        # ローカル環境などでSSLが不要な場合は sslmode='prefer' などに変更してください
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        return conn
    except psycopg2.Error as e:
        print(f"データベース接続エラー: {e}")
        exit()

def add_detail_columns_to_students(conn):
    """students テーブルに target_level, grade, previous_school 列を追加します（存在しない場合のみ）。"""
    print("--- students テーブルへの列追加を開始 ---")
    try:
        with conn.cursor() as cur:
            # target_level 列を追加 (存在しない場合のみ)
            cur.execute('''
                ALTER TABLE students
                ADD COLUMN IF NOT EXISTS target_level TEXT;
            ''')
            print("  - target_level 列を追加（または確認）しました。")

            # grade 列を追加 (存在しない場合のみ)
            cur.execute('''
                ALTER TABLE students
                ADD COLUMN IF NOT EXISTS grade TEXT;
            ''')
            print("  - grade 列を追加（または確認）しました。")

            # previous_school 列を追加 (存在しない場合のみ)
            cur.execute('''
                ALTER TABLE students
                ADD COLUMN IF NOT EXISTS previous_school TEXT;
            ''')
            print("  - previous_school 列を追加（または確認）しました。")

        conn.commit()
        print("--- 列の追加（または確認）完了 ---")
    except (Exception, psycopg2.Error) as e:
        print(f"[エラー] 列追加中にエラーが発生しました: {e}")
        if conn: # エラーが発生しても接続があればロールバック試行
             conn.rollback()

if __name__ == '__main__':
    print("="*60)
    print("既存の students テーブルに詳細情報関連の列を追加します。")
    db_name = DATABASE_URL.split('@')[-1].split('/')[0] if DATABASE_URL else '未設定'
    db_path = DATABASE_URL.split('/')[-1] if DATABASE_URL else '未設定'
    print(f"対象データベース: {db_name}/{db_path}")
    print("この操作は既存のデータには影響しません。")
    print("="*60)

    connection = None
    try:
        connection = get_db_connection()
        add_detail_columns_to_students(connection)
        print("\n✅ テーブル列追加処理が完了しました。")
    except Exception as e:
         print(f"\n❌ 処理中にエラーが発生しました: {e}")
    finally:
        if connection:
            connection.close()
            print("データベース接続を閉じました。")