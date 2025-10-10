# components/main_layout.py

from dash import dcc, html
import dash_bootstrap_components as dbc

def create_main_layout(user_info):
    """
    アプリケーションのメインレイアウト（学習進捗表示ページ）を生成します。
    """
    if not user_info:
        return html.Div()

    main_content = [
        # タブとボタンを横並びにするためのコンテナ
        html.Div(
            [
                html.Div(id='subject-tabs-container', style={'flexGrow': 1}), # タブが幅を占める
                html.Div(id='dashboard-actions-container', className="ms-3"), # ボタン用のコンテナ
            ],
            className="d-flex align-items-center"
        ),
        html.Div(id='dashboard-content-container', className="mt-4"),
    ]
    return html.Div(main_content)

def create_navbar(user_info):
    """
    ユーザー情報に基づいてナビゲーションバーを生成します。
    """
    if not user_info:
        return None

    username = user_info.get('username', 'ゲスト')
    
    user_menu = dbc.DropdownMenu(
        [
            # ★★★ 修正点: n_clicks=0 を削除 ★★★
            dbc.DropdownMenuItem("プロフィール", id="user-profile-btn"),
            dbc.DropdownMenuItem(divider=True),
            # ★★★ 修正点: n_clicks=0 を削除 ★★★
            dbc.DropdownMenuItem("ログアウト", id="logout-button", href="/login"),
        ],
        label=username,
        nav=True,
        in_navbar=True,
    )

    admin_link = []
    if user_info.get('role') == 'admin':
        admin_link = [dbc.NavItem(dbc.NavLink("管理者メニュー", href="/admin"))]
        
    return dbc.NavbarSimple(
        children=[
            dbc.NavItem(dbc.NavLink("ホーム", href="/")),
            dbc.NavItem(dbc.NavLink("過去問管理", href="/past-exam")),
            dbc.NavItem(dbc.NavLink("宿題管理", href="/homework")),
            *admin_link,
            user_menu,
        ],
        brand="学習進捗ダッシュボード",
        brand_href="/",
        color="dark",
        dark=True,
        className="mb-4",
    )