import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { analysisApi } from '../api';
import type { PromptImprovementExample } from '../types';
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
  const [searchParams, setSearchParams] = useSearchParams();
  const [days, setDays] = useState(7);
  const [draft, setDraft] = useState('');
  const [submittedPrompt, setSubmittedPrompt] = useState('');

  // Best practices score + perspective breakdown (on-demand)
  const bp = useQuery({
    queryKey: ['adviceBestPractices', days],
    queryFn: async () => (await analysisApi.getBestPractices(days)).data,
    enabled: false,
    staleTime: 15 * 60 * 1000,
    gcTime: 60 * 60 * 1000,
  });

  // High-cost prompt patterns (on-demand)
  const insights = useQuery({
    queryKey: ['adviceInsights', days],
    queryFn: async () => (await analysisApi.getPromptTokenInsights(days)).data,
    enabled: false,
    staleTime: 15 * 60 * 1000,
    gcTime: 60 * 60 * 1000,
  });

  // Recent prompts for the rewrite picker
  const recent = useQuery({
    queryKey: ['adviceRecentPrompts'],
    queryFn: async () => (await analysisApi.getRecentPrompts(20)).data,
  });

  // Prompt rewrite (on-demand, keyed by submitted prompt)
  const improve = useQuery({
    queryKey: ['adviceImprove', submittedPrompt],
    queryFn: async () => (await analysisApi.improvePrompt(submittedPrompt)).data,
    enabled: !!submittedPrompt,
    staleTime: 15 * 60 * 1000,
  });

  // プロンプト分析からの遷移（?prompt=...）を受けて自動でプリフィル＆実行
  useEffect(() => {
    const p = searchParams.get('prompt');
    if (p) {
      setDraft(p);
      setSubmittedPrompt(p);
      searchParams.delete('prompt');
      setSearchParams(searchParams, { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const runRewrite = () => {
    if (draft.trim().length >= 5) setSubmittedPrompt(draft.trim());
  };

  return (
    <div className="advice-page">
      <h1 className="page-title">改善アドバイス</h1>
      <p className="adv-description">
        最新の公式ベストプラクティスに基づき、使い方の評価・高消費パターン・プロンプトの書き換えを提案します。各分析はボタンを押したときだけ実行されます。
      </p>

      <div className="period-selector">
        {PERIODS.map(d => (
          <button key={d} className={days === d ? 'active' : ''} onClick={() => setDays(d)}>
            過去{d}日間
          </button>
        ))}
      </div>

      {/* 1. Prompt rewrite tool */}
      <section className="adv-section">
        <h2>✏️ プロンプト書き換えツール</h2>
        <p className="adv-hint">改善したいプロンプトを貼り付けるか、最近のプロンプトから選んでください。</p>
        {recent.data?.prompts && recent.data.prompts.length > 0 && (
          <select
            className="adv-select"
            value=""
            onChange={(e) => { if (e.target.value) setDraft(e.target.value); }}
          >
            <option value="">最近のプロンプトから選ぶ...</option>
            {recent.data.prompts.map((p, i) => (
              <option key={i} value={p.prompt}>
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
        <button className="adv-run-btn" onClick={runRewrite} disabled={draft.trim().length < 5 || improve.isFetching}>
          {improve.isFetching ? '改善中...' : 'このプロンプトを改善'}
        </button>

        {improve.isError && (
          <div className="adv-error">改善案の生成に失敗しました。OpenAI APIキーを確認してください。</div>
        )}
        {improve.data && submittedPrompt && (
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
          <button className="adv-run-btn small" onClick={() => insights.refetch()} disabled={insights.isFetching}>
            {insights.isFetching ? '分析中...' : insights.data ? '再分析' : '分析を実行'}
          </button>
        </div>
        {insights.isFetching ? (
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
                <h3>効率に関する観察</h3>
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
          <p className="adv-placeholder">「分析を実行」で、消費上位プロンプトから高コストなパターンと改善策を抽出します。</p>
        )}
      </section>

      {/* 3. Best-practices score */}
      <section className="adv-section">
        <div className="adv-section-header">
          <h2>✅ ベストプラクティス評価</h2>
          <button className="adv-run-btn small" onClick={() => bp.refetch()} disabled={bp.isFetching}>
            {bp.isFetching ? '評価中...' : bp.data ? '再評価' : '評価を実行'}
          </button>
        </div>
        {bp.isFetching ? (
          <div className="loading-container"><div className="spinner" /><p className="loading-text">最近の使い方を評価中...</p></div>
        ) : bp.isError ? (
          <div className="adv-error">評価に失敗しました。OpenAI APIキーを確認してください。</div>
        ) : bp.data ? (
          <div className="adv-insights">
            <div className="adv-score">スコア: <strong>{bp.data.score.toFixed(0)}</strong> / 100</div>
            <div className="adv-block">
              <h3>できている点（{bp.data.passed_checks.length}）</h3>
              <ul>{bp.data.passed_checks.map((c, i) => <li key={i} className="pass"><Bilingual text={c} /></li>)}</ul>
            </div>
            <div className="adv-block">
              <h3>改善が必要な点（{bp.data.failed_checks.length}）</h3>
              <ul>{bp.data.failed_checks.map((c, i) => <li key={i} className="fail"><Bilingual text={c} /></li>)}</ul>
            </div>
            <div className="adv-block">
              <h3>推奨事項</h3>
              <ul>{bp.data.recommendations.map((r, i) => <li key={i}><Bilingual text={r} /></li>)}</ul>
            </div>
          </div>
        ) : (
          <p className="adv-placeholder">「評価を実行」で、最近のプロンプト履歴を公式ベストプラクティスに照らして採点します。</p>
        )}
      </section>
    </div>
  );
}
