# callbacks/admin_callbacks.py

import json
import datetime
# sqlite3 は不要なので削除
import os
import base64
import io
import pandas as pd
from dash import Input, Output, State, html, dcc, no_update, callback_context, ALL, MATCH
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
from datetime import date # ★ date をインポート

from auth.user_manager import load_users, add_user, update_user, delete_user
from data.nested_json_processor import (
    get_all_master_textbooks, add_master_textbook,
    update_master_textbook, delete_master_textbook, get_all_subjects,
    get_all_students_with_details, add_student, update_student, delete_student,
    get_all_instructors_for_school,
    get_all_presets_with_books, add_preset, update_preset, delete_preset,
    add_changelog_entry,
    get_all_mock_exam_details_for_school, get_mock_exam_filter_options # ★ 追加
)
# configからDATABASE_URLを読み込むように変更
from config.settings import APP_CONFIG

DATABASE_URL = APP_CONFIG['data']['database_url']

# BASE_DIR, RENDER_DATA_DIR, DATABASE_FILE の定義は不要なので削除


# ★★★ 新しいヘルパー関数: 管理者モーダル用の模試結果テーブル生成 ★★★
def _create_admin_mock_exam_table(df, table_type):
    """管理者モーダル用の模試結果テーブル(マークまたは記述)を生成する"""
    if df.empty:
        type_jp = "マーク" if table_type == "mark" else "記述"
        return dbc.Alert(f"フィルター条件に一致する{type_jp}模試の結果はありません。", color="warning", className="mt-3")

    # 表示するカラムを選択
    base_cols = ['student_name', 'result_type', 'mock_exam_name', 'grade', 'round', 'exam_date']
    base_headers_jp = ["生徒名", "種類", "模試名", "学年", "回", "受験日"]
    # ★ 点数カラムのスタイル (固定幅)
    score_col_style = {'width': '60px', 'minWidth': '60px', 'textAlign': 'center', 'fontSize': '0.85rem'}
    # ★ 基本情報カラムのスタイル (最小幅)
    base_col_style = {'minWidth': '100px', 'verticalAlign': 'middle'}
    base_col_style_narrow = {'minWidth': '80px', 'verticalAlign': 'middle'} # 種類、学年、回など

    if table_type == "mark":
        score_cols = [
            'subject_kokugo_mark', 'subject_math1a_mark', 'subject_math2bc_mark',
            'subject_english_r_mark', 'subject_english_l_mark', 'subject_rika1_mark', 'subject_rika2_mark',
            'subject_shakai1_mark', 'subject_shakai2_mark', 'subject_rika_kiso1_mark',
            'subject_rika_kiso2_mark', 'subject_info_mark'
        ]
        col_headers_jp = ["国", "数IA", "数IIBC", "英R", "英L", "理①", "理②", "社①", "社②", "理基①", "理基②", "情報"]
    else: # descriptive
        score_cols = [
            'subject_kokugo_desc', 'subject_math_desc', 'subject_english_desc',
            'subject_rika1_desc', 'subject_rika2_desc', 'subject_shakai1_desc', 'subject_shakai2_desc'
        ]
        col_headers_jp = ["国", "数", "英", "理①", "理②", "社①", "社②"]

    # DataFrameに必要なカラムが存在するか確認し、なければNaNで埋める
    # (get_all_mock_exam_details_for_school で全カラム取得する前提なら不要だが念のため)
    for col in base_cols + score_cols:
        if col not in df.columns:
            df[col] = pd.NA

    df_display = df[base_cols + score_cols].copy()

    # ヘッダー生成 (スタイルを適用)
    header_cells = [
        html.Th("生徒名", style={'minWidth': '120px', 'verticalAlign': 'middle'}),
        html.Th("種類", style=base_col_style_narrow),
        html.Th("模試名", style={'minWidth': '150px', 'verticalAlign': 'middle'}),
        html.Th("学年", style=base_col_style_narrow),
        html.Th("回", style=base_col_style_narrow),
        html.Th("受験日", style=base_col_style_narrow)
    ] + [html.Th(jp, style=score_col_style) for jp in col_headers_jp]
    table_header = [html.Thead(html.Tr(header_cells))]

    # ボディ生成
    table_body_rows = []
    for _, row in df_display.iterrows():
        cells = []
        # 基本情報セル
        for col in base_cols:
            value = row[col]
            if col == 'exam_date':
                # exam_date は callback 側でフォーマット済みの想定だが、ここでも処理
                display_val = value if pd.notna(value) else '-'
                if isinstance(value, date): # dateオブジェクトの場合
                    display_val = value.strftime('%Y-%m-%d')
            else:
                display_val = '-' if pd.isna(value) else value
            cells.append(html.Td(display_val))

        # 点数セル
        for col in score_cols:
            score = row[col]
            display_score = '-' if pd.isna(score) else int(score)
            cells.append(html.Td(display_score, style=score_col_style))

        table_body_rows.append(html.Tr(cells))

    table_body = [html.Tbody(table_body_rows)]
    return dbc.Table(table_header + table_body, striped=True, bordered=True, hover=True, responsive=True, size="sm")
# ★★★ ヘルパー関数ここまで ★★★


def register_admin_callbacks(app):
    # --- ユーザー管理関連コールバック ---
    # (このセクションのコールバックはデータアクセス層の関数を呼び出しているため変更なし)
    @app.callback(
        Output('user-list-modal', 'is_open'),
        [Input('user-list-btn', 'n_clicks'),
         Input('close-user-list-modal', 'n_clicks')],
        [State('user-list-modal', 'is_open')],
        prevent_initial_call=True
    )
    def toggle_user_list_modal_visibility(open_clicks, close_clicks, is_open):
        ctx = callback_context
        if not ctx.triggered or not ctx.triggered[0]['value']:
            raise PreventUpdate
        return not is_open

    @app.callback(
        Output('user-list-table', 'children'),
        [Input('user-list-modal', 'is_open'),
         Input('admin-update-trigger', 'data')],
        prevent_initial_call=True
    )
    def update_user_list_table(is_open, update_signal):
        if not is_open:
            raise PreventUpdate
        users = load_users()
        if not users:
            return dbc.Alert("登録されているユーザーがいません。", color="info")

        table_header = [html.Thead(html.Tr([html.Th("ユーザー名"), html.Th("役割"), html.Th("所属校舎"), html.Th("操作")]))]
        table_body = [html.Tbody([
            html.Tr([
                html.Td(user['username']),
                html.Td(user['role']),
                html.Td(user.get('school', 'N/A')),
                html.Td([
                    dbc.Button("編集", id={'type': 'edit-user-btn', 'index': user['id']}, size="sm", className="me-1"),
                    dbc.Button("削除", id={'type': 'delete-user-btn', 'index': user['id']}, color="danger", size="sm", outline=True)
                ])
            ]) for user in users
        ])]
        return dbc.Table(table_header + table_body, bordered=True, striped=True, hover=True, responsive=True)

    @app.callback(
        [Output('new-user-modal', 'is_open'),
         Output('new-user-alert', 'children'),
         Output('new-user-alert', 'is_open'),
         Output('admin-update-trigger', 'data', allow_duplicate=True),
         Output('toast-trigger', 'data', allow_duplicate=True)],
        [Input('new-user-btn', 'n_clicks'),
         Input('close-new-user-modal', 'n_clicks'),
         Input('create-user-button', 'n_clicks')],
        [State('new-username', 'value'),
         State('new-password', 'value'),
         State('new-user-role', 'value'),
         State('new-user-school', 'value'),
         State('new-user-modal', 'is_open')],
        prevent_initial_call=True
    )
    def handle_new_user_modal_and_creation(
        open_clicks, close_clicks, create_clicks,
        username, password, role, school, is_open):

        ctx = callback_context
        if not ctx.triggered or not ctx.triggered[0]['value']:
            return no_update, no_update, no_update, no_update, no_update

        trigger_id = ctx.triggered_id

        if trigger_id == 'new-user-btn':
            return True, "", False, no_update, no_update

        if trigger_id == 'close-new-user-modal':
            return False, "", False, no_update, no_update

        if trigger_id == 'create-user-button':
            if not all([username, password, role]):
                return True, dbc.Alert("ユーザー名、パスワード、役割は必須です。", color="warning"), True, no_update, no_update

            success, message = add_user(username, password, role, school)

            if success:
                toast_data = {'timestamp': datetime.datetime.now().isoformat(), 'message': message}
                return False, "", False, datetime.datetime.now().isoformat(), toast_data
            else:
                return True, dbc.Alert(message, color="danger"), True, no_update, no_update

        return no_update, no_update, no_update, no_update, no_update

    @app.callback(
        Output('download-backup', 'data'),
        Input('backup-btn', 'n_clicks'),
        prevent_initial_call=True
    )
    def download_backup(n_clicks):
        # PostgreSQLの場合、ファイル直接ダウンロードは適さないため、
        # pg_dumpコマンドを実行してバックアップファイルを作成し、それを返すロジックに変更する必要があります。
        # Render環境ではファイルシステムへの書き込みが制限されるため、この機能は一旦無効化するか、
        # 外部ストレージ(S3など)と連携する方式を検討する必要があります。
        # ここでは一旦機能をコメントアウトします。
        if not n_clicks:
            return no_update
        # Renderではセキュリティ上、サーバー上のシェルコマンド実行は推奨されません。
        # データベースのバックアップはRenderのダッシュボードから手動で行うのが安全です。
        print("バックアップ機能はRenderのダッシュボードから実行してください。")
        return no_update

    @app.callback(Output('master-textbook-modal', 'is_open'),[Input('open-master-textbook-modal-btn', 'n_clicks'),Input('close-master-textbook-modal', 'n_clicks')],State('master-textbook-modal', 'is_open'),prevent_initial_call=True)
    def toggle_master_textbook_modal(open_clicks, close_clicks, is_open):
        if open_clicks or close_clicks: return not is_open
        return is_open

    @app.callback(
        [Output('master-textbook-list-container', 'children')],
        [Input('master-textbook-modal', 'is_open'),
         Input('admin-update-trigger', 'data'),
         Input('master-textbook-subject-filter', 'value'),
         Input('master-textbook-level-filter', 'value'),
         Input('master-textbook-name-filter', 'value')],
        prevent_initial_call=True
    )
    def update_master_textbook_list(is_open, update_signal, subject, level, name):
        textbooks = get_all_master_textbooks()
        df = pd.DataFrame(textbooks)
        if subject: df = df[df['subject'] == subject]
        if level: df = df[df['level'] == level]
        if name: df = df[df['book_name'].str.contains(name, na=False)]

        if df.empty:
            return [dbc.Alert("該当する参考書がありません。", color="info")]

        table_header = [html.Thead(html.Tr([html.Th("科目"), html.Th("レベル"), html.Th("参考書名"), html.Th("所要時間(h)"), html.Th("操作")]))]
        table_body = [html.Tbody([html.Tr([html.Td(row['subject']),html.Td(row['level']),html.Td(row['book_name']),html.Td(row['duration']),html.Td([dbc.Button("編集", id={'type': 'edit-textbook-btn', 'index': row['id']}, size="sm", className="me-1"),dbc.Button("削除", id={'type': 'delete-textbook-btn', 'index': row['id']}, color="danger", size="sm")])]) for _, row in df.iterrows()])]

        return [dbc.Table(table_header + table_body, bordered=True, striped=True, hover=True, responsive=True)]


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
        [Output('student-list-container', 'children')],
        [Input('student-management-modal', 'is_open'),
         Input('admin-update-trigger', 'data')],
        State('auth-store', 'data'),
        prevent_initial_call=True
    )
    def update_student_list_and_handle_delete(is_open, update_signal, user_info):
        if not user_info:
            return [[]]

        all_students = get_all_students_with_details()
        admin_school = user_info.get('school')
        students = [s for s in all_students if s['school'] == admin_school]

        if not students:
            return [dbc.Alert("この校舎には生徒が登録されていません。", color="info")]

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

        return [dbc.Table(table_header + table_body, bordered=True, striped=True, hover=True, responsive=True)]

    @app.callback(
        [Output('student-edit-modal', 'is_open'),
         Output('student-edit-modal-title', 'children'),
         Output('editing-student-id-store', 'data'),
         Output('student-school-input', 'value'),
         Output('student-name-input', 'value'),
         Output('student-deviation-input', 'value'),
         # ★ Output に target_level, grade, previous_school を追加
         Output('student-target-level-input', 'value'),
         Output('student-grade-input', 'value'),
         Output('student-previous-school-input', 'value'),
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

        # ★ no_update の数を 13 に増やす
        if not trigger_id or (isinstance(trigger_id, dict) and not ctx.triggered[0]['value']):
            return [no_update] * 13

        admin_school = user_info.get('school', '')

        # ★ キャンセル時の戻り値の数を 13 に増やす (None または [] を追加)
        if trigger_id == 'cancel-student-edit-btn':
            return False, "", None, "", "", None, None, None, None, "", [], [], False

        sub_instructors = get_all_instructors_for_school(admin_school, role='user')
        sub_instructor_options = [{'label': i['username'], 'value': i['id']} for i in sub_instructors]

        main_instructors = get_all_instructors_for_school(admin_school, role='admin')
        main_instructor_username = main_instructors[0]['username'] if main_instructors else ""

        # ★ 新規追加時の戻り値の数を 13 に増やす (None を追加)
        if trigger_id == 'add-student-btn':
            return True, "新規生徒の追加", None, admin_school, "", None, None, None, None, main_instructor_username, sub_instructor_options, [], False

        if isinstance(trigger_id, dict) and trigger_id.get('type') == 'edit-student-btn':
            student_id = trigger_id['index']
            # ★ get_all_students_with_details を使うように変更
            all_students = get_all_students_with_details()
            student_to_edit = next((s for s in all_students if s['id'] == student_id), None)

            if student_to_edit:
                sub_instructor_users = [i for i in sub_instructors if i['username'] in student_to_edit.get('sub_instructors', [])]
                sub_instructor_ids = [i['id'] for i in sub_instructor_users]

                # ★ 戻り値に target_level, grade, previous_school を追加
                return (True, f"編集: {student_to_edit['name']}", student_id,
                        student_to_edit['school'], student_to_edit['name'], student_to_edit.get('deviation_value'),
                        student_to_edit.get('target_level'), # ★ 追加
                        student_to_edit.get('grade'), # ★ 追加
                        student_to_edit.get('previous_school'), # ★ 追加
                        main_instructor_username, sub_instructor_options, sub_instructor_ids, False)

        # ★ no_update の数を 13 に増やす
        return [no_update] * 13

    @app.callback(
        [Output('student-edit-alert', 'children'),
         Output('student-edit-alert', 'is_open'),
         Output('admin-update-trigger', 'data', allow_duplicate=True)], # allow_duplicate=True が必要か確認
        Input('save-student-btn', 'n_clicks'),
        [State('editing-student-id-store', 'data'),
         State('student-name-input', 'value'),
         State('student-school-input', 'value'),
         State('student-deviation-input', 'value'),
         # ★ State に target_level, grade, previous_school を追加
         State('student-target-level-input', 'value'),
         State('student-grade-input', 'value'),
         State('student-previous-school-input', 'value'),
         State('student-main-instructor-input', 'value'),
         State('student-sub-instructor-input', 'value')],
        prevent_initial_call=True
    )
    def save_student(n_clicks, student_id, name, school, deviation,
                     target_level, grade, previous_school, # ★ 追加
                     main_instructor_username, sub_instructor_ids):
        if not n_clicks:
            return "", False, no_update

        # ★ name と school の必須チェックは維持
        if not name or not school:
            return dbc.Alert("生徒名と校舎は必須です。", color="warning"), True, no_update

        # メイン講師IDを取得
        main_instructors = get_all_instructors_for_school(school, role='admin')
        main_instructor_user = next((i for i in main_instructors if i['username'] == main_instructor_username), None)
        main_instructor_id = main_instructor_user['id'] if main_instructor_user else None

        # ★ add_student と update_student の引数を修正
        if student_id is None:
            success, message = add_student(name, school, deviation, target_level, grade, previous_school, main_instructor_id, sub_instructor_ids)
        else:
            success, message = update_student(student_id, name, deviation, target_level, grade, previous_school, main_instructor_id, sub_instructor_ids)

        if success:
            # ★ タイムスタンプの代わりに一意な値をトリガーに渡す (datetime.datetime は未インポートのため修正)
            return "", False, datetime.datetime.now().isoformat()
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
        [Output('bulk-preset-list-container', 'children')],
        [Input('bulk-preset-management-modal', 'is_open'),
         Input('admin-update-trigger', 'data')],
        prevent_initial_call=True
    )
    def update_bulk_preset_list(is_open, update_signal):
        presets = get_all_presets_with_books()
        if not presets:
            return [dbc.Alert("登録されているプリセットがありません。", color="info")]

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

        return [dbc.ListGroup(items)]

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
                all_textbooks = get_all_master_textbooks()
                book_name_to_id = {b['book_name']: b['id'] for b in all_textbooks}
                selected_book_ids = [book_name_to_id[name] for name in preset_to_edit.get('books', []) if name in book_name_to_id]

                return (True, f"編集: {preset_to_edit['preset_name']}", preset_id,
                        subject_options, preset_to_edit['subject'], preset_to_edit['preset_name'],
                        selected_book_ids,
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
        Output('preset-selected-books-store', 'data', allow_duplicate=True),
        [Input({'type': 'add-preset-book-btn', 'index': ALL}, 'n_clicks'),
         Input({'type': 'remove-preset-book-btn', 'index': ALL}, 'n_clicks')],
        [State('preset-selected-books-store', 'data')],
        prevent_initial_call=True
    )
    def update_selected_books_store(add_clicks, remove_clicks, selected_book_ids):
        ctx = callback_context
        if not ctx.triggered or not ctx.triggered[0]['value']:
            raise PreventUpdate

        triggered_id = ctx.triggered_id
        updated_ids = selected_book_ids or []

        button_type = triggered_id.get('type')
        book_id = triggered_id.get('index')

        if button_type == 'add-preset-book-btn':
            if book_id not in updated_ids:
                updated_ids.append(book_id)
        elif button_type == 'remove-preset-book-btn':
            if book_id in updated_ids:
                updated_ids.remove(book_id)

        return updated_ids

    @app.callback(
        Output('preset-selected-books-list', 'children'),
        Input('preset-selected-books-store', 'data'),
    )
    def render_selected_books_list(selected_book_ids):
        """
        選択された参考書のリストを描画する。
        DB接続を直接行わず、データアクセス層の関数を利用するように修正。
        """
        if not selected_book_ids:
            return []

        # 全てのマスター参考書を取得し、IDでフィルタリングする
        all_books = get_all_master_textbooks()
        book_info = {book['id']: book['book_name'] for book in all_books if book['id'] in selected_book_ids}

        return [
            dbc.ListGroupItem([
                book_info.get(book_id, f"不明な参考書 ID: {book_id}"),
                dbc.Button("×", id={'type': 'remove-preset-book-btn', 'index': book_id}, color="danger", size="sm", className="float-end")
            ]) for book_id in selected_book_ids if book_id in book_info
        ]

    @app.callback(
        [Output('bulk-preset-edit-alert', 'children'),
         Output('bulk-preset-edit-alert', 'is_open'),
         Output('admin-update-trigger', 'data', allow_duplicate=True),
         Output('bulk-preset-edit-modal', 'is_open', allow_duplicate=True),
         Output('toast-trigger', 'data', allow_duplicate=True)],
        Input('save-bulk-preset-btn', 'n_clicks'),
        [State('editing-preset-id-store', 'data'),
         State('preset-subject-input', 'value'),
         State('preset-name-input', 'value'),
         State('preset-selected-books-store', 'data')],
        prevent_initial_call=True
    )
    def save_bulk_preset(n_clicks, preset_id, subject, name, book_ids):
        if not n_clicks:
            return "", False, no_update, no_update, no_update
        if not all([subject, name, book_ids]):
            return dbc.Alert("すべての項目を選択・入力してください。", color="warning"), True, no_update, True, no_update

        if preset_id is None:
            success, message = add_preset(subject, name, book_ids)
        else:
            success, message = update_preset(preset_id, subject, name, book_ids)

        if success:
            toast_data = {'timestamp': datetime.datetime.now().isoformat(), 'message': message}
            return "", False, datetime.datetime.now().timestamp(), False, toast_data
        else:
            return dbc.Alert(message, color="danger"), True, no_update, True, no_update

    @app.callback(
        [Output('user-edit-modal', 'is_open'),
         Output('user-edit-modal-title', 'children'),
         Output('editing-user-id-store', 'data'),
         Output('user-username-input', 'value'),
         Output('user-role-input', 'value'),
         Output('user-school-input', 'value'),
         Output('user-edit-alert', 'is_open', allow_duplicate=True)],
        [Input({'type': 'edit-user-btn', 'index': ALL}, 'n_clicks'),
         Input('cancel-user-edit-btn', 'n_clicks')],
        prevent_initial_call=True
    )
    def handle_user_edit_modal(edit_clicks, cancel_clicks):
        ctx = callback_context
        if not ctx.triggered or (isinstance(trigger_id, dict) and not ctx.triggered[0]['value']):
            raise PreventUpdate

        trigger_id = ctx.triggered_id

        if trigger_id == 'cancel-user-edit-btn':
            return False, "", None, "", "", "", False

        if isinstance(trigger_id, dict) and trigger_id.get('type') == 'edit-user-btn':
            user_id = trigger_id['index']
            users = load_users()
            user_to_edit = next((u for u in users if u['id'] == user_id), None)
            if user_to_edit:
                return (True, f"編集: {user_to_edit['username']}", user_id,
                        user_to_edit['username'], user_to_edit['role'], user_to_edit.get('school', ''), False)
        return no_update, "", None, "", "", "", False

    @app.callback(
        [Output('user-edit-alert', 'children'),
         Output('user-edit-alert', 'is_open'),
         Output('admin-update-trigger', 'data', allow_duplicate=True),
         Output('user-edit-modal', 'is_open', allow_duplicate=True),
         Output('toast-trigger', 'data', allow_duplicate=True)],
        Input('save-user-btn', 'n_clicks'),
        [State('editing-user-id-store', 'data'),
         State('user-username-input', 'value'),
         State('user-role-input', 'value'),
         State('user-school-input', 'value')],
        prevent_initial_call=True
    )
    def save_user_edit(n_clicks, user_id, username, role, school):
        if not n_clicks or not user_id:
            raise PreventUpdate

        success, message = update_user(user_id, username, role, school)
        if success:
            toast_data = {'timestamp': datetime.datetime.now().isoformat(), 'message': message}
            return "", False, datetime.datetime.now().isoformat(), False, toast_data
        else:
            return dbc.Alert(message, color="danger"), True, no_update, True, no_update

    @app.callback(
        [Output('delete-user-confirm', 'displayed'),
         Output('item-to-delete-store', 'data', allow_duplicate=True)],
        Input({'type': 'delete-user-btn', 'index': ALL}, 'n_clicks'),
        prevent_initial_call=True
    )
    def display_delete_user_confirmation(delete_clicks):
        ctx = callback_context
        if not ctx.triggered or not any(delete_clicks):
            raise PreventUpdate
        user_id = ctx.triggered_id['index']
        return True, {'type': 'user', 'id': user_id}

    @app.callback(
        [Output('admin-update-trigger', 'data', allow_duplicate=True),
         Output('toast-trigger', 'data', allow_duplicate=True)],
        Input('delete-user-confirm', 'submit_n_clicks'),
        State('item-to-delete-store', 'data'),
        prevent_initial_call=True
    )
    def do_delete_user(submit_n_clicks, item_to_delete):
        if not submit_n_clicks or not item_to_delete or item_to_delete.get('type') != 'user':
            raise PreventUpdate
        user_id = item_to_delete.get('id')
        success, message = delete_user(user_id)
        toast_data = {'timestamp': datetime.datetime.now().isoformat(), 'message': message}
        return datetime.datetime.now().isoformat(), toast_data

    @app.callback(
        [Output('delete-student-confirm', 'displayed'),
         Output('item-to-delete-store', 'data', allow_duplicate=True)],
        Input({'type': 'delete-student-btn', 'index': ALL}, 'n_clicks'),
        prevent_initial_call=True
    )
    def display_delete_student_confirmation(n_clicks):
        ctx = callback_context
        if not ctx.triggered or not any(n_clicks):
            raise PreventUpdate
        student_id = ctx.triggered_id['index']
        return True, {'type': 'student', 'id': student_id}

    @app.callback(
        [Output('admin-update-trigger', 'data', allow_duplicate=True),
         Output('toast-trigger', 'data', allow_duplicate=True)],
        Input('delete-student-confirm', 'submit_n_clicks'),
        State('item-to-delete-store', 'data'),
        prevent_initial_call=True
    )
    def do_delete_student(submit_n_clicks, item_to_delete):
        if not submit_n_clicks or not item_to_delete or item_to_delete.get('type') != 'student':
            raise PreventUpdate
        student_id = item_to_delete.get('id')
        success, message = delete_student(student_id)
        toast_data = {'timestamp': datetime.datetime.now().isoformat(), 'message': message}
        return datetime.datetime.now().isoformat(), toast_data

    @app.callback(
        [Output('delete-textbook-confirm', 'displayed'),
         Output('item-to-delete-store', 'data', allow_duplicate=True)],
        Input({'type': 'delete-textbook-btn', 'index': ALL}, 'n_clicks'),
        prevent_initial_call=True
    )
    def display_delete_textbook_confirmation(n_clicks):
        ctx = callback_context
        if not ctx.triggered or not any(n_clicks):
            raise PreventUpdate
        book_id = ctx.triggered_id['index']
        return True, {'type': 'textbook', 'id': book_id}

    @app.callback(
        [Output('admin-update-trigger', 'data', allow_duplicate=True),
         Output('toast-trigger', 'data', allow_duplicate=True)],
        Input('delete-textbook-confirm', 'submit_n_clicks'),
        State('item-to-delete-store', 'data'),
        prevent_initial_call=True
    )
    def do_delete_textbook(submit_n_clicks, item_to_delete):
        if not submit_n_clicks or not item_to_delete or item_to_delete.get('type') != 'textbook':
            raise PreventUpdate
        book_id = item_to_delete.get('id')
        success, message = delete_master_textbook(book_id)
        toast_data = {'timestamp': datetime.datetime.now().isoformat(), 'message': message}
        return datetime.datetime.now().isoformat(), toast_data

    @app.callback(
        [Output('delete-preset-confirm', 'displayed'),
         Output('item-to-delete-store', 'data', allow_duplicate=True)],
        Input({'type': 'delete-bulk-preset-btn', 'index': ALL}, 'n_clicks'),
        prevent_initial_call=True
    )
    def display_delete_preset_confirmation(n_clicks):
        ctx = callback_context
        if not ctx.triggered or not any(n_clicks):
            raise PreventUpdate
        preset_id = ctx.triggered_id['index']
        return True, {'type': 'preset', 'id': preset_id}

    @app.callback(
        [Output('admin-update-trigger', 'data', allow_duplicate=True),
         Output('toast-trigger', 'data', allow_duplicate=True)],
        Input('delete-preset-confirm', 'submit_n_clicks'),
        State('item-to-delete-store', 'data'),
        prevent_initial_call=True
    )
    def do_delete_preset(submit_n_clicks, item_to_delete):
        if not submit_n_clicks or not item_to_delete or item_to_delete.get('type') != 'preset':
            raise PreventUpdate
        preset_id = item_to_delete.get('id')
        success, message = delete_preset(preset_id)
        toast_data = {'timestamp': datetime.datetime.now().isoformat(), 'message': message}
        return datetime.datetime.now().isoformat(), toast_data

    @app.callback(
        Output('add-changelog-modal', 'is_open'),
        [Input('add-changelog-btn', 'n_clicks'),
         Input('cancel-changelog-btn', 'n_clicks'),
         Input('toast-trigger', 'data')],
        State('add-changelog-modal', 'is_open'),
        prevent_initial_call=True
    )
    def toggle_changelog_modal(open_clicks, cancel_clicks, toast_data, is_open):
        ctx = callback_context
        if not ctx.triggered:
            raise PreventUpdate

        trigger_id = ctx.triggered_id

        if trigger_id == 'toast-trigger':
            if toast_data and toast_data.get('source') == 'changelog_save':
                return False
            return no_update

        if trigger_id in ['add-changelog-btn', 'cancel-changelog-btn']:
            return not is_open

        return no_update

    @app.callback(
        [Output('changelog-modal-alert', 'children'),
         Output('changelog-modal-alert', 'is_open'),
         Output('toast-trigger', 'data', allow_duplicate=True)],
        Input('save-changelog-btn', 'n_clicks'),
        [State('changelog-version-input', 'value'),
         State('changelog-title-input', 'value'),
         State('changelog-description-input', 'value')],
        prevent_initial_call=True
    )
    def save_changelog_entry(n_clicks, version, title, description):
        if not n_clicks:
            raise PreventUpdate

        if not all([version, title, description]):
            return dbc.Alert("すべての項目を入力してください。", color="warning"), True, no_update

        success, message = add_changelog_entry(version, title, description)

        if success:
            toast_data = {'timestamp': datetime.datetime.now().isoformat(), 'message': message, 'source': 'changelog_save'}
            return "", False, toast_data
        else:
            return dbc.Alert(message, color="danger"), True, no_update


    # --- 校舎別 模試結果一覧モーダル ---

    @app.callback(
        Output('mock-exam-list-modal', 'is_open'),
        [Input('open-mock-exam-list-modal-btn', 'n_clicks'),
         Input('close-mock-exam-list-modal', 'n_clicks')],
        State('mock-exam-list-modal', 'is_open'),
        prevent_initial_call=True
    )
    def toggle_mock_exam_list_modal(open_clicks, close_clicks, is_open):
        """模試結果一覧モーダルの表示/非表示を切り替える"""
        if open_clicks or close_clicks:
            return not is_open
        return no_update

    @app.callback(
        [Output('mock-exam-list-filter-name', 'options'),
         Output('mock-exam-list-filter-grade', 'options')],
        Input('mock-exam-list-modal', 'is_open'),
        State('auth-store', 'data'),
        prevent_initial_call=True
    )
    def update_mock_exam_list_filters(is_open, user_info):
        """モーダルが開かれたときにフィルターオプションを読み込む"""
        if not is_open or not user_info:
            return no_update, no_update

        school_name = user_info.get('school')
        if not school_name:
            return [], []

        options = get_mock_exam_filter_options(school_name)
        return options.get('names', []), options.get('grades', [])

    # ★★★ 模試結果一覧テーブルコールバックを修正 ★★★
    @app.callback(
        [Output('mock-exam-list-table-container-mark', 'children'),
         Output('mock-exam-list-table-container-descriptive', 'children')],
        [Input('mock-exam-list-modal', 'is_open'), # モーダルが開いた時もトリガー
         Input('mock-exam-list-filter-type', 'value'),
         Input('mock-exam-list-filter-name', 'value'),
         Input('mock-exam-list-filter-format', 'value'),
         Input('mock-exam-list-filter-grade', 'value')],
        State('auth-store', 'data'),
        prevent_initial_call=True
    )
    def update_mock_exam_list_table(
        is_open, filter_type, filter_name, filter_format, filter_grade,
        user_info):
        """フィルターの値に基づいて模試結果一覧テーブルを更新する"""

        ctx = callback_context
        triggered_id = ctx.triggered_id

        # モーダルが閉じている場合は更新しない
        if not is_open:
            return no_update, no_update

        if not user_info:
            alert = dbc.Alert("ユーザー情報が見つかりません。", color="danger")
            return alert, alert

        school_name = user_info.get('school')
        if not school_name:
            alert = dbc.Alert("所属校舎が設定されていません。", color="danger")
            return alert, alert

        # データを取得
        results = get_all_mock_exam_details_for_school(school_name)
        if not results:
            no_data_alert = dbc.Alert("この校舎には登録されている模試結果がありません。", color="info")
            return no_data_alert, no_data_alert

        df = pd.DataFrame(results)

        # 日付のフォーマット (pd.to_datetime と .dt.strftime を使う)
        df['exam_date'] = pd.to_datetime(df['exam_date'], errors='coerce').dt.strftime('%Y-%m-%d').fillna('-')


        # フィルタリング (形式フィルターを除く)
        if filter_type:
            df = df[df['result_type'] == filter_type]
        if filter_name:
            df = df[df['mock_exam_name'] == filter_name]
        if filter_grade:
            df = df[df['grade'] == filter_grade]

        if df.empty:
            no_match_alert = dbc.Alert("フィルター条件に一致する結果はありません。", color="warning")
            return no_match_alert, no_match_alert

        # フィルター後のデータでマークと記述に分割
        df_mark = df[df['mock_exam_format'] == 'マーク'].copy()
        df_desc = df[df['mock_exam_format'] == '記述'].copy()

        # ヘルパー関数を使ってテーブルを生成
        mark_table = _create_admin_mock_exam_table(df_mark, "mark")
        desc_table = _create_admin_mock_exam_table(df_desc, "descriptive")

        # 形式フィルターが適用されている場合、片方のタブを空にする
        if filter_format == 'マーク':
            desc_table = None # 記述タブは非表示 (空にする)
            if df_mark.empty: # 絞り込んだ結果マークが無い場合
                 mark_table = dbc.Alert("フィルター条件に一致するマーク模試の結果はありません。", color="warning", className="mt-3")
        elif filter_format == '記述':
            mark_table = None # マークタブは非表示 (空にする)
            if df_desc.empty: # 絞り込んだ結果記述が無い場合
                 desc_table = dbc.Alert("フィルター条件に一致する記述模試の結果はありません。", color="warning", className="mt-3")

        return mark_table, desc_table
