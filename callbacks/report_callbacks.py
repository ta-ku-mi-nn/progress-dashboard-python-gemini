# callbacks/report_callbacks.py

from dash import Input, Output, State, html, dcc, no_update
import dash_bootstrap_components as dbc
import pandas as pd
from datetime import datetime

from data.nested_json_processor import get_past_exam_results_for_student
from callbacks.progress_callbacks import generate_dashboard_content

def generate_past_exam_table_for_report(student_id):
    """レポート専用に過去問テーブルのDashコンポーネントを生成する"""
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
    
    table_df = df[['date', 'university_name', 'year', 'subject', '正答率']]
    table_df.columns = ['日付', '大学名', '年度', '科目', '正答率']
    
    return dbc.Table.from_dataframe(table_df, striped=True, bordered=True, hover=True, responsive=True, size='sm')

def register_report_callbacks(app):
    """レポートページの生成と印刷機能のコールバック"""

    # 1. ダッシュボードのボタンで新しいタブを開く
    app.clientside_callback(
        """
        function(n_clicks, student_id) {
            if (n_clicks > 0 && student_id) {
                window.open(`/report/${student_id}`);
            }
            return ""; 
        }
        """,
        Output('dummy-clientside-output', 'children'),
        Input('print-report-btn', 'n_clicks'),
        State('student-selection-store', 'data'),
        prevent_initial_call=True
    )

    # 2. レポートページが開かれたら、内容を生成して各セクションに配置する
    @app.callback(
        [Output('report-dashboard-content', 'children'),
         Output('report-past-exam-content', 'children'),
         Output('report-creation-date', 'children')],
        Input('url', 'pathname')
    )
    def generate_custom_report_content(pathname):
        if not pathname or not pathname.startswith('/report/'):
            return no_update, no_update, no_update
        try:
            student_id = int(pathname.split('/')[-1])
        except (ValueError, IndexError):
            return dbc.Alert("無効なURLです。", color="danger"), "", ""

        # --- 各パーツを生成 ---
        dashboard_content = generate_dashboard_content(student_id, '総合')
        past_exam_table = generate_past_exam_table_for_report(student_id)
        creation_date = f"作成日: {datetime.now().strftime('%Y年%m月%d日')}"
        
        return dashboard_content, past_exam_table, creation_date

    # 3. レポートページの印刷ボタンで印刷ダイアログを開く
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

    # --- ★★★ ここから修正 ★★★ ---
    # 4. コメント入力欄の高さ自動調整
    app.clientside_callback(
        """
        function(value) {
            const el = document.getElementById('report-comment-input');
            if (el) {
                // 一時的に高さをリセットして、スクロールハイトを正しく計算させる
                el.style.height = 'auto';
                // スクロールハイト（内容の高さ）に行の高さ（おおよそ24px）を加える
                const newHeight = el.scrollHeight + 24;
                el.style.height = newHeight + 'px';
            }
            // DashはOutputへの何らかの返り値を期待するが、DOMを直接操作しているので
            // no_updateを返す
            return window.dash_clientside.no_update;
        }
        """,
        Output('dummy-clientside-output', 'children', allow_duplicate=True), # ダミーのOutput
        Input('report-comment-input', 'value'),
        prevent_initial_call=True
    )
    # --- ★★★ ここまで修正 ★★★ ---