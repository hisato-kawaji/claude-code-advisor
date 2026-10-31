import { useState, Fragment } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import { analysisApi } from '../api';
import type { PromptTurn } from '../types';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { SendPreview } from '../components/SendPreview';
import './PromptAnalysisPage.css';

const PAGE_SIZE = 20;

type SortKey =
  | 'total_tokens'
  | 'output_tokens'
  | 'tool_use_count'
  | 'duration_seconds'
  | 'timestamp';

const formatNumber = (num: number) => num.toLocaleString();
const formatCost = (cost: number | null) => cost === null ? "不明" : `$${cost.toFixed(6)}`;

const formatDuration = (seconds: number) => {
  if (seconds < 60) return `${Math.round(seconds)}秒`;
  const min = Math.floor(seconds / 60);
  if (min < 60) return `${min}分${Math.round(seconds % 60)}秒`;
  return `${Math.floor(min / 60)}時間${min % 60}分`;
};

const formatTimestamp = (ts: string) => {
  const d = new Date(ts);
  if (isNaN(d.getTime())) return ts;
  return d.toLocaleString('ja-JP', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
};

// "English\n日本語" 形式のバイリンガル文字列を表示
function Bilingual({ text }: { text: string }) {
  const [en, ja] = text.split('\n');
  return (
    <div className="pt-bilingual">
      <span className="pt-bilingual-ja">{ja || en}</span>
      {ja && en && <span className="pt-bilingual-en">{en}</span>}
    </div>
  );
}

export function PromptAnalysisPage() {
  const navigate = useNavigate();
  const [days, setDays] = useState(7);
  const [sort, setSort] = useState<SortKey>('total_tokens');
  const [order, setOrder] = useState<'asc' | 'desc'>('desc');
  const [page, setPage] = useState(0);
  const [includeCommands, setIncludeCommands] = useState(true);
  const [expandedKey, setExpandedKey] = useState<string | null>(null);

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['promptTokens', days, sort, order, page, includeCommands],
    queryFn: async () =>
      (
        await analysisApi.getPromptTokens({
          days,
          sort,
          order,
          limit: PAGE_SIZE,
          offset: page * PAGE_SIZE,
          include_commands: includeCommands,
        })
      ).data,
  });

  const { data: insights, isPending: insightsLoading, isError: insightsError, mutate: analyzeInsights } = useMutation({
    mutationFn: async (preview: Awaited<ReturnType<typeof analysisApi.previewPromptTokenInsights>>['data']) =>
      (await analysisApi.getPromptTokenInsights(preview)).data,
  });
  const [previewError, setPreviewError] = useState(false);
  const [preview, setPreview] = useState<Awaited<ReturnType<typeof analysisApi.previewPromptTokenInsights>>['data'] | null>(null);
  const fetchInsights = async () => {
    try {
      setPreviewError(false);
      setPreview((await analysisApi.previewPromptTokenInsights(days)).data);
    } catch { setPreviewError(true); }
  };

  const changePeriod = (d: number) => {
    setDays(d);
    setPage(0);
    setExpandedKey(null);
  };

  const changeSort = (key: SortKey) => {
    if (sort === key) {
      setOrder(order === 'desc' ? 'asc' : 'desc');
    } else {
      setSort(key);
      setOrder('desc');
    }
    setPage(0);
  };

  const sortIndicator = (key: SortKey) =>
    sort === key ? (order === 'desc' ? ' ▼' : ' ▲') : '';

  const turnKey = (t: PromptTurn) => `${t.session_id}-${t.timestamp}`;

  const summary = data?.summary;
  const totalPages = data ? Math.max(1, Math.ceil(data.total_count / PAGE_SIZE)) : 1;

  const topChartData =
    summary?.top_prompts.map((t, i) => ({
      name: `#${i + 1} ${t.prompt.slice(0, 24)}${t.prompt.length > 24 ? '…' : ''}`,
      fullPrompt: t.prompt.slice(0, 120),
      total_tokens: t.total_tokens,
    })) ?? [];

  return (
    <div className="prompt-analysis-page">
      {preview && <SendPreview payload={preview} onCancel={() => setPreview(null)} onConfirm={() => { analyzeInsights(preview); setPreview(null); }} />}
      <h1>プロンプト別トークン分析</h1>
      <p className="pt-description">
        取得済みのローカル履歴を時系列でプロンプトに推定帰属しています。子エージェントは収集し、親が特定できない消費は未帰属にします。並列作業等は誤って帰属される場合があります。合計はInput・Output・Cache Creation・Cache Readの合算です。
      </p>

      {/* Period Selector */}
      <div className="period-selector">
        {[7, 14, 30].map((d) => (
          <button
            key={d}
            className={days === d ? 'active' : ''}
            onClick={() => changePeriod(d)}
          >
            過去{d}日間
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="loading-container">
          <div className="spinner"></div>
          <p className="loading-text">プロンプト別の消費データを集計中...</p>
        </div>
      ) : isError ? (
        <div className="error-container">
          <h3>エラーが発生しました</h3>
          <p>{error instanceof Error ? error.message : 'データの取得に失敗しました'}</p>
        </div>
      ) : data && summary ? (
        <>
          {/* Summary Cards */}
          <div className="pt-summary-grid">
            <div className="pt-summary-card">
              <h3>プロンプト数</h3>
              <p className="pt-summary-value">{formatNumber(summary.total_prompts)}</p>
              <p className="pt-summary-label">うちコマンド {summary.command_prompts}</p>
            </div>
            <div className="pt-summary-card">
              <h3>平均トークン</h3>
              <p className="pt-summary-value">{formatNumber(Math.round(summary.avg_tokens_per_prompt))}</p>
              <p className="pt-summary-label">中央値 {formatNumber(Math.round(summary.median_tokens_per_prompt))}</p>
            </div>
            <div className="pt-summary-card">
              <h3>最大消費</h3>
              <p className="pt-summary-value">{formatNumber(summary.max_tokens_per_prompt)}</p>
              <p className="pt-summary-label">p90 {formatNumber(Math.round(summary.p90_tokens_per_prompt))}</p>
            </div>
            <div className="pt-summary-card">
              <h3>帰属分の参考コスト</h3>
              <p className="pt-summary-value cost">{formatCost(summary.total_cost_usd)}</p>
              <p className="pt-summary-label">設定したAPI単価による参考額。請求額ではありません</p>
            </div>
            <div className="pt-summary-card">
              <h3>帰属率</h3>
              <p className="pt-summary-value score">{summary.attribution_coverage_pct == null ? "不明" : `${summary.attribution_coverage_pct.toFixed(1)}%`}</p>
              <p className="pt-summary-label">
                取得済みデータ内の未帰属 {formatNumber(summary.unattributed_tokens)} トークン。取得漏れや帰属の正確性は含みません。
              </p>
            </div>
          </div>

          {/* Charts */}
          <div className="pt-charts-row">
            <div className="pt-chart-container">
              <h2>消費上位プロンプト Top {topChartData.length}</h2>
              {topChartData.length > 0 ? (
                <ResponsiveContainer width="100%" height={Math.max(240, topChartData.length * 36)}>
                  <BarChart data={topChartData} layout="vertical" margin={{ left: 8, right: 24 }}>
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                    <XAxis type="number" tickFormatter={(v: number) => v.toLocaleString()} />
                    <YAxis type="category" dataKey="name" width={220} tick={{ fontSize: 12 }} />
                    <Tooltip
                      formatter={(value) => [Number(value).toLocaleString(), 'トークン']}
                      labelFormatter={(_, payload) => payload?.[0]?.payload?.fullPrompt ?? ''}
                    />
                    <Bar dataKey="total_tokens" name="トークン" fill="#8884d8" isAnimationActive={false} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <p className="pt-empty">データがありません</p>
              )}
            </div>
            <div className="pt-chart-container">
              <h2>消費量の分布（プロンプト数）</h2>
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={summary.histogram}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="label" tick={{ fontSize: 12 }} />
                  <YAxis allowDecimals={false} />
                  <Tooltip formatter={(value) => [value, 'プロンプト数']} />
                  <Bar dataKey="count" name="プロンプト数" fill="#82ca9d" isAnimationActive={false} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Comprehensive Table */}
          <div className="pt-table-section">
            <div className="pt-table-header">
              <h2>取得済みプロンプト一覧（{formatNumber(data.total_count)}件）</h2>
              <label className="pt-checkbox">
                <input
                  type="checkbox"
                  checked={includeCommands}
                  onChange={(e) => {
                    setIncludeCommands(e.target.checked);
                    setPage(0);
                  }}
                />
                スラッシュコマンドを含める
              </label>
            </div>
            <div className="pt-table-container">
              <table>
                <thead>
                  <tr>
                    <th className="sortable" onClick={() => changeSort('timestamp')}>
                      日時{sortIndicator('timestamp')}
                    </th>
                    <th>プロジェクト</th>
                    <th>プロンプト</th>
                    <th className="sortable num" onClick={() => changeSort('total_tokens')}>
                      トークン{sortIndicator('total_tokens')}
                    </th>
                    <th className="sortable num" onClick={() => changeSort('output_tokens')}>
                      Output{sortIndicator('output_tokens')}
                    </th>
                    <th className="num">
                      コスト
                    </th>
                    <th className="sortable num" onClick={() => changeSort('tool_use_count')}>
                      ツール{sortIndicator('tool_use_count')}
                    </th>
                    <th className="sortable num" onClick={() => changeSort('duration_seconds')}>
                      記録上の経過時間{sortIndicator('duration_seconds')}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {data.turns.map((t) => {
                    const key = turnKey(t);
                    const expanded = expandedKey === key;
                    return (
                      <Fragment key={key}>
                        <tr
                          className={`pt-row ${expanded ? 'expanded' : ''}`}
                          onClick={() => setExpandedKey(expanded ? null : key)}
                        >
                          <td className="nowrap">{formatTimestamp(t.timestamp)}</td>
                          <td className="nowrap">{t.project ?? '-'}</td>
                          <td className="pt-prompt-cell">
                            {t.is_command && <span className="pt-badge">cmd</span>}
                            {t.prompt.slice(0, 80)}
                            {t.prompt.length > 80 ? '…' : ''}
                          </td>
                          <td className="num">{formatNumber(t.total_tokens)}</td>
                          <td className="num">{formatNumber(t.output_tokens)}</td>
                          <td className="num">{formatCost(t.estimated_cost_usd)}</td>
                          <td className="num">{t.tool_use_count}</td>
                          <td className="num nowrap">{formatDuration(t.duration_seconds)}</td>
                        </tr>
                        {expanded && (
                          <tr className="pt-detail-row">
                            <td colSpan={8}>
                              <div className="pt-detail">
                                <pre className="pt-full-prompt">{t.prompt}</pre>
                                {t.prompt_length > t.prompt.length && (
                                  <p className="pt-truncated-note">
                                    （全{formatNumber(t.prompt_length)}文字中、先頭{formatNumber(t.prompt.length)}文字を表示）
                                  </p>
                                )}
                                <div className="pt-detail-grid">
                                  <div><span>Input</span>{formatNumber(t.input_tokens)}</div>
                                  <div><span>Output</span>{formatNumber(t.output_tokens)}</div>
                                  <div><span>Cache Creation</span>{formatNumber(t.cache_creation_tokens)}</div>
                                  <div><span>Cache Read</span>{formatNumber(t.cache_read_tokens)}</div>
                                  <div><span>アシスタント応答</span>{t.assistant_messages}回</div>
                                  <div><span>ツール実行</span>{t.tool_use_count}回</div>
                                  <div><span>記録上の経過時間</span>{formatDuration(t.duration_seconds)}</div>
                                  <div><span>セッション</span>{t.session_id.slice(0, 8)}…</div>
                                </div>
                                {!t.is_command && (
                                  <button
                                    className="pt-improve-btn"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      navigate('/advice', { state: { prompt: t.prompt, projectPath: t.project_path } });
                                    }}
                                  >
                                    ✏️ このプロンプトを改善する
                                  </button>
                                )}
                              </div>
                            </td>
                          </tr>
                        )}
                      </Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <div className="pt-pagination">
              <button disabled={page === 0} onClick={() => setPage(page - 1)}>
                ← 前へ
              </button>
              <span>
                {page + 1} / {totalPages} ページ
              </span>
              <button disabled={page + 1 >= totalPages} onClick={() => setPage(page + 1)}>
                次へ →
              </button>
            </div>
          </div>

          {/* AI Insights */}
          <div className="pt-insights-section">
            <div className="pt-insights-header">
              <h2>🤖 AI分析：高消費パターンと改善提案</h2>
              <button
                className="pt-insights-button"
                onClick={() => fetchInsights()}
                disabled={insightsLoading}
              >
                {insightsLoading ? '分析中...' : insights ? '再分析する' : 'AI分析を実行'}
              </button>
            </div>

            {insightsLoading ? (
              <div className="loading-container">
                <div className="spinner"></div>
                <p className="loading-text">消費上位プロンプトを分析中...</p>
              </div>
            ) : insightsError || previewError ? (
              <div className="error-container">
                <p>AI分析に失敗しました。OpenAI APIキーの設定を確認してください。</p>
              </div>
            ) : insights ? (
              <div className="pt-insights-body">
                <div className="pt-insight-block">
                  <h3>💸 トークン消費が多いプロンプトのパターン</h3>
                  <ul>
                    {insights.high_cost_patterns.map((item, i) => (
                      <li key={i}><Bilingual text={item} /></li>
                    ))}
                  </ul>
                </div>

                {insights.efficiency_observations.length > 0 && (
                  <div className="pt-insight-block">
                    <h3>🔍 利用状況に関する観察</h3>
                    <ul>
                      {insights.efficiency_observations.map((item, i) => (
                        <li key={i}><Bilingual text={item} /></li>
                      ))}
                    </ul>
                  </div>
                )}

                <div className="pt-insight-block">
                  <h3>💡 改善提案</h3>
                  <ul>
                    {insights.improvement_suggestions.map((item, i) => (
                      <li key={i}><Bilingual text={item} /></li>
                    ))}
                  </ul>
                </div>

                {insights.example_rewrites.length > 0 && (
                  <div className="pt-insight-block">
                    <h3>✏️ 実際のプロンプトの改善例</h3>
                    {insights.example_rewrites.map((ex, i) => (
                      <div key={i} className="pt-rewrite">
                        <div className="pt-rewrite-pair">
                          <div className="pt-rewrite-col original">
                            <h4>元のプロンプト</h4>
                            <pre>{ex.original}</pre>
                          </div>
                          <div className="pt-rewrite-col improved">
                            <h4>改善後</h4>
                            <pre>{ex.improved}</pre>
                          </div>
                        </div>
                        <p className="pt-rewrite-explanation">{ex.explanation_ja}</p>
                      </div>
                    ))}
                  </div>
                )}

                {insights.reflection && (
                  <div className="pt-insight-block">
                    <h3>📝 総合振り返り</h3>
                    <p className="pt-reflection">{insights.reflection}</p>
                  </div>
                )}
              </div>
            ) : (
              <p className="pt-insights-placeholder">
                「AI分析を実行」を押すと、消費上位プロンプトをLLMが分析し、
                高消費パターンの特定・改善提案・実プロンプトの書き換え例を表示します。
              </p>
            )}
          </div>
        </>
      ) : null}
    </div>
  );
}
