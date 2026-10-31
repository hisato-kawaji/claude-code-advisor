import { useEffect, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { settingsApi, type AppSettings, type Rate } from '../api';
import './SettingsPage.css';

const example: Rate = { model: 'claude-sonnet-4-6', provider: 'anthropic', valid_from: '2026-10-31', valid_until: null, input: 3, output: 15, cache_read: 0.3, cache_write_5m: 3.75, cache_write_1h: 6 };

export function SettingsPage() {
  const queryClient = useQueryClient();
  const settings = useQuery({ queryKey: ['settings'], queryFn: async () => (await settingsApi.get()).data });
  const telemetry = useQuery({ queryKey: ['telemetry'], queryFn: async () => (await settingsApi.telemetry()).data, refetchOnMount: 'always' });
  const [form, setForm] = useState<AppSettings | null>(null);
  const [rates, setRates] = useState('[]');
  const [message, setMessage] = useState('');
  useEffect(() => { if (settings.data) { setForm(settings.data); setRates(JSON.stringify(settings.data.rates, null, 2)); } }, [settings.data]);
  const save = async () => {
    if (!form) return;
    try {
      const parsed: unknown = JSON.parse(rates);
      if (!Array.isArray(parsed)) throw new Error('単価表は配列にしてください');
      await settingsApi.save({ ...form, rates: parsed as Rate[], excluded_projects: form.excluded_projects.filter(x => x.trim()), redact_literals: form.redact_literals.filter(x => x.trim()) });
      await queryClient.invalidateQueries();
      setMessage('設定を保存しました。');
    } catch { setMessage('保存できませんでした。単価表、日付、項目を確認してください。'); }
  };
  if (!form) return <p>{settings.isError ? '設定を読み込めませんでした。' : '読み込み中...'}</p>;
  return <div className="settings-page">
    <h1>設定とテレメトリー</h1>
    <h2>費用の参考計算</h2>
    <p>単価はUSD／100万トークン。適用期間・モデルID・プロバイダーが一致するAPI利用のみ計算します。契約割引・特別料金・税・請求額は含みません。条件不明、単価重複、キャッシュ書き込みのTTL不明時は不明です。</p>
    <label>契約 <select value={form.contract} onChange={e => setForm({ ...form, contract: e.target.value as AppSettings['contract'] })}>
      <option value="unknown">不明</option><option value="api">API従量課金（参考換算）</option><option value="subscription">定額プラン</option>
    </select></label>
    {form.contract === 'subscription' && <label>定額プランの月額（USD・任意）<input type="number" min="0" step="0.01" value={form.monthly_subscription_usd ?? ''} onChange={e => setForm({ ...form, monthly_subscription_usd: e.target.value === '' ? null : Number(e.target.value) })} /></label>}
    {form.contract === 'subscription' && <p>定額月額: {form.monthly_subscription_usd == null ? '未設定' : `$${form.monthly_subscription_usd.toFixed(2)} / 月`}。作業ごとの費用には配分しません。追加課金は含みません。</p>}
    <label>プロバイダー <input value={form.provider} onChange={e => setForm({ ...form, provider: e.target.value })} /></label>
    <label>モデルごとの単価表（JSON）<textarea aria-label="モデルごとの単価表" rows={10} value={rates} onChange={e => setRates(e.target.value)} /></label>
    <button type="button" onClick={() => setRates(JSON.stringify([example], null, 2))}>単価入力例を表示</button>
    <p>入力例は2026-10-31確認時点の参考です。モデルID、期間と実際の契約単価を確認してください。<a href="https://platform.claude.com/docs/en/about-claude/pricing" target="_blank" rel="noreferrer">公式料金</a></p>
    <h2>外部AIへの送信</h2>
    <p>履歴分析から除外するプロジェクトのパスまたは名前を1行ずつ指定します（* 使用可）。対象が特定できない履歴も除外します。手入力したプロンプトは対象外です。メール・主なキー類と下記の文字列は送信前にマスクされますが、すべての機密情報を検出できるわけではありません。</p>
    <label>除外プロジェクト<textarea aria-label="除外プロジェクト" rows={4} value={form.excluded_projects.join('\n')} onChange={e => setForm({ ...form, excluded_projects: e.target.value.split('\n') })} /></label>
    <label>追加でマスクする文字列<textarea aria-label="追加でマスクする文字列" rows={4} value={form.redact_literals.join('\n')} onChange={e => setForm({ ...form, redact_literals: e.target.value.split('\n') })} /></label>
    <button type="button" onClick={save}>設定を保存</button> <span role="status">{message}</span>
    <h2>OpenTelemetry</h2>
    <p>OTLP HTTP/JSON のログを任意で受け取ります。プロンプト本文とツール内容は保存しません。ローカル履歴とは別集計です。設定方法はREADMEを参照してください。</p>
    <p>受信: {telemetry.data?.enabled ? '有効' : '無効'} / APIリクエスト: {telemetry.data?.counts.api_request ?? 0} / プロンプトイベント: {telemetry.data?.counts.user_prompt ?? 0}</p>
    <p>OTLPトークン（Input / Output / Cache Read / Cache Write）: {['input_tokens', 'output_tokens', 'cache_read_tokens', 'cache_creation_tokens'].map(k => telemetry.data?.totals[k]?.toLocaleString() ?? '不明').join(' / ')}。OTLP参考コスト: {telemetry.data?.totals.estimated_cost_usd == null ? '不明' : `$${telemetry.data.totals.estimated_cost_usd.toFixed(4)}`}（請求額ではありません）</p>
    {telemetry.data?.models.map(m => <p key={m.model}>{m.model}: {m.requests}件</p>)}
  </div>;
}
