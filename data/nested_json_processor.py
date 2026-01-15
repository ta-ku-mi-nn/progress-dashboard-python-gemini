# data/nested_json_processor.py

import psycopg2
from psycopg2.extras import DictCursor, execute_values
import os
import json
import uuid
import pandas as pd
from datetime import datetime, timedelta, date # date をインポート
from config.settings import APP_CONFIG
import psycopg2
from psycopg2.extras import DictCursor, execute_values

DATABASE_URL = APP_CONFIG['data']['database_url']

def get_db_connection():
    """PostgreSQLデータベース接続を取得します。"""
    conn = psycopg2.connect(DATABASE_URL)
    return conn

# --- (既存の関数は省略) ---

def get_all_schools():
    """データベースからすべての校舎名を取得する"""
    conn = get_db_connection()
    schools = []
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            # usersテーブルとstudentsテーブルの両方から校舎名を取得し、重複を除外
            cur.execute('''
                SELECT DISTINCT school FROM users WHERE school IS NOT NULL
                UNION
                SELECT DISTINCT school FROM students WHERE school IS NOT NULL
                ORDER BY school
            ''')
            schools = cur.fetchall()
    except psycopg2.Error as e:
        print(f"データベースエラー (get_all_schools): {e}")
    finally:
        if conn:
            conn.close()
    return [school['school'] for school in schools]

def get_all_grades():
    """データベースからすべての学年を取得する"""
    conn = get_db_connection()
    grades = []
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute('SELECT DISTINCT grade FROM students WHERE grade IS NOT NULL ORDER BY grade')
            grades = cur.fetchall()
    except psycopg2.Error as e:
        print(f"データベースエラー (get_all_grades): {e}")
    finally:
        if conn:
            conn.close()
    # 必要に応じて学年の順序をソートするロジックを追加
    # 例: ['中1', '中2', '中3', '高1', '高2', '高3', '既卒']
    grade_order = ['中1', '中2', '中3', '高1', '高2', '高3', '既卒']
    raw_grades = [g['grade'] for g in grades]
    sorted_grades = sorted(
        raw_grades,
        key=lambda x: grade_order.index(x) if x in grade_order else len(grade_order)
    )
    return sorted_grades

def get_students_for_user(user_info):
    """
    ユーザー情報に基づいて表示すべき生徒のリストを取得する。
    - 管理者（メイン講師）: 所属校舎の全生徒
    - 一般ユーザー（サブ講師）: 自身が担当する生徒のみ
    """
    if not user_info:
        return []

    conn = get_db_connection()
    students_cursor = []

    with conn.cursor(cursor_factory=DictCursor) as cur:
        if user_info.get('role') == 'admin':
            user_school = user_info.get('school')
            if user_school:
                cur.execute(
                    'SELECT id, name, school FROM students WHERE school = %s ORDER BY name',
                    (user_school,)
                )
                students_cursor = cur.fetchall()
        else:  # 'user' role
            user_id = user_info.get('id')
            if user_id:
                cur.execute('''
                    SELECT s.id, s.name, s.school
                    FROM students s
                    JOIN student_instructors si ON s.id = si.student_id
                    WHERE si.user_id = %s
                    ORDER BY s.name
                ''', (user_id,))
                students_cursor = cur.fetchall()
    conn.close()

    return [dict(row) for row in students_cursor]


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
    """生徒IDに基づいて生徒情報（追加項目含む）を取得する"""
    conn = get_db_connection()
    student = None
    instructors = []
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            # ★ 取得するカラムに target_level, grade, previous_school を追加
            cur.execute('SELECT id, name, school, deviation_value, target_level, grade, previous_school FROM students WHERE id = %s', (student_id,))
            student = cur.fetchone()
            if not student:
                return {}

            cur.execute('''
                SELECT u.username, si.is_main
                FROM student_instructors si
                JOIN users u ON si.user_id = u.id
                WHERE si.student_id = %s
            ''', (student_id,))
            instructors = cur.fetchall()
    except psycopg2.Error as e:
         print(f"データベースエラー (get_student_info_by_id): {e}")
         return {}
    finally:
        if conn:
            conn.close()

    student_info = dict(student)
    student_info['main_instructors'] = [i['username'] for i in instructors if i['is_main'] == 1]
    student_info['sub_instructors'] = [i['username'] for i in instructors if i['is_main'] == 0]

    return student_info

def get_student_progress_by_id(student_id):
    """生徒IDに基づいて生徒の進捗データを取得し、偏差値に応じて所要時間を調整する"""
    student_info = get_student_info_by_id(student_id)
    student_deviation = student_info.get('deviation_value')

    level_deviation_map = {
        '基礎徹底': 50,
        '日大': 60,
        'MARCH': 70,
        '早慶': 75
    }

    conn = get_db_connection()
    progress_records = [] # progress_records を空リストで初期化
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            # DBから取得するdurationは元の値 (COALESCEで取得)
            cur.execute(
                """
                SELECT
                    p.subject, p.level, p.book_name,
                    COALESCE(p.duration, m.duration, 0) as base_duration, -- 元のdurationをbase_durationとして取得
                    p.is_planned, p.is_done,
                    COALESCE(p.completed_units, 0) as completed_units,
                    COALESCE(p.total_units, 1) as total_units
                FROM progress p
                LEFT JOIN master_textbooks m ON p.book_name = m.book_name AND p.subject = m.subject AND p.level = m.level
                WHERE p.student_id = %s
                """, (student_id,)
            )
            progress_records = cur.fetchall()
    except psycopg2.Error as e:
         print(f"データベースエラー (get_student_progress_by_id): {e}")
         return {} # エラー時は空の辞書を返す
    finally:
        if conn:
            conn.close()

    progress_data = {}
    for row in progress_records:
        subject, level, book_name = row['subject'], row['level'], row['book_name']
        base_duration = row['base_duration'] # 元の所要時間

        adjusted_duration = base_duration # デフォルトは元の値
        if student_deviation is not None and level in level_deviation_map:
            level_deviation = level_deviation_map[level]
            # 計算式を適用
            factor = ((level_deviation - student_deviation) * 0.025 + 1)
            adjusted_duration = factor * base_duration
            # 結果が負にならないように調整
            adjusted_duration = max(0, adjusted_duration)

        if subject not in progress_data:
            progress_data[subject] = {}
        if level not in progress_data[subject]:
            progress_data[subject][level] = {}

        progress_data[subject][level][book_name] = {
            '所要時間': adjusted_duration, # 計算後の値を入れる
            '予定': bool(row['is_planned']),
            '達成済': bool(row['is_done']),
            'completed_units': row['completed_units'],
            'total_units': row['total_units']
        }
    return progress_data

def get_student_info(school, student_name):
    conn = get_db_connection()
    student = None # student を None で初期化
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute('SELECT id FROM students WHERE name = %s AND school = %s', (student_name, school))
            student = cur.fetchone()
    except psycopg2.Error as e:
         print(f"データベースエラー (get_student_info): {e}")
         return {} # エラー時は空の辞書を返す
    finally:
        if conn:
            conn.close()

    if not student:
        return {}
    return get_student_info_by_id(student['id'])

def get_assigned_students_for_user(user_id):
    """指定されたユーザーIDに紐づく生徒のリスト（idとname）を取得する"""
    if not user_id:
        return []
    conn = get_db_connection()
    students = [] # students を空リストで初期化
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute('''
                SELECT s.id, s.name
                FROM students s
                JOIN student_instructors si ON s.id = si.student_id
                WHERE si.user_id = %s
                ORDER BY s.name
            ''', (user_id,))
            students = cur.fetchall()
    except psycopg2.Error as e:
         print(f"データベースエラー (get_assigned_students_for_user): {e}")
         return [] # エラー時は空リストを返す
    finally:
        if conn:
            conn.close()
    return [dict(row) for row in students]

def get_master_textbook_list(subject, search_term=""):
    conn = get_db_connection()
    records = [] # records を空リストで初期化
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            query = "SELECT level, book_name FROM master_textbooks WHERE subject = %s"
            params = [subject]
            if search_term:
                query += " AND book_name LIKE %s"
                params.append(f"%{search_term}%")
            cur.execute(query, tuple(params))
            records = cur.fetchall()
    except psycopg2.Error as e:
         print(f"データベースエラー (get_master_textbook_list): {e}")
         return {} # エラー時は空辞書を返す
    finally:
        if conn:
            conn.close()

    level_order = ['基礎徹底', '日大', 'MARCH', '早慶']
    textbooks_by_level = {}
    for row in records:
        level, book_name = row['level'], row['book_name']
        if level not in textbooks_by_level:
            textbooks_by_level[level] = []
        textbooks_by_level[level].append(book_name)
    # 存在しないレベルを除外してソート
    sorted_textbooks = {level: textbooks_by_level[level] for level in level_order if level in textbooks_by_level}
    # 順序リストに含まれないレベルを追加
    for level in textbooks_by_level:
        if level not in sorted_textbooks:
            sorted_textbooks[level] = textbooks_by_level[level]
    return sorted_textbooks

def add_or_update_student_progress(student_id, progress_updates):
    """
    生徒の進捗情報を一括で更新または追加（UPSERT）する。
    PostgreSQLのON CONFLICT句を使用。
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # UPSERT用のデータリストを作成
            data_to_upsert = []
            for update in progress_updates:
                # 'is_done'が明示的に指定されているかをチェック
                if 'is_done' in update:
                    is_done = update['is_done']
                else:
                    # 指定されていない場合は、従来通り計算
                    is_done = update.get('completed_units', 0) >= update.get('total_units', 1)

                # is_plannedがFalseの場合、進捗をリセット
                if not update.get('is_planned', True):
                    update['completed_units'] = 0
                    update['total_units'] = 1
                    is_done = False # 予定外になったら未達成に戻す

                data_to_upsert.append((
                    student_id,
                    update['subject'],
                    update['level'],
                    update['book_name'],
                    update.get('duration'),
                    bool(update.get('is_planned', True)),
                    is_done,
                    update.get('completed_units', 0),
                    max(1, update.get('total_units', 1)) # total_unitsが0以下にならないように
                ))

            # INSERT ... ON CONFLICT を使ったUPSERTクエリ
            upsert_query = """
                INSERT INTO progress (
                    student_id, subject, level, book_name, duration,
                    is_planned, is_done, completed_units, total_units
                ) VALUES %s
                ON CONFLICT (student_id, subject, level, book_name) DO UPDATE SET
                    duration = COALESCE(EXCLUDED.duration, progress.duration), -- duration が None で渡された場合は既存の値を維持
                    is_planned = EXCLUDED.is_planned,
                    is_done = EXCLUDED.is_done,
                    completed_units = EXCLUDED.completed_units,
                    total_units = EXCLUDED.total_units;
            """

            if data_to_upsert:
                execute_values(cur, upsert_query, data_to_upsert)

        conn.commit()
        return True, f"{len(progress_updates)}件の進捗を更新しました。"
    except (Exception, psycopg2.Error) as e:
        print(f"進捗の一括更新エラー: {e}")
        conn.rollback()
        return False, "進捗の更新に失敗しました。"
    finally:
        if conn:
            conn.close()

def get_all_subjects():
    """データベースからすべての科目を指定された順序で取得する"""
    conn = get_db_connection()
    subjects_raw = [] # 初期化
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute('SELECT DISTINCT subject FROM master_textbooks')
            subjects_raw = cur.fetchall()
    except psycopg2.Error as e:
        print(f"データベースエラー (get_all_subjects): {e}")
    finally:
        if conn:
            conn.close()

    all_subjects = [s['subject'] for s in subjects_raw]

    subject_order = [
        '英語', '国語', '数学', '日本史', '世界史', '政治経済', '物理', '化学', '生物'
    ]

    # subject_orderに含まれる科目を先に、それ以外を後にソート
    sorted_subjects = sorted(
        all_subjects,
        key=lambda s: (subject_order.index(s) if s in subject_order else len(subject_order), s)
    )

    return sorted_subjects

def get_subjects_for_student(student_id):
    """生徒の学習予定がある科目のみを取得する"""
    conn = get_db_connection()
    subjects_raw = [] # 初期化
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(
                'SELECT DISTINCT subject FROM progress WHERE student_id = %s AND is_planned = true',
                (student_id,)
            )
            subjects_raw = cur.fetchall()
    except psycopg2.Error as e:
        print(f"データベースエラー (get_subjects_for_student): {e}")
    finally:
        if conn:
            conn.close()

    student_subjects = [s['subject'] for s in subjects_raw]

    subject_order = [
        '英語', '国語', '数学', '日本史', '世界史', '政治経済', '物理', '化学', '生物'
    ]

    # subject_orderに含まれる科目を先に、それ以外を後にソート
    sorted_subjects = sorted(
        student_subjects,
        key=lambda s: (subject_order.index(s) if s in subject_order else len(subject_order), s)
    )
    return sorted_subjects

def get_all_homework_for_student(student_id):
    """特定の生徒の宿題をすべて取得する (参考書名も結合)"""
    conn = get_db_connection()
    homework_list = [] # 初期化
    try:
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
                    hw.subject, -- hw.subject を COALESCE の外に出す
                    hw.other_info -- other_info を追加
                FROM homework hw
                LEFT JOIN master_textbooks mt ON hw.master_textbook_id = mt.id
                WHERE hw.student_id = %s
                ORDER BY hw.subject, textbook_name, hw.task_date -- hw.subject でソート
                """,
                (student_id,)
            )
            homework_list = cur.fetchall()
    except psycopg2.Error as e:
         print(f"データベースエラー (get_all_homework_for_student): {e}")
    finally:
        if conn:
            conn.close()
    return [dict(row) for row in homework_list]


def get_homework_for_textbook(student_id, textbook_id, custom_textbook_name=None):
    """特定の生徒・参考書(またはカスタム名)の宿題を取得する"""
    conn = get_db_connection()
    homework_list = [] # 初期化
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            query = """
                SELECT id, task, task_date, status, other_info
                FROM homework
                WHERE student_id = %s AND
            """
            params = [student_id]

            if textbook_id is not None and textbook_id != -1: # None チェックを追加
                query += "master_textbook_id = %s"
                params.append(textbook_id)
            elif custom_textbook_name:
                query += "custom_textbook_name = %s"
                params.append(custom_textbook_name)
            else:
                return [] # textbook_id も custom_name もない場合は空リスト

            query += " ORDER BY task_date"

            cur.execute(query, tuple(params))
            homework_list = cur.fetchall()
    except psycopg2.Error as e:
         print(f"データベースエラー (get_homework_for_textbook): {e}")
    finally:
        if conn:
            conn.close()
    return [dict(row) for row in homework_list]


def add_or_update_homework(student_id, subject, textbook_id, custom_textbook_name, homework_data, other_info):
    """宿題を一括で追加・更新・削除する"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # --- 既存の宿題を削除 ---
            delete_query = "DELETE FROM homework WHERE student_id = %s AND "
            delete_params = [student_id]
            # textbook_id が None または -1 の場合 custom_textbook_name を使う
            if textbook_id is not None and textbook_id != -1:
                delete_query += "master_textbook_id = %s"
                delete_params.append(textbook_id)
            elif custom_textbook_name:
                # カスタム名が空文字列でないことを確認
                if custom_textbook_name.strip():
                     delete_query += "custom_textbook_name = %s"
                     delete_params.append(custom_textbook_name)
                else:
                    # 両方指定がない場合はエラー（または特定の処理）
                     raise ValueError("参考書IDまたはカスタム参考書名が必要です。")
            else:
                 raise ValueError("参考書IDまたはカスタム参考書名が必要です。")

            cur.execute(delete_query, tuple(delete_params))

            # --- 新しい宿題を追加 ---
            tasks_to_add = []
            # task_group_id を生成 (UUIDを使用)
            task_group_id = str(uuid.uuid4())
            for hw in homework_data:
                # task が空文字列やNoneでない場合のみ追加
                if hw.get('task') and str(hw.get('task')).strip():
                    tasks_to_add.append(
                        (student_id,
                         textbook_id if textbook_id != -1 else None, # -1はNoneとして扱う
                         custom_textbook_name if custom_textbook_name and custom_textbook_name.strip() else None, # 空文字列はNone
                         subject,
                         hw['task'],
                         hw['date'],
                         task_group_id, # task_group_id を追加
                         other_info)
                    )

            if tasks_to_add:
                # executemany を使って一括挿入
                execute_values(
                    cur,
                    """
                    INSERT INTO homework (student_id, master_textbook_id, custom_textbook_name, subject, task, task_date, task_group_id, other_info)
                    VALUES %s
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
        if conn:
            conn.close()

def get_bulk_presets():
    conn = get_db_connection()
    presets_raw = [] # 初期化
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("""
                SELECT
                    p.id, p.subject, p.preset_name, pb.book_name
                FROM bulk_presets p
                JOIN bulk_preset_books pb ON p.id = pb.preset_id
                ORDER BY p.subject, p.preset_name, pb.id -- 書籍の順序も安定させるために pb.id を追加
            """)
            presets_raw = cur.fetchall()
    except psycopg2.Error as e:
        print(f"データベースエラー (get_bulk_presets): {e}")
    finally:
        if conn:
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
    textbooks = [] # 初期化
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute('SELECT id, subject, level, book_name, duration FROM master_textbooks ORDER BY subject, level, book_name')
            textbooks = cur.fetchall()
    except psycopg2.Error as e:
         print(f"データベースエラー (get_all_master_textbooks): {e}")
    finally:
        if conn:
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
    except psycopg2.IntegrityError: # UNIQUE制約違反
        conn.rollback()
        return False, "同じ参考書が既に存在します。"
    except psycopg2.Error as e: # その他のDBエラー
        conn.rollback()
        print(f"データベースエラー (add_master_textbook): {e}")
        return False, f"追加中にエラーが発生しました: {e}"
    finally:
        if conn:
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
        # 更新された行数をチェック
        if cur.rowcount == 0:
             return False, "指定されたIDの参考書が見つかりません。"
        return True, "参考書が正常に更新されました。"
    except psycopg2.IntegrityError: # UNIQUE制約違反
        conn.rollback()
        return False, "更新後の参考書名が他のものと重複しています。"
    except psycopg2.Error as e: # その他のDBエラー
        conn.rollback()
        print(f"データベースエラー (update_master_textbook): {e}")
        return False, f"更新中にエラーが発生しました: {e}"
    finally:
        if conn:
            conn.close()

def delete_master_textbook(book_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # 関連する homework レコードの master_textbook_id を NULL に設定
            cur.execute("UPDATE homework SET master_textbook_id = NULL WHERE master_textbook_id = %s", (book_id,))
            # master_textbooks から削除
            cur.execute("DELETE FROM master_textbooks WHERE id = %s", (book_id,))
        conn.commit()
        # 削除された行数をチェック
        if cur.rowcount == 0:
            return False, "指定されたIDの参考書が見つかりません。"
        return True, "参考書が正常に削除されました。閉じるボタンを押してください。"
    except psycopg2.Error as e:
        conn.rollback()
        print(f"データベースエラー (delete_master_textbook): {e}")
        return False, f"削除中にエラーが発生しました: {e}"
    finally:
        if conn:
            conn.close()

def get_all_students_with_details():
    """すべての生徒情報を詳細（追加項目含む）付きで取得する"""
    conn = get_db_connection()
    students_raw = []
    instructors_raw = []
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            # ★ 取得するカラムに target_level, grade, previous_school を追加
            cur.execute('SELECT id, name, school, deviation_value, target_level, grade, previous_school FROM students ORDER BY school, name')
            students_raw = cur.fetchall()

            cur.execute('''
                SELECT si.student_id, u.username, si.is_main
                FROM student_instructors si
                JOIN users u ON si.user_id = u.id
            ''')
            instructors_raw = cur.fetchall()
    except psycopg2.Error as e:
         print(f"データベースエラー (get_all_students_with_details): {e}")
    finally:
        if conn:
            conn.close()

    students = [dict(s) for s in students_raw]
    instructors_by_student = {}
    for i in instructors_raw:
        s_id = i['student_id']
        if s_id not in instructors_by_student:
             instructors_by_student[s_id] = {'main': [], 'sub': []}
        if i['is_main'] == 1:
             instructors_by_student[s_id]['main'].append(i['username'])
        else:
             instructors_by_student[s_id]['sub'].append(i['username'])

    for student in students:
        s_id = student['id']
        student['main_instructors'] = instructors_by_student.get(s_id, {}).get('main', [])
        student['sub_instructors'] = instructors_by_student.get(s_id, {}).get('sub', [])

    return students

def add_student(name, school, deviation_value, target_level, grade, previous_school, main_instructor_id, sub_instructor_ids):
    """新しい生徒を追加（追加項目含む）"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            dev_val = int(deviation_value) if deviation_value is not None and str(deviation_value).strip() != '' else None
            # ★ target_level, grade, previous_school を INSERT 文に追加
            cur.execute(
                """
                INSERT INTO students (name, school, deviation_value, target_level, grade, previous_school)
                VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
                """,
                (name, school, dev_val, target_level or None, grade or None, previous_school or None) # 空文字列はNoneとして登録
            )
            student_id = cur.fetchone()[0]

            instructors_to_insert = []
            if main_instructor_id:
                 instructors_to_insert.append((student_id, main_instructor_id, 1))
            if sub_instructor_ids:
                 for sub_id in sub_instructor_ids:
                     instructors_to_insert.append((student_id, sub_id, 0))

            if instructors_to_insert:
                 execute_values(
                     cur,
                     "INSERT INTO student_instructors (student_id, user_id, is_main) VALUES %s",
                     instructors_to_insert
                 )
        conn.commit()
        return True, "生徒が正常に追加されました。"
    except psycopg2.IntegrityError as e: # UNIQUE制約違反など
        conn.rollback()
        if 'students_school_name_key' in str(e):
             return False, "同じ校舎に同名の生徒が既に存在します。"
        else:
             print(f"データベース整合性エラー (add_student): {e}")
             return False, f"追加中にエラーが発生しました: {e}"
    except psycopg2.Error as e: # その他のDBエラー
        conn.rollback()
        print(f"データベースエラー (add_student): {e}")
        return False, f"追加中にエラーが発生しました: {e}"
    finally:
        if conn:
            conn.close()

def update_student(student_id, name, deviation_value, target_level, grade, previous_school, main_instructor_id, sub_instructor_ids):
    """生徒情報を更新（追加項目含む）"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # 生徒情報の更新
            dev_val = int(deviation_value) if deviation_value is not None and str(deviation_value).strip() != '' else None
            # ★ target_level, grade, previous_school を UPDATE 文に追加
            cur.execute(
                """
                UPDATE students SET name = %s, deviation_value = %s, target_level = %s, grade = %s, previous_school = %s
                WHERE id = %s
                """,
                (name, dev_val, target_level or None, grade or None, previous_school or None, student_id)
            )
            # 既存の講師関連を削除
            cur.execute("DELETE FROM student_instructors WHERE student_id = %s", (student_id,))

            # 新しい講師関連を追加
            instructors_to_insert = []
            if main_instructor_id:
                 instructors_to_insert.append((student_id, main_instructor_id, 1))
            if sub_instructor_ids:
                 for sub_id in sub_instructor_ids:
                     instructors_to_insert.append((student_id, sub_id, 0))

            if instructors_to_insert:
                 execute_values(
                     cur,
                     "INSERT INTO student_instructors (student_id, user_id, is_main) VALUES %s",
                     instructors_to_insert
                 )

        conn.commit()
        if cur.rowcount == 0:
             return False, "指定されたIDの生徒が見つかりません。"
        return True, "生徒情報が正常に更新されました。"
    except psycopg2.IntegrityError as e: # UNIQUE制約違反など
        conn.rollback()
        if 'students_school_name_key' in str(e):
            return False, "更新後の生徒名が、校舎内で他の生徒と重複しています。"
        else:
            print(f"データベース整合性エラー (update_student): {e}")
            return False, f"更新中にエラーが発生しました: {e}"
    except psycopg2.Error as e: # その他のDBエラー
        conn.rollback()
        print(f"データベースエラー (update_student): {e}")
        return False, f"更新中にエラーが発生しました: {e}"
    finally:
        if conn:
            conn.close()

def delete_student(student_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # 外部キー制約 (ON DELETE CASCADE) により、関連データも自動削除されるはず
            # 明示的に削除する場合は以下のコメントアウトを外す
            # cur.execute("DELETE FROM homework WHERE student_id = %s", (student_id,))
            # cur.execute("DELETE FROM progress WHERE student_id = %s", (student_id,))
            # cur.execute("DELETE FROM student_instructors WHERE student_id = %s", (student_id,))
            # cur.execute("DELETE FROM past_exam_results WHERE student_id = %s", (student_id,))
            # cur.execute("DELETE FROM university_acceptance WHERE student_id = %s", (student_id,))
            # cur.execute("DELETE FROM mock_exam_results WHERE student_id = %s", (student_id,)) # ★ mock_exam_results も追加

            # students テーブルから削除
            cur.execute("DELETE FROM students WHERE id = %s", (student_id,))
        conn.commit()
        # 削除された行数をチェック
        if cur.rowcount == 0:
            return False, "指定されたIDの生徒が見つかりません。"
        return True, "生徒および関連データが正常に削除されました。"
    except psycopg2.Error as e:
        conn.rollback()
        print(f"データベースエラー (delete_student): {e}")
        return False, f"削除中にエラーが発生しました: {e}"
    finally:
        if conn:
            conn.close()

def get_all_instructors_for_school(school, role=None):
    """指定された校舎の講師（ユーザー）を取得する。roleで絞り込みも可能。"""
    conn = get_db_connection()
    instructors = [] # 初期化
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            query = "SELECT id, username FROM users WHERE school = %s"
            params = [school]
            if role:
                query += " AND role = %s"
                params.append(role)
            query += " ORDER BY username"
            cur.execute(query, tuple(params))
            instructors = cur.fetchall()
    except psycopg2.Error as e:
         print(f"データベースエラー (get_all_instructors_for_school): {e}")
    finally:
        if conn:
            conn.close()
    return [dict(row) for row in instructors]

def get_all_presets_with_books():
    """すべてのプリセットを、関連する参考書リストと共に取得する"""
    conn = get_db_connection()
    presets = [] # 初期化
    books = [] # 初期化
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("SELECT id, subject, preset_name FROM bulk_presets ORDER BY subject, preset_name")
            presets = cur.fetchall()
            cur.execute("SELECT preset_id, book_name FROM bulk_preset_books ORDER BY preset_id, id") # 順序安定のため id も追加
            books = cur.fetchall()
    except psycopg2.Error as e:
         print(f"データベースエラー (get_all_presets_with_books): {e}")
    finally:
        if conn:
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
            # プリセット本体を追加
            cur.execute(
                "INSERT INTO bulk_presets (subject, preset_name) VALUES (%s, %s) RETURNING id",
                (subject, preset_name)
            )
            preset_id = cur.fetchone()[0]

            # 関連書籍を追加
            if book_ids:
                # book_ids から book_names を取得
                placeholders = ','.join(['%s'] * len(book_ids))
                cur.execute(f"SELECT book_name FROM master_textbooks WHERE id IN ({placeholders})", book_ids)
                book_names_rows = cur.fetchall()
                book_names = [row['book_name'] for row in book_names_rows]

                # bulk_preset_books に挿入
                books_to_insert = [(preset_id, book) for book in book_names]
                if books_to_insert:
                     execute_values(
                         cur,
                         "INSERT INTO bulk_preset_books (preset_id, book_name) VALUES %s",
                         books_to_insert
                     )
        conn.commit()
        return True, "プリセットが追加されました。"
    except psycopg2.IntegrityError: # UNIQUE制約違反
        conn.rollback()
        return False, "同じ科目・プリセット名の組み合わせが既に存在します。"
    except psycopg2.Error as e: # その他のDBエラー
        conn.rollback()
        print(f"データベースエラー (add_preset): {e}")
        return False, f"追加中にエラーが発生しました: {e}"
    finally:
        if conn:
            conn.close()


def update_preset(preset_id, subject, preset_name, book_ids):
    """既存のプリセットを更新する"""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            # プリセット本体を更新
            cur.execute(
                "UPDATE bulk_presets SET subject = %s, preset_name = %s WHERE id = %s",
                (subject, preset_name, preset_id)
            )
            # 既存の関連書籍を削除
            cur.execute("DELETE FROM bulk_preset_books WHERE preset_id = %s", (preset_id,))

            # 新しい関連書籍を追加
            if book_ids:
                # book_ids から book_names を取得
                placeholders = ','.join(['%s'] * len(book_ids))
                cur.execute(f"SELECT book_name FROM master_textbooks WHERE id IN ({placeholders})", book_ids)
                book_names_rows = cur.fetchall()
                book_names = [row['book_name'] for row in book_names_rows]

                # bulk_preset_books に挿入
                books_to_insert = [(preset_id, book) for book in book_names]
                if books_to_insert:
                    execute_values(
                        cur,
                        "INSERT INTO bulk_preset_books (preset_id, book_name) VALUES %s",
                        books_to_insert
                    )
        conn.commit()
        # 更新された行数をチェック (bulk_presets テーブルのみ)
        if cur.rowcount == 0:
             return False, "指定されたIDのプリセットが見つかりません。"
        return True, "プリセットが更新されました。"
    except psycopg2.IntegrityError: # UNIQUE制約違反
        conn.rollback()
        return False, "更新後のプリセット名が、同じ科目内で重複しています。"
    except psycopg2.Error as e: # その他のDBエラー
        conn.rollback()
        print(f"データベースエラー (update_preset): {e}")
        return False, f"更新中にエラーが発生しました: {e}"
    finally:
        if conn:
            conn.close()

def delete_preset(preset_id):
    """プリセットを削除する (ON DELETE CASCADEにより関連書籍も削除される)"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # bulk_presets から削除
            cur.execute("DELETE FROM bulk_presets WHERE id = %s", (preset_id,))
        conn.commit()
        # 削除された行数をチェック
        if cur.rowcount == 0:
            return False, "指定されたIDのプリセットが見つかりません。"
        return True, "プリセットが削除されました。"
    except psycopg2.Error as e:
        conn.rollback()
        print(f"データベースエラー (delete_preset): {e}")
        return False, f"削除中にエラーが発生しました: {e}"
    finally:
        if conn:
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
            elif custom_textbook_name and custom_textbook_name.strip(): # 空白でないことを確認
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
        if conn:
            conn.close()

def get_total_past_exam_time(student_id):
    """特定の生徒の過去問の合計実施時間(分)を取得する"""
    conn = get_db_connection()
    total_time_minutes = 0 # 初期化
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT SUM(time_required) FROM past_exam_results WHERE student_id = %s AND time_required IS NOT NULL",
                (student_id,)
            )
            total_time_row = cur.fetchone()
            if total_time_row and total_time_row[0] is not None:
                total_time_minutes = total_time_row[0]
    except psycopg2.Error as e:
         print(f"データベースエラー (get_total_past_exam_time): {e}")
    finally:
        if conn:
            conn.close()

    return total_time_minutes / 60.0 # 時間単位で返す

def get_past_exam_results_for_student(student_id):
    """特定の生徒の過去問結果をすべて取得する"""
    conn = get_db_connection()
    results = [] # 初期化
    try:
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
    except psycopg2.Error as e:
         print(f"データベースエラー (get_past_exam_results_for_student): {e}")
    finally:
        if conn:
            conn.close()
    # 日付文字列をdateオブジェクトに変換（エラー時はNone）
    processed_results = []
    for row_dict in [dict(row) for row in results]:
        try:
            row_dict['date'] = date.fromisoformat(row_dict['date']) if row_dict.get('date') else None
        except (ValueError, TypeError):
            row_dict['date'] = None # 不正な形式の場合はNoneにする
        processed_results.append(row_dict)
    return processed_results

def add_past_exam_result(student_id, result_data):
    """新しい過去問結果をデータベースに追加する"""
    conn = get_db_connection()
    try:
        # 日付を文字列形式に変換
        date_str = result_data['date'].isoformat() if isinstance(result_data.get('date'), date) else result_data.get('date')

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
                    date_str, # 文字列形式の日付
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
        print(f"データベースエラー (add_past_exam_result): {e}")
        return False, f"登録中にエラーが発生しました: {e}"
    finally:
        if conn:
            conn.close()

def update_past_exam_result(result_id, result_data):
    """既存の過去問結果を更新する"""
    conn = get_db_connection()
    try:
        # 日付を文字列形式に変換
        date_str = result_data['date'].isoformat() if isinstance(result_data.get('date'), date) else result_data.get('date')

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
                    date_str, # 文字列形式の日付
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
        if cur.rowcount == 0:
            return False, "指定されたIDの結果が見つかりません。"
        return True, "過去問の結果を更新しました。"
    except psycopg2.Error as e:
        conn.rollback()
        print(f"データベースエラー (update_past_exam_result): {e}")
        return False, f"更新中にエラーが発生しました: {e}"
    finally:
        if conn:
            conn.close()

def delete_past_exam_result(result_id):
    """指定されたIDの過去問結果を削除する"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM past_exam_results WHERE id = %s", (result_id,))
        conn.commit()
        if cur.rowcount == 0:
            return False, "指定されたIDの結果が見つかりません。"
        return True, "過去問の結果を削除しました。"
    except psycopg2.Error as e:
        conn.rollback()
        print(f"データベースエラー (delete_past_exam_result): {e}")
        return False, f"削除中にエラーが発生しました: {e}"
    finally:
        if conn:
            conn.close()

def get_student_count_by_school():
    """校舎ごとの生徒数を取得する"""
    conn = get_db_connection()
    records = [] # 初期化
    try:
        # pandasを使わずに直接SQLで集計
        with conn.cursor(cursor_factory=DictCursor) as cur:
             cur.execute("SELECT school, COUNT(id) as count FROM students GROUP BY school ORDER BY school")
             records = cur.fetchall()
    except psycopg2.Error as e:
         print(f"データベースエラー (get_student_count_by_school): {e}")
    finally:
        if conn:
            conn.close()
    return [dict(row) for row in records]

def get_textbook_count_by_subject():
    """科目ごとの参考書数を取得する"""
    conn = get_db_connection()
    records = [] # 初期化
    try:
         # pandasを使わずに直接SQLで集計
        with conn.cursor(cursor_factory=DictCursor) as cur:
             cur.execute("SELECT subject, COUNT(id) as count FROM master_textbooks GROUP BY subject ORDER BY subject")
             records = cur.fetchall()
    except psycopg2.Error as e:
         print(f"データベースエラー (get_textbook_count_by_subject): {e}")
    finally:
        if conn:
            conn.close()
    return [dict(row) for row in records]

def get_students_for_instructor(user_id):
    """担当講師のIDに紐づく生徒のリストを取得する"""
    if not user_id:
        return []
    conn = get_db_connection()
    students = [] # 初期化
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute('''
                SELECT s.name, s.school
                FROM students s
                JOIN student_instructors si ON s.id = si.student_id
                WHERE si.user_id = %s
                ORDER BY s.school, s.name
            ''', (user_id,))
            students = cur.fetchall()
    except psycopg2.Error as e:
         print(f"データベースエラー (get_students_for_instructor): {e}")
    finally:
        if conn:
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
        print(f"データベースエラー (add_bug_report): {e}")
        return False, f"報告中にエラーが発生しました: {e}"
    finally:
        if conn:
            conn.close()

def get_all_bug_reports():
    """すべての不具合報告を取得する"""
    conn = get_db_connection()
    reports = [] # 初期化
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("SELECT * FROM bug_reports ORDER BY report_date DESC")
            reports = cur.fetchall()
    except psycopg2.Error as e:
         print(f"データベースエラー (get_all_bug_reports): {e}")
    finally:
        if conn:
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
        if cur.rowcount == 0:
             return False, "指定されたIDの報告が見つかりません。"
        return True, "ステータスが更新されました。"
    except psycopg2.Error as e:
        conn.rollback()
        print(f"データベースエラー (update_bug_status): {e}")
        return False, f"ステータス更新中にエラーが発生しました: {e}"
    finally:
        if conn:
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
        if cur.rowcount == 0:
             return False, "指定されたIDの報告が見つかりません。"
        return True, "不具合が対応済みに更新されました。"
    except psycopg2.Error as e:
        conn.rollback()
        print(f"データベースエラー (resolve_bug): {e}")
        return False, f"更新中にエラーが発生しました: {e}"
    finally:
        if conn:
            conn.close()

def get_all_changelog_entries():
    """すべての更新履歴を取得する"""
    conn = get_db_connection()
    entries = [] # 初期化
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            # PostgreSQLでは version 文字列を適切にソートするために工夫が必要
            # 例: バージョン番号を数値配列に変換してソート
            cur.execute("""
                SELECT * FROM changelog
                ORDER BY
                    string_to_array(substring(version from E'^(\\d+\\.?)+'), '.')::int[] DESC,
                    release_date DESC
            """)
            entries = cur.fetchall()
    except psycopg2.Error as e:
         print(f"データベースエラー (get_all_changelog_entries): {e}")
    finally:
        if conn:
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
                (version, date.today().isoformat(), title, description) # date.today()を使用
            )
        conn.commit()
        return True, "更新履歴が追加されました。"
    except psycopg2.Error as e:
        conn.rollback()
        print(f"データベースエラー (add_changelog_entry): {e}")
        return False, f"登録中にエラーが発生しました: {e}"
    finally:
        if conn:
            conn.close()

def get_student_level_statistics(target_school=None, target_grade=None):
    """
    指定された校舎・学年の生徒について、各科目のレベル達成人数を集計する。
    target_school が None の場合は全校舎を集計する。
    """
    conn = get_db_connection()
    progress_data = []
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            # ★ ベースとなるクエリ
            query = """
                SELECT
                    s.id as student_id,
                    p.subject,
                    p.level
                FROM progress p
                JOIN students s ON p.student_id = s.id
                WHERE p.is_done = true AND p.level IN ('日大', 'MARCH', '早慶')
            """
            params = []
            # ★ target_school が指定されている場合のみ WHERE句に追加
            if target_school:
                query += " AND s.school = %s"
                params.append(target_school)
            if target_grade:
                query += " AND s.grade = %s"
                params.append(target_grade)

            cur.execute(query, tuple(params)) # params が空でも tuple() はOK
            progress_data = cur.fetchall()
    except psycopg2.Error as e:
         print(f"データベースエラー (get_student_level_statistics): {e}")
         return {}
    finally:
        if conn:
            conn.close()

    if not progress_data:
        return {}

    progress_list = [dict(row) for row in progress_data]
    df = pd.DataFrame(progress_list)

    required_columns = ['student_id', 'subject', 'level']
    if not all(col in df.columns for col in required_columns):
        return {}

    # ★ 生徒ごと、科目ごと、レベルごとの達成記録にユニーク化
    df_unique_students = df.drop_duplicates(subset=required_columns)

    # 科目とレベルでグループ化し、生徒数をカウント
    level_counts = df_unique_students.groupby(['subject', 'level']).size().reset_index(name='student_count')

    stats = {}
    for _, row in level_counts.iterrows():
        subject = row['subject']
        level = row['level']
        count = row['student_count']

        if subject not in stats:
            stats[subject] = {'日大': 0, 'MARCH': 0, '早慶': 0}

        if level in stats[subject]:
            stats[subject][level] = count

    # 集計結果に含まれない科目を追加し、カウントを0で初期化
    all_subjects = get_all_subjects() # データベースから全科目リストを取得
    for subj in all_subjects:
        if subj not in stats:
            stats[subj] = {'日大': 0, 'MARCH': 0, '早慶': 0}

    return stats

def get_acceptance_results_for_student(student_id):
    """特定の生徒の大学合否結果をすべて取得する"""
    conn = get_db_connection()
    results = [] # 初期化
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(
                """
                SELECT id, university_name, faculty_name, department_name, exam_system, result,
                       application_deadline, exam_date, announcement_date, procedure_deadline
                FROM university_acceptance
                WHERE student_id = %s
                ORDER BY exam_date DESC NULLS LAST, application_deadline DESC NULLS LAST, university_name, faculty_name
                """,
                (student_id,)
            )
            results = cur.fetchall()
    except psycopg2.Error as e:
         print(f"データベースエラー (get_acceptance_results_for_student): {e}")
    finally:
        if conn:
            conn.close()
    # 日付文字列をdateオブジェクトに変換（エラー時はNone）
    processed_results = []
    date_cols = ['application_deadline', 'exam_date', 'announcement_date', 'procedure_deadline']
    for row_dict in [dict(row) for row in results]:
        for col in date_cols:
             try:
                 row_dict[col] = date.fromisoformat(row_dict[col]) if row_dict.get(col) else None
             except (ValueError, TypeError):
                 row_dict[col] = None # 不正な形式の場合はNoneにする
        processed_results.append(row_dict)
    return processed_results

# --- add_acceptance_result ---
def add_acceptance_result(student_id, data):
    """新しい大学合否結果を追加する"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # 日付データを文字列に変換 (Noneもそのまま渡す)
            app_deadline_str = data.get('application_deadline').isoformat() if isinstance(data.get('application_deadline'), date) else data.get('application_deadline')
            exam_date_str = data.get('exam_date').isoformat() if isinstance(data.get('exam_date'), date) else data.get('exam_date')
            announcement_date_str = data.get('announcement_date').isoformat() if isinstance(data.get('announcement_date'), date) else data.get('announcement_date')
            proc_deadline_str = data.get('procedure_deadline').isoformat() if isinstance(data.get('procedure_deadline'), date) else data.get('procedure_deadline')

            cur.execute(
                """
                INSERT INTO university_acceptance (
                    student_id, university_name, faculty_name, department_name, exam_system, result,
                    application_deadline, exam_date, announcement_date, procedure_deadline
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    student_id,
                    data.get('university_name'),
                    data.get('faculty_name'),
                    data.get('department_name'),
                    data.get('exam_system'),
                    data.get('result'),
                    app_deadline_str,
                    exam_date_str,
                    announcement_date_str,
                    proc_deadline_str
                )
            )
        conn.commit()
        return True, "大学合否結果を追加しました。"
    except psycopg2.Error as e:
        conn.rollback()
        print(f"DB Error in add_acceptance_result: {e}")
        print(f"Data passed: student_id={student_id}, data={data}")
        return False, f"追加中にエラーが発生しました: {e}"
    finally:
        if conn:
            conn.close()

def update_acceptance_result(result_id, data):
    """既存の大学合否結果を更新する"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            set_clauses = []
            params = []

            # 更新対象のフィールドを動的に構築
            fields_to_update = [
                'university_name', 'faculty_name', 'department_name', 'exam_system', 'result',
                'application_deadline', 'exam_date', 'announcement_date', 'procedure_deadline'
            ]
            for field in fields_to_update:
                if field in data:
                    value = data[field]
                    # 日付オブジェクトは文字列に変換
                    if isinstance(value, date):
                         value = value.isoformat()
                    # resultが空文字列の場合はNoneに変換
                    elif field == 'result' and value == '':
                         value = None
                    set_clauses.append(f"{field} = %s")
                    params.append(value)

            if not set_clauses:
                return False, "更新するデータがありません。"

            query = f"UPDATE university_acceptance SET {', '.join(set_clauses)} WHERE id = %s"
            params.append(result_id)

            cur.execute(query, tuple(params))
        conn.commit()
        if cur.rowcount == 0:
            return False, "指定されたIDの結果が見つかりません。"
        return True, "大学合否結果を更新しました。"
    except psycopg2.Error as e:
        conn.rollback()
        print(f"DB Error in update_acceptance_result: {e}")
        return False, f"更新中にエラーが発生しました: {e}"
    finally:
        if conn:
            conn.close()

def delete_acceptance_result(result_id):
    """指定されたIDの大学合否結果を削除する"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM university_acceptance WHERE id = %s", (result_id,))
        conn.commit()
        if cur.rowcount == 0:
            return False, "指定されたIDの結果が見つかりません。"
        return True, "大学合否結果を削除しました。"
    except psycopg2.Error as e:
        conn.rollback()
        print(f"DB Error in delete_acceptance_result: {e}")
        return False, f"削除中にエラーが発生しました: {e}"
    finally:
        if conn:
            conn.close()

def add_feature_request(reporter_username, title, description):
    """新しい機能要望をデータベースに追加する"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO feature_requests (reporter_username, report_date, title, description)
                VALUES (%s, %s, %s, %s)
                """,
                (reporter_username, datetime.now().strftime("%Y-%m-%d %H:%M"), title, description)
            )
        conn.commit()
        return True, "要望が送信されました。"
    except psycopg2.Error as e:
        conn.rollback()
        print(f"データベースエラー (add_feature_request): {e}") # エラーログ追加
        return False, f"要望の送信中にエラーが発生しました: {e}"
    finally:
        if conn:
            conn.close()

def get_all_feature_requests():
    """すべての機能要望を取得する"""
    conn = get_db_connection()
    requests = [] # 初期化
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            # report_date で降順ソート
            cur.execute("SELECT * FROM feature_requests ORDER BY report_date DESC")
            requests_cursor = cur.fetchall()
            requests = [dict(row) for row in requests_cursor]
    except psycopg2.Error as e:
        print(f"データベースエラー (get_all_feature_requests): {e}") # エラーログ追加
    finally:
        if conn:
            conn.close()
    return requests

def update_request_status(request_id, status):
    """機能要望のステータスを更新する"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE feature_requests SET status = %s WHERE id = %s",
                (status, request_id)
            )
        conn.commit()
        # 更新された行数をチェック
        if cur.rowcount == 0:
             return False, "指定されたIDの要望が見つかりません。"
        return True, "ステータスが更新されました。"
    except psycopg2.Error as e:
        conn.rollback()
        print(f"データベースエラー (update_request_status): {e}") # エラーログ追加
        return False, f"ステータス更新中にエラーが発生しました: {e}"
    finally:
        if conn:
            conn.close()

def resolve_request(request_id, resolution_message, status='対応済'): # status 引数を追加
    """機能要望を指定されたステータスにし、対応メッセージを保存する"""
    conn = get_db_connection()
    # status が '対応済' または '見送り' であることを確認
    if status not in ['対応済', '見送り']:
        return False, "無効なステータスです。"

    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE feature_requests SET status = %s, resolution_message = %s WHERE id = %s",
                (status, resolution_message, request_id)
            )
        conn.commit()
        # 更新された行数をチェック
        if cur.rowcount == 0:
             return False, "指定されたIDの要望が見つかりません。"
        status_text = "対応済み" if status == "対応済" else "見送り"
        return True, f"要望が {status_text} に更新されました。"
    except psycopg2.Error as e:
        conn.rollback()
        print(f"データベースエラー (resolve_request): {e}") # エラーログ追加
        return False, f"更新中にエラーが発生しました: {e}"
    finally:
        if conn:
            conn.close()

# ★★★ ここから模試結果関連の関数を追加 ★★★

def add_mock_exam_result(student_id, data):
    """新しい模試結果をデータベースに追加する"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # 数値に変換すべきカラムのリスト
            int_columns = [
                'subject_kokugo_desc', 'subject_math_desc', 'subject_english_desc',
                'subject_rika1_desc', 'subject_rika2_desc', 'subject_shakai1_desc', 'subject_shakai2_desc',
                'subject_kokugo_mark', 'subject_math1a_mark', 'subject_math2bc_mark',
                'subject_english_r_mark', 'subject_english_l_mark', 'subject_rika1_mark', 'subject_rika2_mark',
                'subject_shakai1_mark', 'subject_shakai2_mark', 'subject_rika_kiso1_mark',
                'subject_rika_kiso2_mark', 'subject_info_mark'
            ]
            # data辞書内の数値を整数に変換、変換できない場合はNone
            for col in int_columns:
                if col in data and data[col] is not None:
                    try:
                        data[col] = int(data[col])
                    except (ValueError, TypeError):
                        data[col] = None # 数値変換失敗時はNULL

            # exam_date の処理 (YYYY-MM-DD形式を想定)
            exam_date_val = None
            if data.get('exam_date'):
                try:
                    exam_date_val = datetime.strptime(str(data['exam_date']), '%Y-%m-%d').date()
                except (ValueError, TypeError):
                    exam_date_val = None # 不正な形式ならNone

            # SQLクエリの構築
            columns = [
                'student_id', 'result_type', 'mock_exam_name', 'mock_exam_format',
                'grade', 'round', 'exam_date'
            ] + int_columns
            values_placeholder = ', '.join(['%s'] * len(columns))
            sql = f"INSERT INTO mock_exam_results ({', '.join(columns)}) VALUES ({values_placeholder})"

            # パラメータリストの作成
            params = [
                student_id,
                data.get('result_type'),
                data.get('mock_exam_name'),
                data.get('mock_exam_format'),
                data.get('grade'),
                data.get('round'),
                exam_date_val
            ] + [data.get(col) for col in int_columns] # .get()で安全にアクセス

            cur.execute(sql, tuple(params))

        conn.commit()
        return True, "模試結果を登録しました。"
    except psycopg2.Error as e:
        conn.rollback()
        print(f"データベースエラー (add_mock_exam_result): {e}")
        print(f"Data received: {data}") # 受け取ったデータをログ出力
        return False, f"模試結果の登録中にエラーが発生しました: {e}"
    finally:
        if conn:
            conn.close()


def get_mock_exam_results_for_student(student_id):
    """特定の生徒の模試結果をすべて取得する"""
    conn = get_db_connection()
    results = []
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(
                """
                SELECT *
                FROM mock_exam_results
                WHERE student_id = %s
                ORDER BY exam_date DESC NULLS LAST, id DESC -- 受験日の降順、なければ登録順の降順
                """,
                (student_id,)
            )
            results = cur.fetchall()
    except psycopg2.Error as e:
         print(f"データベースエラー (get_mock_exam_results_for_student): {e}")
    finally:
        if conn:
            conn.close()
    return [dict(row) for row in results]


def update_mock_exam_result(result_id, data):
    """既存の模試結果を更新する"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            set_clauses = []
            params = []

            # 更新可能なフィールドリスト
            updatable_fields = [
                'result_type', 'mock_exam_name', 'mock_exam_format', 'grade', 'round', 'exam_date',
                'subject_kokugo_desc', 'subject_math_desc', 'subject_english_desc', 'subject_rika1_desc',
                'subject_rika2_desc', 'subject_shakai1_desc', 'subject_shakai2_desc',
                'subject_kokugo_mark', 'subject_math1a_mark', 'subject_math2bc_mark',
                'subject_english_r_mark', 'subject_english_l_mark', 'subject_rika1_mark', 'subject_rika2_mark',
                'subject_shakai1_mark', 'subject_shakai2_mark', 'subject_rika_kiso1_mark',
                'subject_rika_kiso2_mark', 'subject_info_mark'
            ]
            int_columns = updatable_fields[6:] # 点数カラム

            for field in updatable_fields:
                if field in data:
                    value = data[field]
                    # 日付処理
                    if field == 'exam_date':
                         try:
                             value = datetime.strptime(str(value), '%Y-%m-%d').date() if value else None
                         except (ValueError, TypeError):
                             value = None
                    # 数値処理
                    elif field in int_columns:
                         try:
                             value = int(value) if value is not None and value != '' else None
                         except (ValueError, TypeError):
                             value = None
                    # 空文字列はNoneとして扱う (必須項目以外)
                    elif field not in ['result_type', 'mock_exam_name', 'mock_exam_format', 'grade', 'round'] and value == '':
                         value = None

                    set_clauses.append(f"{field} = %s")
                    params.append(value)

            if not set_clauses:
                return False, "更新するデータがありません。"

            query = f"UPDATE mock_exam_results SET {', '.join(set_clauses)} WHERE id = %s"
            params.append(result_id)

            cur.execute(query, tuple(params))

        conn.commit()
        if cur.rowcount == 0:
            return False, "指定されたIDの模試結果が見つかりません。"
        return True, "模試結果を更新しました。"
    except psycopg2.Error as e:
        conn.rollback()
        print(f"データベースエラー (update_mock_exam_result): {e}")
        return False, f"模試結果の更新中にエラーが発生しました: {e}"
    finally:
        if conn:
            conn.close()


def delete_mock_exam_result(result_id):
    """指定されたIDの模試結果を削除する"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM mock_exam_results WHERE id = %s", (result_id,))
        conn.commit()
        if cur.rowcount == 0:
            return False, "指定されたIDの模試結果が見つかりません。"
        return True, "模試結果を削除しました。"
    except psycopg2.Error as e:
        conn.rollback()
        print(f"データベースエラー (delete_mock_exam_result): {e}")
        return False, f"模試結果の削除中にエラーが発生しました: {e}"
    finally:
        if conn:
            conn.close()

def get_all_mock_exam_details_for_school(school_name):
    """
    指定された校舎の全生徒の模試結果を、生徒名と共に取得する。
    """
    conn = get_db_connection()
    results = []
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(
                """
                SELECT
                    s.name AS student_name,
                    mer.*
                FROM mock_exam_results mer
                JOIN students s ON mer.student_id = s.id
                WHERE s.school = %s
                ORDER BY s.name, mer.exam_date DESC, mer.id DESC
                """,
                (school_name,)
            )
            results = cur.fetchall()
    except psycopg2.Error as e:
         print(f"データベースエラー (get_all_mock_exam_details_for_school): {e}")
    finally:
        if conn:
            conn.close()
    return [dict(row) for row in results]

def get_mock_exam_filter_options(school_name):
    """
    指定された校舎の模試結果から、フィルター用のユニークな値を取得する。
    """
    conn = get_db_connection()
    results = []
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(
                """
                SELECT
                    DISTINCT mer.mock_exam_name, mer.grade
                FROM mock_exam_results mer
                JOIN students s ON mer.student_id = s.id
                WHERE s.school = %s
                """,
                (school_name,)
            )
            results = cur.fetchall()
    except psycopg2.Error as e:
         print(f"データベースエラー (get_mock_exam_filter_options): {e}")
    finally:
        if conn:
            conn.close()

    names = sorted(list(set([r['mock_exam_name'] for r in results if r['mock_exam_name']])))
    grades = sorted(list(set([r['grade'] for r in results if r['grade']])))

    # grade_order に基づいて学年をソート
    grade_order = ['中学生', '高1', '高2', '高3', '既卒']
    sorted_grades = sorted(
        grades,
        key=lambda x: grade_order.index(x) if x in grade_order else len(grade_order)
    )

    return {
        'names': [{'label': n, 'value': n} for n in names],
        'grades': [{'label': g, 'value': g} for g in sorted_grades]
    }

def get_eiken_results_for_student(student_id):
    """生徒の英検結果を取得する"""
    conn = get_db_connection()
    results = []
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(
                "SELECT * FROM eiken_results WHERE student_id = %s ORDER BY grade",
                (student_id,)
            )
            results = cur.fetchall()
    except psycopg2.Error as e:
        print(f"データベースエラー (get_eiken_results_for_student): {e}")
    finally:
        if conn:
            conn.close()
    return [dict(row) for row in results]

def add_or_update_eiken_result(student_id, grade, cse_score):
    """英検結果を登録または更新する (UPSERT)"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # cse_score のバリデーション
            score_val = int(cse_score) if cse_score is not None and str(cse_score).strip() != '' else None
            
            query = """
                INSERT INTO eiken_results (student_id, grade, cse_score)
                VALUES (%s, %s, %s)
                ON CONFLICT (student_id, grade) 
                DO UPDATE SET cse_score = EXCLUDED.cse_score
            """
            cur.execute(query, (student_id, grade, score_val))
        conn.commit()
        return True, "英検結果を保存しました。"
    except psycopg2.Error as e:
        conn.rollback()
        print(f"データベースエラー (add_or_update_eiken_result): {e}")
        return False, f"保存中にエラーが発生しました: {e}"
    finally:
        if conn:
            conn.close()

def save_root_table(filename, content_bytes):
    """PDFファイルをデータベースに保存する"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO root_tables (filename, file_content) VALUES (%s, %s)",
                (filename, content_bytes)
            )
        conn.commit()
        return True, "アップロードが完了しました。"
    except Exception as e:
        conn.rollback()
        return False, f"保存エラー: {e}"
    finally:
        conn.close()

def get_all_root_tables():
    """登録されているルート表の一覧（IDとファイル名）を取得する"""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("SELECT id, filename, uploaded_at FROM root_tables ORDER BY uploaded_at DESC")
            return cur.fetchall()
    finally:
        conn.close()

def get_root_table_by_id(table_id):
    """IDを指定してファイル名とバイナリデータを取得する"""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("SELECT filename, file_content FROM root_tables WHERE id = %s", (table_id,))
            return cur.fetchone()
    finally:
        conn.close()

def save_root_table_with_tags(filename, content_bytes, subject, level, year):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO root_tables (filename, file_content, subject, level, academic_year) 
                   VALUES (%s, %s, %s, %s, %s)""",
                (filename, content_bytes, subject, level, year)
            )
        conn.commit()
        return True, "アップロードに成功しました。"
    except Exception as e:
        conn.rollback()
        return False, f"保存エラー: {e}"
    finally:
        conn.close()

def get_filtered_root_tables(subject=None, level=None, year=None):
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            query = "SELECT id, filename, subject, level, academic_year FROM root_tables WHERE 1=1"
            params = []
            if subject:
                query += " AND subject = %s"
                params.append(subject)
            if level:
                query += " AND level = %s"
                params.append(level)
            if year:
                query += " AND academic_year = %s"
                params.append(year)
            query += " ORDER BY academic_year DESC, subject ASC"
            cur.execute(query, tuple(params))
            return cur.fetchall()
    finally:
        conn.close()
