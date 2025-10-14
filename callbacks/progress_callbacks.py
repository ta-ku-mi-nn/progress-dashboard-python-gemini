# callbacks/progress_callbacks.py

from dash import Input, Output, State, dcc, html, no_update, callback_context
import dash_bootstrap_components as dbc
import pandas as pd
from dash.exceptions import PreventUpdate

from data.nested_json_processor import get_student_progress_by_id, get_student_info_by_id, get_total_past_exam_time
from charts.chart_generator import create_progress_stacked_bar_chart, create_subject_achievement_bar

# ( ... create_welcome_layout と generate_dashboard_content は変更なし ... )
def create_welcome_layout():
    """初期画面に表示する「How to use」レイアウトを生成します。"""
    return dbc.Row(
        dbc.Col(
            dbc.Card(
                [
                    dbc.CardHeader(html.H4("ようこそ！学習進捗ダッシュボードへ", className="mb-0")),
                    dbc.CardBody([
                        html.P(
                            "このダッシュボードは、生徒一人ひとりの学習状況を可視化し、管理するためのツールです。",
                            className="lead",
                        ),
                        html.Hr(),
                        html.H5("基本的な使い方", className="mt-4"),
                        dbc.ListGroup(
                            [
                                dbc.ListGroupItem([
                                    html.Div(className="d-flex w-100 justify-content-start align-items-center", children=[
                                        html.I(className="fas fa-user-graduate fa-2x me-3 text-primary"),
                                        html.Div([
                                            html.H6("1. 生徒を選択する", className="mb-1"),
                                            html.P("まずは画面上部のドロップダウンメニューから、進捗を確認したい生徒を選択してください。", className="mb-1 small text-muted"),
                                        ])
                                    ])
                                ]),
                                dbc.ListGroupItem([
                                    html.Div(className="d-flex w-100 justify-content-start align-items-center", children=[
                                        html.I(className="fas fa-chart-line fa-2x me-3 text-success"),
                                        html.Div([
                                            html.H6("2. 学習進捗を確認する", className="mb-1"),
                                            html.P("生徒を選択すると、科目ごとの達成率や学習時間のグラフが表示されます。タブを切り替えることで、各科目の詳細な進捗も確認できます。", className="mb-1 small text-muted"),
                                        ])
                                    ])
                                ]),
                                dbc.ListGroupItem([
                                    html.Div(className="d-flex w-100 justify-content-start align-items-center", children=[
                                        html.I(className="fas fa-edit fa-2x me-3 text-info"),
                                        html.Div([
                                            html.H6("3. 進捗を更新する", className="mb-1"),
                                            html.P("「進捗を更新」ボタンから、学習計画の作成や変更、達成度の入力ができます。", className="mb-1 small text-muted"),
                                        ])
                                    ])
                                ]),
                                dbc.ListGroupItem([
                                    html.Div(className="d-flex w-100 justify-content-start align-items-center", children=[
                                        html.I(className="fas fa-book fa-2x me-3 text-warning"),
                                        html.Div([
                                            html.H6("4. 他の機能", className="mb-1"),
                                            html.P("ナビゲーションバーから「宿題管理」や「過去問管理」ページに移動できます。", className="mb-1 small text-muted"),
                                        ])
                                    ])
                                ]),
                            ],
                            flush=True,
                            className="mb-4",
                        ),
                        dbc.Alert(
                            "さあ、はじめましょう！まずは、上のドロップダウンから生徒を選択してください。",
                            color="primary",
                        ),
                    ]),
                ]
            ),
            width=12,
            lg=10,
            xl=8,
        ),
        justify="center",
        className="mt-5",
    )


def generate_dashboard_content(student_id, active_tab):
    """指定された生徒とタブに基づいてダッシュボードのコンテンツを生成する"""
    if not student_id or not active_tab:
        return None

    progress_data = get_student_progress_by_id(student_id)
    if not progress_data and active_tab != '総合':
        return dbc.Alert("この生徒の進捗データはまだありません。「進捗を更新」から作成してください。", color="info")

    if active_tab == '総合':
        all_records = []
        for subject, levels in progress_data.items():
            for level, books in levels.items():
                for book_name, details in books.items():
                    all_records.append({
                        'subject': subject, 'book_name': book_name,
                        'duration': details.get('所要時間', 0),
                        'is_planned': details.get('予定', False),
                        'is_done': details.get('達成済', False),
                        'completed_units': details.get('completed_units', 0),
                        'total_units': details.get('total_units', 1),
                    })
        
        past_exam_hours = get_total_past_exam_time(student_id)
        
        df_all = pd.DataFrame(all_records) if all_records else pd.DataFrame()
        
        summary_cards = create_summary_cards(df_all, past_exam_hours)
        
        if past_exam_hours > 0:
            past_exam_record = pd.DataFrame([{
                'subject': '過去問', 'book_name': '過去問演習',
                'duration': past_exam_hours,
                'is_planned': True, 'is_done': True,
                'completed_units': 1, 'total_units': 1,
            }])
            df_all = pd.concat([df_all, past_exam_record], ignore_index=True)

        if df_all.empty:
            return dbc.Alert("予定されている学習がありません。", color="info")

        stacked_bar_fig = create_progress_stacked_bar_chart(df_all, '全科目の合計学習時間')
        
        left_col = html.Div([
            dcc.Graph(figure=stacked_bar_fig, style={'height': '250px'}) if stacked_bar_fig else html.Div(),
            summary_cards
        ])
        
        bar_charts = []
        # is_planned が True の科目に絞り込んでからグラフを生成
        planned_subjects = df_all[df_all['is_planned'] == True]['subject'].unique()
        for subject in sorted([s for s in planned_subjects if s != '過去問']):
            fig = create_subject_achievement_bar(df_all, subject)
            bar_chart_component = dcc.Graph(
                figure=fig,
                config={'displayModeBar': False},
                id={'type': 'subject-achievement-bar', 'subject': subject}
            )
            bar_charts.append(dbc.Col(bar_chart_component, width=12, md=6, lg=4, className="mb-3"))
        right_col = dbc.Row(bar_charts, id="subject-charts-row") 
        
        return dbc.Row([
            dbc.Col(left_col, md=8),
            dbc.Col(right_col, md=4),
        ])
    else:
        if active_tab not in progress_data:
            return dbc.Alert(f"「{active_tab}」の進捗データがありません。", color="info")

        subject_records = []
        for level, books in progress_data[active_tab].items():
            for book_name, details in books.items():
                subject_records.append({
                    'book_name': book_name,
                    'duration': details.get('所要時間', 0),
                    'is_planned': details.get('予定', False),
                    'is_done': details.get('達成済', False),
                    'completed_units': details.get('completed_units', 0),
                    'total_units': details.get('total_units', 1),
                })
        
        df_subject = pd.DataFrame(subject_records)
        fig = create_progress_stacked_bar_chart(df_subject, f'<b>{active_tab}</b> の学習進捗')
        summary_cards = create_summary_cards(df_subject)

        left_col = html.Div([
            dcc.Graph(figure=fig, style={'height': '250px'}) if fig else dbc.Alert("予定されている学習がありません。", color="info"),
            summary_cards
        ])

        student_info = get_student_info_by_id(student_id)
        right_col = create_progress_table(progress_data, student_info, active_tab)
        
        return dbc.Row([
            dbc.Col(left_col, md=8),
            dbc.Col(right_col, md=4),
        ])

# ★★★ 修正点: `register_progress_callbacks` のコールバックを修正 ★★★
def register_progress_callbacks(app):
    """進捗表示に関連するコールバックを登録します。"""

    @app.callback(
        Output('dashboard-content-container', 'children', allow_duplicate=True),
        [Input('subject-tabs', 'active_tab'),
         Input('toast-trigger', 'data')],
        State('student-selection-store', 'data'),
        prevent_initial_call=True
    )
    def update_dashboard_on_tab_click_or_save(active_tab, toast_data, student_id):
        ctx = callback_context
        if not ctx.triggered:
            raise PreventUpdate

        # 保存処理（plan）によるトリガーでなければ更新しない
        if ctx.triggered_id == 'toast-trigger':
            if not toast_data or toast_data.get('source') != 'plan':
                raise PreventUpdate

        return generate_dashboard_content(student_id, active_tab)

def create_summary_cards(df, past_exam_hours=0):
    """進捗データのDataFrameからサマリーカードを生成するヘルパー関数"""
    df_planned = df[df['is_planned']].copy()
    if df_planned.empty and past_exam_hours == 0:
        return None

    df_planned['achieved_duration'] = df_planned.apply(
        lambda row: row['duration'] * (row.get('completed_units', 0) / row.get('total_units', 1)) if row.get('total_units', 1) > 0 else 0,
        axis=1
    )
    
    planned_hours = df_planned['duration'].sum()
    achieved_reference_hours = df_planned['achieved_duration'].sum()
    
    total_achieved_hours = achieved_reference_hours + past_exam_hours
    
    achievement_rate = (achieved_reference_hours / planned_hours * 100) if planned_hours > 0 else 0
    completed_books = df_planned[df_planned['is_done']].shape[0]
    
    cards = dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([html.H5(f"{total_achieved_hours:.1f} h", className="card-title"), html.P("達成済時間", className="card-text small text-muted")])), width=6, className="mb-3"),
        dbc.Col(dbc.Card(dbc.CardBody([html.H5(f"{planned_hours:.1f} h", className="card-title"), html.P("予定総時間（参考書）", className="card-text small text-muted")])), width=6, className="mb-3"),
        dbc.Col(dbc.Card(dbc.CardBody([html.H5(f"{achievement_rate:.1f} %", className="card-title"), html.P("達成率（参考書）", className="card-text small text-muted")])), width=6, className="mb-3"),
        dbc.Col(dbc.Card(dbc.CardBody([html.H5(f"{completed_books} 冊", className="card-title"), html.P("完了参考書", className="card-text small text-muted")])), width=6, className="mb-3"),
    ], className="mt-4")
    
    return cards

def create_progress_table(progress_data, student_info, active_tab):
    """進捗詳細テーブルのコンポーネントを生成するヘルパー関数"""
    subject_data = progress_data.get(active_tab, {})
    if not subject_data:
        return None

    table_header = [html.Thead(html.Tr([
        html.Th("レベル"), html.Th("参考書名"), html.Th("ステータス")
    ]))]

    table_rows = []
    for level, books in sorted(subject_data.items()):
        for book_name, details in books.items():
            if not details.get('予定'):
                continue

            status_badge = dbc.Badge(
                "完了", color="success") if details.get('達成済') else (
                dbc.Badge("学習中", color="primary") if details.get('予定') else 
                dbc.Badge("未着手", color="secondary")
            )
            
            table_rows.append(html.Tr([
                html.Td(level),
                html.Td(book_name),
                html.Td(status_badge)
            ]))
    
    if not table_rows:
        return dbc.Alert("予定されている学習はありません。", color="info", className="mt-4")
        
    table_body = [html.Tbody(table_rows)]
    
    student_name = student_info.get('name', 'N/A')
    main_instructors = ", ".join(student_info.get('main_instructors', []))
    
    return html.Div([
        html.H4(f"{active_tab} の進捗詳細"),
        html.P(f"（{student_name}さん / メイン講師: {main_instructors}）", className="text-muted small"),
        dbc.Table(table_header + table_body, bordered=False, striped=True, hover=True, responsive=True, className="mt-3")
    ])