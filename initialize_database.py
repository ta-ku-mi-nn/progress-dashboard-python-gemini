# initialize_database.py

import os
import pandas as pd
import json
from werkzeug.security import generate_password_hash
from datetime import date
import psycopg2
from psycopg2.extras import DictCursor, execute_values
from dotenv import load_dotenv

# .envファイルを読み込んで環境変数を設定
load_dotenv()

# --- 設定 ---
DATABASE_URL = os.getenv('DATABASE_URL')
CSV_FILE = 'text_data.csv'
JSON_FILE = 'bulk_buttons.json'


def get_db_connection():
    """PostgreSQLデータベース接続を取得します。"""
    return psycopg2.connect(DATABASE_URL)

def drop_all_tables(conn):
    """データベース内のすべてのテーブルを削除します。"""
    print("--- 既存テーブルの削除を開始 ---")
    with conn.cursor() as cur:
        # テーブルとその依存関係を取得 (外部キー制約を考慮)
        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        tables = [row[0] for row in cur.fetchall()]

        # 依存関係の逆順で削除を試みる (単純な例)
        # より堅牢にするには依存関係グラフを構築する必要がある
        for table_name in reversed(tables):
            try:
                # CASCADE をつけて依存オブジェクトも削除
                cur.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE;")
                print(f"  - '{table_name}' テーブルを削除しました。")
            except psycopg2.Error as e:
                # 既に削除されている場合などは無視できるエラーもある
                if "does not exist" in str(e):
                     print(f"  - '{table_name}' は既に削除されています。")
                else:
                    print(f"  - '{table_name}' の削除中にエラーが発生しました: {e}")
                    # エラーが発生した場合でも他のテーブル削除を続けるため、ここではロールバックしない
    conn.commit() # ループ完了後にコミット
    print("--- テーブルの削除が完了 ---\n")


def create_all_tables(conn):
    """最新のスキーマですべてのテーブルを作成します。"""
    print("--- 最新スキーマでのテーブル作成を開始 ---")
    with conn.cursor() as cur:

        # usersテーブル
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                school TEXT
            )
        ''')
        print("  - 'users' テーブルを作成しました（または確認）。")

        # studentsテーブル
        cur.execute('''
            CREATE TABLE IF NOT EXISTS students (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                school TEXT NOT NULL,
                deviation_value INTEGER,
                target_level TEXT,       -- ★ 追加: 志望校レベル
                grade TEXT,              -- ★ 追加: 学年
                previous_school TEXT,    -- ★ 追加: 出身校・在籍校
                UNIQUE(school, name)
            )
        ''')
        print("  - 'students' テーブルを作成しました（または確認）。")

        # student_instructors テーブル
        cur.execute('''
            CREATE TABLE IF NOT EXISTS student_instructors (
                id SERIAL PRIMARY KEY,
                student_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                is_main INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                UNIQUE(student_id, user_id)
            )
        ''')
        print("  - 'student_instructors' テーブルを作成しました（または確認）。")

        # master_textbooksテーブル
        cur.execute('''
            CREATE TABLE IF NOT EXISTS master_textbooks (
                id SERIAL PRIMARY KEY,
                level TEXT NOT NULL,
                subject TEXT NOT NULL,
                book_name TEXT NOT NULL,
                duration REAL,
                UNIQUE(subject, level, book_name)
            )
        ''')
        print("  - 'master_textbooks' テーブルを作成しました（または確認）。")

        # progressテーブル (UNIQUE制約を追加)
        cur.execute('''
            CREATE TABLE IF NOT EXISTS progress (
                id SERIAL PRIMARY KEY,
                student_id INTEGER NOT NULL,
                subject TEXT NOT NULL,
                level TEXT NOT NULL,
                book_name TEXT NOT NULL,
                duration REAL,
                is_planned BOOLEAN,
                is_done BOOLEAN,
                completed_units INTEGER NOT NULL DEFAULT 0,
                total_units INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE,
                UNIQUE (student_id, subject, level, book_name)
            )
        ''')
        print("  - 'progress' テーブルを作成しました（または確認）。")

        # homeworkテーブル
        cur.execute('''
            CREATE TABLE IF NOT EXISTS homework (
                id SERIAL PRIMARY KEY,
                student_id INTEGER NOT NULL,
                master_textbook_id INTEGER REFERENCES master_textbooks(id) ON DELETE SET NULL, -- 削除時にNULLに設定
                custom_textbook_name TEXT,
                subject TEXT NOT NULL,
                task TEXT NOT NULL,
                task_date TEXT NOT NULL,
                task_group_id TEXT,
                status TEXT NOT NULL DEFAULT '未着手',
                other_info TEXT,
                FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE
            )
        ''')
        print("  - 'homework' テーブルを作成しました（または確認）。")

        # bulk_presetsテーブル
        cur.execute('''
            CREATE TABLE IF NOT EXISTS bulk_presets (
                id SERIAL PRIMARY KEY,
                subject TEXT NOT NULL,
                preset_name TEXT NOT NULL,
                UNIQUE(subject, preset_name)
            )
        ''')
        print("  - 'bulk_presets' テーブルを作成しました（または確認）。")

        # bulk_preset_booksテーブル
        cur.execute('''
            CREATE TABLE IF NOT EXISTS bulk_preset_books (
                id SERIAL PRIMARY KEY,
                preset_id INTEGER NOT NULL,
                book_name TEXT NOT NULL,
                FOREIGN KEY (preset_id) REFERENCES bulk_presets (id) ON DELETE CASCADE
            )
        ''')
        print("  - 'bulk_preset_books' テーブルを作成しました（または確認）。")

        # past_exam_resultsテーブル
        cur.execute('''
            CREATE TABLE IF NOT EXISTS past_exam_results (
                id SERIAL PRIMARY KEY,
                student_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                university_name TEXT NOT NULL,
                faculty_name TEXT,
                exam_system TEXT,
                year INTEGER NOT NULL,
                subject TEXT NOT NULL,
                time_required INTEGER,
                total_time_allowed INTEGER,
                correct_answers INTEGER,
                total_questions INTEGER,
                FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE
            )
        ''')
        print("  - 'past_exam_results' テーブルを作成しました（または確認）。")

        # university_acceptance テーブル (期日関連列も含む)
        cur.execute('''
            CREATE TABLE IF NOT EXISTS university_acceptance (
                id SERIAL PRIMARY KEY,
                student_id INTEGER NOT NULL,
                university_name TEXT NOT NULL,
                faculty_name TEXT NOT NULL,
                department_name TEXT,
                exam_system TEXT,
                result TEXT, -- '合格', '不合格', または NULL
                application_deadline TEXT,
                exam_date TEXT,
                announcement_date TEXT,
                procedure_deadline TEXT,
                FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE
            )
        ''')
        print("  - 'university_acceptance' テーブルを作成しました（または確認）。")

        # feature_requests テーブル
        cur.execute('''
            CREATE TABLE IF NOT EXISTS feature_requests (
                id SERIAL PRIMARY KEY,
                reporter_username TEXT NOT NULL,
                report_date TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT '未対応', -- '未対応', '検討中', '対応済', '見送り'
                resolution_message TEXT
            )
        ''')
        print("  - 'feature_requests' テーブルを作成しました（または確認）。")

        # bug_reportsテーブル
        cur.execute('''
            CREATE TABLE IF NOT EXISTS bug_reports (
                id SERIAL PRIMARY KEY,
                reporter_username TEXT NOT NULL,
                report_date TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT '未対応',
                resolution_message TEXT
            )
        ''')
        print("  - 'bug_reports' テーブルを作成しました（または確認）。")

        # changelogテーブル
        cur.execute('''
            CREATE TABLE IF NOT EXISTS changelog (
                id SERIAL PRIMARY KEY,
                version TEXT NOT NULL,
                release_date TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL
            )
        ''')
        print("  - 'changelog' テーブルを作成しました（または確認）。")

        # ★★★ mock_exam_results テーブルを追加 ★★★
        cur.execute('''
            CREATE TABLE IF NOT EXISTS mock_exam_results (
                id SERIAL PRIMARY KEY,
                student_id INTEGER NOT NULL,
                result_type TEXT NOT NULL,          -- 自己採点 or 結果
                mock_exam_name TEXT NOT NULL,       -- 模試の種類 (例: 共通テスト模試)
                mock_exam_format TEXT NOT NULL,     -- 模試の形式 (例: マーク, 記述)
                grade TEXT NOT NULL,                -- 学年 (例: 高3)
                round TEXT NOT NULL,                -- 回数 (例: 第1回)
                exam_date DATE,                     -- 受験日 (任意)
                -- 記述科目
                subject_kokugo_desc INTEGER,
                subject_math_desc INTEGER,
                subject_english_desc INTEGER,
                subject_rika1_desc INTEGER,
                subject_rika2_desc INTEGER,
                subject_shakai1_desc INTEGER,
                subject_shakai2_desc INTEGER,
                -- マーク科目
                subject_kokugo_mark INTEGER,
                subject_math1a_mark INTEGER,
                subject_math2bc_mark INTEGER,
                subject_english_r_mark INTEGER,
                subject_english_l_mark INTEGER,
                subject_rika1_mark INTEGER,
                subject_rika2_mark INTEGER,
                subject_shakai1_mark INTEGER,
                subject_shakai2_mark INTEGER,
                subject_rika_kiso1_mark INTEGER,
                subject_rika_kiso2_mark INTEGER,
                subject_info_mark INTEGER,
                -- 外部キー制約
                FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE
            )
        ''')
        print("  - 'mock_exam_results' テーブルを作成しました（または確認）。")
        # ★★★ ここまで追加 ★★★

    conn.commit()
    print("--- 全テーブルの作成完了 ---\n")


def setup_initial_data(conn):
    """ユーザー、生徒、サンプル進捗などの初期データを投入します。"""
    print("--- 初期データのセットアップを開始 ---")
    with conn.cursor(cursor_factory=DictCursor) as cur:
        # 既存データの存在チェックと削除 (より安全に)
        cur.execute("SELECT COUNT(*) FROM users")
        if cur.fetchone()[0] > 0:
            print("  - 既存のユーザーデータが見つかったため、スキップします。")
        else:
            # ユーザーの作成
            users_to_create = [
                ('tokyo_admin', generate_password_hash('admin'), 'admin', '東京校'),
                ('tokyo_user1', generate_password_hash('user'), 'user', '東京校'),
                ('osaka_admin', generate_password_hash('admin'), 'admin', '大阪校'),
                ('osaka_user1', generate_password_hash('user'), 'user', '大阪校'),
                ('nagoya_admin', generate_password_hash('admin'), 'admin', '名古屋校'),
                ('nagoya_user1', generate_password_hash('user'), 'user', '名古屋校'),
            ]
            execute_values(cur, 'INSERT INTO users (username, password, role, school) VALUES %s', users_to_create)
            print(f"  - {len(users_to_create)} 件のユーザーを作成しました。")

        cur.execute("SELECT COUNT(*) FROM students")
        if cur.fetchone()[0] > 0:
            print("  - 既存の生徒データが見つかったため、スキップします。")
        else:
            # 生徒の作成
            students_to_create = [
                ('生徒A', '東京校', 65), ('生徒B', '東京校', 58),
                ('生徒C', '大阪校', 62), ('生徒D', '大阪校', 55),
                ('生徒E', '名古屋校', 68), ('生徒F', '名古屋校', 60),
            ]
            execute_values(cur, 'INSERT INTO students (name, school, deviation_value) VALUES %s', students_to_create)
            print(f"  - {len(students_to_create)} 人の生徒を作成しました。")

        cur.execute("SELECT COUNT(*) FROM student_instructors")
        if cur.fetchone()[0] > 0:
            print("  - 既存の講師・生徒関係データが見つかったため、スキップします。")
        else:
             # 講師と生徒の関連付け (エラーハンドリング強化)
            try:
                cur.execute("SELECT id, school FROM students")
                students_list = [dict(row) for row in cur.fetchall()]
                cur.execute("SELECT id, school, role FROM users")
                users_list = [dict(row) for row in cur.fetchall()]

                instructors_to_add = []
                for student in students_list:
                    # メイン講師を見つける (管理者の中から同じ校舎の人)
                    main_instructor = next((user for user in users_list if user['school'] == student['school'] and user['role'] == 'admin'), None)
                    if main_instructor:
                        main_instructor_id = int(main_instructor['id'])
                        student_id = int(student['id'])
                        instructors_to_add.append((student_id, main_instructor_id, 1)) # is_main=1
                    else:
                         print(f"  - 警告: 生徒 {student['name']} ({student['school']}) のメイン講師(管理者)が見つかりません。")

                if instructors_to_add:
                    execute_values(cur, "INSERT INTO student_instructors (student_id, user_id, is_main) VALUES %s", instructors_to_add)
                    print(f"  - {len(instructors_to_add)} 件の講師・生徒関係を作成しました。")
                else:
                    print("  - 追加する講師・生徒関係がありませんでした。")
            except Exception as e:
                 print(f"  - 講師・生徒関連付け中にエラー: {e}")
                 conn.rollback() # エラーが発生したらこの部分の変更をロールバック

        cur.execute("SELECT COUNT(*) FROM changelog")
        if cur.fetchone()[0] > 0:
            print("  - 既存の更新履歴データが見つかったため、スキップします。")
        else:
            # 更新履歴の追加
            changelog_entries = [
                ('1.1.0', date(2025, 10, 12).isoformat(), '更新履歴機能の追加', 'サイドバーに「更新履歴」ページを追加し、アプリケーションの変更点を確認できるようにしました。'),
                ('1.0.0', date(2025, 10, 1).isoformat(), '初期リリース', '学習進捗ダッシュボードの最初のバージョンをリリースしました。')
            ]
            execute_values(cur, "INSERT INTO changelog (version, release_date, title, description) VALUES %s", changelog_entries)
            print(f"  - {len(changelog_entries)} 件の更新履歴を追加しました。")

    conn.commit() # すべての変更をコミット
    print("--- 初期データのセットアップが完了 ---\n")


def import_master_textbooks(conn):
    """text_data.csv から参考書マスターデータをインポートします。"""
    if not os.path.exists(CSV_FILE):
        print(f"[警告] '{CSV_FILE}' が見つかりません。参考書マスターのインポートをスキップします。")
        return

    print("--- 参考書マスターデータのインポートを開始 ---")
    try:
        df = pd.read_csv(CSV_FILE, encoding='utf-8')
        df.columns = ['level', 'subject', 'book_name', 'duration']
        original_count = len(df)
        df.drop_duplicates(subset=['subject', 'level', 'book_name'], keep='first', inplace=True)
        unique_count = len(df)
        print(f"  - CSVから {original_count} 件読み込み、{unique_count} 件のユニークなデータを検出しました。")

        with conn.cursor() as cur:
            # 既存データの確認
            cur.execute("SELECT COUNT(*) FROM master_textbooks")
            existing_count = cur.fetchone()[0]
            if existing_count > 0:
                 print(f"  - 既存のマスターデータが {existing_count} 件あります。CSVからのインポートをスキップします。")
                 print("  - 更新する場合は、一度テーブルを空にするか、update_master_textbooks.py スクリプトを使用してください。")
                 return

            # データ挿入
            data_to_insert = [tuple(row) for row in df.to_numpy()]
            execute_values(
                cur,
                "INSERT INTO master_textbooks (level, subject, book_name, duration) VALUES %s",
                data_to_insert
            )
        conn.commit()
        print(f"  - {unique_count} 件のマスターデータをデータベースに保存しました。")
    except Exception as e:
         print(f"  - [エラー] インポート中にエラーが発生しました: {e}")
         conn.rollback()
    print("--- インポート完了 ---\n")


def setup_bulk_presets_from_json(conn):
    """bulk_buttons.json から一括登録プリセットをセットアップします。"""
    if not os.path.exists(JSON_FILE):
        print(f"[警告] '{JSON_FILE}' が見つかりません。プリセットのセットアップをスキップします。")
        return

    print("--- 一括登録プリセットのセットアップを開始 ---")
    try:
        with conn.cursor() as cur:
            # 既存データの確認
            cur.execute("SELECT COUNT(*) FROM bulk_presets")
            existing_count = cur.fetchone()[0]
            if existing_count > 0:
                 print(f"  - 既存のプリセットデータが {existing_count} 件あります。JSONからのインポートをスキップします。")
                 return

            with open(JSON_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)

            preset_count = 0
            book_relation_count = 0
            for subject, presets in config.items():
                for preset_name, books in presets.items():
                    try:
                        cur.execute("INSERT INTO bulk_presets (subject, preset_name) VALUES (%s, %s) ON CONFLICT DO NOTHING RETURNING id", (subject, preset_name))
                        result = cur.fetchone()
                        if result: # 新規挿入された場合のみ
                            preset_id = result[0]
                            preset_count += 1
                            book_inserts = [(preset_id, book_name) for book_name in books]
                            if book_inserts:
                                execute_values(cur, "INSERT INTO bulk_preset_books (preset_id, book_name) VALUES %s", book_inserts)
                                book_relation_count += len(book_inserts)
                        # else: # 既に存在する場合はスキップ
                        #    print(f"  - プリセット '{subject} - {preset_name}' は既に存在するためスキップします。")
                    except psycopg2.Error as insert_error:
                         print(f"  - [エラー] プリセット '{subject} - {preset_name}' の挿入中にエラー: {insert_error}")
                         conn.rollback() # エラー箇所のみロールバックして継続試行

        conn.commit()
        print(f"  - {preset_count} 件の新規プリセットと {book_relation_count} 件の書籍関連を保存しました。")
    except FileNotFoundError:
        print(f"  - [エラー] '{JSON_FILE}' が見つかりませんでした。")
    except json.JSONDecodeError:
         print(f"  - [エラー] '{JSON_FILE}' の形式が正しくありません。")
    except Exception as e:
         print(f"  - [エラー] プリセット設定中に予期せぬエラーが発生しました: {e}")
         if conn: conn.rollback() # 念のためロールバック
    print("--- プリセットのセットアップ完了 ---\n")


if __name__ == '__main__':
    if not DATABASE_URL:
        print("エラー: 環境変数 'DATABASE_URL' が設定されていません。")
        exit()

    print("="*60)
    print("データベース初期化スクリプト")
    print(f"対象データベース: {DATABASE_URL.split('@')[-1]}")
    print("\n警告: このスクリプトは既存のテーブルを削除し、新しいスキーマで再作成します。")
    print("      既存のデータはすべて失われます。")
    print("      デモデータ（ユーザー、生徒、更新履歴）を投入します。")
    print("      CSV/JSONファイルが存在し、DBが空の場合のみマスターデータ・プリセットを投入します。")
    print("="*60)

    # 削除確認をより明確に
    response_drop = input("本当に既存のテーブルを全て削除してもよろしいですか？ (yes/no): ").lower()
    if response_drop != 'yes':
        print("\n処理を中断しました。")
        exit()

    response_run = input("上記を理解した上で、初期化処理を実行しますか？ (yes/no): ").lower()
    if response_run != 'yes':
        print("\n処理を中断しました。")
        exit()

    connection = None
    try:
        connection = get_db_connection()

        drop_all_tables(connection)
        create_all_tables(connection)

        # 初期データ投入（デモデータ）
        setup_initial_data(connection)

        # CSV/JSONからのデータ投入（DBが空の場合のみ）
        import_master_textbooks(connection)
        setup_bulk_presets_from_json(connection)

        print("\n🎉🎉🎉 データベースの初期化がすべて完了しました！ 🎉🎉🎉")

    except (Exception, psycopg2.Error) as e:
        print(f"\n[エラー] 処理中に致命的なエラーが発生しました: {e}")
        if connection:
            connection.rollback()
    finally:
        if connection:
            connection.close()
            print("データベース接続を閉じました。")