# migrate_data.py

import sqlite3
import pandas as pd
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()

# --- 設定 ---
SQLITE_DB_PATH = 'progress.db' # 手順1でダウンロードしたファイル
POSTGRES_URL_EXTERNAL = os.getenv('DATABASE_URL_EXTERNAL') # Renderから取得する外部接続URL

if not POSTGRES_URL_EXTERNAL:
    print("エラー: 環境変数 'DATABASE_URL_EXTERNAL' が設定されていません。")
    print(".envファイルにRenderのPostgreSQLページの'External Database URL'を設定してください。")
    exit()

def migrate_table(table_name, sqlite_conn, pg_engine):
    """指定されたテーブルのデータをSQLiteからPostgreSQLに移行する"""
    try:
        print(f"テーブル '{table_name}' のデータ移行を開始...")
        # SQLiteからデータをDataFrameに読み込む
        df = pd.read_sql_query(f'SELECT * FROM {table_name}', sqlite_conn)
        
        # 'id'カラムが存在する場合は削除する（PostgreSQL側で自動採番させるため）
        if 'id' in df.columns:
            df = df.drop(columns=['id'])

        if not df.empty:
            # PostgreSQLにデータを書き込む
            # SQLAlchemyエンジンを使うことで、データ型が適切に処理される
            df.to_sql(table_name, pg_engine, if_exists='append', index=False)
            print(f" -> {len(df)} 件のデータを '{table_name}' に移行しました。")
        else:
            print(f" -> '{table_name}' にはデータがありませんでした。スキップします。")
            
    except Exception as e:
        print(f"エラー: テーブル '{table_name}' の移行中に問題が発生しました: {e}")

def main():
    # PostgreSQLへの接続エンジンを作成
    pg_engine = create_engine(POSTGRES_URL_EXTERNAL)
    
    # SQLiteへの接続
    sqlite_conn = sqlite3.connect(SQLITE_DB_PATH)
    
    # 移行したいテーブルのリスト
    # 外部キー制約の順序を考慮して、参照されるテーブルから先に移行します
    tables_to_migrate = [
        'users',
        'students',
        'master_textbooks',
        'student_instructors',
        'progress',
        'homework',
        'bulk_presets',
        'bulk_preset_books',
        'past_exam_results',
        'bug_reports',
        'changelog'
    ]
    
    for table in tables_to_migrate:
        migrate_table(table, sqlite_conn, pg_engine)
        
    sqlite_conn.close()
    print("\n🎉 全てのテーブルのデータ移行が完了しました！")

if __name__ == '__main__':
    print("="*60)
    print("SQLiteからPostgreSQLへのデータ移行を開始します。")
    print("【事前準備の確認】")
    print("1. RenderでPostgreSQLデータベースを作成し、`initialize_database.py`を実行してテーブルを作成しましたか？")
    print("2. RenderのDB設定ページから'External Database URL'をコピーし、このプロジェクトの`.env`ファイルに`DATABASE_URL_EXTERNAL`として設定しましたか？")
    print("3. `progress.db`ファイルをこのスクリプトと同じディレクトリに配置しましたか？")
    print("="*60)
    response = input("準備が完了していれば 'yes' と入力してください: ").lower()

    if response == 'yes':
        main()
    else:
        print("処理を中断しました。")