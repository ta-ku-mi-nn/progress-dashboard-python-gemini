# callbacks/main_callbacks.py

import pandas as pd
from dash import Input, Output, State, dcc, html, no_update # ★ dcc をインポート
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
from data.nested_json_processor import get_subjects_for_student, get_student_info_by_id, get_students_for_user
from utils.permissions import can_access_student
from callbacks.progress_callbacks import create_welcome_layout, generate_dashboard_content

def register_main_callbacks(app):
    """メインページとグローバルセレクターに関連するコールバックを登録します。"""

    @app.callback(
        Output('student-dropdown-container', 'children'),
        Input('url', 'pathname'),
        State('auth-store', 'data'),
        State('student-selection-store', 'data')
    )
    def update_student_dropdown(pathname, user_info, selected_student_id):
        """
        ログインユーザーの役割に応じて、表示する生徒のドロップダウンを生成する。
        """
        if not user_info or pathname not in ['/', '/homework', '/past-exam']:
            return None

        # ユーザー情報に基づいて表示すべき生徒のリストを取得
        students = get_students_for_user(user_info)

        if not students:
            message = "担当の生徒が登録されていません。" if user_info.get('role') != 'admin' else "この校舎には生徒が登録されていません。"
            return dbc.Alert(message, color="info")

        return dcc.Dropdown(
            id='student-dropdown',
            options=[{'label': s['name'], 'value': s['id']} for s in students],
            placeholder="生徒を選択...",
            value=selected_student_id
        )

    # ★★★ 修正箇所 ★★★
    @app.callback(
        [Output('subject-tabs-container', 'children'),
         Output('dashboard-actions-container', 'children'),
         Output('dashboard-content-container', 'children', allow_duplicate=True)],
        Input('student-selection-store', 'data'),
        [State('url', 'pathname'),
         State('auth-store', 'data')],
        prevent_initial_call=True
    )
    def update_dashboard_on_student_select(student_id, pathname, user_info):
        """生徒が選択されたら、タブ、アクションボタン、初期コンテンツを生成する"""
        if not student_id or pathname != '/':
            # 生徒が選択されていない場合は、ウェルカム画面を表示
            return None, None, create_welcome_layout()

        student_info = get_student_info_by_id(student_id)
        subjects = get_subjects_for_student(student_id)

        all_tabs = [dbc.Tab(label="総合", tab_id="総合")]
        if subjects:
            all_tabs.extend([dbc.Tab(label=subject, tab_id=subject) for subject in subjects])

        # ここで `subject-tabs` を生成する
        tabs = dbc.Tabs(all_tabs, id="subject-tabs", active_tab="総合")

        action_buttons = []
        if can_access_student(user_info, student_info):
            action_buttons.append(dbc.Button("進捗を更新", id={'type': 'open-plan-modal', 'index': 'main'}, color="primary", outline=True))

        action_buttons.append(dbc.Button("印刷", id="download-report-btn", color="info", outline=True, className="ms-2"))

        actions = dbc.ButtonGroup(action_buttons)

        # ★ 修正 ★
        # 最初の表示として「総合」タブの内容を生成する代わりに、ローディングスピナーを返す
        # initial_content = generate_dashboard_content(student_id, '総合') # <-- ★ 削除
        
        # ★ dcc.Loading を返すように変更
        initial_content = dcc.Loading(id="loading-initial-content", children=None, type="default")

        return tabs, actions, initial_content
    # ★★★ 修正ここまで ★★★

    @app.callback(
        Output('student-selection-store', 'data'),
        Input('student-dropdown', 'value'),
        prevent_initial_call=True
    )
    def store_student_selection(student_id):
        """選択された生徒IDをセッションに保存する"""
        if student_id is None:
            raise PreventUpdate
        return student_id