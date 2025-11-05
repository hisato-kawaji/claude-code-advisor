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
  score: number;
  passed_checks: string[];
  failed_checks: string[];
  recommendations: string[];
}

export interface PromptImprovement {
  original_prompt: string;
  improved_prompt: string;
  explanation: string;
  best_practice_references: string[];
}

export interface RecentPrompt {
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
  estimated_cost_usd: number;
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
