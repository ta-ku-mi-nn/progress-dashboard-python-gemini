# callbacks/progress_callbacks.py

import json
import pandas as pd
from dash import Input, Output, State, html, dcc, callback_context, no_update, ALL
import dash_bootstrap_components as dbc

from data.nested_json_processor import get_student_progress, get_student_info
from charts.chart_generator import create_progress_stacked_bar_chart, create_subject_progress_pie_chart

def calculate_true_duration(df, student_info):
    """真所要時間を計算してDataFrameに新しい列として追加する"""
    student_deviation = student_info.get('deviation_value')
    if not student_deviation:
        df['true_duration'] = df['所要時間']
        return df

    standard_hensachi = {'基礎徹底': 50, '日大': 60, 'MARCH': 70, '早慶': 75}
    
    def calc_row(row):
        level = row['ルートレベル']
        base_duration = row['所要時間']
        standard_dev = standard_hensachi.get(level, student_deviation)
        
        adjustment_factor = 1 + 0.025 * (standard_dev - student_deviation)
        return max(0, base_duration * adjustment_factor)

    df['true_duration'] = df.apply(calc_row, axis=1)
    return df

def register_progress_callbacks(app):
    """進捗グラフの表示に関連するコールバックを登録します。"""

    @app.callback(
        [Output('cumulative-progress-container', 'children'),
         Output('subject-pie-charts-container', 'children')],
        Input('student-dropdown', 'value'),
        State('school-dropdown', 'value')
    )
    def update_main_dashboard(selected_student, selected_school):
        if not selected_student or not selected_school:
            return html.Div("生徒を選択してください。"), html.Div()

        student_progress = get_student_progress(selected_school, selected_student)
        student_info = get_student_info(selected_school, selected_student)
        if not student_progress:
            return html.Div(f"「{selected_student}」さんの進捗データが見つかりません。"), html.Div()

        records = []
        for subject, levels in student_progress.items():
            for level, books in levels.items():
                for book_name, details in books.items():
                    records.append({
                        '科目': subject, 'ルートレベル': level, 'book_name': book_name,
                        '所要時間': details.get('所要時間', 0),
                        '予定': details.get('予定', False),
                        'completed_units': details.get('completed_units', 0),
                        'total_units': details.get('total_units', 1)
                    })
        
        if not records:
            return html.Div("この生徒には登録されている参考書がありません。"), html.Div()

        df = pd.DataFrame(records)
        df = calculate_true_duration(df, student_info)
        planned_df = df[df['予定'] == True].copy()
        
        if planned_df.empty:
            return dbc.Alert("予定されている学習はありません。", color="info"), html.Div()

        planned_df['achieved_duration'] = planned_df.apply(lambda row: row['true_duration'] * (row['completed_units'] / row['total_units']) if row['total_units'] > 0 else 0, axis=1)
        planned_df['planned_duration'] = planned_df['true_duration'] - planned_df['achieved_duration']
        
        cumulative_chart = create_progress_stacked_bar_chart(planned_df, "全科目累計")
        cumulative_graph_div = dcc.Graph(figure=cumulative_chart) if cumulative_chart else dbc.Alert("予定されている学習はありません。", color="info")

        subjects = sorted(planned_df['科目'].unique())
        pie_charts = [dbc.Col(create_subject_progress_pie_chart(planned_df, subject), width=6, md=4, lg=3) for subject in subjects]
        
        return cumulative_graph_div, dbc.Row(pie_charts)

    @app.callback(
        Output('detailed-progress-view-container', 'children'),
        Input({'type': 'subject-pie-chart', 'subject': ALL}, 'clickData'),
        [State('school-dropdown', 'value'), State('student-dropdown', 'value')],
        prevent_initial_call=True
    )
    def display_detailed_chart(click_data, school, student):
        if not any(click_data) or not school or not student:
            return html.Div()

        ctx = callback_context
        subject_clicked = json.loads(ctx.triggered[0]['prop_id'].split('.')[0])['subject']
        
        student_progress = get_student_progress(school, student)
        student_info = get_student_info(school, student)

        # ★★★ ここが修正点です ★★★
        # 複雑な一行のリスト内包表記を、より安全な複数行のforループに書き換え
        records = []
        for s, lvls in student_progress.items():
            for l, bks in lvls.items():
                for b, d in bks.items():
                    record = {'科目': s, 'ルートレベル': l, 'book_name': b}
                    record.update(d)
                    records.append(record)
        
        df = pd.DataFrame(records)
        df = calculate_true_duration(df, student_info)
        subject_df = df[(df['科目'] == subject_clicked) & (df['予定'] == True)].copy()

        if subject_df.empty:
            return html.Div(f"{subject_clicked}には予定された学習がありません。")

        subject_df['total_units'] = subject_df['total_units'].replace(0, 1)
        subject_df['achieved_duration'] = subject_df['true_duration'] * (subject_df['completed_units'] / subject_df['total_units'])
        subject_df['planned_duration'] = subject_df['true_duration'] - subject_df['achieved_duration']
        
        detailed_chart = create_progress_stacked_bar_chart(subject_df, f"詳細: {subject_clicked}")
        
        total_hours = subject_df['true_duration'].sum()
        done_hours = subject_df['achieved_duration'].sum()
        achievement_rate = (done_hours / total_hours * 100) if total_hours > 0 else 0
        
        summary_cards = dbc.Row([
            dbc.Col(dbc.Card([dbc.CardHeader("予定時間"), dbc.CardBody(f"{total_hours:.1f} h")], color="primary", inverse=True)),
            dbc.Col(dbc.Card([dbc.CardHeader("達成時間"), dbc.CardBody(f"{done_hours:.1f} h")], color="success", inverse=True)),
            dbc.Col(dbc.Card([dbc.CardHeader("達成度"), dbc.CardBody(f"{achievement_rate:.1f} %")], color="info", inverse=True)),
        ], className="mt-3")

        return html.Div([dcc.Graph(figure=detailed_chart), summary_cards])