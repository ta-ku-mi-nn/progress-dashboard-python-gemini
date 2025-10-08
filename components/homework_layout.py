# components/homework_layout.py

from dash import html, dcc
import dash_bootstrap_components as dbc

def create_homework_layout(user_info):
    """宿題管理ページのレイアウトを生成する"""
    return dbc.Container([
        dbc.Row([
            # 左側のフィルターパネル (メインレイアウトと共通)
            dbc.Col([
                html.H4("フィルター", className="mt-4"),
                dbc.Card(dbc.CardBody([
                    dbc.Label("校舎選択"),
                    dcc.Dropdown(id='school-dropdown', placeholder="校舎を選択..."),
                    html.Br(),
                    dbc.Label("生徒選択"),
                    dcc.Dropdown(id='student-dropdown', placeholder="生徒を選択..."),
                ]))
            ], width=12, lg=3, className="bg-light sticky-top"),

            # 右側の宿題コンテンツエリア
            dbc.Col([
                dbc.Row([
                    dbc.Col(html.H4("宿題管理", className="mt-4"), width='auto'),
                    dbc.Col(
                        dbc.Button(
                            [html.I(className="fas fa-plus me-2"), "宿題を追加"], 
                            id="add-homework-btn", 
                            color="success", 
                            size="sm",
                            disabled=True # 生徒が選択されるまで無効
                        ), 
                        className="text-end"
                    )
                ], align="center", className="mb-3"),
                
                # 宿題リストが表示されるコンテナ
                dcc.Loading(
                    id="loading-homework-list",
                    type="default",
                    children=html.Div(id='homework-list-container')
                )
            ], width=12, lg=9)
        ])
    ], fluid=True)