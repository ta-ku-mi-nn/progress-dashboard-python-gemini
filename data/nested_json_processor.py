"""
SQLiteデータベースとの接続とデータ操作を行う関数群を定義します。
"""
import sqlite3
from datetime import datetime

DATABASE_FILE = 'progress.db'

def get_db_connection():
    """データベース接続を取得します。"""
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# --- 生徒・進捗関連の関数 (変更なし) ---

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
    if user_info.get('role') == 'admin':
        students_cursor = conn.execute('SELECT name, school FROM students ORDER BY school, name').fetchall()
    else:
        students_cursor = conn.execute(
            'SELECT name, school FROM students WHERE main_instructor = ? OR sub_instructor = ? ORDER BY school, name',
            (username, username)
        ).fetchall()
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

def update_progress_status(school, student_name, subject, level, book_name, column, value):
    """特定の参考書の進捗ステータス（予定 or 達成済）を更新します。"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        student_id = cursor.execute(
            'SELECT id FROM students WHERE name = ? AND school = ?', (student_name, school)
        ).fetchone()['id']
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

def initialize_user_data(username):
    pass

# --- 【新規追加】宿題管理関連の関数 ---

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
    
    # フロントエンドで扱いやすいように辞書のリストに変換
    return [dict(row) for row in homework_list]

def add_homework(school, student_name, subject, task, due_date):
    """新しい宿題をデータベースに追加します。"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        student_id = cursor.execute(
            'SELECT id FROM students WHERE name = ? AND school = ?', (student_name, school)
        ).fetchone()['id']
        
        cursor.execute(
            'INSERT INTO homework (student_id, subject, task, due_date) VALUES (?, ?, ?, ?)',
            (student_id, subject, task, due_date)
        )
        conn.commit()
        return True, "宿題を追加しました。"
    except (sqlite3.Error, TypeError) as e:
        print(f"宿題追加エラー: {e}")
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
        return False, "宿題の削除に失敗しました。"
    finally:
        conn.close()