# callbacks/main_callbacks.py

from dash import Input, Output, State, no_update

from data.nested_json_processor import get_all_schools, get_students_for_user

def register_main_callbacks(app, _data):
    """
    メインレイアウトの基本的なUI動作に関連するコールバックを登録します。
    """

    # --- ドロップダウンの選択肢を生成するコールバック (変更なし) ---
    @app.callback(
        Output('school-dropdown', 'options'),
        Input('url', 'pathname')
    )
    def update_school_dropdown(_):
        schools = get_all_schools()
        return [{'label': school, 'value': school} for school in schools]

    @app.callback(
        Output('student-dropdown', 'options'),
        Input('school-dropdown', 'value'),
        State('auth-store', 'data')
    )
    def update_student_dropdown(selected_school, user_info):
        if not selected_school or not user_info:
            return []
        students_by_school = get_students_for_user(user_info)
        students_in_school = students_by_school.get(selected_school, [])
        return [{'label': student, 'value': student} for student in sorted(students_in_school)]

    # --- ★★★ ここから下を新規追加 ★★★ ---

    # --- 選択された校舎をセッションに保存 ---
    @app.callback(
        Output('school-selection-store', 'data'),
        Input('school-dropdown', 'value'),
        prevent_initial_call=True
    )
    def save_school_selection(school):
        return school

    # --- 選択された生徒をセッションに保存 ---
    @app.callback(
        Output('student-selection-store', 'data'),
        Input('student-dropdown', 'value'),
        prevent_initial_call=True
    )
    def save_student_selection(student):
        return student

    # --- ページ読み込み時に校舎の選択を復元 ---
    @app.callback(
        Output('school-dropdown', 'value'),
        Input('school-dropdown', 'options'), # optionsが読み込まれた後に実行
        State('school-selection-store', 'data')
    )
    def restore_school_selection(options, stored_school):
        if stored_school and any(opt['value'] == stored_school for opt in options):
            return stored_school
        return no_update

    # --- ページ読み込み/校舎変更時に生徒の選択を復元 ---
    @app.callback(
        Output('student-dropdown', 'value'),
        Input('student-dropdown', 'options'), # optionsが読み込まれた後に実行
        State('student-selection-store', 'data')
    )
    def restore_student_selection(options, stored_student):
        if stored_student and any(opt['value'] == stored_student for opt in options):
            return stored_student
        return no_update
        
    # --- (既存のナビゲーションバーのコールバックは変更なし) ---
    @app.callback(
        Output("navbar-collapse", "is_open"),
        Input("navbar-toggler", "n_clicks"),
        State("navbar-collapse", "is_open"),
    )
    def toggle_navbar_collapse(n, is_open):
        if n:
            return not is_open
        return is_open