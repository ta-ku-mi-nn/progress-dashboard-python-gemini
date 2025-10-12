# update_master_textbooks.py

import sqlite3
import pandas as pd
import os

# --- 設定 ---
# RenderのDiskマウントパス（/var/data）が存在すればそちらを使用
RENDER_DATA_DIR = "/var/data"
if os.path.exists(RENDER_DATA_DIR):
    # 本番環境（Render）用のパス
    DB_DIR = RENDER_DATA_DIR
else:
    # このファイルと同じ階層にDBファイルがあると想定
    DB_DIR = os.path.dirname(os.path.abspath(__file__))

DATABASE_FILE = os.path.join(DB_DIR, 'progress.db')
CSV_FILE = 'text_data.csv'

def update_textbooks_from_csv():
    """
    text_data.csv から参考書マスターデータを読み込み、
    既存のマスターデータをクリアしてから、新しいデータで上書きします。
    """
    if not os.path.exists(CSV_FILE):
        print(f"エラー: '{CSV_FILE}' が見つかりません。スクリプトを中止します。")
        return

    print("="*50)
    print("参考書マスターデータの更新を開始します...")
    print(f"入力ファイル: {CSV_FILE}")
    print(f"対象データベース: {DATABASE_FILE}")
    print("="*50)

    try:
        # CSVファイルを読み込み、重複を除去
        df = pd.read_csv(CSV_FILE, encoding='utf-8')
        df.columns = ['level', 'subject', 'book_name', 'duration']
        original_rows = len(df)
        df.drop_duplicates(subset=['subject', 'level', 'book_name'], keep='first', inplace=True)
        
        print(f"1. '{CSV_FILE}' から {len(df)} 件のユニークなデータを読み込みました。")
        if original_rows > len(df):
            print(f"   ({original_rows - len(df)} 件の重複データは除去されました)")

        # データベースに接続
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        # 2. 'master_textbooks' テーブルの既存データをすべて削除
        cursor.execute("DELETE FROM master_textbooks;")
        print("2. 既存の参考書マスターデータをすべてクリアしました。")

        # 3. DataFrameからデータベースに新しいデータを挿入
        df.to_sql('master_textbooks', conn, if_exists='append', index=False)
        
        conn.commit()
        conn.close()

        print(f"3. {len(df)} 件の新しいマスターデータをデータベースに保存しました。")
        print("\n🎉 参考書マスターデータの更新が正常に完了しました！")

    except Exception as e:
        print(f"\n[エラー] 処理中にエラーが発生しました: {e}")

if __name__ == '__main__':
    update_textbooks_from_csv()