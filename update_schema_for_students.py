# update_schema_for_students.py

import sqlite3
import pandas as pd

DATABASE_FILE = 'progress.db'

def update_student_schema():
    print("--- 生徒テーブルのスキーマ更新を開始 ---")
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        # pandasでテーブル情報を読み込み
        df = pd.read_sql_query(f"PRAGMA table_info(students)", conn)

        # main_instructor カラムが存在する場合のみ処理
        if 'main_instructor' in df['name'].values:
            print("  - 'main_instructor' カラムを検出しました。テーブルを再構築します。")
            
            # 1. 既存テーブルをリネーム
            cursor.execute("ALTER TABLE students RENAME TO students_old;")

            # 2. 新しいスキーマでテーブルを再作成
            cursor.execute('''
                CREATE TABLE students (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    school TEXT NOT NULL,
                    deviation_value INTEGER,
                    sub_instructor TEXT,
                    UNIQUE(school, name)
                )
            ''')

            # 3. データを移行
            cursor.execute('''
                INSERT INTO students (id, name, school, deviation_value, sub_instructor)
                SELECT id, name, school, deviation_value, sub_instructor
                FROM students_old;
            ''')
            
            # 4. 古いテーブルを削除
            cursor.execute("DROP TABLE students_old;")
            
            print("  - テーブルの再構築が完了しました。")
        else:
            print("  - 'main_instructor' カラムが存在しないため、スキーマは最新です。")

        conn.commit()
        conn.close()
        print("--- スキーマ更新完了 ---")

    except sqlite3.Error as e:
        print(f"\n[エラー] データベース操作中にエラーが発生しました: {e}")

if __name__ == '__main__':
    update_student_schema()