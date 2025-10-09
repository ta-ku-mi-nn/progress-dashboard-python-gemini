# callbacks/report_callbacks.py

from dash import Input, Output, State

def register_report_callbacks(app):
    """PDFレポート生成に関連するコールバックを登録します。"""

    # --- ★★★ ここから修正 ★★★ ---
    # このクライアントサイドコールバックは、レポートを新しいタブで開きます。
    # サーバーサイドのロジックは、app_main.pyのFlaskルートで処理されます。
    app.clientside_callback(
        """
        function(n_clicks, student_id) {
            // ボタンがクリックされ、かつ生徒が選択されている場合のみ動作します
            if (n_clicks === undefined || n_clicks === null || !student_id) {
                return window.dash_clientside.no_update;
            }
            
            // URLを組み立てて、新しいタブで開きます
            const url = `/report/pdf/${student_id}`;
            window.open(url);

            // ダウンロードはトリガーしないため、更新なしを返します
            return window.dash_clientside.no_update;
        }
        """,
        Output("download-pdf-report", "data"), # これはダミーの出力先です
        Input("download-report-btn", "n_clicks"),
        State("student-selection-store", "data"),
        prevent_initial_call=True
    )
    # --- ★★★ ここまで修正 ★★★ ---