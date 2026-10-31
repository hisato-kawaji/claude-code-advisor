# Claude Code Analytics Dashboard

Claude Code のローカル履歴を集計し、利用状況とプロンプト別のトークン使用を振り返るダッシュボードです。FastAPI、SQLite、React、TypeScript、Vite を使用します。

## 機能と制限

- 日・週・月ごとのセッション、メッセージ、Input/Output の集計と時間別表示。
- 取得済みのプロンプトに対し、次のプロンプトまでの消費を時系列で推定帰属。合計は Input、Output、Cache Creation、Cache Read の合算です。履歴の取り込み範囲外、並列作業、子エージェントなどは正確に帰属できない場合があります。帰属率は取得できたデータ内の割合で、取り込みの網羅性や帰属の正確性を示すものではありません。
- 契約・モデル別に設定された単価で参考額を表示します。不明な条件がある場合は「不明」です。
- OpenAI を用いたプロンプトの書き換え・振り返りは任意です。送信する履歴や集計を確認してから実行します。AIの意見は事実を保証しません。
- 根拠のない完了率・エラー率・スコアを返していた `/api/analysis/performance` と `/api/analysis/token-reflection` は停止しています（HTTP 410）。

改善方針は [見直し提案](docs/claude-code-modernization-proposal.md)、助言の基準は [観点整理](docs/claude-prompting-best-practices.md) を参照してください。

## Docker で起動

```bash
cp .env.example .env
# .env に OpenAI API キーなどを設定
./setup.sh
docker compose up -d
```

画面は http://localhost:3332 、API ドキュメントは http://localhost:8000/docs です。停止は `docker compose down`。Claude の履歴はコンテナに読み取り専用でマウントし、SQLite は `data/` に保存します。初回起動時に空のDBを同期し、以後は画面の同期操作で更新します。

## ローカル開発

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env
uvicorn app.main:app --reload
```

別のターミナルで:

```bash
cd frontend
npm install
npm run dev
```

Vite の開発画面は通常 http://localhost:5173 です。設定項目は `.env.example` を参照してください。履歴やプロンプトには機密情報が含まれる場合があります。外部AI分析のプレビューを確認し、送信対象を判断してください。

## 変更された分析API

`POST /api/analysis/improve-prompt` は JSON body `{"prompt": "...", "consent": true}` を受け付けます。ベストプラクティスとトークン分析は、それぞれ `/api/analysis/best-practices/preview` と `/api/analysis/prompt-tokens/insights/preview` で対象を取得し、内容の確認後に対応する `POST` に `consent: true` と対象を送ります。以前のクエリ文字列にプロンプトを載せるAPIは使えません。

## 費用・履歴・外部送信の設定

画面の「設定とテレメトリー」で契約種別、プロバイダー、モデルID、適用期間、トークン区分ごとの単価を設定できます。設定したAPI単価で計算した**帰属分の参考額**であり、請求額ではありません。モデルID・期間・契約・キャッシュ書き込みTTLが不明、または単価期間が重複する場合は不明になります。定額プランでは任意で月額を記録でき、作業単位に配賦しません。追加課金は含みません。複数プロバイダーを使う場合は、集計対象のプロバイダーを選んでください。リージョン、割引、バッチ、長文料金などは自動判別しません。実際の請求は提供元で確認してください。[公式料金](https://platform.claude.com/docs/en/about-claude/pricing)

同期は `projects/*/*.jsonl` に加え `projects/*/<session>/subagents/*.jsonl` を含む配下のJSONLを読みます。UUIDで再取り込みを抑止し、同じrequest IDを持つ複数ブロックの使用量は最後の記録を一度だけ集計します。IDがない場合の重複や、期間外・未取得の履歴は正確に判断できません。子エージェントの使用量は親への関連が確実でないため未帰属に含めます。同期結果には不正行・読込失敗を表示します。既存DBは同期時に互換更新します。大切なDBは更新前にバックアップしてください。

外部AIへの送信前に、画面の設定で除外プロジェクト（名前またはパスのglob）と追加マスク文字列を登録できます。メールアドレスと代表的なキー・パスワード等もマスクします。履歴分析では除外対象とプロジェクトを特定できない履歴を送信対象から外します。手入力したプロンプトのプロジェクトは自動判定できません。マスクは完全ではないため、送信前のプレビューを確認してください。設定と元履歴はローカルDBに保存されます。

## OpenTelemetry（任意）

ローカルの `.env` にランダムな `OTEL_RECEIVER_TOKEN` を設定してバックエンドを再起動します。Claude Code を起動するシェルで以下を設定します（トークンは `.env` と同じ値）。受信側は **OTLP HTTP/JSON のログのみ**に対応し、メトリクス・トレースやprotobuf/gRPCは受け付けません。プロンプト本文やツール内容は保存せず、許可したイベントのメタデータだけを保持します。

```bash
export CLAUDE_CODE_ENABLE_TELEMETRY=1
export OTEL_LOGS_EXPORTER=otlp
export OTEL_METRICS_EXPORTER=none
export OTEL_EXPORTER_OTLP_LOGS_PROTOCOL=http/json
export OTEL_EXPORTER_OTLP_LOGS_ENDPOINT=http://127.0.0.1:8000/v1/logs
export OTEL_EXPORTER_OTLP_LOGS_HEADERS="Authorization=Bearer YOUR_TOKEN"
claude
```

受信状況・APIリクエスト数・トークン・参考費用は設定画面に表示します。OTLPとJSONLは異なるデータソースとして別集計し、互いに合算しません。イベント欠落時の値は不明です。Docker Compose のバックエンドはローカルホストにのみ公開します。別マシンから利用する場合は認証に加えてTLS等を適切に構成してください。[公式モニタリング](https://code.claude.com/docs/en/monitoring-usage)

## テスト

```bash
cd backend
python -m venv venv
. venv/bin/activate
pip install -r requirements-dev.txt
python -m unittest discover -s tests -v

cd ../frontend
npm ci
npx playwright install chromium
npm run lint
npm run build
npm run test:e2e
```

E2Eはテスト用の一時ディレクトリとポート18765/18766で実際のAPIと画面を起動し、終了後にデータを削除します。個人のClaude履歴やOpenAI APIには接続しません。ポートが使用中の場合は解放してから実行してください。
