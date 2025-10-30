# components/admin_components.py

from dash import html, dcc
import dash_bootstrap_components as dbc
import datetime # この行を追加

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
        size="lg", # ★ サイズを少し大きく
        children=[
            dbc.ModalHeader(dbc.ModalTitle(id="student-edit-modal-title")),
            dbc.ModalBody([
                dbc.Alert(id="student-edit-alert", is_open=False),
                dcc.Store(id='editing-student-id-store'),
                dbc.Form([
                    dbc.Row([
                        dbc.Col([ # ★ 左列
                            dbc.Label("校舎", width=3),
                            dbc.Col(dbc.Input(id="student-school-input", type="text", disabled=True), width=9),
                        ], md=6),
                        dbc.Col([ # ★ 右列
                            dbc.Label("生徒名 *", width=3),
                            dbc.Col(dbc.Input(id="student-name-input", type="text", required=True), width=9),
                        ], md=6),
                    ], className="mb-3"),
                    dbc.Row([
                        dbc.Col([ # ★ 左列
                            dbc.Label("学年", width=3),
                            # ★ 学年ドロップダウンの選択肢から「その他」を削除
                            dbc.Col(dcc.Dropdown(
                                id="student-grade-input",
                                options=[
                                    {'label': '中1', 'value': '中1'}, {'label': '中2', 'value': '中2'}, {'label': '中3', 'value': '中3'},
                                    {'label': '高1', 'value': '高1'}, {'label': '高2', 'value': '高2'}, {'label': '高3', 'value': '高3'},
                                    {'label': '既卒', 'value': '既卒'},
                                    # {'label': 'その他', 'value': 'その他'}, # <-- この行を削除
                                ],
                                placeholder="学年を選択..."
                            ), width=9),
                        ], md=6),
                        dbc.Col([ # ★ 右列
                            dbc.Label("偏差値", width=3),
                            dbc.Col(dbc.Input(id="student-deviation-input", type="number", placeholder="（任意）"), width=9),
                        ], md=6),
                    ], className="mb-3"),
                     dbc.Row([
                        dbc.Col([ # ★ 左列
                            dbc.Label("志望校レベル", width=3),
                            # ★ 志望校レベルドロップダウンの選択肢から「その他」を削除
                            dbc.Col(dcc.Dropdown(
                                id="student-target-level-input",
                                options=[
                                    {'label': '基礎徹底', 'value': '基礎徹底'},
                                    {'label': '日大', 'value': '日大'},
                                    {'label': 'MARCH', 'value': 'MARCH'},
                                    {'label': '早慶', 'value': '早慶'},
                                    # {'label': 'その他', 'value': 'その他'}, # <-- この行を削除
                                ],
                                placeholder="レベルを選択..."
                            ), width=9),
                        ], md=6),
                        dbc.Col([ # ★ 右列
                            dbc.Label("出身/在籍校", width=3),
                            # ★ 出身校・在籍校入力欄を追加
                            dbc.Col(dbc.Input(id="student-previous-school-input", type="text", placeholder="（任意）"), width=9),
                        ], md=6),
                    ], className="mb-3"),
                    html.Hr(), # ★ 区切り線を追加
                    dbc.Row([
                        dbc.Col([ # ★ 左列
                            dbc.Label("メイン講師", width=3),
                            dbc.Col(dbc.Input(id="student-main-instructor-input", type="text", disabled=True), width=9),
                        ], md=6),
                        dbc.Col([ # ★ 右列
                            dbc.Label("サブ講師", width=3),
                            dbc.Col(dcc.Dropdown(id="student-sub-instructor-input", multi=True, placeholder="（任意）"), width=9),
                        ], md=6),
                    ]),
                ])
            ]),
            dbc.ModalFooter([
                dbc.Button("保存", id="save-student-btn", color="primary"),
                dbc.Button("キャンセル", id="cancel-student-edit-btn"),
            ]),
        ],
    )

def create_bulk_preset_management_modal():
    """一括登録プリセット管理用のメインモーダル"""
    return dbc.Modal(
        id="bulk-preset-management-modal",
        is_open=False,
        size="lg",
        scrollable=True,
        children=[
            dbc.ModalHeader(dbc.ModalTitle("一括登録プリセット管理")),
            dbc.ModalBody([
                dbc.Alert(id="bulk-preset-alert", is_open=False),
                dbc.Button("新規プリセットを追加", id="add-bulk-preset-btn", color="success", className="mb-3"),
                dcc.Loading(html.Div(id="bulk-preset-list-container"))
            ]),
            dbc.ModalFooter(dbc.Button("閉じる", id="close-bulk-preset-modal")),
        ],
    )

def create_bulk_preset_edit_modal():
    """一括登録プリセットの新規追加・編集用モーダル（2カラムレイアウト）"""
    return dbc.Modal(
        id="bulk-preset-edit-modal",
        is_open=False,
        size="xl",
        children=[
            dbc.ModalHeader(dbc.ModalTitle(id="bulk-preset-edit-modal-title")),
            dbc.ModalBody([
                dbc.Alert(id="bulk-preset-edit-alert", is_open=False),
                dcc.Store(id='editing-preset-id-store'),
                dcc.Store(id='preset-selected-books-store', data=[]),
                dbc.Form([
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("科目"),
                            dcc.Dropdown(id="preset-subject-input"),
                        ], width=6),
                        dbc.Col([
                            dbc.Label("プリセット名"),
                            dbc.Input(id="preset-name-input", type="text"),
                        ], width=6),
                    ], className="mb-3"),
                    html.Hr(),
                    dbc.Row([
                        dbc.Col([
                            html.H5("選択可能な参考書"),
                            dbc.Row([
                                dbc.Col(dcc.Dropdown(id='preset-book-subject-filter', placeholder="科目で絞り込み..."), width=4),
                                dbc.Col(dcc.Dropdown(id='preset-book-level-filter', placeholder="レベルで絞り込み..."), width=4),
                                dbc.Col(dbc.Input(id='preset-book-name-filter', placeholder="参考書名..."), width=4),
                            ], className="mb-2"),
                            dcc.Loading(
                                html.Div(
                                    id='preset-available-books-list',
                                    style={'maxHeight': '300px', 'overflowY': 'auto', 'border': '1px solid #ccc', 'borderRadius': '5px', 'padding': '10px'}
                                )
                            ),
                        ], md=6),
                        dbc.Col([
                            html.H5("選択済みの参考書"),
                            dcc.Loading(
                                html.Div(
                                    id='preset-selected-books-list',
                                    style={'maxHeight': '350px', 'overflowY': 'auto', 'border': '1px solid #ccc', 'borderRadius': '5px', 'padding': '10px'}
                                )
                            ),
                        ], md=6),
                    ]),
                ])
            ]),
            dbc.ModalFooter([
                dbc.Button("保存", id="save-bulk-preset-btn", color="primary"),
                dbc.Button("キャンセル", id="cancel-bulk-preset-edit-btn"),
            ]),
        ],
    )

def create_user_edit_modal():
    """ユーザー編集用のモーダルを生成する"""
    return dbc.Modal(
        id="user-edit-modal",
        is_open=False,
        children=[
            dbc.ModalHeader(dbc.ModalTitle(id="user-edit-modal-title")),
            dbc.ModalBody([
                dbc.Alert(id="user-edit-alert", is_open=False),
                dcc.Store(id='editing-user-id-store'),
                dbc.Form([
                    dbc.Row([
                        dbc.Label("ユーザー名", width=3),
                        dbc.Col(dbc.Input(id="user-username-input", type="text"), width=9),
                    ], className="mb-3"),
                    dbc.Row([
                        dbc.Label("役割", width=3),
                        dbc.Col(dcc.Dropdown(
                            id='user-role-input',
                            options=[
                                {'label': '一般ユーザー', 'value': 'user'},
                                {'label': '管理者', 'value': 'admin'},
                            ]
                        ), width=9),
                    ], className="mb-3"),
                    dbc.Row([
                        dbc.Label("所属校舎", width=3),
                        dbc.Col(dbc.Input(id="user-school-input", type="text"), width=9),
                    ]),
                ])
            ]),
            dbc.ModalFooter([
                dbc.Button("保存", id="save-user-btn", color="primary"),
                dbc.Button("キャンセル", id="cancel-user-edit-btn"),
            ]),
        ],
    )

def create_add_changelog_modal():
    """更新履歴追加用のモーダルを生成する"""
    return dbc.Modal(
        id="add-changelog-modal",
        is_open=False,
        children=[
            dbc.ModalHeader(dbc.ModalTitle("更新履歴を追加")),
            dbc.ModalBody([
                dbc.Alert(id="changelog-modal-alert", is_open=False),
                dbc.Row([
                    dbc.Label("バージョン", width=3),
                    dbc.Col(dbc.Input(id="changelog-version-input", placeholder="例: 1.2.0"), width=9),
                ], className="mb-3"),
                dbc.Row([
                    dbc.Label("タイトル", width=3),
                    dbc.Col(dbc.Input(id="changelog-title-input", placeholder="変更点の概要"), width=9),
                ], className="mb-3"),
                dbc.Row([
                    dbc.Label("詳細", width=3),
                    dbc.Col(dbc.Textarea(id="changelog-description-input", rows=4), width=9),
                ]),
            ]),
            dbc.ModalFooter([
                dbc.Button("保存", id="save-changelog-btn", color="primary"),
                dbc.Button("キャンセル", id="cancel-changelog-btn", className="ms-auto"),
            ]),
        ],
    )


# ★★★ 模試結果一覧モーダルを新設 ★★★
def create_mock_exam_list_modal():
    """校舎全体の模試結果一覧を表示・検索するためのモーダル"""
    return dbc.Modal(
        id="mock-exam-list-modal",
        is_open=False,
        size="xl", # 大きなモーダル
        scrollable=True,
        children=[
            dbc.ModalHeader(dbc.ModalTitle("校舎 模試結果一覧")),
            dbc.ModalBody([
                dbc.Row([
                    # フィルター群
                    dbc.Col(dcc.Dropdown(
                        id='mock-exam-list-filter-type',
                        options=[
                            {'label': '自己採点', 'value': '自己採点'},
                            {'label': '結果', 'value': '結果'}
                        ],
                        placeholder="種類 (自己採点/結果)...",
                        clearable=True
                    ), width=12, md=3, className="mb-2"),
                    dbc.Col(dcc.Dropdown(
                        id='mock-exam-list-filter-name',
                        placeholder="模試名...",
                        clearable=True
                    ), width=12, md=3, className="mb-2"),
                    dbc.Col(dcc.Dropdown(
                        id='mock-exam-list-filter-format',
                        options=[
                            {'label': 'マーク', 'value': 'マーク'},
                            {'label': '記述', 'value': '記述'}
                        ],
                        placeholder="形式 (マーク/記述)...",
                        clearable=True
                    ), width=12, md=3, className="mb-2"),
                    dbc.Col(dcc.Dropdown(
                        id='mock-exam-list-filter-grade',
                        placeholder="学年...",
                        clearable=True
                    ), width=12, md=3, className="mb-2"),
                ], className="mb-3"),

                # ★★★ テーブル表示エリアをタブに変更 ★★★
                dbc.Tabs(
                    [
                        dbc.Tab(
                            dcc.Loading(
                                html.Div(id="mock-exam-list-table-container-mark", style={"minHeight": "200px"}),
                            ),
                            label="マーク模試",
                            tab_id="tab-mock-list-mark",
                        ),
                        dbc.Tab(
                            dcc.Loading(
                                html.Div(id="mock-exam-list-table-container-descriptive", style={"minHeight": "200px"}),
                            ),
                            label="記述模試",
                            tab_id="tab-mock-list-descriptive",
                        ),
                    ],
                    id="mock-exam-list-tabs",
                    active_tab="tab-mock-list-mark", # デフォルトでマークタブをアクティブに
                )
            ]),
            dbc.ModalFooter(dbc.Button("閉じる", id="close-mock-exam-list-modal", className="ms-auto")),
        ],
    )