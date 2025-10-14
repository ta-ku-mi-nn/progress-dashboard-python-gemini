# components/report_layout.py
from dash import dcc, html
import dash_bootstrap_components as dbc
from datetime import datetime

def create_report_layout(student_name):
    """印刷専用ページのレイアウトを生成する"""
    
    # --- ヘッダー部分 ---
    report_header = dbc.Row([
        # 左揃えのタイトル
        dbc.Col(html.H2("学習進捗レポート"), width="auto", className="me-auto align-self-end"),
        # 右揃えの情報
        dbc.Col([
            html.P(id="report-creation-date", className="mb-0 text-muted"),
            html.P(f"生徒名: {student_name}", className="mb-0 text-muted"),
        ], width="auto", className="text-end"),
    ], align="center", className="mb-4")

    # --- 印刷ボタンや説明を含む操作エリア ---
    action_header = html.Div([
        html.H1(f"{student_name}さん の学習進捗レポート"),
        html.P("内容を確認し、コメントを入力してから印刷してください。"),
        dbc.Button(
            [html.I(className="fas fa-print me-2"), "この内容を印刷"],
            id="final-print-btn", color="success", size="lg", className="mt-2"
        ),
    ], id="report-header", className="my-4")

    # --- メインコンテンツ部分 ---
    main_content = dcc.Loading(html.Div(id="report-dashboard-content"))

    # --- 下段部分（過去問とコメント） ---
    bottom_section = dbc.Row([
        # 左列：過去問情報
        dbc.Col([
            html.H4("過去問情報"),
            dcc.Loading(html.Div(id="report-past-exam-content")),
        ], md=7),
        # 右列：コメント欄
        dbc.Col([
            html.H4("特記事項・コメント"),
            dbc.Textarea(
                id="report-comment-input",
                placeholder="この欄に入力した内容は、そのままレポートに印刷されます...",
                rows=15, className="mb-4"
            ),
        ], md=5),
    ], className="mt-4")

    return dbc.Container([
        action_header,
        html.Hr(),
        report_header,
        main_content,
        bottom_section,
    ], fluid=True, style={'backgroundColor': 'white'})