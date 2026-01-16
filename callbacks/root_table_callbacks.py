# callbacks/root_table_callbacks.py
import dash
from dash import dcc, html, Input, Output, State, ctx, ALL
import dash_bootstrap_components as dbc
from data.nested_json_processor import get_filtered_root_tables, get_root_table_by_id

def register_root_table_callbacks(app):
    # 絞り込み & 更新後のリスト表示のみに限定
    @app.callback(
        Output('rt-list-container', 'children'),
        [Input('rt-filter-subject', 'value'),
         Input('rt-filter-level', 'value'),
         Input('rt-filter-year', 'value'),
         Input('admin-update-trigger', 'data')]
    )
    def update_root_table_view(f_subj, f_lvl, f_year, admin_trigger):
        # データの取得
        rows = get_filtered_root_tables(f_subj, f_lvl, f_year)
        
        if not rows:
            return html.Div("該当するルート表が見つかりません。", className="text-muted p-3")

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

        return dbc.Table(table_header + table_body, hover=True, striped=True, className="bg-white shadow-sm")

    # ダウンロード処理 (変更なし)
    @app.callback(
        Output("rt-download-component", "data"),
        Input({'type': 'rt-dl-btn', 'index': ALL}, 'n_clicks'),
        prevent_initial_call=True
    )
    def handle_rt_download(n_clicks):
        if not ctx.triggered or not any(n_clicks): 
            return dash.no_update
        
        triggered_id = ctx.triggered_id
        if not isinstance(triggered_id, dict) or triggered_id.get('type') != 'rt-dl-btn':
            return dash.no_update
            
        file_id = triggered_id['index']
        file_data = get_root_table_by_id(file_id)
        
        if file_data:
            return dcc.send_bytes(bytes(file_data['file_content']), file_data['filename'])
        return dash.no_update