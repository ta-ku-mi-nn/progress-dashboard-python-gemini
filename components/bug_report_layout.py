# components/bug_report_layout.py

from dash import dcc, html
import dash_bootstrap_components as dbc

# --- フォーム生成 (変更なし) ---
def create_report_form(report_type):
    form_id_prefix = f"{report_type}"
    header_text = "不具合を報告する" if report_type == "bug" else "機能要望を送信する"
    placeholder_text = "不具合の詳細を記入してください..." if report_type == "bug" else "要望の詳細を記入してください..."
    button_text = "送信する"
    # アラートIDはコールバック側で使うので、ここでは不要
    # alert_id = f"{form_id_prefix}-submit-alert"

    return dbc.Card([
        dbc.CardHeader(header_text),
        dbc.CardBody([
            # ★★★ アラートをフォーム内に移動 ★★★
            dbc.Alert(id=f"{form_id_prefix}-submit-alert", is_open=False, duration=4000), # durationを追加しても良い
            # ★★★ ここまで変更 ★★★
            dbc.Input(id=f"{form_id_prefix}-title", placeholder="件名", className="mb-3"),
            dbc.Textarea(id=f"{form_id_prefix}-description", placeholder=placeholder_text, className="mb-3", rows=5),
            dbc.Button(button_text, id=f"submit-{form_id_prefix}-btn", color="primary", className="w-100")
        ])
    ], className="mb-4")

# --- リスト表示エリア生成 (変更なし) ---
def create_report_list(report_type):
    list_id = f"{report_type}-list-container"
    return dcc.Loading(html.Div(id=list_id))

# --- 詳細モーダル (変更なし) ---
def create_detail_modal(report_type):
    modal_id = f"{report_type}-detail-modal"
    title_id = f"{report_type}-detail-modal-title"
    body_id = f"{report_type}-detail-modal-body"
    close_btn_id = f"close-{report_type}-detail-modal"

    return dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle(id=title_id)),
            dbc.ModalBody(id=body_id),
            dbc.ModalFooter(dbc.Button("閉じる", id=close_btn_id, className="ms-auto")),
        ],
        id=modal_id, is_open=False, size="lg"
    )

# --- 管理者モーダル (変更なし) ---
def create_admin_modal(report_type):
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
                dbc.Alert(id=alert_id, is_open=False),
                html.Div(id=display_id),
                html.Hr(),
                dbc.Label("ステータス"),
                dcc.Dropdown(id=dropdown_id, options=status_options),
                html.Hr(),
                dbc.Label("対応メッセージ（任意）"),
                dbc.Textarea(id=input_id, rows=4),
            ]),
            dbc.ModalFooter([
                dbc.Button("更新する", id=save_btn_id, color="primary"),
                dbc.Button("キャンセル", id=cancel_btn_id, className="ms-auto")
            ]),
        ],
        id=modal_id, is_open=False,
    )

# --- レイアウト生成 ---
def create_bug_report_layout(user_info):
    is_admin = user_info.get('role') == 'admin'
    # 各フォームコンポーネントを生成
    bug_form = create_report_form("bug")
    request_form = create_report_form("request")

    # タブの中身を作成
    bug_report_tab_content = dbc.Row([
        dbc.Col(bug_form, md=4), # フォーム
        dbc.Col(create_report_list("bug"), md=8), # リスト
    ])
    request_tab_content = dbc.Row([
        dbc.Col(request_form, md=4), # フォーム
        dbc.Col(create_report_list("request"), md=8), # リスト
    ])

    return dbc.Container([
        # ★★★ アラートをタブの外（ただしページコンテナの中）に移動 ★★★
        # dbc.Alert(id="bug-submit-alert", is_open=False, duration=4000), # フォーム内に移動したので削除
        # dbc.Alert(id="request-submit-alert", is_open=False, duration=4000), # フォーム内に移動したので削除

        dbc.Tabs(
            [
                dbc.Tab(bug_report_tab_content, label="不具合報告", tab_id="tab-bug-report"),
                dbc.Tab(request_tab_content, label="要望", tab_id="tab-request"),
            ],
            id="report-tabs",
            active_tab="tab-bug-report",
        ),
        # Stores and Modals (変更なし)
        dcc.Store(id='editing-report-store', storage_type='memory'),
        html.Div([
            create_detail_modal("bug"), create_detail_modal("request"),
            create_admin_modal("bug"), create_admin_modal("request"),
        ]),
        dcc.Store(id='report-update-trigger', storage_type='memory'),
        dcc.Store(id='report-modal-control-store', storage_type='memory'),
    ], fluid=True)