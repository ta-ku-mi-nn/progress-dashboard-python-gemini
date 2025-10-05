import json
import sqlite3
from config.settings import APP_CONFIG

# --- 設定 ---
JSON_FILE = APP_CONFIG['data']['json_file'] # route-subject-text-time_new.json
DATABASE_FILE = 'progress.db'

def migrate_data():
    """
    JSONファイルからデータを読み込み、SQLiteデータベースに移行します。
    """
    # --- 1. JSONデータの読み込み ---
    print(f"'{JSON_FILE}' を読み込んでいます...")
    try:
        with open(JSON_FILE, 'r', encoding='utf-8') as f:
            # 修正点：開いたファイルオブジェクト 'f' を json.load に渡します
            json_data = json.load(f)
        source_data = json_data.get('data', {})
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"エラー: JSONファイルの読み込みに失敗しました: {e}")
        return

    # --- 2. データベースへの接続 ---
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        print(f"データベース '{DATABASE_FILE}' に接続しました。")
    except sqlite3.Error as e:
        print(f"データベースエラー: {e}")
        return

    # --- 3. データの移行処理 ---
    print("データの移行を開始します...")
    student_count = 0
    progress_count = 0

    for school, students in source_data.items():
        for student_name, details in students.items():
            student_info = details.get('data', {})

            # (1) 生徒を 'students' テーブルに追加
            try:
                cursor.execute(
                    "INSERT INTO students (name, school, deviation_value, main_instructor, sub_instructor) VALUES (?, ?, ?, ?, ?)",
                    (
                        student_name,
                        school,
                        student_info.get('偏差値'),
                        student_info.get('メイン講師'),
                        student_info.get('サブ講師')
                    )
                )
                student_id = cursor.lastrowid  # 追加した生徒のIDを取得
                student_count += 1

                # (2) 各科目の進捗を 'progress' テーブルに追加
                progress_data = details.get('progress', {})
                for subject, levels in progress_data.items():
                    for level, books in levels.items():
                        for book_name, book_details in books.items():
                            cursor.execute(
                                """
                                INSERT INTO progress (student_id, subject, level, book_name, duration, is_planned, is_done)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                                """,
                                (
                                    student_id,
                                    subject,
                                    level,
                                    book_name,
                                    book_details.get('所要時間'),
                                    book_details.get('予定'),
                                    book_details.get('達成済')
                                )
                            )
                            progress_count += 1

            except sqlite3.IntegrityError:
                print(f"警告: 生徒 '{student_name}' は校舎 '{school}' に既に存在するため、スキップします。")
            except sqlite3.Error as e:
                print(f"データベースエラー: {e}")

    # --- 4. 完了処理 ---
    conn.commit()
    conn.close()
    print("\n✅ データ移行が完了しました。")
    print(f"  - {student_count} 人の生徒を移行しました。")
    print(f"  - {progress_count} 件の進捗レコードを移行しました。")

if __name__ == '__main__':
    migrate_data()