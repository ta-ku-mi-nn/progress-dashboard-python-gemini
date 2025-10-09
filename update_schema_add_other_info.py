import sqlite3
import os

# データベースファイルのパス
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
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

def add_other_info_column():
    """homeworkテーブルにother_infoカラムを追加する"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()

    try:
        # カラムが存在しない場合のみ追加
        cursor.execute("PRAGMA table_info(homework)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if 'other_info' not in columns:
            # 備考などをJSON形式で保存するためのTEXT型のカラムを追加
            cursor.execute("""
                ALTER TABLE homework
                ADD COLUMN other_info TEXT
            """)
            print("homeworkテーブルに 'other_info' カラムを追加しました。")
        else:
            print("'other_info' カラムは既に存在します。")
        
        conn.commit()

    except sqlite3.Error as e:
        print(f"データベースの更新中にエラーが発生しました: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    add_other_info_column()