import axios from 'axios';
import type { ComparisonStats, UsageStats, PerformanceAnalysis, BestPracticesCheck, PromptImprovement, RecentPrompt, TokenReflection, HourlyUsage, PromptTokenAnalysis, PromptTokenInsights, SyncStatus } from './types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
});

export const statsApi = {
  getDaily: (date?: string) =>
    api.get<ComparisonStats>('/api/stats/daily', { params: { date } }),

  getWeekly: (date?: string) =>
    api.get<ComparisonStats>('/api/stats/weekly', { params: { date } }),

  getMonthly: (date?: string) =>
    api.get<ComparisonStats>('/api/stats/monthly', { params: { date } }),

  getHourly: (date: string) =>
    api.get<HourlyUsage[]>('/api/stats/hourly', { params: { date } }),

  getDailyHistory: (days: number = 30) =>
    api.get<{ history: UsageStats[] }>('/api/stats/history/daily', { params: { days } }),

  getWeeklyHistory: (weeks: number = 26) =>
    api.get<{ history: UsageStats[] }>('/api/stats/history/weekly', { params: { weeks } }),

  getMonthlyHistory: (months: number = 12) =>
    api.get<{ history: UsageStats[] }>('/api/stats/history/monthly', { params: { months } }),

  syncDatabase: () =>
    api.post<{ status: string; inserted: number; skipped: number; invalid: number; malformed: number; files_processed: number; subagent_files: number; total_entries: number }>('/api/stats/sync'),

  getSyncStatus: () =>
    api.get<SyncStatus>('/api/stats/sync-status'),
};

export const analysisApi = {
  getPerformance: (days: number = 7) =>
    api.get<PerformanceAnalysis>('/api/analysis/performance', { params: { days } }),

  previewBestPractices: (days: number) =>
    api.get<{ prompt_excerpts: string[] }>('/api/analysis/best-practices/preview', { params: { days } }),

  getBestPractices: (prompt_excerpts: string[]) =>
    api.post<BestPracticesCheck>('/api/analysis/best-practices', { prompt_excerpts, consent: true }),

  previewPrompt: (prompt: string, project_path: string | null) =>
    api.post<{ prompt: string; project_path: string | null }>('/api/analysis/improve-prompt/preview', { prompt, project_path, consent: false }),

  improvePrompt: (prompt: string, project_path: string | null) =>
    api.post<PromptImprovement>('/api/analysis/improve-prompt', { prompt, project_path, consent: true }),

  getRecentPrompts: (limit: number = 10) =>
    api.get<{ prompts: RecentPrompt[] }>('/api/analysis/recent-prompts', { params: { limit } }),

  getTokenReflection: (days: number = 7) =>
    api.get<TokenReflection>('/api/analysis/token-reflection', { params: { days } }),

  getPromptTokens: (params: {
    days: number;
    sort?: string;
    order?: 'asc' | 'desc';
    limit?: number;
    offset?: number;
    include_commands?: boolean;
  }) =>
    api.get<PromptTokenAnalysis>('/api/analysis/prompt-tokens', { params }),

  previewPromptTokenInsights: (days: number) =>
    api.get<{ period_days: number; summary: Record<string, unknown>; turns: Record<string, unknown>[] }>('/api/analysis/prompt-tokens/insights/preview', { params: { days } }),

  getPromptTokenInsights: (data: { period_days: number; summary: Record<string, unknown>; turns: Record<string, unknown>[] }) =>
    api.post<PromptTokenInsights>('/api/analysis/prompt-tokens/insights', { ...data, consent: true }),
};

export interface Rate {
  model: string; provider: string; valid_from: string; valid_until: string | null;
  input: number; output: number; cache_read: number; cache_write_5m: number; cache_write_1h: number;
}
export interface AppSettings {
  contract: 'unknown' | 'api' | 'subscription'; monthly_subscription_usd: number | null; provider: string; rates: Rate[];
  excluded_projects: string[]; redact_literals: string[];
}
export const settingsApi = {
  get: () => api.get<AppSettings>('/api/settings'),
  save: (settings: AppSettings) => api.put<AppSettings>('/api/settings', settings),
  telemetry: () => api.get<{ enabled: boolean; counts: Record<string, number>; models: {model: string; requests: number}[]; totals: Record<string, number | null> }>('/api/telemetry/summary'),
};
