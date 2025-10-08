import sqlite3
import os

# データベースファイルのパス
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_FILE = os.path.join(BASE_DIR, 'progress.db')

def add_custom_textbook_name_column():
    """homeworkテーブルにcustom_textbook_nameカラムを追加する"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()

    try:
        # カラムが存在しない場合のみ追加
        cursor.execute("PRAGMA table_info(homework)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if 'custom_textbook_name' not in columns:
            cursor.execute("""
                ALTER TABLE homework
                ADD COLUMN custom_textbook_name TEXT
            """)
            print("homeworkテーブルに 'custom_textbook_name' カラムを追加しました。")
        else:
            print("'custom_textbook_name' カラムは既に存在します。")
        
        conn.commit()

    except sqlite3.Error as e:
        print(f"データベースの更新中にエラーが発生しました: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    add_custom_textbook_name_column()