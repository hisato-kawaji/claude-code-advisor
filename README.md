# Claude Code Analytics Dashboard

Claude Codeの使用状況を分析し、使い方を改善するためのダッシュボードです。

## 機能

- 使用状況の可視化（日別・週別・月別）
- 前日比・先週比・先月比の比較
- LLMによるタスク実行の分析とフィードバック
- プロンプト改善のレクチャー
- Anthropicのベストプラクティスに基づくチェック

## 技術スタック

- Backend: Python (FastAPI)
- Frontend: React + TypeScript + Vite
- Database: SQLite
- LLM: OpenAI API (GPT-4o-mini)
- Container: Docker + Docker Compose

## セットアップ

### 1. 環境変数の設定

`.env`ファイルを作成してください：

```bash
cp .env.example .env
```

`.env`ファイルを編集してOpenAIのAPIキーを設定：

```
OPENAI_API_KEY=sk-proj-your_actual_api_key_here
OPENAI_MODEL=gpt-4o-mini
CLAUDE_DATA_PATH=/Users/your_username/.claude
DATABASE_PATH=./data/analytics.db
```

### 2. セットアップスクリプトの実行

```bash
./setup.sh
```

### 3. アプリケーションの起動

```bash
docker-compose up -d
```

### 4. アクセス

- ダッシュボード: http://localhost:3332
- API ドキュメント: http://localhost:8000/docs

### 5. 停止

```bash
docker-compose down
```

## 開発モード

### バックエンド

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# .envファイルを設定
cp ../.env.example .env
# .envを編集

# 起動
uvicorn app.main:app --reload
```

### フロントエンド

```bash
cd frontend
npm install

# .envファイルを設定
cp .env.example .env

# 起動
npm run dev
```

## アーキテクチャ

### データソース
- `~/.claude/history.jsonl` - 全体の履歴
- `~/.claude/projects/[project]/[session].jsonl` - セッション詳細（usage情報含む）

### API エンドポイント

#### 統計API
- `GET /api/stats/daily?date=YYYY-MM-DD` - 日次統計と前日比
- `GET /api/stats/weekly?date=YYYY-MM-DD` - 週次統計と先週比
- `GET /api/stats/monthly?date=YYYY-MM-DD` - 月次統計と先月比
- `GET /api/stats/range?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD` - 期間指定統計

#### 分析API
- `GET /api/analysis/performance?days=7` - パフォーマンス分析
  - 総合スコア
  - タスク完了率
  - 平均ターン数
  - エラー率
  - フィードバックと改善点

- `GET /api/analysis/best-practices?days=7` - ベストプラクティスチェック
  - スコア
  - 遵守している項目
  - 改善が必要な項目
  - 推奨事項

- `POST /api/analysis/improve-prompt?prompt=<text>` - プロンプト改善提案
  - 改善されたプロンプト
  - 改善理由
  - ベストプラクティス参照

- `GET /api/analysis/recent-prompts?limit=10` - 最近のプロンプト一覧

## 機能詳細

### 1. 使用状況ダッシュボード

- セッション数、メッセージ数、トークン使用量を可視化
- 日次・週次・月次の切り替え
- 前期間との比較（変化率表示）
- チャートによる視覚的な表示

### 2. パフォーマンス分析

OpenAI APIを使用して以下を分析：
- 総合的な使い方のスコアリング
- タスクの完了率推定
- エラー処理の効率性
- 強みと改善点の特定
- 具体的なフィードバック

### 3. ベストプラクティスチェック

Anthropicの公式ベストプラクティスに基づいて：
- CLAUDE.mdの活用状況
- ワークフローの適切性
- コンテキストの管理
- ツールの効果的な使用
- 安全性の考慮

### 4. プロンプト改善ツール

- 最近使用したプロンプトを選択
- LLMが改善案を提案
- 改善理由の説明
- ベストプラクティスとの関連性を示す

## トラブルシューティング

### データが表示されない

- Claude Codeの使用履歴が`~/.claude`にあることを確認
- `CLAUDE_DATA_PATH`が正しく設定されているか確認
- Dockerコンテナがホームディレクトリをマウントできているか確認

### APIエラー

- `OPENAI_API_KEY`が正しく設定されているか確認
- APIキーが有効で残高があるか確認
- バックエンドのログを確認: `docker-compose logs backend`

### フロントエンドが表示されない

- ブラウザのコンソールでエラーを確認
- フロントエンドのログを確認: `docker-compose logs frontend`
- CORSエラーの場合、バックエンドの設定を確認

## ライセンス

MIT
