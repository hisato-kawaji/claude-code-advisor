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
