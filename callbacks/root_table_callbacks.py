import dash
from dash import dcc, html, Input, Output, State, ctx, ALL
import dash_bootstrap_components as dbc
import base64
import json
from data.nested_json_processor import save_root_table_with_tags, get_filtered_root_tables, get_root_table_by_id

def register_root_table_callbacks(app):
    # 絞り込み & アップロード後のリスト更新
    @app.callback(
        [Output('rt-list-container', 'children'),
         Output('rt-upload-status', 'children')],
        [Input('rt-filter-subject', 'value'),
         Input('rt-filter-level', 'value'),
         Input('rt-filter-year', 'value'),
         Input('rt-upload-file', 'contents')],
        [State('rt-upload-file', 'filename'),
         State('rt-upload-subject', 'value'),
         State('rt-upload-level', 'value'),
         State('rt-upload-year', 'value'),
         State('auth-store', 'data')]
    )
    def update_root_table_view(f_subj, f_lvl, f_year, upload_contents, filename, u_subj, u_lvl, u_year, auth_data):
        trigger = ctx.triggered_id
        status_msg = ""

        # アップロード処理
        if trigger == 'rt-upload-file' and upload_contents:
            if auth_data.get('role') != 'admin':
                status_msg = dbc.Alert("権限がありません", color="danger")
            elif not all([u_subj, u_lvl, u_year]):
                status_msg = dbc.Alert("タグ（科目・レベル・年度）をすべて選択してください", color="warning")
            else:
                _, content_string = upload_contents.split(',')
                decoded = base64.b64decode(content_string)
                success, msg = save_root_table_with_tags(filename, decoded, u_subj, u_lvl, u_year)
                status_msg = dbc.Alert(msg, color="success" if success else "danger")

        # データの取得とテーブル生成
        rows = get_filtered_root_tables(f_subj, f_lvl, f_year)
        
        table_header = [html.Thead(html.Tr([
            html.Th("年度"), html.Th("科目"), html.Th("レベル"), html.Th("ファイル名"), html.Th("操作")
        ]))]
        
        table_body = [html.Tbody([
            html.Tr([
                html.Td(r['academic_year']),
                html.Td(r['subject']),
                html.Td(r['level']),
                html.Td(r['filename']),
                html.Td(dbc.Button("DL", id={'type': 'rt-dl-btn', 'index': r['id']}, color="link", size="sm"))
            ]) for r in rows
        ])]

        return dbc.Table(table_header + table_body, hover=True, striped=True, className="bg-white"), status_msg

    # ダウンロード処理
    @app.callback(
        Output("rt-download-component", "data"),
        Input({'type': 'rt-dl-btn', 'index': ALL}, 'n_clicks'),
        prevent_initial_call=True
    )
    def handle_rt_download(n_clicks):
        if not ctx.triggered or not any(n_clicks): return dash.no_update
        
        button_id = json.loads(ctx.triggered[0]['prop_id'].split('.')[0])
        file_id = button_id['index']
        file_data = get_root_table_by_id(file_id)
        
        if file_data:
            return dcc.send_bytes(file_data['file_content'], file_data['filename'])
        return dash.no_update