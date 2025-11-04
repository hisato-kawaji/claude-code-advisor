import { useState } from 'react';
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query';
import { statsApi, analysisApi } from './api';
import { XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, LineChart, Line } from 'recharts';
import './App.css';

const queryClient = new QueryClient();

function Dashboard() {
  const [period, setPeriod] = useState<'daily' | 'weekly' | 'monthly'>('daily');
  const [selectedPrompt, setSelectedPrompt] = useState('');
  const [promptLimit, setPromptLimit] = useState(10);

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

  const { data: performance } = useQuery({
    queryKey: ['performance'],
    queryFn: async () => (await analysisApi.getPerformance(7)).data,
  });

  const { data: bestPractices } = useQuery({
    queryKey: ['bestPractices'],
    queryFn: async () => (await analysisApi.getBestPractices(7)).data,
  });

  const { data: recentPrompts, isLoading: promptsLoading } = useQuery({
    queryKey: ['recentPrompts', promptLimit],
    queryFn: async () => (await analysisApi.getRecentPrompts(promptLimit)).data,
  });

  const { data: promptImprovement, refetch: improvePrompt, isLoading: improvementLoading, isError: improvementError, error: improvementErrorData } = useQuery({
    queryKey: ['improvePrompt', selectedPrompt],
    queryFn: async () => (await analysisApi.improvePrompt(selectedPrompt)).data,
    enabled: false,
  });

  const formatNumber = (num: number) => num.toLocaleString();
  const formatPercentage = (num: number | null) =>
    num !== null ? `${num > 0 ? '+' : ''}${num.toFixed(1)}%` : '-';

  const chartData = historyData?.history.map((item: any) => ({
    date: item.date,
    sessions: item.total_sessions,
    messages: item.total_messages,
    inputTokens: Math.round(item.total_input_tokens / 1000),
    outputTokens: Math.round(item.total_output_tokens / 1000),
  })) || [];

  return (
    <div className="dashboard">
      <h1>Claude Code Analytics</h1>

      {/* Period Selector */}
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
                <Line type="monotone" dataKey="sessions" stroke="#8884d8" strokeWidth={3} name="Sessions" dot={{ r: 4 }} />
                <Line type="monotone" dataKey="messages" stroke="#82ca9d" strokeWidth={3} name="Messages" dot={{ r: 4 }} />
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
                <Line type="monotone" dataKey="inputTokens" stroke="#ffc658" strokeWidth={3} name="Input Tokens (K)" dot={{ r: 4 }} />
                <Line type="monotone" dataKey="outputTokens" stroke="#ff7c7c" strokeWidth={3} name="Output Tokens (K)" dot={{ r: 4 }} />
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
      {performance && (
        <div className="analysis-section">
          <h2>Performance Analysis</h2>
          <div className="score-card">
            <h3>Overall Score: {performance.overall_score.toFixed(1)}/100</h3>
            <p>Task Completion Rate: {(performance.task_completion_rate * 100).toFixed(1)}%</p>
            <p>Avg Turns per Task: {performance.avg_turns_per_task.toFixed(1)}</p>
            <p>Error Rate: {(performance.error_rate * 100).toFixed(1)}%</p>
          </div>

          <div className="feedback">
            <h4>Feedback</h4>
            <p>{performance.feedback}</p>
          </div>

          <div className="lists">
            <div>
              <h4>Strengths</h4>
              <ul>
                {performance.strengths.map((s, i) => <li key={i}>{s}</li>)}
              </ul>
            </div>
            <div>
              <h4>Areas for Improvement</h4>
              <ul>
                {performance.areas_for_improvement.map((a, i) => <li key={i}>{a}</li>)}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Best Practices Check */}
      {bestPractices && (
        <div className="analysis-section">
          <h2>Best Practices Check</h2>
          <div className="score-card">
            <h3>Score: {bestPractices.score.toFixed(1)}/100</h3>
          </div>

          <div className="lists">
            <div>
              <h4>Passed Checks ({bestPractices.passed_checks.length})</h4>
              <ul>
                {bestPractices.passed_checks.map((c, i) => <li key={i} className="passed">{c}</li>)}
              </ul>
            </div>
            <div>
              <h4>Failed Checks ({bestPractices.failed_checks.length})</h4>
              <ul>
                {bestPractices.failed_checks.map((c, i) => <li key={i} className="failed">{c}</li>)}
              </ul>
            </div>
          </div>

          <div className="recommendations">
            <h4>Recommendations</h4>
            <ul>
              {bestPractices.recommendations.map((r, i) => <li key={i}>{r}</li>)}
            </ul>
          </div>
        </div>
      )}

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
                <p>{promptImprovement.explanation}</p>
              </div>
              <div>
                <h4>Best Practice References</h4>
                <ul>
                  {promptImprovement.best_practice_references.map((ref, i) => (
                    <li key={i}>{ref}</li>
                  ))}
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

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Dashboard />
    </QueryClientProvider>
  );
}

export default App;
