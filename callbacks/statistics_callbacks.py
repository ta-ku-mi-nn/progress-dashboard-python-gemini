# callbacks/statistics_callbacks.py

from dash import Input, Output, State, dcc
import dash_bootstrap_components as dbc
from data.nested_json_processor import get_student_level_statistics, get_all_subjects
from charts.chart_generator import create_level_statistics_chart

def register_statistics_callbacks(app):
    """統計ページのコールバックを登録する"""

    # 科目フィルターの選択肢を更新する
    @app.callback(
        Output('statistics-subject-filter', 'options'),
        Input('url', 'pathname')
    )
    def update_subject_filter_options(pathname):
        if pathname == '/statistics':
            subjects = get_all_subjects()
            return [{'label': s, 'value': s} for s in subjects]
        return []

    # 統計グラフを更新する
    @app.callback(
        Output('statistics-content-container', 'children'),
        Input('statistics-subject-filter', 'value'),
        State('auth-store', 'data')
    )
    def update_statistics_content(selected_subject, user_info):
        if not selected_subject or not user_info:
            return dbc.Alert("科目を選択してください。", color="info")

        school = user_info.get('school')
        if not school:
            return dbc.Alert("校舎情報が見つかりません。", color="danger")

        stats_data = get_student_level_statistics(school)

        fig = create_level_statistics_chart(stats_data, selected_subject)

        return dcc.Graph(figure=fig)