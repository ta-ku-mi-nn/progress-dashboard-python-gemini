# components/past_exam_layout.py

from dash import dcc, html
import dash_bootstrap_components as dbc
from datetime import date

def create_past_exam_layout():
    """過去問管理ページのメインレイアウトを生成する"""

    return html.Div([
        # 編集/削除対象のIDを保持するStore
        dcc.Store(id='editing-past-exam-id-store'),

        dbc.Row([
            dbc.Col(html.H2("過去問管理")),
            dbc.Col(
                dbc.Button("過去問結果を入力する", id="open-past-exam-modal-btn", color="success"),
                className="text-end"
            )
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

        # 入力・編集用モーダル
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

        # 削除確認ダイアログ
        dcc.ConfirmDialog(
            id='delete-past-exam-confirm',
            message='本当にこの結果を削除しますか？\nこの操作は取り消せません。',
        ),
    ])