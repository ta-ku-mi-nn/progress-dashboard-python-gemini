# callbacks/report_callbacks.py

from dash import Input, Output, State

def register_report_callbacks(app):
    """ブラウザ印刷をトリガーするコールバックを登録します。"""

    app.clientside_callback(
        """
        function(n_clicks) {
            // ボタンがクリックされた場合のみ動作します
            if (n_clicks === undefined || n_clicks === null) {
                return window.dash_clientside.no_update;
            }
            
            // ブラウザの印刷ダイアログを呼び出します
            window.print();

            return window.dash_clientside.no_update;
        }
        """,
        Output("download-pdf-report", "data"), # ダミーの出力先
        Input("download-report-btn", "n_clicks"),
        # student_idは不要なのでStateから削除
        prevent_initial_call=True
    )