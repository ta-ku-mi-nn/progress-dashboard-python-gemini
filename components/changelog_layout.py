# components/changelog_layout.py

from dash import html
import dash_bootstrap_components as dbc
import pandas as pd
from data.nested_json_processor import get_all_changelog_entries

def create_changelog_layout():
    """更新履歴ページのレイアウトを生成する"""

    entries = get_all_changelog_entries()

    if not entries:
        return dbc.Alert("更新履歴はありません。", color="info")

    # バージョン番号で降順にソートする
    # 'v'プレフィックスを削除し、'.'で分割して数値のリストに変換して比較
    sorted_entries = sorted(
        entries,
        key=lambda e: [int(part) for part in e['version'].lstrip('v').split('.')],
        reverse=True
    )

    # テーブルのヘッダーを作成
    table_header = [
        html.Thead(html.Tr([
            html.Th("バージョン"),
            html.Th("リリース日"),
            html.Th("タイトル"),
            html.Th("詳細")
        ]))
    ]

    # テーブルのボディ（各行）を作成
    table_body = [
        html.Tbody([
            html.Tr([
                html.Td(f"v{entry['version']}"),
                html.Td(entry['release_date']),
                html.Td(entry['title']),
                html.Td(entry['description'])
            ]) for entry in sorted_entries
        ])
    ]

    # レイアウトを返す
    return html.Div([
        html.H3("更新履歴", className="my-4"),
        dbc.Table(
            table_header + table_body,
            bordered=True,
            striped=True,
            hover=True,
            responsive=True,
            className="mt-4"
        )
    ])