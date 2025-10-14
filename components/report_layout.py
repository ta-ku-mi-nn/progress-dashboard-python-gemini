# components/report_layout.py
from dash import dcc, html
import dash_bootstrap_components as dbc
from datetime import datetime

def create_report_layout(student_name):
    """印刷専用ページのレイアウトを生成する"""
    
    # 印刷時には非表示になる、操作用のヘッダー
    action_header = html.Div([
        html.H1(f"{student_name}さん の学習進捗レポート"),
        html.P("内容を確認し、コメントを入力してから印刷してください。"),
        dbc.Button(
            [html.I(className="fas fa-print me-2"), "この内容を印刷"],
            id="final-print-btn", color="success", size="lg", className="mt-2"
        ),
        html.Hr(),
    ], id="report-header", className="my-4")

    # --- ここからが印刷されるコンテンツ ---
    printable_area = html.Div([
        
        # 1ページ目のコンテンツ
        html.Div([
            # 印刷用ヘッダー
            dbc.Row([
                dbc.Col(html.H2("学習進捗レポート"), width="auto", className="me-auto align-self-end"),
                dbc.Col([
                    html.P(id="report-creation-date", className="mb-0 text-muted"),
                    html.P(f"生徒名: {student_name}", className="mb-0 text-muted"),
                ], width="auto", className="text-end"),
            ], align="center", className="mb-4"),
            
            # ダッシュボード部分（画像で示された部分）
            dcc.Loading(html.Div(id="report-dashboard-content")),
        ], className="page-break"), # 1ページ目の終わりに改ページ

        # 2ページ目のコンテンツ
        html.Div([
            dbc.Row([
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
                        rows=8, # 初期表示の高さを調整
                        className="mb-4"
                    ),
                    # ★★★ 修正: 印刷専用のコメント表示エリアを追加 ★★★
                    html.Div(id="printable-comment-output", style={'display': 'none'})
                ], md=5),
            ], className="mt-4"),
        ]),
    ])

    return dbc.Container([action_header, printable_area], fluid=True, style={'backgroundColor': 'white'})