from dash import dcc, html
import dash_bootstrap_components as dbc
from data.nested_json_processor import get_all_subjects
from datetime import datetime

def create_root_table_layout(user_info):
    is_admin = user_info.get('role') == 'admin'
    subjects = get_all_subjects()
    levels = ['基礎徹底', '日大', 'MARCH', '早慶']
    years = [datetime.now().year - i for i in range(5)]

    # 絞り込みフィルター
    filter_card = dbc.Card(dbc.CardBody([
        dbc.Row([
            dbc.Col([
                html.Label("科目", className="small"),
                dcc.Dropdown(id='rt-filter-subject', options=[{'label': s, 'value': s} for s in subjects], placeholder="全科目")
            ], md=4),
            dbc.Col([
                html.Label("レベル", className="small"),
                dcc.Dropdown(id='rt-filter-level', options=[{'label': l, 'value': l} for l in levels], placeholder="全レベル")
            ], md=4),
            dbc.Col([
                html.Label("年度", className="small"),
                dcc.Dropdown(id='rt-filter-year', options=[{'label': str(y), 'value': y} for y in years], placeholder="全年度")
            ], md=4),
        ])
    ]), className="mb-4 shadow-sm")

    # アップロードエリア (管理者のみ)
    upload_area = dbc.Collapse(
        dbc.Card(dbc.CardBody([
            html.H5("ルート表の新規アップロード"),
            dbc.Row([
                dbc.Col(dcc.Dropdown(id='rt-upload-subject', options=[{'label': s, 'value': s} for s in subjects], placeholder="科目を選択"), md=3),
                dbc.Col(dcc.Dropdown(id='rt-upload-level', options=[{'label': l, 'value': l} for l in levels], placeholder="レベルを選択"), md=3),
                dbc.Col(dcc.Dropdown(id='rt-upload-year', options=[{'label': str(y), 'value': y} for y in years], placeholder="年度を選択"), md=2),
                dbc.Col(dcc.Upload(id='rt-upload-file', children=dbc.Button("PDFを選択", color="primary", outline=True, className="w-100")), md=4),
            ], className="mb-2"),
            html.Div(id='rt-upload-status')
        ]), className="mb-4 border-primary"),
        is_open=is_admin
    )

    return dbc.Container([
        html.H3("指導要領（ルート表）管理", className="mt-4 mb-4"),
        upload_area,
        filter_card,
        html.Div(id='rt-list-container'),
        dcc.Download(id="rt-download-component")
    ], fluid=True)