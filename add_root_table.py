# add_root_table.py

import sys
import os

# プロジェクトのルートディレクトリをPythonのパスに追加
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from data.nested_json_processor import get_db_connection

def create_root_tables_table():
    """
    ルート表（指導要領）を管理するためのテーブルを作成します。
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # テーブル作成のSQL実行
            # 科目(subject)、レベル(level)、年度(academic_year)のカラムを含みます
            cur.execute("""
                CREATE TABLE IF NOT EXISTS root_tables (
                    id SERIAL PRIMARY KEY,
                    filename TEXT NOT NULL,
                    file_content BYTEA NOT NULL,
                    subject TEXT,
                    level TEXT,
                    academic_year INT,
                    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """)
            print("Success: 'root_tables' テーブルが正常に作成または確認されました。")
        conn.commit()
    except Exception as e:
        print(f"Error: テーブルの作成中にエラーが発生しました: {e}")
        conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    create_root_tables_table()