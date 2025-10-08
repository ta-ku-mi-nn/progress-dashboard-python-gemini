# callbacks/admin_callbacks.py

import json
import datetime
import sqlite3
import os
import pandas as pd
from dash import Input, Output, State, html, dcc, no_update, callback_context, ALL, MATCH
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc

from auth.user_manager import load_users, add_user
from data.nested_json_processor import (
    get_all_master_textbooks, add_master_textbook,
    update_master_textbook, delete_master_textbook, get_all_subjects,
    get_all_students_with_details, add_student, update_student, delete_student,
    get_all_instructors_for_school,
    get_all_presets_with_books, add_preset, update_preset, delete_preset
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_FILE = os.path.join(os.path.dirname(BASE_DIR), 'progress.db')

def register_admin_callbacks(app):
    """管理者ページの機能に関連するコールバックを登録します。"""

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

    @app.callback(Output('master-textbook-modal', 'is_open'),[Input('open-master-textbook-modal-btn', 'n_clicks'),Input('close-master-textbook-modal', 'n_clicks')],State('master-textbook-modal', 'is_open'),prevent_initial_call=True)
    def toggle_master_textbook_modal(open_clicks, close_clicks, is_open):
        if open_clicks or close_clicks: return not is_open
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
            ctx = callback_context
            if ctx.triggered_id == 'admin-update-trigger':
                 return False
        return no_update

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
        ctx = callback_context # ctxを定義
        if n_clicks and ctx.triggered_id == 'admin-update-trigger':
            return False
        return no_update

    # --- 一括登録プリセット管理 ---

    @app.callback(
        Output('bulk-preset-management-modal', 'is_open'),
        [Input('open-bulk-preset-modal-btn', 'n_clicks'),
         Input('close-bulk-preset-modal', 'n_clicks')],
        State('bulk-preset-management-modal', 'is_open'),
        prevent_initial_call=True
    )
    def toggle_bulk_preset_modal(open_clicks, close_clicks, is_open):
        if open_clicks or close_clicks:
            return not is_open
        return no_update

    @app.callback(
        [Output('bulk-preset-list-container', 'children'),
         Output('bulk-preset-alert', 'children'),
         Output('bulk-preset-alert', 'is_open')],
        [Input('bulk-preset-management-modal', 'is_open'),
         Input('admin-update-trigger', 'data'),
         Input({'type': 'delete-bulk-preset-btn', 'index': ALL}, 'n_clicks')],
        prevent_initial_call=True
    )
    def update_bulk_preset_list(is_open, update_signal, delete_clicks):
        ctx = callback_context
        triggered_prop_id = ctx.triggered[0]['prop_id'] if ctx.triggered else "No trigger"

        alert_msg, alert_is_open = "", False

        if 'delete-bulk-preset-btn' in triggered_prop_id and ctx.triggered[0].get('value'):
            preset_id = json.loads(triggered_prop_id.split('.')[0])['index']
            success, message = delete_preset(preset_id)
            alert_msg = dbc.Alert(message, color="success" if success else "danger")
            alert_is_open = True

        presets = get_all_presets_with_books()
        if not presets:
            return dbc.Alert("登録されているプリセットがありません。", color="info"), alert_msg, alert_is_open

        items = []
        for preset in presets:
            items.append(dbc.ListGroupItem([
                dbc.Row([
                    dbc.Col([
                        html.Strong(f"{preset['subject']} - {preset['preset_name']}"),
                        html.P(", ".join(preset['books']), className="text-muted small")
                    ]),
                    dbc.Col([
                        dbc.Button("編集", id={'type': 'edit-bulk-preset-btn', 'index': preset['id']}, size="sm", className="me-1"),
                        dbc.Button("削除", id={'type': 'delete-bulk-preset-btn', 'index': preset['id']}, color="danger", size="sm")
                    ], width="auto")
                ], align="center")
            ]))

        return dbc.ListGroup(items), alert_msg, alert_is_open

    # --- ★★★ ここから修正箇所 ★★★ ---
    @app.callback(
        [Output('bulk-preset-edit-modal', 'is_open'),
         Output('bulk-preset-edit-modal-title', 'children'),
         Output('editing-preset-id-store', 'data'),
         Output('preset-subject-input', 'options'),
         Output('preset-subject-input', 'value'),
         Output('preset-name-input', 'value'),
         Output('preset-selected-books-store', 'data'),
         Output('preset-book-subject-filter', 'options'),
         Output('preset-book-level-filter', 'options')],
        [Input('add-bulk-preset-btn', 'n_clicks'),
         Input({'type': 'edit-bulk-preset-btn', 'index': ALL}, 'n_clicks'),
         Input('cancel-bulk-preset-edit-btn', 'n_clicks')],
        prevent_initial_call=True
    )
    def handle_bulk_preset_edit_modal(add_clicks, edit_clicks, cancel_clicks):
        ctx = callback_context
        if not ctx.triggered or (isinstance(ctx.triggered_id, dict) and not ctx.triggered[0]['value']):
            return [no_update] * 9
        
        trigger_id = ctx.triggered_id
        
        subjects = get_all_subjects()
        subject_options = [{'label': s, 'value': s} for s in subjects]
        levels = ['基礎徹底', '日大', 'MARCH', '早慶']
        level_options = [{'label': l, 'value': l} for l in levels]

        if trigger_id == 'cancel-bulk-preset-edit-btn':
            return False, "", None, no_update, None, "", [], no_update, no_update
        
        if trigger_id == 'add-bulk-preset-btn':
            return True, "新規プリセット作成", None, subject_options, None, "", [], subject_options, level_options
            
        if isinstance(trigger_id, dict) and trigger_id.get('type') == 'edit-bulk-preset-btn':
            preset_id = trigger_id['index']
            presets = get_all_presets_with_books()
            preset_to_edit = next((p for p in presets if p['id'] == preset_id), None)
            if preset_to_edit:
                # 参考書名からIDへの変換ロジック
                all_textbooks = get_all_master_textbooks()
                book_name_to_id = {b['book_name']: b['id'] for b in all_textbooks}
                selected_book_ids = [book_name_to_id[name] for name in preset_to_edit.get('books', []) if name in book_name_to_id]
                
                return (True, f"編集: {preset_to_edit['preset_name']}", preset_id, 
                        subject_options, preset_to_edit['subject'], preset_to_edit['preset_name'], 
                        selected_book_ids, # 名前リストの代わりにIDリストを渡す
                        subject_options, level_options)
        
        return [no_update] * 9

    @app.callback(
        Output('preset-available-books-list', 'children'),
        [Input('bulk-preset-edit-modal', 'is_open'),
         Input('preset-book-subject-filter', 'value'),
         Input('preset-book-level-filter', 'value'),
         Input('preset-book-name-filter', 'value')]
    )
    def update_available_books_list(is_open, subject, level, name):
        if not is_open:
            return []
        all_books = get_all_master_textbooks()
        df = pd.DataFrame(all_books)
        if subject: df = df[df['subject'] == subject]
        if level: df = df[df['level'] == level]
        if name: df = df[df['book_name'].str.contains(name, na=False)]
        
        items = []
        for _, b in df.iterrows():
            item = dbc.ListGroupItem(
                dbc.Row(
                    [
                        dbc.Col(f"[{b['level']}] {b['book_name']}", width="auto", className="me-auto"),
                        dbc.Col(
                            dbc.Button("追加", id={'type': 'add-preset-book-btn', 'index': b['id']}, size="sm", color="primary", outline=True), 
                            width="auto"
                        )
                    ],
                    align="center",
                    justify="between",
                )
            )
            items.append(item)
        return dbc.ListGroup(items, flush=True)

    @app.callback(
        [Output('preset-selected-books-store', 'data', allow_duplicate=True),
         Output('preset-selected-books-list', 'children')],
        [Input('bulk-preset-edit-modal', 'is_open'),
         Input({'type': 'add-preset-book-btn', 'index': ALL}, 'n_clicks'),
         Input({'type': 'remove-preset-book-btn', 'index': ALL}, 'n_clicks')],
        [State('preset-selected-books-store', 'data')],
        prevent_initial_call=True
    )
    def handle_book_selection_and_render(is_open, add_clicks, remove_clicks, selected_book_ids):
        ctx = callback_context
        triggered_id = ctx.triggered_id
        
        updated_ids = selected_book_ids or []

        # ボタンクリックによるIDリストの更新
        if isinstance(triggered_id, dict) and ctx.triggered[0]['value']:
            button_type = triggered_id.get('type')
            book_id = triggered_id.get('index')
            
            if button_type == 'add-preset-book-btn':
                if book_id not in updated_ids:
                    updated_ids.append(book_id)
            elif button_type == 'remove-preset-book-btn':
                if book_id in updated_ids:
                    updated_ids.remove(book_id)
        
        # IDリストを元に表示用コンポーネントを生成
        if not updated_ids:
            return [], []

        conn = sqlite3.connect(DATABASE_FILE)
        try:
            placeholders = ','.join('?' for _ in updated_ids)
            query = f"SELECT id, book_name FROM master_textbooks WHERE id IN ({placeholders})"
            cursor = conn.cursor()
            cursor.execute(query, updated_ids)
            book_info = {row[0]: row[1] for row in cursor.fetchall()}
        finally:
            conn.close()

        selected_list_items = [
            dbc.ListGroupItem([
                book_info.get(book_id, f"不明な参考書 ID: {book_id}"),
                dbc.Button("×", id={'type': 'remove-preset-book-btn', 'index': book_id}, color="danger", size="sm", className="float-end")
            ]) for book_id in updated_ids if book_id in book_info
        ]

        # ボタンが押された場合のみストアを更新する
        if isinstance(triggered_id, dict):
            return updated_ids, selected_list_items
        
        # モーダルが開かれただけの時は、表示リストのみを更新
        return no_update, selected_list_items


    @app.callback(
        [Output('bulk-preset-edit-alert', 'children'),
         Output('bulk-preset-edit-alert', 'is_open'),
         Output('admin-update-trigger', 'data', allow_duplicate=True)],
        Input('save-bulk-preset-btn', 'n_clicks'),
        [State('editing-preset-id-store', 'data'),
         State('preset-subject-input', 'value'),
         State('preset-name-input', 'value'),
         State('preset-selected-books-store', 'data')],
        prevent_initial_call=True
    )
    def save_bulk_preset(n_clicks, preset_id, subject, name, book_ids):
        if not n_clicks:
            return "", False, no_update
        if not all([subject, name, book_ids]):
            return dbc.Alert("すべての項目を選択・入力してください。", color="warning"), True, no_update
        
        if preset_id is None:
            success, message = add_preset(subject, name, book_ids)
        else:
            success, message = update_preset(preset_id, subject, name, book_ids)
            
        if success:
            return "", False, datetime.datetime.now().timestamp()
        else:
            return dbc.Alert(message, color="danger"), True, no_update
            
    @app.callback(
        Output('bulk-preset-edit-modal', 'is_open', allow_duplicate=True),
        Input('admin-update-trigger', 'data'),
        State('save-bulk-preset-btn', 'n_clicks'),
        prevent_initial_call=True
    )
    def close_bulk_preset_edit_modal_on_success(ts, n_clicks):
        ctx = callback_context
        if n_clicks and ctx.triggered_id == 'admin-update-trigger':
            return False
        return no_update
    # --- ★★★ 修正箇所ここまで ★★★ ---