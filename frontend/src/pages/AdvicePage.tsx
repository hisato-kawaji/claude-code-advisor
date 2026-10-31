import { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import { analysisApi } from '../api';
import type { PromptImprovementExample } from '../types';
import { SendPreview } from '../components/SendPreview';
import './AdvicePage.css';

// "[Perspective] English\n[Perspective] 日本語" を分解して日本語優先で表示
function Bilingual({ text }: { text: string }) {
  const [en, ja] = text.split('\n');
  return (
    <div className="adv-bilingual">
      <span className="adv-bilingual-ja">{ja || en}</span>
      {ja && en && <span className="adv-bilingual-en">{en}</span>}
    </div>
  );
}

const PERIODS = [7, 14, 30];

export function AdvicePage() {
  const location = useLocation();
  const [days, setDays] = useState(7);
  const [draft, setDraft] = useState('');
  const [draftProject, setDraftProject] = useState<string | null>(null);
  useEffect(() => {
    const state = location.state as { prompt?: string; projectPath?: string | null } | null;
    if (state?.prompt) { setDraft(state.prompt); setDraftProject(state.projectPath ?? null); }
  }, [location.state]);

  const cacheAdvice = useQuery({ queryKey: ['cacheAdvice', days],
    queryFn: async () => (await analysisApi.getCacheAdvice(days)).data });
  const bp = useMutation({ mutationFn: async (promptExcerpts: string[]) =>
    (await analysisApi.getBestPractices(promptExcerpts)).data });
  const insights = useMutation({ mutationFn: async (preview: Awaited<ReturnType<typeof analysisApi.previewPromptTokenInsights>>['data']) =>
    (await analysisApi.getPromptTokenInsights(preview)).data });
  const improve = useMutation({ mutationFn: async (value: { prompt: string; project_path: string | null }) =>
    (await analysisApi.improvePrompt(value.prompt, value.project_path)).data });
  const recent = useQuery({ queryKey: ['adviceRecentPrompts'],
    queryFn: async () => (await analysisApi.getRecentPrompts(20)).data });
  const [previewError, setPreviewError] = useState(false);
  const [pending, setPending] = useState<{ payload: unknown; send: () => void } | null>(null);

  const runRewrite = async () => {
    try {
      setPreviewError(false);
      const prompt = draft.trim();
      if (prompt.length < 5) return;
      const preview = (await analysisApi.previewPrompt(prompt, draftProject)).data;
      setPending({ payload: preview, send: () => improve.mutate(preview) });
    } catch { setPreviewError(true); }
  };
  const runBestPractices = async () => {
    try {
      setPreviewError(false);
      const preview = (await analysisApi.previewBestPractices(days)).data;
      setPending({ payload: preview, send: () => bp.mutate(preview.prompt_excerpts) });
    } catch { setPreviewError(true); }
  };
  const runInsights = async () => {
    try {
      setPreviewError(false);
      const preview = (await analysisApi.previewPromptTokenInsights(days)).data;
      setPending({ payload: preview, send: () => insights.mutate(preview) });
    } catch { setPreviewError(true); }
  };

  return (
    <div className="advice-page">
      {pending && <SendPreview payload={pending.payload} onCancel={() => setPending(null)} onConfirm={() => { pending.send(); setPending(null); }} />}
      <h1 className="page-title">改善アドバイス</h1>
      <p className="adv-description">
        公式ガイドを参考に、プロンプトの振り返りや書き換えを提案します。分析前にOpenAIへ送る内容を確認できます。履歴に現れない作業は評価できません。
      </p>

      {previewError && <div className="adv-error">分析対象を取得できませんでした。除外設定、同期状態、対象期間を確認してください。</div>}
      <div className="period-selector">
        {PERIODS.map(d => (
          <button key={d} className={days === d ? 'active' : ''} aria-pressed={days === d} onClick={() => setDays(d)}>
            過去{d}日間
          </button>
        ))}
      </div>

      <section className="adv-section" aria-labelledby="cache-advice-title">
        <h2 id="cache-advice-title">キャッシュ利用の振り返り</h2>
        <p className="adv-hint">この分析はローカルで行います。キャッシュ読み込みは再利用の記録で、多いことだけでは無駄や効率の悪さを示しません。</p>
        {cacheAdvice.isLoading ? <p>集計中...</p> : cacheAdvice.isError ? <div className="adv-error">キャッシュ利用状況を取得できませんでした。</div> : cacheAdvice.data && cacheAdvice.data.request_count > 0 ? (
          <div className="cache-advice">
            <p>対象: {cacheAdvice.data.start_date}〜{cacheAdvice.data.end_date}（UTC）。記録のあるリクエストまたは行 {cacheAdvice.data.request_count.toLocaleString()}件。</p>
            <div className="cache-summary">
              <div><span>キャッシュ読み込み</span><strong>{cacheAdvice.data.totals.cache_read_tokens.toLocaleString()}</strong></div>
              <div><span>キャッシュ書き込み</span><strong>{cacheAdvice.data.totals.cache_creation_tokens.toLocaleString()}</strong></div>
              <div><span>入力のうち読み込みの割合</span><strong>{cacheAdvice.data.cache_read_share_of_input_pct == null ? '不明' : `${cacheAdvice.data.cache_read_share_of_input_pct}%`}</strong></div>
            </div>
            <p className="adv-hint">割合は読み込み ÷（通常Input＋書き込み＋読み込み）。リクエスト単位のヒット率や、週間上限の消費率ではありません。{cacheAdvice.data.missing_request_ids > 0 && `リクエストIDのない ${cacheAdvice.data.missing_request_ids.toLocaleString()} 行は行単位で数えています。`}</p>
            <p>読み込みの内訳: メイン {cacheAdvice.data.sources.main.toLocaleString()} / 子エージェント {cacheAdvice.data.sources.subagent.toLocaleString()} / 判別不可 {cacheAdvice.data.sources.unknown.toLocaleString()}</p>
            <h3>読み込みが多いセッション・記録</h3>
            <div className="cache-table-wrap"><table className="cache-table"><thead><tr><th>セッションID（先頭）</th><th>種別</th><th>リクエスト・行</th><th>読み込み</th><th>1回あたり平均</th></tr></thead><tbody>
              {cacheAdvice.data.top_sessions.map((item, index) => <tr key={`${item.session_id}-${item.source_kind}-${index}`}><td>{item.session_id}</td><td>{item.source_kind === 'main' ? 'メイン' : item.source_kind === 'subagent' ? '子エージェント' : '判別不可'}</td><td>{item.request_count.toLocaleString()}</td><td>{item.cache_read_tokens.toLocaleString()}</td><td>{item.avg_cache_read_per_request.toLocaleString()}</td></tr>)}
            </tbody></table></div>
            <p className="adv-hint">別ファイルや未同期・別端末の履歴は含まれません。同じセッションの子エージェントは別行になる場合があります。平均は累積使用量を件数で割った値で、現在のコンテキストサイズではありません。</p>
            <h3>改善候補と確認方法</h3>
            <ol>{cacheAdvice.data.recommendations.map(item => <li key={item.title}><strong>{item.title}</strong><p>{item.detail}</p></li>)}</ol>
            <p className="adv-hint">参照: <a href="https://code.claude.com/docs/en/prompt-caching" target="_blank" rel="noreferrer">Claude Codeのキャッシュ仕様</a> / <a href="https://code.claude.com/docs/en/costs" target="_blank" rel="noreferrer">コスト管理</a></p>
          </div>
        ) : <p className="adv-placeholder">この期間にトークン使用の記録がありません。同期状況や対象期間を確認してください。</p>}
      </section>

      {/* 1. Prompt rewrite tool */}
      <section className="adv-section">
        <h2>✏️ プロンプト書き換えツール</h2>
        <p className="adv-hint">改善したいプロンプトを貼り付けるか、最近のプロンプトから選んでください。</p>
        {recent.data?.prompts && recent.data.prompts.length > 0 && (
          <select
            className="adv-select"
            value=""
            onChange={(e) => { const p = recent.data?.prompts[Number(e.target.value)]; if (e.target.value !== "" && p) { setDraft(p.prompt); setDraftProject(p.project_path); } }}
          >
            <option value="">最近のプロンプトから選ぶ...</option>
            {recent.data.prompts.map((p, i) => (
              <option key={i} value={i}>
                {p.prompt.substring(0, 100)}{p.prompt.length > 100 ? '...' : ''}
              </option>
            ))}
          </select>
        )}
        <textarea
          className="adv-textarea"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="ここにプロンプトを入力または貼り付け..."
          rows={4}
        />
        <button className="adv-run-btn" onClick={runRewrite} disabled={draft.trim().length < 5 || improve.isPending}>
          {improve.isPending ? '改善中...' : 'このプロンプトを改善'}
        </button>

        {improve.isError && (
          <div className="adv-error">改善案の生成に失敗しました。OpenAI APIキーを確認してください。</div>
        )}
        {improve.data && (
          <div className="adv-rewrite-result">
            <div className="adv-rewrite-pair">
              <div className="adv-rewrite-col original">
                <h4>元のプロンプト</h4>
                <pre>{improve.data.original_prompt}</pre>
              </div>
              <div className="adv-rewrite-col improved">
                <h4>改善後</h4>
                <pre>{improve.data.improved_prompt}</pre>
              </div>
            </div>
            {improve.data.explanation_ja && <p className="adv-explanation">{improve.data.explanation_ja}</p>}
            {improve.data.best_practice_references?.length > 0 && (
              <ul className="adv-refs">
                {improve.data.best_practice_references.map((r, i) => (
                  <li key={i}><Bilingual text={r} /></li>
                ))}
              </ul>
            )}
          </div>
        )}
      </section>

      {/* 2. High-cost patterns */}
      <section className="adv-section">
        <div className="adv-section-header">
          <h2>💸 高消費プロンプトのパターン</h2>
          <button className="adv-run-btn small" onClick={() => runInsights()} disabled={insights.isPending}>
            {insights.isPending ? '分析中...' : insights.data ? '再分析' : '分析を実行'}
          </button>
        </div>
        {insights.isPending ? (
          <div className="loading-container"><div className="spinner" /><p className="loading-text">消費上位プロンプトを分析中...</p></div>
        ) : insights.isError ? (
          <div className="adv-error">分析に失敗しました。期間内にデータがあるか、OpenAI APIキーを確認してください。</div>
        ) : insights.data ? (
          <div className="adv-insights">
            <div className="adv-block">
              <h3>高消費パターン</h3>
              <ul>{insights.data.high_cost_patterns.map((p, i) => <li key={i}><Bilingual text={p} /></li>)}</ul>
            </div>
            {insights.data.efficiency_observations.length > 0 && (
              <div className="adv-block">
                <h3>利用状況に関する観察</h3>
                <ul>{insights.data.efficiency_observations.map((p, i) => <li key={i}><Bilingual text={p} /></li>)}</ul>
              </div>
            )}
            <div className="adv-block">
              <h3>改善提案</h3>
              <ul>{insights.data.improvement_suggestions.map((p, i) => <li key={i}><Bilingual text={p} /></li>)}</ul>
            </div>
            {insights.data.example_rewrites.length > 0 && (
              <div className="adv-block">
                <h3>実際のプロンプトの書き換え例</h3>
                {insights.data.example_rewrites.map((ex: PromptImprovementExample, i) => (
                  <div key={i} className="adv-rewrite-result">
                    <div className="adv-rewrite-pair">
                      <div className="adv-rewrite-col original"><h4>元</h4><pre>{ex.original}</pre></div>
                      <div className="adv-rewrite-col improved"><h4>改善後</h4><pre>{ex.improved}</pre></div>
                    </div>
                    {ex.explanation_ja && <p className="adv-explanation">{ex.explanation_ja}</p>}
                  </div>
                ))}
              </div>
            )}
            {insights.data.reflection && (
              <div className="adv-block"><h3>総合振り返り</h3><p className="adv-reflection">{insights.data.reflection}</p></div>
            )}
          </div>
        ) : (
          <p className="adv-placeholder">「分析を実行」で、消費上位プロンプトから消費量の多い履歴を振り返り、確認候補を提示します。</p>
        )}
      </section>

      {/* 3. Best-practices score */}
      <section className="adv-section">
        <div className="adv-section-header">
          <h2>✅ ベストプラクティス評価</h2>
          <button className="adv-run-btn small" onClick={() => runBestPractices()} disabled={bp.isPending}>
            {bp.isPending ? '評価中...' : bp.data ? '再評価' : '評価を実行'}
          </button>
        </div>
        {bp.isPending ? (
          <div className="loading-container"><div className="spinner" /><p className="loading-text">最近の使い方を評価中...</p></div>
        ) : bp.isError ? (
          <div className="adv-error">評価に失敗しました。OpenAI APIキーを確認してください。</div>
        ) : bp.data ? (
          <div className="adv-insights">
            <p>以下は選択した履歴の抜粋に基づく参考意見です。表示されていない作業は判断できません。</p>
            <div className="adv-block">
              <h3>できている点（{bp.data.passed_checks.length}）</h3>
              <ul>{bp.data.passed_checks.map((c, i) => <li key={i} className="pass"><Bilingual text={c} /></li>)}</ul>
            </div>
            <div className="adv-block">
              <h3>確認したい点（{bp.data.failed_checks.length}）</h3>
              <ul>{bp.data.failed_checks.map((c, i) => <li key={i} className="fail"><Bilingual text={c} /></li>)}</ul>
            </div>
            <div className="adv-block">
              <h3>推奨事項</h3>
              <ul>{bp.data.recommendations.map((r, i) => <li key={i}><Bilingual text={r} /></li>)}</ul>
            </div>
          </div>
        ) : (
          <p className="adv-placeholder">「評価を実行」で、最近のプロンプトの抜粋を公式ガイドに照らして振り返ります。</p>
        )}
      </section>
    </div>
  );
}
