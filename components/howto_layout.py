from dash import html
import dash_bootstrap_components as dbc

def create_howto_layout(user_info):
    return html.Div([
        dbc.Row([
            dbc.Col(html.H3("使い方")),
        ], className="my-4"),
        dbc.Row(
            dbc.Col(
                dbc.Card(
                    [
                    dbc.CardHeader(html.H4("ようこそ！学習進捗ダッシュボードへ", className="mb-0")),
                    dbc.CardBody([
                        html.P(
                            "このダッシュボードは、生徒一人ひとりの学習状況を可視化し、管理するためのツールです。",
                            className="lead",
                        ),
                        html.Hr(),
                        html.H5("基本的な使い方", className="mt-4"),
                        dbc.ListGroup(
                            [
                                dbc.ListGroupItem([
                                    html.Div(className="d-flex w-100 justify-content-start align-items-center", children=[
                                        html.I(className="fas fa-user-graduate fa-2x me-3 text-primary"),
                                        html.Div([
                                            html.H6("1. 生徒を選択する", className="mb-1"),
                                            html.P("まずは画面上部のドロップダウンメニューから、進捗を確認したい生徒を選択してください。", className="mb-1 small text-muted"),
                                        ])
                                    ])
                                ]),
                                dbc.ListGroupItem([
                                    html.Div(className="d-flex w-100 justify-content-start align-items-center", children=[
                                        html.I(className="fas fa-chart-line fa-2x me-3 text-success"),
                                        html.Div([
                                            html.H6("2. 学習進捗を確認する", className="mb-1"),
                                            html.P("生徒を選択すると、科目ごとの達成率や学習時間のグラフが表示されます。タブを切り替えることで、各科目の詳細な進捗も確認できます。", className="mb-1 small text-muted"),
                                        ])
                                    ])
                                ]),
                                dbc.ListGroupItem([
                                    html.Div(className="d-flex w-100 justify-content-start align-items-center", children=[
                                        html.I(className="fas fa-edit fa-2x me-3 text-info"),
                                        html.Div([
                                            html.H6("3. 進捗を更新する", className="mb-1"),
                                            html.P("「進捗を更新」ボタンから、学習計画の作成や変更、達成度の入力ができます。", className="mb-1 small text-muted"),
                                        ])
                                    ])
                                ]),
                                dbc.ListGroupItem([
                                    html.Div(className="d-flex w-100 justify-content-start align-items-center", children=[
                                        html.I(className="fas fa-book fa-2x me-3 text-warning"),
                                        html.Div([
                                            html.H6("4. 他の機能", className="mb-1"),
                                            html.P("ナビゲーションバーから「宿題管理」や「過去問管理」ページに移動できます。", className="mb-1 small text-muted"),
                                        ])
                                    ])
                                ]),
                            ],
                            flush=True,
                            className="mb-4",
                        ),
                        dbc.Alert(
                            "さあ、はじめましょう！まずは、上のドロップダウンから生徒を選択してください。",
                            color="primary",
                        ),
                    ]),
                    ]
                ),
            width=12,
            lg=10,
            xl=8,
            ),
        justify="center",
        className="mt-5",
        )
    ])