# update_schema_for_multiple_instructors.py

import sqlite3
import pandas as pd
import os

# RenderのDiskマウントパス（/var/data）が存在すればそちらを使用
RENDER_DATA_DIR = "/var/data"
if os.path.exists(RENDER_DATA_DIR):
    # 本番環境（Render）用のパス
    DB_DIR = RENDER_DATA_DIR
else:
    # ローカル開発環境用のパス (プロジェクトのルートディレクトリを指す)
    # このファイルの2階層上がプロジェクトルート
    DB_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATABASE_FILE = os.path.join(DB_DIR, 'progress.db')

def update_student_schema_for_multiple_instructors():
    print("--- 生徒・講師関連テーブルのスキーマ更新を開始 ---")
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        # --- 1. student_instructors テーブルの作成 ---
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS student_instructors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                is_main INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (student_id) REFERENCES students (id),
                FOREIGN KEY (user_id) REFERENCES users (id),
                UNIQUE(student_id, user_id)
            )
        ''')
        print("  - 'student_instructors' テーブルを準備しました。")

        # --- 2. 既存のstudentsテーブルから講師情報を移行 ---
        df_students_info = pd.read_sql_query("PRAGMA table_info(students)", conn)

        # sub_instructorカラムが存在する場合のみデータ移行処理を行う
        if 'sub_instructor' in df_students_info['name'].values:
            print("  - 旧スキーマを検出。講師データの移行を開始します。")
            
            # 既存の生徒と講師の情報を取得
            students = pd.read_sql_query("SELECT id, school, sub_instructor FROM students", conn)
            users = pd.read_sql_query("SELECT id, username, school, role FROM users", conn)
            
            instructors_to_add = []
            
            for _, student in students.iterrows():
                # メイン講師 (admin) を設定
                main_instructor = users[(users['school'] == student['school']) & (users['role'] == 'admin')]
                if not main_instructor.empty:
                    main_instructor_id = main_instructor.iloc[0]['id']
                    instructors_to_add.append((student['id'], main_instructor_id, 1))

                # サブ講師を設定
                if student['sub_instructor']:
                    sub_instructor = users[users['username'] == student['sub_instructor']]
                    if not sub_instructor.empty:
                        sub_instructor_id = sub_instructor.iloc[0]['id']
                        instructors_to_add.append((student['id'], sub_instructor_id, 0))

            # student_instructorsテーブルにデータを挿入（重複は無視）
            cursor.executemany(
                "INSERT OR IGNORE INTO student_instructors (student_id, user_id, is_main) VALUES (?, ?, ?)",
                instructors_to_add
            )
            print(f"  - {len(instructors_to_add)} 件の講師・生徒関係を移行しました。")

            # --- 3. studentsテーブルの再構築（sub_instructorカラムの削除） ---
            print("  - 'students' テーブルを再構築します。")
            cursor.execute("ALTER TABLE students RENAME TO students_old_for_instructor_migration;")
            cursor.execute('''
                CREATE TABLE students (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    school TEXT NOT NULL,
                    deviation_value INTEGER,
                    UNIQUE(school, name)
                )
            ''')
            cursor.execute('''
                INSERT INTO students (id, name, school, deviation_value)
                SELECT id, name, school, deviation_value FROM students_old_for_instructor_migration;
            ''')
            cursor.execute("DROP TABLE students_old_for_instructor_migration;")
            print("  - 'students' テーブルから 'sub_instructor' カラムを削除しました。")

        else:
            print("  - スキーマは既に更新済みか、移行対象のデータがありません。")

        conn.commit()
        conn.close()
        print("--- スキーマ更新完了 ---")

    except sqlite3.Error as e:
        print(f"\n[エラー] データベース操作中にエラーが発生しました: {e}")

if __name__ == '__main__':
    update_student_schema_for_multiple_instructors()