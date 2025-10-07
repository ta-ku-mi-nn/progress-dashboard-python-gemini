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
    get_all_students_with_details, add_student, update_student, delete_student
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_FILE = os.path.join(os.path.dirname(BASE_DIR), 'progress.db')

def register_admin_callbacks(app):
    """管理者ページの機能に関連するコールバックを登録します。"""
    # (...既存のユーザー管理、データバックアップ、参考書管理のコールバックは変更なし...)
    # (user management, backup, and textbook master callbacks remain unchanged)
    
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
            tables = ["users", "students", "progress", "homework", "master_textbooks", "bulk_presets", "bulk_preset_books"]
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

    @app.callback(Output('master-textbook-modal', 'is_open'),[Input('open-master-textbook-modal-btn', 'n_clicks'),Input('close-master-textbook-modal', 'n_clicks')],State('master-textbook-modal', 'is_open'),prevent_initial_call=True)
    def toggle_master_textbook_modal(open_clicks, close_clicks, is_open):
        if open_clicks or close_clicks: return not is_open
        return is_open

    @app.callback(Output('master-textbook-subject-filter', 'options'),Input('master-textbook-modal', 'is_open'))
    def update_subject_filter_options(is_open):
        if not is_open: return []
        subjects = get_all_subjects()
        return [{'label': s, 'value': s} for s in subjects]

    @app.callback(Output('master-textbook-level-filter', 'options'),Input('master-textbook-modal', 'is_open'))
    def update_level_filter_options(is_open):
        if not is_open: return []
        levels = ['基礎徹底', '日大', 'MARCH', '早慶']
        return [{'label': l, 'value': l} for l in levels]

    @app.callback(Output('master-textbook-list-container', 'children'),[Input('master-textbook-subject-filter', 'value'),Input('master-textbook-level-filter', 'value'),Input('master-textbook-name-filter', 'value'),Input('textbook-edit-modal', 'is_open')])
    def update_master_textbook_list(subject, level, name, edit_modal_is_open):
        textbooks = get_all_master_textbooks()
        df = pd.DataFrame(textbooks)
        if subject: df = df[df['subject'] == subject]
        if level: df = df[df['level'] == level]
        if name: df = df[df['book_name'].str.contains(name, na=False)]
        if df.empty: return dbc.Alert("該当する参考書がありません。", color="info")
        table_header = [html.Thead(html.Tr([html.Th("科目"), html.Th("レベル"), html.Th("参考書名"), html.Th("所要時間(h)"), html.Th("操作")]))]
        table_body = [html.Tbody([html.Tr([html.Td(row['subject']),html.Td(row['level']),html.Td(row['book_name']),html.Td(row['duration']),html.Td([dbc.Button("編集", id={'type': 'edit-textbook-btn', 'index': row['id']}, size="sm", className="me-1"),dbc.Button("削除", id={'type': 'delete-textbook-btn', 'index': row['id']}, color="danger", size="sm")])]) for _, row in df.iterrows()])]
        return dbc.Table(table_header + table_body, bordered=True, striped=True, hover=True, responsive=True)

    @app.callback([Output('textbook-edit-modal', 'is_open'),Output('textbook-edit-modal-title', 'children'),Output('editing-textbook-id-store', 'data'),Output('textbook-subject-input', 'value'),Output('textbook-level-input', 'value'),Output('textbook-name-input', 'value'),Output('textbook-duration-input', 'value')],[Input('add-textbook-btn', 'n_clicks'),Input({'type': 'edit-textbook-btn', 'index': ALL}, 'n_clicks'),Input('cancel-textbook-edit-btn', 'n_clicks')],prevent_initial_call=True)
    def handle_edit_modal_open(add_clicks, edit_clicks, cancel_clicks):
        ctx = callback_context
        if not ctx.triggered or not ctx.triggered[0].get('value'): return [no_update] * 7
        trigger_id_str = ctx.triggered[0]['prop_id'].split('.')[0]
        if 'cancel-textbook-edit-btn' in trigger_id_str: return False, "", None, "", "", "", ""
        if 'add-textbook-btn' in trigger_id_str: return True, "新規参考書の追加", None, "", "", "", ""
        if 'edit-textbook-btn' in trigger_id_str:
            book_id = json.loads(trigger_id_str)['index']
            all_books = get_all_master_textbooks()
            book_to_edit = next((book for book in all_books if book['id'] == book_id), None)
            if book_to_edit: return (True, f"編集: {book_to_edit['book_name']}", book_id, book_to_edit['subject'], book_to_edit['level'], book_to_edit['book_name'], book_to_edit['duration'])
        return [no_update] * 7

    @app.callback([Output('textbook-edit-alert', 'children'),Output('textbook-edit-alert', 'is_open'),Output('textbook-edit-modal', 'is_open', allow_duplicate=True)],Input('save-textbook-btn', 'n_clicks'),[State('editing-textbook-id-store', 'data'),State('textbook-subject-input', 'value'),State('textbook-level-input', 'value'),State('textbook-name-input', 'value'),State('textbook-duration-input', 'value')],prevent_initial_call=True)
    def save_textbook(n_clicks, book_id, subject, level, name, duration):
        if not n_clicks: return "", False, no_update
        if not all([subject, level, name, duration is not None]): return dbc.Alert("すべての項目を入力してください。", color="warning"), True, no_update
        if book_id is None: success, message = add_master_textbook(subject, level, name, float(duration))
        else: success, message = update_master_textbook(book_id, subject, level, name, float(duration))
        if success: return "", False, False
        else: return dbc.Alert(message, color="danger"), True, no_update

    @app.callback([Output('master-textbook-alert', 'children'),Output('master-textbook-alert', 'is_open'),Output('master-textbook-modal', 'is_open', allow_duplicate=True)],Input({'type': 'delete-textbook-btn', 'index': ALL}, 'n_clicks'),prevent_initial_call=True)
    def delete_textbook(n_clicks):
        ctx = callback_context
        if not ctx.triggered or not ctx.triggered[0].get('value'): return "", False, no_update
        trigger_id_str = ctx.triggered[0]['prop_id'].split('.')[0]
        book_id = json.loads(trigger_id_str)['index']
        success, message = delete_master_textbook(book_id)
        if success: return dbc.Alert(message, color="success"), True, True
        else: return dbc.Alert(message, color="danger"), True, no_update

    # --- ★★★ ここからが生徒管理のコールバック（全体を修正） ★★★
    
    @app.callback(
        Output('student-management-modal', 'is_open'),
        [Input('open-student-management-modal-btn', 'n_clicks'),
         Input('close-student-management-modal', 'n_clicks'),
         Input('save-student-btn', 'n_clicks')], # 保存成功時にも閉じるためInputに追加
        [State('student-management-modal', 'is_open'),
         State('student-edit-alert', 'is_open')],
        prevent_initial_call=True
    )
    def toggle_student_management_modal(open_clicks, close_clicks, save_clicks, is_open, edit_alert_is_open):
        ctx = callback_context
        trigger_id = ctx.triggered_id
        
        # 保存ボタンが押され、かつエラーアラートが表示されていない（＝成功した）場合に閉じる
        if trigger_id == 'save-student-btn' and not edit_alert_is_open:
            return False
        
        if trigger_id == 'open-student-management-modal-btn' or trigger_id == 'close-student-management-modal':
            return not is_open
        
        return no_update

    @app.callback(
        Output('student-list-container', 'children'),
        # is_openだけでなく、save_student_btnのクリックもトリガーにする
        [Input('student-management-modal', 'is_open'),
         Input('save-student-btn', 'n_clicks'),
         Input({'type': 'delete-student-btn', 'index': ALL}, 'n_clicks')],
        State('auth-store', 'data'),
        prevent_initial_call=True
    )
    def update_student_list(is_open, save_clicks, delete_clicks, user_info):
        ctx = callback_context
        # モーダルが開いていない、かつ、削除ボタンも押されていない場合は更新しない
        if not is_open and not any(delete_clicks):
            return no_update

        if not user_info:
            return []
        
        all_students = get_all_students_with_details()
        admin_school = user_info.get('school')
        students = [s for s in all_students if s['school'] == admin_school]

        if not students:
            return dbc.Alert("この校舎には生徒が登録されていません。", color="info")

        table_header = [html.Thead(html.Tr([
            html.Th("生徒名"), html.Th("偏差値"), html.Th("メイン講師"), html.Th("サブ講師"), html.Th("操作")
        ]))]
        
        table_body = [html.Tbody([
            html.Tr([
                html.Td(s['name']),
                html.Td(s.get('deviation_value', 'N/A')),
                html.Td(s.get('main_instructor', 'N/A')),
                html.Td(s.get('sub_instructor', '')),
                html.Td([
                    dbc.Button("編集", id={'type': 'edit-student-btn', 'index': s['id']}, size="sm", className="me-1"),
                    dbc.Button("削除", id={'type': 'delete-student-btn', 'index': s['id']}, color="danger", size="sm")
                ])
            ]) for s in students
        ])]
        return dbc.Table(table_header + table_body, bordered=True, striped=True, hover=True, responsive=True)
        
    @app.callback(
        [Output('student-edit-modal', 'is_open'),
         Output('student-edit-modal-title', 'children'),
         Output('editing-student-id-store', 'data'),
         Output('student-school-input', 'value'),
         Output('student-main-instructor-input', 'value'),
         Output('student-name-input', 'value'),
         Output('student-deviation-input', 'value'),
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
        if not ctx.triggered or not ctx.triggered[0].get('value'):
            return [no_update] * 9

        trigger_id_str = ctx.triggered[0]['prop_id'].split('.')[0]
        admin_school = user_info.get('school', '')
        admin_username = user_info.get('username', '')
        
        if 'cancel-student-edit-btn' in trigger_id_str:
            return False, "", None, "", "", "", None, "", False

        if 'add-student-btn' in trigger_id_str:
            return True, "新規生徒の追加", None, admin_school, admin_username, "", None, "", False
        
        if 'edit-student-btn' in trigger_id_str:
            student_id = json.loads(trigger_id_str)['index']
            all_students = get_all_students_with_details()
            student_to_edit = next((s for s in all_students if s['id'] == student_id), None)
            if student_to_edit:
                return (True, f"編集: {student_to_edit['name']}", student_id,
                        student_to_edit['school'], student_to_edit.get('main_instructor', ''),
                        student_to_edit['name'], student_to_edit.get('deviation_value'),
                        student_to_edit.get('sub_instructor', ''), False)

        return [no_update] * 9

    @app.callback(
        [Output('student-edit-alert', 'children'),
         Output('student-edit-alert', 'is_open'),
         Output('student-edit-modal', 'is_open', allow_duplicate=True)],
        Input('save-student-btn', 'n_clicks'),
        [State('editing-student-id-store', 'data'),
         State('student-name-input', 'value'),
         State('student-school-input', 'value'),
         State('student-deviation-input', 'value'),
         State('student-sub-instructor-input', 'value')],
        prevent_initial_call=True
    )
    def save_student(n_clicks, student_id, name, school, deviation, sub_instructor):
        if not n_clicks:
            return "", False, no_update

        if not name or not school:
            return dbc.Alert("生徒名と校舎は必須です。", color="warning"), True, no_update

        if student_id is None:
            success, message = add_student(name, school, deviation, sub_instructor)
        else:
            success, message = update_student(student_id, name, deviation, sub_instructor)

        if success:
            return "", False, False # 成功したらアラートを消し、編集モーダルを閉じる
        else:
            return dbc.Alert(message, color="danger"), True, no_update

    @app.callback(
        [Output('student-management-alert', 'children'),
         Output('student-management-alert', 'is_open')],
        Input({'type': 'delete-student-btn', 'index': ALL}, 'n_clicks'),
        prevent_initial_call=True
    )
    def handle_delete_student(n_clicks):
        ctx = callback_context
        if not ctx.triggered or not ctx.triggered[0].get('value'):
            return "", False
        
        # ★★★ 修正：ctx.triggered_id は辞書なので、直接アクセスする ★★★
        student_id = ctx.triggered_id['index']
        success, message = delete_student(student_id)
        
        return dbc.Alert(message, color="success" if success else "danger"), True