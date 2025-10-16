# update_master_textbooks.py

import psycopg2
from psycopg2.extras import execute_values
import pandas as pd
import os
from config.settings import APP_CONFIG

# --- 設定 ---
DATABASE_URL = APP_CONFIG['data']['database_url']
CSV_FILE = 'text_data.csv'

def get_db_connection():
    """PostgreSQLデータベース接続を取得します。"""
    return psycopg2.connect(DATABASE_URL)

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
    print("="*50)

    conn = None  # 接続オブジェクトを初期化
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
        conn = get_db_connection()
        with conn.cursor() as cur:
            # 2. 'master_textbooks' テーブルの既存データをすべて削除 (TRUNCATEを使用)
            # TRUNCATEはDELETEよりも高速で、テーブルのIDシーケンスもリセットします。
            print("2. 既存の参考書マスターデータをクリアしています...")
            cur.execute("TRUNCATE TABLE master_textbooks RESTART IDENTITY CASCADE;")
            print("   -> 既存データをすべてクリアしました。")

            # 3. DataFrameからタプルのリストに変換して、新しいデータを挿入
            print("3. 新しいマスターデータをデータベースに保存しています...")
            data_to_insert = [tuple(row) for row in df.to_numpy()]
            
            # execute_values を使って高速に一括挿入
            execute_values(
                cur,
                "INSERT INTO master_textbooks (level, subject, book_name, duration) VALUES %s",
                data_to_insert
            )
            
            print(f"   -> {len(data_to_insert)} 件の新しいマスターデータを保存しました。")

        # 変更をコミット
        conn.commit()

        print("\n🎉 参考書マスターデータの更新が正常に完了しました！")

    except (Exception, psycopg2.Error) as e:
        print(f"\n[エラー] 処理中にエラーが発生しました: {e}")
        if conn:
            conn.rollback() # エラーが発生した場合は変更を取り消し
    finally:
        if conn:
            conn.close() # 接続を閉じる

if __name__ == '__main__':
    update_textbooks_from_csv()