# components/report_layout.py
from dash import dcc, html
import dash_bootstrap_components as dbc

def create_report_layout(student_name):
    """印刷専用ページのレイアウトを生成する"""
    return dbc.Container([
        # 画面上部に表示されるヘッダー
        html.Div([
            html.H2(f"{student_name}さん の学習進捗レポート"),
            html.P("内容を確認し、コメントを入力してから印刷してください。"),
            dbc.Button(
                [html.I(className="fas fa-print me-2"), "この内容を印刷"],
                id="final-print-btn",
                color="success",
                size="lg",
                className="mt-2"
            ),
        ], id="report-header", className="my-4"),

        # 実際のレポートコンテンツ（ここに各タブの内容が挿入される）
        html.Div(id="printable-report-content"),

        # コメント入力エリア
        html.Div([
            html.H4("特記事項・コメント", className="mt-4"),
            dbc.Textarea(
                id="report-comment-input",
                placeholder="この欄に入力した内容は、そのままレポートに印刷されます...",
                rows=8,
                className="mb-4"
            ),
        ], id="comment-section"),
        
    ], fluid=True)