import dash
import base64
import json
from dash import Input, Output, State, callback, html, ctx, dcc  # ctx (callback_contextの短縮) を追加
import dash_bootstrap_components as dbc
from data.nested_json_processor import save_root_table, get_all_root_tables, get_root_table_by_id

def register_root_table_callbacks(app):
    # 一覧の更新とアップロード処理
    @app.callback(
        [Output('root-table-list', 'children'),
         Output('upload-status-msg', 'children')],
        [Input('upload-root-table', 'contents'),
         Input('auth-store', 'data')],
        [State('upload-root-table', 'filename')],
        prevent_initial_call=False
    )
    def update_list_and_upload(contents, auth_data, filename):
        msg = ""
        # アップロード処理 (管理者のみ)
        # 権限チェックは既存の仕組みを利用
        if contents and auth_data and auth_data.get('role') == 'admin':
            try:
                content_type, content_string = contents.split(',')
                decoded = base64.b64decode(content_string)
                success, res_msg = save_root_table(filename, decoded)
                msg = dbc.Alert(res_msg, color="success" if success else "danger", duration=3000)
            except Exception as e:
                msg = dbc.Alert(f"エラーが発生しました: {e}", color="danger", duration=3000)

        # リスト生成
        tables = get_all_root_tables()
        if not tables:
            return [html.P("登録されているルート表はありません。", className="text-muted")], msg

        list_items = [
            dbc.ListGroupItem([
                html.Span(t['filename']),
                # パターンマッチングIDを使用
                dbc.Button("ダウンロード", id={'type': 'btn-download-rt', 'index': t['id']}, 
                           size="sm", color="link", className="float-end")
            ]) for t in tables
        ]
        return list_items, msg

    # ダウンロード実行
    @app.callback(
        Output("download-root-table", "data"),
        # dash.dependencies.ALL (または単に ALL) を使用するために import dash が必要
        Input({'type': 'btn-download-rt', 'index': dash.dependencies.ALL}, 'n_clicks'),
        prevent_initial_call=True
    )
    def download_file(n_clicks):
        # ctx.triggered を使ってどのボタンが押されたか判定 (dash 2.4以降の推奨)
        if not ctx.triggered or not any(n_clicks):
            return None
        
        # 押されたボタンのID（json文字列）を取得してパース
        try:
            prop_id = ctx.triggered[0]['prop_id']
            button_id_json = prop_id.split('.')[0]
            button_id = json.loads(button_id_json)
            file_id = button_id['index']
            
            file_data = get_root_table_by_id(file_id)
            if file_data:
                # 取得したバイナリデータをブラウザへ送信
                return dcc.send_bytes(file_data['file_content'], file_data['filename'])
        except Exception as e:
            print(f"Download error: {e}")
            
        return None