# update_schema_for_homework.py
import sqlite3
import pandas as pd
import os

DATABASE_FILE = 'progress.db'

def update_homework_schema():
    print("--- 宿題テーブルのスキーマ更新を開始 ---")
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        df_info = pd.read_sql_query("PRAGMA table_info(homework)", conn)

        # due_dateカラムが存在する場合（＝旧スキーマ）のみ実行
        if 'due_date' in df_info['name'].values:
            print("  - 旧スキーマを検出。テーブルを再構築します。")
            
            # 1. 既存テーブルをリネーム
            cursor.execute("ALTER TABLE homework RENAME TO homework_old;")

            # 2. 新しいスキーマでテーブルを再作成
            # task_date: 各宿題の日付
            # task_group_id: 期間設定で作成された宿題をまとめるID
            cursor.execute('''
                CREATE TABLE homework (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER NOT NULL,
                    subject TEXT NOT NULL,
                    task TEXT NOT NULL,
                    task_date TEXT NOT NULL,
                    task_group_id TEXT,
                    status TEXT NOT NULL DEFAULT '未着手',
                    FOREIGN KEY (student_id) REFERENCES students (id)
                )
            ''')

            # 3. データを移行（due_dateをtask_dateに）
            cursor.execute('''
                INSERT INTO homework (id, student_id, subject, task, task_date, status)
                SELECT id, student_id, subject, task, due_date, status
                FROM homework_old;
            ''')
            
            # 4. 古いテーブルを削除
            cursor.execute("DROP TABLE homework_old;")
            
            print("  - テーブルの再構築とデータ移行が完了しました。")
        else:
            print("  - スキーマは既に最新です。")

        conn.commit()
        conn.close()
        print("--- スキーマ更新完了 ---")

    except sqlite3.Error as e:
        print(f"\n[エラー] データベース操作中にエラーが発生しました: {e}")

if __name__ == '__main__':
    update_homework_schema()