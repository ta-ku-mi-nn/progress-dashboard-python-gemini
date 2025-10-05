"""
生徒の学習計画テーブルの表示と更新に関連するコールバックを定義します。
"""
import json
import dash
from dash import Input, Output, State, html, callback_context, no_update
import dash_bootstrap_components as dbc

# データベース操作用のヘルパー関数をインポート
from data.nested_json_processor import get_student_progress, update_progress_status

def register_student_callbacks(app, _data):
    """
    生徒の学習計画や進捗を管理するUIのコールバックを登録します。

    Args:
        app (dash.Dash): Dashアプリケーションインスタンス。
        _data: データベース移行に伴い、この引数は直接は使用しません。
    """

    # 生徒の学習計画テーブルを更新するコールバック
    @app.callback(
        Output('student-progress-table', 'children'),
        [Input('student-dropdown', 'value')],
        [State('school-dropdown', 'value')]
    )
    def update_student_progress_table(selected_student, selected_school):
        if not selected_student or not selected_school:
            return dbc.Alert("校舎と生徒を選択してください。", color="info", className="mt-3")

        # データベースから生徒の進捗データを取得
        student_progress = get_student_progress(selected_school, selected_student)

        if not student_progress:
            return dbc.Alert(f"「{selected_student}」さんの学習計画が見つかりません。", color="warning", className="mt-3")

        accordions = []
        for subject, levels in sorted(student_progress.items()):
            table_header = [html.Thead(html.Tr([
                html.Th("ルート"), html.Th("参考書名"), html.Th("予定"), html.Th("達成済")
            ]))]

            rows = []
            for level, books in sorted(levels.items()):
                for i, (book_name, details) in enumerate(books.items()):
                    # IDを一意に特定するための文字列を作成
                    row_id = f'{selected_school}-{selected_student}-{subject}-{level}-{book_name}'
                    row = html.Tr([
                        html.Td(level) if i == 0 else html.Td(),
                        html.Td(book_name),
                        html.Td(dbc.Checkbox(
                            id={'type': 'plan-checkbox', 'id': row_id},
                            value=details.get('予定', False)
                        )),
                        html.Td(dbc.Checkbox(
                            id={'type': 'done-checkbox', 'id': row_id},
                            value=details.get('達成済', False)
                        )),
                    ])
                    rows.append(row)

            table = dbc.Table(
                table_header + [html.Tbody(rows)],
                bordered=True, striped=True, hover=True, responsive=True, size='sm'
            )
            accordions.append(dbc.AccordionItem(children=table, title=subject))

        return dbc.Accordion(accordions, start_collapsed=True, always_open=True, className="mt-3")

    # チェックボックスの変更をデータベースに反映するコールバック
    @app.callback(
        Output('success-toast', 'is_open'),
        [Input({'type': 'plan-checkbox', 'id': dash.ALL}, 'value'),
         Input({'type': 'done-checkbox', 'id': dash.ALL}, 'value')],
        prevent_initial_call=True
    )
    def update_student_data(_plan_values, _done_values):
        """
        チェックボックスの値が変更されたときに、データベースを更新する。
        """
        ctx = callback_context
        if not ctx.triggered:
            return no_update

        # 変更されたチェックボックスの情報を解析
        trigger_id_dict = json.loads(ctx.triggered[0]['prop_id'].split('.')[0])
        component_type = trigger_id_dict['type']
        school, student, subject, level, book_name = trigger_id_dict['id'].split('-')
        new_value = ctx.triggered[0]['value']

        # 更新対象のカラム名を決定
        column_to_update = 'is_planned' if component_type == 'plan-checkbox' else 'is_done'

        # データベース更新関数を呼び出し
        success, _message = update_progress_status(
            school, student, subject, level, book_name, column_to_update, new_value
        )

        # 成功した場合のみトーストを表示
        return success