import json
from dash import html, dcc
import dash_bootstrap_components as dbc
from config.settings import APP_CONFIG

def create_all_modals(subjects):
    """
    アプリケーションで使用するすべてのモーダルを生成して返す。
    """
    # bulk_buttons.json からボタンの構成を読み込む
    try:
        with open(APP_CONFIG['data']['bulk_buttons_file'], 'r', encoding='utf-8') as f:
            bulk_buttons_config = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        bulk_buttons_config = {}

    bulk_buttons = []
    for subject, categories in bulk_buttons_config.items():
        # subjectsがNoneでないことを確認
        if subjects and subject in subjects:
            buttons = [html.H5(subject)]
            for category, books in categories.items():
                buttons.append(
                    dbc.Button(
                        category,
                        id={'type': 'bulk-plan-button', 'index': f'{subject}-{category}'},
                        color='primary',
                        className='me-2 mb-2'
                    )
                )
            bulk_buttons.append(html.Div(buttons, className="mb-3"))

    return [
        # 一括登録モーダル
        dbc.Modal(
            id="bulk-register-modal",
            is_open=False,
            size="lg",
            children=[
                dbc.ModalHeader(dbc.ModalTitle("学習計画の一括登録")),
                dbc.ModalBody([
                    dbc.Alert("生徒を選択してください。", id="bulk-register-alert", color="warning", is_open=False),
                    html.P("ボタンをクリックすると、対応する参考書セットが「予定」に追加されます。"),
                    html.Div(bulk_buttons)
                ]),
                dbc.ModalFooter(dbc.Button("閉じる", id="close-bulk-modal", className="ms-auto")),
            ],
        ),
        # 管理者向けユーザー一覧モーダル
        dbc.Modal(
            id="user-list-modal",
            is_open=False,
            size="lg",
            children=[
                dbc.ModalHeader(dbc.ModalTitle("ユーザー一覧")),
                dbc.ModalBody(id="user-list-table"),
                dbc.ModalFooter(dbc.Button("閉じる", "close-user-list-modal", className="ms-auto"))
            ]
        ),
        # 管理者向け新規ユーザー作成モーダル
        dbc.Modal(
            id="new-user-modal",
            is_open=False,
            children=[
                dbc.ModalHeader(dbc.ModalTitle("新規ユーザー作成")),
                dbc.ModalBody([
                    dbc.Alert(id="new-user-alert", is_open=False),
                    dbc.Form([
                        dbc.Row([
                            dbc.Label("ユーザー名", width=3),
                            dbc.Col(dbc.Input(id="new-username", type="text"), width=9),
                        ], className="mb-3"),
                        dbc.Row([
                            dbc.Label("パスワード", width=3),
                            dbc.Col(dbc.Input(id="new-password", type="password"), width=9),
                        ], className="mb-3"),
                        dbc.Row([
                            dbc.Label("役割", width=3),
                            dbc.Col(dcc.Dropdown(
                                id='new-user-role',
                                options=[
                                    {'label': '一般ユーザー', 'value': 'user'},
                                    {'label': '管理者', 'value': 'admin'},
                                ],
                                value='user'
                            ), width=9),
                        ], className="mb-3"),
                        dbc.Row([
                            dbc.Label("所属校舎", width=3),
                            dbc.Col(dbc.Input(id="new-user-school", type="text", placeholder="（任意）"), width=9),
                        ]),
                    ])
                ]),
                dbc.ModalFooter([
                    dbc.Button("作成", id="create-user-button", color="primary"),
                    dbc.Button("閉じる", id="close-new-user-modal", className="ms-auto")
                ]),
            ]
        ),
        # データダウンロード用コンポーネント
        dcc.Download(id="download-backup"),
    ]