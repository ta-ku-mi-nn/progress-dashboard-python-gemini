# callbacks/report_callbacks.py

from dash import Input, Output, State, html, dcc, no_update
import dash_bootstrap_components as dbc
import pandas as pd

# 必要な関数をインポート
from data.nested_json_processor import get_subjects_for_student, get_student_info_by_id, get_past_exam_results_for_student
from callbacks.progress_callbacks import generate_dashboard_content

def generate_past_exam_table_for_report(student_id):
    """レポート専用に過去問テーブルを直接生成する関数"""
    results = get_past_exam_results_for_student(student_id)
    if not results:
        return dbc.Alert("この生徒の過去問結果はまだありません。", color="info")

    df = pd.DataFrame(results)

    def calculate_percentage(row):
        correct, total = row['correct_answers'], row['total_questions']
        return f"{(correct / total * 100):.1f}%" if pd.notna(correct) and pd.notna(total) and total > 0 else ""
    df['正答率'] = df.apply(calculate_percentage, axis=1)

    def format_time(row):
        req, total = row['time_required'], row['total_time_allowed']
        if pd.notna(total): return f"{int(req)}/{int(total)}"
        return f"{int(req)}" if pd.notna(req) else ""
    df['所要時間(分)'] = df.apply(format_time, axis=1)
    
    # レポートに不要な「操作」列を削除
    table_df = df[['date', 'university_name', 'faculty_name', 'year', 'subject', '所要時間(分)', '正答率']]
    table_df.columns = ['日付', '大学名', '学部名', '年度', '科目', '所要時間(分)', '正答率']
    
    return dbc.Table.from_dataframe(table_df, striped=True, bordered=True, hover=True, responsive=True)


def register_report_callbacks(app):
    """レポートページの生成と印刷機能のコールバックを登録します。"""

    # 1. 「レポート印刷」ボタンで新しいタブを開く
    app.clientside_callback(
        """
        function(n_clicks, student_id) {
            // n_clicks > 0 は、アプリ起動時にコールバックが発火するのを防ぐため
            if (n_clicks > 0 && student_id) {
                window.open(`/report/${student_id}`);
            }
            return ""; // ダミー出力を返す
        }
        """,
        Output('dummy-clientside-output', 'children'), 
        Input('print-report-btn', 'n_clicks'),
        State('student-selection-store', 'data'),
        prevent_initial_call=True
    )

    # 2. レポートページが開かれたら、そのページのコンテンツを生成する
    @app.callback(
        Output('printable-report-content', 'children'),
        Input('url', 'pathname'),
        prevent_initial_call=True
    )
    def generate_report_content_for_page(pathname):
        if not pathname or not pathname.startswith('/report/'):
            return no_update
        
        try:
            student_id = int(pathname.split('/')[-1])
        except (ValueError, IndexError):
            return dbc.Alert("無効なURLです。", color="danger")

        subjects = get_subjects_for_student(student_id)
        all_content_ids = ["総合"] + subjects + ["過去問"]
        
        report_pages = []
        for i, content_id in enumerate(all_content_ids):
            page_style = {'page-break-after': 'always' if i < len(all_content_ids) - 1 else 'avoid'}
            
            if content_id == "過去問":
                content = generate_past_exam_table_for_report(student_id)
            else:
                content = generate_dashboard_content(student_id, content_id)
            
            # コンテンツがない場合はスキップ
            if content is None:
                continue

            report_pages.append(html.Div([
                html.H2(f"レポート: {content_id}", className="print-header"),
                content
            ], style=page_style))
            
        return report_pages

    # 3. レポートページの「この内容を印刷」ボタンで印刷ダイアログを開く
    app.clientside_callback(
        """
        function(n_clicks) {
            if (n_clicks > 0) {
                window.print();
            }
            return window.dash_clientside.no_update;
        }
        """,
        Output('final-print-btn', 'n_clicks', allow_duplicate=True),
        Input('final-print-btn', 'n_clicks'),
        prevent_initial_call=True
    )