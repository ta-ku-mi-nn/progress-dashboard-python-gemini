import json
from dash import html, dcc
import dash_bootstrap_components as dbc
from data.nested_json_processor import get_bulk_presets

def create_plan_update_modal(subjects):
    """学習計画の追加・更新を行うための複数ステップモーダルを生成する。"""
    
        # (...step0_content は変更なし...)
    step0_content = html.Div(
        [
            html.P("まず、更新したい科目を選択してください。", className="mb-3"),
            html.Div(id='plan-subject-selection-container', className="d-grid gap-2 d-md-flex justify-content-md-center")
        ]
    )
    # ★★★ step1_content のみ修正 ★★★
    step1_content = html.Div([
        # 一括チェックボタンと「すべて外す」ボタンのコンテナ
        dbc.Row([
            dbc.Col(html.Div(id='plan-bulk-buttons-container'), width="auto"),
            dbc.Col(
                dbc.Button(
                    "すべて外す", 
                    id='plan-uncheck-all-btn', 
                    color='danger', 
                    outline=True, 
                    size="sm",
                    className='mb-2'
                ),
                width="auto",
                className="ms-auto" # 右寄せにする
            )
        ], align="center", className="mb-3"),
        
        # 検索窓
        dbc.Input(
            id="plan-search-input",
            placeholder="参考書名で検索...",
            type="search",
            className="mb-3"
        ),
        
        # 参考書リスト
        dcc.Loading(
            id="loading-textbooks",
            type="default",
            children=html.Div(id='plan-textbook-list-container', style={'maxHeight': '400px', 'overflowY': 'auto'})
        )
    ])

    # ステップ2: 進捗入力
    step2_content = html.Div([
        html.P("選択した参考書の進捗を入力してください。"),
        dcc.Loading(
            id="loading-progress-inputs",
            type="default",
            children=html.Div(id='plan-progress-input-container', style={'maxHeight': '400px', 'overflowY': 'auto'})
        )
    ])
    
    return dbc.Modal(
        id="plan-update-modal",
        is_open=False,
        size="lg",
        backdrop="static",
        children=[
            dbc.ModalHeader(dbc.ModalTitle(id="plan-modal-title")),
            dbc.ModalBody([
                dbc.Alert(id="plan-modal-alert", is_open=False),
                dcc.Store(id='plan-step-store', data=0),
                dcc.Store(id='plan-subject-store'),
                dcc.Store(id='plan-selected-books-store'),
                dcc.Store(id='plan-all-books-store'),
                
                html.Div(step0_content, id='plan-step-0'),
                html.Div(step1_content, id='plan-step-1', style={'display': 'none'}),
                html.Div(step2_content, id='plan-step-2', style={'display': 'none'}),
            ]),
            dbc.ModalFooter([
                dbc.Button("戻る", id="plan-back-btn", color="secondary", style={'display': 'none'}),
                dbc.Button("次へ", id="plan-next-btn", color="primary", style={'display': 'none'}), # ★★★ 修正：最初は非表示 ★★★
                dbc.Button("保存", id="plan-save-btn", color="success", style={'display': 'none'}),
                dbc.Button("キャンセル", id="plan-cancel-btn", color="light"),
            ]),
        ]
    )
def create_all_modals(subjects):
    """
    アプリケーションで使用するすべてのモーダルを生成して返す。
    """
    # データベースから一括登録ボタンの構成を読み込む
    bulk_buttons_config = get_bulk_presets()

    bulk_buttons_by_subject = []
    if subjects:
        for subject in subjects:
            if subject in bulk_buttons_config:
                buttons = [html.H5(subject, className="mt-3")]
                for preset_name, books in bulk_buttons_config[subject].items():
                    buttons.append(
                        dbc.Button(
                            preset_name,
                            id={'type': 'bulk-plan-button', 'subject': subject, 'books': json.dumps(books)},
                            color='primary',
                            className='me-2 mb-2'
                        )
                    )
                bulk_buttons_by_subject.append(html.Div(buttons))

    return [
        create_plan_update_modal(subjects),
        dbc.Modal(
            id="bulk-register-modal",
            is_open=False,
            size="lg",
            children=[
                dbc.ModalHeader(dbc.ModalTitle("学習計画の一括登録")),
                dbc.ModalBody([
                    dbc.Alert(id="bulk-register-alert", color="warning", is_open=False, children=""),
                    html.P("下のボタンをクリックすると、対応する参考書セットが「予定」に一括で追加されます。"),
                    html.Hr(),
                    *bulk_buttons_by_subject
                ]),
                dbc.ModalFooter(dbc.Button("閉じる", id="close-bulk-modal", className="ms-auto")),
            ],
        ),
        dbc.Modal(
            id="homework-modal",
            is_open=False,
            children=[
                dbc.ModalHeader(dbc.ModalTitle(id="homework-modal-title")),
                dbc.ModalBody([
                    dbc.Alert(id="homework-alert", is_open=False),
                    dbc.Form([
                        dbc.Row([
                            dbc.Label("科目", width=3),
                            dbc.Col(dcc.Dropdown(
                                id='homework-subject',
                                options=[{'label': s, 'value': s} for s in (subjects or [])]
                            ), width=9),
                        ], className="mb-3"),
                        dbc.Row([
                            dbc.Label("課題内容", width=3),
                            dbc.Col(dbc.Textarea(id="homework-task", placeholder="例: 基礎問題精講 P.10-15"), width=9),
                        ], className="mb-3"),
                        dbc.Row([
                            dbc.Label("提出期限", width=3),
                            dbc.Col(dcc.DatePickerSingle(
                                id='homework-due-date',
                                display_format='YYYY-MM-DD',
                            ), width=9),
                        ]),
                    ])
                ]),
                dbc.ModalFooter([
                    dbc.Button("保存", id="save-homework-button", color="primary"),
                    dbc.Button("キャンセル", id="close-homework-modal", className="ms-auto"),
                ]),
            ]
        ),
        dbc.Modal(
            id="user-list-modal",
            is_open=False,
            size="lg",
            children=[
                dbc.ModalHeader(dbc.ModalTitle("ユーザー一覧")),
                dbc.ModalBody(id="user-list-table"),
                dbc.ModalFooter(dbc.Button("閉じる", id="close-user-list-modal", className="ms-auto"))
            ]
        ),
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
        dcc.Download(id="download-backup"),
    ]