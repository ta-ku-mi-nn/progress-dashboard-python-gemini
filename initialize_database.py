# initialize_database.py

import os
import pandas as pd
import json
from werkzeug.security import generate_password_hash
from datetime import date
import psycopg2
from psycopg2.extras import DictCursor, execute_values
from dotenv import load_dotenv

# .envファイルを読み込んで環境変数を設定
load_dotenv()

# --- 設定 ---
DATABASE_URL = os.getenv('DATABASE_URL')
CSV_FILE = 'text_data.csv'
JSON_FILE = 'bulk_buttons.json'


def get_db_connection():
    """PostgreSQLデータベース接続を取得します。"""
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def drop_all_tables(conn):
    """データベース内のすべてのテーブルを削除します。"""
    print("--- 既存テーブルの削除を開始 ---")
    with conn.cursor() as cur:
        # publicスキーマ内の全テーブルを取得
        cur.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public';")
        tables = cur.fetchall()
        for table in tables:
            table_name = table[0]
            try:
                # CASCADE をつけて関連するオブジェクトも削除
                cur.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE;")
                print(f"  - '{table_name}' テーブルを削除しました。")
            except psycopg2.Error as e:
                print(f"  - '{table_name}' の削除中にエラーが発生しました: {e}")
    conn.commit()
    print("--- テーブルの削除が完了 ---\n")


def create_all_tables(conn):
    """最新のスキーマですべてのテーブルを作成します。"""
    print("--- 最新スキーマでのテーブル作成を開始 ---")
    with conn.cursor() as cur:

        # usersテーブル (SERIAL PRIMARY KEY を使用)
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                school TEXT
            )
        ''')

        # studentsテーブル
        cur.execute('''
            CREATE TABLE IF NOT EXISTS students (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                school TEXT NOT NULL,
                deviation_value INTEGER,
                UNIQUE(school, name)
            )
        ''')
    
        # student_instructors テーブル
        cur.execute('''
            CREATE TABLE IF NOT EXISTS student_instructors (
                id SERIAL PRIMARY KEY,
                student_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                is_main INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                UNIQUE(student_id, user_id)
            )
        ''')

        # master_textbooksテーブル
        cur.execute('''
            CREATE TABLE IF NOT EXISTS master_textbooks (
                id SERIAL PRIMARY KEY,
                level TEXT NOT NULL,
                subject TEXT NOT NULL,
                book_name TEXT NOT NULL,
                duration REAL,
                UNIQUE(subject, level, book_name)
            )
        ''')

        # progressテーブル
        cur.execute('''
            CREATE TABLE IF NOT EXISTS progress (
                id SERIAL PRIMARY KEY,
                student_id INTEGER NOT NULL,
                subject TEXT NOT NULL,
                level TEXT NOT NULL,
                book_name TEXT NOT NULL,
                duration REAL,
                is_planned BOOLEAN,
                is_done BOOLEAN,
                completed_units INTEGER NOT NULL DEFAULT 0,
                total_units INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE
            )
        ''')

        # homeworkテーブル
        cur.execute('''
            CREATE TABLE IF NOT EXISTS homework (
                id SERIAL PRIMARY KEY,
                student_id INTEGER NOT NULL,
                master_textbook_id INTEGER REFERENCES master_textbooks(id),
                custom_textbook_name TEXT,
                subject TEXT NOT NULL,
                task TEXT NOT NULL,
                task_date TEXT NOT NULL,
                task_group_id TEXT,
                status TEXT NOT NULL DEFAULT '未着手',
                other_info TEXT,
                FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE
            )
        ''')

        # bulk_presetsテーブル
        cur.execute('''
            CREATE TABLE IF NOT EXISTS bulk_presets (
                id SERIAL PRIMARY KEY,
                subject TEXT NOT NULL,
                preset_name TEXT NOT NULL,
                UNIQUE(subject, preset_name)
            )
        ''')

        # bulk_preset_booksテーブル
        cur.execute('''
            CREATE TABLE IF NOT EXISTS bulk_preset_books (
                id SERIAL PRIMARY KEY,
                preset_id INTEGER NOT NULL,
                book_name TEXT NOT NULL,
                FOREIGN KEY (preset_id) REFERENCES bulk_presets (id) ON DELETE CASCADE
            )
        ''')

        # past_exam_resultsテーブル
        cur.execute('''
            CREATE TABLE IF NOT EXISTS past_exam_results (
                id SERIAL PRIMARY KEY,
                student_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                university_name TEXT NOT NULL,
                faculty_name TEXT,
                exam_system TEXT,
                year INTEGER NOT NULL,
                subject TEXT NOT NULL,
                time_required INTEGER,
                total_time_allowed INTEGER,
                correct_answers INTEGER,
                total_questions INTEGER,
                FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE
            )
        ''')
    
        # bug_reportsテーブル
        cur.execute('''
            CREATE TABLE IF NOT EXISTS bug_reports (
                id SERIAL PRIMARY KEY,
                reporter_username TEXT NOT NULL,
                report_date TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT '未対応',
                resolution_message TEXT
            )
        ''')
    
        # changelogテーブル
        cur.execute('''
            CREATE TABLE IF NOT EXISTS changelog (
                id SERIAL PRIMARY KEY,
                version TEXT NOT NULL,
                release_date TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL
            )
        ''')

    conn.commit()
    print("--- 全テーブルの作成完了 ---\n")


def setup_initial_data(conn):
    """ユーザー、生徒、サンプル進捗などの初期データを投入します。"""
    print("--- 初期データのセットアップを開始 ---")
    with conn.cursor() as cur:
        # ユーザーの作成
        users_to_create = [
            ('tokyo_admin', generate_password_hash('admin'), 'admin', '東京校'),
            ('tokyo_user1', generate_password_hash('user'), 'user', '東京校'),
            ('osaka_admin', generate_password_hash('admin'), 'admin', '大阪校'),
            ('osaka_user1', generate_password_hash('user'), 'user', '大阪校'),
            ('nagoya_admin', generate_password_hash('admin'), 'admin', '名古屋校'),
            ('nagoya_user1', generate_password_hash('user'), 'user', '名古屋校'),
        ]
        execute_values(cur, 'INSERT INTO users (username, password, role, school) VALUES %s', users_to_create)
        print(f"  - {len(users_to_create)} 件のユーザーを作成しました。")

        # 生徒の作成
        students_to_create = [
            ('生徒A', '東京校', 65), ('生徒B', '東京校', 58),
            ('生徒C', '大阪校', 62), ('生徒D', '大阪校', 55),
            ('生徒E', '名古屋校', 68), ('生徒F', '名古屋校', 60),
        ]
        execute_values(cur, 'INSERT INTO students (name, school, deviation_value) VALUES %s', students_to_create)
        print(f"  - {len(students_to_create)} 人の生徒を作成しました。")

        # 講師と生徒の関連付け
        students_df = pd.read_sql("SELECT id, school FROM students", conn)
        users_df = pd.read_sql("SELECT id, school, role FROM users", conn)
        
        instructors_to_add = []
        for _, student in students_df.iterrows():
            main_instructor = users_df[(users_df['school'] == student['school']) & (users_df['role'] == 'admin')]
            if not main_instructor.empty:
                main_instructor_id = main_instructor.iloc[0]['id']
                instructors_to_add.append((student['id'], main_instructor_id, 1))
        
        execute_values(cur, "INSERT INTO student_instructors (student_id, user_id, is_main) VALUES %s", instructors_to_add)
        print(f"  - {len(instructors_to_add)} 件の講師・生徒関係を作成しました。")
    
        # 更新履歴の追加
        changelog_entries = [
            ('1.1.0', date(2025, 10, 12).isoformat(), '更新履歴機能の追加', 'サイドバーに「更新履歴」ページを追加し、アプリケーションの変更点を確認できるようにしました。'),
            ('1.0.0', date(2025, 10, 1).isoformat(), '初期リリース', '学習進捗ダッシュボードの最初のバージョンをリリースしました。')
        ]
        execute_values(cur, "INSERT INTO changelog (version, release_date, title, description) VALUES %s", changelog_entries)
        print(f"  - {len(changelog_entries)} 件の更新履歴を追加しました。")

    conn.commit()
    print("--- 初期データのセットアップが完了 ---\n")


def import_master_textbooks(conn):
    """text_data.csv から参考書マスターデータをインポートします。"""
    if not os.path.exists(CSV_FILE):
        print(f"[警告] '{CSV_FILE}' が見つかりません。参考書マスターのインポートをスキップします。")
        return

    print("--- 参考書マスターデータのインポートを開始 ---")
    df = pd.read_csv(CSV_FILE, encoding='utf-8')
    df.columns = ['level', 'subject', 'book_name', 'duration']
    df.drop_duplicates(subset=['subject', 'level', 'book_name'], keep='first', inplace=True)
    
    with conn.cursor() as cur:
        data_to_insert = [tuple(row) for row in df.to_numpy()]
        execute_values(
            cur,
            "INSERT INTO master_textbooks (level, subject, book_name, duration) VALUES %s",
            data_to_insert
        )
    conn.commit()
    print(f"  - {len(df)} 件のユニークなマスターデータをデータベースに保存しました。")
    print("--- インポート完了 ---\n")


def setup_bulk_presets_from_json(conn):
    """bulk_buttons.json から一括登録プリセットをセットアップします。"""
    if not os.path.exists(JSON_FILE):
        print(f"[警告] '{JSON_FILE}' が見つかりません。プリセットのセットアップをスキップします。")
        return
        
    print("--- 一括登録プリセットのセットアップを開始 ---")
    with conn.cursor() as cur:
        with open(JSON_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)

        for subject, presets in config.items():
            for preset_name, books in presets.items():
                cur.execute("INSERT INTO bulk_presets (subject, preset_name) VALUES (%s, %s) RETURNING id", (subject, preset_name))
                preset_id = cur.fetchone()[0]
                book_inserts = [(preset_id, book_name) for book_name in books]
                execute_values(cur, "INSERT INTO bulk_preset_books (preset_id, book_name) VALUES %s", book_inserts)
    
    conn.commit()
    print("--- プリセットのセットアップ完了 ---\n")


if __name__ == '__main__':
    if not DATABASE_URL:
        print("エラー: 環境変数 'DATABASE_URL' が設定されていません。")
        print(".envファイルを作成するか、環境変数を設定してください。")
        exit()

    print("="*60)
    print("警告: このスクリプトはPostgreSQLデータベースを完全にリセットします。")
    print("      データベース内のすべてのデータが削除されます。")
    print(f"対象データベース: {DATABASE_URL.split('@')[-1]}") # パスワードなどを隠して表示
    print("="*60)
    response = input("実行してもよろしいですか？ (yes/no): ").lower()
    if response != 'yes':
        print("\n処理を中断しました。")
        exit()

    connection = None
    try:
        connection = get_db_connection()
        
        # 1. すべてのテーブルを一旦削除
        drop_all_tables(connection)

        # 2. 最新のスキーマでテーブルを再作成
        create_all_tables(connection)
        
        # 3. 初期データを投入
        setup_initial_data(connection)
        
        # 4. CSV/JSONからデータをインポート
        import_master_textbooks(connection)
        setup_bulk_presets_from_json(connection)
        
        print("\n🎉🎉🎉 データベースの初期化がすべて完了しました！ 🎉🎉🎉")

    except (Exception, psycopg2.Error) as e:
        print(f"\n[エラー] 処理中に致命的なエラーが発生しました: {e}")
        if connection:
            connection.rollback()
    finally:
        if connection:
            connection.close()