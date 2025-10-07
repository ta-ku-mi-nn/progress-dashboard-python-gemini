from dash import html, dcc
import dash_bootstrap_components as dbc

def create_master_textbook_modal():
    """参考書マスター管理用のメインモーダルを生成する"""
    return dbc.Modal(
        id="master-textbook-modal",
        is_open=False,
        size="xl",
        scrollable=True,
        children=[
            dbc.ModalHeader(dbc.ModalTitle("参考書マスター管理")),
            dbc.ModalBody([
                dbc.Alert(id="master-textbook-alert", is_open=False),
                dbc.Row([
                    dbc.Col(dcc.Dropdown(id='master-textbook-subject-filter', placeholder="科目で絞り込み..."), width=12, md=3),
                    dbc.Col(dcc.Dropdown(id='master-textbook-level-filter', placeholder="レベルで絞り込み..."), width=12, md=3),
                    dbc.Col(dbc.Input(id='master-textbook-name-filter', placeholder="参考書名で検索..."), width=12, md=4),
                    dbc.Col(dbc.Button("新規追加", id="add-textbook-btn", color="success", className="w-100"), width=12, md=2)
                ], className="mb-3"),
                dbc.Spinner(
                    html.Div(id="master-textbook-list-container", style={"minHeight": "150px"}),
                    color="primary", type="border", fullscreen=False,
                    spinner_style={"width": "3rem", "height": "3rem"}, delay_show=200
                )
            ]),
            dbc.ModalFooter(dbc.Button("閉じる", id="close-master-textbook-modal", className="ms-auto")),
        ],
    )

def create_textbook_edit_modal():
    """参考書の新規追加・編集用のモーダルを生成する"""
    return dbc.Modal(
        id="textbook-edit-modal",
        is_open=False,
        children=[
            dbc.ModalHeader(dbc.ModalTitle(id="textbook-edit-modal-title")),
            dbc.ModalBody([
                dbc.Alert(id="textbook-edit-alert", is_open=False),
                dcc.Store(id='editing-textbook-id-store'),
                dbc.Form([
                    dbc.Row([
                        dbc.Label("科目", width=3),
                        dbc.Col(dbc.Input(id="textbook-subject-input", type="text"), width=9),
                    ], className="mb-3"),
                    dbc.Row([
                        dbc.Label("レベル", width=3),
                        dbc.Col(dcc.Dropdown(
                            id="textbook-level-input",
                            options=[
                                {'label': '基礎徹底', 'value': '基礎徹底'},
                                {'label': '日大', 'value': '日大'},
                                {'label': 'MARCH', 'value': 'MARCH'},
                                {'label': '早慶', 'value': '早慶'},
                            ]
                        ), width=9),
                    ], className="mb-3"),
                    dbc.Row([
                        dbc.Label("参考書名", width=3),
                        dbc.Col(dbc.Input(id="textbook-name-input", type="text"), width=9),
                    ], className="mb-3"),
                    dbc.Row([
                        dbc.Label("所要時間(h)", width=3),
                        dbc.Col(dbc.Input(id="textbook-duration-input", type="number", min=0), width=9),
                    ]),
                ])
            ]),
            dbc.ModalFooter([
                dbc.Button("保存", id="save-textbook-btn", color="primary"),
                dbc.Button("キャンセル", id="cancel-textbook-edit-btn", className="ms-auto"),
            ]),
        ],
    )

# ★★★ ここから新規追加 ★★★
def create_student_management_modal():
    """生徒管理用のメインモーダルを生成する"""
    return dbc.Modal(
        id="student-management-modal",
        is_open=False,
        size="xl",
        scrollable=True,
        children=[
            dbc.ModalHeader(dbc.ModalTitle("生徒管理")),
            dbc.ModalBody([
                dbc.Alert(id="student-management-alert", is_open=False),
                dbc.Button("新規生徒を追加", id="add-student-btn", color="success", className="mb-3"),
                dcc.Loading(html.Div(id="student-list-container"))
            ]),
            dbc.ModalFooter(dbc.Button("閉じる", id="close-student-management-modal")),
        ],
    )

def create_student_edit_modal():
    """生徒の新規追加・編集用のモーダルを生成する"""
    return dbc.Modal(
        id="student-edit-modal",
        is_open=False,
        children=[
            dbc.ModalHeader(dbc.ModalTitle(id="student-edit-modal-title")),
            dbc.ModalBody([
                dbc.Alert(id="student-edit-alert", is_open=False),
                dcc.Store(id='editing-student-id-store'),
                dbc.Form([
                    dbc.Row([
                        dbc.Label("校舎", width=3),
                        dbc.Col(dbc.Input(id="student-school-input", type="text", disabled=True), width=9),
                    ], className="mb-3"),
                    dbc.Row([
                        dbc.Label("メイン講師", width=3),
                        dbc.Col(dbc.Input(id="student-main-instructor-input", type="text", disabled=True), width=9),
                    ], className="mb-3"),
                    dbc.Row([
                        dbc.Label("生徒名", width=3),
                        dbc.Col(dbc.Input(id="student-name-input", type="text", required=True), width=9),
                    ], className="mb-3"),
                    dbc.Row([
                        dbc.Label("偏差値", width=3),
                        dbc.Col(dbc.Input(id="student-deviation-input", type="number"), width=9),
                    ], className="mb-3"),
                    dbc.Row([
                        dbc.Label("サブ講師", width=3),
                        dbc.Col(dbc.Input(id="student-sub-instructor-input", type="text"), width=9),
                    ]),
                ])
            ]),
            dbc.ModalFooter([
                dbc.Button("保存", id="save-student-btn", color="primary"),
                dbc.Button("キャンセル", id="cancel-student-edit-btn"),
            ]),
        ],
    )
# ★★★ ここまで新規追加 ★★★