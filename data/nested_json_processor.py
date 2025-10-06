# data/nested_json_processor.py

import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_FILE = os.path.join(os.path.dirname(BASE_DIR), 'progress.db')

def get_db_connection():
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def get_all_schools():
    conn = get_db_connection()
    schools = conn.execute('SELECT DISTINCT school FROM students ORDER BY school').fetchall()
    conn.close()
    return [school['school'] for school in schools]

def get_students_for_user(user_info):
    if not user_info:
        return {}
    conn = get_db_connection()
    username = user_info.get('username')
    
    if user_info.get('role') == 'admin':
        students_cursor = conn.execute('SELECT name, school FROM students ORDER BY school, name').fetchall()
    else:
        user = conn.execute('SELECT school FROM users WHERE username = ?', (username,)).fetchone()
        user_school = user['school'] if user else None
        if user_school:
            students_cursor = conn.execute(
                'SELECT name, school FROM students WHERE school = ? ORDER BY name',
                (user_school,)
            ).fetchall()
        else:
            students_cursor = []
    conn.close()
    students_by_school = {}
    for student in students_cursor:
        if student['school'] not in students_by_school:
            students_by_school[student['school']] = []
        students_by_school[student['school']].append(student['name'])
    return students_by_school

def get_student_progress(school, student_name):
    """達成割合のカラムも取得するように修正"""
    conn = get_db_connection()
    student = conn.execute('SELECT id FROM students WHERE name = ? AND school = ?', (student_name, school)).fetchone()
    if student is None:
        conn.close()
        return {}
    student_id = student['id']
    # master_textbooks と LEFT JOIN して、生徒に進捗がない参考書も取得できるようにする
    # さらに、completed_units と total_units も取得
    progress_records = conn.execute(
        """
        SELECT 
            p.subject, p.level, p.book_name, 
            COALESCE(p.duration, m.duration, 0) as duration,
            p.is_planned, p.is_done,
            COALESCE(p.completed_units, 0) as completed_units,
            COALESCE(p.total_units, 1) as total_units
        FROM progress p
        LEFT JOIN master_textbooks m ON p.book_name = m.book_name AND p.subject = m.subject AND p.level = m.level
        WHERE p.student_id = ?
        """, (student_id,)
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
            '達成済': bool(row['is_done']),
            'completed_units': row['completed_units'],
            'total_units': row['total_units']
        }
    return progress_data

def get_student_info(school, student_name):
    conn = get_db_connection()
    student_info = conn.execute('SELECT * FROM students WHERE name = ? AND school = ?', (student_name, school)).fetchone()
    conn.close()
    return dict(student_info) if student_info else {}

def get_master_textbook_list(subject, search_term=""):
    conn = get_db_connection()
    query = "SELECT level, book_name FROM master_textbooks WHERE subject = ?"
    params = [subject]
    if search_term:
        query += " AND book_name LIKE ?"
        params.append(f"%{search_term}%")
    records = conn.execute(query, tuple(params)).fetchall()
    conn.close()
    level_order = ['基礎徹底', '日大', 'MARCH', '早慶']
    textbooks_by_level = {}
    for row in records:
        level, book_name = row['level'], row['book_name']
        if level not in textbooks_by_level:
            textbooks_by_level[level] = []
        textbooks_by_level[level].append(book_name)
    sorted_textbooks = {level: textbooks_by_level[level] for level in level_order if level in textbooks_by_level}
    for level in textbooks_by_level:
        if level not in sorted_textbooks:
            sorted_textbooks[level] = textbooks_by_level[level]
    return sorted_textbooks

def add_or_update_student_progress(school, student_name, progress_updates):
    """達成割合も保存できるように修正"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        student_id_row = cursor.execute('SELECT id FROM students WHERE name = ? AND school = ?', (student_name, school)).fetchone()
        if not student_id_row:
            raise ValueError(f"生徒が見つかりません: {school} - {student_name}")
        student_id = student_id_row['id']
        for update in progress_updates:
            existing = cursor.execute(
                "SELECT id FROM progress WHERE student_id = ? AND subject = ? AND level = ? AND book_name = ?",
                (student_id, update['subject'], update['level'], update['book_name'])
            ).fetchone()
            
            is_done = update.get('completed_units', 0) >= update.get('total_units', 1)
            
            if existing:
                cursor.execute(
                    "UPDATE progress SET is_planned = ?, is_done = ?, completed_units = ?, total_units = ? WHERE id = ?",
                    (update['is_planned'], is_done, update.get('completed_units', 0), update.get('total_units', 1), existing['id'])
                )
            else:
                master_book = cursor.execute(
                    "SELECT duration FROM master_textbooks WHERE subject = ? AND level = ? AND book_name = ?",
                    (update['subject'], update['level'], update['book_name'])
                ).fetchone()
                duration = master_book['duration'] if master_book else 0

                cursor.execute(
                    "INSERT INTO progress (student_id, subject, level, book_name, is_planned, is_done, duration, completed_units, total_units) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (student_id, update['subject'], update['level'], update['book_name'], update['is_planned'], is_done, duration, update.get('completed_units', 0), update.get('total_units', 1))
                )
        conn.commit()
        return True, f"{len(progress_updates)}件の進捗を更新しました。"
    except (sqlite3.Error, ValueError) as e:
        print(f"進捗の一括更新エラー: {e}")
        conn.rollback()
        return False, "進捗の更新に失敗しました。"
    finally:
        conn.close()

# --- これ以降の関数 (homework関連) は変更なし ---
def get_all_subjects():
    conn = get_db_connection()
    subjects = conn.execute('SELECT DISTINCT subject FROM master_textbooks ORDER BY subject').fetchall()
    conn.close()
    return [subject['subject'] for subject in subjects]

def get_student_homework(school, student_name):
    conn = get_db_connection()
    student = conn.execute('SELECT id FROM students WHERE name = ? AND school = ?', (student_name, school)).fetchone()
    if student is None:
        conn.close()
        return []
    student_id = student['id']
    homework_list = conn.execute('SELECT id, subject, task, due_date, status FROM homework WHERE student_id = ? ORDER BY due_date', (student_id,)).fetchall()
    conn.close()
    return [dict(row) for row in homework_list]

def add_homework(school, student_name, subject, task, due_date):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        student_id_row = cursor.execute('SELECT id FROM students WHERE name = ? AND school = ?', (student_name, school)).fetchone()
        if not student_id_row:
             raise ValueError(f"生徒が見つかりません: {school} - {student_name}")
        student_id = student_id_row['id']
        cursor.execute('INSERT INTO homework (student_id, subject, task, due_date) VALUES (?, ?, ?, ?)', (student_id, subject, task, due_date))
        conn.commit()
        return True, "宿題を追加しました。"
    except (sqlite3.Error, TypeError, ValueError) as e:
        print(f"宿題追加エラー: {e}")
        conn.rollback()
        return False, "宿題の追加に失敗しました。"
    finally:
        conn.close()

def update_homework_status(homework_id, new_status):
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