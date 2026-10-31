import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './e2e', fullyParallel: false, workers: 1, retries: 0,
  use: { baseURL: 'http://localhost:18766', browserName: 'chromium', headless: true },
  webServer: { command: 'node e2e/server.mjs', url: 'http://localhost:18766', timeout: 30000, reuseExistingServer: false },
});
