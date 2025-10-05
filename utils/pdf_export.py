# PDFエクスポート用のユーティリティ
import io
import plotly.io as pio
from dash import dcc
from dash.dependencies import Input, Output, State
from flask import send_file

def register_pdf_export_callback(app, fig_id, button_id, download_id):
    @app.callback(
        Output(download_id, "data"),
        [Input(button_id, "n_clicks")],
        [State(fig_id, "figure")],
        prevent_initial_call=True
    )
    def export_pdf(n_clicks, figure):
        if n_clicks:
            # Plotly figureをPDFバイトに変換
            buf = io.BytesIO()
            pio.write_image(figure, buf, format="pdf")
            buf.seek(0)
            return dcc.send_bytes(buf.read(), filename="graph.pdf")
        return None
