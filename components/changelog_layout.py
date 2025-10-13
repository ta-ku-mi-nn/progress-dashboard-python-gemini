# components/changelog_layout.py

from dash import html
import dash_bootstrap_components as dbc
from data.nested_json_processor import get_all_changelog_entries

def create_changelog_layout():
    """更新履歴ページのレイアウトを生成する"""
    
    entries = get_all_changelog_entries()
    
    if not entries:
        return dbc.Alert("更新履歴はありません。", color="info")
        
    # ▼ ここから追加 ▼
    # バージョン番号で降順にソートする
    # 'v'プレフィックスを削除し、'.'で分割して数値のリストに変換して比較
    sorted_entries = sorted(
        entries, 
        key=lambda e: [int(part) for part in e['version'].lstrip('v').split('.')], 
        reverse=True
    )
    # ▲ ここまで追加 ▲
        
    timeline_items = []
    # イテレートする対象をソート済みのリストに変更
    for entry in sorted_entries:
        timeline_items.append(
            html.Div([
                # 'v'がバージョン文字列に含まれていない場合を想定し、f-stringで付与
                html.H4(f"v{entry['version']} - {entry['title']}", className="mb-1"),
                html.Small(f"リリース日: {entry['release_date']}", className="text-muted"),
                html.P(entry['description'], className="mt-2")
            ], className="mb-4")
        )

    return html.Div([
        html.H1("更新履歴", className="my-4"),
        *timeline_items
    ])