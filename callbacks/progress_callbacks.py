# callbacks/progress_callbacks.py

from dash import Input, Output, State, dcc, html, no_update
import dash_bootstrap_components as dbc
import pandas as pd

from data.nested_json_processor import get_student_progress_by_id, get_student_info_by_id
# --- ★★★ ここから修正 ★★★ ---
# インポートする関数名を変更
from charts.chart_generator import create_progress_stacked_bar_chart, create_subject_achievement_bar
# --- ★★★ ここまで修正 ★★★ ---

def register_progress_callbacks(app):
    """進捗表示に関連するコールバックを登録します。"""

    @app.callback(
        Output('dashboard-content-container', 'children'),
        Input('subject-tabs', 'active_tab'),
        State('student-selection-store', 'data')
    )
    def update_dashboard_layout(active_tab, student_id):
        """
        選択されたタブに応じて、グラフやテーブルの2カラムレイアウトを生成する。
        """
        if not student_id or not active_tab:
            return None

        progress_data = get_student_progress_by_id(student_id)
        if not progress_data:
            return dbc.Alert("進捗データがありません。", color="info")

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
            
            if not all_records:
                return dbc.Alert("予定されている学習がありません。", color="info")

            df_all = pd.DataFrame(all_records)
            
            stacked_bar_fig = create_progress_stacked_bar_chart(df_all, '全科目の合計学習時間')
            summary_cards = create_summary_cards(df_all)
            
            left_col = html.Div([
                dcc.Graph(figure=stacked_bar_fig, style={'height': '250px'}) if stacked_bar_fig else html.Div(),
                summary_cards
            ])

            bar_charts = []
            for subject in sorted(df_all['subject'].unique()):
                # --- ★★★ ここから修正 ★★★ ---
                # 呼び出す関数名を変更
                bar_chart = create_subject_achievement_bar(df_all, subject)
                bar_charts.append(dbc.Col(bar_chart, width=12, md=6, lg=4, className="mb-3"))
                # --- ★★★ ここまで修正 ★★★ ---
            right_col = dbc.Row(bar_charts)
            
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

def create_summary_cards(df):
    """進捗データのDataFrameからサマリーカードを生成するヘルパー関数"""
    df_planned = df[df['is_planned']].copy()
    if df_planned.empty:
        return None

    df_planned['achieved_duration'] = df_planned.apply(
        lambda row: row['duration'] * (row.get('completed_units', 0) / row.get('total_units', 1)) if row.get('total_units', 1) > 0 else 0,
        axis=1
    )
    
    planned_hours = df_planned['duration'].sum()
    achieved_hours = df_planned['achieved_duration'].sum()
    achievement_rate = (achieved_hours / planned_hours * 100) if planned_hours > 0 else 0
    completed_books = df_planned[df_planned['is_done']].shape[0]
    
    cards = dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([html.H5(f"{achieved_hours:.1f} h", className="card-title"), html.P("達成済時間", className="card-text small text-muted")])), width=6, className="mb-3"),
        dbc.Col(dbc.Card(dbc.CardBody([html.H5(f"{planned_hours:.1f} h", className="card-title"), html.P("予定総時間", className="card-text small text-muted")])), width=6, className="mb-3"),
        dbc.Col(dbc.Card(dbc.CardBody([html.H5(f"{achievement_rate:.1f} %", className="card-title"), html.P("達成率", className="card-text small text-muted")])), width=6, className="mb-3"),
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