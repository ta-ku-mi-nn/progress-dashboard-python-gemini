import dash
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objs as go
import os
import json

# CSV読み込み
csv_path = os.path.join(os.path.dirname(__file__), 'route-subject-text-time.csv')
# 達成割合を文字列として読み込み
df = pd.read_csv(csv_path, dtype={'達成割合': 'str'})

# 旧「ユーザー」列から「生徒」列への変換（下位互換性確保）
if 'ユーザー' in df.columns and '生徒' not in df.columns:
    df = df.rename(columns={'ユーザー': '生徒'})
    # CSVファイルを更新して列名を変更
    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print("CSVの「ユーザー」列を「生徒」列に変更しました")

# 進捗用の列を追加（初期値False）
if '予定' not in df.columns:
    df['予定'] = False
if '達成済' not in df.columns:
    df['達成済'] = False
if '達成割合' not in df.columns:
    df['達成割合'] = ''
if '生徒' not in df.columns:
    df['生徒'] = 'デフォルト生徒'  # デフォルト生徒を設定
    # CSVファイルを更新して生徒列を追加
    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
else:
    # 達成割合のNaN値を空文字列に変換
    df['達成割合'] = df['達成割合'].fillna('').astype(str)
    # 'nan'文字列も空文字列に変換
    df.loc[df['達成割合'] == 'nan', '達成割合'] = ''
    # 生徒列のNaN値をデフォルト生徒に変換
    df['生徒'] = df['生徒'].fillna('デフォルト生徒').astype(str)
    df.loc[df['生徒'] == 'nan', '生徒'] = 'デフォルト生徒'

app = dash.Dash(__name__, external_stylesheets=[
    dbc.themes.BOOTSTRAP, 
    "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css"
], suppress_callback_exceptions=True)

# 正方形コンテナ用のCSS
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
        /* 全体フォント設定 */
        body {
            font-family: 'Segoe UI', 'Yu Gothic UI', 'Meiryo UI', 'Hiragino Sans', 'Hiragino Kaku Gothic ProN', sans-serif !important;
            font-weight: 400;
            line-height: 1.6;
        }
        
        /* 科目選択ボタンの改善 */
        .subject-selection-btn {
            font-family: 'Segoe UI', 'Yu Gothic UI', 'Meiryo UI', sans-serif !important;
            font-size: 1.1rem !important;
            font-weight: 600 !important;
            padding: 15px 20px !important;
            border-radius: 12px !important;
            border: 2px solid #007bff !important;
            transition: all 0.3s ease !important;
            text-align: center !important;
            letter-spacing: 0.5px !important;
        }
        
        .subject-selection-btn:hover {
            transform: translateY(-3px) !important;
            box-shadow: 0 8px 25px rgba(0, 123, 255, 0.3) !important;
            border-color: #0056b3 !important;
            background: linear-gradient(135deg, #007bff 0%, #0056b3 100%) !important;
            color: white !important;
        }
        
        .subject-selection-btn i {
            font-size: 1.2em !important;
            margin-right: 8px !important;
        }
        
        .square-container {
            position: relative;
            width: 100%;
            aspect-ratio: 1 / 1; /* モダンブラウザ用 */
        }
        
        /* 古いブラウザ用フォールバック */
        @supports not (aspect-ratio: 1 / 1) {
            .square-container::before {
                content: '';
                display: block;
                padding-top: 100%;
            }
            .square-container > div {
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
            }
        }
        
        /* カードホバー効果 */
        .subject-card-hover:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.15) !important;
        }
        
        /* レスポンシブ対応: 横幅770-1400pxでのテキスト調整 */
        @media (min-width: 770px) and (max-width: 1400px) {
            .square-container {
                min-height: 200px;
            }
        }
        
        @media (min-width: 770px) and (max-width: 991px) {
            .square-container {
                min-height: 180px;
            }
        }
        
        /* チェックボックのカスタムスタイル */
        .custom-checkbox {
            appearance: none;
            width: 20px;
            height: 20px;
            border: 2px solid #007bff;
            border-radius: 4px;
            background-color: white;
            cursor: pointer;
            position: relative;
            transition: all 0.2s ease;
            margin-right: 8px;
        }
        
        .custom-checkbox:checked {
            background-color: #007bff;
            border-color: #007bff;
            transform: scale(1.05);
        }
        
        .custom-checkbox:checked::after {
            content: '✓';
            position: absolute;
            color: white;
            font-size: 14px;
            font-weight: bold;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
        }
        
        .custom-checkbox:hover {
            border-color: #0056b3;
            box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.1);
        }
        
        /* 達成チェックボックスタイル */
        .done-checkbox {
            border-color: #28a745;
        }
        
        .done-checkbox:checked {
            background-color: #28a745;
            border-color: #28a745;
        }
        
        .done-checkbox:hover {
            border-color: #1e7e34;
            box-shadow: 0 0 0 3px rgba(40, 167, 69, 0.1);
        }
        
        /* チェックボックコンテナ */
        .checkbox-container {
            display: flex;
            align-items: center;
            justify-content: center;
            flex-direction: column;
            padding: 8px;
            border-radius: 8px;
            transition: background-color 0.2s ease;
        }
        
        .checkbox-container:hover {
            background-color: rgba(0, 123, 255, 0.05);
        }
        
        .checkbox-label {
            font-size: 12px;
            font-weight: 600;
            margin-bottom: 4px;
        }
        
        /* モダンなカードスタイル */
        .card {
            border: none !important;
            border-radius: 15px !important;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.08) !important;
            transition: all 0.3s ease !important;
        }
        
        .card:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15) !important;
        }
        
        .card-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
            color: white !important;
            border: none !important;
            border-top-left-radius: 15px !important;
            border-top-right-radius: 15px !important;
            padding: 12px 20px !important;
        }
        
        /* ナビバー改善 */
        .navbar {
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1) !important;
            border-radius: 0 0 15px 15px !important;
        }
        
        .navbar-brand {
            font-size: 1.4rem !important;
            font-weight: 700 !important;
        }
        
        /* ボタンスタイル改善 */
        .btn {
            border-radius: 10px !important;
            font-weight: 600 !important;
            transition: all 0.3s ease !important;
            border: none !important;
        }
        
        .btn:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15) !important;
        }
        
        .btn-primary {
            background: linear-gradient(135deg, #007bff 0%, #0056b3 100%) !important;
        }
        
        .btn-info {
            background: linear-gradient(135deg, #17a2b8 0%, #138496 100%) !important;
        }
        
        .btn-secondary {
            background: linear-gradient(135deg, #6c757d 0%, #5a6268 100%) !important;
        }
        
        .btn-success {
            background: linear-gradient(135deg, #28a745 0%, #1e7e34 100%) !important;
        }
        
        .btn-danger {
            background: linear-gradient(135deg, #dc3545 0%, #c82333 100%) !important;
        }
        
        .btn-warning {
            background: linear-gradient(135deg, #ffc107 0%, #e0a800 100%) !important;
            color: #212529 !important;
        }
        
        /* グラフエリア改善 */
        .js-plotly-plot {
            border-radius: 12px !important;
            overflow: hidden !important;
        }
        
        /* サイドメニュー固定 */
        .sticky-menu {
            position: sticky !important;
            top: 20px !important;
            z-index: 1000 !important;
        }
        
        /* レスポンシブ改善 */
        @media (max-width: 768px) {
            .col-md-2 {
                margin-bottom: 20px !important;
            }
            
            .sticky-menu {
                position: relative !important;
                top: 0 !important;
            }
            
            .navbar-brand {
                font-size: 1.2rem !important;
            }
        }
        
        /* アニメーション */
        .fade-in {
            animation: fadeIn 0.5s ease-in !important;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        /* プログレスバー改善 */
        .progress {
            height: 8px !important;
            border-radius: 10px !important;
            background-color: #f1f3f4 !important;
        }
        
        .progress-bar {
            border-radius: 10px !important;
            background: linear-gradient(90deg, #4facfe 0%, #00f2fe 100%) !important;
        }
        
        /* グラフアニメーション効果 */
        .js-plotly-plot {
            animation: graphFadeIn 1.2s ease-out !important;
        }
        
        @keyframes graphFadeIn {
            0% { 
                opacity: 0;
                transform: scale(0.9) translateY(20px);
            }
            50% {
                opacity: 0.6;
                transform: scale(0.95) translateY(10px);
            }
            100% { 
                opacity: 1;
                transform: scale(1) translateY(0);
            }
        }
        
        /* グラフホバー効果 */
        .js-plotly-plot:hover {
            transform: scale(1.02) !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        }
        
        /* 円グラフ専用アニメーション */
        div[id*="subject-pie-chart"] .js-plotly-plot {
            animation: pieChartSpin 1.5s ease-out !important;
        }
        
        @keyframes pieChartSpin {
            0% { 
                opacity: 0;
                transform: rotate(-90deg) scale(0.8);
            }
            70% {
                opacity: 0.8;
                transform: rotate(10deg) scale(1.05);
            }
            100% { 
                opacity: 1;
                transform: rotate(0deg) scale(1);
            }
        }
        
        /* バーグラフ専用アニメーション - 左から右に伸びる */
        div[id="progress-bar-graph"] .js-plotly-plot {
            animation: barSlideLeft 1.5s ease-out !important;
        }
        
        @keyframes barSlideLeft {
            0% { 
                opacity: 0;
                transform: translateX(-50px) scaleX(0.1);
                clip-path: inset(0 100% 0 0);
            }
            60% {
                opacity: 0.8;
                transform: translateX(5px) scaleX(1.05);
                clip-path: inset(0 10% 0 0);
            }
            100% { 
                opacity: 1;
                transform: translateX(0) scaleX(1);
                clip-path: inset(0 0% 0 0);
            }
        }
        
        /* 液体コンテナアニメーション */
        .liquid-wave {
            animation: liquidWave 2s ease-in-out infinite alternate;
        }
        
        @keyframes liquidWave {
            0% {
                transform: scaleY(0.98);
                filter: brightness(1);
            }
            100% {
                transform: scaleY(1.02);
                filter: brightness(1.1);
            }
        }
        
        /* 科目カードのホバーエフェクト強化 */
        .subject-card-hover {
            transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        }
        
        .subject-card-hover:hover {
            transform: translateY(-8px) scale(1.02);
            box-shadow: 0 12px 35px rgba(0,0,0,0.15);
        }
        
        /* 達成率コンテナのグロー効果 */
        .achievement-glow {
            box-shadow: 0 0 20px rgba(40, 167, 69, 0.3);
        }
        
        .achievement-glow-warning {
            box-shadow: 0 0 15px rgba(255, 193, 7, 0.3);
        }
        
        .achievement-glow-danger {
            box-shadow: 0 0 15px rgba(220, 53, 69, 0.3);
        }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# 科目リストと生徒リスト
subjects = df['科目'].unique()
users = df['生徒'].unique()
current_user = users[0] if len(users) > 0 else 'デフォルト生徒'

# 達成割合を考慮した進捗時間計算関数
def calculate_progress_time(row):
    """新しい達成率計算: 達成済み時間 + 達成割合による時間"""
    try:
        # データ型チェック
        if not isinstance(row, pd.Series):
            print(f"Warning: Invalid row type: {type(row)}")
            return 0
            
        base_time = float(row.get('所要時間', 0))
        if base_time <= 0:
            return 0
        
        # 達成済みの場合は全時間を返す
        if row.get('達成済', False):
            return base_time
        
        # 達成済みでない場合は達成割合を確認
        ratio_val = row.get('達成割合', '')
        if pd.isna(ratio_val) or str(ratio_val).strip() in ['', '0', '0.0', 'nan']:
            return 0
    except (KeyError, ValueError, AttributeError) as e:
        print(f"Error in calculate_progress_time initial checks: {e}")
        return 0
    
    try:
        # 分数形式の達成割合を解析 (例: "3/5" -> 0.6)
        if '/' in str(ratio_val):
            parts = str(ratio_val).split('/')
            if len(parts) == 2:
                numerator, denominator = map(float, parts)  # floatに変更して小数対応
                ratio = numerator / denominator if denominator != 0 else 0
            else:
                raise ValueError("Invalid fraction format")
        else:
            # 小数形式の場合
            ratio = float(ratio_val)
            # 100以上の場合はパーセンテージとして扱う
            if ratio > 1:
                ratio = ratio / 100
        
        # 比率が0-1の範囲外の場合は制限
        ratio = max(0, min(1, ratio))
        
        # 所要時間に達成割合をかけて進捗時間を計算
        return base_time * ratio
    except (ValueError, ZeroDivisionError, KeyError):
        return 0

# 新しい達成率計算関数
def calculate_achievement_rate(df_subject):
    """新仕様の達成率計算: (達成済所要時間の和+(達成割合×所要時間)の和)/(予定所要時間)"""
    try:
        if df_subject is None or df_subject.empty:
            return 0
            
        df_planned = df_subject[df_subject['予定'] == True].copy()
        if df_planned.empty:
            return 0
        
        # 所要時間の合計を安全に計算
        try:
            total_planned_time = pd.to_numeric(df_planned['所要時間'], errors='coerce').fillna(0).sum()
        except Exception as e:
            print(f"Error calculating total_planned_time: {e}")
            return 0
            
        if total_planned_time <= 0:
            return 0
        
        # 達成済みの所要時間の和
        try:
            done_time = pd.to_numeric(df_planned[df_planned['達成済'] == True]['所要時間'], errors='coerce').fillna(0).sum()
        except Exception as e:
            print(f"Error calculating done_time: {e}")
            done_time = 0
        
        # 達成割合による時間の和（達成済みでないもののみ）
        try:
            df_not_done = df_planned[df_planned['達成済'] == False].copy()
            if df_not_done.empty:
                ratio_time = 0
            else:
                ratio_time = df_not_done.apply(calculate_progress_time, axis=1).fillna(0).sum()
        except Exception as e:
            print(f"Error calculating ratio_time: {e}")
            ratio_time = 0
        
        # 達成率 = (達成済み時間 + 達成割合時間) / 予定時間 * 100
        try:
            achievement_rate = ((done_time + ratio_time) / total_planned_time) * 100
            return min(100, max(0, achievement_rate))  # 0-100%の範囲に制限
        except Exception as e:
            print(f"Error calculating final achievement_rate: {e}")
            return 0
            
    except Exception as e:
        print(f"Fatal error in calculate_achievement_rate: {e}")
        return 0

app.layout = dbc.Container([
    # ヘッダー
    dbc.Navbar([
        dbc.Container([
            dbc.NavbarBrand(
                [
                    html.I(className="fas fa-chart-line me-2"),
                    "学習進捗ダッシュボード"
                ],
                href="#",
                style={"fontSize": "1.5rem", "fontWeight": "bold"}
            ),
            dbc.Nav([
                dbc.NavItem(dbc.NavLink("📈 ダッシュボード", href="#dashboard", active=True)),
                dbc.NavItem(dbc.NavLink("📊 統計", href="#stats")),
            ], navbar=True),
        ])
    ], color="dark", dark=True, className="mb-4"),
    
    # メインコンテンツ - サイドメニューレイアウト
    html.Div(id="dashboard", children=[
        dbc.Row([
            # 左サイドメニュー
            dbc.Col([
                # 進捗更新メニュー
                dbc.Card([
                    dbc.CardHeader([
                        html.H6("� 操作メニュー", className="mb-0")
                    ]),
                    dbc.CardBody([
                        dbc.Button(
                            [
                                html.I(className="fas fa-user-graduate me-2"),
                                "生徒選択"
                            ],
                            id="open-student-selection-modal",
                            color="info",
                            className="w-100 mb-2",
                            size="sm"
                        ),
                        dbc.Button(
                            [
                                html.I(className="fas fa-users-cog me-2"),
                                "生徒管理"
                            ],
                            id="open-student-management-modal",
                            color="secondary",
                            className="w-100 mb-2",
                            size="sm"
                        ),
                        dbc.Button(
                            [
                                html.I(className="fas fa-edit me-2"),
                                "進捗更新"
                            ],
                            id="open-progress-modal",
                            color="primary",
                            className="w-100",
                            size="sm"
                        )
                    ], className="p-2")
                ], className="mb-3"),
                
                # 管理者メニュー
                dbc.Card([
                    dbc.CardHeader([
                        html.H6("🛠️ 管理者メニュー", className="mb-0")
                    ]),
                    dbc.CardBody([
                        dbc.Nav([
                            dbc.NavItem(
                                dbc.Button(
                                    [
                                        html.I(className="fas fa-plus me-2"),
                                        "データ入力"
                                    ],
                                    id="open-data-input-modal",
                                    color="success",
                                    className="w-100 mb-2",
                                    size="sm"
                                )
                            ),
                            dbc.NavItem(
                                dbc.Button(
                                    [
                                        html.I(className="fas fa-trash me-2"),
                                        "データ削除"
                                    ],
                                    id="open-data-delete-modal",
                                    color="danger",
                                    className="w-100 mb-2",
                                    size="sm"
                                )
                            ),
                            dbc.NavItem(
                                dbc.Button(
                                    [
                                        html.I(className="fas fa-check-double me-2"),
                                        "一括チェック設定"
                                    ],
                                    id="open-bulk-check-modal",
                                    color="warning",
                                    className="w-100 mb-2",
                                    size="sm"
                                )
                            )
                        ], vertical=True, pills=True)
                    ], className="p-2")
                ], className="sticky-menu fade-in")
            ], xs=12, md=2, className="mb-4"),
            
            # メインコンテンツエリア
            dbc.Col([
                dbc.Row([
                # 左列 - 全体進捗状況
                dbc.Col([
                    # 全体進捗グラフセクション
                    dbc.Card([
                        dbc.CardHeader([
                            html.H5("📈 全体進捗状況", className="mb-0")
                        ]),
                        dbc.CardBody([
                            dcc.Graph(
                                id="progress-bar-graph",
                                style={"height": "300px"}
                            )
                        ])
                    ], className="mb-3 fade-in"),
                
                # 進捗統計セクション
                dbc.Card([
                    dbc.CardHeader([
                        html.H6("📊 進捗統計", className="mb-0")
                    ]),
                    dbc.CardBody([
                        html.Div(id="progress-stats")
                    ])
                ], className="fade-in")
            ], xs=12, sm=12, md=8, lg=8, xl=8, className="pe-3"),
            
                # 右列 - 科目別進捗状況
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H5("🎯 科目別進捗状況", className="mb-0"),
                            html.Small("円グラフをクリックして詳細を表示", className="text-muted")
                        ]),
                        dbc.CardBody([
                            html.Div(id="subject-pie-graphs")
                        ])
                    ], className="fade-in")
                ], xs=12, sm=12, md=4, lg=4, xl=4, className="ps-3")
                ], className="g-4 mb-4")
            ], xs=12, md=10)
        ], className="g-4")
    ]),
    # 進捗更新用モーダル
    dbc.Modal(
        [
            dbc.ModalHeader([
                html.I(className="fas fa-graduation-cap me-2"),
                "📚 進捗更新 - 科目を選択してください"
            ], close_button=True),
            dbc.ModalBody([
                html.P("更新したい科目を選択してください:", className="text-muted mb-3"),
                dbc.Row([
                    dbc.Col([
                        dbc.Button(
                            [html.I(className="fas fa-graduation-cap me-2"), subject], 
                            id={'type': 'subject-btn', 'index': subject}, 
                            color="outline-primary", 
                            className="w-100 mb-3 subject-selection-btn",
                            size="lg"
                        )
                    ], width=4)
                    for subject in subjects
                ], className="g-3")
            ])
        ],
        id="progress-modal",
        is_open=False,
        size="xl",
        backdrop="static"
    ),
    # 予定入力用モーダル
    dbc.Modal([
        dbc.ModalHeader([
            html.I(className="fas fa-calendar-plus me-2"),
            html.Span(id="plan-modal-header")
        ], close_button=True),
        dbc.ModalBody([
            html.Div([
                html.H5("📋 予定を設定してください", className="text-primary mb-4"),
                html.P(id="plan-modal-description", className="text-muted mb-3"),
                
                # 次へボタンを上部に設置
                dbc.Row([
                    dbc.Col([
                        dbc.Button(
                            [html.I(className="fas fa-arrow-left me-2"), "戻る"],
                            id="plan-back-btn",
                            color="secondary",
                            outline=True,
                            className="me-2"
                        )
                    ], width="auto"),
                    dbc.Col([
                        dbc.Button(
                            [html.I(className="fas fa-arrow-right me-2"), "次へ：進捗入力"],
                            id="plan-next-btn",
                            color="primary",
                            className="float-end",
                            size="lg"
                        )
                    ])
                ], className="mb-4"),
                
                dbc.Row([
                    # 左列：一括チェック機能（既存の一括チェック設定ボタンを使用）
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader([
                                html.H6([
                                    html.I(className="fas fa-check-double me-2"),
                                    "一括選択"
                                ], className="mb-0 text-success fw-bold")
                            ]),
                            dbc.CardBody([
                                dbc.Button([
                                    html.I(className="fas fa-square me-2"),
                                    "全て解除"
                                ], id="plan-deselect-all-btn", color="outline-secondary", size="sm", className="w-100 mb-2"),
                                html.Hr(className="my-2"),
                                html.P("一括チェック設定:", className="small text-muted mb-1"),
                                html.Div(id="plan-bulk-buttons-container")
                            ])
                        ], className="mb-3 shadow-sm")
                    ], xs=12, md=4),
                    
                    # 右列：検索機能と参考書リスト
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader([
                                html.H6([
                                    html.I(className="fas fa-book me-2"),
                                    "参考書選択"
                                ], className="mb-0 text-primary fw-bold")
                            ]),
                            dbc.CardBody([
                                # 検索ボックス
                                dbc.InputGroup([
                                    dbc.Input(
                                        id="plan-search-input",
                                        placeholder="参考書名で検索...",
                                        type="text",
                                        size="sm"
                                    ),
                                    dbc.Button(
                                        [html.I(className="fas fa-search")],
                                        color="outline-secondary",
                                        size="sm",
                                        id="plan-search-btn"
                                    )
                                ], size="sm", className="mb-3"),
                                
                                # 参考書リスト
                                html.Div(id="plan-selection-content", style={"maxHeight": "400px", "overflowY": "auto"})
                            ])
                        ], className="shadow-sm")
                    ], xs=12, md=8)
                ], className="g-3")
            ])
        ])
    ], id="plan-modal", is_open=False, size="xl", backdrop="static"),
    # 進捗入力用モーダル
    dbc.Modal([
        dbc.ModalHeader([
            html.I(className="fas fa-chart-line me-2"),
            html.Span(id="progress-input-modal-header")
        ], close_button=True),
        dbc.ModalBody([
            html.Div([
                html.H5("📈 進捗を入力してください", className="text-success mb-4"),
                html.P(id="progress-input-modal-description", className="text-muted mb-3"),
                html.Div(id="progress-input-content"),
                html.Hr(),
                dbc.Row([
                    dbc.Col([
                        dbc.Button(
                            [html.I(className="fas fa-arrow-left me-2"), "戻る：予定設定"],
                            id="progress-back-btn",
                            color="secondary",
                            outline=True,
                            className="me-2"
                        )
                    ], width="auto"),
                    dbc.Col([
                        dbc.Button(
                            [html.I(className="fas fa-save me-2"), "保存して完了"],
                            id="progress-save-btn",
                            color="success",
                            className="float-end"
                        )
                    ])
                ])
            ])
        ])
    ], id="progress-input-modal", is_open=False, size="xl", backdrop="static"),
    # 科目ごとの参考書リスト用モーダル
    dbc.Modal(
        [
            dbc.ModalHeader([
                html.I(className="fas fa-list me-2"),
                html.Span(id="subject-modal-header")
            ], close_button=True),
            dbc.ModalBody([
                dbc.Row([
                    # 左列: 一括チェックとタブ選択
                    dbc.Col([
                        # 一括チェックセクション
                        dbc.Card([
                            dbc.CardHeader([
                                html.H6([
                                    html.I(className="fas fa-check-double me-2"),
                                    "一括チェック"
                                ], className="mb-0 text-success fw-bold")
                            ]),
                            dbc.CardBody([
                                dbc.Button([
                                    html.I(className="fas fa-cog me-2"),
                                    "設定"
                                ], id="open-bulk-manage-btn", color="warning", size="sm", className="w-100 mb-3"),
                                html.Div(id="bulk-check-buttons-container")
                            ])
                        ], className="mb-3 shadow-sm"),
                        
                        # ルートレベルタブセクション
                        dbc.Card([
                            dbc.CardHeader([
                                html.H6([
                                    html.I(className="fas fa-road me-2"),
                                    "ルートレベル選択"
                                ], className="mb-0 text-primary fw-bold")
                            ]),
                            dbc.CardBody([
                                html.Div(id="subject-modal-tabs")
                            ])
                        ], className="shadow-sm")
                    ], xs=12, md=4, className="mb-3"),
                    
                    # 右列: 参考書リスト
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader([
                                html.H6([
                                    html.I(className="fas fa-book me-2"),
                                    "参考書リスト"
                                ], className="mb-0 text-info fw-bold")
                            ]),
                            dbc.CardBody([
                                html.Div(id="subject-modal-content")
                            ], style={"maxHeight": "600px", "overflowY": "auto"})
                        ], className="shadow-sm")
                    ], xs=12, md=8)
                ], className="g-3")
            ])
        ],
        id="subject-modal",
        is_open=False,
        size="xl",
        backdrop="static"
    ),
    # データ入力用モーダル
    dbc.Modal(
        [
            dbc.ModalHeader([
                html.I(className="fas fa-plus-circle me-2"),
                "📝 新しい参考書データを追加"
            ], close_button=True),
            dbc.ModalBody([
                dbc.Alert([
                    html.I(className="fas fa-info-circle me-2"),
                    "新しい参考書情報を入力してください。すべての項目が必須です。"
                ], color="info", className="mb-4"),
                dbc.Row([
                    dbc.Col([
                        dbc.Label([
                            html.I(className="fas fa-layer-group me-1"),
                            "ルートレベル"
                        ], className="fw-bold"),
                        dbc.Input(
                            id="input-route-level", 
                            type="text", 
                            placeholder="例: 日大、MARCH、早慶",
                            className="mb-2"
                        )
                    ], width=6),
                    dbc.Col([
                        dbc.Label([
                            html.I(className="fas fa-graduation-cap me-1"),
                            "科目"
                        ], className="fw-bold"),
                        dbc.Input(
                            id="input-subject", 
                            type="text", 
                            placeholder="例: 英語、数学、現代文",
                            className="mb-2"
                        )
                    ], width=6)
                ], className="mb-3"),
                dbc.Row([
                    dbc.Col([
                        dbc.Label([
                            html.I(className="fas fa-book me-1"),
                            "参考書名"
                        ], className="fw-bold"),
                        dbc.Input(
                            id="input-book-name", 
                            type="text", 
                            placeholder="例: システム英単語、青チャート",
                            className="mb-2"
                        )
                    ], width=8),
                    dbc.Col([
                        dbc.Label([
                            html.I(className="fas fa-clock me-1"),
                            "所要時間（時間）"
                        ], className="fw-bold"),
                        dbc.Input(
                            id="input-time", 
                            type="number", 
                            placeholder="210",
                            min=1,
                            className="mb-2"
                        )
                    ], width=6)
                ], className="mb-3"),
                html.Div(id="input-status-message", className="mt-3")
            ]),
            dbc.ModalFooter([
                dbc.Button([
                    html.I(className="fas fa-check me-2"),
                    "追加"
                ], id="add-data-btn", color="success", size="lg", className="me-2"),
                dbc.Button([
                    html.I(className="fas fa-times me-2"),
                    "キャンセル"
                ], id="cancel-data-btn", color="secondary", size="lg")
            ])
        ],
        id="data-input-modal",
        is_open=False,
        size="lg",
        backdrop="static"
    ),
    # データ削除用モーダル
    dbc.Modal(
        [
            dbc.ModalHeader([
                html.I(className="fas fa-trash-alt me-2"),
                "🗑️ 参考書データを削除"
            ], close_button=True),
            dbc.ModalBody([
                dbc.Alert([
                    html.I(className="fas fa-exclamation-triangle me-2"),
                    "⚠️ 注意: 削除したデータは復元できません。慎重に選択してください。"
                ], color="warning", className="mb-4"),
                dbc.Row([
                    dbc.Col([
                        dbc.Label([
                            html.I(className="fas fa-road me-1"),
                            "ルートで絞り込み"
                        ], className="fw-bold"),
                        dbc.Select(
                            id="delete-route-filter",
                            options=[
                                {"label": "📚 すべてのルート", "value": "all"}
                            ] + [
                                {"label": f"🛤️ {route}", "value": route} for route in sorted(df['ルートレベル'].unique())
                            ],
                            value="all",
                            className="mb-2"
                        )
                    ], width=6),
                    dbc.Col([
                        dbc.Label([
                            html.I(className="fas fa-filter me-1"),
                            "科目で絞り込み"
                        ], className="fw-bold"),
                        dbc.Select(
                            id="delete-subject-filter",
                            options=[
                                {"label": "📚 すべての科目", "value": "all"}
                            ] + [
                                {"label": f"📖 {subj}", "value": subj} for subj in subjects
                            ],
                            value="all",
                            className="mb-2"
                        )
                    ], width=6)
                ], className="mb-3"),
                html.Div([
                    html.H6("削除対象を選択:", className="fw-bold mb-2"),
                    # 検索ボックス
                    dbc.InputGroup([
                        dbc.Input(
                            id="delete-search-input",
                            placeholder="参考書名で検索...",
                            type="text",
                            size="sm"
                        ),
                        dbc.Button(
                            [html.I(className="fas fa-search")],
                            color="outline-secondary",
                            size="sm"
                        )
                    ], size="sm", className="mb-3"),
                    html.Div(id="delete-books-list")
                ]),
                html.Div(id="delete-status-message", className="mt-3")
            ]),
            dbc.ModalFooter([
                dbc.Button([
                    html.I(className="fas fa-trash me-2"),
                    "選択したアイテムを削除"
                ], id="confirm-delete-btn", color="danger", size="lg", className="me-2"),
                dbc.Button([
                    html.I(className="fas fa-times me-2"),
                    "キャンセル"
                ], id="cancel-delete-btn", color="secondary", size="lg")
            ])
        ],
        id="data-delete-modal",
        is_open=False,
        size="lg",
        backdrop="static"
    ),

    # 一括チェック管理モーダル（科目選択）
    dbc.Modal(
        [
            dbc.ModalHeader([
                html.I(className="fas fa-check-double me-2"),
                "📋 一括チェック管理"
            ], close_button=True),
            dbc.ModalBody([
                dbc.Alert([
                    html.I(className="fas fa-info-circle me-2"),
                    "管理したい科目を選択してください。"
                ], color="info", className="mb-4"),
                html.Div(id="bulk-check-subject-selection")
            ])
        ],
        id="bulk-check-modal",
        is_open=False,
        size="lg",
        backdrop="static"
    ),

    # 一括チェックボタン管理モーダル
    dbc.Modal(
        [
            dbc.ModalHeader([
                html.I(className="fas fa-cogs me-2"),
                html.Span(id="bulk-manage-header")
            ], close_button=True),
            dbc.ModalBody([
                dbc.Row([
                    dbc.Col([
                        dbc.Button([
                            html.I(className="fas fa-plus me-2"),
                            "新しいボタンを追加"
                        ], id="add-bulk-button", color="primary", className="w-100 mb-3")
                    ])
                ]),
                html.Div(id="bulk-button-list")
            ])
        ],
        id="bulk-manage-modal",
        is_open=False,
        size="xl",
        backdrop="static"
    ),

    # 一括チェックボタン編集モーダル
    dbc.Modal(
        [
            dbc.ModalHeader([
                dbc.Row([
                    dbc.Col([
                        html.I(className="fas fa-edit me-2"),
                        "✏️ ボタン編集"
                    ], width="auto"),
                    dbc.Col([
                        dbc.Button([
                            html.I(className="fas fa-save me-2"),
                            "保存"
                        ], id="save-button-edit", color="success", size="lg", className="me-2 px-4 py-2", 
                        style={"fontSize": "1.1rem", "fontWeight": "600", "borderRadius": "8px"})
                    ], width="auto", className="ms-auto")
                ], className="w-100 align-items-center")
            ], close_button=True),
            dbc.ModalBody([
                dbc.Row([
                    dbc.Col([
                        dbc.Label("ボタン名", className="fw-bold"),
                        dbc.Input(id="edit-button-name", placeholder="例：基礎固め、応用対策など")
                    ], width=12)
                ], className="mb-3"),
                dbc.Row([
                    dbc.Col([
                        dbc.Label("対象参考書", className="fw-bold"),
                        html.Div(id="edit-button-books")
                    ], width=12)
                ])
            ]),
            dbc.ModalFooter([
                dbc.Button([
                    html.I(className="fas fa-times me-2"),
                    "キャンセル"
                ], id="cancel-button-edit", color="secondary", size="lg", className="w-100")
            ])
        ],
        id="bulk-edit-modal",
        is_open=False,
        size="xl",
        backdrop="static"
    ),
    
    # 生徒選択モーダル
    dbc.Modal(
        [
            dbc.ModalHeader([
                html.I(className="fas fa-user-graduate me-2"),
                "�‍🎓 生徒選択"
            ], close_button=True),
            dbc.ModalBody([
                html.Div([
                    html.H5("現在の生徒", className="text-primary mb-3"),
                    html.Div(id="current-student-display", className="mb-4"),
                    
                    html.H5("生徒一覧", className="text-info mb-3"),
                    html.P("ダッシュボードを表示したい生徒を選択してください:", className="text-muted mb-3"),
                    
                    html.Div(id="student-selection-buttons"),
                    
                    html.Div(id="student-selection-message", className="mt-3")
                ])
            ])
        ],
        id="student-selection-modal",
        is_open=False,
        size="lg",
        backdrop="static"
    ),
    
    # 生徒管理モーダル
    dbc.Modal(
        [
            dbc.ModalHeader([
                html.I(className="fas fa-users-cog me-2"),
                "👥 生徒管理"
            ], close_button=True),
            dbc.ModalBody([
                dbc.Row([
                    # 左列：生徒追加
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader([
                                html.H6([
                                    html.I(className="fas fa-user-plus me-2"),
                                    "生徒追加"
                                ], className="mb-0 text-success")
                            ]),
                            dbc.CardBody([
                                dbc.Input(
                                    id="new-student-name-input",
                                    placeholder="新しい生徒名を入力...",
                                    type="text",
                                    className="mb-3"
                                ),
                                dbc.Button(
                                    [html.I(className="fas fa-plus me-2"), "追加"],
                                    id="add-new-student-btn",
                                    color="success",
                                    className="w-100"
                                )
                            ])
                        ], className="mb-3")
                    ], width=6),
                    
                    # 右列：生徒削除・編集
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader([
                                html.H6([
                                    html.I(className="fas fa-user-edit me-2"),
                                    "生徒削除・編集"
                                ], className="mb-0 text-warning")
                            ]),
                            dbc.CardBody([
                                html.Div(id="student-management-list"),
                                html.Div(id="student-edit-controls", style={"display": "none"}, children=[
                                    dcc.Store(id="editing-student-original-name"),
                                    dbc.Input(
                                        id="edit-student-name-input",
                                        type="text",
                                        placeholder="生徒名を入力...",
                                        className="mb-2"
                                    ),
                                    dbc.ButtonGroup([
                                        dbc.Button("保存", id="save-student-edit-btn", color="success", size="sm"),
                                        dbc.Button("キャンセル", id="cancel-student-edit-btn", color="secondary", size="sm")
                                    ])
                                ])
                            ])
                        ])
                    ], width=6)
                ]),
                
                html.Hr(),
                html.Div(id="student-management-message", className="mt-3")
            ])
        ],
        id="student-management-modal",
        is_open=False,
        size="xl",
        backdrop="static"
    ),
    
    # 科目別詳細情報モーダル
    dbc.Modal(
        [
            dbc.ModalHeader([
                html.I(className="fas fa-chart-bar me-2"),
                html.Span(id="subject-detail-header")
            ], close_button=True),
            dbc.ModalBody([
                # 科目別横棒グラフ
                dbc.Card([
                    dbc.CardHeader([
                        html.H6("📈 科目別進捗グラフ", className="mb-0")
                    ]),
                    dbc.CardBody([
                        dcc.Graph(id="subject-detail-graph", style={"height": "300px"})
                    ])
                ], className="mb-3"),
                
                # 科目別統計
                dbc.Card([
                    dbc.CardHeader([
                        html.H6("📊 科目別統計", className="mb-0")
                    ]),
                    dbc.CardBody([
                        html.Div(id="subject-detail-stats")
                    ])
                ])
            ])
        ],
        id="subject-detail-modal",
        is_open=False,
        size="xl",
        backdrop="static"
    ),
    
    dcc.Store(id="progress-data", data=df.to_dict("records")),
    dcc.Store(id="selected-subject-store", data=""),  # 選択された科目を保存
    dcc.Store(id="current-student-store", data=current_user),  # 現在選択中の生徒を保存
    dcc.Store(id="graph-update-trigger", data=0),  # グラフ更新専用トリガー
])

# 検索機能コールバック（進捗更新モーダル用）
@app.callback(
    Output({'type': 'books-list', 'index': dash.MATCH}, 'children'),
    [Input({'type': 'search-input', 'index': dash.MATCH}, 'value')],
    [State("subject-modal-header", "children"),
     State("subject-tabs", "value"),
     State("progress-data", "data"),
     State("current-student-store", "data")],
    prevent_initial_call=True
)
def search_books(search_value, header, tab_value, data, current_user):
    subject = header.replace("の参考書リスト", "")
    df = pd.DataFrame(data)
    # 現在の生徒のデータのみにフィルタリング
    df = df[df['生徒'] == current_user]
    
    if tab_value == "全て":
        filtered = df[df['科目'] == subject]
    else:
        filtered = df[(df['科目'] == subject) & (df['ルートレベル'] == tab_value)]
    
    # 検索フィルタリング
    if search_value:
        filtered = filtered[filtered['参考書名'].str.contains(search_value, case=False, na=False)]
    
    if filtered.empty:
        return [html.P("該当する参考書が見つかりません。", className="text-muted")]
    
    return [
        html.Div([
            html.Div([
                html.Div([
                    dbc.Badge(row['ルートレベル'], color="secondary", className="me-2", style={"fontSize": "10px"}),
                    html.Span(row['参考書名'], style={"fontSize": "14px", "fontWeight": "bold", "color": "#2c3e50"})
                ])
            ], style={"width": "280px", "display": "inline-block"}),
            
            html.Div([
                html.Div([
                    html.Span("予定", className="checkbox-label"),
                    dbc.Checkbox(
                        id={'type': 'plan-check', 'index': f"{row['科目']}|{row['参考書名']}"},
                        value=row['予定'],
                        className="custom-checkbox"
                    )
                ], className="checkbox-container")
            ], style={"width": "80px", "display": "inline-block", "textAlign": "center"}),
            
            html.Div([
                html.Div([
                    html.Span("達成", className="checkbox-label"),
                    dbc.Checkbox(
                        id={'type': 'done-check', 'index': f"{row['科目']}|{row['参考書名']}"},
                        value=row['達成済'],
                        className="custom-checkbox done-checkbox"
                    )
                ], className="checkbox-container")
            ], style={"width": "80px", "display": "inline-block", "textAlign": "center"}),
            
            html.Div([
                html.Span("達成割合", style={"fontSize": "12px", "marginRight": "4px"}),
                dbc.Input(
                    id={'type': 'progress-ratio', 'index': f"{row['科目']}|{row['参考書名']}"},
                    type="text",
                    placeholder="例: 3/5 または 0.6",
                    value=row.get('達成割合', ''),
                    size="sm",
                    style={"width": "100px", "fontSize": "12px"}
                ),
                html.Small("分数または小数", className="text-muted ms-1", style={"fontSize": "9px"})
            ], style={"width": "160px", "display": "inline-block"})
        ], style={
            "marginBottom": "4px", 
            "display": "flex", 
            "alignItems": "center", 
            "padding": "4px 8px", 
            "border": "1px solid #e9ecef", 
            "borderRadius": "6px", 
            "backgroundColor": "#f8f9fa",
            "minHeight": "auto"
        })
        for _, row in filtered.iterrows()
    ]

# 科目ごとの達成状況円グラフ
@app.callback(
    Output("subject-pie-graphs", "children"),
    [Input("progress-data", "data"), Input("current-student-store", "data"), Input("graph-update-trigger", "data")]
)
def update_subject_pie_graphs(data, current_user, _trigger):
    try:
        # 達成率に応じた色を計算する関数（内部関数として定義）
        def get_liquid_color(rate):
            """達成率(0-100)に応じて赤から緑へのグラデーション色を返す"""
            if rate <= 0:
                return "rgb(220, 53, 69)"  # 赤
            elif rate >= 100:
                return "rgb(40, 167, 69)"  # 緑
            else:
                # 赤(220,53,69)から緑(40,167,69)へのグラデーション
                red_start, red_end = 220, 40
                green_start, green_end = 53, 167
                blue_start, blue_end = 69, 69
                
                ratio = rate / 100
                red = int(red_start + (red_end - red_start) * ratio)
                green = int(green_start + (green_end - green_start) * ratio)
                blue = int(blue_start + (blue_end - blue_start) * ratio)
                
                return f"rgb({red}, {green}, {blue})"
        # グラフ更新コールバック
        if not data:
            return []
            
        df = pd.DataFrame(data)
        # タイムスタンプ列がある場合は削除
        if '_update_timestamp' in df.columns:
            # タイムスタンプカラム削除
            df = df.drop('_update_timestamp', axis=1)
        
        # 現在の生徒のデータのみにフィルタリング
        df_filtered = df[df['生徒'] == current_user]
        
        if df_filtered.empty:
            return []
        
        # 予定が設定された科目のみを処理
        df_planned = df_filtered[df_filtered['予定'] == True]
        
        if df_planned.empty:
            return [dbc.Row([
                dbc.Col([
                    create_new_user_help()
                ], xs=12, md=8, className="mx-auto")
            ], justify="center")]
            
        subjects = df_planned['科目'].unique()
        containers = []
        
        for subj in subjects:
            df_sub = df_filtered[df_filtered['科目'] == subj]
            df_sub_planned = df_sub[df_sub['予定'] == True]
            
            if df_sub_planned.empty:
                continue
            
            # 達成率計算
            achievement_rate = calculate_achievement_rate(df_sub_planned)
            
            # 時間計算
            try:
                planned_time = pd.to_numeric(df_sub_planned['所要時間'], errors='coerce').fillna(0).sum()
                done_time = (achievement_rate / 100) * planned_time if planned_time > 0 else 0
            except Exception as e:
                print(f"Error calculating times for {subj}: {e}")
                planned_time = 0
                done_time = 0
                
            # 達成率に応じた色を取得
            fill_color = get_liquid_color(achievement_rate)
            
            # 液体タンクデザインのコンテナを作成
            containers.append(
                dbc.Col([
                    html.Div([
                        dbc.Card([
                            dbc.CardBody([
                                # タイトル
                                html.H5(subj, className="text-center mb-3", 
                                       style={"fontWeight": "bold", "color": "#2c3e50"}),
                                
                                # 液体タンクコンテナ
                                html.Div([
                                    # 背景（空の部分）
                                    html.Div([
                                        # 液体部分（下から染まる）
                                        html.Div([
                                            # 液体の波紋効果
                                            html.Div(className="liquid-wave", style={
                                                "position": "absolute",
                                                "top": "0",
                                                "left": "0",
                                                "width": "100%",
                                                "height": "100%",
                                                "background": f"linear-gradient(45deg, {fill_color}, rgba(255,255,255,0.1))",
                                                "borderRadius": "8px",
                                                "opacity": "0.9"
                                            })
                                        ], style={
                                            "position": "absolute",
                                            "bottom": "0",
                                            "left": "0",
                                            "width": "100%",
                                            "height": f"{achievement_rate}%",
                                            "backgroundColor": fill_color,
                                            "transition": "height 1s ease-in-out, background-color 0.5s ease",
                                            "borderRadius": "0 0 8px 8px" if achievement_rate < 100 else "8px"
                                        }),
                                        
                                        # 達成率テキスト（中央）
                                        html.Div([
                                            html.H3(f"{achievement_rate:.1f}%", 
                                                   style={"fontWeight": "bold", "margin": "0", "color": "white" if achievement_rate > 50 else "#2c3e50",
                                                         "textShadow": "1px 1px 2px rgba(0,0,0,0.3)" if achievement_rate > 50 else "none"}),
                                            html.Small(f"{done_time:.0f}/{planned_time:.0f}分", 
                                                     style={"color": "white" if achievement_rate > 50 else "#6c757d",
                                                           "textShadow": "1px 1px 2px rgba(0,0,0,0.3)" if achievement_rate > 50 else "none"})
                                        ], style={
                                            "position": "absolute",
                                            "top": "50%",
                                            "left": "50%",
                                            "transform": "translate(-50%, -50%)",
                                            "textAlign": "center",
                                            "zIndex": "10"
                                        })
                                    ], style={
                                        "position": "relative",
                                        "width": "100%",
                                        "height": "120px",
                                        "backgroundColor": "#f8f9fa",
                                        "border": "2px solid #dee2e6",
                                        "borderRadius": "8px",
                                        "overflow": "hidden"
                                    })
                                ], className="mb-2"),
                                
                                # 進捗バー（補足）
                                dbc.Progress(
                                    value=achievement_rate,
                                    style={"height": "8px"},
                                    color="success" if achievement_rate >= 80 else "warning" if achievement_rate >= 50 else "danger",
                                    className="mb-2"
                                )
                            ], className="p-3")
                        ], className="shadow-sm border-0 h-100 subject-card-hover", 
                           style={
                               "cursor": "pointer", 
                               "transition": "all 0.3s ease",
                               "borderRadius": "12px"
                           },
                           id={'type': 'subject-card', 'index': subj}),
                        
                        # クリック可能なオーバーレイ
                        html.Button(
                            "",
                            style={
                                "position": "absolute",
                                "top": "0",
                                "left": "0", 
                                "width": "100%",
                                "height": "100%",
                                "zIndex": "5",
                                "cursor": "pointer",
                                "background": "transparent",
                                "border": "none",
                                "outline": "none"
                            },
                            n_clicks=0,
                            id={'type': 'subject-overlay', 'index': subj}
                        )
                    ], style={"position": "relative", "height": "100%"})
                ], 
                   xs=12, sm=12, md=6, lg=4, xl=4,  # レスポンシブ列幅
                   className="mb-4 px-2")
            )
    
        # グリッドレイアウトで返す（3列）
        rows = []
        for i in range(0, len(containers), 3):
            row_containers = containers[i:i+3]
            rows.append(dbc.Row(row_containers, className="g-3 mb-3"))
        
        return rows
        
    except Exception as e:
        print(f"Fatal error in update_subject_pie_graphs: {e}")
        import traceback
        traceback.print_exc()
        return [html.Div([
            html.H5("コンテナ作成エラー", className="text-center text-danger"),
            html.P(f"エラー: {str(e)}", className="text-center text-muted")
        ])]

# 新しい生徒向けヘルプメッセージコンポーネント
def create_new_user_help():
    return dbc.Card([
        dbc.CardHeader([
            html.H5([
                html.I(className="fas fa-info-circle me-2 text-primary"),
                "🚀 はじめての方へ"
            ], className="mb-0 text-primary")
        ]),
        dbc.CardBody([
            html.P("進捗データを表示するには、まず学習予定を設定する必要があります：", className="mb-3"),
            html.Ol([
                html.Li("左メニューの「進捗更新」ボタンをクリック"),
                html.Li("勉強したい科目を選択"),
                html.Li("参考書の「予定」にチェックを入れる"),
                html.Li("進捗や達成状況を入力")
            ], className="mb-3"),
            dbc.Alert([
                html.I(className="fas fa-lightbulb me-2"),
                "まずは1つの科目から始めてみましょう！"
            ], color="info", className="mb-0")
        ])
    ], className="shadow-sm")


# 進捗更新ボタンや×ボタンでモーダル表示/非表示
@app.callback(
    Output("progress-modal", "is_open"),
    [Input("open-progress-modal", "n_clicks")],
    [State("progress-modal", "is_open")],
    prevent_initial_call=True
)
def toggle_progress_modal(n, is_open):
    if n:
        return not is_open
    return is_open

# 科目ボタン押下で参考書リストモーダル表示/非表示（段階的フローでは使用しない）
@app.callback(
    [Output("subject-modal", "is_open"),
     Output("subject-modal-header", "children"),
     Output("subject-modal-tabs", "children")],
    [Input({'type': 'subject-btn-old', 'index': dash.ALL}, 'n_clicks')],  # 旧タイプのボタンのみ反応
    [State("progress-data", "data"), State("subject-modal", "is_open"), State("subject-modal-header", "children")],
    prevent_initial_call=True
)
def open_subject_modal(n_clicks_list, data, is_open, header):
    ctx = dash.callback_context
    if not ctx.triggered:
        return is_open, header, dash.no_update
    trigger = ctx.triggered[0]["prop_id"].split(".")[0]
    # 科目ボタン
    btn_id = trigger
    if not btn_id:
        return is_open, header, dash.no_update
    subject = eval(btn_id)['index']
    df = pd.DataFrame(data)
    # ルートレベルごと＋全てのタブ
    route_levels = df[df['科目'] == subject]['ルートレベル'].unique()

    
    tabs = dbc.Tabs([
        dbc.Tab(label="📚 全て", tab_id="全て", active_tab_style={"backgroundColor": "#007bff", "color": "white"}),
    ] + [
        dbc.Tab(label=f"🛤️ {rl}", tab_id=rl, active_tab_style={"backgroundColor": "#007bff", "color": "white"})
        for rl in sorted(route_levels)
    ], id="subject-tabs", active_tab="全て", className="mb-3")
    
    return (
        not is_open,
        f"{subject}の参考書リスト",
        tabs
    )

# タブ切り替えで参考書リスト表示（チェックボックスは参考書名の横）
@app.callback(
    Output("subject-modal-content", "children"),
    [Input("subject-tabs", "active_tab"),
     State("subject-modal-header", "children"),
     State("progress-data", "data"),
     State("current-student-store", "data")],
    prevent_initial_call=True
)
def update_subject_tab(tab_value, header, data, current_user):
    subject = header.replace("の参考書リスト", "")
    df = pd.DataFrame(data)
    # 現在の生徒のデータのみにフィルタリング
    df = df[df['生徒'] == current_user]
    
    if tab_value == "全て":
        filtered = df[df['科目'] == subject]
    else:
        filtered = df[(df['科目'] == subject) & (df['ルートレベル'] == tab_value)]
    
    if filtered.empty:
        return html.Div([html.P(f"該当する参考書が見つかりません。科目: {subject}, タブ: {tab_value}")])
    
    # 検索機能付き参考書リスト
    return html.Div([
        # 検索ボックス
        html.Div([
            dbc.InputGroup([
                dbc.Input(
                    id={'type': 'search-input', 'index': subject},
                    placeholder="参考書名で検索...",
                    type="text",
                    size="sm"
                ),
                dbc.Button(
                    [html.I(className="fas fa-search")],
                    color="outline-secondary",
                    size="sm"
                )
            ], size="sm")
        ], className="mb-3"),
        
        # 参考書リスト（ルートレベル付き）
        html.Div([
            html.Div([
                html.Div([
                    html.Div([
                        dbc.Badge(row['ルートレベル'], color="secondary", className="me-2", style={"fontSize": "10px"}),
                        html.Span(row['参考書名'], style={"fontSize": "14px", "fontWeight": "bold", "color": "#2c3e50"})
                    ])
                ], style={"width": "280px", "display": "inline-block", "lineHeight": "1.2"}),
            
            html.Div([
                html.Div([
                    html.Span("予定", className="checkbox-label"),
                    dbc.Checkbox(
                        id={'type': 'plan-check', 'index': f"{row['科目']}|{row['参考書名']}"},
                        value=row['予定'],
                        className="custom-checkbox"
                    )
                ], className="checkbox-container")
            ], style={"width": "80px", "display": "inline-block", "textAlign": "center"}),
            
            html.Div([
                html.Div([
                    html.Span("達成", className="checkbox-label"),
                    dbc.Checkbox(
                        id={'type': 'done-check', 'index': f"{row['科目']}|{row['参考書名']}"},
                        value=row['達成済'],
                        className="custom-checkbox done-checkbox"
                    )
                ], className="checkbox-container")
            ], style={"width": "80px", "display": "inline-block", "textAlign": "center"}),
            
            html.Div([
                html.Span("達成割合", style={"fontSize": "12px", "marginRight": "4px"}),
                dbc.Input(
                    id={'type': 'progress-ratio', 'index': f"{row['科目']}|{row['参考書名']}"},
                    type="text",
                    placeholder="例: 3/5 または 0.6",
                    value=row.get('達成割合', ''),
                    size="sm",
                    style={"width": "100px", "fontSize": "12px"}
                ),
                html.Small("分数または小数", className="text-muted ms-1", style={"fontSize": "9px"})
            ], style={"width": "160px", "display": "inline-block"})
        ], style={
            "marginBottom": "4px", 
            "display": "flex", 
            "alignItems": "center", 
            "padding": "4px 8px", 
            "border": "1px solid #e9ecef", 
            "borderRadius": "6px", 
            "backgroundColor": "#f8f9fa",
            "minHeight": "auto"
        })
        for _, row in filtered.iterrows()
        ], id={'type': 'books-list', 'index': subject})
    ])

# チェックボックス＋達成割合更新でデータ保存
@app.callback(
    Output("progress-data", "data"),
    [Input({'type': 'plan-check', 'index': dash.ALL}, 'value'),
     Input({'type': 'done-check', 'index': dash.ALL}, 'value'),
     Input({'type': 'progress-ratio', 'index': dash.ALL}, 'value')],
    [State("progress-data", "data"), State("current-student-store", "data")],
    prevent_initial_call=True
)
def update_progress(plan_values, done_values, ratio_values, data, current_user):
    df = pd.DataFrame(data)
    ctx = dash.callback_context
    # ctx.inputsは{<component_id>.value: value, ...}のdict
    for k, v in ctx.inputs.items():
        # k例: {"type":"plan-check","index":"数学|青チャート"}.value
        if not k.endswith('.value'):
            continue
        id_part = k[:-6]  # .valueを除去
        try:
            id_dict = json.loads(id_part.replace("'", '"'))
        except json.JSONDecodeError:
            continue
        if id_dict['type'] == 'plan-check':
            subj, book = id_dict['index'].split('|', 1)
            df.loc[(df['科目'] == subj) & (df['参考書名'] == book) & (df['生徒'] == current_user), '予定'] = v
        elif id_dict['type'] == 'done-check':
            subj, book = id_dict['index'].split('|', 1)
            df.loc[(df['科目'] == subj) & (df['参考書名'] == book) & (df['生徒'] == current_user), '達成済'] = v
        elif id_dict['type'] == 'progress-ratio':
            subj, book = id_dict['index'].split('|', 1)
            # 空文字列または0の場合は空文字列として保存
            value = v if v else ''
            if str(value).strip() in ['0', '0.0']:
                value = ''
            df.loc[(df['科目'] == subj) & (df['参考書名'] == book) & (df['生徒'] == current_user), '達成割合'] = value
    
    # 進捗変更をCSVファイルにも保存
    try:
        csv_path = os.path.join(os.path.dirname(__file__), 'route-subject-text-time.csv')
        column_order = ["ルートレベル", "科目", "参考書名", "所要時間", "予定", "達成済", "達成割合", "生徒"]
        df_save = df[column_order].copy()
        # 達成割合のデータ型を文字列に統一（NaN値を空文字列に変換）
        df_save['達成割合'] = df_save['達成割合'].fillna('').astype(str)
        # '0.0'を空文字列に変換
        df_save.loc[df_save['達成割合'] == '0.0', '達成割合'] = ''
        df_save.to_csv(csv_path, index=False, encoding='utf-8-sig')
    except Exception as e:
        print(f"進捗データのCSV保存に失敗: {e}")
    
    return df.to_dict("records")

# 積み上げ横棒グラフ（y軸：予定・達成済の2項目、x軸：合計所要時間）
@app.callback(
    Output("progress-bar-graph", "figure"),
    [Input("progress-data", "data"), Input("current-student-store", "data"), Input("graph-update-trigger", "data")]
)
def update_bar_graph(data, current_user, trigger):
    # バーグラフ更新コールバック
    df = pd.DataFrame(data)
    # タイムスタンプ列がある場合は削除
    if '_update_timestamp' in df.columns:
        df = df.drop('_update_timestamp', axis=1)
    # 現在の生徒のデータのみにフィルタリング
    df_filtered = df[df['生徒'] == current_user]
    # 予定データのみを処理
    df = df_filtered[df_filtered['予定'] == True]
    
    # 予定データがない場合は空のグラフを返す
    if df.empty:
        fig = go.Figure()
        fig.update_layout(
            title=dict(
                text="📊 学習予定を設定してください",
                x=0.5,
                font=dict(size=16, color='#6c757d')
            ),
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            height=280,
            margin=dict(l=60, r=40, t=50, b=60),
            plot_bgcolor='rgba(248,249,250,0.3)',
            paper_bgcolor='white',
            showlegend=False,
            annotations=[
                dict(
                    text="左メニューの「進捗更新」から<br>学習予定を設定してください",
                    x=0.5,
                    y=0.5,
                    xref="paper",
                    yref="paper",
                    showarrow=False,
                    font=dict(size=14, color='#6c757d'),
                    align="center"
                )
            ]
        )
        return fig
    
    # 達成割合を考慮した進捗表示
    planned_books = df[df['予定'] == True][['参考書名', '所要時間']].copy()
    
    # グラフ用のデータを準備
    achieved_data = []
    remaining_data = []
    
    # 各予定参考書について達成時間と残り時間を計算
    for _, row in planned_books.iterrows():
        book_name = row['参考書名']
        total_time = row['所要時間']
        
        # 該当する行を取得して達成時間を計算
        book_row = df[(df['参考書名'] == book_name) & (df['予定'] == True)].iloc[0]
        achieved_time = calculate_progress_time(book_row)
        remaining_time = total_time - achieved_time
        
        # 達成時間がある場合は達成データに追加
        if achieved_time > 0:
            achieved_data.append({'参考書名': book_name, '所要時間': achieved_time})
        
        # 残り時間がある場合は残りデータに追加
        if remaining_time > 0:
            remaining_data.append({'参考書名': book_name, '所要時間': remaining_time})
    
    # DataFrameに変換
    achieved_df = pd.DataFrame(achieved_data) if achieved_data else pd.DataFrame(columns=['参考書名', '所要時間'])
    remaining_df = pd.DataFrame(remaining_data) if remaining_data else pd.DataFrame(columns=['参考書名', '所要時間'])
    
    # 全参考書のユニークなリストを作成
    all_books = list(df['参考書名'].unique())
    
    # カラーパレット
    color_palette = [
        'rgba(52, 144, 220, 0.8)',   # 青
        'rgba(40, 167, 69, 0.8)',    # 緑  
        'rgba(255, 193, 7, 0.8)',    # 黄色
        'rgba(220, 53, 69, 0.8)',    # 赤
        'rgba(111, 66, 193, 0.8)',   # 紫
        'rgba(32, 201, 151, 0.8)',   # ターコイズ
        'rgba(253, 126, 20, 0.8)',   # オレンジ
        'rgba(232, 62, 140, 0.8)',   # ピンク
        'rgba(108, 117, 125, 0.8)',  # グレー
        'rgba(155, 89, 182, 0.8)'    # ライトパープル
    ]
    
    # 参考書名をインデックスとして同じ色を割り当て
    def get_book_color(book_name):
        try:
            index = all_books.index(book_name)
            return color_palette[index % len(color_palette)]
        except ValueError:
            return color_palette[0]
    
    # 各参考書に同じ色を割り当て
    achieved_colors = [get_book_color(book) for book in achieved_df['参考書名']] if not achieved_df.empty else []
    _remaining_colors = [get_book_color(book) for book in remaining_df['参考書名']] if not remaining_df.empty else []
    
    bars = []
    
    # 予定
    bar_planned = go.Bar(
        y=["予定"]*len(planned_books),
        x=planned_books['所要時間'],
        name="📅 予定中",
        orientation='h',
        marker=dict(
            color=[get_book_color(book) for book in planned_books['参考書名']],
            opacity=0.7  # パターンを削除してシンプルに
        ),
        customdata=planned_books['参考書名'],
        hovertemplate='<b>📚 %{customdata}</b><br>' +
                     '⏰ 所要時間: %{x}h<br>' +
                     '<i>予定中</i><extra></extra>'
    )
    
    # 達成済み
    bars = [bar_planned]
    if not achieved_df.empty:
        achieved_colors = [get_book_color(book) for book in achieved_df['参考書名']]
        bar_achieved = go.Bar(
            y=["達成済"]*len(achieved_df),
            x=achieved_df['所要時間'],
            name="✅ 達成済み",
            orientation='h',
            marker=dict(
                color=achieved_colors,
                line=dict(color='rgba(255, 255, 255, 0.8)', width=1),
                # アニメーションエフェクト
                opacity=0.95
            ),
            customdata=achieved_df['参考書名'],
            hovertemplate='<b>📚 %{customdata}</b><br>' +
                         '⏰ 達成時間: %{x}h<br>' +
                         '<i>達成済み</i><extra></extra>'
        )
        bars.append(bar_achieved)
    
    fig = go.Figure(bars)
    fig.update_layout(
        barmode='stack',
        title=dict(
            text="📊 学習進捗概要",
            x=0.5,
            font=dict(size=16, color='#2c3e50')
        ),
        xaxis=dict(
            title=dict(text="所要時間（時間）", font=dict(size=12, color='#34495e')),
            tickfont=dict(size=11, color='#34495e'),
            gridcolor='rgba(0,0,0,0.1)',
            showgrid=True
        ),
        yaxis=dict(
            tickfont=dict(size=12, color='#34495e')
        ),
        height=280,
        margin=dict(l=60, r=40, t=50, b=60),
        font=dict(family="Arial, sans-serif", size=12),
        plot_bgcolor='rgba(248,249,250,0.8)',
        paper_bgcolor='white',
        showlegend=False,
        # アニメーション効果
        transition={
            'duration': 1200,
            'easing': 'elastic-out'
        }
    )
    return fig

# 進捗統計表示
@app.callback(
    Output("progress-stats", "children"),
    [Input("progress-data", "data"), Input("current-student-store", "data"), Input("graph-update-trigger", "data")]
)
def update_progress_stats(data, current_user, _trigger):
    # 進捗統計更新コールバック
    df = pd.DataFrame(data)
    # タイムスタンプ列がある場合は削除
    if '_update_timestamp' in df.columns:
        # 統計タイムスタンプカラム削除
        df = df.drop('_update_timestamp', axis=1)
    # 現在の生徒のデータのみにフィルタリング
    df_filtered = df[df['生徒'] == current_user]
    # 統計データフィルタリング完了
    
    # 予定データのみで統計を計算
    df = df_filtered[df_filtered['予定'] == True]
    # 統計データフィルタリング完了
    
    # 予定データがない場合は空の統計を返す
    if df.empty:
        return dbc.Alert([
            html.I(className="fas fa-info-circle me-2"),
            "学習予定を設定すると、ここに進捗統計が表示されます。"
        ], color="info", className="text-center")
    
    # 統計計算 - 達成割合を考慮した進捗時間
    total_planned_time = df[df['予定'] == True]['所要時間'].astype(float).sum()
    
    # 各行の達成時間を個別に計算して合計
    df_planned = df[df['予定'] == True].copy()
    total_done_time = df_planned.apply(calculate_progress_time, axis=1).sum()
    
    # 達成率の計算
    achievement_rate = (total_done_time / total_planned_time * 100) if total_planned_time > 0 else 0
    
    # 冊数統計
    total_planned_books = len(df[df['予定'] == True])
    total_done_books = len(df[df['達成済'] == True])
    
    # 統計カード
    stats_cards = dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.I(className="fas fa-calendar-alt fa-2x text-primary mb-2"),
                        html.H3(f"{total_planned_time:.1f}h", className="text-primary mb-1 fw-bold"),
                        html.P("予定時間", className="text-muted mb-0 fw-semibold")
                    ], className="text-center")
                ], className="py-3")
            ], className="shadow-sm border-0", style={"background": "linear-gradient(135deg, #e3f2fd 0%, #ffffff 100%)"})
        ], xs=6, sm=6, md=3, lg=3, xl=3),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.I(className="fas fa-check-circle fa-2x text-success mb-2"),
                        html.H3(f"{total_done_time:.1f}h", className="text-success mb-1 fw-bold"),
                        html.P("達成時間", className="text-muted mb-0 fw-semibold")
                    ], className="text-center")
                ], className="py-3")
            ], className="shadow-sm border-0", style={"background": "linear-gradient(135deg, #e8f5e8 0%, #ffffff 100%)"})
        ], xs=6, sm=6, md=3, lg=3, xl=3),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.I(className="fas fa-chart-pie fa-2x text-info mb-2"),
                        html.H3(f"{achievement_rate:.1f}%", className="text-info mb-1 fw-bold"),
                        html.P("達成率", className="text-muted mb-0 fw-semibold")
                    ], className="text-center")
                ], className="py-3")
            ], className="shadow-sm border-0", style={"background": "linear-gradient(135deg, #e1f5fe 0%, #ffffff 100%)"})
        ], xs=6, sm=6, md=3, lg=3, xl=3),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.I(className="fas fa-book fa-2x text-warning mb-2"),
                        html.H3(f"{total_done_books}/{total_planned_books}", className="text-warning mb-1 fw-bold"),
                        html.P("達成冊数", className="text-muted mb-0 fw-semibold")
                    ], className="text-center")
                ], className="py-3")
            ], className="shadow-sm border-0", style={"background": "linear-gradient(135deg, #fff3cd 0%, #ffffff 100%)"})
        ], xs=6, sm=6, md=3, lg=3, xl=3)
    ], className="g-3")
    
    return stats_cards

# 科目別詳細モーダル表示
@app.callback(
    [Output("subject-detail-modal", "is_open"),
     Output("subject-detail-header", "children"),
     Output("subject-detail-graph", "figure"),
     Output("subject-detail-stats", "children")],
    [Input({'type': 'subject-overlay', 'index': dash.ALL}, 'n_clicks')],
    [State("progress-data", "data"), State("subject-detail-modal", "is_open"), State("current-student-store", "data")],
    prevent_initial_call=True
)
def show_subject_detail(overlay_clicks_list, data, is_open, current_user):

    # コールバックトリガー
    # クリックリストチェック
    # モーダル状態チェック
    
    ctx = dash.callback_context
    if not ctx.triggered:
        print("No trigger detected")
        return is_open, "", {}, ""
    
    triggered_prop = ctx.triggered[0]["prop_id"]
    _triggered_value = ctx.triggered[0]["value"]
    
    # トリガー情報チェック
    
    # クリックが発生したかチェック
    if any(clicks and clicks > 0 for clicks in overlay_clicks_list):
        # triggered_propから科目名を直接取得
        import json
        try:
            # triggered_propからID部分を抽出
            # 例: '{"index":"English","type":"subject-overlay"}.n_clicks'
            prop_parts = triggered_prop.split('.')
            id_str = prop_parts[0]
            id_dict = json.loads(id_str)
            subject = id_dict['index']
            # モーダルオープン: {subject}
        except Exception as e:
            print(f"Error parsing subject from triggered_prop: {e}")
            # より安全な正規表現による抽出
            import re
            match = re.search(r'"index":"([^"]+)"', triggered_prop)
            if match:
                subject = match.group(1)
                print(f"Extracted subject via regex: {subject}")
            else:
                # 科目抽出失敗
                return is_open, dash.no_update, dash.no_update, dash.no_update
    else:
        # 有効なクリックなし
        return is_open, dash.no_update, dash.no_update, dash.no_update
    
    df = pd.DataFrame(data)
    # 現在の生徒のデータのみにフィルタリング
    df = df[df['生徒'] == current_user]
    df_subject = df[df['科目'] == subject]
    
    # 科目別横棒グラフを作成（達成割合を考慮）
    planned_books = df_subject[df_subject['予定'] == True][['参考書名', '所要時間']].copy()
    
    # 達成割合を考慮したデータを準備
    achieved_data_detail = []
    
    # 各予定参考書について達成時間を計算
    for _, row in planned_books.iterrows():
        book_name = row['参考書名']
        _total_time = row['所要時間']
        
        # 該当する行を取得して達成時間を計算
        book_row = df_subject[(df_subject['参考書名'] == book_name) & (df_subject['予定'] == True)].iloc[0]
        achieved_time = calculate_progress_time(book_row)
        
        # 達成時間がある場合は達成データに追加
        if achieved_time > 0:
            achieved_data_detail.append({'参考書名': book_name, '所要時間': achieved_time})
    
    # DataFrameに変換
    achieved_df_detail = pd.DataFrame(achieved_data_detail) if achieved_data_detail else pd.DataFrame(columns=['参考書名', '所要時間'])
    
    # カラーパレット（科目別詳細用）
    color_palette = [
        'rgba(52, 144, 220, 0.8)',   # 青
        'rgba(40, 167, 69, 0.8)',    # 緑  
        'rgba(255, 193, 7, 0.8)',    # 黄色
        'rgba(220, 53, 69, 0.8)',    # 赤
        'rgba(111, 66, 193, 0.8)',   # 紫
        'rgba(32, 201, 151, 0.8)',   # ターコイズ
        'rgba(253, 126, 20, 0.8)',   # オレンジ
        'rgba(232, 62, 140, 0.8)',   # ピンク
        'rgba(108, 117, 125, 0.8)',  # グレー
        'rgba(155, 89, 182, 0.8)'    # ライトパープル
    ]
    
    # 全参考書リスト
    all_subject_books = list(df_subject['参考書名'].unique())
    
    # 参考書名をインデックスとして色を割り当て
    def get_book_color_detail(book_name):
        try:
            index = all_subject_books.index(book_name)
            return color_palette[index % len(color_palette)]
        except ValueError:
            return color_palette[0]
    
    # 予定
    bar_planned = go.Bar(
        y=["予定"]*len(planned_books),
        x=planned_books['所要時間'],
        name="📅 予定中",
        orientation='h',
        marker=dict(
            color=[get_book_color_detail(book) for book in planned_books['参考書名']],
            opacity=0.7  # パターンを削除してシンプルに
        ),
        customdata=planned_books['参考書名'],
        hovertemplate='<b>📚 %{customdata}</b><br>' +
                     '⏰ 所要時間: %{x}h<br>' +
                     f'📖 科目: {subject}<br>' +
                     '<i>予定中</i><extra></extra>'
    )
    
    # 達成済み（達成割合を考慮）
    bars_detail = [bar_planned]
    if not achieved_df_detail.empty:
        bar_achieved_detail = go.Bar(
            y=["達成済"]*len(achieved_df_detail),
            x=achieved_df_detail['所要時間'],
            name="✅ 達成済み",
            orientation='h',
            marker=dict(
                color=[get_book_color_detail(book) for book in achieved_df_detail['参考書名']],
                line=dict(color='rgba(255, 255, 255, 0.8)', width=1)
            ),
            customdata=achieved_df_detail['参考書名'],
            hovertemplate='<b>📚 %{customdata}</b><br>' +
                         '⏰ 達成時間: %{x}h<br>' +
                         f'📖 科目: {subject}<br>' +
                         '<i>達成済み</i><extra></extra>'
        )
        bars_detail.append(bar_achieved_detail)
    
    fig = go.Figure(bars_detail)
    fig.update_layout(
        barmode='stack',
        title=dict(
            text=f"📊 {subject} - 詳細進捗分析",
            x=0.5,
            font=dict(size=18, color='#2c3e50', family="Arial Black")
        ),
        xaxis=dict(
            title=dict(text="所要時間（時間）", font=dict(size=13, color='#34495e')),
            tickfont=dict(size=11, color='#34495e'),
            gridcolor='rgba(0,0,0,0.1)',
            showgrid=True,
            zeroline=False
        ),
        yaxis=dict(
            tickfont=dict(size=13, color='#34495e', family="Arial Black")
        ),
        height=280,
        margin=dict(l=80, r=40, t=60, b=60),
        font=dict(family="Arial, sans-serif", size=12),
        plot_bgcolor='rgba(248,249,250,0.6)',
        paper_bgcolor='white',
        showlegend=False,
        # 詳細モーダル用アニメーション効果
        transition={
            'duration': 1500,
            'easing': 'bounce-out'
        }
    )
    
    # 科目別統計を作成（達成割合を考慮した計算）
    subject_planned_time = df_subject[df_subject['予定'] == True]['所要時間'].astype(float).sum()
    df_subject_planned = df_subject[df_subject['予定'] == True].copy()
    subject_done_time = df_subject_planned.apply(calculate_progress_time, axis=1).sum()
    subject_achievement_rate = (subject_done_time / subject_planned_time * 100) if subject_planned_time > 0 else 0
    _total_books = len(df_subject)
    planned_books_count = len(df_subject[df_subject['予定'] == True])
    done_books_count = len(df_subject[df_subject['達成済'] == True])
    
    stats_cards = dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.I(className="fas fa-calendar-check fa-lg text-primary mb-2"),
                        html.H4(f"{subject_planned_time:.1f}h", className="text-primary mb-1 fw-bold"),
                        html.P("予定時間", className="text-muted mb-1 fw-semibold small"),
                        dbc.Badge(f"{planned_books_count}冊", color="primary", className="rounded-pill")
                    ], className="text-center")
                ], className="py-2")
            ], className="shadow border-0 h-100", style={"background": "linear-gradient(135deg, #e3f2fd 0%, #f8f9fa 100%)", "borderLeft": "4px solid #007bff !important"})
        ], width=3),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.I(className="fas fa-trophy fa-lg text-success mb-2"),
                        html.H4(f"{subject_done_time:.1f}h", className="text-success mb-1 fw-bold"),
                        html.P("達成時間", className="text-muted mb-1 fw-semibold small"),
                        dbc.Badge(f"{done_books_count}冊", color="success", className="rounded-pill")
                    ], className="text-center")
                ], className="py-2")
            ], className="shadow border-0 h-100", style={"background": "linear-gradient(135deg, #e8f5e8 0%, #f8f9fa 100%)", "borderLeft": "4px solid #28a745 !important"})
        ], width=3),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.I(className="fas fa-chart-line fa-lg text-info mb-2"),
                        html.H4(f"{subject_achievement_rate:.1f}%", className="text-info mb-1 fw-bold"),
                        html.P("達成率", className="text-muted mb-1 fw-semibold small"),
                        dbc.Progress(
                            value=subject_achievement_rate, 
                            color="info", 
                            className="mt-2", 
                            style={"height": "6px"}
                        )
                    ], className="text-center")
                ], className="py-2")
            ], className="shadow border-0 h-100", style={"background": "linear-gradient(135deg, #e1f5fe 0%, #f8f9fa 100%)", "borderLeft": "4px solid #17a2b8 !important"})
        ], width=3),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.I(className="fas fa-books fa-lg text-warning mb-2"),
                        html.H4(f"{done_books_count}/{planned_books_count}", className="text-warning mb-1 fw-bold"),
                        html.P("達成冊数", className="text-muted mb-1 fw-semibold small"),
                        html.Small(f"{subject}科目", className="text-muted")
                    ], className="text-center")
                ], className="py-2")
            ], className="shadow border-0 h-100", style={"background": "linear-gradient(135deg, #fff3cd 0%, #f8f9fa 100%)", "borderLeft": "4px solid #ffc107 !important"})
        ], width=3)
    ], className="g-3")
    
    return True, f"📖 {subject} - 詳細情報", fig, stats_cards

# データ入力モーダル表示/非表示
@app.callback(
    Output("data-input-modal", "is_open"),
    [Input("open-data-input-modal", "n_clicks"), Input("cancel-data-btn", "n_clicks")],
    [State("data-input-modal", "is_open")],
    prevent_initial_call=True
)
def toggle_data_input_modal(_open_clicks, _cancel_clicks, is_open):
    ctx = dash.callback_context
    if not ctx.triggered:
        return is_open
    
    button_id = ctx.triggered[0]["prop_id"].split(".")[0]
    if button_id in ["open-data-input-modal", "cancel-data-btn"]:
        return not is_open
    return is_open

# データ追加処理
@app.callback(
    [Output("progress-data", "data", allow_duplicate=True),
     Output("input-status-message", "children"),
     Output("input-route-level", "value"),
     Output("input-subject", "value"),
     Output("input-book-name", "value"),
     Output("input-time", "value")],
    Input("add-data-btn", "n_clicks"),
    [State("input-route-level", "value"),
     State("input-subject", "value"),
     State("input-book-name", "value"),
     State("input-time", "value"),
     State("progress-data", "data"),
     State("current-student-store", "data")],
    prevent_initial_call=True
)
def add_new_data(n_clicks, route_level, subject, book_name, time_hours, current_data, current_user):
    if not n_clicks:
        return dash.no_update, "", "", "", "", ""
    
    # 入力値の検証
    if not all([route_level, subject, book_name, time_hours]):
        return (dash.no_update, 
                dbc.Alert("すべての項目を入力してください。", color="danger", dismissable=True),
                dash.no_update, dash.no_update, dash.no_update, dash.no_update)
    
    try:
        time_hours = float(time_hours)
        if time_hours <= 0:
            raise ValueError()
    except (ValueError, TypeError):
        return (dash.no_update, 
                dbc.Alert("所要時間は正の数値を入力してください。", color="danger", dismissable=True),
                dash.no_update, dash.no_update, dash.no_update, dash.no_update)
    
    # 新しいデータを作成
    new_row = {
        "ルートレベル": route_level.strip(),
        "科目": subject.strip(),
        "参考書名": book_name.strip(),
        "所要時間": time_hours,
        "予定": False,
        "達成済": False,
        "達成割合": "",
        "生徒": current_user
    }
    
    # データフレームに追加
    df_current = pd.DataFrame(current_data)
    
    # 重複チェック
    duplicate = df_current[
        (df_current["科目"] == new_row["科目"]) & 
        (df_current["参考書名"] == new_row["参考書名"])
    ]
    if not duplicate.empty:
        return (dash.no_update, 
                dbc.Alert("同じ科目・参考書名の組み合わせが既に存在します。", color="warning", dismissable=True),
                dash.no_update, dash.no_update, dash.no_update, dash.no_update)
    
    # データフレームに新しい行を追加
    df_new = pd.concat([df_current, pd.DataFrame([new_row])], ignore_index=True)
    
    # CSVファイルに保存
    try:
        csv_path = os.path.join(os.path.dirname(__file__), 'route-subject-text-time.csv')
        # バックアップ作成
        backup_path = csv_path + '.bak'
        if os.path.exists(csv_path):
            import shutil
            shutil.copy2(csv_path, backup_path)
        
        # CSVファイルに保存（列の順序を保持）
        column_order = ["ルートレベル", "科目", "参考書名", "所要時間", "予定", "達成済", "達成割合", "生徒"]
        df_new = df_new[column_order]
        df_new.to_csv(csv_path, index=False, encoding='utf-8')
        
        # 保存が成功したらバックアップを削除
        if os.path.exists(backup_path):
            os.remove(backup_path)
        
        # グローバルのsubjectsリストも更新
        global subjects
        subjects = df_new['科目'].unique()
        
        return (df_new.to_dict("records"), 
                dbc.Alert(f"データが正常に追加されCSVファイルに保存されました！\n保存先: {csv_path}", color="success", dismissable=True),
                "", "", "", "")
    except Exception as e:
        # エラーが発生した場合、バックアップから復元を試みる
        backup_path = csv_path + '.bak'
        if os.path.exists(backup_path):
            try:
                import shutil
                shutil.move(backup_path, csv_path)
            except:
                pass
        return (dash.no_update, 
                dbc.Alert(f"CSVファイルの保存に失敗しました: {str(e)}\nバックアップから復元しました。", color="danger", dismissable=True),
                dash.no_update, dash.no_update, dash.no_update, dash.no_update)

# データ削除モーダル表示/非表示
@app.callback(
    Output("data-delete-modal", "is_open"),
    [Input("open-data-delete-modal", "n_clicks"), Input("cancel-delete-btn", "n_clicks")],
    [State("data-delete-modal", "is_open")],
    prevent_initial_call=True
)
def toggle_data_delete_modal(open_clicks, cancel_clicks, is_open):
    ctx = dash.callback_context
    if not ctx.triggered:
        return is_open
    
    button_id = ctx.triggered[0]["prop_id"].split(".")[0]
    if button_id in ["open-data-delete-modal", "cancel-delete-btn"]:
        return not is_open
    return is_open

# 削除対象の参考書リスト表示
@app.callback(
    Output("delete-books-list", "children"),
    [Input("delete-route-filter", "value"),
     Input("delete-subject-filter", "value"), 
     Input("data-delete-modal", "is_open"),
     Input("delete-search-input", "value"),
     Input("progress-data", "data")],  # データ更新でリアルタイム更新
    prevent_initial_call=True
)
def update_delete_books_list(route_filter, subject_filter, is_open, search_value, data):
    if not is_open:
        return []
    
    df = pd.DataFrame(data)
    
    # ルートフィルタリング
    if route_filter == "all":
        filtered_df = df
    else:
        filtered_df = df[df['ルートレベル'] == route_filter]
    
    # 科目フィルタリング
    if subject_filter != "all":
        filtered_df = filtered_df[filtered_df['科目'] == subject_filter]
    
    # 検索フィルタリング
    if search_value:
        filtered_df = filtered_df[filtered_df['参考書名'].str.contains(search_value, case=False, na=False)]
    
    if filtered_df.empty:
        return [html.P("該当する参考書がありません。", className="text-muted")]
    
    checkboxes = []
    for idx, row in filtered_df.iterrows():
        checkbox = dbc.Checkbox(
            id={'type': 'delete-checkbox', 'index': f"{row['科目']}|{row['参考書名']}"},
            label=html.Span([
                dbc.Badge(row['ルートレベル'], color="info", className="me-2"),
                f"【{row['科目']}】{row['参考書名']} ({row['所要時間']}h)"
            ]),
            value=False,
            className="mb-2"
        )
        checkboxes.append(checkbox)
    
    return checkboxes

# データ削除処理
@app.callback(
    [Output("progress-data", "data", allow_duplicate=True),
     Output("delete-status-message", "children")],
    Input("confirm-delete-btn", "n_clicks"),
    [State({'type': 'delete-checkbox', 'index': dash.ALL}, 'value'),
     State({'type': 'delete-checkbox', 'index': dash.ALL}, 'id'),
     State("progress-data", "data")],
    prevent_initial_call=True
)
def delete_selected_data(n_clicks, checkbox_values, checkbox_ids, current_data):
    if not n_clicks:
        return dash.no_update, ""
    
    # 選択されたアイテムを取得
    selected_items = []
    for value, checkbox_id in zip(checkbox_values, checkbox_ids):
        if value:  # チェックされている場合
            subject, book_name = checkbox_id['index'].split('|', 1)
            selected_items.append((subject, book_name))
    
    if not selected_items:
        return (dash.no_update, 
                dbc.Alert("削除するアイテムを選択してください。", color="warning", dismissable=True))
    
    # データフレームから削除
    df_current = pd.DataFrame(current_data)
    
    # 削除対象のインデックスを特定
    delete_indices = []
    for subject, book_name in selected_items:
        mask = (df_current['科目'] == subject) & (df_current['参考書名'] == book_name)
        indices = df_current[mask].index.tolist()
        delete_indices.extend(indices)
    
    if not delete_indices:
        return (dash.no_update, 
                dbc.Alert("削除対象のデータが見つかりません。", color="warning", dismissable=True))
    
    # データフレームから削除
    df_new = df_current.drop(delete_indices).reset_index(drop=True)
    
    # CSVファイルに保存
    try:
        csv_path = os.path.join(os.path.dirname(__file__), 'route-subject-text-time.csv')
        # バックアップ作成
        backup_path = csv_path + '.bak'
        if os.path.exists(csv_path):
            import shutil
            shutil.copy2(csv_path, backup_path)
        
        # CSVファイルに保存
        column_order = ["ルートレベル", "科目", "参考書名", "所要時間", "予定", "達成済", "達成割合", "生徒"]
        df_new = df_new[column_order]
        df_new.to_csv(csv_path, index=False, encoding='utf-8')
        
        # 保存が成功したらバックアップを削除
        if os.path.exists(backup_path):
            os.remove(backup_path)
        
        # グローバルのsubjectsリストも更新
        global subjects
        subjects = df_new['科目'].unique()
        
        deleted_count = len(selected_items)
        return (df_new.to_dict("records"), 
                dbc.Alert(f"{deleted_count}件のデータが削除されCSVファイルが更新されました！", 
                         color="success", dismissable=True))
        
    except Exception as e:
        # エラーが発生した場合、バックアップから復元を試みる
        backup_path = csv_path + '.bak'
        if os.path.exists(backup_path):
            try:
                import shutil
                shutil.move(backup_path, csv_path)
            except:
                pass
        return (dash.no_update, 
                dbc.Alert(f"CSVファイルの更新に失敗しました: {str(e)}", color="danger", dismissable=True))

# 一括チェック管理モーダル表示/非表示
@app.callback(
    Output("bulk-check-modal", "is_open"),
    [Input("open-bulk-check-modal", "n_clicks")],
    [State("bulk-check-modal", "is_open")],
    prevent_initial_call=True
)
def toggle_bulk_check_modal(open_clicks, is_open):
    if open_clicks:
        return not is_open
    return is_open

# 一括チェック管理の科目選択表示
@app.callback(
    Output("bulk-check-subject-selection", "children"),
    [Input("bulk-check-modal", "is_open")],
    [State("progress-data", "data")],
    prevent_initial_call=True
)
def update_subject_selection(is_open, data):
    if not is_open or not data:
        return []
    
    df = pd.DataFrame(data)
    all_subjects = df['科目'].unique()
    
    # 科目の順序を指定
    subject_order = ['英語', '国語', '日本史', '世界史', '政治経済', '数学', '物理', '化学', '生物']
    subjects = [subject for subject in subject_order if subject in all_subjects]
    
    buttons = []
    for subject in subjects:
        button = dbc.Col([
            dbc.Button(
                [html.I(className="fas fa-book me-2"), subject], 
                id={'type': 'bulk-subject-btn', 'index': subject}, 
                color="outline-primary", 
                className="w-100 mb-2",
                size="lg"
            )
        ], width=4)
        buttons.append(button)
    
    return dbc.Row(buttons, className="g-2")

# 科目選択から一括チェックボタン管理モーダル表示
@app.callback(
    [Output("bulk-manage-modal", "is_open"),
     Output("bulk-manage-header", "children"),
     Output("bulk-check-modal", "is_open", allow_duplicate=True)],
    [Input({'type': 'bulk-subject-btn', 'index': dash.ALL}, 'n_clicks')],
    [State("bulk-manage-modal", "is_open")],
    prevent_initial_call=True
)
def open_bulk_manage_from_subject(subject_clicks, is_open):
    ctx = dash.callback_context
    if not ctx.triggered:
        return is_open, dash.no_update, dash.no_update
    
    # どのボタンがクリックされたかを特定
    if any(clicks and clicks > 0 for clicks in subject_clicks):
        # トリガーされたIDから科目を抽出
        trigger_prop = ctx.triggered[0]["prop_id"]
        
        try:
            # prop_idから科目名を抽出
            import re
            match = re.search(r'"index":"([^"]+)"', trigger_prop)
            if match:
                subject = match.group(1)
                return True, f"📚 {subject} - 一括チェックボタン管理", False
            else:
                return is_open, dash.no_update, dash.no_update
        except Exception:
            return is_open, dash.no_update, dash.no_update
    
    return is_open, dash.no_update, dash.no_update

# 科目モーダルから一括チェックボタン管理モーダル表示
@app.callback(
    [Output("bulk-manage-modal", "is_open", allow_duplicate=True),
     Output("bulk-manage-header", "children", allow_duplicate=True)],
    [Input("open-bulk-manage-btn", "n_clicks")],
    [State("subject-modal-header", "children"),
     State("bulk-manage-modal", "is_open")],
    prevent_initial_call=True
)
def open_bulk_manage_from_modal(manage_clicks, header, is_open):
    if not manage_clicks or not header:
        return is_open, dash.no_update
    
    subject = header.replace("の参考書リスト", "")
    return True, f"📚 {subject} - 一括チェックボタン管理"

# 一括チェックボタンリスト表示
@app.callback(
    Output("bulk-button-list", "children"),
    [Input("bulk-manage-modal", "is_open")],
    [State("bulk-manage-header", "children")],
    prevent_initial_call=True
)
def update_bulk_button_list(is_open, header):
    import sys
    
    message = f"=== 一括チェックボタンリスト表示 === is_open: {is_open}, header: {header}"
    print(message)
    sys.stdout.flush()
    
    # ファイルにもログを書き出し
    with open("debug.log", "a", encoding="utf-8") as f:
        f.write(f"{message}\n")
    
    if not is_open or not header:
        skip_message = "ボタンリスト更新スキップ: モーダルが閉じているかヘッダーが空"
        print(skip_message)
        with open("debug.log", "a", encoding="utf-8") as f:
            f.write(f"{skip_message}\n")
        return []
    
    subject = header.replace("📚 ", "").replace(" - 一括チェックボタン管理", "")
    subject_message = f"対象科目: {subject}"
    print(subject_message)
    with open("debug.log", "a", encoding="utf-8") as f:
        f.write(f"{subject_message}\n")
    
    # 既存の設定を読み込み
    bulk_buttons_path = os.path.join(os.path.dirname(__file__), 'bulk_buttons.json')
    bulk_buttons = {}
    if os.path.exists(bulk_buttons_path):
        try:
            with open(bulk_buttons_path, 'r', encoding='utf-8') as f:
                bulk_buttons = json.load(f)
            print(f"既存設定読み込み完了: {list(bulk_buttons.keys())}")
        except Exception as e:
            print(f"既存設定読み込み失敗: {e}")
            bulk_buttons = {}
    else:
        print("bulk_buttons.jsonファイルが存在しません")
    
    subject_buttons = bulk_buttons.get(subject, {})
    print(f"科目'{subject}'のボタン数: {len(subject_buttons)}")
    
    if not subject_buttons:
        return dbc.Alert("まだボタンが作成されていません。「新しいボタンを追加」から作成してください。", color="info")
    
    cards = []
    for button_name, button_books in subject_buttons.items():
        card = dbc.Card([
            dbc.CardHeader([
                dbc.Row([
                    dbc.Col([
                        html.H6(f"✅ {button_name}", className="mb-0")
                    ], width=6),
                    dbc.Col([
                        dbc.ButtonGroup([
                            dbc.Button([
                                html.I(className="fas fa-edit me-2"),
                                "編集"
                            ], id={'type': 'edit-bulk-btn', 'subject': subject, 'name': button_name}, 
                               color="warning", size="lg", 
                               style={"fontWeight": "600", "borderRadius": "8px 0 0 8px"}),
                            dbc.Button([
                                html.I(className="fas fa-trash me-2"),
                                "削除"
                            ], id={'type': 'delete-bulk-btn', 'subject': subject, 'name': button_name}, 
                               color="danger", size="lg",
                               style={"fontWeight": "600", "borderRadius": "0 8px 8px 0"})
                        ], size="lg")
                    ], width=6, className="text-end")
                ])
            ]),
            dbc.CardBody([
                html.P(f"対象参考書数: {len(button_books)}冊", className="text-muted mb-2"),
                html.Div([
                    dbc.Badge(book, color="secondary", className="me-1 mb-1") 
                    for book in button_books[:5]  # 最初の5冊のみ表示
                ] + ([dbc.Badge(f"+{len(button_books)-5}冊", color="info", className="me-1 mb-1")] if len(button_books) > 5 else []))
            ])
        ], className="mb-3")
        cards.append(card)
    
    return cards

# 科目モーダルの一括チェックボタン表示
@app.callback(
    Output("bulk-check-buttons-container", "children"),
    [Input("subject-modal-tabs", "children")],  # タブが変わったときに更新
    [State("subject-modal-header", "children")],
    prevent_initial_call=True
)
def update_bulk_check_buttons(tabs, header):
    if not header:
        return []
    
    subject = header.replace("の参考書リスト", "")
    
    # 既存の設定を読み込み
    bulk_buttons_path = os.path.join(os.path.dirname(__file__), 'bulk_buttons.json')
    bulk_buttons = {}
    if os.path.exists(bulk_buttons_path):
        try:
            with open(bulk_buttons_path, 'r', encoding='utf-8') as f:
                bulk_buttons = json.load(f)
        except:
            bulk_buttons = {}
    
    subject_buttons = bulk_buttons.get(subject, {})
    
    if not subject_buttons:
        return dbc.Alert("一括チェックボタンが設定されていません。", color="info", className="text-center")
    
    buttons = []
    for button_name in subject_buttons.keys():
        buttons.append(
            dbc.Button(
                [html.I(className="fas fa-check me-1"), button_name],
                id={'type': 'bulk-execute-btn', 'subject': subject, 'name': button_name},
                color="success",
                size="sm",
                className="w-100 mb-2"
            )
        )
    
    return buttons

# ボタン編集モーダル表示
@app.callback(
    [Output("bulk-edit-modal", "is_open"),
     Output("edit-button-name", "value"),
     Output("edit-button-books", "children")],
    [Input({'type': 'edit-bulk-btn', 'subject': dash.ALL, 'name': dash.ALL}, 'n_clicks'),
     Input("add-bulk-button", "n_clicks"),
     Input("cancel-button-edit", "n_clicks")],
    [State("bulk-manage-header", "children"),
     State("progress-data", "data"),
     State("bulk-edit-modal", "is_open")],
    prevent_initial_call=True
)
def toggle_edit_modal(edit_clicks, add_clicks, cancel_clicks, header, data, is_open):
    import sys
    
    message = f"=== ボタン編集モーダル === add_clicks: {add_clicks}, edit_clicks: {edit_clicks}"
    print(message)
    sys.stdout.flush()
    
    # ファイルにもログを書き出し
    with open("debug.log", "a", encoding="utf-8") as f:
        f.write(f"{message}\n")
    
    ctx = dash.callback_context
    if not ctx.triggered:
        skip_message = "編集モーダル: ctx.triggeredが空"
        print(skip_message)
        with open("debug.log", "a", encoding="utf-8") as f:
            f.write(f"{skip_message}\n")
        return is_open, dash.no_update, dash.no_update
    
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
    trigger_message = f"編集モーダルトリガー: {trigger_id}"
    print(trigger_message)
    with open("debug.log", "a", encoding="utf-8") as f:
        f.write(f"{trigger_message}\n")
    
    # 保存ボタンによるトリガーの場合は何もしない（保存コールバックが処理する）
    if trigger_id == "save-button-edit":
        skip_save_message = "編集モーダル: 保存ボタンによるトリガーはスキップ"
        print(skip_save_message)
        with open("debug.log", "a", encoding="utf-8") as f:
            f.write(f"{skip_save_message}\n")
        return is_open, dash.no_update, dash.no_update
    
    if "edit-bulk-btn" in trigger_id:
        # 編集ボタンのクリック数をチェック - None の場合は新規作成されたボタンなのでスキップ
        if not edit_clicks or all(click is None or click == 0 for click in edit_clicks):
            skip_edit_message = "編集モーダル: 編集ボタンのクリックが無効（新規作成されたボタン）"
            print(skip_edit_message)
            with open("debug.log", "a", encoding="utf-8") as f:
                f.write(f"{skip_edit_message}\n")
            return is_open, dash.no_update, dash.no_update
        
        # 編集モード
        button_info = eval(trigger_id)
        subject = button_info['subject']
        button_name = button_info['name']
        
        # 既存設定読み込み
        bulk_buttons_path = os.path.join(os.path.dirname(__file__), 'bulk_buttons.json')
        bulk_buttons = {}
        if os.path.exists(bulk_buttons_path):
            try:
                with open(bulk_buttons_path, 'r', encoding='utf-8') as f:
                    bulk_buttons = json.load(f)
            except:
                bulk_buttons = {}
        
        selected_books = bulk_buttons.get(subject, {}).get(button_name, [])
        
        # 参考書チェックボックス生成
        df = pd.DataFrame(data)
        subject_books = df[df['科目'] == subject]
        
        checkboxes = []
        for idx, row in subject_books.iterrows():
            book_name = row['参考書名']
            is_checked = book_name in selected_books
            checkboxes.append(
                dbc.Checkbox(
                    id={'type': 'edit-book-checkbox', 'book': book_name},
                    label=f"【{row['ルートレベル']}】{book_name} ({row['所要時間']}h)",
                    value=is_checked,
                    className="mb-2"
                )
            )
        
        return True, button_name, checkboxes
        
    elif trigger_id == "add-bulk-button":
        # 新規追加モード
        add_message = f"=== 新しいボタン追加処理開始 === header: '{header}', data件数: {len(data) if data else 0}"
        print(add_message)
        with open("debug.log", "a", encoding="utf-8") as f:
            f.write(f"{add_message}\n")
        
        if not header or not data:
            skip_message = "新規追加処理スキップ: ヘッダーまたはデータが不足"
            print(skip_message)
            with open("debug.log", "a", encoding="utf-8") as f:
                f.write(f"{skip_message}\n")
            return is_open, dash.no_update, dash.no_update
            
        subject = header.replace("📚 ", "").replace(" - 一括チェックボタン管理", "")
        subject_message = f"対象科目: '{subject}'"
        print(subject_message)
        with open("debug.log", "a", encoding="utf-8") as f:
            f.write(f"{subject_message}\n")
        
        df = pd.DataFrame(data)
        subject_books = df[df['科目'] == subject]
        books_message = f"科目の参考書数: {len(subject_books)}"
        print(books_message)
        with open("debug.log", "a", encoding="utf-8") as f:
            f.write(f"{books_message}\n")
        
        checkboxes = []
        for idx, row in subject_books.iterrows():
            book_name = row['参考書名']
            checkboxes.append(
                dbc.Checkbox(
                    id={'type': 'edit-book-checkbox', 'book': book_name},
                    label=f"【{row['ルートレベル']}】{book_name} ({row['所要時間']}h)",
                    value=False,
                    className="mb-2"
                )
            )
        
        complete_message = f"チェックボックス作成完了: {len(checkboxes)}個"
        print(complete_message)
        with open("debug.log", "a", encoding="utf-8") as f:
            f.write(f"{complete_message}\n")
        return True, "", checkboxes
        
    elif trigger_id == "cancel-button-edit":
        return False, dash.no_update, dash.no_update
    
    return is_open, dash.no_update, dash.no_update

# ボタン保存処理
@app.callback(
    [Output("bulk-edit-modal", "is_open", allow_duplicate=True),
     Output("bulk-button-list", "children", allow_duplicate=True)],
    Input("save-button-edit", "n_clicks"),
    [State("edit-button-name", "value"),
     State({'type': 'edit-book-checkbox', 'book': dash.ALL}, 'value'),
     State({'type': 'edit-book-checkbox', 'book': dash.ALL}, 'id'),
     State("bulk-manage-header", "children")],
    prevent_initial_call=True
)
def save_button_edit(n_clicks, button_name, checkbox_values, checkbox_ids, header):
    import sys
    
    # ファイルログへの出力も追加
    debug_msg = f"=== 保存コールバック呼び出し開始 === n_clicks: {n_clicks}"
    print(debug_msg)
    with open("debug.log", "a", encoding="utf-8") as f:
        f.write(f"{debug_msg}\n")
    
    # 簡潔なログ出力
    def log_msg(msg):
        print(msg)
        with open("debug.log", "a", encoding="utf-8") as f:
            f.write(f"{msg}\n")
    
    log_msg(f"n_clicks: {n_clicks}")
    log_msg(f"button_name: '{button_name}'")
    log_msg(f"header: '{header}'")
    log_msg(f"checkbox_values: {checkbox_values}")
    log_msg(f"checkbox_ids数: {len(checkbox_ids) if checkbox_ids else 0}")
    sys.stdout.flush()
    
    if not n_clicks:
        log_msg("保存処理スキップ: n_clicksがNoneまたは0")
        return dash.no_update, dash.no_update
    
    log_msg("=== 保存処理メイン開始 ===")
    
    if not button_name:
        log_msg("保存処理スキップ: ボタン名が空")
        return dash.no_update, dash.no_update
        
    if not header:
        log_msg("保存処理スキップ: ヘッダーが空")
        return dash.no_update, dash.no_update
    
    log_msg("=== ヘッダー処理開始 ===")
    subject = header.replace("📚 ", "").replace(" - 一括チェックボタン管理", "")
    log_msg(f"抽出された科目: '{subject}'")
    
    log_msg("=== チェックボックス処理開始 ===")
    # 選択された参考書を取得
    selected_books = []
    try:
        for i, (value, checkbox_id) in enumerate(zip(checkbox_values, checkbox_ids)):
            log_msg(f"チェックボックス {i}: value={value}, id={checkbox_id}")
            if value:
                selected_books.append(checkbox_id['book'])
    except Exception as e:
        log_msg(f"チェックボックス処理エラー: {e}")
        return dash.no_update, dash.no_update
    
    log_msg(f"選択された参考書: {selected_books}")
    
    if not selected_books:
        log_msg("警告: 参考書が選択されていません")
        return dash.no_update, dash.no_update
    
    log_msg("=== JSON保存処理開始 ===")
    # 設定を保存
    bulk_buttons_path = os.path.join(os.path.dirname(__file__), 'bulk_buttons.json')
    log_msg(f"JSONファイルパス: {bulk_buttons_path}")
    bulk_buttons = {}
    log_msg("JSONファイル読み込み開始")
    if os.path.exists(bulk_buttons_path):
        try:
            with open(bulk_buttons_path, 'r', encoding='utf-8') as f:
                bulk_buttons = json.load(f)
            log_msg("既存JSONファイル読み込み成功")
        except Exception as e:
            log_msg(f"既存JSONファイル読み込みエラー: {e}")
            bulk_buttons = {}
    else:
        log_msg("JSONファイルが存在しません - 新規作成します")
    
    log_msg("データ構造準備中")
    if subject not in bulk_buttons:
        bulk_buttons[subject] = {}
        log_msg(f"新しい科目 '{subject}' を追加しました")
    
    log_msg(f"ボタン '{button_name}' を科目 '{subject}' に設定中")
    bulk_buttons[subject][button_name] = selected_books
    
    try:
        log_msg(f"=== ファイル書き込み開始 === 科目={subject}, ボタン名={button_name}, 参考書数={len(selected_books)}")
        with open(bulk_buttons_path, 'w', encoding='utf-8') as f:
            json.dump(bulk_buttons, f, ensure_ascii=False, indent=2)
        log_msg(f"JSONファイルへの保存完了: {bulk_buttons_path}")
        
        # 保存直後にファイル内容を確認
        try:
            with open(bulk_buttons_path, 'r', encoding='utf-8') as f:
                saved_content = json.load(f)
            log_msg(f"=== 保存後の確認 === ファイル内容: {saved_content}")
        except Exception as check_e:
            log_msg(f"保存後の確認でエラー: {check_e}")
        
        log_msg(f"ボタン '{button_name}' を保存しました")
        
        # ボタンリストを更新
        log_msg("=== ボタンリスト更新開始 ===")
        updated_list = update_bulk_button_list(True, header)
        log_msg(f"ボタンリスト更新完了: {len(updated_list) if isinstance(updated_list, list) else 'Alert表示'}")
        
        # ボタンリスト更新後にもう一度ファイル内容を確認
        try:
            with open(bulk_buttons_path, 'r', encoding='utf-8') as f:
                final_content = json.load(f)
            log_msg(f"=== ボタンリスト更新後の確認 === ファイル内容: {final_content}")
        except Exception as final_e:
            log_msg(f"ボタンリスト更新後の確認でエラー: {final_e}")
        
        log_msg("=== 保存コールバック正常終了 ===")
        log_msg("モーダルを閉じる: False を返します")
        # モーダルを閉じて、一覧を更新
        return False, updated_list
    except Exception as e:
        error_msg = f"=== 保存処理でエラーが発生 === エラー: {e}"
        print(error_msg)
        log_msg(error_msg)
        
        import traceback
        trace_msg = f"スタックトレース: {traceback.format_exc()}"
        print(trace_msg)
        log_msg(trace_msg)
        
        return dash.no_update, dash.no_update

# ボタン削除処理
@app.callback(
    Output("bulk-button-list", "children", allow_duplicate=True),
    Input({'type': 'delete-bulk-btn', 'subject': dash.ALL, 'name': dash.ALL}, 'n_clicks'),
    [State("bulk-manage-header", "children")],
    prevent_initial_call=True
)
def delete_bulk_button(delete_clicks, header):
    ctx = dash.callback_context
    
    # ファイルログへの出力も追加
    def log_delete_msg(msg):
        print(msg)
        with open("debug.log", "a", encoding="utf-8") as f:
            f.write(f"{msg}\n")
    
    # 詳細な削除処理ログを追加
    log_delete_msg(f"=== 削除コールバック呼び出し === delete_clicks: {delete_clicks}")
    log_delete_msg(f"削除コールバック - ctx.triggered: {ctx.triggered}")
    log_delete_msg(f"削除コールバック - header: {header}")
    
    # 基本チェック：コンテキストとヘッダーがない場合はスキップ
    if not ctx.triggered or not header:
        log_delete_msg("削除処理スキップ: トリガーまたはヘッダーなし")
        return dash.no_update
    
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
    triggered_value = ctx.triggered[0]["value"]
    log_delete_msg(f"削除トリガーID: {trigger_id}")
    log_delete_msg(f"削除トリガー値: {triggered_value}")
    
    # 削除ボタンのトリガーかチェック
    if "delete-bulk-btn" not in trigger_id:
        log_delete_msg(f"削除処理スキップ: 削除ボタン以外のトリガー ({trigger_id})")
        return dash.no_update
    
    # delete_clicks に実際のクリック数があるかチェック
    if not delete_clicks or all(click is None or click == 0 for click in delete_clicks):
        log_delete_msg(f"削除処理スキップ: 削除クリック数が無効 (delete_clicks: {delete_clicks})")
        return dash.no_update
    
    # 実際にクリックされたボタンを特定
    log_delete_msg(f"削除処理続行: delete_clicks = {delete_clicks}")
    
    try:
        button_info = eval(trigger_id)
        subject = button_info['subject']
        button_name = button_info['name']
        log_delete_msg(f"削除対象: 科目={subject}, ボタン名={button_name}")
    except Exception as e:
        log_delete_msg(f"ボタン情報の解析に失敗: {e}")
        return dash.no_update
    
    # 設定から削除
    bulk_buttons_path = os.path.join(os.path.dirname(__file__), 'bulk_buttons.json')
    bulk_buttons = {}
    if os.path.exists(bulk_buttons_path):
        try:
            with open(bulk_buttons_path, 'r', encoding='utf-8') as f:
                bulk_buttons = json.load(f)
            
            log_delete_msg(f"現在のJSONファイル内容: {bulk_buttons}")
            
            if subject in bulk_buttons and button_name in bulk_buttons[subject]:
                del bulk_buttons[subject][button_name]
                
                with open(bulk_buttons_path, 'w', encoding='utf-8') as f:
                    json.dump(bulk_buttons, f, ensure_ascii=False, indent=2)
                log_delete_msg(f"=== 削除実行完了 === ボタン '{button_name}' を削除しました (科目: {subject})")
                log_delete_msg(f"削除後のJSONファイル更新完了")
            else:
                log_delete_msg(f"削除対象が見つかりません: 科目'{subject}'にボタン'{button_name}'が存在しません")
                log_delete_msg(f"利用可能な科目: {list(bulk_buttons.keys())}")
                if subject in bulk_buttons:
                    log_delete_msg(f"科目'{subject}'のボタン: {list(bulk_buttons[subject].keys())}")
        except Exception as e:
            log_delete_msg(f"ボタン削除に失敗しました: {e}")
            return dash.no_update
    else:
        log_delete_msg(f"JSONファイルが存在しません: {bulk_buttons_path}")
    
    # リストを更新
    return update_bulk_button_list(True, header)

# 一括チェック実行
@app.callback(
    [Output("progress-data", "data", allow_duplicate=True),
     Output("subject-modal-content", "children", allow_duplicate=True)],
    Input({'type': 'bulk-execute-btn', 'subject': dash.ALL, 'name': dash.ALL}, 'n_clicks'),
    [State("progress-data", "data"),
     State("subject-tabs", "active_tab"),
     State("subject-modal-header", "children")],
    prevent_initial_call=True
)
def execute_bulk_check(execute_clicks, data, active_tab, header):
    ctx = dash.callback_context
    if not ctx.triggered or not data or not header:
        return dash.no_update, dash.no_update
    
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
    if "bulk-execute-btn" not in trigger_id:
        return dash.no_update, dash.no_update
    
    button_info = eval(trigger_id)
    subject = button_info['subject']
    button_name = button_info['name']
    
    # ボタン設定を読み込み
    bulk_buttons_path = os.path.join(os.path.dirname(__file__), 'bulk_buttons.json')
    bulk_buttons = {}
    if os.path.exists(bulk_buttons_path):
        try:
            with open(bulk_buttons_path, 'r', encoding='utf-8') as f:
                bulk_buttons = json.load(f)
        except:
            return dash.no_update, dash.no_update
    
    target_books = bulk_buttons.get(subject, {}).get(button_name, [])
    if not target_books:
        return dash.no_update, dash.no_update
    
    # データ更新
    df = pd.DataFrame(data)
    updated = False
    for idx, row in df.iterrows():
        if row['科目'] == subject and row['参考書名'] in target_books:
            df.at[idx, '予定'] = True
            updated = True
    
    if updated:
        # CSVファイルに保存
        try:
            csv_path = os.path.join(os.path.dirname(__file__), 'route-subject-text-time.csv')
            column_order = ["ルートレベル", "科目", "参考書名", "所要時間", "予定", "達成済", "達成割合", "生徒"]
            df_save = df[column_order]
            df_save.to_csv(csv_path, index=False, encoding='utf-8')
            print(f"一括チェック '{button_name}' を実行しました")
        except Exception as e:
            print(f"一括チェックの保存に失敗しました: {e}")
            return dash.no_update, dash.no_update
        
        # コンテンツを再表示
        return df.to_dict("records"), update_subject_tab(active_tab, header, df.to_dict("records"))
    
    return dash.no_update, dash.no_update

# === 段階的進捗更新フロー ===
# 予定入力コンテンツ作成関数
def create_plan_content(subject_books, search_filter=""):
    """Plan modal content creation function"""
    filtered_books = subject_books
    if search_filter:
        filtered_books = subject_books[subject_books['参考書名'].str.contains(search_filter, case=False, na=False)]
    
    plan_content = []
    for _, row in filtered_books.iterrows():
        plan_content.append(
            dbc.Card([
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Div([
                                dbc.Badge(row['ルートレベル'], color="secondary", className="me-2", style={"fontSize": "10px"}),
                                html.Span(row['参考書名'], style={"fontSize": "14px", "fontWeight": "bold"})
                            ])
                        ], width=8),
                        dbc.Col([
                            dbc.Checkbox(
                                id={'type': 'plan-check-new', 'index': f"{row['科目']}|{row['参考書名']}"},
                                value=row['予定'],
                                label="予定に追加"
                            )
                        ], width=4, className="text-end")
                    ])
                ], className="py-2")
            ], className="mb-2 border-0", style={"backgroundColor": "#f8f9fa"})
        )
    
    if not plan_content:
        plan_content = [html.P("該当する参考書が見つかりません。", className="text-muted text-center p-4")]
    
    return plan_content

# 1. 科目選択 → 予定入力モーダルを開く
@app.callback(
    [Output("progress-modal", "is_open", allow_duplicate=True),
     Output("plan-modal", "is_open", allow_duplicate=True),
     Output("plan-modal-header", "children", allow_duplicate=True),
     Output("plan-modal-description", "children", allow_duplicate=True),
     Output("plan-selection-content", "children", allow_duplicate=True),
     Output("selected-subject-store", "data", allow_duplicate=True)],
    [Input({'type': 'subject-btn', 'index': dash.ALL}, 'n_clicks')],
    [State("progress-data", "data"), State("current-student-store", "data")],
    prevent_initial_call=True
)
def open_plan_modal(clicks, data, current_user):
    ctx = dash.callback_context
    if not ctx.triggered or not data:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
    
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
    button_info = eval(trigger_id)
    selected_subject = button_info['index']
    
    df = pd.DataFrame(data)
    # 現在の生徒のデータのみにフィルタリング
    df = df[df['生徒'] == current_user]
    subject_books = df[df['科目'] == selected_subject]
    
    # 予定入力用コンテンツを作成
    plan_content = create_plan_content(subject_books)
    
    header = f"📅 {selected_subject} - 予定設定"
    description = f"{selected_subject}の参考書で予定に追加したいものにチェックを入れてください。"
    
    return False, True, header, description, plan_content, selected_subject

# 予定入力ステップの一括チェック機能
@app.callback(
    Output({'type': 'plan-check-new', 'index': dash.ALL}, 'value', allow_duplicate=True),
    [Input("plan-deselect-all-btn", "n_clicks"),
     Input({'type': 'plan-bulk-execute-btn', 'subject': dash.ALL, 'name': dash.ALL}, 'n_clicks')],
    [State({'type': 'plan-check-new', 'index': dash.ALL}, 'id'),
     State({'type': 'plan-check-new', 'index': dash.ALL}, 'value'),
     State("selected-subject-store", "data"),
     State("progress-data", "data")],
    prevent_initial_call=True
)
def plan_bulk_check(deselect_all_clicks, bulk_execute_clicks, plan_ids, current_values, selected_subject, data):
    ctx = dash.callback_context
    if not ctx.triggered or not plan_ids:
        # dash.no_updateの代わりに現在の値を返す
        if not current_values:
            return [False] * len(plan_ids)
        # リストの長さを調整
        while len(current_values) < len(plan_ids):
            current_values.append(False)
        return current_values[:len(plan_ids)]
    
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
    
    # 現在の値がない場合のデフォルト値
    if not current_values:
        current_values = [False] * len(plan_ids)
    
    # リストの長さを揃える
    while len(current_values) < len(plan_ids):
        current_values.append(False)
    current_values = current_values[:len(plan_ids)]
    
    if "plan-deselect-all-btn" in trigger_id and deselect_all_clicks:
        return [False] * len(plan_ids)
    elif "plan-bulk-execute-btn" in trigger_id and any(bulk_execute_clicks):
        # 一括チェック設定ボタンによる選択
        try:
            button_info = eval(trigger_id)
            subject = button_info['subject']
            button_name = button_info['name']
            
            # 一括チェック設定を読み込み
            bulk_buttons_path = os.path.join(os.path.dirname(__file__), 'bulk_buttons.json')
            bulk_buttons = {}
            if os.path.exists(bulk_buttons_path):
                try:
                    with open(bulk_buttons_path, 'r', encoding='utf-8') as f:
                        bulk_buttons = json.load(f)
                except:
                    return current_values
            
            target_books = bulk_buttons.get(subject, {}).get(button_name, [])
            if not target_books or not data:
                return current_values
                
            df = pd.DataFrame(data)
            new_values = []
            
            for i, plan_id in enumerate(plan_ids):
                try:
                    subj, book_name = plan_id['index'].split('|')
                    if subj == subject and book_name in target_books:
                        new_values.append(True)
                    else:
                        new_values.append(current_values[i] if i < len(current_values) else False)
                except (ValueError, IndexError, KeyError):
                    new_values.append(current_values[i] if i < len(current_values) else False)
            
            # リストの長さを保証
            while len(new_values) < len(plan_ids):
                new_values.append(False)
            
            return new_values[:len(plan_ids)]
        except:
            return current_values
    
    return current_values

# 予定入力ステップの検索機能
@app.callback(
    Output("plan-selection-content", "children", allow_duplicate=True),
    [Input("plan-search-input", "value"),
     Input("plan-search-btn", "n_clicks")],
    [State("selected-subject-store", "data"),
     State("progress-data", "data")],
    prevent_initial_call=True
)
def search_plan_books(search_value, search_clicks, selected_subject, data):
    if not selected_subject or not data:
        return dash.no_update
    
    df = pd.DataFrame(data)
    subject_books = df[df['科目'] == selected_subject]
    
    return create_plan_content(subject_books, search_value or "")

# 予定入力モーダルの一括チェック設定ボタンを表示
@app.callback(
    Output("plan-bulk-buttons-container", "children"),
    Input("selected-subject-store", "data"),
    prevent_initial_call=True
)
def update_plan_bulk_buttons(selected_subject):
    if not selected_subject:
        return []
    
    # 一括チェック設定ファイルから科目のボタンを読み込み
    bulk_buttons_path = os.path.join(os.path.dirname(__file__), 'bulk_buttons.json')
    bulk_buttons = {}
    if os.path.exists(bulk_buttons_path):
        try:
            with open(bulk_buttons_path, 'r', encoding='utf-8') as f:
                bulk_buttons = json.load(f)
        except:
            return [html.P("一括チェック設定が読み込めませんでした。", className="text-muted small")]
    
    subject_buttons = bulk_buttons.get(selected_subject, {})
    if not subject_buttons:
        return [html.P("この科目の一括チェック設定がありません。", className="text-muted small")]
    
    button_elements = []
    for button_name in subject_buttons.keys():
        button_elements.append(
            dbc.Button(
                [html.I(className="fas fa-check-circle me-1"), button_name],
                id={'type': 'plan-bulk-execute-btn', 'subject': selected_subject, 'name': button_name},
                color="info",
                size="sm",
                className="w-100 mb-1"
            )
        )
    
    return button_elements

# 2. 予定入力 → 進捗入力モーダルを開く（選択された科目のみ表示）
@app.callback(
    [Output("plan-modal", "is_open", allow_duplicate=True),
     Output("progress-input-modal", "is_open", allow_duplicate=True),
     Output("progress-input-modal-header", "children", allow_duplicate=True),
     Output("progress-input-modal-description", "children", allow_duplicate=True),
     Output("progress-input-content", "children", allow_duplicate=True),
     Output("progress-data", "data", allow_duplicate=True)],
    Input("plan-next-btn", "n_clicks"),
    [State({'type': 'plan-check-new', 'index': dash.ALL}, 'value'),
     State({'type': 'plan-check-new', 'index': dash.ALL}, 'id'),
     State("selected-subject-store", "data"),
     State("progress-data", "data"),
     State("current-student-store", "data")],
    prevent_initial_call=True
)
def open_progress_input_modal(next_clicks, plan_values, plan_ids, selected_subject, data, current_user):
    if not next_clicks or not data or not selected_subject:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
    
    df = pd.DataFrame(data)
    
    # 選択された予定をデータに反映
    data_updated = False
    if plan_ids and plan_values:
        for i, plan_id in enumerate(plan_ids):
            if i < len(plan_values) and plan_values[i] is not None:
                try:
                    subject, book_name = plan_id['index'].split('|')
                    mask = (df['科目'] == subject) & (df['参考書名'] == book_name) & (df['生徒'] == current_user)
                    if mask.any():
                        old_value = df.loc[mask, '予定'].iloc[0]
                        new_value = bool(plan_values[i])
                        if old_value != new_value:
                            df.loc[mask, '予定'] = new_value
                            data_updated = True
                            print(f"予定更新: {subject}|{book_name} → {new_value}")
                except (ValueError, KeyError, IndexError):
                    continue
    
    # データが更新された場合はCSVファイルに保存
    if data_updated:
        try:
            csv_path = os.path.join(os.path.dirname(__file__), 'route-subject-text-time.csv')
            column_order = ["ルートレベル", "科目", "参考書名", "所要時間", "予定", "達成済", "達成割合", "生徒"]
            df_save = df[column_order].copy()
            df_save['達成割合'] = df_save['達成割合'].fillna('').astype(str)
            df_save.loc[df_save['達成割合'] == '0.0', '達成割合'] = ''
            df_save.to_csv(csv_path, index=False, encoding='utf-8-sig')
            print(f"予定データを保存しました: {current_user} - {selected_subject}")
        except Exception as e:
            print(f"予定データの保存に失敗: {e}")
    
    # 現在の生徒かつ選択された科目かつ予定が設定された参考書のみを進捗入力対象とする
    planned_books = df[(df['科目'] == selected_subject) & (df['予定'] == True) & (df['生徒'] == current_user)]
    
    if len(planned_books) == 0:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, [
            html.Div([
                html.I(className="fas fa-exclamation-triangle text-warning me-2"),
                f"{selected_subject}の予定に追加された参考書がありません。戻って予定を設定してください。"
            ], className="text-center text-muted p-4")
        ], df.to_dict("records")
    
    # 進捗入力用コンテンツを作成（選択された科目のみ）
    progress_content = []
    for _, row in planned_books.iterrows():
        progress_content.append(
            dbc.Card([
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Div([
                                dbc.Badge(row['ルートレベル'], color="secondary", className="me-2", style={"fontSize": "10px"}),
                                html.Span(row['参考書名'], style={"fontSize": "14px", "fontWeight": "bold"}),
                                html.Span(f" ({selected_subject})", className="text-info small ms-2")
                            ])
                        ], width=6),
                        dbc.Col([
                            dbc.Checkbox(
                                id={'type': 'progress-check-new', 'index': f"{row['科目']}|{row['参考書名']}"},
                                value=row['達成済'],
                                label="達成済み"
                            )
                        ], width=3),
                        dbc.Col([
                            dbc.Input(
                                id={'type': 'progress-percent-new', 'index': f"{row['科目']}|{row['参考書名']}"},
                                type="text",
                                value=row.get('達成割合', ''),
                                placeholder="例: 3/5, 0.6, 60%",
                                size="sm"
                            )
                        ], width=3)
                    ])
                ], className="py-2")
            ], className="mb-2 border-0", style={"backgroundColor": "#f0f8ff"})
        )
    
    header = f"� {selected_subject} - 進捗入力"
    description = f"{selected_subject}の予定に追加した {len(planned_books)} 冊の参考書の進捗を入力してください。"
    
    # 更新されたDataFrameをストアに反映
    updated_data = df.to_dict("records")
    
    return False, True, header, description, progress_content, updated_data

# 3. 進捗保存
@app.callback(
    [Output("progress-input-modal", "is_open", allow_duplicate=True),
     Output("progress-data", "data", allow_duplicate=True),
     Output("graph-update-trigger", "data", allow_duplicate=True)],
    Input("progress-save-btn", "n_clicks"),
    [State({'type': 'progress-check-new', 'index': dash.ALL}, 'value'),
     State({'type': 'progress-check-new', 'index': dash.ALL}, 'id'),
     State({'type': 'progress-percent-new', 'index': dash.ALL}, 'value'),
     State({'type': 'progress-percent-new', 'index': dash.ALL}, 'id'),
     State("progress-data", "data"),
     State("current-student-store", "data")],
    prevent_initial_call=True
)
def save_progress_data(save_clicks, progress_values, progress_ids, percent_values, percent_ids, data, current_user):
    if not save_clicks or not data:
        return dash.no_update, dash.no_update, dash.no_update
    
    df = pd.DataFrame(data)
    
    # 達成済みデータを更新
    if progress_ids and progress_values:
        for i, progress_id in enumerate(progress_ids):
            if i < len(progress_values) and progress_values[i] is not None:
                try:
                    subject, book_name = progress_id['index'].split('|')
                    mask = (df['科目'] == subject) & (df['参考書名'] == book_name) & (df['生徒'] == current_user)
                    if mask.any():
                        df.loc[mask, '達成済'] = bool(progress_values[i])
                except (ValueError, KeyError, IndexError):
                    continue
    
    # 達成割合データを更新
    if percent_ids and percent_values:
        for i, percent_id in enumerate(percent_ids):
            if i < len(percent_values) and percent_values[i] is not None:
                try:
                    subject, book_name = percent_id['index'].split('|')
                    mask = (df['科目'] == subject) & (df['参考書名'] == book_name) & (df['生徒'] == current_user)
                    if mask.any():
                        # 空文字列または0の場合は空文字列として保存
                        value = percent_values[i]
                        if str(value).strip() in ['', '0', '0.0']:
                            value = ''
                        df.loc[mask, '達成割合'] = value
                except (ValueError, KeyError, IndexError):
                    continue
    
    # CSVファイルに保存
    try:
        csv_path = os.path.join(os.path.dirname(__file__), 'route-subject-text-time.csv')
        column_order = ["ルートレベル", "科目", "参考書名", "所要時間", "予定", "達成済", "達成割合", "生徒"]
        df_save = df[column_order].copy()
        # 達成割合のデータ型を文字列に統一（NaN値を空文字列に変換）
        df_save['達成割合'] = df_save['達成割合'].fillna('').astype(str)
        # '0.0'を空文字列に変換
        df_save.loc[df_save['達成割合'] == '0.0', '達成割合'] = ''
        df_save.to_csv(csv_path, index=False, encoding='utf-8-sig')
        print("段階的進捗更新が完了しました！")
        
        # グラフ更新を確実にトリガーするため、データに一意のタイムスタンプを追加
        import time
        updated_data = df.to_dict("records")
        # 各レコードにタイムスタンプを追加してデータ変更を確実に検出させる
        timestamp = time.time()
        for record in updated_data:
            record['_update_timestamp'] = timestamp
            
        print(f"グラフデータを更新中... タイムスタンプ: {timestamp}")
        print(f"更新データ件数: {len(updated_data)}")
        return False, updated_data, timestamp
        
    except Exception as e:
        print(f"進捗保存に失敗しました: {e}")
        return dash.no_update, dash.no_update, dash.no_update

# 戻るボタンのコールバック
@app.callback(
    [Output("plan-modal", "is_open", allow_duplicate=True),
     Output("progress-modal", "is_open", allow_duplicate=True)],
    Input("plan-back-btn", "n_clicks"),
    prevent_initial_call=True
)
def plan_back_to_subject_selection(back_clicks):
    if not back_clicks:
        return dash.no_update, dash.no_update
    return False, True

@app.callback(
    [Output("progress-input-modal", "is_open", allow_duplicate=True),
     Output("plan-modal", "is_open", allow_duplicate=True)],
    Input("progress-back-btn", "n_clicks"),
    prevent_initial_call=True
)
def progress_back_to_plan_input(back_clicks):
    if not back_clicks:
        return dash.no_update, dash.no_update
    return False, True

# 生徒選択モーダル表示/非表示
@app.callback(
    Output("user-selection-modal", "is_open"),
    [Input("open-user-selection-modal", "n_clicks")],
    [State("user-selection-modal", "is_open")],
    prevent_initial_call=True
)
def toggle_user_selection_modal(n_clicks, is_open):
    if n_clicks:
        return not is_open
    return is_open

# 現在の生徒表示
@app.callback(
    Output("current-user-display", "children"),
    Input("current-student-store", "data")
)
def update_current_user_display(current_user):
    # 現在の生徒の予定データ数を確認
    import os
    csv_path = os.path.join(os.path.dirname(__file__), 'route-subject-text-time.csv')
    df = pd.read_csv(csv_path, dtype={'達成割合': 'str'})
    user_planned_count = len(df[(df['生徒'] == current_user) & (df['予定'] == True)])
    
    if user_planned_count == 0:
        return dbc.Alert([
            html.Div([
                html.I(className="fas fa-user me-2"),
                f"現在選択中: {current_user}"
            ], className="mb-2"),
            html.Hr(className="my-2"),
            html.Small([
                html.I(className="fas fa-info-circle me-1"),
                "予定データがありません。左メニューの「進捗更新」から学習予定を設定してください。"
            ], className="text-muted")
        ], color="warning", className="mb-0")
    else:
        return dbc.Alert([
            html.I(className="fas fa-user me-2"),
            f"現在選択中: {current_user}",
            html.Small(f" ({user_planned_count}件の予定)", className="ms-2 text-muted")
        ], color="info", className="mb-0")

# 生徒選択ボタン一覧表示
@app.callback(
    Output("user-selection-buttons", "children"),
    [Input("progress-data", "data"), Input("current-student-store", "data")]
)
def update_user_selection_buttons(data, current_user):
    df = pd.DataFrame(data)
    # タイムスタンプ列がある場合は削除
    if '_update_timestamp' in df.columns:
        df = df.drop('_update_timestamp', axis=1)
    users = df['生徒'].unique()
    
    buttons = []
    for user in sorted(users):
        is_current = user == current_user
        color = "success" if is_current else "outline-primary"
        icon = "fas fa-check" if is_current else "fas fa-user"
        
        button = dbc.Button(
            [
                html.I(className=f"{icon} me-2"),
                user,
                html.Span(" (選択中)", className="ms-2 text-success fw-bold") if is_current else ""
            ],
            id={'type': 'user-select-btn', 'index': user},
            color=color,
            className="w-100 mb-2",
            size="lg",
            disabled=is_current
        )
        buttons.append(button)
    
    return buttons

# 生徒選択モーダルの制御
@app.callback(
    Output("student-selection-modal", "is_open"),
    Input("open-student-selection-modal", "n_clicks"),
    State("student-selection-modal", "is_open"),
    prevent_initial_call=True
)
def toggle_student_selection_modal(n_clicks, is_open):
    if n_clicks:
        return not is_open
    return is_open

# 生徒管理モーダルの制御
@app.callback(
    Output("student-management-modal", "is_open"),
    Input("open-student-management-modal", "n_clicks"),
    State("student-management-modal", "is_open"),
    prevent_initial_call=True
)
def toggle_student_management_modal(n_clicks, is_open):
    if n_clicks:
        return not is_open
    return is_open

# 生徒選択ボタンの生成
@app.callback(
    Output("student-selection-buttons", "children"),
    [Input("progress-data", "data"), Input("current-student-store", "data")]
)
def update_student_selection_buttons(data, current_student):
    if not data:
        return []
    
    df = pd.DataFrame(data)
    students = sorted(df['生徒'].unique())
    buttons = []
    
    for student in students:
        is_current = (student == current_student)
        color = "success" if is_current else "outline-primary"
        
        button = dbc.Button([
                student,
                html.Span(" (選択中)", className="ms-2 text-success fw-bold") if is_current else ""
            ],
            id={'type': 'student-select-btn', 'index': student},
            color=color,
            className="w-100 mb-2",
            size="lg",
            disabled=is_current
        )
        buttons.append(button)
    
    return buttons

# 生徒管理リストの生成
@app.callback(
    Output("student-management-list", "children"),
    Input("progress-data", "data"),
    prevent_initial_call=True
)
def update_student_management_list(data):
    if not data:
        return []
    
    df = pd.DataFrame(data)
    students = sorted(df['生徒'].unique())
    cards = []
    
    for student in students:
        student_data = df[df['生徒'] == student]
        total_subjects = len(student_data['科目'].unique())
        planned_count = len(student_data[student_data['予定'] == True])
        completed_count = len(student_data[student_data['達成済'] == True])
        
        card = dbc.Card([
            dbc.CardBody([
                html.H5(student, className="card-title text-primary"),
                html.P([
                    html.I(className="fas fa-book me-2"),
                    f"科目数: {total_subjects}",
                    html.Br(),
                    html.I(className="fas fa-calendar-check me-2"),
                    f"予定設定: {planned_count}件",
                    html.Br(),
                    html.I(className="fas fa-check-circle me-2"),
                    f"完了: {completed_count}件"
                ], className="card-text"),
                dbc.ButtonGroup([
                    dbc.Button([
                        html.I(className="fas fa-edit me-1"),
                        "編集"
                    ], 
                    id={'type': 'edit-student-btn', 'index': student},
                    color="info", size="sm"),
                    dbc.Button([
                        html.I(className="fas fa-trash me-1"),
                        "削除"
                    ], 
                    id={'type': 'delete-student-btn', 'index': student},
                    color="danger", size="sm")
                ], className="w-100")
            ])
        ], className="mb-3")
        
        cards.append(card)
    
    return cards

# 生徒選択処理
@app.callback(
    [Output("current-student-store", "data"),
     Output("progress-data", "data", allow_duplicate=True),
     Output("graph-update-trigger", "data", allow_duplicate=True),
     Output("student-selection-message", "children")],
    [Input({'type': 'student-select-btn', 'index': dash.ALL}, 'n_clicks')],
    [State("progress-data", "data"), State("current-student-store", "data")],
    prevent_initial_call=True
)
def select_student(n_clicks_list, data, current_student):
    ctx = dash.callback_context
    if not ctx.triggered or not any(n_clicks_list):
        return current_student, data, dash.no_update, ""
    
    # クリックされた生徒を特定
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
    selected_student = json.loads(triggered_id)['index']
    
    # グラフ強制更新のためにタイムスタンプを生成
    import time
    update_trigger = time.time()
    
    print(f"生徒切り替え: {current_student} → {selected_student}")
    print(f"グラフ更新トリガー: {update_trigger}")
    
    message = dbc.Alert([
        html.I(className="fas fa-check-circle me-2"),
        f"生徒 '{selected_student}' を選択しました！"
    ], color="success", dismissable=True)
    
    return selected_student, data, update_trigger, message

# 新規生徒追加処理
@app.callback(
    [Output("progress-data", "data", allow_duplicate=True),
     Output("new-student-name-input", "value"),
     Output("student-management-message", "children", allow_duplicate=True)],
    Input("add-new-student-btn", "n_clicks"),
    [State("new-student-name-input", "value"), State("progress-data", "data")],
    prevent_initial_call=True
)
def add_new_student(n_clicks, new_student_name, data):
    if not n_clicks or not new_student_name or not new_student_name.strip():
        return data, dash.no_update, ""
    
    df = pd.DataFrame(data)
    new_student_name = new_student_name.strip()
    
    # 既存生徒チェック
    if new_student_name in df['生徒'].values:
        message = dbc.Alert([
            html.I(className="fas fa-exclamation-triangle me-2"),
            f"生徒 '{new_student_name}' は既に存在します。"
        ], color="warning", dismissable=True)
        return data, "", message
    
    # デフォルト生徒のデータをコピーして新規生徒を作成
    default_data = df[df['生徒'] == 'デフォルト生徒'].copy()
    if default_data.empty:
        # デフォルト生徒がない場合は最初の生徒のデータをコピー
        default_data = df[df['生徒'] == df['生徒'].iloc[0]].copy()
    
    # 新規生徒のデータを作成（進捗はリセット）
    new_student_data = default_data.copy()
    new_student_data['生徒'] = new_student_name
    new_student_data['予定'] = False
    new_student_data['達成済'] = False
    new_student_data['達成割合'] = ''
    
    # データフレームに追加
    df = pd.concat([df, new_student_data], ignore_index=True)
    
    # CSVに保存
    try:
        csv_path = os.path.join(os.path.dirname(__file__), 'route-subject-text-time.csv')
        column_order = ["ルートレベル", "科目", "参考書名", "所要時間", "予定", "達成済", "達成割合", "生徒"]
        df_save = df[column_order].copy()
        df_save.to_csv(csv_path, index=False, encoding='utf-8-sig')
        print(f"新規生徒データを保存: {new_student_name}")
    except Exception as e:
        print(f"新規生徒データのCSV保存に失敗: {e}")
    
    message = dbc.Alert([
        html.I(className="fas fa-check-circle me-2"),
        f"新規生徒 '{new_student_name}' を追加しました！"
    ], color="success", dismissable=True)
    
    return df.to_dict("records"), "", message

# 生徒削除処理
@app.callback(
    [Output("progress-data", "data", allow_duplicate=True),
     Output("current-student-store", "data", allow_duplicate=True),
     Output("student-management-message", "children", allow_duplicate=True)],
    [Input({'type': 'delete-student-btn', 'index': dash.ALL}, 'n_clicks')],
    [State("progress-data", "data"), State("current-student-store", "data")],
    prevent_initial_call=True
)
def delete_student(n_clicks_list, data, current_student):
    ctx = dash.callback_context
    if not ctx.triggered or not any(n_clicks_list):
        return data, current_student, ""
    
    # 削除対象の生徒を特定
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
    student_to_delete = json.loads(triggered_id)['index']
    
    df = pd.DataFrame(data)
    students = df['生徒'].unique()
    
    # 最後の生徒は削除できない
    if len(students) <= 1:
        message = dbc.Alert([
            html.I(className="fas fa-exclamation-triangle me-2"),
            "最後の生徒は削除できません。"
        ], color="warning", dismissable=True)
        return data, current_student, message
    
    # 生徒データを削除
    df_filtered = df[df['生徒'] != student_to_delete]
    
    # 現在選択中の生徒が削除された場合、別の生徒を選択
    new_current_student = current_student
    if current_student == student_to_delete:
        remaining_students = df_filtered['生徒'].unique()
        new_current_student = remaining_students[0] if len(remaining_students) > 0 else 'デフォルト生徒'
    
    # CSVに保存
    try:
        csv_path = os.path.join(os.path.dirname(__file__), 'route-subject-text-time.csv')
        column_order = ["ルートレベル", "科目", "参考書名", "所要時間", "予定", "達成済", "達成割合", "生徒"]
        df_save = df_filtered[column_order].copy()
        df_save.to_csv(csv_path, index=False, encoding='utf-8-sig')
        print(f"生徒データを削除: {student_to_delete}")
    except Exception as e:
        print(f"生徒削除のCSV保存に失敗: {e}")
    
    message = dbc.Alert([
        html.I(className="fas fa-check-circle me-2"),
        f"生徒 '{student_to_delete}' を削除しました。"
    ], color="success", dismissable=True)
    
    return df_filtered.to_dict("records"), new_current_student, message

# 生徒編集モードの制御
@app.callback(
    [Output("student-edit-controls", "style"),
     Output("edit-student-name-input", "value"),
     Output("editing-student-original-name", "data")],
    [Input({'type': 'edit-student-btn', 'index': dash.ALL}, 'n_clicks'),
     Input("cancel-student-edit-btn", "n_clicks")],
    prevent_initial_call=True
)
def toggle_student_edit_mode(edit_clicks_list, cancel_clicks):
    ctx = dash.callback_context
    if not ctx.triggered:
        return {"display": "none"}, "", ""
    
    triggered_id = ctx.triggered[0]['prop_id']
    
    # キャンセルボタンがクリックされた場合
    if "cancel-student-edit-btn" in triggered_id:
        return {"display": "none"}, "", ""
    
    # 編集ボタンがクリックされた場合
    if edit_clicks_list and any(edit_clicks_list):
        triggered_id_dict = json.loads(triggered_id.split('.')[0])
        student_name = triggered_id_dict['index']
        return {"display": "block"}, student_name, student_name
    
    return {"display": "none"}, "", ""

# 生徒名編集の保存処理
@app.callback(
    [Output("progress-data", "data", allow_duplicate=True),
     Output("current-student-store", "data", allow_duplicate=True),
     Output("student-management-message", "children", allow_duplicate=True),
     Output("student-edit-controls", "style", allow_duplicate=True)],
    Input("save-student-edit-btn", "n_clicks"),
    [State("edit-student-name-input", "value"),
     State("editing-student-original-name", "data"),
     State("progress-data", "data"),
     State("current-student-store", "data")],
    prevent_initial_call=True
)
def save_student_edit(n_clicks, new_name, original_name, data, current_student):
    if not n_clicks or not new_name or not new_name.strip() or not original_name:
        return data, current_student, "", {"display": "none"}
    
    df = pd.DataFrame(data)
    new_name = new_name.strip()
    
    # 新しい名前が既存の他の生徒と重複していないかチェック
    if new_name != original_name and new_name in df['生徒'].values:
        message = dbc.Alert([
            html.I(className="fas fa-exclamation-triangle me-2"),
            f"生徒名 '{new_name}' は既に存在します。"
        ], color="warning", dismissable=True)
        return data, current_student, message, {"display": "block"}
    
    # 生徒名を更新
    df.loc[df['生徒'] == original_name, '生徒'] = new_name
    
    # 現在選択中の生徒も更新
    updated_current_student = new_name if current_student == original_name else current_student
    
    # CSVに保存
    try:
        csv_path = os.path.join(os.path.dirname(__file__), 'route-subject-text-time.csv')
        column_order = ["ルートレベル", "科目", "参考書名", "所要時間", "予定", "達成済", "達成割合", "生徒"]
        df_save = df[column_order].copy()
        df_save.to_csv(csv_path, index=False, encoding='utf-8-sig')
        print(f"生徒名を更新: {original_name} → {new_name}")
    except Exception as e:
        print(f"生徒編集のCSV保存に失敗: {e}")
        message = dbc.Alert([
            html.I(className="fas fa-exclamation-circle me-2"),
            "保存に失敗しました。"
        ], color="danger", dismissable=True)
        return data, current_student, message, {"display": "block"}
    
    message = dbc.Alert([
        html.I(className="fas fa-check-circle me-2"),
        f"生徒名を '{original_name}' から '{new_name}' に変更しました。"
    ], color="success", dismissable=True)
    
    return df.to_dict("records"), updated_current_student, message, {"display": "none"}

if __name__ == "__main__":
    print("📊 学習進捗ダッシュボード起動中...")
    print("🌐 http://127.0.0.1:8050/")
    import json
    import webbrowser
    import threading
    import time
    
    # ブラウザを自動で開く
    def open_browser():
        time.sleep(1.5)
        webbrowser.open('http://127.0.0.1:8050/')
    
    threading.Thread(target=open_browser).start()
    app.run(debug=False, host='127.0.0.1', port=8050)
