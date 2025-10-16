# callbacks/main_callbacks.py

import sqlite3
import os
import pandas as pd
from dash import Input, Output, State, dcc, html, no_update
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
from data.nested_json_processor import get_subjects_for_student, get_student_info_by_id, get_assigned_students_for_user # 変更箇所: get_assigned_students_for_userをインポート
from utils.permissions import can_access_student
# ★★★ インポートを追加 ★★★
from callbacks.progress_callbacks import create_welcome_layout, generate_dashboard_content

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# RenderのDiskマウントパス（/var/data）が存在すればそちらを使用
RENDER_DATA_DIR = "/var/data"
if os.path.exists(RENDER_DATA_DIR):
    # 本番環境（Render）用のパス
    DB_DIR = RENDER_DATA_DIR
else:
    # ローカル開発環境用のパス (プロジェクトのルートディレクトリを指す)
    # このファイルの2階層上がプロジェクトルート
    DB_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATABASE_FILE = os.path.join(DB_DIR, 'progress.db')

def register_main_callbacks(app):
    """メインページとグローバルセレクターに関連するコールバックを登録します。"""

    # --- ★★★ ここから修正 ★★★
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

        students = []
        # 管理者の場合は校舎の全生徒を取得
        if user_info.get('role') == 'admin':
            user_school = user_info.get('school')
            if not user_school:
                return dbc.Alert("ユーザーに校舎が設定されていません。", color="danger")
            conn = sqlite3.connect(DATABASE_FILE)
            students_df = pd.read_sql_query(
                "SELECT id, name FROM students WHERE school = ?", conn, params=(user_school,)
            )
            conn.close()
            students = students_df.to_dict('records')
        # 一般ユーザーの場合は担当生徒のみ取得
        else:
            user_id = user_info.get('id')
            if not user_id:
                 return dbc.Alert("ユーザー情報が不正です。", color="danger")
            students = get_assigned_students_for_user(user_id)


        if not students:
            message = "担当の生徒が登録されていません。" if user_info.get('role') != 'admin' else "この校舎には生徒が登録されていません。"
            return dbc.Alert(message, color="info")

        return dcc.Dropdown(
            id='student-dropdown',
            options=[{'label': s['name'], 'value': s['id']} for s in students],
            placeholder="生徒を選択...",
            value=selected_student_id
        )
    # --- ★★★ ここまで修正 ★★★

    @app.callback(
        [Output('subject-tabs-container', 'children'),
         Output('dashboard-actions-container', 'children'),
         Output('dashboard-content-container', 'children')],
        Input('student-selection-store', 'data'),
        [State('url', 'pathname'),
         State('auth-store', 'data')]
    )
    def update_dashboard_on_student_select(student_id, pathname, user_info):
        """生徒が選択されたら、タブ、アクションボタン、初期コンテンツを生成する"""
        if not student_id or pathname != '/':
            # 生徒が選択されていない場合は「How to use」を表示
            return None, None, create_welcome_layout()

        # --- 生徒選択時の処理 ---
        student_info = get_student_info_by_id(student_id)
        subjects = get_subjects_for_student(student_id)
        
        all_tabs = [dbc.Tab(label="総合", tab_id="総合")]
        if subjects:
            all_tabs.extend([dbc.Tab(label=subject, tab_id=subject) for subject in subjects])

        tabs = dbc.Tabs(all_tabs, id="subject-tabs", active_tab="総合")
        
        action_buttons = []
        # 変更箇所: can_access_studentはメイン講師か管理者かを判定するため、ここでは役割で判定
        if user_info.get('role') == 'admin' or user_info.get('username') in student_info.get('main_instructors', []):
            action_buttons.append(dbc.Button("進捗を更新", id="bulk-register-btn", color="primary", outline=True))
        
        action_buttons.append(dbc.Button("PDFレポート", id="download-report-btn", color="info", outline=True, className="ms-2"))

        actions = dbc.ButtonGroup(action_buttons)

        # 初期表示として「総合」タブの内容を生成
        initial_content = generate_dashboard_content(student_id, '総合')

        return tabs, actions, initial_content

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