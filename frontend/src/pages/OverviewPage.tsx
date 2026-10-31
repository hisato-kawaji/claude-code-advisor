import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { statsApi } from '../api';
import {
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  LineChart, Line, BarChart, Bar,
} from 'recharts';
import './OverviewPage.css';

type Period = 'daily' | 'weekly' | 'monthly';

const getYesterday = () => {
  const d = new Date();
  d.setDate(d.getDate() - 1);
  return d.toISOString().split('T')[0];
};

const formatNumber = (n: number) => n.toLocaleString();
const formatPercentage = (n: number | null | undefined) =>
  n !== null && n !== undefined ? `${n > 0 ? '+' : ''}${n.toFixed(1)}%` : '-';

const periodLabel: Record<Period, string> = {
  daily: '過去30日',
  weekly: '過去6か月',
  monthly: '過去12か月',
};

export function OverviewPage() {
  const [period, setPeriod] = useState<Period>('daily');
  const [selectedDate, setSelectedDate] = useState(getYesterday());

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['stats', period],
    queryFn: async () => {
      const res = period === 'daily'
        ? await statsApi.getDaily()
        : period === 'weekly'
        ? await statsApi.getWeekly()
        : await statsApi.getMonthly();
      return res.data;
    },
  });

  const { data: historyData, isLoading: historyLoading } = useQuery({
    queryKey: ['history', period],
    queryFn: async () => {
      const res = period === 'daily'
        ? await statsApi.getDailyHistory(30)
        : period === 'weekly'
        ? await statsApi.getWeeklyHistory(26)
        : await statsApi.getMonthlyHistory(12);
      return res.data;
    },
  });

  const { data: hourlyData, isLoading: hourlyLoading } = useQuery({
    queryKey: ['hourlyStats', selectedDate],
    queryFn: () => statsApi.getHourly(selectedDate).then(r => r.data),
    enabled: !!selectedDate,
  });

  const chartData = useMemo(() => {
    if (!historyData?.history) return [];
    return historyData.history.map((item) => ({
      date: item.date,
      sessions: item.total_sessions,
      messages: item.total_messages,
      inputTokens: Math.round(item.total_input_tokens / 1000),
      outputTokens: Math.round(item.total_output_tokens / 1000),
    }));
  }, [historyData]);

  const hourlyTable = useMemo(() => {
    if (!hourlyData) return [];
    let ci = 0, co = 0;
    return hourlyData.map(d => {
      ci += d.input_tokens; co += d.output_tokens;
      return { ...d, cumulative_input: ci, cumulative_output: co };
    });
  }, [hourlyData]);

  return (
    <div className="overview-page">
      <h1 className="page-title">使用状況</h1>

      <div className="period-selector">
        {(['daily', 'weekly', 'monthly'] as Period[]).map(p => (
          <button key={p} className={period === p ? 'active' : ''} onClick={() => setPeriod(p)}>
            {p === 'daily' ? '日次' : p === 'weekly' ? '週次' : '月次'}
          </button>
        ))}
      </div>

      {/* KPI Cards */}
      {statsLoading ? (
        <div className="loading-container"><div className="spinner" /><p className="loading-text">統計を読み込み中...</p></div>
      ) : stats ? (
        <div className="ov-kpi-grid">
          <div className="ov-kpi-card">
            <h3>セッション</h3>
            <p className="ov-kpi-value">{formatNumber(stats.current.total_sessions)}</p>
            <p className="ov-kpi-change">{formatPercentage(stats.change_percentage?.total_sessions)}</p>
          </div>
          <div className="ov-kpi-card">
            <h3>メッセージ</h3>
            <p className="ov-kpi-value">{formatNumber(stats.current.total_messages)}</p>
            <p className="ov-kpi-change">{formatPercentage(stats.change_percentage?.total_messages)}</p>
          </div>
          <div className="ov-kpi-card">
            <h3>Input トークン</h3>
            <p className="ov-kpi-value">{formatNumber(stats.current.total_input_tokens)}</p>
            <p className="ov-kpi-change">{formatPercentage(stats.change_percentage?.total_input_tokens)}</p>
          </div>
          <div className="ov-kpi-card">
            <h3>Output トークン</h3>
            <p className="ov-kpi-value">{formatNumber(stats.current.total_output_tokens)}</p>
            <p className="ov-kpi-change">{formatPercentage(stats.change_percentage?.total_output_tokens)}</p>
          </div>
        </div>
      ) : null}

      {/* Trend Charts */}
      {historyLoading ? (
        <div className="loading-container"><div className="spinner" /><p className="loading-text">チャートを読み込み中...</p></div>
      ) : chartData.length > 0 ? (
        <div className="ov-charts">
          <div className="ov-chart-card">
            <h2>セッション・メッセージ推移（{periodLabel[period]}）</h2>
            <ResponsiveContainer width="100%" height={320}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" angle={-45} textAnchor="end" height={70} tick={{ fontSize: 11 }} />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="sessions" stroke="#8884d8" strokeWidth={2} name="セッション" dot={{ r: 3 }} isAnimationActive={false} />
                <Line type="monotone" dataKey="messages" stroke="#82ca9d" strokeWidth={2} name="メッセージ" dot={{ r: 3 }} isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <div className="ov-chart-card">
            <h2>トークン使用量推移（{periodLabel[period]}）</h2>
            <ResponsiveContainer width="100%" height={320}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" angle={-45} textAnchor="end" height={70} tick={{ fontSize: 11 }} />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="inputTokens" stroke="#ffc658" strokeWidth={2} name="Input (K)" dot={{ r: 3 }} isAnimationActive={false} />
                <Line type="monotone" dataKey="outputTokens" stroke="#ff7c7c" strokeWidth={2} name="Output (K)" dot={{ r: 3 }} isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      ) : (
        <div className="ov-chart-card"><p className="ov-empty">選択期間のデータがありません。</p></div>
      )}

      {/* Hourly drill-down (旧モニタリング) */}
      <div className="ov-chart-card">
        <div className="ov-hourly-header">
          <h2>時間別トークン消費（1日を掘り下げ）</h2>
          <div className="ov-date-picker">
            <label htmlFor="ov-date">日付:</label>
            <input
              id="ov-date"
              type="date"
              value={selectedDate}
              max={getYesterday()}
              onChange={(e) => setSelectedDate(e.target.value)}
            />
          </div>
        </div>
        {hourlyLoading ? (
          <div className="loading-container"><div className="spinner" /><p className="loading-text">読み込み中...</p></div>
        ) : hourlyData && hourlyData.length > 0 ? (
          <>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={hourlyData} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="hour" label={{ value: '時', position: 'insideBottom', offset: -5 }} />
                <YAxis />
                <Tooltip />
                <Legend verticalAlign="top" />
                <Bar dataKey="input_tokens" name="Input" fill="#8884d8" isAnimationActive={false} />
                <Bar dataKey="output_tokens" name="Output" fill="#82ca9d" isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
            <div className="ov-hourly-table-wrap">
              <table className="ov-hourly-table">
                <thead>
                  <tr><th>時間</th><th>Input</th><th>Output</th><th>累積 Input</th><th>累積 Output</th></tr>
                </thead>
                <tbody>
                  {hourlyTable.map(row => (
                    <tr key={row.hour}>
                      <td>{`${row.hour}:00`}</td>
                      <td>{row.input_tokens.toLocaleString()}</td>
                      <td>{row.output_tokens.toLocaleString()}</td>
                      <td>{row.cumulative_input.toLocaleString()}</td>
                      <td>{row.cumulative_output.toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        ) : (
          <p className="ov-empty">選択日のデータがありません。</p>
        )}
      </div>
    </div>
  );
}
