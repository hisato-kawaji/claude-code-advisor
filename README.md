# Claude Code Analytics Dashboard

Claude Codeの使用状況を分析し、使い方を改善するためのダッシュボードです。

## デモ

![Demo](demo.gif)

## 機能

### 📊 ダッシュボード
- 使用状況の可視化（日別・週別・月別）
- 前日比・先週比・先月比の比較
- LLMによるタスク実行の分析とフィードバック
- プロンプト改善のレクチャー
- Anthropicのベストプラクティスに基づくチェック

### 🔍 トークン消費振り返り
- **詳細な統計分析**: 総トークン数、推定コスト、効率スコアの可視化
- **AI分析レポート**: 使用パターンの分析とトークン消費が多かった活動の特定
- **コスト最適化提案**: Claude Code公式ベストプラクティスに基づく改善提案
- **実践的な改善例**: 実際のプロンプトを使った具体的な改善デモ
- **期間選択**: 過去7日間、14日間、30日間の分析
- **チャート表示**: Input/Outputトークンの構成比を円グラフで表示

### 🔍 プロンプト別トークン分析
- **1対1のトークン帰属**: 各プロンプトに、次のプロンプトまでのアシスタント消費（ツール実行・サブエージェント・バックグラウンド作業含む）を帰属
- **網羅テーブル**: 全プロンプトをソート・ページング・行展開付きで表示（トークン内訳／コスト／ツール実行回数／所要時間）
- **消費上位チャートと分布ヒストグラム**: どのプロンプトが重いかが一目で分かる
- **帰属率の表示**: 帰属できた消費の割合を表示し、データの正確性を検証可能
- **AI分析**: 高消費プロンプトのパターン特定・改善提案・実プロンプトの書き換え例
  - アドバイスは公式ドキュメント比重で整理した最新ベストプラクティス（[観点整理](docs/claude-prompting-best-practices.md)）に基づき、観点ラベル付きで提示

### 🕒 時間別モニタリング
- 日付を選択し、1日のトークン消費量を1時間ごとに可視化
- Input/Outputトークンの内訳を棒グラフで表示
- 時間ごとの消費量と累積消費量を表形式で確認

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

- **ダッシュボード**: http://localhost:5173
  - メインダッシュボード: http://localhost:5173/
  - トークン消費振り返り: http://localhost:5173/token-reflection
  - 時間別モニタリング: http://localhost:5173/monitoring
  - プロンプト分析: http://localhost:5173/prompt-analysis
- **API ドキュメント**: http://localhost:8000/docs

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
- `GET /api/stats/hourly?date=YYYY-MM-DD` - 指定日の1時間ごとの統計（JST対応）
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

- `GET /api/analysis/prompt-tokens?days=7&sort=total_tokens&order=desc&limit=50&offset=0&include_commands=true` - プロンプト別トークン帰属データ（LLM不使用・高速）
  - 各プロンプトへの1対1トークン帰属（Input/Output/Cache別、コスト、ツール実行回数、所要時間）
  - サマリー統計（平均・中央値・p90・最大、分布ヒストグラム、上位消費プロンプト）
  - 帰属率（attribution_coverage_pct）による正確性の検証

- `GET /api/analysis/prompt-tokens/insights?days=7&top=15` - プロンプト消費パターンのAI分析
  - 高消費プロンプトのパターン特定
  - 効率に関する観察と改善提案
  - 実際のプロンプトの書き換え例

- `GET /api/analysis/token-reflection?days=7` - トークン消費振り返り
  - トークン消費統計（Input/Output/Cache）
  - 推定コスト（USD）
  - 効率スコア（0-100）
  - 使用パターン分析
  - トークン消費が多かった活動
  - コスト最適化提案
  - 次のアクションステップ
  - 実際のプロンプト改善例（元のプロンプト vs 改善後のプロンプト）
  - AI による総合振り返り

## 機能詳細

### 1. 使用状況ダッシュボード

- セッション数、メッセージ数、トークン使用量を可視化
- 日次・週次・月次の切り替え
- 前期間との比較（変化率表示）
- チャートによる視覚的な表示
- サイドバーナビゲーションで簡単に画面切り替え

### 2. パフォーマンス分析

OpenAI APIを使用して以下を分析：
- 総合的な使い方のスコアリング
- タスクの完了率推定
- エラー処理の効率性
- 強みと改善点の特定
- 具体的なフィードバック

### 3. ベストプラクティスチェック

[Claude Code公式ベストプラクティス](https://www.anthropic.com/engineering/claude-code-best-practices)に基づいて：
- CLAUDE.mdの活用状況
- "Explore, Plan, Code, Commit" ワークフローの適切性
- コンテキストの管理（/clearの使用）
- ファイル参照の明示性
- ツールの効果的な使用
- 画像・URLの活用
- チェックリストの利用
- 安全性の考慮

### 4. プロンプト改善ツール

- 最近使用したプロンプトを選択
- LLMが[公式ベストプラクティス](https://www.anthropic.com/engineering/claude-code-best-practices)に基づいて改善案を提案
- 改善理由の詳細な説明
- 適用されるベストプラクティスの明示
- より具体的で効果的なプロンプトへの変換例

### 5. トークン消費振り返り 🆕

**統計情報**
- 総トークン数（Input/Output/Cache Creation/Cache Read別）
- 推定コスト（Claude Sonnet 3.5の料金体系に基づく）
- 1日あたり平均トークン数
- セッションあたり平均トークン数
- Input/Output比率
- 効率スコア（0-100）

**AI分析**
- 使用パターンの分析（頻繁な短時間利用 vs 集中的な長時間利用など）
- トークン消費が多かった活動の特定（英語＋日本語で表示）
- コスト最適化の提案（公式ベストプラクティスに基づく、英語＋日本語で表示）
- 次のアクションステップ（具体的な改善項目、英語＋日本語で表示）

**プロンプト改善例**
- 実際に使用したプロンプトから1つを抽出
- 元のプロンプト vs 改善後のプロンプトを横並び比較表示
- 改善のポイントを英語と日本語で解説
- [Claude Code公式ベストプラクティス](https://www.anthropic.com/engineering/claude-code-best-practices)に基づいた具体的な改善手法

**総合振り返り**
- AIによる包括的な振り返りコメント
- 期間内の使い方の傾向分析
- 今後の改善方向性の提示

### 6. 時間別モニタリング 🆕

特定の日付における1時間ごとのトークン消費量を詳細に分析できます。これにより、どの時間帯に最もClaude Codeを利用しているかを把握し、作業パターンの見直しに役立てることができます。

**主な機能**
- **日付選択**: カレンダーから分析したい日付を自由に選択できます（当日を除く）。
- **時間別グラフ**: 選択した日の24時間について、1時間ごとのInput/Outputトークン消費量を棒グラフで表示します。
- **詳細データ表**: グラフの下に、各時間帯の具体的なトークン消費量と、その時間までの累積消費量を数値で表示します。

*(注: 対応するスクリーンショットは後ほど `screenshots/09-monitoring.png` として追加してください)*

## トラブルシューティング

### データが表示されない

- Claude Codeの使用履歴が`~/.claude`にあることを確認
- `CLAUDE_DATA_PATH`が正しく設定されているか確認
- Dockerコンテナがホームディレクトリをマウントできているか確認
- Docker volumeの確認: `docker exec claude-analytics-backend ls -la /claude-data`

### トークン消費振り返りで「データが見つかりません」と表示される

これは正常な動作です。以下のいずれかの理由で表示されます：
- 選択した期間内にClaude Codeの使用履歴がない
- セッションデータにタイムスタンプ情報がない

**解決方法**:
1. より長い期間（過去30日間など）を選択してみる
2. Claude Codeを実際に使用してデータを生成する
3. 期間ボタンをクリックして再分析を実行する（キャッシュされたデータではなく最新データを取得）

### APIエラー

- `OPENAI_API_KEY`が正しく設定されているか確認
- APIキーが有効で残高があるか確認
- バックエンドのログを確認: `docker-compose logs backend`
- OpenAI APIの利用制限に達していないか確認

### フロントエンドが表示されない

- ブラウザのコンソールでエラーを確認
- フロントエンドのログを確認: `docker-compose logs frontend`
- CORSエラーの場合、バックエンドの設定を確認
- ブラウザのキャッシュをクリア（Ctrl+Shift+R / Cmd+Shift+R）

### 分析結果が更新されない

- ブラウザのキャッシュが原因の可能性があります
- **期間ボタンをクリック**して再分析を実行してください
- ハードリフレッシュ: Windows/Linux: `Ctrl + Shift + R`、Mac: `Cmd + Shift + R`
- コンテナを再起動: `docker-compose restart`

## 使い方のヒント

### トークン消費振り返りを最大限活用する

1. **定期的にチェック**: 週1回程度、過去7日間の振り返りを確認して使い方を見直す
2. **期間を変えて分析**: 7日間、14日間、30日間と変えて長期的なトレンドを把握
3. **改善提案を実践**: AIが提案するベストプラクティスを1つずつ実践してみる
4. **プロンプト改善例を参考に**: 実際の改善例を見て、自分のプロンプトの書き方を改善
5. **コストを意識**: 推定コストを確認して、必要に応じて使い方を調整

### ベストプラクティスの実践

このダッシュボードで提案される改善は、[Claude Code公式ベストプラクティス](https://www.anthropic.com/engineering/claude-code-best-practices)に基づいています。詳しくは公式ドキュメントを参照してください。

主要なポイント：
- 📝 **CLAUDE.md**を活用してプロジェクト固有の情報を文書化
- 🔍 **Explore → Plan → Code → Commit**のワークフローを意識
- 📸 **画像やスクリーンショット**を活用して視覚的に指示
- 🎯 **具体的で詳細な指示**を与える
- 🧹 **`/clear`コマンド**でコンテキストを管理
- ✅ **チェックリスト**で大きなタスクを分割

## 今後の拡張予定

- [ ] より詳細なコスト分析（プロジェクト別、タスク別）
- [ ] カスタムダッシュボード機能
- [ ] アラート機能（コスト超過、効率低下など）
- [ ] CLAUDE.md自動生成支援

## 貢献

Issue や Pull Request を歓迎します！

## ライセンス

MIT
