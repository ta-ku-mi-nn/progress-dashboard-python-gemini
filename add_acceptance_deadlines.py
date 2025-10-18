# add_acceptance_deadlines.py
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
    # SSLモードを 'require' に設定 (Renderの要件)
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    return conn

def add_deadline_columns_to_acceptance(conn):
    """university_acceptance テーブルに application_deadline と procedure_deadline 列を追加します（存在しない場合のみ）。"""
    print("--- university_acceptance テーブルへの列追加を開始 ---")
    try:
        with conn.cursor() as cur:
            # application_deadline 列を追加 (存在しない場合のみ)
            cur.execute('''
                ALTER TABLE university_acceptance
                ADD COLUMN IF NOT EXISTS application_deadline TEXT;
            ''')
            print("  - application_deadline 列を追加（または確認）しました。")

            # procedure_deadline 列を追加 (存在しない場合のみ)
            cur.execute('''
                ALTER TABLE university_acceptance
                ADD COLUMN IF NOT EXISTS procedure_deadline TEXT;
            ''')
            print("  - procedure_deadline 列を追加（または確認）しました。")
        conn.commit()
        print("--- 列の追加（または確認）完了 ---")
    except (Exception, psycopg2.Error) as e:
        print(f"[エラー] 列追加中にエラーが発生しました: {e}")
        if conn: # エラーが発生しても接続があればロールバック試行
             conn.rollback()

if __name__ == '__main__':
    print("="*60)
    print("既存の university_acceptance テーブルに期日関連の列を追加します。")
    print(f"対象データベース: {DATABASE_URL.split('@')[-1] if DATABASE_URL else '未設定'}")
    print("この操作は既存のデータには影響しません。")
    print("="*60)

    connection = None
    try:
        connection = get_db_connection()
        add_deadline_columns_to_acceptance(connection)
        print("\n✅ テーブル列追加処理が完了しました。")
    except Exception as e:
         print(f"\n❌ 処理中にエラーが発生しました: {e}")
    finally:
        if connection:
            connection.close()
            print("データベース接続を閉じました。")