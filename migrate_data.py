# migrate_data.py

import sqlite3
import pandas as pd
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import DictCursor, execute_values

# .envファイルから環境変数を読み込む
load_dotenv()

# --- 設定 ---
SQLITE_DB_PATH = 'progress.db' # 手順1でダウンロードしたファイル
POSTGRES_URL_EXTERNAL = os.getenv('DATABASE_URL_EXTERNAL') 

if not POSTGRES_URL_EXTERNAL:
    print("エラー: 環境変数 'DATABASE_URL_EXTERNAL' が設定されていません。")
    print(".envファイルにRenderのPostgreSQLページの'External Database URL'を設定してください。")
    exit()

def get_pg_connection():
    """PostgreSQLデータベース接続を取得します。"""
    return psycopg2.connect(POSTGRES_URL_EXTERNAL)

def get_sqlite_connection():
    """SQLiteデータベース接続を取得します。"""
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row # カラム名でアクセスできるようにする
    return conn

def main():
    # 接続の確立
    sqlite_conn = get_sqlite_connection()
    pg_conn = get_pg_connection()
    
    # SQLiteとPostgreSQLのカーソルを作成
    sqlite_cur = sqlite_conn.cursor()
    pg_cur = pg_conn.cursor()

    try:
        print("データ移行を開始します...")

        # --- IDのマッピング用辞書 ---
        user_id_map = {}
        student_id_map = {}
        master_textbook_id_map = {}
        bulk_preset_id_map = {}

        # 1. users テーブルの移行
        print("  - 'users' テーブルを移行中...")
        sqlite_cur.execute("SELECT * FROM users ORDER BY id")
        users = sqlite_cur.fetchall()
        for user in users:
            old_id = user['id']
            pg_cur.execute(
                "INSERT INTO users (username, password, role, school) VALUES (%s, %s, %s, %s) RETURNING id",
                (user['username'], user['password'], user['role'], user['school'])
            )
            new_id = pg_cur.fetchone()[0]
            user_id_map[old_id] = new_id
        print(f"    -> {len(users)} 件完了")

        # 2. students テーブルの移行
        print("  - 'students' テーブルを移行中...")
        sqlite_cur.execute("SELECT * FROM students ORDER BY id")
        students = sqlite_cur.fetchall()
        for student in students:
            old_id = student['id']
            pg_cur.execute(
                "INSERT INTO students (name, school, deviation_value) VALUES (%s, %s, %s) RETURNING id",
                (student['name'], student['school'], student['deviation_value'])
            )
            new_id = pg_cur.fetchone()[0]
            student_id_map[old_id] = new_id
        print(f"    -> {len(students)} 件完了")

        # 3. master_textbooks テーブルの移行
        print("  - 'master_textbooks' テーブルを移行中...")
        sqlite_cur.execute("SELECT * FROM master_textbooks ORDER BY id")
        textbooks = sqlite_cur.fetchall()
        for book in textbooks:
            old_id = book['id']
            pg_cur.execute(
                "INSERT INTO master_textbooks (level, subject, book_name, duration) VALUES (%s, %s, %s, %s) RETURNING id",
                (book['level'], book['subject'], book['book_name'], book['duration'])
            )
            new_id = pg_cur.fetchone()[0]
            master_textbook_id_map[old_id] = new_id
        print(f"    -> {len(textbooks)} 件完了")
        
        # 4. student_instructors テーブルの移行 (IDマッピングを使用)
        print("  - 'student_instructors' テーブルを移行中...")
        sqlite_cur.execute("SELECT * FROM student_instructors")
        student_instructors = sqlite_cur.fetchall()
        instructors_to_insert = []
        for rel in student_instructors:
            new_student_id = student_id_map.get(rel['student_id'])
            new_user_id = user_id_map.get(rel['user_id'])
            if new_student_id and new_user_id:
                instructors_to_insert.append((new_student_id, new_user_id, rel['is_main']))
        
        if instructors_to_insert:
            execute_values(pg_cur, "INSERT INTO student_instructors (student_id, user_id, is_main) VALUES %s", instructors_to_insert)
        print(f"    -> {len(instructors_to_insert)} 件完了")

        # 5. progress テーブルの移行
        print("  - 'progress' テーブルを移行中...")
        sqlite_cur.execute("SELECT * FROM progress")
        progress_items = sqlite_cur.fetchall()
        progress_to_insert = []
        for item in progress_items:
            new_student_id = student_id_map.get(item['student_id'])
            if new_student_id:
                # 整数をbool型に変換
                is_planned_bool = bool(item['is_planned'])
                is_done_bool = bool(item['is_done'])

                progress_to_insert.append((
                    new_student_id, item['subject'], item['level'], item['book_name'],
                    item['duration'], is_planned_bool, is_done_bool, # 変換後の変数を使用
                    item['completed_units'], item['total_units']
                ))
        if progress_to_insert:
            execute_values(pg_cur, """
                INSERT INTO progress (student_id, subject, level, book_name, duration, is_planned, is_done, completed_units, total_units)
                VALUES %s
            """, progress_to_insert)
        print(f"    -> {len(progress_to_insert)} 件完了")

        # 6. homework テーブルの移行
        print("  - 'homework' テーブルを移行中...")
        sqlite_cur.execute("SELECT * FROM homework")
        homework_items = sqlite_cur.fetchall()
        homework_to_insert = []
        for item in homework_items:
            new_student_id = student_id_map.get(item['student_id'])
            # master_textbook_idがNoneの場合も考慮
            new_master_textbook_id = master_textbook_id_map.get(item['master_textbook_id']) if item['master_textbook_id'] is not None else None
            if new_student_id:
                homework_to_insert.append((
                    new_student_id, new_master_textbook_id, item['custom_textbook_name'],
                    item['subject'], item['task'], item['task_date'],
                    item['task_group_id'], item['status'], item['other_info']
                ))
        if homework_to_insert:
            execute_values(pg_cur, """
                INSERT INTO homework (student_id, master_textbook_id, custom_textbook_name, subject, task, task_date, task_group_id, status, other_info)
                VALUES %s
            """, homework_to_insert)
        print(f"    -> {len(homework_to_insert)} 件完了")
        
        # 7. bulk_presets と bulk_preset_books の移行
        print("  - 'bulk_presets' と 'bulk_preset_books' テーブルを移行中...")
        sqlite_cur.execute("SELECT * FROM bulk_presets ORDER BY id")
        presets = sqlite_cur.fetchall()
        for preset in presets:
            old_id = preset['id']
            pg_cur.execute(
                "INSERT INTO bulk_presets (subject, preset_name) VALUES (%s, %s) RETURNING id",
                (preset['subject'], preset['preset_name'])
            )
            new_id = pg_cur.fetchone()[0]
            bulk_preset_id_map[old_id] = new_id

        sqlite_cur.execute("SELECT * FROM bulk_preset_books")
        preset_books = sqlite_cur.fetchall()
        preset_books_to_insert = []
        for book in preset_books:
            new_preset_id = bulk_preset_id_map.get(book['preset_id'])
            if new_preset_id:
                preset_books_to_insert.append((new_preset_id, book['book_name']))
        
        if preset_books_to_insert:
            execute_values(pg_cur, "INSERT INTO bulk_preset_books (preset_id, book_name) VALUES %s", preset_books_to_insert)
        print(f"    -> {len(presets)} 件のプリセットと {len(preset_books_to_insert)} 件の関連書籍を完了")

        # 8. past_exam_results テーブルの移行
        print("  - 'past_exam_results' テーブルを移行中...")
        sqlite_cur.execute("SELECT * FROM past_exam_results")
        exam_items = sqlite_cur.fetchall()
        exam_to_insert = []
        for item in exam_items:
            new_student_id = student_id_map.get(item['student_id'])
            if new_student_id:
                exam_to_insert.append((
                    new_student_id, item['date'], item['university_name'], item['faculty_name'],
                    item['exam_system'], item['year'], item['subject'],
                    item['time_required'], item['total_time_allowed'], item['correct_answers'], item['total_questions']
                ))
        if exam_to_insert:
            execute_values(pg_cur, """
                INSERT INTO past_exam_results (student_id, date, university_name, faculty_name, exam_system, year, subject, time_required, total_time_allowed, correct_answers, total_questions)
                VALUES %s
            """, exam_to_insert)
        print(f"    -> {len(exam_to_insert)} 件完了")

        # 9. 依存関係のないテーブル (bug_reports, changelog)
        print("  - 'bug_reports' と 'changelog' テーブルを移行中...")
        for table in ['bug_reports', 'changelog']:
            sqlite_cur.execute(f"SELECT * FROM {table}")
            rows = sqlite_cur.fetchall()
            if rows:
                df = pd.DataFrame([dict(row) for row in rows])
                if 'id' in df.columns:
                    df = df.drop(columns=['id'])
                engine = create_engine(POSTGRES_URL_EXTERNAL)
                df.to_sql(table, engine, if_exists='append', index=False)
                print(f"    -> {len(df)} 件のデータを '{table}' に移行しました。")

        # 全ての変更をコミット
        pg_conn.commit()
        print("\n🎉 全てのテーブルのデータ移行が正常に完了しました！")

    except (Exception, psycopg2.Error) as e:
        print(f"\n[エラー] 処理中にエラーが発生しました: {e}")
        pg_conn.rollback()
    finally:
        # 接続を閉じる
        sqlite_cur.close()
        sqlite_conn.close()
        pg_cur.close()
        pg_conn.close()


if __name__ == '__main__':
    print("="*60)
    print("SQLiteからPostgreSQLへのデータ移行を開始します。")
    print("【事前準備の確認】")
    print("1. RenderでPostgreSQLデータベースを作成し、`initialize_database.py`を実行して空のテーブルを作成しましたか？")
    print("2. RenderのDB設定ページから'External Database URL'をコピーし、`.env`ファイルに`DATABASE_URL_EXTERNAL`として設定しましたか？")
    print("3. `progress.db`ファイルをこのスクリプトと同じディレクトリに配置しましたか？")
    print("="*60)
    response = input("準備が完了していれば 'yes' と入力してください: ").lower()

    if response == 'yes':
        main()
    else:
        print("処理を中断しました。")