# callbacks/report_callbacks.py

from dash import Input, Output, State, html, dcc, no_update
import dash_bootstrap_components as dbc

# ... (必要なインポート) ...
from data.nested_json_processor import get_subjects_for_student
from callbacks.progress_callbacks import generate_dashboard_content
from components.past_exam_layout import create_past_exam_layout

def register_report_callbacks(app):
    """レポートページの生成と印刷機能のコールバックを登録します。"""

    # 1. ダッシュボードの「レポート印刷」ボタンで新しいタブを開く
    app.clientside_callback(
        """
        function(n_clicks, student_id) {
            if (!n_clicks || !student_id) {
                return window.dash_clientside.no_update;
            }
            // /report/<student_id> というURLを新しいタブで開く
            window.open(`/report/${student_id}`);
            return window.dash_clientside.no_update;
        }
        """,
        Output('print-report-btn', 'n_clicks', allow_duplicate=True),
        Input('print-report-btn', 'n_clicks'),
        State('student-selection-store', 'data'),
        prevent_initial_call=True
    )

    # 2. レポートページが開かれたら、そのページのコンテンツを生成する
    app.callback(
        Output('printable-report-content', 'children'),
        Input('url', 'pathname'), # URLの変更をトリガーにする
        prevent_initial_call=True
    )
    def generate_report_content_for_page(pathname):
        if not pathname.startswith('/report/'):
            return no_update
        
        student_id = int(pathname.split('/')[-1])
        subjects = get_subjects_for_student(student_id)
        all_content_ids = ["総合"] + subjects + ["過去問"]
        
        report_pages = []
        for i, content_id in enumerate(all_content_ids):
            page_style = {'page-break-after': 'always' if i < len(all_content_ids) - 1 else 'avoid'}
            if content_id == "過去問":
                content = create_past_exam_layout()
            else:
                content = generate_dashboard_content(student_id, content_id)
            
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