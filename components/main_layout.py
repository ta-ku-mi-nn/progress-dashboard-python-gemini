# components/main_layout.py

from dash import html, dcc
import dash_bootstrap_components as dbc

# ... (create_navbar 関数は変更なし) ...
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
    """メインアプリケーションのレイアウトを生成する"""
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
                        # ★★★ ここから修正 ★★★
                        html.Div([
                            dbc.Button(
                                [html.I(className="fas fa-edit me-2"), "個別更新"],
                                id="update-plan-btn", color="primary", className="flex-grow-1 me-2", disabled=True
                            ),
                            dbc.Button(
                                [html.I(className="fas fa-layer-group me-2"), "一括登録"],
                                id="open-bulk-modal-btn", color="secondary", className="flex-grow-1", disabled=True
                            ),
                        ], className="d-flex"),
                        html.Div(
                            dbc.Button(
                                [html.I(className="fas fa-file-pdf me-2"), "PDFレポート出力"],
                                id="create-report-btn", color="info", className="w-100", disabled=True
                            ), className="d-grid gap-2 mt-2"
                        )
                        # ★★★ ここまで修正 ★★★
                    ]))
                ], width=12, lg=3, className="bg-light"),

                # --- 右側のコンテンツエリア (変更なし) ---
                dbc.Col([
                    html.H4("学習状況サマリー", className="mt-4"),
                    html.Div(id='cumulative-progress-container'),
                    html.Hr(),
                    
                    html.H4("科目別 達成度"),
                    dbc.Alert("円グラフをクリックすると詳細が表示されます。", color="info", className="small"),
                    html.Div(id='subject-pie-charts-container'),
                    html.Hr(),

                    html.Div(id='detailed-progress-view-container'),
                    html.Hr(),

                    dbc.Row([
                        dbc.Col(html.H4("宿題管理"), width='auto'),
                        dbc.Col(dbc.Button([html.I(className="fas fa-plus me-2"), "宿題を追加"], id="add-homework-btn", color="success", size="sm"), className="text-end")
                    ], align="center", className="mb-3"),
                    html.Div(id='homework-list-container')
                ], width=12, lg=9)
            ])
        ], fluid=True),
    ])