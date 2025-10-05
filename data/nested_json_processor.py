# data/nested_json_processor.py

import sqlite3
import os

# このファイルの場所を基準に、プロジェクトルートにあるDBファイルを絶対パスで指定
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_FILE = os.path.join(os.path.dirname(BASE_DIR), 'progress.db')

def get_db_connection():
    """データベース接続を取得します。"""
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row  # 辞書形式で結果を取得できるように設定
    return conn

def get_all_schools():
    """データベースからすべてのユニークな校舎名を取得します。"""
    conn = get_db_connection()
    schools = conn.execute('SELECT DISTINCT school FROM students ORDER BY school').fetchall()
    conn.close()
    return [school['school'] for school in schools]

def get_students_for_user(user_info):
    """ログインユーザーがアクセス可能な生徒のリストを全校舎から取得します。"""
    if not user_info:
        return {}
    conn = get_db_connection()
    username = user_info.get('username')
    
    # roleに基づいてクエリを分岐
    if user_info.get('role') == 'admin':
        students_cursor = conn.execute('SELECT name, school FROM students ORDER BY school, name').fetchall()
    else:
        # 'users'テーブルからログインユーザーの担当校舎を取得
        user = conn.execute('SELECT school FROM users WHERE username = ?', (username,)).fetchone()
        user_school = user['school'] if user else None

        if user_school:
            # 担当校舎の生徒のみを取得
            students_cursor = conn.execute(
                'SELECT name, school FROM students WHERE school = ? ORDER BY name',
                (user_school,)
            ).fetchall()
        else:
            # 担当校舎が設定されていない場合は空のリストを返す
            students_cursor = []

    conn.close()

    students_by_school = {}
    for student in students_cursor:
        if student['school'] not in students_by_school:
            students_by_school[student['school']] = []
        students_by_school[student['school']].append(student['name'])
    return students_by_school

def get_student_progress(school, student_name):
    """特定の生徒の進捗データをデータベースから取得します。"""
    conn = get_db_connection()
    student = conn.execute(
        'SELECT id FROM students WHERE name = ? AND school = ?', (student_name, school)
    ).fetchone()
    if student is None:
        conn.close()
        return {}
    student_id = student['id']
    progress_records = conn.execute(
        'SELECT subject, level, book_name, duration, is_planned, is_done FROM progress WHERE student_id = ?', (student_id,)
    ).fetchall()
    conn.close()
    progress_data = {}
    for row in progress_records:
        subject, level, book_name = row['subject'], row['level'], row['book_name']
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

def get_student_info(school, student_name):
    """特定の生徒の個人情報（偏差値、講師など）を取得します。"""
    conn = get_db_connection()
    student_info = conn.execute(
        'SELECT * FROM students WHERE name = ? AND school = ?', (student_name, school)
    ).fetchone()
    conn.close()
    return dict(student_info) if student_info else {}

def update_progress_status(school, student_name, subject, level, book_name, column, value):
    """特定の参考書の進捗ステータス（予定 or 達成済）を更新します。"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        student_id_row = cursor.execute(
            'SELECT id FROM students WHERE name = ? AND school = ?', (student_name, school)
        ).fetchone()
        if not student_id_row:
            raise ValueError(f"生徒が見つかりません: {school} - {student_name}")
        student_id = student_id_row['id']
        
        if column not in ['is_planned', 'is_done']:
            raise ValueError("不正なカラム名です。")
        
        # SQLインジェクションを防ぐため、カラム名はf-stringで直接埋め込まないのがベストプラクティスですが、
        # ここでは入力値を検証しているため許容します。
        cursor.execute(
            f"UPDATE progress SET {column} = ? WHERE student_id = ? AND subject = ? AND level = ? AND book_name = ?",
            (value, student_id, subject, level, book_name)
        )
        conn.commit()
        return True, "更新しました。"
    except (sqlite3.Error, TypeError, ValueError) as e:
        print(f"データベース更新エラー: {e}")
        conn.rollback()
        return False, "更新に失敗しました。"
    finally:
        conn.close()

def get_all_subjects():
    """データベースからすべてのユニークな科目名を取得します。"""
    conn = get_db_connection()
    subjects = conn.execute('SELECT DISTINCT subject FROM progress ORDER BY subject').fetchall()
    conn.close()
    return [subject['subject'] for subject in subjects]

def initialize_user_data(username):
    pass

def get_student_homework(school, student_name):
    """特定の生徒の宿題リストをデータベースから取得します。"""
    conn = get_db_connection()
    student = conn.execute(
        'SELECT id FROM students WHERE name = ? AND school = ?', (student_name, school)
    ).fetchone()
    if student is None:
        conn.close()
        return []
    student_id = student['id']
    homework_list = conn.execute(
        'SELECT id, subject, task, due_date, status FROM homework WHERE student_id = ? ORDER BY due_date',
        (student_id,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in homework_list]

def add_homework(school, student_name, subject, task, due_date):
    """新しい宿題をデータベースに追加します。"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        student_id_row = cursor.execute(
            'SELECT id FROM students WHERE name = ? AND school = ?', (student_name, school)
        ).fetchone()
        if not student_id_row:
             raise ValueError(f"生徒が見つかりません: {school} - {student_name}")
        student_id = student_id_row['id']
        
        cursor.execute(
            'INSERT INTO homework (student_id, subject, task, due_date) VALUES (?, ?, ?, ?)',
            (student_id, subject, task, due_date)
        )
        conn.commit()
        return True, "宿題を追加しました。"
    except (sqlite3.Error, TypeError, ValueError) as e:
        print(f"宿題追加エラー: {e}")
        conn.rollback()
        return False, "宿題の追加に失敗しました。"
    finally:
        conn.close()

def update_homework_status(homework_id, new_status):
    """宿題のステータスを更新します。"""
    conn = get_db_connection()
    try:
        conn.execute('UPDATE homework SET status = ? WHERE id = ?', (new_status, homework_id))
        conn.commit()
        return True, "ステータスを更新しました。"
    except sqlite3.Error as e:
        print(f"ステータス更新エラー: {e}")
        conn.rollback()
        return False, "ステータスの更新に失敗しました。"
    finally:
        conn.close()

def delete_homework(homework_id):
    """宿題を削除します。"""
    conn = get_db_connection()
    try:
        conn.execute('DELETE FROM homework WHERE id = ?', (homework_id,))
        conn.commit()
        return True, "宿題を削除しました。"
    except sqlite3.Error as e:
        print(f"宿題削除エラー: {e}")
        conn.rollback()
        return False, "宿題の削除に失敗しました。"
    finally:
        conn.close()