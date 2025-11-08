import { useState, useMemo, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { statsApi, analysisApi } from '../api';
import { XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, LineChart, Line } from 'recharts';
import '../App.css';

export function DashboardPage() {
  const [period, setPeriod] = useState<'daily' | 'weekly' | 'monthly'>('daily');
  const [selectedPrompt, setSelectedPrompt] = useState('');
  const [promptLimit, setPromptLimit] = useState(10);
  const queryClient = useQueryClient();

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['stats', period],
    queryFn: async () => {
      const response = period === 'daily'
        ? await statsApi.getDaily()
        : period === 'weekly'
        ? await statsApi.getWeekly()
        : await statsApi.getMonthly();
      return response.data;
    },
  });

  const { data: historyData, isLoading: historyLoading } = useQuery({
    queryKey: ['history', period],
    queryFn: async () => {
      const response = period === 'daily'
        ? await statsApi.getDailyHistory(30)
        : period === 'weekly'
        ? await statsApi.getWeeklyHistory(26)
        : await statsApi.getMonthlyHistory(12);
      return response.data;
    },
  });

  // Lazy load performance and best practices to avoid blocking initial page load
  const { data: performance, isLoading: performanceLoading, refetch: refetchPerformance } = useQuery({
    queryKey: ['performance'],
    queryFn: async () => (await analysisApi.getPerformance(7)).data,
    // Longer staleTime for expensive LLM analysis (15 minutes)
    staleTime: 15 * 60 * 1000,
    gcTime: 60 * 60 * 1000, // 1 hour cache
    enabled: false, // Don't auto-fetch, will be triggered manually
  });

  const { data: bestPractices, isLoading: bestPracticesLoading, refetch: refetchBestPractices } = useQuery({
    queryKey: ['bestPractices'],
    queryFn: async () => (await analysisApi.getBestPractices(7)).data,
    // Longer staleTime for expensive LLM analysis (15 minutes)
    staleTime: 15 * 60 * 1000,
    gcTime: 60 * 60 * 1000, // 1 hour cache
    enabled: false, // Don't auto-fetch, will be triggered manually
  });

  // Auto-fetch analysis data after initial page load (after 1 second delay)
  useEffect(() => {
    const timer = setTimeout(() => {
      refetchPerformance();
      refetchBestPractices();
    }, 1000);
    return () => clearTimeout(timer);
  }, []); // Only run once on mount

  const { data: recentPrompts, isLoading: promptsLoading, refetch: refetchPrompts } = useQuery({
    queryKey: ['recentPrompts', promptLimit],
    queryFn: async () => (await analysisApi.getRecentPrompts(promptLimit)).data,
    enabled: false, // Don't auto-fetch, will be triggered manually
  });

  // Auto-fetch recent prompts after a longer delay (5 seconds)
  useEffect(() => {
    const timer = setTimeout(() => {
      refetchPrompts();
    }, 5000);
    return () => clearTimeout(timer);
  }, []); // Only run once on mount

  const { data: promptImprovement, refetch: improvePrompt, isLoading: improvementLoading, isError: improvementError, error: improvementErrorData } = useQuery({
    queryKey: ['improvePrompt', selectedPrompt],
    queryFn: async () => (await analysisApi.improvePrompt(selectedPrompt)).data,
    enabled: false,
  });

  const syncMutation = useMutation({
    mutationFn: async () => (await statsApi.syncDatabase()).data,
    onSuccess: (data) => {
      // データ同期後、全てのクエリを無効化して再取得
      queryClient.invalidateQueries({ queryKey: ['stats'] });
      queryClient.invalidateQueries({ queryKey: ['history'] });
      alert(`同期完了: ${data.inserted}件の新規エントリを追加しました`);
    },
    onError: () => {
      alert('同期に失敗しました');
    },
  });

  const formatNumber = (num: number) => num.toLocaleString();
  const formatPercentage = (num: number | null) =>
    num !== null ? `${num > 0 ? '+' : ''}${num.toFixed(1)}%` : '-';

  // Memoize chart data calculation to avoid recalculation on every render
  const chartData = useMemo(() => {
    if (!historyData?.history) return [];
    return historyData.history.map((item: any) => ({
      date: item.date,
      sessions: item.total_sessions,
      messages: item.total_messages,
      inputTokens: Math.round(item.total_input_tokens / 1000),
      outputTokens: Math.round(item.total_output_tokens / 1000),
    }));
  }, [historyData]);

  return (
    <div className="dashboard">
      <h1>Claude Code Analytics</h1>

      {/* Period Selector and Sync Button */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div className="period-selector">
          <button
            className={period === 'daily' ? 'active' : ''}
            onClick={() => setPeriod('daily')}
          >
            Daily
          </button>
          <button
            className={period === 'weekly' ? 'active' : ''}
            onClick={() => setPeriod('weekly')}
          >
            Weekly
          </button>
          <button
            className={period === 'monthly' ? 'active' : ''}
            onClick={() => setPeriod('monthly')}
          >
            Monthly
          </button>
        </div>
        <button
          onClick={() => syncMutation.mutate()}
          disabled={syncMutation.isPending}
          style={{
            padding: '8px 16px',
            backgroundColor: syncMutation.isPending ? '#ccc' : '#4CAF50',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: syncMutation.isPending ? 'not-allowed' : 'pointer',
            fontSize: '14px',
            fontWeight: 'bold',
          }}
        >
          {syncMutation.isPending ? '同期中...' : 'データを同期'}
        </button>
      </div>

      {/* Stats Cards */}
      {statsLoading ? (
        <div className="loading-container">
          <div className="spinner"></div>
          <p className="loading-text">Loading statistics...</p>
        </div>
      ) : stats ? (
        <div className="stats-grid">
          <div className="stat-card">
            <h3>Sessions</h3>
            <p className="stat-value">{formatNumber(stats.current.total_sessions)}</p>
            <p className="stat-change">{formatPercentage(stats.change_percentage?.total_sessions || null)}</p>
          </div>
          <div className="stat-card">
            <h3>Messages</h3>
            <p className="stat-value">{formatNumber(stats.current.total_messages)}</p>
            <p className="stat-change">{formatPercentage(stats.change_percentage?.total_messages || null)}</p>
          </div>
          <div className="stat-card">
            <h3>Input Tokens</h3>
            <p className="stat-value">{formatNumber(stats.current.total_input_tokens)}</p>
            <p className="stat-change">{formatPercentage(stats.change_percentage?.total_input_tokens || null)}</p>
          </div>
          <div className="stat-card">
            <h3>Output Tokens</h3>
            <p className="stat-value">{formatNumber(stats.current.total_output_tokens)}</p>
            <p className="stat-change">{formatPercentage(stats.change_percentage?.total_output_tokens || null)}</p>
          </div>
        </div>
      ) : null}

      {/* Charts */}
      {historyLoading ? (
        <div className="loading-container">
          <div className="spinner"></div>
          <p className="loading-text">Loading chart data...</p>
        </div>
      ) : historyData && chartData.length > 0 ? (
        <div className="charts-wrapper">
          {/* Sessions and Messages Chart */}
          <div className="chart-container">
            <h2>Sessions & Messages ({period === 'daily' ? 'Past 30 Days' : period === 'weekly' ? 'Past 6 Months' : 'Past 12 Months'})</h2>
            <ResponsiveContainer width="100%" height={400}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="date"
                  angle={-45}
                  textAnchor="end"
                  height={80}
                  tick={{ fontSize: 11 }}
                />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="sessions" stroke="#8884d8" strokeWidth={3} name="Sessions" dot={{ r: 4 }} isAnimationActive={false} />
                <Line type="monotone" dataKey="messages" stroke="#82ca9d" strokeWidth={3} name="Messages" dot={{ r: 4 }} isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Tokens Chart */}
          <div className="chart-container">
            <h2>Token Usage ({period === 'daily' ? 'Past 30 Days' : period === 'weekly' ? 'Past 6 Months' : 'Past 12 Months'})</h2>
            <ResponsiveContainer width="100%" height={400}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="date"
                  angle={-45}
                  textAnchor="end"
                  height={80}
                  tick={{ fontSize: 11 }}
                />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="inputTokens" stroke="#ffc658" strokeWidth={3} name="Input Tokens (K)" dot={{ r: 4 }} isAnimationActive={false} />
                <Line type="monotone" dataKey="outputTokens" stroke="#ff7c7c" strokeWidth={3} name="Output Tokens (K)" dot={{ r: 4 }} isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      ) : (
        <div className="chart-container">
          <p>No data available for the selected period.</p>
        </div>
      )}

      {/* Performance Analysis */}
      <div className="analysis-section" style={{ display: 'block', visibility: 'visible' }}>
        <h2>Performance Analysis</h2>

        <div className="score-card">
          {performanceLoading ? (
            <div className="loading-container">
              <div className="spinner"></div>
              <p className="loading-text">Loading performance analysis...</p>
            </div>
          ) : performance ? (
            <>
              <h3>Overall Score: {performance.overall_score.toFixed(1)}/100</h3>
              <p>Task Completion Rate: {(performance.task_completion_rate * 100).toFixed(1)}%</p>
              <p>Avg Turns per Task: {performance.avg_turns_per_task.toFixed(1)}</p>
              <p>Error Rate: {(performance.error_rate * 100).toFixed(1)}%</p>
            </>
          ) : (
            <p>No data available</p>
          )}
        </div>

        {!performanceLoading && performance && (
          <>
            <div className="feedback">
              <h4>Feedback</h4>
              <p>{performance.feedback}</p>
            </div>

            <div className="lists">
              <div>
                <h4>Strengths</h4>
                <ul>
                  {performance.strengths.map((s, i) => {
                    const [english, japanese] = s.split('\n');
                    return (
                      <li key={i}>
                        <span className="english-text" style={{ color: '#000' }}>{english}</span>
                        {japanese && <span className="japanese-text" style={{ color: '#000', display: 'block', marginTop: '4px' }}>{japanese}</span>}
                      </li>
                    );
                  })}
                </ul>
              </div>
              <div>
                <h4>Areas for Improvement</h4>
                <ul>
                  {performance.areas_for_improvement.map((a, i) => {
                    const [english, japanese] = a.split('\n');
                    return (
                      <li key={i}>
                        <span className="english-text" style={{ color: '#000' }}>{english}</span>
                        {japanese && <span className="japanese-text" style={{ color: '#000', display: 'block', marginTop: '4px' }}>{japanese}</span>}
                      </li>
                    );
                  })}
                </ul>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Best Practices Check */}
      <div className="analysis-section" style={{ display: 'block', visibility: 'visible' }}>
        <h2>Best Practices Check</h2>

        <div className="score-card">
          {bestPracticesLoading ? (
            <div className="loading-container">
              <div className="spinner"></div>
              <p className="loading-text">Loading best practices analysis...</p>
            </div>
          ) : bestPractices ? (
            <h3>Score: {bestPractices.score.toFixed(1)}/100</h3>
          ) : (
            <p>No data available</p>
          )}
        </div>

        {!bestPracticesLoading && bestPractices && (
          <>
            <div className="lists">
              <div>
                <h4>Passed Checks ({bestPractices.passed_checks.length})</h4>
                <ul>
                  {bestPractices.passed_checks.map((c, i) => {
                    const [english, japanese] = c.split('\n');
                    return (
                      <li key={i} className="passed">
                        <span className="english-text" style={{ color: '#000' }}>{english}</span>
                        {japanese && <span className="japanese-text" style={{ color: '#000', display: 'block', marginTop: '4px' }}>{japanese}</span>}
                      </li>
                    );
                  })}
                </ul>
              </div>
              <div>
                <h4>Failed Checks ({bestPractices.failed_checks.length})</h4>
                <ul>
                  {bestPractices.failed_checks.map((c, i) => {
                    const [english, japanese] = c.split('\n');
                    return (
                      <li key={i} className="failed">
                        <span className="english-text" style={{ color: '#000' }}>{english}</span>
                        {japanese && <span className="japanese-text" style={{ color: '#000', display: 'block', marginTop: '4px' }}>{japanese}</span>}
                      </li>
                    );
                  })}
                </ul>
              </div>
            </div>

            <div className="recommendations">
              <h4>Recommendations</h4>
              <ul>
                {bestPractices.recommendations.map((r, i) => {
                  const [english, japanese] = r.split('\n');
                  return (
                    <li key={i}>
                      <span className="english-text" style={{ color: '#000' }}>{english}</span>
                      {japanese && <span className="japanese-text" style={{ color: '#000', display: 'block', marginTop: '4px' }}>{japanese}</span>}
                    </li>
                  );
                })}
              </ul>
            </div>
          </>
        )}
      </div>

      {/* Prompt Improvement */}
      <div className="prompt-improvement">
        <h2>Prompt Improvement Tool</h2>
        <div>
          <h4>Recent Prompts</h4>
          {promptsLoading ? (
            <div className="loading-container-small">
              <div className="spinner-small"></div>
              <p className="loading-text-small">Loading prompts...</p>
            </div>
          ) : recentPrompts && recentPrompts.prompts && recentPrompts.prompts.length > 0 ? (
            <>
              <div className="prompt-info">
                <p>Showing {recentPrompts.prompts.length} prompts</p>
              </div>
              <select
                value={selectedPrompt}
                onChange={(e) => setSelectedPrompt(e.target.value)}
                className="prompt-select"
              >
                <option value="">Select a recent prompt...</option>
                {recentPrompts.prompts.map((p, i) => (
                  <option key={i} value={p.prompt}>
                    {p.prompt.substring(0, 100)}{p.prompt.length > 100 ? '...' : ''}
                  </option>
                ))}
              </select>
              <div className="button-group">
                <button
                  onClick={() => improvePrompt()}
                  disabled={!selectedPrompt}
                  className="improve-btn"
                >
                  Improve Prompt
                </button>
                <button
                  onClick={() => setPromptLimit(prev => prev + 10)}
                  className="load-more-btn"
                  disabled={promptsLoading}
                >
                  Load 10 More Prompts
                </button>
              </div>
            </>
          ) : (
            <p>No recent prompts found. Start using Claude Code to see prompts here.</p>
          )}
        </div>

        {improvementError && (
          <div className="error-message">
            <h4>Error</h4>
            <p>Failed to improve prompt: {improvementErrorData instanceof Error ? improvementErrorData.message : 'Unknown error'}</p>
            <p>Please make sure the backend is running and OpenAI API key is configured.</p>
          </div>
        )}

        {/* Always show the improvement result section */}
        <div className="improvement-result">
          {promptImprovement ? (
            <>
              <div>
                <h4>Original</h4>
                <p className="prompt-box">{promptImprovement.original_prompt}</p>
              </div>
              <div>
                <h4>Improved</h4>
                <p className="prompt-box improved">{promptImprovement.improved_prompt}</p>
              </div>
              <div>
                <h4>Explanation</h4>
                {promptImprovement.explanation_en && (
                  <p className="explanation-en" style={{ marginBottom: '12px' }}>
                    <strong>English:</strong> {promptImprovement.explanation_en}
                  </p>
                )}
                {promptImprovement.explanation_ja && (
                  <p className="explanation-ja">
                    <strong>日本語:</strong> {promptImprovement.explanation_ja}
                  </p>
                )}
                {/* Fallback for old format */}
                {!promptImprovement.explanation_en && !promptImprovement.explanation_ja && promptImprovement.explanation && (
                  <p>{promptImprovement.explanation}</p>
                )}
              </div>
              <div>
                <h4>Best Practice References</h4>
                <ul>
                  {promptImprovement.best_practice_references.map((ref, i) => {
                    const [english, japanese] = ref.split('\n');
                    return (
                      <li key={i}>
                        <span className="english-text" style={{ color: '#000' }}>{english}</span>
                        {japanese && <span className="japanese-text" style={{ color: '#000', display: 'block', marginTop: '4px' }}>{japanese}</span>}
                      </li>
                    );
                  })}
                </ul>
              </div>
            </>
          ) : (
            <div className="placeholder-text">
              <p>Select a prompt above and click "Improve Prompt" to see the analysis results here.</p>
            </div>
          )}
        </div>

        {/* Full screen loading overlay */}
        {improvementLoading && (
          <div className="loading-overlay">
            <div className="loading-overlay-content">
              <div className="spinner-large"></div>
              <p className="loading-text-large">Analyzing and improving your prompt...</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
