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
