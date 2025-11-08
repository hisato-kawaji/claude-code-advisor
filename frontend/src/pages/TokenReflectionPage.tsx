import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { analysisApi } from '../api';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';
import './TokenReflectionPage.css';

export function TokenReflectionPage() {
  const [days, setDays] = useState(7);

  const { data: tokenReflection, isLoading, isError, error } = useQuery({
    queryKey: ['tokenReflection', days],
    queryFn: async () => (await analysisApi.getTokenReflection(days)).data,
    // Longer staleTime for expensive LLM analysis (15 minutes)
    staleTime: 15 * 60 * 1000,
    gcTime: 60 * 60 * 1000, // 1 hour cache
  });

  const formatNumber = (num: number) => num.toLocaleString();
  const formatCost = (cost: number) => `$${cost.toFixed(2)}`;

  // Prepare data for pie chart
  const pieData = tokenReflection ? [
    { name: 'Input Tokens', value: tokenReflection.summary.total_input_tokens, color: '#ffc658' },
    { name: 'Output Tokens', value: tokenReflection.summary.total_output_tokens, color: '#ff7c7c' },
  ] : [];

  return (
    <div className="token-reflection-page">
      <h1>トークン消費振り返り</h1>

      {/* Period Selector */}
      <div className="period-selector">
        <button
          className={days === 7 ? 'active' : ''}
          onClick={() => setDays(7)}
        >
          過去7日間
        </button>
        <button
          className={days === 14 ? 'active' : ''}
          onClick={() => setDays(14)}
        >
          過去14日間
        </button>
        <button
          className={days === 30 ? 'active' : ''}
          onClick={() => setDays(30)}
        >
          過去30日間
        </button>
      </div>

      {isLoading ? (
        <div className="loading-container">
          <div className="spinner"></div>
          <p className="loading-text">トークン消費データを分析中...</p>
        </div>
      ) : isError ? (
        <div className="error-container">
          <h3>エラーが発生しました</h3>
          <p>{error instanceof Error ? error.message : 'データの取得に失敗しました'}</p>
          <p>バックエンドが起動しているか、OpenAI APIキーが設定されているか確認してください。</p>
        </div>
      ) : tokenReflection ? (
        <>
          {/* Summary Cards */}
          <div className="summary-grid">
            <div className="summary-card">
              <h3>総トークン数</h3>
              <p className="summary-value">{formatNumber(tokenReflection.summary.total_tokens)}</p>
              <p className="summary-label">トークン</p>
            </div>
            <div className="summary-card">
              <h3>推定コスト</h3>
              <p className="summary-value cost">{formatCost(tokenReflection.summary.estimated_cost_usd)}</p>
              <p className="summary-label">USD</p>
            </div>
            <div className="summary-card">
              <h3>1日あたり平均</h3>
              <p className="summary-value">{formatNumber(Math.round(tokenReflection.summary.avg_tokens_per_day))}</p>
              <p className="summary-label">トークン/日</p>
            </div>
            <div className="summary-card">
              <h3>効率スコア</h3>
              <p className="summary-value score">{tokenReflection.analysis.efficiency_score.toFixed(1)}</p>
              <p className="summary-label">/100</p>
            </div>
          </div>

          {/* Detailed Stats */}
          <div className="stats-section">
            <h2>詳細統計</h2>
            <div className="stats-grid-two">
              <div className="stat-item">
                <span className="stat-label">Input Tokens:</span>
                <span className="stat-value">{formatNumber(tokenReflection.summary.total_input_tokens)}</span>
              </div>
              <div className="stat-item">
                <span className="stat-label">Output Tokens:</span>
                <span className="stat-value">{formatNumber(tokenReflection.summary.total_output_tokens)}</span>
              </div>
              <div className="stat-item">
                <span className="stat-label">Cache Creation:</span>
                <span className="stat-value">{formatNumber(tokenReflection.summary.cache_creation_tokens)}</span>
              </div>
              <div className="stat-item">
                <span className="stat-label">Cache Read:</span>
                <span className="stat-value">{formatNumber(tokenReflection.summary.cache_read_tokens)}</span>
              </div>
              <div className="stat-item">
                <span className="stat-label">セッションあたり平均:</span>
                <span className="stat-value">{formatNumber(Math.round(tokenReflection.summary.avg_tokens_per_session))}</span>
              </div>
              <div className="stat-item">
                <span className="stat-label">Input/Output比率:</span>
                <span className="stat-value">{tokenReflection.summary.input_output_ratio.toFixed(2)}</span>
              </div>
            </div>
          </div>

          {/* Pie Chart */}
          {pieData.length > 0 && (
            <div className="chart-section">
              <h2>トークン構成比</h2>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }: any) => `${name}: ${(percent * 100).toFixed(1)}%`}
                    outerRadius={100}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {pieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Usage Pattern */}
          <div className="pattern-section">
            <h2>使用パターン</h2>
            <div className="pattern-box">
              <p>{tokenReflection.analysis.token_usage_pattern}</p>
            </div>
          </div>

          {/* Analysis Sections */}
          <div className="analysis-grid">
            <div className="analysis-card">
              <h3>トークン消費が多かった活動</h3>
              <ul>
                {tokenReflection.analysis.most_token_intensive_activities.map((activity, i) => {
                  const [english, japanese] = activity.split('\n');
                  return (
                    <li key={i}>
                      <span className="english-text">{english}</span>
                      {japanese && <span className="japanese-text">{japanese}</span>}
                    </li>
                  );
                })}
              </ul>
            </div>

            <div className="analysis-card">
              <h3>コスト最適化の提案</h3>
              <ul>
                {tokenReflection.analysis.cost_optimization_suggestions.map((suggestion, i) => {
                  const [english, japanese] = suggestion.split('\n');
                  return (
                    <li key={i}>
                      <span className="english-text">{english}</span>
                      {japanese && <span className="japanese-text">{japanese}</span>}
                    </li>
                  );
                })}
              </ul>
            </div>
          </div>

          {/* Next Steps */}
          <div className="next-steps-section">
            <h2>次のアクションステップ</h2>
            <div className="next-steps-list">
              {tokenReflection.analysis.next_steps.map((step, i) => {
                const [english, japanese] = step.split('\n');
                return (
                  <div key={i} className="next-step-item">
                    <span className="step-number">{i + 1}</span>
                    <div className="step-text">
                      <span className="english-text">{english}</span>
                      {japanese && <span className="japanese-text">{japanese}</span>}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Prompt Improvement Example */}
          {tokenReflection.analysis.prompt_improvement_example && (
            <div className="prompt-improvement-section">
              <h2>プロンプト改善例</h2>
              <div className="prompt-comparison">
                <div className="prompt-box original">
                  <h3>元のプロンプト</h3>
                  <pre>{tokenReflection.analysis.prompt_improvement_example.original}</pre>
                </div>
                <div className="prompt-arrow">→</div>
                <div className="prompt-box improved">
                  <h3>改善後のプロンプト</h3>
                  <pre>{tokenReflection.analysis.prompt_improvement_example.improved}</pre>
                </div>
              </div>
              <div className="prompt-explanation">
                <h3>改善のポイント</h3>
                <p className="explanation-en">{tokenReflection.analysis.prompt_improvement_example.explanation_en}</p>
                <p className="explanation-ja">{tokenReflection.analysis.prompt_improvement_example.explanation_ja}</p>
              </div>
            </div>
          )}

          {/* AI Reflection */}
          <div className="reflection-section">
            <h2>AI による総合振り返り</h2>
            <div className="reflection-content">
              <p>{tokenReflection.reflection}</p>
            </div>
          </div>
        </>
      ) : null}
    </div>
  );
}
