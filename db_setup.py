import sqlite3

DATABASE_FILE = 'progress.db'

def create_tables():
    """
    データベースファイルと、必要なテーブル（students, progress, homework）を作成します。
    """
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        print(f"データベース '{DATABASE_FILE}' に接続しました。")

        # --- 生徒テーブル (students) ---
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            school TEXT NOT NULL,
            deviation_value INTEGER,
            main_instructor TEXT,
            sub_instructor TEXT,
            UNIQUE(school, name)
        )
        ''')
        print("テーブル 'students' を確認しました。")

        # --- 進捗テーブル (progress) ---
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
            FOREIGN KEY (student_id) REFERENCES students (id)
        )
        ''')
        print("テーブル 'progress' を確認しました。")

        # --- 【新規追加】宿題テーブル (homework) ---
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS homework (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            subject TEXT NOT NULL,
            task TEXT NOT NULL,
            due_date TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT '未着手',  -- (未着手, 進行中, 完了)
            FOREIGN KEY (student_id) REFERENCES students (id)
        )
        ''')
        print("✅ 新しいテーブル 'homework' を作成しました（または既に存在します）。")

        conn.commit()

    except sqlite3.Error as e:
        print(f"データベースエラーが発生しました: {e}")
    finally:
        if conn:
            conn.close()
            print("データベース接続を閉じました。")

if __name__ == '__main__':
    create_tables()