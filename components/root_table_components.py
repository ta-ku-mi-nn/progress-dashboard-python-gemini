from dash import dcc, html
import dash_bootstrap_components as dbc

def create_root_table_layout(user_info):
    # 管理者権限のチェック
    is_admin = user_info.get('role') == 'admin' if user_info else False

    upload_component = html.Div([
        html.H5("新規アップロード (管理者のみ)", className="card-title"),
        dcc.Upload(
            id='upload-root-table',
            children=dbc.Button("PDFファイルを選択", color="primary", outline=True),
            multiple=False
        ),
        html.Div(id='upload-status-msg', className="mt-2 small")
    ], className="mb-4") if is_admin else html.Div()

    return dbc.Card([
        dbc.CardHeader(html.H4("指導要領（ルート表）", className="mb-0")),
        dbc.CardBody([
            upload_component,
            html.H5("公開中のルート表一覧"),
            dbc.ListGroup(id='root-table-list', flush=True),
            dcc.Download(id="download-root-table")
        ])
    ], className="shadow-sm border-0 fade-in") # styles.pyのfade-inアニメーションを適用