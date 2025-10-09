# update_schema_for_past_exams.py

import sqlite3
import os

DATABASE_FILE = 'progress.db'

def add_column_if_not_exists(cursor, table_name, column_name, column_type):
    """テーブルに指定されたカラムが存在しない場合のみ追加する"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [info[1] for info in cursor.fetchall()]
    if column_name not in columns:
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
        print(f"  - '{table_name}' テーブルに '{column_name}' カラムを追加しました。")
    else:
        print(f"  - '{column_name}' カラムは既に存在するため、スキップします。")


def create_past_exam_results_table():
    """
    データベースに過去問結果を保存するためのテーブルを作成・更新する。
    """
    print("--- 過去問結果テーブルの作成・更新を開始 ---")
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS past_exam_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                university_name TEXT NOT NULL,
                faculty_name TEXT,
                exam_system TEXT,
                year INTEGER NOT NULL,
                subject TEXT NOT NULL,
                time_required INTEGER,
                correct_answers INTEGER,
                total_questions INTEGER,
                FOREIGN KEY (student_id) REFERENCES students (id)
            )
        ''')
        print("  - 'past_exam_results' テーブルを正常に作成または確認しました。")
        
        # --- ★★★ ここから修正 ★★★ ---
        # 試験時間全体を保存するカラムを追加
        add_column_if_not_exists(cursor, 'past_exam_results', 'total_time_allowed', 'INTEGER')
        # --- ★★★ ここまで修正 ★★★ ---
        
        conn.commit()
        conn.close()
        print("--- テーブル作成・更新完了 ---")

    except sqlite3.Error as e:
        print(f"\n[エラー] データベース操作中にエラーが発生しました: {e}")

if __name__ == '__main__':
    create_past_exam_results_table()