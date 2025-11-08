from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class UsageStats(BaseModel):
    date: str
    total_sessions: int
    total_messages: int
    total_input_tokens: int
    total_output_tokens: int
    cache_creation_tokens: int
    cache_read_tokens: int


class ComparisonStats(BaseModel):
    current: UsageStats
    previous: Optional[UsageStats]
    change_percentage: Optional[dict]


class PerformanceAnalysis(BaseModel):
    overall_score: float
    task_completion_rate: float
    avg_turns_per_task: float
    error_rate: float
    feedback: str
    strengths: list[str]
    areas_for_improvement: list[str]


class BestPracticesCheck(BaseModel):
    score: float
    passed_checks: list[str]
    failed_checks: list[str]
    recommendations: list[str]


class PromptImprovement(BaseModel):
    original_prompt: str
    improved_prompt: str
    explanation: str
    best_practice_references: list[str]


class TokenConsumptionSummary(BaseModel):
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    cache_creation_tokens: int
    cache_read_tokens: int
    estimated_cost_usd: float
    avg_tokens_per_session: float
    avg_tokens_per_day: float
    input_output_ratio: float


class PromptImprovementExample(BaseModel):
    original: str
    improved: str
    explanation_en: str
    explanation_ja: str


class TokenEfficiencyAnalysis(BaseModel):
    efficiency_score: float
    token_usage_pattern: str
    most_token_intensive_activities: list[str]
    cost_optimization_suggestions: list[str]
    next_steps: list[str]
    prompt_improvement_example: PromptImprovementExample | None = None


class TokenReflection(BaseModel):
    period_days: int
    summary: TokenConsumptionSummary
    analysis: TokenEfficiencyAnalysis
    reflection: str


class HourlyUsage(BaseModel):
    hour: int
    input_tokens: int
    output_tokens: int


class HourlyUsageResponse(BaseModel):
    data: list[HourlyUsage]
