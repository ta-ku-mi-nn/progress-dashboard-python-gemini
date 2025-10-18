# components/bug_report_layout.py

from dash import dcc, html
import dash_bootstrap_components as dbc

# --- フォーム生成 (アラートID修正) ---
def create_report_form(report_type):
    form_id_prefix = f"{report_type}"
    header_text = "不具合を報告する" if report_type == "bug" else "機能要望を送信する"
    placeholder_text = "不具合の詳細を記入してください..." if report_type == "bug" else "要望の詳細を記入してください..."
    button_text = "送信する"
    # ★★★ 単純なIDに変更 ★★★
    alert_id = f"{form_id_prefix}-submit-alert"

    return dbc.Card([
        dbc.CardHeader(header_text + "(褒め言葉でもOK)"),
        dbc.CardBody([
            # ★★★ 単純なIDを使用 ★★★
            dbc.Alert(id=alert_id, is_open=False),
            dbc.Input(id=f"{form_id_prefix}-title", placeholder="件名", className="mb-3"),
            dbc.Textarea(id=f"{form_id_prefix}-description", placeholder=placeholder_text, className="mb-3", rows=5),
            dbc.Button(button_text, id=f"submit-{form_id_prefix}-btn", color="primary", className="w-100")
        ])
    ], className="mb-4")

# --- リスト表示エリア生成 (変更なし) ---
def create_report_list(report_type):
    list_id = f"{report_type}-list-container"
    # pattern matching ID はリスト項目に残す (Inputで使うため)
    return dcc.Loading(html.Div(id=list_id))

# --- ★★★ ID 変更: 詳細モーダル ★★★ ---
def create_detail_modal(report_type):
    # ★★★ 単純な文字列IDを使用 ★★★
    modal_id = f"{report_type}-detail-modal"
    title_id = f"{report_type}-detail-modal-title"
    body_id = f"{report_type}-detail-modal-body"
    close_btn_id = f"close-{report_type}-detail-modal"

    return dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle(id=title_id)),
            dbc.ModalBody(id=body_id),
            dbc.ModalFooter(
                dbc.Button("閉じる", id=close_btn_id, className="ms-auto") # 単純なID
            ),
        ],
        id=modal_id, # 単純なID
        is_open=False,
        size="lg"
    )

# --- ★★★ ID 変更: 管理者モーダル ★★★ ---
def create_admin_modal(report_type):
    # ★★★ 単純な文字列IDを使用 ★★★
    modal_id = f"{report_type}-admin-modal"
    alert_id = f"{report_type}-admin-alert"
    display_id = f'{report_type}-admin-detail-display'
    dropdown_id = f'{report_type}-status-dropdown'
    input_id = f"{report_type}-resolution-message-input"
    save_btn_id = f"save-{report_type}-status-btn"
    cancel_btn_id = f"cancel-{report_type}-admin-modal"

    status_options = [ {'label': '未対応', 'value': '未対応'}, {'label': '対応中', 'value': '対応中'}, {'label': '対応済', 'value': '対応済'}, ]
    if report_type == "request": status_options.append({'label': '見送り', 'value': '見送り'})

    return dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle(f"対応状況を更新 ({'不具合' if report_type == 'bug' else '要望'})")),
            dbc.ModalBody([
                dbc.Alert(id=alert_id, is_open=False), # 単純なID
                html.Div(id=display_id),             # 単純なID
                html.Hr(),
                dbc.Label("ステータス"),
                dcc.Dropdown(id=dropdown_id, options=status_options), # 単純なID
                html.Hr(),
                dbc.Label("対応メッセージ（任意）"),
                dbc.Textarea(id=input_id, rows=4),         # 単純なID
            ]),
            dbc.ModalFooter([
                dbc.Button("更新する", id=save_btn_id, color="primary"),     # 単純なID
                dbc.Button("キャンセル", id=cancel_btn_id, className="ms-auto") # 単純なID
            ]),
        ],
        id=modal_id, # 単純なID
        is_open=False,
    )

# --- レイアウト生成 ---
def create_bug_report_layout(user_info):
    is_admin = user_info.get('role') == 'admin'
    bug_report_tab_content = dbc.Row([ dbc.Col(create_report_form("bug"), md=4), dbc.Col(create_report_list("bug"), md=8), ])
    request_tab_content = dbc.Row([ dbc.Col(create_report_form("request"), md=4), dbc.Col(create_report_list("request"), md=8), ])

    return dbc.Container([
        html.H3("不具合報告・要望", className="my-4"),
        dbc.Tabs(
            [ dbc.Tab(bug_report_tab_content, label="不具合報告", tab_id="tab-bug-report"), dbc.Tab(request_tab_content, label="要望", tab_id="tab-request"), ],
            id="report-tabs", active_tab="tab-bug-report",
        ),
        # ★★★ 共有のEditing Store (変更なし) ★★★
        dcc.Store(id='editing-report-store', storage_type='memory'), # {id: ..., type: 'bug'/'request'}
        # モーダル (ラッパーDivは維持)
        html.Div([
            create_detail_modal("bug"), create_detail_modal("request"),
            create_admin_modal("bug"), create_admin_modal("request"),
        ]),
        dcc.Store(id='report-update-trigger', storage_type='memory'),
        dcc.Store(id='report-modal-control-store', storage_type='memory'), # これは保存→閉じる連携で使用
    ], fluid=True)