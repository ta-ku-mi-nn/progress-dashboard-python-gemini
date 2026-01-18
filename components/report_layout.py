# components/report_layout.py
from dash import dcc, html
import dash_bootstrap_components as dbc

def create_report_layout(student_name):
    """印刷専用ページのレイアウトを生成する（整理・完全版）"""

    # 1. 操作用ヘッダー（画面上でのみ表示、印刷時はCSSで非表示）
    action_header = html.Div([
        dbc.Container([
            dbc.Row([
                dbc.Col([
                    html.H3("レポート作成モード", className="text-primary"),
                    html.P("内容を確認・入力し、最後に「この内容を印刷する」ボタンを押してください。"),
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

    # 2. 印刷されるコンテンツエリア
    # printable-container と printable-page クラスを使い、CSSでA4サイズに固定します
    printable_content = html.Div([
        
        # 【第1ページ】サマリーとダッシュボード
        html.Div([
            # レポートヘッダー（タイトル・生徒名・日付）
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
                        html.P("発行：進捗管理システム (Progress Dashboard)", className="text-end small text-muted"),
                    ], width=6),
                ], className="mb-4 align-items-end"),
            ], className="report-header-section"),

            # メイングラフエリア
            html.Div([
                html.H4("■ 学習進捗サマリー", className="section-title"),
                dcc.Loading(html.Div(id="report-dashboard-content")),
            ], className="report-section"),
            
        ], className="printable-page"), # ← これがCSSでA4縦サイズに固定される単位です

        # 【第2ページ】過去問詳細と指導コメント
        html.Div([
            dbc.Row([
                # 左列：過去問分析 (width=7 で固定)
                dbc.Col([
                    html.H4("■ 過去問実施記録", className="section-title"),
                    dcc.Loading(html.Div(id="report-past-exam-content", className="past-exam-table-container")),
                ], width=7),
                
                # 右列：講師コメント (width=5 で固定)
                dbc.Col([
                    html.H4("■ 指導・特記事項", className="section-title"),
                    # 入力欄（画面上のみ表示）
                    dbc.Textarea(
                        id="report-comment-input",
                        placeholder="今月の学習状況やアドバイスを入力してください...",
                        rows=15,
                        className="mb-3 no-print"
                    ),
                    # 印刷用表示エリア（印刷時のみ表示）
                    html.Div(id="printable-comment-output", className="comment-print-box")
                ], width=5),
            ]),
            
            # フッター（ページ下部）
            html.Div([
                html.Hr(),
                html.P("※本レポートはシステムにより自動生成されたデータに基づいています。", className="text-center small text-muted")
            ], className="report-footer mt-auto")
            
        ], className="printable-page"),
        
    ], id="report-content-area", className="printable-container")

    # 最終的な戻り値（操作用ヘッダー + 印刷エリア）
    return html.Div([
        action_header,
        printable_content
    ], style={'backgroundColor': '#f4f4f4', 'minHeight': '100vh'})