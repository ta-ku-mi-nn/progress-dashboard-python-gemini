from dash import Input, Output, State, dcc
import dash_bootstrap_components as dbc

# 新しいデータ構造に対応したヘルパー関数をインポート
from data.nested_json_processor import get_students_for_user

def register_main_callbacks(app, data):
    """
    メインレイアウトの基本的なUI動作に関連するコールバックを登録します。

    Args:
        app (dash.Dash): Dashアプリケーションインスタンス。
        data (dict): アプリケーション起動時に読み込まれた全データ。
    """

    # 校舎ドロップダウンの選択肢を生成するコールバック
    @app.callback(
        Output('school-dropdown', 'options'),
        Input('url', 'pathname') # ページ読み込み時に一度だけ実行
    )
    def update_school_dropdown(_):
        schools = list(data.keys())
        return [{'label': school, 'value': school} for school in schools]

    # 生徒ドロップダウンの選択肢を生成するコールバック
    @app.callback(
        Output('student-dropdown', 'options'),
        [Input('school-dropdown', 'value')],
        [State('auth-store', 'data')] # ログイン中のユーザー情報を利用
    )
    def update_student_dropdown(selected_school, user_info):
        """
        校舎が選択されたら、ログインユーザーが閲覧可能な生徒のリストを生成する。
        """
        if not selected_school or not user_info:
            return []
        
        # ログインユーザーがアクセスできる生徒のリストを取得
        students = get_students_for_user(data, selected_school, user_info)
        
        return [{'label': student, 'value': student} for student in sorted(students)]

    # ナビゲーションバーのトグル機能
    @app.callback(
        Output("navbar-collapse", "is_open"),
        [Input("navbar-toggler", "n_clicks")],
        [State("navbar-collapse", "is_open")],
    )
    def toggle_navbar_collapse(n, is_open):
        if n:
            return not is_open
        return is_open