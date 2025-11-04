# プロジェクト構造

```
claude-code-analytics/
├── backend/                    # Pythonバックエンド
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py            # FastAPIアプリケーション
│   │   ├── config.py          # 設定管理
│   │   ├── api/               # APIエンドポイント
│   │   │   ├── __init__.py
│   │   │   ├── stats.py       # 統計API
│   │   │   └── analysis.py    # 分析API
│   │   ├── models/            # データモデル
│   │   │   ├── __init__.py
│   │   │   └── schemas.py     # Pydanticスキーマ
│   │   └── services/          # ビジネスロジック
│   │       ├── __init__.py
│   │       ├── data_collector.py  # Claude Codeデータ収集
│   │       └── analyzer.py        # LLM分析サービス
│   ├── requirements.txt       # Python依存関係
│   └── Dockerfile            # バックエンドDocker設定
│
├── frontend/                  # React + TypeScriptフロントエンド
│   ├── src/
│   │   ├── App.tsx           # メインダッシュボード
│   │   ├── App.css           # スタイル
│   │   ├── main.tsx          # エントリーポイント
│   │   ├── types.ts          # TypeScript型定義
│   │   └── api.ts            # APIクライアント
│   ├── package.json          # npm依存関係
│   ├── nginx.conf            # Nginx設定
│   └── Dockerfile            # フロントエンドDocker設定
│
├── docker-compose.yml        # Docker Compose設定
├── setup.sh                  # セットアップスクリプト
├── .env.example              # 環境変数テンプレート
├── .gitignore               # Git無視設定
└── README.md                # プロジェクトドキュメント
```

## ファイル説明

### Backend

- **main.py**: FastAPIアプリケーションのエントリーポイント。CORS設定とルーター登録
- **config.py**: 環境変数の管理とSettings定義
- **api/stats.py**: 統計データAPIエンドポイント（日次・週次・月次）
- **api/analysis.py**: LLM分析APIエンドポイント（パフォーマンス、ベストプラクティス、プロンプト改善）
- **models/schemas.py**: Pydanticモデル定義
- **services/data_collector.py**: ~/.claudeからデータを読み込む
- **services/analyzer.py**: Claude APIを使用した分析ロジック

### Frontend

- **App.tsx**: メインダッシュボードコンポーネント
- **api.ts**: バックエンドAPIとの通信
- **types.ts**: TypeScript型定義
- **App.css**: ダッシュボードのスタイル

## データフロー

1. **データ収集**: `data_collector.py`が`~/.claude`からセッションデータを読み込む
2. **統計処理**: 収集したデータを日次・週次・月次で集計
3. **LLM分析**: Claude APIを使用してパフォーマンス分析とベストプラクティスチェック
4. **表示**: Reactダッシュボードでデータを可視化

## 技術スタック

### Backend
- FastAPI: 高速なPython Webフレームワーク
- Anthropic Python SDK: Claude API連携
- Pydantic: データバリデーション
- Uvicorn: ASGIサーバー

### Frontend
- React 18: UIライブラリ
- TypeScript: 型安全性
- Vite: 高速ビルドツール
- TanStack Query: データフェッチング
- Recharts: チャート描画

### Infrastructure
- Docker: コンテナ化
- Docker Compose: マルチコンテナ管理
- Nginx: フロントエンド配信とリバースプロキシ
