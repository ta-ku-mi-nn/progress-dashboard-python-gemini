from dash import html
import dash_bootstrap_components as dbc

def create_howto_layout(user_info):
    return html.Div([
        dbc.Row([
            dbc.Col(html.H1("使い方")),
        ], className="my-4"),

        dbc.Container(html.H1("この機能はただいま準備中です。"), className="text-center my-5"),
    ])