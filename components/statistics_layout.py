# components/statistics_layout.py (全体)

from dash import dcc, html
import dash_bootstrap_components as dbc

def create_statistics_layout(user_info):
    """
    統計ページのレイアウトを生成します。
    校舎、学年、科目での絞り込み機能を追加。
    """
    if not user_info:
        return html.Div()

    # 校舎フィルター (管理者の場合は全校舎を選択可能に、それ以外は自校舎のみ)
    school_filter_options = [] # コールバックで設定
    school_filter_disabled = True # コールバックで設定
    default_school = user_info.get('school', None)

    # 学年フィルター
    grade_filter_options = [] # コールバックで設定

    return dbc.Container([
        html.H3("学習レベル統計", className="my-4", style={"border-left": "solid 5px #7db4e6", "padding": "10px"}),
        dbc.Row([
            # ★ 校舎フィルターを追加
            dbc.Col(
                dcc.Dropdown(
                    id='statistics-school-filter',
                    placeholder="校舎を選択...",
                    options=school_filter_options,
                    value=default_school, # ログインユーザーの校舎をデフォルトに
                    disabled=school_filter_disabled,
                    clearable=False # 校舎選択は必須とする
                ),
                width=12, md=3,
                className="mb-3"
            ),
            # ★ 学年フィルターを追加
            dbc.Col(
                dcc.Dropdown(
                    id='statistics-grade-filter',
                    placeholder="学年で絞り込み (任意)...",
                    options=grade_filter_options,
                    clearable=True # 学年絞り込みは任意
                ),
                width=12, md=3,
                className="mb-3"
            ),
            # 科目フィルター (変更なし)
            dbc.Col(
                dcc.Dropdown(
                    id='statistics-subject-filter',
                    placeholder="科目を選択...",
                    clearable=False # 科目選択は必須とする
                ),
                width=12, md=4,
                className="mb-3"
            )
        ]),
        dcc.Loading(html.Div(id='statistics-content-container')),
    ], fluid=True)