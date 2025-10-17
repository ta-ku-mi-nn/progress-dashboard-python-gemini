import dash_bootstrap_components as dbc
from dash import html

def create_login_layout():
    """ログインページのレイアウトを生成する"""
    login_card = dbc.Card([
        dbc.CardHeader("学習進捗ダッシュボード ログイン"),
        dbc.CardBody([
            dbc.Alert(id='login-alert', color='danger', is_open=False),
            dbc.Row([
                dbc.Col([
                    dbc.Label("ユーザー名"),
                    dbc.Input(type="text", id="username-input", placeholder="ユーザー名を入力"),
                    html.Br(),
                    dbc.Label("パスワード"),
                    dbc.Input(type="password", id="password-input", placeholder="パスワードを入力"),
                    html.Br(),
                    dbc.Button("ログイン", id="login-button", color="primary", className="w-100"),
                ], width=12),
            ]),
        ]),
    ])

    info_card = dbc.Card([
        dbc.CardHeader("デモアカウント"),
        dbc.CardBody([
            html.P("以下の情報でログインできます："),
            html.Ul([
                html.Li(html.B("管理者:")),
                html.Ul([
                    html.Li("ユーザー名: tokyo_admin"),
                    html.Li("ユーザー名: osaka_admin"),
                    html.Li("ユーザー名: nagoya_admin"),
                ]),
                html.B("パスワード: admin", className="text-danger"),
                html.Li(html.B("一般ユーザー:")),
                html.Ul([
                    html.Li("ユーザー名: tokyo_user1"),
                    html.Li("ユーザー名: tokyo_user2"),
                    html.Li("ユーザー名: osaka_user1"),
                    html.Li("ユーザー名: osaka_user2"),
                    html.Li("ユーザー名: nagoya_user1"),
                    html.Li("ユーザー名: nagoya_user2"),
                ]),
                html.B("パスワード: user", className="text-danger"),
            ])
        ])
    ])

    return dbc.Container([
        dbc.Row([
            dbc.Col(login_card, width=12, md=6, lg=4),
            dbc.Col(info_card, width=12, md=6, lg=4),
        ], className="justify-content-center mt-5")
    ], fluid=True)


def create_access_denied_layout():
    """アクセス拒否ページのレイアウトを生成する"""
    return dbc.Container([
        dbc.Alert(
            [
                html.H4("アクセスが拒否されました", className="alert-heading"),
                html.P("このページを表示する権限がありません。"),
            ],
            color="danger",
            className="mt-4"
        )
    ], fluid=True)


def create_user_profile_modal():
    """ユーザープロファイル表示用のモーダルを生成する"""
    return dbc.Modal(
        id="user-profile-modal",
        is_open=False,
        children=[
            dbc.ModalHeader(dbc.ModalTitle("ユーザープロファイル")),
            dbc.ModalBody([
                html.P([html.B("ユーザー名: "), html.P(id="profile-username")]),
                html.P([html.B("役割: "), html.P(id="profile-role")]),
                html.P([html.B("所属校舎: "), html.P(id="profile-school")]),
                html.Hr(),
                html.P(html.B("担当生徒:")),
                html.Div(id="profile-assigned-students", style={'maxHeight': '200px', 'overflowY': 'auto'})
            ]),
            dbc.ModalFooter([
                dbc.Button("パスワード変更", id="change-password-button", color="warning"),
                dbc.Button("閉じる", id="close-profile-modal", className="ms-auto")
            ]),
        ],
    )


def create_password_change_modal():
    """パスワード変更用のモーダルを生成する"""
    return dbc.Modal(
        id="password-change-modal",
        is_open=False,
        children=[
            dbc.ModalHeader(dbc.ModalTitle("パスワード変更")),
            dbc.ModalBody([
                dbc.Alert(id="password-change-alert", is_open=False),
                dbc.Form([
                    dbc.Row([
                        dbc.Label("現在のパスワード", width=4),
                        dbc.Col(dbc.Input(type="password", id="current-password"), width=8),
                    ], className="mb-3"),
                    dbc.Row([
                        dbc.Label("新しいパスワード", width=4),
                        dbc.Col(dbc.Input(type="password", id="new-password"), width=8),
                    ], className="mb-3"),
                    dbc.Row([
                        dbc.Label("新しいパスワード（確認）", width=4),
                        dbc.Col(dbc.Input(type="password", id="confirm-new-password"), width=8),
                    ]),
                ])
            ]),
            dbc.ModalFooter([
                dbc.Button("変更を確定", id="confirm-password-change", color="primary"),
                dbc.Button("キャンセル", id="close-password-modal", className="ms-auto"),
            ]),
        ],
    )