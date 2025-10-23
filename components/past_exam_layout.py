# components/past_exam_layout.py
from dash import dcc, html
# dash_table は不要になったので削除
import dash_bootstrap_components as dbc
from datetime import date
import datetime # datetime をインポート

def create_past_exam_layout():
    """過去問管理ページのメインレイアウトを生成する"""

    # --- 既存の過去問管理タブの内容 ---
    past_exam_tab_content = html.Div([
        # 編集/削除対象のIDを保持するStore
        dcc.Store(id='editing-past-exam-id-store'),

        dbc.Row([
            dbc.Col([
                html.H4("過去問演習記録"),
                html.P("フォームの結果を反映するためには入力ボタン横の更新ボタンを押してください", className="text-muted"),
                html.A("過去問結果入力フォームはこちら", href="https://forms.gle/tGSPWBU6tv5dUogNA", target="_blank", rel="noopener noreferrer")
            ]), # H2からH4に変更
            dbc.Col([ # Pass children as a list
                dbc.Button("過去問結果を入力する", id="open-past-exam-modal-btn", color="success", className="me-2"),
                dbc.Button(html.I(className="fas fa-sync-alt"), id="refresh-past-exam-table-btn", color="secondary", outline=True, title="最新の情報に更新"),
            ], className="text-end") # Pass className as a keyword argument
        ], align="center", className="my-4"),

        # フィルター
        dbc.Row([
            dbc.Col(
                dcc.Dropdown(id='past-exam-university-filter', placeholder="大学名で絞り込み..."),
                width=12, md=4
            ),
            dbc.Col(
                dcc.Dropdown(id='past-exam-subject-filter', placeholder="科目で絞り込み..."),
                width=12, md=4
            )
        ], className="mb-3"),

        # 結果テーブル表示エリア
        dcc.Loading(html.Div(id="past-exam-table-container")),

        # 入力・編集用モーダル (内容は変更なし)
        dbc.Modal([
             dbc.ModalHeader(dbc.ModalTitle(id="past-exam-modal-title")),
             dbc.ModalBody([
                 dbc.Alert(id="past-exam-modal-alert", is_open=False),
                 dbc.Row([
                     dbc.Col(dbc.Label("日付"), width=4),
                     dbc.Col(dcc.DatePickerSingle(id='past-exam-date', date=date.today()), width=8)
                 ], className="mb-3"),
                 dbc.Row([
                     dbc.Col(dbc.Label("大学名"), width=4),
                     dbc.Col(dbc.Input(id='past-exam-university', type='text'), width=8)
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
                     dbc.Col(dbc.Input(id='past-exam-year', type='number', min=2000, step=1), width=8)
                 ], className="mb-3"),
                 dbc.Row([
                     dbc.Col(dbc.Label("科目"), width=4),
                     dbc.Col(dbc.Input(id='past-exam-subject', type='text'), width=8)
                 ], className="mb-3"),
                 dbc.Row([
                     dbc.Col(dbc.Label("所要時間(分)"), width=4),
                     dbc.Col(dbc.Input(id='past-exam-time', type='text', placeholder="例: 60/80"), width=8)
                 ], className="mb-3"),
                 dbc.Row([
                     dbc.Col(dbc.Label("正答数"), width=4),
                     dbc.Col(dbc.Input(id='past-exam-correct', type='number', min=0), width=8)
                 ], className="mb-3"),
                 dbc.Row([
                     dbc.Col(dbc.Label("問題数"), width=4),
                     dbc.Col(dbc.Input(id='past-exam-total', type='number', min=1), width=8)
                 ], className="mb-3"),
             ]),
             dbc.ModalFooter([
                 dbc.Button("キャンセル", id="cancel-past-exam-modal-btn", color="secondary"),
                 dbc.Button("保存", id="save-past-exam-modal-btn", color="primary"),
             ]),
         ], id="past-exam-modal", is_open=False),

        # 削除確認ダイアログ (内容は変更なし)
        dcc.ConfirmDialog(
            id='delete-past-exam-confirm',
            message='本当にこの結果を削除しますか？\nこの操作は取り消せません。',
        ),
    ])

    # --- 既存の大学合否タブの内容 ---
    acceptance_tab_content = html.Div([
        dcc.Store(id='editing-acceptance-id-store'),
        dbc.Row([
            dbc.Col([
                html.H4("入試管理"),
                html.P("フォームの結果を反映するためには入力ボタン横の更新ボタンを押してください", className="text-muted"),
                html.A("入試日程入力フォームはこちら", href="https://forms.gle/3PPyxk3Bw5vSsmBb8", target="_blank", rel="noopener noreferrer")
            ]),
            dbc.Col([ # Pass children as a list
                dbc.Button("入試予定を入力する", id="open-acceptance-modal-btn", color="success", className="me-2"),
                dbc.Button(html.I(className="fas fa-sync-alt"), id="refresh-acceptance-table-btn", color="secondary", outline=True, title="最新の情報に更新"),
            ], className="text-end") # Pass className as a keyword argument
        ], align="center", className="my-4"),
        dcc.Loading(html.Div(id="acceptance-table-container")), # テーブル表示エリア
        dbc.Modal([ # 合否モーダル (日付入力含む)
            dbc.ModalHeader(dbc.ModalTitle(id="acceptance-modal-title")),
            dbc.ModalBody([
                dbc.Alert(id="acceptance-modal-alert", is_open=False),
                dbc.Row([
                    dbc.Col(dbc.Label("大学名"), width=4),
                    dbc.Col(dbc.Input(id='acceptance-university', type='text', required=True), width=8)
                ], className="mb-3"),
                dbc.Row([
                    dbc.Col(dbc.Label("学部名"), width=4),
                    dbc.Col(dbc.Input(id='acceptance-faculty', type='text', required=True), width=8)
                ], className="mb-3"),
                dbc.Row([
                    dbc.Col(dbc.Label("学科名（任意）"), width=4),
                    dbc.Col(dbc.Input(id='acceptance-department', type='text'), width=8)
                ], className="mb-3"),
                dbc.Row([
                    dbc.Col(dbc.Label("受験方式（任意）"), width=4),
                    dbc.Col(dbc.Input(id='acceptance-system', type='text'), width=8)
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
                dbc.Button("キャンセル", id="cancel-acceptance-modal-btn", color="secondary"),
                dbc.Button("保存", id="save-acceptance-modal-btn", color="primary"),
            ]),
        ], id="acceptance-modal", is_open=False),
        dcc.ConfirmDialog( # 合否削除確認 (内容は変更なし)
            id='delete-acceptance-confirm',
            message='本当にこの合否結果を削除しますか？\nこの操作は取り消せません。',
        ),
    ])

    # --- 「受験スケジュール」タブの内容 ---
    calendar_tab_content = html.Div([
        dcc.Store(id='current-calendar-month-store'), # ★ Storeを復活
        dbc.Row([
            dbc.Col([
                html.H4("受験カレンダー"),
                html.P("フォームの結果を反映するためには入力ボタン横の更新ボタンを押してください", className="text-muted", id="calendar-print-hide-text")
            ]),
            dbc.Col([
                dbc.ButtonGroup([
                    dbc.Button("<< 前月", id="prev-month-btn", outline=True, color="secondary"),
                    dbc.Button("次月 >>", id="next-month-btn", outline=True, color="secondary"),
                ]),
                dbc.Button(html.I(className="fas fa-print"), id="print-calendar-btn", color="info", outline=True, title="カレンダーを印刷", className="ms-2"),
                dbc.Button(html.I(className="fas fa-sync-alt"), id="refresh-calendar-btn", color="secondary", outline=True, title="最新の情報に更新", className="ms-2"),
            ], width='auto', className="ms-auto", id="calendar-action-buttons")
        ], align="center", className="my-4", id="calendar-header-row"),

        # Web表示用カレンダー
        dcc.Loading(
            # IDを変更し、印刷時は非表示にするクラスを追加
            html.Div(id="web-calendar-container", className="printable-hide", style={'overflowX': 'auto'})
        ),
        # ★ 印刷専用エリアを追加 (通常は非表示)
        html.Div(id="printable-calendar-area", className="printable-only", style={'display': 'none'}),

    ], id="calendar-tab-content-wrapper")

    # --- タブ構造 (変更なし) ---
    return html.Div([
        dbc.Tabs(
            [
                dbc.Tab(past_exam_tab_content, label="過去問管理", tab_id="tab-past-exam"),
                dbc.Tab(acceptance_tab_content, label="入試管理", tab_id="tab-acceptance"),
                dbc.Tab(calendar_tab_content, label="受験スケジュール", tab_id="tab-gantt"),
            ],
            id="past-exam-tabs",
            active_tab="tab-past-exam",
        )
    ])