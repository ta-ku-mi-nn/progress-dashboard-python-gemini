# components/bug_report_layout.py

from dash import dcc, html
import dash_bootstrap_components as dbc

def create_bug_report_layout(user_info):
    """不具合報告ページのレイアウトを生成する"""
    
    is_admin = user_info.get('role') == 'admin'

    report_form = dbc.Card([
        dbc.CardHeader("不具合を報告する"),
        dbc.CardBody([
            dbc.Alert(id="bug-report-alert", is_open=False),
            dbc.Input(id="bug-report-title", placeholder="件名", className="mb-3"),
            dbc.Textarea(id="bug-report-description", placeholder="不具合の詳細を記入してください...", className="mb-3", rows=5),
            dbc.Button("送信する", id="submit-bug-report-btn", color="primary", className="w-100")
        ])
    ], className="mb-4")

    report_list = dcc.Loading(html.Div(id="bug-report-list-container"))

    detail_modal = dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle(id="bug-detail-modal-title")),
            dbc.ModalBody(id="bug-detail-modal-body"),
            dbc.ModalFooter(
                dbc.Button("閉じる", id="close-bug-detail-modal", className="ms-auto")
            ),
        ],
        id="bug-detail-modal",
        is_open=False,
        size="lg"
    )
    
    # ★★★ ここから修正 ★★★
    admin_modal = dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle("対応状況を更新")),
            dbc.ModalBody([
                dbc.Alert(id="bug-admin-alert", is_open=False),
                dcc.Store(id='editing-bug-id-store'),
                # 不具合詳細を表示するエリアを追加
                html.Div(id='bug-admin-detail-display'),
                html.Hr(),
                dbc.Label("ステータス"),
                dcc.Dropdown(
                    id='bug-status-dropdown',
                    options=[
                        {'label': '未対応', 'value': '未対応'},
                        {'label': '対応中', 'value': '対応中'},
                        {'label': '対応済', 'value': '対応済'},
                    ],
                ),
                html.Hr(),
                dbc.Label("対応メッセージ（任意）"),
                dbc.Textarea(id="bug-resolution-message-input", rows=4),
            ]),
            dbc.ModalFooter([
                dbc.Button("更新する", id="save-bug-status-btn", color="primary"),
                dbc.Button("キャンセル", id="cancel-bug-admin-modal", className="ms-auto")
            ]),
        ],
        id="bug-admin-modal",
        is_open=False,
    ) if is_admin else html.Div()
    # ★★★ ここまで修正 ★★★

    return dbc.Container([
        html.H2("不具合報告", className="my-4"),
        dbc.Row([
            dbc.Col(report_form, md=4),
            dbc.Col(report_list, md=8),
        ]),
        detail_modal,
        admin_modal
    ], fluid=True)