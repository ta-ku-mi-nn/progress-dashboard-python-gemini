# components/homework_layout.py

from dash import dcc, html
import dash_bootstrap_components as dbc
from datetime import date, timedelta

def create_homework_modal():
    """宿題の追加・編集を行うモーダルを生成する"""

    homework_days_container = html.Div(
        [
            dbc.Row([
                dbc.Col(
                    (date.today() + timedelta(days=i)).strftime('%Y-%m-%d (%a)'),
                    width=12, md=3, className="fw-bold small text-muted"
                ),
                dbc.Col(
                    dcc.Input(
                        id={'type': 'homework-modal-range-input', 'index': i},
                        type='text', placeholder='例: p.10-15', className="w-100 form-control-sm"
                    ), width=12, md=9
                )
            ], className="mb-2 align-items-center") for i in range(7)
        ]
    )

    assignment_controls = dbc.Card(
        dbc.CardBody([
            html.H6("宿題自動割り振り", className="card-title"),
            dbc.Row([
                dbc.Col(dbc.Input(id="modal-start-page-input", type="number", placeholder="開始P", min=1, size="sm")),
                dbc.Col(dbc.Input(id="modal-interval-input", type="number", placeholder="間隔", min=1, size="sm")),
            ], className="mb-2"),
            dbc.ButtonGroup([
                dbc.Button("4進2復", id="modal-btn-4-2", color="primary", outline=True, size="sm"),
                dbc.Button("2進1復", id="modal-btn-2-1", color="primary", outline=True, size="sm"),
                dbc.Button("6進", id="modal-btn-6-0", color="primary", outline=True, size="sm"),
            ], size="sm", className="w-100")
        ])
    )

    other_inputs = dbc.Card(
        dbc.CardBody([
            html.H6("補足情報", className="card-title"),
            dbc.Textarea(id="modal-remarks-input", placeholder="備考...", className="mb-2", rows=1),
            dbc.Input(id="modal-test-result-input", placeholder="テスト結果...", className="mb-2"),
            dcc.Dropdown(id="modal-achievement-input", placeholder="宿題達成度...", options=[
                {'label': '100%', 'value': 100}, {'label': '80-99%', 'value': 80},
                {'label': '60-79%', 'value': 60}, {'label': '40-59%', 'value': 40},
                {'label': '20-39%', 'value': 20}, {'label': '0-19%', 'value': 0},
            ]),
        ])
    )

    return dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle(id="homework-modal-title")),
            dbc.ModalBody([
                dbc.Alert(id="homework-modal-alert", is_open=False),
                dcc.Store(id='editing-homework-store'),

                html.Div(
                    dcc.Dropdown(
                        id='homework-modal-subject-dropdown',
                        placeholder="科目を選択...",
                        disabled=True
                    ),
                    id='homework-modal-subject-selector-container',
                    className="mb-2"
                ),
                html.Div(
                    dcc.Dropdown(
                        id='homework-modal-textbook-dropdown',
                        placeholder="先に科目を選択してください",
                        disabled=True
                    ),
                    id='homework-modal-textbook-selector-container',
                    className="mb-2"
                ),
                dbc.Input(id='homework-modal-custom-textbook-input', placeholder="リストにない参考書はこちらに入力...", className="mb-3"),
                html.Hr(),

                dbc.Row([
                    dbc.Col([homework_days_container], md=7),
                    dbc.Col([assignment_controls, other_inputs], md=5),
                ]),
            ]),
            dbc.ModalFooter([
                dbc.Button("削除", id="delete-homework-btn", color="danger", className="me-auto"),
                dbc.Button("クリア", id="clear-homework-modal-btn", color="light"),
                dbc.Button("キャンセル", id="cancel-homework-btn", color="secondary"),
                dbc.Button("保存", id="save-homework-modal-btn", color="primary"),
            ]),
        ],
        id="homework-modal",
        size="lg",
        is_open=False,
    )


def create_homework_layout(user_info):
    """宿題管理ページのメインレイアウト（リスト表示）を生成します。"""

    return html.Div([
        dbc.Row([
            dbc.Col(html.H3("宿題管理")),
            dbc.Col(
                dbc.Button("新しい宿題を追加", id="add-homework-btn", color="success"),
                className="text-end"
            )
        ], align="center", className="my-4"),

        # 機能未実装のため、準備中メッセージを表示
        dbc.Alert([
            dbc.Container(html.H2("この機能はただいま準備中です"), className="text-center mt-5"),
            dbc.Container(html.H3("開発終了までお待ちください"), className="text-center mt-5 mb-5"),
        ], color="info"),
        dcc.Loading(html.Div(id="homework-list-container")),

        # 宿題編集用のモーダルをレイアウトに追加
        create_homework_modal(),

        # 削除確認ダイアログをレイアウトに追加
        dcc.ConfirmDialog(
            id='delete-homework-confirm',
            message='本当にこの宿題グループを削除しますか？\nこの操作は取り消せません。',
            submit_n_clicks=0,
        ),
    ])