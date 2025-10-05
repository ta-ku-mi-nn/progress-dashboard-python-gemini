from dash import html, dcc
import dash_bootstrap_components as dbc

def create_navbar(user_info=None):
    """ナビゲーションバーを生成する"""
    username = user_info.get('username', 'Guest') if user_info else 'Guest'
    is_admin = user_info and user_info.get('role') == 'admin'

    nav_items = [
        dbc.NavItem(dbc.NavLink("ホーム", href="/")),
    ]
    if is_admin:
        nav_items.append(dbc.NavItem(dbc.NavLink("管理者メニュー", href="/admin")))

    user_dropdown = dbc.DropdownMenu(
        [
            dbc.DropdownMenuItem("プロフィール", id="user-menu"),
            dbc.DropdownMenuItem(divider=True),
            dbc.DropdownMenuItem("ログアウト", id="logout-button"),
        ],
        nav=True,
        in_navbar=True,
        label=username,
    )

    return dbc.Navbar(
        dbc.Container([
            html.A(
                dbc.Row([
                    dbc.Col(html.I(className="fas fa-chart-line me-2")),
                    dbc.Col(dbc.NavbarBrand("学習進捗ダッシュボード")),
                ], align="center", className="g-0"),
                href="/",
                style={"textDecoration": "none"},
            ),
            dbc.NavbarToggler(id="navbar-toggler"),
            dbc.Collapse(
                dbc.Nav(nav_items + [user_dropdown], className="ms-auto", navbar=True),
                id="navbar-collapse",
                navbar=True,
            ),
        ]),
        color="dark",
        dark=True,
    )

def create_main_layout(user_info):
    """メインアプリケーションのレイアウトを生成する（レポート機能追加）"""
    return html.Div([
        create_navbar(user_info),
        dbc.Container([
            dbc.Row([
                # 左側のフィルターパネル
                dbc.Col([
                    html.H4("フィルター", className="mt-4"),
                    dbc.Card(dbc.CardBody([
                        dbc.Label("校舎選択"),
                        dcc.Dropdown(id='school-dropdown', placeholder="校舎を選択..."),
                        html.Br(),
                        dbc.Label("生徒選択"),
                        dcc.Dropdown(id='student-dropdown', placeholder="生徒を選択..."),
                        html.Hr(),
                        # --- 【新規追加】レポート出力ボタン ---
                        html.Div(
                            dbc.Button(
                                [html.I(className="fas fa-file-pdf me-2"), "PDFレポート出力"],
                                id="create-report-btn",
                                color="info",
                                className="w-100",
                                disabled=True # 生徒が選択されるまで非アクティブ
                            ),
                            id="report-button-container"
                        )
                    ]))
                ], width=12, lg=3, className="bg-light"),

                # 右側のコンテンツエリア
                dbc.Col([
                    # --- 進捗テーブル ---
                    html.Div(id='student-progress-table'),
                    html.Hr(),

                    # --- 科目別進捗グラフ ---
                    html.H4("科目別進捗グラフ"),
                    html.Div(id='progress-graph-container'),
                    html.Hr(),

                    # --- 宿題管理セクション ---
                    dbc.Row([
                        dbc.Col(html.H4("宿題管理"), width='auto'),
                        dbc.Col(
                            dbc.Button(
                                [html.I(className="fas fa-plus me-2"), "宿題を追加"],
                                id="add-homework-btn",
                                color="success",
                                size="sm"
                            ),
                            className="text-end"
                        )
                    ], align="center", className="mb-3"),
                    html.Div(id='homework-list-container')

                ], width=12, lg=9)
            ])
        ], fluid=True),
        # dcc.Downloadコンポーネントをレイアウトのどこかに追加
        dcc.Download(id="download-pdf-report")
    ])