# components/past_exam_layout.py
from dash import dcc, html
import dash_bootstrap_components as dbc
from datetime import date
import datetime # datetime をインポート

# === ヘルパー関数: 模試結果モーダルの作成 ===
def _create_mock_exam_modal():
    """模試結果の追加・編集を行うモーダルを生成する"""
    return dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle(id="mock-exam-modal-title")),
        dbc.ModalBody([
            dbc.Alert(id="mock-exam-modal-alert", is_open=False),
            # --- 必須項目 ---
            dbc.Row([
                dbc.Col(dbc.Label("種類 *"), width=4),
                dbc.Col(dcc.Dropdown(id='mock-exam-result-type', options=[
                    {'label': '自己採点', 'value': '自己採点'},
                    {'label': '結果', 'value': '結果'}
                ], placeholder="自己採点か結果かを選択..."), width=8)
            ], className="mb-3"),
            dbc.Row([
                dbc.Col(dbc.Label("模試名 *"), width=4),
                # ★ 自由記述に変更
                dbc.Col(dbc.Input(id='mock-exam-name', type='text', placeholder="例: 共通テスト模試"), width=8)
            ], className="mb-3"),
            dbc.Row([
                dbc.Col(dbc.Label("形式 *"), width=4),
                # ★ 選択肢を固定
                dbc.Col(dcc.Dropdown(id='mock-exam-format', options=[
                    {'label': 'マーク', 'value': 'マーク'},
                    {'label': '記述', 'value': '記述'}
                ], placeholder="マークか記述を選択..."), width=8)
            ], className="mb-3"),
             dbc.Row([
                dbc.Col(dbc.Label("学年 *"), width=4),
                # ★ 選択肢を変更・固定
                dbc.Col(dcc.Dropdown(id='mock-exam-grade', options=[
                    {'label': '中学生', 'value': '中学生'},
                    {'label': '高1', 'value': '高1'},
                    {'label': '高2', 'value': '高2'},
                    {'label': '高3', 'value': '高3'}
                ], placeholder="学年を選択..."), width=8)
            ], className="mb-3"),
             dbc.Row([
                dbc.Col(dbc.Label("回数 *"), width=4),
                # ★ 自由記述に変更
                dbc.Col(dbc.Input(id='mock-exam-round', type='text', placeholder="例: 第1回"), width=8)
            ], className="mb-3"),
            # --- 任意項目 ---
            dbc.Row([
                dbc.Col(dbc.Label("受験日"), width=4),
                dbc.Col(dcc.DatePickerSingle(id='mock-exam-date', date=None, display_format='YYYY-MM-DD'), width=8)
            ], className="mb-3"),
            html.Hr(),

            # ★★★ 修正箇所: 点数入力を2カラムレイアウトに変更 ★★★
            dbc.Row([
                # --- 左列: マーク科目 ---
                dbc.Col([
                    html.H5("マーク科目 点数", className="mt-4"),
                    dbc.Row([
                        dbc.Col(dbc.Label("国語"), width=4),
                        dbc.Col(dbc.Input(id='mock-exam-kokugo-mark', type='number', min=0), width=8)
                    ], className="mb-2"),
                    dbc.Row([
                        dbc.Col(dbc.Label("数学ⅠA"), width=4),
                        dbc.Col(dbc.Input(id='mock-exam-math1a-mark', type='number', min=0), width=8)
                    ], className="mb-2"),
                    dbc.Row([
                        dbc.Col(dbc.Label("数学ⅡBC"), width=4),
                        dbc.Col(dbc.Input(id='mock-exam-math2bc-mark', type='number', min=0), width=8)
                    ], className="mb-2"),
                     dbc.Row([
                        dbc.Col(dbc.Label("英語R"), width=4),
                        dbc.Col(dbc.Input(id='mock-exam-english-r-mark', type='number', min=0), width=8)
                    ], className="mb-2"),
                     dbc.Row([
                        dbc.Col(dbc.Label("英語L"), width=4),
                        dbc.Col(dbc.Input(id='mock-exam-english-l-mark', type='number', min=0), width=8)
                    ], className="mb-2"),
                     dbc.Row([
                        dbc.Col(dbc.Label("理科①"), width=4),
                        dbc.Col(dbc.Input(id='mock-exam-rika1-mark', type='number', min=0), width=8)
                    ], className="mb-2"),
                    dbc.Row([
                        dbc.Col(dbc.Label("理科②"), width=4),
                        dbc.Col(dbc.Input(id='mock-exam-rika2-mark', type='number', min=0), width=8)
                    ], className="mb-2"),
                     dbc.Row([
                        dbc.Col(dbc.Label("社会①"), width=4),
                        dbc.Col(dbc.Input(id='mock-exam-shakai1-mark', type='number', min=0), width=8)
                    ], className="mb-2"),
                     dbc.Row([
                        dbc.Col(dbc.Label("社会②"), width=4),
                        dbc.Col(dbc.Input(id='mock-exam-shakai2-mark', type='number', min=0), width=8)
                    ], className="mb-2"),
                     dbc.Row([
                        dbc.Col(dbc.Label("理科基礎①"), width=4),
                        dbc.Col(dbc.Input(id='mock-exam-rika-kiso1-mark', type='number', min=0), width=8)
                    ], className="mb-2"),
                     dbc.Row([
                        dbc.Col(dbc.Label("理科基礎②"), width=4),
                        dbc.Col(dbc.Input(id='mock-exam-rika-kiso2-mark', type='number', min=0), width=8)
                    ], className="mb-2"),
                     dbc.Row([
                        dbc.Col(dbc.Label("情報"), width=4),
                        dbc.Col(dbc.Input(id='mock-exam-info-mark', type='number', min=0), width=8)
                    ], className="mb-2"),
                ], md=6),
                
                # --- 右列: 記述科目 ---
                dbc.Col([
                    html.H5("記述科目 点数", className="mt-4"),
                    dbc.Row([
                        dbc.Col(dbc.Label("国語"), width=4),
                        dbc.Col(dbc.Input(id='mock-exam-kokugo-desc', type='number', min=0), width=8)
                    ], className="mb-2"),
                    dbc.Row([
                        dbc.Col(dbc.Label("数学"), width=4),
                        dbc.Col(dbc.Input(id='mock-exam-math-desc', type='number', min=0), width=8)
                    ], className="mb-2"),
                    dbc.Row([
                        dbc.Col(dbc.Label("英語"), width=4),
                        dbc.Col(dbc.Input(id='mock-exam-english-desc', type='number', min=0), width=8)
                    ], className="mb-2"),
                    dbc.Row([
                        dbc.Col(dbc.Label("理科①"), width=4),
                        dbc.Col(dbc.Input(id='mock-exam-rika1-desc', type='number', min=0), width=8)
                    ], className="mb-2"),
                     dbc.Row([
                        dbc.Col(dbc.Label("理科②"), width=4),
                        dbc.Col(dbc.Input(id='mock-exam-rika2-desc', type='number', min=0), width=8)
                    ], className="mb-2"),
                     dbc.Row([
                        dbc.Col(dbc.Label("社会①"), width=4),
                        dbc.Col(dbc.Input(id='mock-exam-shakai1-desc', type='number', min=0), width=8)
                    ], className="mb-2"),
                    dbc.Row([
                        dbc.Col(dbc.Label("社会②"), width=4),
                        dbc.Col(dbc.Input(id='mock-exam-shakai2-desc', type='number', min=0), width=8)
                    ], className="mb-2"),
                ], md=6),
            ]),
            # ★★★ 修正ここまで ★★★
        ]),
        dbc.ModalFooter([
            dbc.Button("削除", id="delete-mock-exam-btn", color="danger", className="me-auto", outline=True), # 削除ボタン追加
            dbc.Button("キャンセル", id="cancel-mock-exam-modal-btn", color="secondary"),
            dbc.Button("保存", id="save-mock-exam-modal-btn", color="primary"),
        ]),
    ], id="mock-exam-modal", is_open=False, size="lg") # sizeをlgに

# === ヘルパー関数: 各タブの内容を作成 ===
def _create_past_exam_tab():
    """過去問管理タブの内容を作成"""
    return html.Div([
        dcc.Store(id='editing-past-exam-id-store'),
        dbc.Row([
            dbc.Col([
                html.H4("過去問演習記録", style={"border-left": "solid 5px #7db4e6", "padding": "10px"}),
                html.P("フォームの結果を反映するためには入力ボタン横の更新ボタンを押してください", className="text-muted"),
                html.A("過去問結果入力フォームはこちら", href="https://forms.gle/swYQQdhDrryRNLjL7", target="_blank", rel="noopener noreferrer") # 要変更
            ]),
            dbc.Col([
                dbc.Button("過去問結果を入力する", id="open-past-exam-modal-btn", color="success", className="me-2"),
                dbc.Button(html.I(className="fas fa-sync-alt"), id="refresh-past-exam-table-btn", color="secondary", outline=True, title="最新の情報に更新"),
            ], className="text-end")
        ], align="center", className="my-4"),
        dbc.Row([
            dbc.Col(dcc.Dropdown(id='past-exam-university-filter', placeholder="大学名で絞り込み..."), width=12, md=4),
            dbc.Col(dcc.Dropdown(id='past-exam-subject-filter', placeholder="科目で絞り込み..."), width=12, md=4)
        ], className="mb-3"),
        dcc.Loading(html.Div(id="past-exam-table-container")),
        dbc.Modal([ # 過去問モーダル
             dbc.ModalHeader(dbc.ModalTitle(id="past-exam-modal-title")),
             dbc.ModalBody([
                 dbc.Alert(id="past-exam-modal-alert", is_open=False),
                 dbc.Row([
                     dbc.Col(dbc.Label("日付"), width=4),
                     dbc.Col(dcc.DatePickerSingle(id='past-exam-date', date=date.today()), width=8)
                 ], className="mb-3"),
                 dbc.Row([
                     dbc.Col(dbc.Label("大学名"), width=4),
                     dbc.Col(dbc.Input(id='past-exam-university', type='text', required=True), width=8) # required追加
                 ], className="mb-3"),
                 dbc.Row([
                     dbc.Col(dbc.Label("学部名"), width=4),
                     dbc.Col(dbc.Input(id='past-exam-faculty', type='text'), width=8)
                 ], className="mb-3"),
                 dbc.Row([
                     dbc.Col(dbc.Label("入試方式"), width=4),
                     dbc.Col(dbc.Input(id='past-exam-system', type='text'), width=8)
                 ], className="mb-3"),
                 dbc.Row([
                     dbc.Col(dbc.Label("年度"), width=4),
                     dbc.Col(dbc.Input(id='past-exam-year', type='number', min=2000, step=1, required=True), width=8) # required追加
                 ], className="mb-3"),
                 dbc.Row([
                     dbc.Col(dbc.Label("科目"), width=4),
                     dbc.Col(dbc.Input(id='past-exam-subject', type='text', required=True), width=8) # required追加
                 ], className="mb-3"),
                 dbc.Row([
                     dbc.Col(dbc.Label("所要時間(分)"), width=4),
                     dbc.Col(dbc.Input(id='past-exam-time', type='text', placeholder="例: 60 または 60/80"), width=8) # placeholder変更
                 ], className="mb-3"),
                 dbc.Row([
                     dbc.Col(dbc.Label("正答数"), width=4),
                     dbc.Col(dbc.Input(id='past-exam-correct', type='number', min=0), width=8)
                 ], className="mb-3"),
                 dbc.Row([
                     dbc.Col(dbc.Label("問題数"), width=4),
                     dbc.Col(dbc.Input(id='past-exam-total', type='number', min=1, required=True), width=8) # required追加
                 ], className="mb-3"),
             ]),
             dbc.ModalFooter([
                 dbc.Button("削除", id="delete-past-exam-btn", color="danger", className="me-auto", outline=True), # 削除ボタン追加
                 dbc.Button("キャンセル", id="cancel-past-exam-modal-btn", color="secondary"),
                 dbc.Button("保存", id="save-past-exam-modal-btn", color="primary"),
             ]),
         ], id="past-exam-modal", is_open=False),
        dcc.ConfirmDialog(id='delete-past-exam-confirm', message='本当にこの過去問結果を削除しますか？'),
    ])

def _create_acceptance_tab():
    """入試管理タブの内容を作成"""
    return html.Div([
        dcc.Store(id='editing-acceptance-id-store'),
        dbc.Row([
            dbc.Col([
                html.H4("入試管理", style={"border-left": "solid 5px #7db4e6", "padding": "10px"}), # 左線を追加
                html.P("フォームの結果を反映するためには入力ボタン横の更新ボタンを押してください", className="text-muted"),
                html.A("入試日程入力フォームはこちら", href="https://forms.gle/32AzVyUF1pRuDQRy9", target="_blank", rel="noopener noreferrer") # 要変更
            ]),
            dbc.Col([
                dbc.Button("入試予定を入力する", id="open-acceptance-modal-btn", color="success", className="me-2"),
                dbc.Button(html.I(className="fas fa-sync-alt"), id="refresh-acceptance-table-btn", color="secondary", outline=True, title="最新の情報に更新"),
            ], className="text-end")
        ], align="center", className="my-4"),
        dcc.Loading(html.Div(id="acceptance-table-container")),
        dbc.Modal([ # 合否モーダル
            dbc.ModalHeader(dbc.ModalTitle(id="acceptance-modal-title")),
            dbc.ModalBody([
                dbc.Alert(id="acceptance-modal-alert", is_open=False),
                dbc.Row([
                    dbc.Col(dbc.Label("大学名 *"), width=4),
                    dbc.Col(dbc.Input(id='acceptance-university', type='text', required=True), width=8)
                ], className="mb-3"),
                dbc.Row([
                    dbc.Col(dbc.Label("学部名 *"), width=4),
                    dbc.Col(dbc.Input(id='acceptance-faculty', type='text', required=True), width=8)
                ], className="mb-3"),
                dbc.Row([
                    dbc.Col(dbc.Label("学科名"), width=4),
                    dbc.Col(dbc.Input(id='acceptance-department', type='text'), width=8)
                ], className="mb-3"),
                dbc.Row([
                    dbc.Col(dbc.Label("受験方式"), width=4),
                    dbc.Col(dbc.Input(id='acceptance-system', type='text'), width=8)
                ], className="mb-3"),
                 dbc.Row([ # 合否結果ドロップダウンを追加
                    dbc.Col(dbc.Label("合否結果"), width=4),
                    dbc.Col(dcc.Dropdown(id='acceptance-result', options=[
                        {'label': '未定', 'value': ''}, {'label': '合格', 'value': '合格'},
                        {'label': '不合格', 'value': '不合格'}, {'label': '補欠', 'value': '補欠'}
                    ], value='', clearable=False), width=8)
                ], className="mb-3"),
                dbc.Row([
                    dbc.Col(dbc.Label("出願期日"), width=4),
                    dbc.Col(dcc.DatePickerSingle(id='acceptance-application-deadline', date=None, display_format='YYYY-MM-DD'), width=8)
                ], className="mb-3"),
                dbc.Row([
                    dbc.Col(dbc.Label("受験日"), width=4),
                    dbc.Col(dcc.DatePickerSingle(id='acceptance-exam-date', date=None, display_format='YYYY-MM-DD'), width=8)
                ], className="mb-3"),
                dbc.Row([
                    dbc.Col(dbc.Label("合格発表日"), width=4),
                    dbc.Col(dcc.DatePickerSingle(id='acceptance-announcement-date', date=None, display_format='YYYY-MM-DD'), width=8)
                ], className="mb-3"),
                dbc.Row([
                    dbc.Col(dbc.Label("入学手続期日"), width=4),
                    dbc.Col(dcc.DatePickerSingle(id='acceptance-procedure-deadline', date=None, display_format='YYYY-MM-DD'), width=8)
                ], className="mb-3"),
            ]),
            dbc.ModalFooter([
                 dbc.Button("削除", id="delete-acceptance-btn", color="danger", className="me-auto", outline=True), # 削除ボタン追加
                 dbc.Button("キャンセル", id="cancel-acceptance-modal-btn", color="secondary"),
                 dbc.Button("保存", id="save-acceptance-modal-btn", color="primary"),
            ]),
        ], id="acceptance-modal", is_open=False),
        dcc.ConfirmDialog(id='delete-acceptance-confirm', message='本当にこの入試情報を削除しますか？'),
    ])

def _create_calendar_tab():
    """受験スケジュールタブの内容を作成"""
    return html.Div([
        dcc.Store(id='current-calendar-month-store'),
        dbc.Row([
            dbc.Col([
                html.H4("受験カレンダー", style={"border-left": "solid 5px #7db4e6", "padding": "10px"}),
                html.P("フォームの結果を反映するためには入力ボタン横の更新ボタンを押してください", className="text-muted", id="calendar-print-hide-text")
            ]),
            dbc.Col([
                html.Div(id='current-month-display', className="text-center fw-bold fs-5 mb-2 printable-hide"), # 現在年月表示
                dbc.ButtonGroup([
                    dbc.Button("<< 前月", id="prev-month-btn", outline=True, color="secondary"),
                    dbc.Button("次月 >>", id="next-month-btn", outline=True, color="secondary"),
                ], className="printable-hide"),
                dbc.Button(html.I(className="fas fa-print"), id="print-calendar-btn", color="info", outline=True, title="カレンダーを印刷", className="ms-2 printable-hide"),
                dbc.Button(html.I(className="fas fa-sync-alt"), id="refresh-calendar-btn", color="secondary", outline=True, title="最新の情報に更新", className="ms-2 printable-hide"),
            ], width='auto', className="ms-auto", id="calendar-action-buttons")
        ], align="center", className="my-4", id="calendar-header-row"),
        dcc.Loading(html.Div(id="web-calendar-container", className="printable-hide", style={'overflowX': 'auto'})),
        html.Div(id="printable-calendar-area", className="printable-only", style={'display': 'none'}),
    ], id="calendar-tab-content-wrapper")

# ★★★ 新しいヘルパー関数: 模試結果タブの内容を作成 ★★★
def _create_mock_exam_tab():
    """模試結果タブの内容を作成"""
    return html.Div([
        dcc.Store(id='editing-mock-exam-id-store'), # 編集/削除用IDストア
        dbc.Row([
            dbc.Col([
                html.H4("模試結果記録", style={"border-left": "solid 5px #7db4e6", "padding": "10px"}),
                html.P("フォームの結果を反映するためには入力ボタン横の更新ボタンを押してください", className="text-muted"),
                html.A("模試結果入力フォームはこちら", href="https://docs.google.com/forms/d/e/1FAIpQLSdh-ODgOadM3JeHHnuVpnymclRJQ6ejRLWoWcEQoHZTOiiLoA/viewform?usp=header", target="_blank", rel="noopener noreferrer") # 要変更
            ]),
            dbc.Col([
                dbc.Button("模試結果を入力する", id="open-mock-exam-modal-btn", color="success", className="me-2"),
                dbc.Button(html.I(className="fas fa-sync-alt"), id="refresh-mock-exam-table-btn", color="secondary", outline=True, title="最新の情報に更新"),
            ], className="text-end")
        ], align="center", className="my-4"),

        # フィルター (必要であれば後で追加)
        # dbc.Row([...], className="mb-3"),

        html.H5("マーク模試 結果", className="mt-4"),
        dcc.Loading(html.Div(id="mock-exam-mark-table-container")),

        html.H5("記述模試 結果", className="mt-4"),
        dcc.Loading(html.Div(id="mock-exam-descriptive-table-container")),

        # 入力・編集用モーダル
        _create_mock_exam_modal(),

        # 削除確認ダイアログ
        dcc.ConfirmDialog(
            id='delete-mock-exam-confirm',
            message='本当にこの模試結果を削除しますか？\nこの操作は取り消せません。',
        ),
    ])

# === メインレイアウト生成関数 ===
def create_past_exam_layout():
    """過去問・入試管理・模試結果ページのメインレイアウトを生成する"""

    # 各タブの内容をヘルパー関数で生成
    past_exam_tab_content = _create_past_exam_tab()
    acceptance_tab_content = _create_acceptance_tab()
    calendar_tab_content = _create_calendar_tab()
    mock_exam_tab_content = _create_mock_exam_tab() # ★ 模試結果タブの内容を生成

    # タブ構造
    return html.Div([
        dbc.Tabs(
            [
                dbc.Tab(past_exam_tab_content, label="過去問管理", tab_id="tab-past-exam"),
                dbc.Tab(acceptance_tab_content, label="入試管理", tab_id="tab-acceptance"),
                dbc.Tab(calendar_tab_content, label="受験スケジュール", tab_id="tab-gantt"),
                dbc.Tab(mock_exam_tab_content, label="模試結果", tab_id="tab-mock-exam"), # ★ 模試結果タブを追加
            ],
            id="past-exam-tabs",
            active_tab="tab-past-exam", # デフォルトで過去問タブをアクティブに
        )
    ])
