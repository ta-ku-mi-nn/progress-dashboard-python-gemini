"""
アプリケーションのスタイル設定とCSS定義
"""

# HTML テンプレート文字列
APP_INDEX_STRING = '''
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

        /* ローディング画面のアニメーション */
        ._dash-loading {
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            z-index: 9999;
            display: flex;
            flex-direction: column; /* アイコンとテキストを縦に並べる */
            justify-content: center;
            align-items: center;
            width: 100vw;
            height: 100vh;
            background-color: rgba(255, 255, 255, 0.8);
        }

        /* テキストメッセージ */
        ._dash-loading::before {
            content: '画面が変わらなかったらページをリロード(F5)するかキャッシュをクリア(Ctrl+Shift+R)してください';
            font-family: 'Segoe UI', 'Yu Gothic UI', 'Meiryo UI', sans-serif;
            font-size: 1rem;
            color: #555;
            font-weight: 500;
            margin-top: 20px; /* アイコンとの間に余白を追加 */
        }

        /* スピナー（回転する円） */
        ._dash-loading::after {
            content: '';
            display: inline-block;
            width: 50px;
            height: 50px;
            border: 5px solid #0d6efd; /* Bootstrapのプライマリカラー */
            border-radius: 50%;
            border-top-color: transparent;
            animation: spin 1s linear infinite;
        }

        @keyframes spin {
            to {
                transform: rotate(360deg);
            }
        }


        /* タブの文字色を黒に設定 */
        .nav-tabs .nav-link {
            color: #333 !important;
        }

        .nav-tabs .nav-link.active {
            color: #000 !important;
            font-weight: 600 !important;
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

        /* シンプルなカスタムスタイル */
        .card {
            border-radius: 8px !important;
            transition: all 0.2s ease-in-out;
        }

        .card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 20px rgba(0,0,0,0.1) !important;
        }

        .btn {
            border-radius: 6px !important;
            font-weight: 500;
            transition: all 0.2s ease-in-out;
        }

        .navbar {
            border-radius: 0 !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }

        .navbar-brand {
            font-size: 1.4rem !important;
            font-weight: 700 !important;
        }

        .card-header {
            background-color: #f8f9fa !important;
            border-bottom: 1px solid #e9ecef !important;
            font-weight: 600;
        }

        .badge {
            font-weight: 500;
        }

        /* レスポンシブ調整 */
        @media (max-width: 768px) {
            .container-fluid {
                padding: 0.5rem !important;
            }
        }

        .modal-body .Select-menu-outer {
            z-index: 1060 !important;
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

# 外部スタイルシート
EXTERNAL_STYLESHEETS = [
    'https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css',
    "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css"
]