import sqlite3
from config.settings import APP_CONFIG

# --- データベースファイル名を設定 ---
# settings.py に 'db_file' を追加するのが望ましいですが、簡単のため直接記述します。
DATABASE_FILE = 'progress.db'

def create_tables():
    """
    データベースファイルと、必要なテーブル（students, progress）を作成します。
    """
    try:
        # データベースに接続（ファイルがなければ自動的に作成される）
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        print(f"データベース '{DATABASE_FILE}' に接続しました。")

        # --- 生徒テーブル (students) ---
        # 生徒の基本情報を格納します。
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
        print("テーブル 'students' を作成しました（または既に存在します）。")

        # --- 進捗テーブル (progress) ---
        # 各生徒の参考書の進捗を格納します。
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
        print("テーブル 'progress' を作成しました（または既に存在します）。")

        # 変更をデータベースに保存
        conn.commit()

    except sqlite3.Error as e:
        print(f"データベースエラーが発生しました: {e}")
    finally:
        if conn:
            conn.close()
            print("データベース接続を閉じました。")

if __name__ == '__main__':
    create_tables()