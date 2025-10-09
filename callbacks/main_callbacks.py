# callbacks/main_callbacks.py

import sqlite3
import os
import pandas as pd
from dash import Input, Output, State, dcc, html, no_update
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
from data.nested_json_processor import get_subjects_for_student
# ★★★ インポートを追加 ★★★
from callbacks.progress_callbacks import create_welcome_layout, generate_dashboard_content

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_FILE = os.path.join(os.path.dirname(BASE_DIR), 'progress.db')

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
        ログインユーザーの校舎に所属する生徒のドロップダウンを生成・表示制御する。
        """
        if not user_info or pathname not in ['/', '/homework', '/past-exam']:
            return None

        user_school = user_info.get('school')
        if not user_school:
            return dbc.Alert("ユーザーに校舎が設定されていません。", color="danger")

        conn = sqlite3.connect(DATABASE_FILE)
        students_df = pd.read_sql_query(
            "SELECT id, name FROM students WHERE school = ?", conn, params=(user_school,)
        )
        conn.close()

        if students_df.empty:
            return dbc.Alert("この校舎には生徒が登録されていません。", color="info")

        return dcc.Dropdown(
            id='student-dropdown',
            options=[{'label': row['name'], 'value': row['id']} for _, row in students_df.iterrows()],
            placeholder="生徒を選択...",
            value=selected_student_id
        )

    # --- ★★★ ここから修正 ★★★ ---
    @app.callback(
        [Output('subject-tabs-container', 'children'),
         Output('dashboard-actions-container', 'children'),
         Output('dashboard-content-container', 'children')],
        Input('student-selection-store', 'data'),
        State('url', 'pathname')
    )
    def update_dashboard_on_student_select(student_id, pathname):
        """生徒が選択されたら、タブ、アクションボタン、初期コンテンツを生成する"""
        if not student_id or pathname != '/':
            # 生徒が選択されていない場合は「How to use」を表示
            return None, None, create_welcome_layout()

        # --- 生徒選択時の処理 ---
        subjects = get_subjects_for_student(student_id)
        
        all_tabs = [dbc.Tab(label="総合", tab_id="総合")]
        if subjects:
            all_tabs.extend([dbc.Tab(label=subject, tab_id=subject) for subject in subjects])

        tabs = dbc.Tabs(all_tabs, id="subject-tabs", active_tab="総合")
        
        actions = dbc.ButtonGroup([
            dbc.Button("進捗を更新", id="bulk-register-btn", color="primary", outline=True),
            dbc.Button("PDFレポート", id="download-report-btn", color="info", outline=True, className="ms-2")
        ])

        # 初期表示として「総合」タブの内容を生成
        initial_content = generate_dashboard_content(student_id, '総合')

        return tabs, actions, initial_content
    # --- ★★★ ここまで修正 ★★★ ---

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