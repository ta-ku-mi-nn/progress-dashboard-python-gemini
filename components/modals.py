# components/modals.py

import json
from dash import html, dcc
import dash_bootstrap_components as dbc
from data.nested_json_processor import get_bulk_presets

def create_plan_update_modal(subjects):
    """学習計画の追加・更新を行うための複数ステップモーダルを生成する。"""
    
    # ステップ0: 科目選択
    step0_content = html.Div([
        html.P("まず、更新したい科目を選択してください。", className="mb-3 text-center"),
        dcc.Loading(id="loading-subjects", children=html.Div(id='plan-subject-selection-container', className="d-grid gap-2 d-md-flex justify-content-md-center flex-wrap"))
    ])

    # ステップ1: 参考書選択（2カラムレイアウト）
    step1_content = dbc.Row([
        # 左列: 選択エリア
        dbc.Col([
            dbc.Tabs([
                dbc.Tab(label="プリセットから選択", tab_id="tab-preset", children=[
                    dcc.Loading(html.Div(id="plan-preset-buttons-container", className="p-3"))
                ]),
                dbc.Tab(label="個別に選択", tab_id="tab-individual", children=[
                    dbc.Input(id="plan-search-input", placeholder="参考書名で検索...", type="search", className="my-3"),
                    dcc.Loading(html.Div(id='plan-textbook-list-container', style={'maxHeight': '400px', 'overflowY': 'auto'}))
                ]),
            ]),
        ], md=7),
        # 右列: 選択済みリスト
        dbc.Col([
            html.H5("選択中の参考書", className="mt-3"),
            dbc.Button("すべて選択解除", id="plan-uncheck-all-btn", color="danger", outline=True, size="sm", className="mb-2 w-100"),
            dcc.Loading(html.Div(id="plan-selected-books-display", className="mt-2 border rounded p-2", style={'maxHeight': '450px', 'overflowY': 'auto'}))
        ], md=5)
    ])

    # ステップ2: 進捗入力
    step2_content = html.Div([
        html.P("選択した参考書の進捗を分数（例: 10/25）で入力してください。"),
        dcc.Loading(
            id="loading-progress-inputs",
            children=html.Div(id='plan-progress-input-container', style={'maxHeight': '500px', 'overflowY': 'auto'})
        )
    ])
    
    return dbc.Modal(
        id="plan-update-modal",
        is_open=False,
        size="xl", # モーダルを大きくする
        backdrop="static",
        children=[
            dbc.ModalHeader(dbc.ModalTitle(id="plan-modal-title")),
            dbc.ModalBody([
                dbc.Alert(id="plan-modal-alert", is_open=False),
                dcc.Store(id='plan-step-store', data=0),
                dcc.Store(id='plan-subject-store'),
                dcc.Store(id='plan-selected-books-store', data=[]),
                dcc.Store(id='plan-current-progress-store', data={}),
            
                html.Div(step0_content, id='plan-step-0'),
                html.Div(step1_content, id='plan-step-1', style={'display': 'none'}),
                html.Div(step2_content, id='plan-step-2', style={'display': 'none'}),
            ]),
            dbc.ModalFooter([
                dbc.Button("戻る", id="plan-back-btn", color="secondary", style={'display': 'none'}),
                dbc.Button("次へ", id="plan-next-btn", color="primary"),
                dbc.Button("保存", id="plan-save-btn", color="success", style={'display': 'none'}),
                dbc.Button("キャンセル", id="plan-cancel-btn", color="light"),
            ]),
        ]
    )

def create_all_modals(subjects):
    """
    アプリケーションで使用するモーダルを生成して返す。
    （管理者ページのユーザー関連モーダルは admin_components.py に移動）
    """
    return [
        create_plan_update_modal(subjects),
        dcc.Download(id="download-backup"),
    ]

# ユーザー一覧と新規作成モーダルを生成する関数をここに追加
def create_user_list_modal():
    """ユーザー一覧表示用のモーダル"""
    return dbc.Modal(
        id="user-list-modal",
        is_open=False,
        size="lg",
        children=[
            dbc.ModalHeader(dbc.ModalTitle("ユーザー一覧")),
            dbc.ModalBody(id="user-list-table"),
            dbc.ModalFooter(dbc.Button("閉じる", id="close-user-list-modal", className="ms-auto"))
        ]
    )

def create_new_user_modal():
    """新規ユーザー作成用のモーダル"""
    return dbc.Modal(
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
    )