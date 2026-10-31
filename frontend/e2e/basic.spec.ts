import { test, expect } from '@playwright/test';

const api = 'http://localhost:18765';

test('sync, child attribution, privacy preview, settings, and telemetry', async ({ page, request }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: '使用状況', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'データを同期' }).click();
  const sync = await request.post(`${api}/api/stats/sync`);
  expect((await sync.json()).subagent_files).toBe(1);
  const stats = await (await request.get(`${api}/api/analysis/prompt-tokens?days=7`)).json();
  expect(stats.summary.unattributed_tokens).toBe(1500);
  expect(stats.turns[0].total_tokens).toBe(1500);
  await page.reload();
  await expect(page.locator('.ov-kpi-card').filter({ hasText: 'キャッシュ読み込み' })).toContainText('400');
  await expect(page.locator('.ov-kpi-card').filter({ hasText: '総処理トークン' })).toContainText('3,000');

  await page.getByRole('link', { name: /設定とテレメトリー/ }).click();
  await page.getByLabel('契約').selectOption('api');
  await page.getByRole('button', { name: '単価入力例を表示' }).click();
  const rates = JSON.parse(await page.getByLabel('モデルごとの単価表').inputValue());
  rates[0].valid_from = '2000-01-01';
  await page.getByLabel('モデルごとの単価表').fill(JSON.stringify(rates));
  await page.getByLabel('追加でマスクする文字列').fill('example-secret');
  await page.getByRole('button', { name: '設定を保存' }).click();
  await expect(page.getByText('設定を保存しました。')).toBeVisible();
  const priced = await (await request.get(`${api}/api/analysis/prompt-tokens?days=7`)).json();
  expect(priced.turns[0].estimated_cost_usd).toBeCloseTo(0.006435, 6);
  await page.getByRole('link', { name: /改善アドバイス/ }).click();
  const cacheSection = page.getByRole('region', { name: 'キャッシュ利用の振り返り' });
  await expect(cacheSection).toContainText('改善候補と確認方法');
  await expect(cacheSection).toContainText('子エージェント 200');
  await page.getByPlaceholder('ここにプロンプトを入力または貼り付け...').fill('Contact alice@example.com with example-secret');
  await page.getByRole('button', { name: 'このプロンプトを改善' }).click();
  const dialog = page.getByRole('dialog');
  await expect(dialog).toContainText('[REDACTED EMAIL]');
  await expect(dialog).not.toContainText('alice@example.com');
  await expect(dialog).not.toContainText('example-secret');
  await dialog.getByRole('button', { name: 'キャンセル' }).click();
  let sentPrompt = '';
  await page.route('**/api/analysis/improve-prompt', async route => {
    const body = route.request().postDataJSON();
    sentPrompt = body.prompt;
    expect(body.consent).toBe(true);
    await route.fulfill({ json: { original_prompt: body.prompt, improved_prompt: 'Improved', best_practice_references: [] } });
  });
  await page.getByRole('button', { name: 'このプロンプトを改善' }).click();
  await dialog.getByRole('button', { name: '確認して送信' }).click();
  await expect(page.getByText('Improved', { exact: true })).toBeVisible();
  expect(sentPrompt).not.toContain('alice@example.com');
  expect(sentPrompt).not.toContain('example-secret');

  const body = {resourceLogs: [{scopeLogs: [{logRecords: [{attributes: [
    {key: 'event.name', value: {stringValue: 'api_request'}},
    {key: 'event.timestamp', value: {stringValue: '2026-10-31T00:00:00Z'}},
    {key: 'model', value: {stringValue: 'claude-sonnet-4-6'}},
    {key: 'prompt', value: {stringValue: 'should-never-be-stored'}}
  ]}]}]}]};
  expect((await request.post(`${api}/v1/logs`, {data: body})).status()).toBe(403);
  for (let i = 0; i < 2; i++) expect((await request.post(`${api}/v1/logs`, {headers: {Authorization: 'Bearer e2e-token'}, data: body})).ok()).toBeTruthy();
  const telemetry = await (await request.get(`${api}/api/telemetry/summary`)).json();
  expect(telemetry.counts.api_request).toBe(1);
  await page.getByRole('link', { name: /設定とテレメトリー/ }).click();
  await expect(page.getByText(/APIリクエスト: 1/)).toBeVisible();
});
