# update_mock_exam_table_split_kokugo.py
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')

def update_database():
    conn = psycopg2.connect(DATABASE_URL)
    print("--- mock_exam_results テーブルの国語分割対応を開始 ---")
    try:
        with conn.cursor() as cur:
            # 1. 新しいカラムを追加
            print("  - 新しいカラム (現代文, 古文, 漢文) を追加しています...")
            cur.execute("ALTER TABLE mock_exam_results ADD COLUMN IF NOT EXISTS subject_gendaibun_mark INTEGER;")
            cur.execute("ALTER TABLE mock_exam_results ADD COLUMN IF NOT EXISTS subject_kobun_mark INTEGER;")
            cur.execute("ALTER TABLE mock_exam_results ADD COLUMN IF NOT EXISTS subject_kanbun_mark INTEGER;")
            
            # 2. 既存のデータを移行 (旧 subject_kokugo_mark を 現代文 にコピー)
            print("  - 既存の国語データを現代文カラムに移行しています...")
            cur.execute("UPDATE mock_exam_results SET subject_gendaibun_mark = subject_kokugo_mark WHERE subject_gendaibun_mark IS NULL;")
            
            # 3. 旧カラムの削除 (任意：安全のためコメントアウトしていますが、完全に移行したら実行してもOKです)
            # cur.execute("ALTER TABLE mock_exam_results DROP COLUMN IF EXISTS subject_kokugo_mark;")
            
        conn.commit()
        print("✅ データベースの更新が正常に完了しました。")
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    update_database()