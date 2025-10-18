# components/statistics_layout.py

from dash import dcc, html
import dash_bootstrap_components as dbc

def create_statistics_layout(user_info):
    """
    校舎内統計ページのレイアウトを生成します。
    """
    if not user_info:
        return html.Div()

    school = user_info.get('school', '校舎不明')

    return dbc.Container([
        html.H3(f"{school} の学習レベル統計", className="my-4"),
        dbc.Row([
            dbc.Col(
                dcc.Dropdown(
                    id='statistics-subject-filter',
                    placeholder="科目を選択...",
                ),
                width=12, md=4,
                className="mb-3"
            )
        ]),
        dcc.Loading(html.Div(id='statistics-content-container')),
    ], fluid=True)