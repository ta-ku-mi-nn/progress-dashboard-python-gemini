# setup_dev_environment.py

import sqlite3
import os
from werkzeug.security import generate_password_hash

# RenderのDiskマウントパス（/var/data）が存在すればそちらを使用
RENDER_DATA_DIR = "/var/data"
if os.path.exists(RENDER_DATA_DIR):
    DB_DIR = RENDER_DATA_DIR
else:
    DB_DIR = os.path.dirname(os.path.abspath(__file__))

DATABASE_FILE = os.path.join(DB_DIR, 'progress.db')

def get_db_connection():
    """データベース接続を取得します。"""
    conn = sqlite3.connect(DATABASE_FILE)
    return conn

def create_tables_if_not_exist(conn):
    """基本的なテーブルが存在しない場合に作成する"""
    print("--- テーブルの存在を確認・作成 ---")
    cursor = conn.cursor()
    
    # usersテーブル
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            school TEXT
        )
    ''')
    # studentsテーブル
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            school TEXT NOT NULL,
            deviation_value INTEGER,
            UNIQUE(school, name)
        )
    ''')
    # progressテーブル
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            subject TEXT NOT NULL,
            level TEXT NOT NULL,
            book_name TEXT NOT NULL,
            duration REAL,
            is_planned BOOLEAN,
            is_done BOOLEAN,
            completed_units INTEGER NOT NULL DEFAULT 0,
            total_units INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY (student_id) REFERENCES students (id)
        )
    ''')
    # homeworkテーブル
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS homework (
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
    conn.commit()
    print("--- 基本テーブルの準備完了 ---\n")


def clear_database(conn):
    """データベース内のすべての関連テーブルをクリアします。"""
    print("--- データベースのクリアを開始 ---")
    cursor = conn.cursor()
    
    cursor.execute("PRAGMA foreign_keys = OFF;")
    
    tables_to_clear = ['users', 'students', 'progress', 'homework', 'sqlite_sequence', 'student_instructors', 'master_textbooks', 'bulk_presets', 'bulk_preset_books', 'past_exam_results']
    for table in tables_to_clear:
        try:
            cursor.execute(f"DELETE FROM {table};")
            print(f"  - '{table}' テーブルをクリアしました。")
        except sqlite3.OperationalError:
            print(f"  - '{table}' テーブルは存在しないため、スキップします。")

    cursor.execute("PRAGMA foreign_keys = ON;")
    
    conn.commit()
    print("--- データベースのクリアが完了 ---\n")

def setup_users(conn):
    """指定された構成でユーザーを再作成します。"""
    print("--- ユーザーのセットアップを開始 ---")
    cursor = conn.cursor()

    users_to_create = [
        ('tokyo_admin', generate_password_hash('admin'), 'admin', '東京校'),
        ('tokyo_user1', generate_password_hash('user'), 'user', '東京校'),
        ('tokyo_user2', generate_password_hash('user'), 'user', '東京校'),
        ('osaka_admin', generate_password_hash('admin'), 'admin', '大阪校'),
        ('osaka_user1', generate_password_hash('user'), 'user', '大阪校'),
        ('osaka_user2', generate_password_hash('user'), 'user', '大阪校'),
        ('nagoya_admin', generate_password_hash('admin'), 'admin', '名古屋校'),
        ('nagoya_user1', generate_password_hash('user'), 'user', '名古屋校'),
        ('nagoya_user2', generate_password_hash('user'), 'user', '名古屋校'),
    ]

    cursor.executemany(
        'INSERT INTO users (username, password, role, school) VALUES (?, ?, ?, ?)',
        users_to_create
    )
    conn.commit()
    print(f"  - {len(users_to_create)} 件のユーザーを作成しました。")
    print("    (管理者のパスワードは 'admin', 一般ユーザーのパスワードは 'user' です)")
    print("--- ユーザーのセットアップが完了 ---\n")


def setup_students_and_data(conn):
    """指定された生徒と関連データを再作成します。"""
    print("--- 生徒およびサンプルデータのセットアップを開始 ---")
    cursor = conn.cursor()

    students_to_create = [
        ('生徒1', '東京校'), ('生徒2', '東京校'),
        ('生徒1', '大阪校'), ('生徒2', '大阪校'),
        ('生徒1', '名古屋校'), ('生徒2', '名古屋校'),
    ]
    
    cursor.executemany('INSERT INTO students (name, school) VALUES (?, ?)', students_to_create)
    conn.commit()
    print(f"  - {len(students_to_create)} 人の生徒を作成しました。")

    students = cursor.execute('SELECT id, name, school FROM students').fetchall()
    
    sample_progress = []
    sample_homework = []
    
    for student_id, student_name, school in students:
        sample_progress.extend([
            (student_id, '英語', '日大', 'システム英単語', 1.0, True, True, 1, 1),
            (student_id, '英語', '日大', '英文法ポラリス1', 1.5, True, False, 0, 1),
            (student_id, '数学', '日大', '数学Ⅰ・A 基礎問題精講', 2.0, True, False, 0, 1),
        ])
        sample_homework.extend([
            (student_id, '英語', 'システム英単語 1-100', '2025-10-10', '進行中'),
            (student_id, '数学', '基礎問題精講 P10-20', '2025-10-12', '未着手'),
        ])

    cursor.executemany(
        'INSERT INTO progress (student_id, subject, level, book_name, duration, is_planned, is_done, completed_units, total_units) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
        sample_progress
    )
    cursor.executemany(
        'INSERT INTO homework (student_id, subject, task, task_date, status) VALUES (?, ?, ?, ?, ?)',
        sample_homework
    )
    conn.commit()
    print(f"  - {len(sample_progress)} 件のサンプル学習進捗データを作成しました。")
    print(f"  - {len(sample_homework)} 件のサンプル宿題データを作成しました。")
    print("--- 生徒およびサンプルデータのセットアップが完了 ---\n")


if __name__ == '__main__':
    if not os.path.exists(os.path.dirname(DATABASE_FILE)):
        os.makedirs(os.path.dirname(DATABASE_FILE), exist_ok=True)

    print("="*60)
    print("開発環境リセットスクリプト")
    print("警告: このスクリプトはデータベース内の既存のデータをすべて削除します。")
    print("="*60)
    
    response = input("実行してもよろしいですか？ (yes/no): ").lower()
    
    if response == 'yes':
        connection = get_db_connection()
        create_tables_if_not_exist(connection) # ★★★ この行でテーブルを作成
        clear_database(connection)
        setup_users(connection)
        setup_students_and_data(connection)
        connection.close()
        print("\n🎉 初期セットアップが正常に完了しました！")
        print("次に、残りの更新スクリプトを実行してください。")
    else:
        print("\n処理を中断しました。")