import axios from 'axios';
import type { ComparisonStats, PerformanceAnalysis, BestPracticesCheck, PromptImprovement, RecentPrompt, TokenReflection, HourlyUsage, PromptTokenAnalysis, PromptTokenInsights, SyncStatus } from './types';

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
    api.get<{ history: any[] }>('/api/stats/history/daily', { params: { days } }),

  getWeeklyHistory: (weeks: number = 26) =>
    api.get<{ history: any[] }>('/api/stats/history/weekly', { params: { weeks } }),

  getMonthlyHistory: (months: number = 12) =>
    api.get<{ history: any[] }>('/api/stats/history/monthly', { params: { months } }),

  syncDatabase: () =>
    api.post<{ status: string; inserted: number; skipped: number; total_entries: number }>('/api/stats/sync'),

  getSyncStatus: () =>
    api.get<SyncStatus>('/api/stats/sync-status'),
};

export const analysisApi = {
  getPerformance: (days: number = 7) =>
    api.get<PerformanceAnalysis>('/api/analysis/performance', { params: { days } }),

  getBestPractices: (days: number = 7) =>
    api.get<BestPracticesCheck>('/api/analysis/best-practices', { params: { days } }),

  improvePrompt: (prompt: string) =>
    api.post<PromptImprovement>('/api/analysis/improve-prompt', null, { params: { prompt } }),

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

  getPromptTokenInsights: (days: number = 7) =>
    api.get<PromptTokenInsights>('/api/analysis/prompt-tokens/insights', { params: { days } }),
};
