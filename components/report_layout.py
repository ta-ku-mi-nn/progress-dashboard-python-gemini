# components/report_layout.py
from dash import dcc, html
import dash_bootstrap_components as dbc

def create_report_layout(student_name):
    """印刷専用ページのレイアウトを生成する（整理・最終版）"""

    # 1. 操作用ヘッダー（印刷時は非表示）
    action_header = html.Div([
        dbc.Container([
            dbc.Row([
                dbc.Col([
                    html.H3("レポート作成モード", className="text-primary"),
                    html.P("ブラウザの印刷設定で「余白：なし」にすると、プレビュー通りに印刷されます。"),
                ], width=8),
                dbc.Col([
                    dbc.Button(
                        [html.I(className="fas fa-print me-2"), "この内容を印刷する"],
                        id="final-print-btn", color="primary", size="lg", className="w-100 shadow"
                    ),
                ], width=4, className="d-flex align-items-center"),
            ])
        ], className="py-3")
    ], id="report-header", className="bg-light border-bottom mb-4")

    # 2. 印刷コンテンツ（A4サイズに固定）
    printable_content = html.Div([
        # 【1ページ目】
        html.Div([
            html.Div([
                dbc.Row([
                    dbc.Col(html.H1("学習進捗報告書", className="report-title"), width=12),
                ], className="mb-2"),
                html.Hr(className="report-hr"),
                dbc.Row([
                    dbc.Col([
                        html.Div([
                            html.Span("生徒氏名：", className="label"),
                            html.Span(f"{student_name} 様", className="value-name"),
                        ], className="student-info-box"),
                    ], width=6),
                    dbc.Col([
                        html.P(id="report-creation-date", className="text-end mb-0"),
                        html.P("発行：進捗管理システム", className="text-end small text-muted"),
                    ], width=6),
                ], className="mb-4 align-items-end"),
            ], className="report-header-section"),

            html.H4("■ 学習進捗サマリー", className="section-title"),
            # IDを囲うDivに余白を持たせます
            dcc.Loading(html.Div(id="report-dashboard-content", className="dashboard-print-container")),
            
        ], className="printable-page"),

        # 【2ページ目】
        html.Div([
            dbc.Row([
                dbc.Col([
                    html.H4("■ 過去問実施記録", className="section-title"),
                    dcc.Loading(html.Div(id="report-past-exam-content")),
                ], width=7),
                dbc.Col([
                    html.H4("■ 指導・特記事項", className="section-title"),
                    dbc.Textarea(id="report-comment-input", rows=15, className="no-print mb-2"),
                    html.Div(id="printable-comment-output", className="comment-print-box")
                ], width=5),
            ]),
        ], className="printable-page"),
    ], id="report-content-area", className="printable-container")

    # 修正：重複を排除し、action_headerとprintable_contentのみを返す
    return html.Div([
        action_header,
        printable_content
    ], style={'backgroundColor': '#f4f4f4', 'minHeight': '100vh'})