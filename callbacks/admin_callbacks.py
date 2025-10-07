# callbacks/admin_callbacks.py

import json
import datetime
import sqlite3
import os
import pandas as pd
from dash import Input, Output, State, html, dcc, no_update, callback_context, ALL, MATCH
import dash_bootstrap_components as dbc

from auth.user_manager import load_users, add_user
from data.nested_json_processor import (
    get_all_master_textbooks, add_master_textbook, 
    update_master_textbook, delete_master_textbook, get_all_subjects,
    get_all_students_with_details, add_student, update_student, delete_student,
    get_all_instructors_for_school
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_FILE = os.path.join(os.path.dirname(BASE_DIR), 'progress.db')

def register_admin_callbacks(app):
    """管理者ページの機能に関連するコールバックを登録します。"""
    
    # (...(user management and backup callbacks remain unchanged)...)
    @app.callback(
        [Output('user-list-modal', 'is_open'), Output('user-list-table', 'children')],
        [Input('user-list-btn', 'n_clicks'), Input('close-user-list-modal', 'n_clicks')],
        [State('user-list-modal', 'is_open')],
        prevent_initial_call=True
    )
    def toggle_user_list_modal(n_clicks, close_clicks, is_open):
        if not n_clicks and not close_clicks: return is_open, no_update
        if is_open: return False, no_update
        users = load_users()
        if not users: table = dbc.Alert("登録されているユーザーがいません。", color="info")
        else:
            table_header = [html.Thead(html.Tr([html.Th("ユーザー名"), html.Th("役割"), html.Th("所属校舎")]))]
            table_body = [html.Tbody([html.Tr([html.Td(user['username']), html.Td(user['role']), html.Td(user.get('school', 'N/A'))]) for user in users])]
            table = dbc.Table(table_header + table_body, bordered=True, striped=True, hover=True)
        return True, table

    @app.callback(Output('new-user-modal', 'is_open'),[Input('new-user-btn', 'n_clicks'), Input('close-new-user-modal', 'n_clicks')],[State('new-user-modal', 'is_open')],prevent_initial_call=True)
    def toggle_new_user_modal(n_clicks, close_clicks, is_open):
        if n_clicks or close_clicks: return not is_open
        return is_open

    @app.callback(Output('new-user-alert', 'children'),Input('create-user-button', 'n_clicks'),[State('new-username', 'value'), State('new-password', 'value'), State('new-user-role', 'value'), State('new-user-school', 'value')],prevent_initial_call=True)
    def create_new_user(n_clicks, username, password, role, school):
        if not all([username, password, role]): return dbc.Alert("ユーザー名、パスワード、役割は必須です。", color="warning")
        success, message = add_user(username, password, role, school)
        if success: return dbc.Alert(message, color="success")
        else: return dbc.Alert(message, color="danger")

    @app.callback(Output('download-backup', 'data'),Input('backup-btn', 'n_clicks'),prevent_initial_call=True)
    def download_backup(n_clicks):
        if not n_clicks: return no_update
        try:
            conn = sqlite3.connect(DATABASE_FILE)
            tables = ["users", "students", "progress", "homework", "master_textbooks", "bulk_presets", "bulk_preset_books", "student_instructors"]
            backup_data = {"export_date": datetime.datetime.now().isoformat()}
            for table in tables:
                df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
                if table == 'users' and 'password' in df.columns: df = df.drop(columns=['password'])
                backup_data[table] = df.to_dict(orient='records')
            conn.close()
            backup_content = json.dumps(backup_data, indent=2, ensure_ascii=False)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            return dict(content=backup_content, filename=f"dashboard_backup_{timestamp}.json")
        except Exception as e:
            print(f"バックアップ作成中にエラーが発生しました: {e}")
            return no_update

    # --- ★★★ ここから修正 ★★★ ---

    # --- 参考書マスター管理 ---
    @app.callback(
        Output('master-textbook-modal', 'is_open'),
        [Input('open-master-textbook-modal-btn', 'n_clicks'),
         Input('close-master-textbook-modal', 'n_clicks')],
        State('master-textbook-modal', 'is_open'),
        prevent_initial_call=True
    )
    def toggle_master_textbook_modal(open_clicks, close_clicks, is_open):
        if open_clicks or close_clicks:
            return not is_open
        return is_open

    @app.callback(
        [Output('master-textbook-list-container', 'children'),
         Output('master-textbook-alert', 'children'),
         Output('master-textbook-alert', 'is_open')],
        [Input('master-textbook-modal', 'is_open'),
         Input('admin-update-trigger', 'data'),
         Input({'type': 'delete-textbook-btn', 'index': ALL}, 'n_clicks'),
         Input('master-textbook-subject-filter', 'value'),
         Input('master-textbook-level-filter', 'value'),
         Input('master-textbook-name-filter', 'value')],
        prevent_initial_call=True
    )
    def update_master_textbook_list(is_open, update_signal, delete_clicks, subject, level, name):
        ctx = callback_context
        triggered_prop_id = ctx.triggered[0]['prop_id'] if ctx.triggered else "No trigger"
        
        alert_msg, alert_is_open = "", False

        if 'delete-textbook-btn' in triggered_prop_id and ctx.triggered[0].get('value'):
            book_id = json.loads(triggered_prop_id.split('.')[0])['index']
            success, message = delete_master_textbook(book_id)
            alert_msg = dbc.Alert(message, color="success" if success else "danger")
            alert_is_open = True

        textbooks = get_all_master_textbooks()
        df = pd.DataFrame(textbooks)
        if subject: df = df[df['subject'] == subject]
        if level: df = df[df['level'] == level]
        if name: df = df[df['book_name'].str.contains(name, na=False)]
        
        if df.empty: 
            return dbc.Alert("該当する参考書がありません。", color="info"), alert_msg, alert_is_open
        
        table_header = [html.Thead(html.Tr([html.Th("科目"), html.Th("レベル"), html.Th("参考書名"), html.Th("所要時間(h)"), html.Th("操作")]))]
        table_body = [html.Tbody([html.Tr([html.Td(row['subject']),html.Td(row['level']),html.Td(row['book_name']),html.Td(row['duration']),html.Td([dbc.Button("編集", id={'type': 'edit-textbook-btn', 'index': row['id']}, size="sm", className="me-1"),dbc.Button("削除", id={'type': 'delete-textbook-btn', 'index': row['id']}, color="danger", size="sm")])]) for _, row in df.iterrows()])]
        
        return dbc.Table(table_header + table_body, bordered=True, striped=True, hover=True, responsive=True), alert_msg, alert_is_open


    @app.callback(
        [Output('textbook-edit-modal', 'is_open'),
         Output('textbook-edit-modal-title', 'children'),
         Output('editing-textbook-id-store', 'data'),
         Output('textbook-subject-input', 'value'),
         Output('textbook-level-input', 'value'),
         Output('textbook-name-input', 'value'),
         Output('textbook-duration-input', 'value'),
         Output('textbook-edit-alert', 'is_open', allow_duplicate=True)],
        [Input('add-textbook-btn', 'n_clicks'),
         Input({'type': 'edit-textbook-btn', 'index': ALL}, 'n_clicks'),
         Input('cancel-textbook-edit-btn', 'n_clicks')],
        prevent_initial_call=True
    )
    def handle_textbook_edit_modal_open(add_clicks, edit_clicks, cancel_clicks):
        ctx = callback_context
        trigger_id = ctx.triggered_id

        if not trigger_id or (isinstance(trigger_id, dict) and not ctx.triggered[0]['value']):
            return [no_update] * 8
            
        if trigger_id == 'cancel-textbook-edit-btn':
            return False, "", None, "", "", "", None, False
        
        if trigger_id == 'add-textbook-btn':
            return True, "新規参考書の追加", None, "", "", "", None, False

        if isinstance(trigger_id, dict) and trigger_id.get('type') == 'edit-textbook-btn':
            book_id = trigger_id['index']
            all_books = get_all_master_textbooks()
            book_to_edit = next((book for book in all_books if book['id'] == book_id), None)
            if book_to_edit: 
                return (True, f"編集: {book_to_edit['book_name']}", book_id, book_to_edit['subject'], book_to_edit['level'], book_to_edit['book_name'], book_to_edit['duration'], False)
        
        return [no_update] * 8

    @app.callback(
        [Output('textbook-edit-alert', 'children'),
         Output('textbook-edit-alert', 'is_open'),
         Output('admin-update-trigger', 'data', allow_duplicate=True)],
        Input('save-textbook-btn', 'n_clicks'),
        [State('editing-textbook-id-store', 'data'),
         State('textbook-subject-input', 'value'),
         State('textbook-level-input', 'value'),
         State('textbook-name-input', 'value'),
         State('textbook-duration-input', 'value')],
        prevent_initial_call=True
    )
    def save_textbook(n_clicks, book_id, subject, level, name, duration):
        if not n_clicks: 
            return "", False, no_update
        if not all([subject, level, name, duration is not None]): 
            return dbc.Alert("すべての項目を入力してください。", color="warning"), True, no_update
        
        if book_id is None: 
            success, message = add_master_textbook(subject, level, name, float(duration))
        else: 
            success, message = update_master_textbook(book_id, subject, level, name, float(duration))
        
        if success: 
            return "", False, datetime.datetime.now().timestamp()
        else: 
            return dbc.Alert(message, color="danger"), True, no_update

    @app.callback(
        Output('textbook-edit-modal', 'is_open', allow_duplicate=True),
        Input('admin-update-trigger', 'data'),
        State('save-textbook-btn', 'n_clicks'),
        prevent_initial_call=True
    )
    def close_textbook_edit_modal_on_success(ts, n_clicks):
        if n_clicks:
             # どのボタンが押されたかを判定。save-textbook-btnでなければ何もしない
            ctx = callback_context
            if ctx.triggered_id == 'admin-update-trigger':
                 return False
        return no_update

    # --- 生徒管理 ---
    @app.callback(
        Output('student-management-modal', 'is_open'),
        [Input('open-student-management-modal-btn', 'n_clicks'),
         Input('close-student-management-modal', 'n_clicks')],
        [State('student-management-modal', 'is_open')],
        prevent_initial_call=True
    )
    def toggle_student_management_modal(open_clicks, close_clicks, is_open):
        if open_clicks or close_clicks:
            return not is_open
        return no_update

    @app.callback(
        [Output('student-list-container', 'children'),
         Output('student-management-alert', 'children'),
         Output('student-management-alert', 'is_open')],
        [Input('student-management-modal', 'is_open'),
         Input('admin-update-trigger', 'data'),
         Input({'type': 'delete-student-btn', 'index': ALL}, 'n_clicks')],
        State('auth-store', 'data'),
        prevent_initial_call=True
    )
    def update_student_list_and_handle_delete(is_open, update_signal, delete_clicks, user_info):
        ctx = callback_context
        triggered_prop_id = ctx.triggered[0]['prop_id'] if ctx.triggered else "No trigger"
        
        alert_msg, alert_is_open = "", False

        if 'delete-student-btn' in triggered_prop_id and ctx.triggered[0].get('value'):
            student_id = json.loads(triggered_prop_id.split('.')[0])['index']
            success, message = delete_student(student_id)
            alert_msg = dbc.Alert(message, color="success" if success else "danger")
            alert_is_open = True
        
        if not user_info:
            return [], alert_msg, alert_is_open

        all_students = get_all_students_with_details()
        admin_school = user_info.get('school')
        students = [s for s in all_students if s['school'] == admin_school]

        if not students:
            return dbc.Alert("この校舎には生徒が登録されていません。", color="info"), alert_msg, alert_is_open

        table_header = [html.Thead(html.Tr([
            html.Th("生徒名"), html.Th("偏差値"), html.Th("メイン講師"), html.Th("サブ講師"), html.Th("操作")
        ]))]
        table_body = [html.Tbody([
            html.Tr([
                html.Td(s['name']),
                html.Td(s.get('deviation_value', 'N/A')),
                html.Td(", ".join(s.get('main_instructors', []))),
                html.Td(", ".join(s.get('sub_instructors', []))),
                html.Td([
                    dbc.Button("編集", id={'type': 'edit-student-btn', 'index': s['id']}, size="sm", className="me-1"),
                    dbc.Button("削除", id={'type': 'delete-student-btn', 'index': s['id']}, color="danger", size="sm")
                ])
            ]) for s in students
        ])]
        
        return dbc.Table(table_header + table_body, bordered=True, striped=True, hover=True, responsive=True), alert_msg, alert_is_open
        
    @app.callback(
        [Output('student-edit-modal', 'is_open'),
         Output('student-edit-modal-title', 'children'),
         Output('editing-student-id-store', 'data'),
         Output('student-school-input', 'value'),
         Output('student-name-input', 'value'),
         Output('student-deviation-input', 'value'),
         Output('student-main-instructor-input', 'value'),
         Output('student-sub-instructor-input', 'options'),
         Output('student-sub-instructor-input', 'value'),
         Output('student-edit-alert', 'is_open', allow_duplicate=True)],
        [Input('add-student-btn', 'n_clicks'),
         Input({'type': 'edit-student-btn', 'index': ALL}, 'n_clicks'),
         Input('cancel-student-edit-btn', 'n_clicks')],
        [State('auth-store', 'data')],
        prevent_initial_call=True
    )
    def handle_student_edit_modal(add_clicks, edit_clicks, cancel_clicks, user_info):
        ctx = callback_context
        trigger_id = ctx.triggered_id

        if not trigger_id or (isinstance(trigger_id, dict) and not ctx.triggered[0]['value']):
            return [no_update] * 10
            
        admin_school = user_info.get('school', '')
        
        if trigger_id == 'cancel-student-edit-btn':
            return False, "", None, "", "", None, "", [], [], False

        sub_instructors = get_all_instructors_for_school(admin_school, role='user')
        sub_instructor_options = [{'label': i['username'], 'value': i['id']} for i in sub_instructors]
        
        main_instructors = get_all_instructors_for_school(admin_school, role='admin')
        main_instructor_username = main_instructors[0]['username'] if main_instructors else ""

        if trigger_id == 'add-student-btn':
            return True, "新規生徒の追加", None, admin_school, "", None, main_instructor_username, sub_instructor_options, [], False
        
        if isinstance(trigger_id, dict) and trigger_id.get('type') == 'edit-student-btn':
            student_id = trigger_id['index']
            all_students = get_all_students_with_details()
            student_to_edit = next((s for s in all_students if s['id'] == student_id), None)
            
            if student_to_edit:
                sub_instructor_users = [i for i in sub_instructors if i['username'] in student_to_edit.get('sub_instructors', [])]
                sub_instructor_ids = [i['id'] for i in sub_instructor_users]

                return (True, f"編集: {student_to_edit['name']}", student_id,
                        student_to_edit['school'], student_to_edit['name'], student_to_edit.get('deviation_value'),
                        main_instructor_username, sub_instructor_options, sub_instructor_ids, False)

        return [no_update] * 10

    @app.callback(
        [Output('student-edit-alert', 'children'),
         Output('student-edit-alert', 'is_open'),
         Output('admin-update-trigger', 'data')],
        Input('save-student-btn', 'n_clicks'),
        [State('editing-student-id-store', 'data'),
         State('student-name-input', 'value'),
         State('student-school-input', 'value'),
         State('student-deviation-input', 'value'),
         State('student-main-instructor-input', 'value'),
         State('student-sub-instructor-input', 'value')],
        prevent_initial_call=True
    )
    def save_student(n_clicks, student_id, name, school, deviation, main_instructor_username, sub_instructor_ids):
        if not n_clicks:
            return "", False, no_update

        if not name or not school:
            return dbc.Alert("生徒名と校舎は必須です。", color="warning"), True, no_update
        
        main_instructors = get_all_instructors_for_school(school, role='admin')
        main_instructor_user = next((i for i in main_instructors if i['username'] == main_instructor_username), None)
        main_instructor_id = main_instructor_user['id'] if main_instructor_user else None

        if student_id is None:
            success, message = add_student(name, school, deviation, main_instructor_id, sub_instructor_ids)
        else:
            success, message = update_student(student_id, name, deviation, main_instructor_id, sub_instructor_ids)

        if success:
            return "", False, datetime.datetime.now().timestamp()
        else:
            return dbc.Alert(message, color="danger"), True, no_update
            
    @app.callback(
        Output('student-edit-modal', 'is_open', allow_duplicate=True),
        Input('admin-update-trigger', 'data'),
        State('save-student-btn', 'n_clicks'),
        prevent_initial_call=True
    )
    def close_student_edit_modal_on_success(ts, n_clicks):
        if n_clicks:
            ctx = callback_context
            if ctx.triggered_id == 'admin-update-trigger':
                return False
        return no_update

    # --- ★★★ ここまで修正 ★★★ ---