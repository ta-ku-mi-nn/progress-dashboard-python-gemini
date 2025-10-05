"""
生徒の学習計画テーブルの表示と更新に関連するコールバックを定義します。
"""
import json
import dash
from dash import Input, Output, State, html, callback_context, no_update
import dash_bootstrap_components as dbc

from data.nested_json_processor import get_student_progress

def register_student_callbacks(app, data):
    """
    生徒の学習計画や進捗を管理するUIのコールバックを登録します。

    Args:
        app (dash.Dash): Dashアプリケーションインスタンス。
        data (dict): アプリケーション起動時に読み込まれた全データ。
    """

    # 生徒の学習計画テーブルを更新するコールバック
    @app.callback(
        Output('student-progress-table', 'children'),
        [Input('student-dropdown', 'value')],
        [State('school-dropdown', 'value')]
    )
    def update_student_progress_table(selected_student, selected_school):
        if not selected_student or not selected_school:
            return dbc.Alert("校舎と生徒を選択してください。", color="info")

        student_progress = get_student_progress(data, selected_school, selected_student)

        if not student_progress:
            return dbc.Alert(f"「{selected_student}」さんの進捗データが見つかりません。", color="warning")

        accordions = []
        for subject, levels in sorted(student_progress.items()):
            table_header = [html.Thead(html.Tr([
                html.Th("ルート"), html.Th("参考書名"), html.Th("予定"), html.Th("達成済")
            ]))]

            rows = []
            for level, books in sorted(levels.items()):
                for i, (book_name, details) in enumerate(books.items()):
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

        if not accordions:
            return dbc.Alert("この生徒には学習計画がありません。", color="info")

        return dbc.Accordion(accordions, start_collapsed=True, always_open=True, className="mt-3")

    # チェックボックスの変更をデータに反映するコールバック
    @app.callback(
        Output('success-toast', 'is_open'),
        [Input({'type': 'plan-checkbox', 'id': dash.ALL}, 'value'),
         Input({'type': 'done-checkbox', 'id': dash.ALL}, 'value')],
        prevent_initial_call=True
    )
    def update_student_data(_plan_values, _done_values):
        """
        チェックボックスの値が変更されたときに、メモリ上の`data`オブジェクトを更新する。
        _plan_valuesと_done_valuesはコールバックのトリガーとして必要だが、関数内では未使用。
        """
        ctx = callback_context
        if not ctx.triggered:
            return no_update

        trigger_id_dict = json.loads(ctx.triggered[0]['prop_id'].split('.')[0])
        component_type = trigger_id_dict['type']
        school, student, subject, level, book_name = trigger_id_dict['id'].split('-')
        new_value = ctx.triggered[0]['value']

        try:
            target_book = data[school][student]['progress'][subject][level][book_name]
            if component_type == 'plan-checkbox':
                target_book['予定'] = new_value
            elif component_type == 'done-checkbox':
                target_book['達成済'] = new_value

            # 変更成功のトーストを表示
            return True
        except KeyError:
            print("Error: データ更新中にキーエラーが発生しました。")
            return no_update