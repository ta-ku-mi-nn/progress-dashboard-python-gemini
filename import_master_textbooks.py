# import_master_textbooks.py

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
CSV_FILE = 'text_data.csv'

def import_textbooks_from_csv():
    """
    text_data.csv から参考書マスターデータを読み込み、重複を除去してデータベースに保存する。
    """
    if not os.path.exists(CSV_FILE):
        print(f"エラー: '{CSV_FILE}' が見つかりません。スクリプトを中止します。")
        return

    print("="*50)
    print("参考書マスターデータのインポートを開始します...")
    print("="*50)

    try:
        # --- ★★★ ここから修正 ★★★ ---
        # CSVファイルをPandasで読み込み、UTF-8エンコーディングを指定
        df = pd.read_csv(CSV_FILE, encoding='utf-8')
        # --- ★★★ ここまで修正 ★★★
        df.columns = ['level', 'subject', 'book_name', 'duration']
        print(f"1. '{CSV_FILE}' から {len(df)} 件のデータを読み込みました。")

        original_rows = len(df)
        df.drop_duplicates(subset=['subject', 'level', 'book_name'], keep='first', inplace=True)
        dropped_rows = original_rows - len(df)
        if dropped_rows > 0:
            print(f"   - {dropped_rows} 件の重複データを発見し、除去しました。")

        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS master_textbooks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                level TEXT NOT NULL,
                subject TEXT NOT NULL,
                book_name TEXT NOT NULL,
                duration REAL,
                UNIQUE(subject, level, book_name)
            )
        ''')
        print("2. 'master_textbooks' テーブルを準備しました。")

        cursor.execute("DELETE FROM master_textbooks;")
        print("3. 既存のマスターデータをクリアしました。")

        df.to_sql('master_textbooks', conn, if_exists='append', index=False)
        
        conn.commit()
        conn.close()

        print(f"4. {len(df)} 件のユニークなマスターデータをデータベースに保存しました。")
        print("\n🎉 インポートが正常に完了しました！")

    except Exception as e:
        print(f"\n[エラー] 処理中にエラーが発生しました: {e}")

if __name__ == '__main__':
    import_textbooks_from_csv()