# components/root_table_layout.py
from dash import dcc, html
import dash_bootstrap_components as dbc
from data.nested_json_processor import get_all_subjects
from datetime import datetime

def create_root_table_layout(user_info):
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

    return dbc.Container([
        html.H3("指導要領（ルート表）一覧", className="mt-4 mb-4"),
        filter_card,
        html.Div(id='rt-list-container'),
        dcc.Download(id="rt-download-component")
    ], fluid=True)