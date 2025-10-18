# components/bug_report_layout.py

from dash import dcc, html
import dash_bootstrap_components as dbc

def create_report_form(report_type):
    """不具合報告または要望の入力フォームを生成する"""
    form_id_prefix = f"{report_type}"
    header_text = "不具合を報告する" if report_type == "bug" else "機能要望を送信する"
    placeholder_text = "不具合の詳細を記入してください..." if report_type == "bug" else "要望の詳細を記入してください..."
    button_text = "送信する"

    return dbc.Card([
        dbc.CardHeader(header_text + "(褒め言葉でもOK)"),
        dbc.CardBody([
            dbc.Input(id=f"{form_id_prefix}-title", placeholder="件名", className="mb-3"),
            dbc.Textarea(id=f"{form_id_prefix}-description", placeholder=placeholder_text, className="mb-3", rows=5),
            dbc.Button(button_text, id=f"submit-{form_id_prefix}-btn", color="primary", className="w-100")
        ])
    ], className="mb-4")

def create_report_list(report_type):
    """不具合報告または要望の一覧表示エリアを生成する"""
    list_id = f"{report_type}-list-container"
    return dcc.Loading(html.Div(id=list_id))

def create_detail_modal(report_type):
    """詳細表示用モーダルを生成する"""
    # modal_id_prefix = f"{report_type}" # 不要になるので削除またはコメントアウト
    return dbc.Modal(
        [
            # ↓↓↓ IDを辞書形式に変更 ↓↓↓
            dbc.ModalHeader(dbc.ModalTitle(id={'type': 'detail-modal-title', 'report_type': report_type})),
            dbc.ModalBody(id={'type': 'detail-modal-body', 'report_type': report_type}),
            dbc.ModalFooter(
                dbc.Button("閉じる", id={'type': 'close-detail-modal', 'report_type': report_type}, className="ms-auto")
            ),
        ],
        id={'type': 'detail-modal', 'report_type': report_type}, # モーダル自体のIDは変更なし
        is_open=False,
        size="lg"
    )

def create_admin_modal(report_type):
    """管理者用編集モーダルを生成する"""
    modal_id_prefix = f"{report_type}"
    status_options = [
        {'label': '未対応', 'value': '未対応'},
        {'label': '対応中', 'value': '対応中'},
        {'label': '対応済', 'value': '対応済'},
    ]
    if report_type == "request":
        status_options.append({'label': '見送り', 'value': '見送り'}) # 要望用に「見送り」を追加

    return dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle(f"対応状況を更新 ({'不具合' if report_type == 'bug' else '要望'})")),
            dbc.ModalBody([
                dbc.Alert(id=f"{modal_id_prefix}-admin-alert", is_open=False),
                dcc.Store(id=f"editing-{modal_id_prefix}-id-store"),
                html.Div(id=f'{modal_id_prefix}-admin-detail-display'), # 詳細表示エリア
                html.Hr(),
                dbc.Label("ステータス"),
                dcc.Dropdown(
                    id=f'{modal_id_prefix}-status-dropdown',
                    options=status_options,
                ),
                html.Hr(),
                dbc.Label("対応メッセージ（任意）"),
                dbc.Textarea(id=f"{modal_id_prefix}-resolution-message-input", rows=4),
            ]),
            dbc.ModalFooter([
                dbc.Button("更新する", id=f"save-{modal_id_prefix}-status-btn", color="primary"),
                dbc.Button("キャンセル", id=f"cancel-{modal_id_prefix}-admin-modal", className="ms-auto")
            ]),
        ],
        id=f"{modal_id_prefix}-admin-modal",
        is_open=False,
    )

def create_bug_report_layout(user_info):
    """不具合報告・要望ページのレイアウトを生成する"""

    is_admin = user_info.get('role') == 'admin'

    # 不具合報告タブの内容
    bug_report_tab_content = dbc.Row([
        dbc.Col(create_report_form("bug"), md=4),
        dbc.Col(create_report_list("bug"), md=8),
    ])

    # 要望タブの内容
    request_tab_content = dbc.Row([
        dbc.Col(create_report_form("request"), md=4),
        dbc.Col(create_report_list("request"), md=8),
    ])

    return dbc.Container([
        html.H3("不具合報告・要望", className="my-4"),
        dbc.Tabs(
            [
                dbc.Tab(bug_report_tab_content, label="不具合報告", tab_id="tab-bug-report"),
                dbc.Tab(request_tab_content, label="要望", tab_id="tab-request"),
            ],
            id="report-tabs",
            active_tab="tab-bug-report",
        ),
        # モーダル (不具合用と要望用)
        create_detail_modal("bug"),
        create_detail_modal("request"),
        create_admin_modal("bug"),
        create_admin_modal("request"),
        # 共通のトースト用Storeなど
        dcc.Store(id='report-update-trigger', storage_type='memory'), # リスト更新トリガー用
    ], fluid=True)