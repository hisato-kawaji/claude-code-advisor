export interface UsageStats {
  date: string;
  total_sessions: number;
  total_messages: number;
  total_input_tokens: number;
  total_output_tokens: number;
  cache_creation_tokens: number;
  cache_read_tokens: number;
}

export interface ComparisonStats {
  current: UsageStats;
  previous: UsageStats | null;
  change_percentage: Record<string, number> | null;
}

export interface PerformanceAnalysis {
  overall_score: number;
  task_completion_rate: number;
  avg_turns_per_task: number;
  error_rate: number;
  feedback: string;
  strengths: string[];
  areas_for_improvement: string[];
}

export interface BestPracticesCheck {
  score: number | null;
  passed_checks: string[];
  failed_checks: string[];
  recommendations: string[];
}

export interface PromptImprovement {
  original_prompt: string;
  improved_prompt: string;
  explanation?: string; // Deprecated: kept for backward compatibility
  explanation_en?: string;
  explanation_ja?: string;
  best_practice_references: string[];
}

export interface RecentPrompt {
  project_path: string | null;
  timestamp: string;
  prompt: string;
  session_id: string;
}

export interface TokenConsumptionSummary {
  total_input_tokens: number;
  total_output_tokens: number;
  total_tokens: number;
  cache_creation_tokens: number;
  cache_read_tokens: number;
  estimated_cost_usd: number | null;
  avg_tokens_per_session: number;
  avg_tokens_per_day: number;
  input_output_ratio: number;
}

export interface PromptImprovementExample {
  original: string;
  improved: string;
  explanation_en: string;
  explanation_ja: string;
}

export interface TokenEfficiencyAnalysis {
  efficiency_score: number;
  token_usage_pattern: string;
  most_token_intensive_activities: string[];
  cost_optimization_suggestions: string[];
  next_steps: string[];
  prompt_improvement_example?: PromptImprovementExample | null;
}

export interface TokenReflection {
  period_days: number;
  summary: TokenConsumptionSummary;
  analysis: TokenEfficiencyAnalysis;
  reflection: string;
}

export interface PromptTurn {
  session_id: string;
  project: string | null;
  project_path: string | null;
  timestamp: string;
  prompt: string;
  prompt_length: number;
  is_command: boolean;
  input_tokens: number;
  output_tokens: number;
  cache_creation_tokens: number;
  cache_read_tokens: number;
  total_tokens: number;
  estimated_cost_usd: number | null;
  assistant_messages: number;
  tool_use_count: number;
  duration_seconds: number;
}

export interface TokenHistogramBucket {
  label: string;
  count: number;
}

export interface PromptTokenSummary {
  total_prompts: number;
  command_prompts: number;
  total_tokens: number;
  total_cost_usd: number | null;
  avg_tokens_per_prompt: number;
  median_tokens_per_prompt: number;
  p90_tokens_per_prompt: number;
  max_tokens_per_prompt: number;
  attributed_tokens: number;
  unattributed_tokens: number;
  attribution_coverage_pct: number | null;
  histogram: TokenHistogramBucket[];
  top_prompts: PromptTurn[];
}

export interface PromptTokenAnalysis {
  period_days: number;
  summary: PromptTokenSummary;
  total_count: number;
  offset: number;
  limit: number;
  turns: PromptTurn[];
}

export interface PromptTokenInsights {
  period_days: number;
  analyzed_prompts: number;
  high_cost_patterns: string[];
  efficiency_observations: string[];
  improvement_suggestions: string[];
  example_rewrites: PromptImprovementExample[];
  reflection: string;
}

export interface HourlyUsage {
  hour: number;
  input_tokens: number;
  output_tokens: number;
  cache_creation_tokens: number;
  cache_read_tokens: number;
}

export interface SyncStatus {
  last_sync: string | null;
  total_entries: number;
  latest_data_date: string | null;
}

export interface CacheAdvice {
  start_date: string; end_date: string; timezone: string;
  totals: {input_tokens: number; output_tokens: number; cache_creation_tokens: number; cache_read_tokens: number};
  request_count: number; missing_request_ids: number; cache_read_share_of_input_pct: number | null;
  sources: {main: number; subagent: number; unknown: number};
  top_sessions: {session_id: string; source_kind: 'main' | 'subagent' | 'unknown'; request_count: number; cache_read_tokens: number; cache_creation_tokens: number; avg_cache_read_per_request: number}[];
  recommendations: {title: string; detail: string}[];
}
