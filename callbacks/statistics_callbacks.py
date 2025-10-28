# callbacks/statistics_callbacks.py (全体)

from dash import Input, Output, State, dcc, no_update
import dash_bootstrap_components as dbc
from data.nested_json_processor import (
    get_student_level_statistics, get_all_subjects,
    get_all_schools, get_all_grades # ★ get_all_schools, get_all_grades をインポート
)
from charts.chart_generator import create_level_statistics_chart
from dash.exceptions import PreventUpdate # ★ PreventUpdate をインポート

def register_statistics_callbacks(app):
    """統計ページのコールバックを登録する"""

    # ★ 校舎フィルターの選択肢と状態を更新
    @app.callback(
        [Output('statistics-school-filter', 'options'),
         Output('statistics-school-filter', 'disabled')],
        Input('url', 'pathname'), # ページ読み込み時に発火
        State('auth-store', 'data')
    )
    def update_school_filter_options(pathname, user_info):
        if pathname != '/statistics' or not user_info:
            return [], True

        is_admin = user_info.get('role') == 'admin'
        all_schools = get_all_schools()
        options = [{'label': s, 'value': s} for s in all_schools]

        if is_admin:
            # 管理者は全校舎を選択可能
            return options, False
        else:
            # 一般ユーザーは自校舎のみ表示 (選択不可)
            user_school = user_info.get('school')
            filtered_options = [{'label': s, 'value': s} for s in all_schools if s == user_school]
            return filtered_options, True # ドロップダウンを無効化

    # ★ 学年フィルターの選択肢を更新
    @app.callback(
        Output('statistics-grade-filter', 'options'),
        Input('url', 'pathname') # ページ読み込み時に発火
    )
    def update_grade_filter_options(pathname):
        if pathname == '/statistics':
            grades = get_all_grades()
            return [{'label': g, 'value': g} for g in grades]
        return []

    # 科目フィルターの選択肢を更新 (変更なし)
    @app.callback(
        Output('statistics-subject-filter', 'options'),
        Input('url', 'pathname')
    )
    def update_subject_filter_options(pathname):
        if pathname == '/statistics':
            subjects = get_all_subjects()
            # 科目が取得できなかった場合も考慮
            return [{'label': s, 'value': s} for s in subjects] if subjects else []
        return []

    # 統計グラフを更新する (★ フィルター値を取得・使用するように修正)
    @app.callback(
        Output('statistics-content-container', 'children'),
        [Input('statistics-school-filter', 'value'),
         Input('statistics-grade-filter', 'value'),
         Input('statistics-subject-filter', 'value')],
        State('auth-store', 'data') # user_info は State のままでOK
    )
    def update_statistics_content(selected_school, selected_grade, selected_subject, user_info):
        # ★ selected_school も必須チェックに追加
        if not selected_school or not selected_subject or not user_info:
             # ★ selected_subject が None の場合も考慮
             if not selected_school:
                  return dbc.Alert("校舎を選択してください。", color="info")
             if not selected_subject:
                  return dbc.Alert("科目を表示するには、まず科目を選択してください。", color="info")
             # user_info がない場合は通常発生しないはずだが念のため
             return dbc.Alert("ユーザー情報が見つかりません。", color="danger")


        # ★ get_student_level_statistics に校舎と学年フィルターを渡す
        stats_data = get_student_level_statistics(selected_school, selected_grade)

        # ★ 選択された校舎と学年（任意）をタイトルに追加
        grade_text = f" ({selected_grade})" if selected_grade else ""
        chart_title = f'<b>{selected_school}{grade_text} - {selected_subject}</b> のレベル達成人数'

        fig = create_level_statistics_chart(stats_data, selected_subject)
        # グラフタイトルを動的に設定
        fig.update_layout(title_text=chart_title)


        # データがない場合のメッセージを改善
        if not stats_data or selected_subject not in stats_data or all(v == 0 for v in stats_data[selected_subject].values()):
             grade_info = f" ({selected_grade})" if selected_grade else ""
             return dbc.Alert(f"{selected_school}{grade_info} には、「{selected_subject}」のレベル達成データがありません。", color="warning")


        return dcc.Graph(figure=fig)