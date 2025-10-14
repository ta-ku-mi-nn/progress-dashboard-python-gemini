# callbacks/report_callbacks.py

from dash import Input, Output, State, html, no_update
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.io as pio
import base64
from flask import render_template_string # Flaskの機能を使います

from data.nested_json_processor import get_subjects_for_student, get_student_info_by_id, get_past_exam_results_for_student
from callbacks.progress_callbacks import generate_dashboard_content

def register_report_callbacks(app):
    """レポートHTMLを生成し、別タブで開いて印刷するコールバックを登録します。"""

    # 1. 「レポート印刷」ボタンでレポート用HTMLを生成し、Storeに保存する
    @app.callback(
        Output('report-content-store', 'data'),
        Input('print-report-btn', 'n_clicks'),
        State('student-selection-store', 'data'),
        prevent_initial_call=True
    )
    def generate_report_html(n_clicks, student_id):
        if not n_clicks or not student_id:
            return no_update

        student_info = get_student_info_by_id(student_id)
        student_name = student_info.get('name', '不明な生徒')
        
        subjects = get_subjects_for_student(student_id)
        all_content_ids = ["総合"] + subjects + ["過去問"]
        
        report_pages_components = []
        for i, content_id in enumerate(all_content_ids):
            page_style = {'page-break-after': 'always' if i < len(all_content_ids) - 1 else 'avoid'}
            
            content = None
            if content_id == "過去問":
                # generate_past_exam_table_for_reportを呼び出す
                content = generate_past_exam_table_for_report(student_id)
            else:
                content = generate_dashboard_content(student_id, content_id)
            
            if content:
                report_pages_components.append(html.Div([
                    html.H2(f"レポート: {content_id}", className="print-header"),
                    content
                ], style=page_style))

        # DashコンポーネントをHTML文字列に変換
        # この処理のために render_template_string を使用します
        from dash.development.base_component import Component
        import json
        
        def dash_component_to_html(component):
            if isinstance(component, str):
                return component
            if hasattr(component, "to_plotly_json"):
                return render_template_string(
                    f"{{% extends 'dash_component.html' %}}{{% block component %}}{json.dumps(component.to_plotly_json())}{{% endblock %}}",
                    json=json
                )
            return ""
            
        final_html_parts = [dash_component_to_html(part) for part in report_pages_components]

        # 完全なHTMLページを作成
        full_html = f"""
        <!DOCTYPE html>
        <html>
            <head>
                <title>{student_name}さん レポート</title>
                <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css">
                <link rel="stylesheet" href="/assets/printable.css">
            </head>
            <body>
                <div class="container-fluid">
                    <div id="report-header" class="my-4">
                        <h1>{student_name}さん の学習進捗レポート</h1>
                        <p>内容を確認し、コメントを入力してから印刷してください。</p>
                        <button onclick="window.print()" class="btn btn-success btn-lg mt-2">
                            <i class="fas fa-print me-2"></i>この内容を印刷
                        </button>
                    </div>
                    {''.join(final_html_parts)}
                    <div id="comment-section">
                        <h4 class="mt-4">特記事項・コメント</h4>
                        <textarea placeholder="この欄に入力した内容は、そのままレポートに印刷されます..." rows="8" class="form-control mb-4"></textarea>
                    </div>
                </div>
            </body>
        </html>
        """
        return full_html


    # 2. StoreにHTMLが保存されたら、新しいタブでそれを開く
    app.clientside_callback(
        """
        function(report_html) {
            if (report_html) {
                var new_window = window.open();
                new_window.document.write(report_html);
                new_window.document.close();
            }
            return ""; // ダミー出力
        }
        """,
        Output('dummy-clientside-output', 'children'),
        Input('report-content-store', 'data'),
        prevent_initial_call=True
    )

def generate_past_exam_table_for_report(student_id):
    """(変更なし) レポート専用に過去問テーブルを直接生成する関数"""
    results = get_past_exam_results_for_student(student_id)
    if not results: return dbc.Alert("この生徒の過去問結果はまだありません。", color="info")
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
    table_df = df[['date', 'university_name', 'faculty_name', 'year', 'subject', '所要時間(分)', '正答率']]
    table_df.columns = ['日付', '大学名', '学部名', '年度', '科目', '所要時間(分)', '正答率']
    return dbc.Table.from_dataframe(table_df, striped=True, bordered=True, hover=True, responsive=True)