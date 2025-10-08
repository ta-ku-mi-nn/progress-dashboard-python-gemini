import sqlite3
import os

# データベースファイルのパス
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_FILE = os.path.join(BASE_DIR, 'progress.db')

def add_master_textbook_id_column():
    """homeworkテーブルにmaster_textbook_idカラムを追加する"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()

    try:
        # カラムが存在しない場合のみ追加
        cursor.execute("PRAGMA table_info(homework)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if 'master_textbook_id' not in columns:
            cursor.execute("""
                ALTER TABLE homework
                ADD COLUMN master_textbook_id INTEGER REFERENCES master_textbooks(id)
            """)
            print("homeworkテーブルに 'master_textbook_id' カラムを追加しました。")
        else:
            print("'master_textbook_id' カラムは既に存在します。")

        # 既存の 'subject' カラムを削除（今後はtextbook_idで管理するため）
        # if 'subject' in columns:
        #     # SQLiteは直接のDROP COLUMNをサポートしていないため、テーブルを再作成する方法が一般的ですが、
        #     # 今回は簡単のため、このカラムは残しておきます。新規データでは使用されなくなります。
        #     print("'subject'カラムは残されますが、新規の宿題登録では使用されません。")
        
        conn.commit()

    except sqlite3.Error as e:
        print(f"データベースの更新中にエラーが発生しました: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    add_master_textbook_id_column()