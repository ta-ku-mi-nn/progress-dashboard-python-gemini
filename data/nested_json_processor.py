"""
SQLiteデータベースとの接続とデータ操作を行う関数群を定義します。
"""
import sqlite3

DATABASE_FILE = 'progress.db'

def get_db_connection():
    """データベース接続を取得します。"""
    conn = sqlite3.connect(DATABASE_FILE)
    # 辞書形式で結果を取得できるように設定
    conn.row_factory = sqlite3.Row
    return conn

def load_data_from_db():
    """
    アプリケーション起動時にデータベースから基本的な構造を取得します。
    （実際には各コールバックが必要なデータを都度取得します）
    この関数は、アプリがデータソースを見失わないためのプレースホルダーとしての役割が強いです。
    """
    # この関数は後方互換性のために残しますが、主要なデータ取得は
    # 各コールバック内で直接行われるようになります。
    print("🗄️ データベースモードで起動します。")
    return {} # ダミーの空辞書を返します

# --- データ取得用ヘルパー関数群（SQLite対応） ---

def get_all_schools():
    """データベースからすべてのユニークな校舎名を取得します。"""
    conn = get_db_connection()
    schools = conn.execute('SELECT DISTINCT school FROM students ORDER BY school').fetchall()
    conn.close()
    return [school['school'] for school in schools]

def get_students_for_user(user_info):
    """
    ログインユーザーがアクセス可能な生徒のリストを全校舎から取得します。
    """
    if not user_info:
        return []

    conn = get_db_connection()
    username = user_info.get('username')
    
    if user_info.get('role') == 'admin':
        # 管理者は全生徒を取得
        students_cursor = conn.execute('SELECT name, school FROM students ORDER BY school, name').fetchall()
    else:
        # 一般ユーザーは担当生徒のみ取得
        students_cursor = conn.execute(
            'SELECT name, school FROM students WHERE main_instructor = ? OR sub_instructor = ? ORDER BY school, name',
            (username, username)
        ).fetchall()
        
    conn.close()
    
    # フロントエンドで使いやすいように整形
    # 例: {'東京校': ['生徒A', '生徒B'], '大阪校': ['生徒C']}
    students_by_school = {}
    for student in students_cursor:
        if student['school'] not in students_by_school:
            students_by_school[student['school']] = []
        students_by_school[student['school']].append(student['name'])
        
    return students_by_school


def get_student_progress(school, student_name):
    """特定の生徒の進捗データをデータベースから取得します。"""
    conn = get_db_connection()
    
    # 1. 生徒名と校舎名から生徒IDを取得
    student = conn.execute(
        'SELECT id FROM students WHERE name = ? AND school = ?', (student_name, school)
    ).fetchone()
    
    if student is None:
        conn.close()
        return {}

    student_id = student['id']
    
    # 2. 生徒IDを使って進捗データを取得
    progress_records = conn.execute(
        'SELECT subject, level, book_name, duration, is_planned, is_done FROM progress WHERE student_id = ?', (student_id,)
    ).fetchall()
    conn.close()

    # 3. JSONライクなネスト構造に変換して返す
    progress_data = {}
    for row in progress_records:
        subject = row['subject']
        level = row['level']
        book_name = row['book_name']
        
        if subject not in progress_data:
            progress_data[subject] = {}
        if level not in progress_data[subject]:
            progress_data[subject][level] = {}
            
        progress_data[subject][level][book_name] = {
            '所要時間': row['duration'],
            '予定': bool(row['is_planned']),
            '達成済': bool(row['is_done'])
        }
        
    return progress_data

def update_progress_status(school, student_name, subject, level, book_name, column, value):
    """特定の参考書の進捗ステータス（予定 or 達成済）を更新します。"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 1. 生徒IDを取得
        student_id = cursor.execute(
            'SELECT id FROM students WHERE name = ? AND school = ?', (student_name, school)
        ).fetchone()['id']

        # 2. 対象の進捗レコードを更新
        # column名は安全のためホワイトリスト形式でチェック
        if column not in ['is_planned', 'is_done']:
            raise ValueError("不正なカラム名です。")

        cursor.execute(
            f"UPDATE progress SET {column} = ? WHERE student_id = ? AND subject = ? AND level = ? AND book_name = ?",
            (value, student_id, subject, level, book_name)
        )
        conn.commit()
        return True, "更新しました。"
    except (sqlite3.Error, TypeError) as e:
        print(f"データベース更新エラー: {e}")
        return False, "更新に失敗しました。"
    finally:
        conn.close()

def get_all_subjects():
    """データベースからすべてのユニークな科目名を取得します。"""
    conn = get_db_connection()
    subjects = conn.execute('SELECT DISTINCT subject FROM progress ORDER BY subject').fetchall()
    conn.close()
    return [subject['subject'] for subject in subjects]

# initialize_user_data はデータベース移行に伴い不要になるため、passのままにする
def initialize_user_data(username):
    pass