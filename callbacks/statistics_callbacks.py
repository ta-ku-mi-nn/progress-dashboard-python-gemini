# callbacks/statistics_callbacks.py

from dash import Input, Output, State, dcc, no_update
import dash_bootstrap_components as dbc
from data.nested_json_processor import (
    get_student_level_statistics, get_all_subjects,
    get_all_schools, get_all_grades
)
from charts.chart_generator import create_level_statistics_chart
from dash.exceptions import PreventUpdate

def register_statistics_callbacks(app):
    """統計ページのコールバックを登録する"""

    @app.callback(
        [Output('statistics-school-filter', 'options'),
         Output('statistics-school-filter', 'disabled'),
         Output('statistics-school-filter', 'value')], # ★ デフォルト値も設定
        Input('url', 'pathname'),
        State('auth-store', 'data')
    )
    def update_school_filter_options(pathname, user_info):
        if pathname != '/statistics' or not user_info:
            return [], True, None

        is_admin = user_info.get('role') == 'admin'
        all_schools = get_all_schools()
        options = [{'label': s, 'value': s} for s in all_schools]
        default_value = None

        if is_admin:
            # ★ 管理者は「すべての校舎」を追加
            options.insert(0, {'label': 'すべての校舎', 'value': 'all'})
            default_value = 'all' # デフォルトを「すべての校舎」に
            return options, False, default_value
        else:
            # 一般ユーザーは自校舎のみ表示 (選択不可)
            user_school = user_info.get('school')
            filtered_options = [{'label': s, 'value': s} for s in all_schools if s == user_school]
            default_value = user_school if user_school else None
            return filtered_options, True, default_value # ドロップダウンを無効化

    # (update_grade_filter_options は変更なし)
    @app.callback(
        Output('statistics-grade-filter', 'options'),
        Input('url', 'pathname')
    )
    def update_grade_filter_options(pathname):
        if pathname == '/statistics':
            grades = get_all_grades()
            # ★ 「その他」を除外する場合 (必要であれば)
            # grades = [g for g in grades if g != 'その他']
            return [{'label': g, 'value': g} for g in grades]
        return []

    # (update_subject_filter_options は変更なし)
    @app.callback(
        Output('statistics-subject-filter', 'options'),
        Input('url', 'pathname')
    )
    def update_subject_filter_options(pathname):
        if pathname == '/statistics':
            subjects = get_all_subjects()
            return [{'label': s, 'value': s} for s in subjects] if subjects else []
        return []

    @app.callback(
        Output('statistics-content-container', 'children'),
        [Input('statistics-school-filter', 'value'),
         Input('statistics-grade-filter', 'value'),
         Input('statistics-subject-filter', 'value')],
        State('auth-store', 'data')
    )
    def update_statistics_content(selected_school, selected_grade, selected_subject, user_info):
        # ★ selected_school のチェックを修正 ('all' も有効な値)
        if not selected_school or not selected_subject or not user_info:
             if not selected_school:
                  return dbc.Alert("校舎を選択してください。", color="info")
             if not selected_subject:
                  return dbc.Alert("科目を表示するには、まず科目を選択してください。", color="info")
             return dbc.Alert("ユーザー情報が見つかりません。", color="danger")

        # ★ 'all' が選択された場合、None を渡して全校舎を対象にする
        school_filter = None if selected_school == 'all' else selected_school
        # ★ get_student_level_statistics に school_filter を渡す
        stats_data = get_student_level_statistics(school_filter, selected_grade)

        # ★ タイトル表示を修正
        school_display_name = "すべての校舎" if selected_school == 'all' else selected_school
        grade_text = f" ({selected_grade})" if selected_grade else ""
        chart_title = f'<b>{school_display_name}{grade_text} - {selected_subject}</b> のレベル達成人数'

        fig = create_level_statistics_chart(stats_data, selected_subject)
        fig.update_layout(title_text=chart_title)

        # ★ データがない場合のメッセージを修正
        school_info = f"{school_display_name}{grade_text}"
        if not stats_data or selected_subject not in stats_data or all(v == 0 for v in stats_data[selected_subject].values()):
             return dbc.Alert(f"{school_info} には、「{selected_subject}」のレベル達成データがありません。", color="warning")

        return dcc.Graph(figure=fig)
