# data/nested_json_processor.py

import psycopg2
from psycopg2.extras import DictCursor
import os
import json
import uuid
import pandas as pd
from datetime import datetime, timedelta
from config.settings import APP_CONFIG

DATABASE_URL = APP_CONFIG['data']['database_url']

def get_db_connection():
    """PostgreSQLデータベース接続を取得します。"""
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def get_all_schools():
    conn = get_db_connection()
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute('SELECT DISTINCT school FROM students ORDER BY school')
        schools = cur.fetchall()
    conn.close()
    return [school['school'] for school in schools]

def get_students_for_user(user_info):
    if not user_info:
        return {}
    conn = get_db_connection()
    username = user_info.get('username')
    
    with conn.cursor(cursor_factory=DictCursor) as cur:
        if user_info.get('role') == 'admin':
            cur.execute('SELECT name, school FROM students ORDER BY school, name')
            students_cursor = cur.fetchall()
        else:
            cur.execute('SELECT school FROM users WHERE username = %s', (username,))
            user = cur.fetchone()
            user_school = user['school'] if user else None
            if user_school:
                cur.execute(
                    'SELECT name, school FROM students WHERE school = %s ORDER BY name',
                    (user_school,)
                )
                students_cursor = cur.fetchall()
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
    conn = get_db_connection()
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute('SELECT id FROM students WHERE name = %s AND school = %s', (student_name, school))
        student = cur.fetchone()
        if student is None:
            conn.close()
            return {}
        student_id = student['id']
        
        cur.execute(
            """
            SELECT 
                p.subject, p.level, p.book_name, 
                COALESCE(p.duration, m.duration, 0) as duration,
                p.is_planned, p.is_done,
                COALESCE(p.completed_units, 0) as completed_units,
                COALESCE(p.total_units, 1) as total_units
            FROM progress p
            LEFT JOIN master_textbooks m ON p.book_name = m.book_name AND p.subject = m.subject AND p.level = m.level
            WHERE p.student_id = %s
            """, (student_id,)
        )
        progress_records = cur.fetchall()
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
    
def get_student_info_by_id(student_id):
    """生徒IDに基づいて生徒情報を取得する"""
    conn = get_db_connection()
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute('SELECT * FROM students WHERE id = %s', (student_id,))
        student = cur.fetchone()
        if not student:
            conn.close()
            return {}
        
        cur.execute('''
            SELECT u.username, si.is_main
            FROM student_instructors si
            JOIN users u ON si.user_id = u.id
            WHERE si.student_id = %s
        ''', (student_id,))
        instructors = cur.fetchall()
    
    conn.close()
    
    student_info = dict(student)
    student_info['main_instructors'] = [i['username'] for i in instructors if i['is_main'] == 1]
    student_info['sub_instructors'] = [i['username'] for i in instructors if i['is_main'] == 0]
    
    return student_info

def get_student_progress_by_id(student_id):
    """生徒IDに基づいて生徒の進捗データを取得する"""
    conn = get_db_connection()
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute(
            """
            SELECT 
                p.subject, p.level, p.book_name, 
                COALESCE(p.duration, m.duration, 0) as duration,
                p.is_planned, p.is_done,
                COALESCE(p.completed_units, 0) as completed_units,
                COALESCE(p.total_units, 1) as total_units
            FROM progress p
            LEFT JOIN master_textbooks m ON p.book_name = m.book_name AND p.subject = m.subject AND p.level = m.level
            WHERE p.student_id = %s
            """, (student_id,)
        )
        progress_records = cur.fetchall()
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
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute('SELECT id FROM students WHERE name = %s AND school = %s', (student_name, school))
        student = cur.fetchone()
    if not student:
        conn.close()
        return {}
    conn.close()
    return get_student_info_by_id(student['id'])

def get_assigned_students_for_user(user_id):
    """指定されたユーザーIDに紐づく生徒のリスト（idとname）を取得する"""
    if not user_id:
        return []
    conn = get_db_connection()
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute('''
            SELECT s.id, s.name
            FROM students s
            JOIN student_instructors si ON s.id = si.student_id
            WHERE si.user_id = %s
            ORDER BY s.name
        ''', (user_id,))
        students = cur.fetchall()
    conn.close()
    return [dict(row) for row in students]

def get_master_textbook_list(subject, search_term=""):
    conn = get_db_connection()
    with conn.cursor(cursor_factory=DictCursor) as cur:
        query = "SELECT level, book_name FROM master_textbooks WHERE subject = %s"
        params = [subject]
        if search_term:
            query += " AND book_name LIKE %s"
            params.append(f"%{search_term}%")
        cur.execute(query, tuple(params))
        records = cur.fetchall()
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
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute('SELECT id FROM students WHERE name = %s AND school = %s', (student_name, school))
            student_id_row = cur.fetchone()
            if not student_id_row:
                raise ValueError(f"生徒が見つかりません: {school} - {student_name}")
            student_id = student_id_row['id']
            for update in progress_updates:
                cur.execute(
                    "SELECT id FROM progress WHERE student_id = %s AND subject = %s AND level = %s AND book_name = %s",
                    (student_id, update['subject'], update['level'], update['book_name'])
                )
                existing = cur.fetchone()
                
                is_done = update.get('completed_units', 0) >= update.get('total_units', 1)
                duration = update.get('duration', None)
                
                if existing:
                    cur.execute(
                        "UPDATE progress SET is_planned = %s, is_done = %s, completed_units = %s, total_units = %s, duration = %s WHERE id = %s",
                        (update['is_planned'], is_done, update.get('completed_units', 0), update.get('total_units', 1), duration, existing['id'])
                    )
                else:
                    cur.execute(
                        "INSERT INTO progress (student_id, subject, level, book_name, is_planned, is_done, completed_units, total_units, duration) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                        (student_id, update['subject'], update['level'], update['book_name'], update['is_planned'], is_done, update.get('completed_units', 0), update.get('total_units', 1), duration)
                    )
        conn.commit()
        return True, f"{len(progress_updates)}件の進捗を更新しました。"
    except (Exception, psycopg2.Error) as e:
        print(f"進捗の一括更新エラー: {e}")
        conn.rollback()
        return False, "進捗の更新に失敗しました。"
    finally:
        conn.close()

def get_all_subjects():
    """データベースからすべての科目を指定された順序で取得する"""
    conn = get_db_connection()
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute('SELECT DISTINCT subject FROM master_textbooks')
        subjects_raw = cur.fetchall()
    conn.close()
    
    all_subjects = [s['subject'] for s in subjects_raw]
    
    subject_order = [
        '英語', '国語', '数学', '日本史', '世界史', '政治経済', '物理', '化学', '生物'
    ]
    
    sorted_subjects = sorted(
        all_subjects,
        key=lambda s: subject_order.index(s) if s in subject_order else len(subject_order)
    )
    
    return sorted_subjects

def get_subjects_for_student(student_id):
    """生徒の学習予定がある科目のみを取得する"""
    conn = get_db_connection()
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute(
            'SELECT DISTINCT subject FROM progress WHERE student_id = %s AND is_planned = true',
            (student_id,)
        )
        subjects_raw = cur.fetchall()
    conn.close()
    
    student_subjects = [s['subject'] for s in subjects_raw]
    
    subject_order = [
        '英語', '国語', '数学', '日本史', '世界史', '政治経済', '物理', '化学', '生物'
    ]
    
    sorted_subjects = sorted(
        student_subjects,
        key=lambda s: subject_order.index(s) if s in subject_order else len(subject_order)
    )
    return sorted_subjects

def get_all_homework_for_student(student_id):
    """特定の生徒の宿題をすべて取得する (参考書名も結合)"""
    conn = get_db_connection()
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute(
            """
            SELECT
                hw.id,
                hw.master_textbook_id,
                hw.custom_textbook_name,
                hw.task,
                hw.task_date,
                hw.status,
                COALESCE(mt.book_name, hw.custom_textbook_name) AS textbook_name,
                mt.subject
            FROM homework hw
            LEFT JOIN master_textbooks mt ON hw.master_textbook_id = mt.id
            WHERE hw.student_id = %s
            ORDER BY mt.subject, textbook_name, hw.task_date
            """,
            (student_id,)
        )
        homework_list = cur.fetchall()
    conn.close()
    return [dict(row) for row in homework_list]


def get_homework_for_textbook(student_id, textbook_id, custom_textbook_name=None):
    """特定の生徒・参考書(またはカスタム名)の宿題を取得する"""
    conn = get_db_connection()
    with conn.cursor(cursor_factory=DictCursor) as cur:
        query = """
            SELECT id, task, task_date, status, other_info
            FROM homework
            WHERE student_id = %s AND 
        """
        params = [student_id]

        if textbook_id:
            query += "master_textbook_id = %s"
            params.append(textbook_id)
        elif custom_textbook_name:
            query += "custom_textbook_name = %s"
            params.append(custom_textbook_name)
        else:
            return []

        query += " ORDER BY task_date"
        
        cur.execute(query, tuple(params))
        homework_list = cur.fetchall()
    conn.close()
    return [dict(row) for row in homework_list]


def add_or_update_homework(student_id, subject, textbook_id, custom_textbook_name, homework_data, other_info):
    """宿題を一括で追加・更新・削除する"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            delete_query = "DELETE FROM homework WHERE student_id = %s AND "
            delete_params = [student_id]
            if textbook_id:
                delete_query += "master_textbook_id = %s"
                delete_params.append(textbook_id)
            elif custom_textbook_name:
                delete_query += "custom_textbook_name = %s"
                delete_params.append(custom_textbook_name)
            else:
                raise ValueError("参考書IDまたはカスタム参考書名のどちらかが必要です。")
                
            cur.execute(delete_query, tuple(delete_params))

            tasks_to_add = []
            for hw in homework_data:
                if hw['task']:
                    tasks_to_add.append(
                        (student_id, textbook_id, custom_textbook_name, subject, hw['task'], hw['date'], other_info)
                    )

            if tasks_to_add:
                cur.executemany(
                    """
                    INSERT INTO homework (student_id, master_textbook_id, custom_textbook_name, subject, task, task_date, other_info)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    tasks_to_add
                )
        conn.commit()
        return True, "宿題を保存しました。"
    except (Exception, psycopg2.Error) as e:
        print(f"宿題の保存エラー: {e}")
        conn.rollback()
        return False, f"宿題の保存に失敗しました: {e}"
    finally:
        conn.close()

def get_bulk_presets():
    conn = get_db_connection()
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute("""
            SELECT 
                p.id, p.subject, p.preset_name, pb.book_name
            FROM bulk_presets p
            JOIN bulk_preset_books pb ON p.id = pb.preset_id
            ORDER BY p.subject, p.preset_name
        """)
        presets_raw = cur.fetchall()
    conn.close()
    presets = {}
    for row in presets_raw:
        subject = row['subject']
        preset_name = row['preset_name']
        book_name = row['book_name']
        
        if subject not in presets:
            presets[subject] = {}
        if preset_name not in presets[subject]:
            presets[subject][preset_name] = []
        
        presets[subject][preset_name].append(book_name)
    return presets

def get_all_master_textbooks():
    conn = get_db_connection()
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute('SELECT id, subject, level, book_name, duration FROM master_textbooks ORDER BY subject, level, book_name')
        textbooks = cur.fetchall()
    conn.close()
    return [dict(row) for row in textbooks]

def add_master_textbook(subject, level, book_name, duration):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO master_textbooks (subject, level, book_name, duration) VALUES (%s, %s, %s, %s)",
                (subject, level, book_name, duration)
            )
        conn.commit()
        return True, "参考書が正常に追加されました。"
    except psycopg2.IntegrityError:
        conn.rollback()
        return False, "同じ参考書が既に存在します。"
    finally:
        conn.close()

def update_master_textbook(book_id, subject, level, book_name, duration):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE master_textbooks SET subject = %s, level = %s, book_name = %s, duration = %s WHERE id = %s",
                (subject, level, book_name, duration, book_id)
            )
        conn.commit()
        return True, "参考書が正常に更新されました。"
    except psycopg2.IntegrityError:
        conn.rollback()
        return False, "更新後の参考書名が他のものと重複しています。"
    finally:
        conn.close()

def delete_master_textbook(book_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM master_textbooks WHERE id = %s", (book_id,))
        conn.commit()
        return True, "参考書が正常に削除されました。閉じるボタンを押してください。"
    except psycopg2.Error as e:
        conn.rollback()
        return False, f"削除中にエラーが発生しました: {e}"
    finally:
        conn.close()

def get_all_students_with_details():
    conn = get_db_connection()
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute('SELECT * FROM students ORDER BY school, name')
        students_raw = cur.fetchall()
        
        cur.execute('''
            SELECT si.student_id, u.username, si.is_main
            FROM student_instructors si
            JOIN users u ON si.user_id = u.id
        ''')
        instructors_raw = cur.fetchall()
    
    conn.close()

    students = [dict(s) for s in students_raw]
    for student in students:
        student['main_instructors'] = [i['username'] for i in instructors_raw if i['student_id'] == student['id'] and i['is_main'] == 1]
        student['sub_instructors'] = [i['username'] for i in instructors_raw if i['student_id'] == student['id'] and i['is_main'] == 0]

    return students

def add_student(name, school, deviation_value, main_instructor_id, sub_instructor_ids):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO students (name, school, deviation_value) VALUES (%s, %s, %s) RETURNING id",
                (name, school, deviation_value)
            )
            student_id = cur.fetchone()[0]
            
            if main_instructor_id:
                cur.execute(
                    "INSERT INTO student_instructors (student_id, user_id, is_main) VALUES (%s, %s, 1)",
                    (student_id, main_instructor_id)
                )
            if sub_instructor_ids:
                cur.executemany(
                    "INSERT INTO student_instructors (student_id, user_id, is_main) VALUES (%s, %s, 0)",
                    [(student_id, sub_id) for sub_id in sub_instructor_ids]
                )
        conn.commit()
        return True, "生徒が正常に追加されました。"
    except psycopg2.IntegrityError:
        conn.rollback()
        return False, "同じ校舎に同名の生徒が既に存在します。"
    finally:
        conn.close()

def update_student(student_id, name, deviation_value, main_instructor_id, sub_instructor_ids):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE students SET name = %s, deviation_value = %s WHERE id = %s",
                (name, deviation_value, student_id)
            )
            
            cur.execute("DELETE FROM student_instructors WHERE student_id = %s", (student_id,))
            
            if main_instructor_id:
                cur.execute(
                    "INSERT INTO student_instructors (student_id, user_id, is_main) VALUES (%s, %s, 1)",
                    (student_id, main_instructor_id)
                )
            if sub_instructor_ids:
                cur.executemany(
                    "INSERT INTO student_instructors (student_id, user_id, is_main) VALUES (%s, %s, 0)",
                    [(student_id, sub_id) for sub_id in sub_instructor_ids]
                )
        conn.commit()
        return True, "生徒情報が正常に更新されました。"
    except psycopg2.IntegrityError:
        conn.rollback()
        return False, "更新後の生徒名が、校舎内で他の生徒と重複しています。"
    finally:
        conn.close()

def delete_student(student_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM homework WHERE student_id = %s", (student_id,))
            cur.execute("DELETE FROM progress WHERE student_id = %s", (student_id,))
            cur.execute("DELETE FROM student_instructors WHERE student_id = %s", (student_id,))
            cur.execute("DELETE FROM students WHERE id = %s", (student_id,))
        conn.commit()
        return True, "生徒および関連データが正常に削除されました。"
    except psycopg2.Error as e:
        conn.rollback()
        return False, f"削除中にエラーが発生しました: {e}"
    finally:
        conn.close()

def get_all_instructors_for_school(school, role=None):
    """指定された校舎の講師（ユーザー）を取得する。roleで絞り込みも可能。"""
    conn = get_db_connection()
    with conn.cursor(cursor_factory=DictCursor) as cur:
        query = "SELECT id, username FROM users WHERE school = %s"
        params = [school]
        if role:
            query += " AND role = %s"
            params.append(role)
        query += " ORDER BY username"
        cur.execute(query, tuple(params))
        instructors = cur.fetchall()
    conn.close()
    return [dict(row) for row in instructors]

def get_all_presets_with_books():
    """すべてのプリセットを、関連する参考書リストと共に取得する"""
    conn = get_db_connection()
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute("SELECT id, subject, preset_name FROM bulk_presets ORDER BY subject, preset_name")
        presets = cur.fetchall()
        cur.execute("SELECT preset_id, book_name FROM bulk_preset_books")
        books = cur.fetchall()
    conn.close()

    presets_dict = {p['id']: dict(p, books=[]) for p in presets}
    for book in books:
        if book['preset_id'] in presets_dict:
            presets_dict[book['preset_id']]['books'].append(book['book_name'])
    
    return list(presets_dict.values())

def add_preset(subject, preset_name, book_ids):
    """新しいプリセットを追加する"""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(
                "INSERT INTO bulk_presets (subject, preset_name) VALUES (%s, %s) RETURNING id",
                (subject, preset_name)
            )
            preset_id = cur.fetchone()[0]
            if book_ids:
                placeholders = ','.join(['%s'] * len(book_ids))
                cur.execute(f"SELECT book_name FROM master_textbooks WHERE id IN ({placeholders})", book_ids)
                book_names_rows = cur.fetchall()
                book_names = [row['book_name'] for row in book_names_rows]
                
                cur.executemany(
                    "INSERT INTO bulk_preset_books (preset_id, book_name) VALUES (%s, %s)",
                    [(preset_id, book) for book in book_names]
                )
        conn.commit()
        return True, "プリセットが追加されました。"
    except psycopg2.IntegrityError:
        conn.rollback()
        return False, "同じ科目・プリセット名の組み合わせが既に存在します。"
    finally:
        conn.close()


def update_preset(preset_id, subject, preset_name, book_ids):
    """既存のプリセットを更新する"""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(
                "UPDATE bulk_presets SET subject = %s, preset_name = %s WHERE id = %s",
                (subject, preset_name, preset_id)
            )
            cur.execute("DELETE FROM bulk_preset_books WHERE preset_id = %s", (preset_id,))
            if book_ids:
                placeholders = ','.join(['%s'] * len(book_ids))
                cur.execute(f"SELECT book_name FROM master_textbooks WHERE id IN ({placeholders})", book_ids)
                book_names_rows = cur.fetchall()
                book_names = [row['book_name'] for row in book_names_rows]

                cur.executemany(
                    "INSERT INTO bulk_preset_books (preset_id, book_name) VALUES (%s, %s)",
                    [(preset_id, book) for book in book_names]
                )
        conn.commit()
        return True, "プリセットが更新されました。"
    except psycopg2.IntegrityError:
        conn.rollback()
        return False, "更新後のプリセット名が、同じ科目内で重複しています。"
    finally:
        conn.close()

def delete_preset(preset_id):
    """プリセットを削除する"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM bulk_preset_books WHERE preset_id = %s", (preset_id,))
            cur.execute("DELETE FROM bulk_presets WHERE id = %s", (preset_id,))
        conn.commit()
        return True, "プリセットが削除されました。"
    except psycopg2.Error as e:
        conn.rollback()
        return False, f"削除中にエラーが発生しました: {e}"
    finally:
        conn.close()

def delete_homework_group(student_id, textbook_id, custom_textbook_name):
    """特定の参考書グループに紐づく宿題をすべて削除する"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            query = "DELETE FROM homework WHERE student_id = %s AND "
            params = [student_id]

            if textbook_id is not None and textbook_id != -1:
                query += "master_textbook_id = %s"
                params.append(textbook_id)
            elif custom_textbook_name:
                query += "custom_textbook_name = %s"
                params.append(custom_textbook_name)
            else:
                return False, "削除対象の参考書が特定できませんでした。"

            cur.execute(query, tuple(params))
            rowcount = cur.rowcount
        conn.commit()

        if rowcount > 0:
            return True, "宿題が正常に削除されました。"
        else:
            return True, "削除対象の宿題はありませんでした。"

    except psycopg2.Error as e:
        print(f"宿題の削除エラー: {e}")
        conn.rollback()
        return False, f"宿題の削除中にエラーが発生しました: {e}"
    finally:
        conn.close()

def get_total_past_exam_time(student_id):
    """特定の生徒の過去問の合計実施時間を取得する"""
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT SUM(time_required) FROM past_exam_results WHERE student_id = %s AND time_required IS NOT NULL",
            (student_id,)
        )
        total_time_row = cur.fetchone()
    conn.close()
    
    return (total_time_row[0] / 60) if total_time_row and total_time_row[0] is not None else 0
    
def get_past_exam_results_for_student(student_id):
    """特定の生徒の過去問結果をすべて取得する"""
    conn = get_db_connection()
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute(
            """
            SELECT
                id, date, university_name, faculty_name, exam_system,
                year, subject, time_required, total_time_allowed, 
                correct_answers, total_questions
            FROM past_exam_results
            WHERE student_id = %s
            ORDER BY date DESC, university_name, subject
            """,
            (student_id,)
        )
        results = cur.fetchall()
    conn.close()
    return [dict(row) for row in results]

def add_past_exam_result(student_id, result_data):
    """新しい過去問結果をデータベースに追加する"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO past_exam_results (
                    student_id, date, university_name, faculty_name, exam_system,
                    year, subject, time_required, total_time_allowed, 
                    correct_answers, total_questions
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    student_id,
                    result_data['date'],
                    result_data['university_name'],
                    result_data.get('faculty_name'),
                    result_data.get('exam_system'),
                    result_data['year'],
                    result_data['subject'],
                    result_data.get('time_required'),
                    result_data.get('total_time_allowed'),
                    result_data.get('correct_answers'),
                    result_data.get('total_questions')
                )
            )
        conn.commit()
        return True, "過去問の結果を登録しました。"
    except psycopg2.Error as e:
        conn.rollback()
        return False, f"登録中にエラーが発生しました: {e}"
    finally:
        conn.close()
    
def update_past_exam_result(result_id, result_data):
    """既存の過去問結果を更新する"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE past_exam_results SET
                    date = %s, university_name = %s, faculty_name = %s, exam_system = %s,
                    year = %s, subject = %s, time_required = %s, total_time_allowed = %s, 
                    correct_answers = %s, total_questions = %s
                WHERE id = %s
                """,
                (
                    result_data['date'],
                    result_data['university_name'],
                    result_data.get('faculty_name'),
                    result_data.get('exam_system'),
                    result_data['year'],
                    result_data['subject'],
                    result_data.get('time_required'),
                    result_data.get('total_time_allowed'),
                    result_data.get('correct_answers'),
                    result_data.get('total_questions'),
                    result_id
                )
            )
        conn.commit()
        return True, "過去問の結果を更新しました。"
    except psycopg2.Error as e:
        conn.rollback()
        return False, f"更新中にエラーが発生しました: {e}"
    finally:
        conn.close()

def delete_past_exam_result(result_id):
    """指定されたIDの過去問結果を削除する"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM past_exam_results WHERE id = %s", (result_id,))
        conn.commit()
        return True, "過去問の結果を削除しました。"
    except psycopg2.Error as e:
        conn.rollback()
        return False, f"削除中にエラーが発生しました: {e}"
    finally:
        conn.close()

def get_student_count_by_school():
    """校舎ごとの生徒数を取得する"""
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT school, COUNT(id) as count FROM students GROUP BY school", conn)
    conn.close()
    return df.to_dict('records')

def get_textbook_count_by_subject():
    """科目ごとの参考書数を取得する"""
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT subject, COUNT(id) as count FROM master_textbooks GROUP BY subject", conn)
    conn.close()
    return df.to_dict('records')

def get_students_for_instructor(user_id):
    """担当講師のIDに紐づく生徒のリストを取得する"""
    if not user_id:
        return []
    conn = get_db_connection()
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute('''
            SELECT s.name, s.school
            FROM students s
            JOIN student_instructors si ON s.id = si.student_id
            WHERE si.user_id = %s
            ORDER BY s.school, s.name
        ''', (user_id,))
        students = cur.fetchall()
    conn.close()
    return [f"{dict(s)['school']} - {dict(s)['name']}" for s in students]

def add_bug_report(reporter_username, title, description):
    """新しい不具合報告をデータベースに追加する"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO bug_reports (reporter_username, report_date, title, description)
                VALUES (%s, %s, %s, %s)
                """,
                (reporter_username, datetime.now().strftime("%Y-%m-%d %H:%M"), title, description)
            )
        conn.commit()
        return True, "不具合報告が送信されました。"
    except psycopg2.Error as e:
        conn.rollback()
        return False, f"報告中にエラーが発生しました: {e}"
    finally:
        conn.close()

def get_all_bug_reports():
    """すべての不具合報告を取得する"""
    conn = get_db_connection()
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute("SELECT * FROM bug_reports ORDER BY report_date DESC")
        reports = cur.fetchall()
    conn.close()
    return [dict(row) for row in reports]

def update_bug_status(bug_id, status):
    """不具合報告のステータスを更新する"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE bug_reports SET status = %s WHERE id = %s",
                (status, bug_id)
            )
        conn.commit()
        return True, "ステータスが更新されました。"
    except psycopg2.Error as e:
        conn.rollback()
        return False, f"ステータス更新中にエラーが発生しました: {e}"
    finally:
        conn.close()

def resolve_bug(bug_id, resolution_message):
    """不具合報告を対応済みにし、対応メッセージを保存する"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE bug_reports SET status = '対応済', resolution_message = %s WHERE id = %s",
                (resolution_message, bug_id)
            )
        conn.commit()
        return True, "不具合が対応済みに更新されました。"
    except psycopg2.Error as e:
        conn.rollback()
        return False, f"更新中にエラーが発生しました: {e}"
    finally:
        conn.close()

def get_all_changelog_entries():
    """すべての更新履歴を取得する"""
    conn = get_db_connection()
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute("SELECT * FROM changelog ORDER BY release_date DESC")
        entries = cur.fetchall()
    conn.close()
    return [dict(row) for row in entries]

def add_changelog_entry(version, title, description):
    """新しい更新履歴をデータベースに追加する"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO changelog (version, release_date, title, description)
                VALUES (%s, %s, %s, %s)
                """,
                (version, datetime.now().strftime("%Y-%m-%d"), title, description)
            )
        conn.commit()
        return True, "更新履歴が追加されました。"
    except psycopg2.Error as e:
        conn.rollback()
        return False, f"登録中にエラーが発生しました: {e}"
    finally:
        conn.close()