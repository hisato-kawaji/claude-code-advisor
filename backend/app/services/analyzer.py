from openai import OpenAI
from typing import List, Dict
import json

from .prompting_knowledge import (
    CLAUDE_PROMPTING_KNOWLEDGE,
    DATA_SIGNAL_MAPPING,
    ADVICE_PERSPECTIVES,
)

# 全LLM分析が参照するベストプラクティス。公式ドキュメント比重で整理した
# 最新ナレッジ（prompting_knowledge.py / docs/claude-prompting-best-practices.md）
BEST_PRACTICES = CLAUDE_PROMPTING_KNOWLEDGE


class ClaudeAnalyzer:
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def analyze_performance(self, stats: Dict, sample_messages: List[str]) -> Dict:
        """統計データからパフォーマンスを分析（最適化版）"""
        total_sessions = stats.get("total_sessions", 0)
        user_messages_count = stats.get("user_messages", 0)
        assistant_messages_count = stats.get("assistant_messages", 0)

        # エラー率を推定（0.05 = 5%をデフォルトとする）
        error_count = int(assistant_messages_count * 0.05)

        # LLMに分析を依頼
        prompt = f"""
Analyze the following Claude Code usage statistics and provide feedback in both English and Japanese:

Total Sessions: {total_sessions}
Total User Messages: {user_messages_count}
Total Assistant Messages: {assistant_messages_count}
Detected Errors: {error_count}

Recent user messages (sample):
{json.dumps(sample_messages[:5], indent=2)}

Please provide:
1. An overall performance score (0-100)
2. Task completion rate estimate
3. Average communication quality
4. Error handling effectiveness
5. Top 3 strengths (each in "English\\n日本語" format - English on first line, Japanese translation on second line)
6. Top 3 areas for improvement (each in "English\\n日本語" format - English on first line, Japanese translation on second line)
7. Specific feedback and actionable advice in Japanese

Return your analysis in JSON format with these keys:
- overall_score (float)
- task_completion_rate (float)
- avg_turns_per_task (float)
- error_rate (float)
- feedback (string in Japanese)
- strengths (array of strings, each with "English\\n日本語" format)
- areas_for_improvement (array of strings, each with "English\\n日本語" format)
"""

        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )

        try:
            # レスポンスからJSONを抽出
            content = response.choices[0].message.content
            # JSONブロックを探す
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0].strip()
            else:
                json_str = content.strip()

            analysis = json.loads(json_str)
            return analysis
        except:
            # パース失敗時のフォールバック
            return {
                "overall_score": 70.0,
                "task_completion_rate": 0.8,
                "avg_turns_per_task": user_messages_count / max(total_sessions, 1),
                "error_rate": error_count / max(assistant_messages_count, 1),
                "feedback": "詳細な分析を生成できませんでした。APIキーを確認して再度お試しください。",
                "strengths": ["Using Claude Code regularly\nClaude Codeを定期的に使用"],
                "areas_for_improvement": ["Analysis unavailable\n分析データが利用できません"]
            }

    def check_best_practices(self, sample_messages: List[str]) -> Dict:
        """ベストプラクティスに沿っているかチェック（最適化版）"""
        perspectives = " / ".join(ADVICE_PERSPECTIVES)
        prompt = f"""
You are an expert in Claude Code usage. Evaluate how well the user follows best
practices. Your evaluation MUST be grounded in the official Anthropic best
practices reference below (official guidance takes priority over community lore).

<best_practices_reference>
{BEST_PRACTICES}
</best_practices_reference>

Advice perspectives (use these as category labels): {perspectives}

Sample User Messages:
{json.dumps(sample_messages[:10], indent=2, ensure_ascii=False)}

Evaluate the sample messages against the perspectives above. Ground every check
in what you can actually observe in the messages (quote or paraphrase them).
Prefix EVERY item in passed_checks / failed_checks / recommendations with its
perspective label in square brackets, e.g. "[Specificity] ...", using the same
label on both the English and Japanese lines. When a point comes from official
guidance, say so naturally.

Return JSON with:
- score (0-100)
- passed_checks (array of strings, each in "[Perspective] English\\n[Perspective] 日本語" format - English on first line, Japanese translation on second line)
- failed_checks (array of strings, each in "[Perspective] English\\n[Perspective] 日本語" format - English on first line, Japanese translation on second line)
- recommendations (array of strings, each in "[Perspective] English\\n[Perspective] 日本語" format - English on first line, Japanese translation on second line)
"""

        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )

        try:
            content = response.choices[0].message.content
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0].strip()
            else:
                json_str = content.strip()

            result = json.loads(json_str)
            return result
        except:
            return {
                "score": 60.0,
                "passed_checks": ["Basic usage\n基本的な使用"],
                "failed_checks": ["Analysis unavailable\n分析データが利用できません"],
                "recommendations": ["Enable API access for detailed analysis\n詳細な分析のためにAPIアクセスを有効にしてください"]
            }

    def suggest_prompt_improvements(self, original_prompt: str) -> Dict:
        """プロンプトの改善案を提案"""
        perspectives = " / ".join(ADVICE_PERSPECTIVES)
        prompt = f"""
You are an expert in Claude Code usage. Improve this user prompt and provide
bilingual explanations. Your improvements MUST be grounded in the official
Anthropic best practices reference below (official guidance takes priority over
community lore).

Original prompt:
"{original_prompt}"

<best_practices_reference>
{BEST_PRACTICES}
</best_practices_reference>

Advice perspectives (use these as category labels): {perspectives}

Analyze the original prompt and produce an improved version that applies the
relevant perspectives above. Depending on the prompt, this may mean: adding
scope and specific file paths (Specificity / Rich Input), separating explore
from implement (Workflow), adding verification criteria such as tests or
expected output (Verification), suggesting delegation to subagents for broad
investigation (Delegation), or recommending /clear when switching tasks
(Context Hygiene). Apply only what genuinely improves THIS prompt — do not
force irrelevant practices.

Return JSON with:
- improved_prompt (the complete improved version with all enhancements)
- explanation_en (detailed explanation in English of why these changes improve the prompt, naming the applied perspectives/official practices)
- explanation_ja (detailed explanation in Japanese of why these changes improve the prompt, naming the applied perspectives/official practices)
- best_practice_references (array of strings, each in "[Perspective] English\\n[Perspective] 日本語" format - English on first line, Japanese translation on second line. For example: ["[Specificity] Scope the task with specific files\\n[Specificity] 対象ファイルを明示してスコープを絞る", "[Verification] Give Claude a check it can run\\n[Verification] Claudeが実行できる検証手段を与える"])
"""

        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}]
        )

        try:
            content = response.choices[0].message.content
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0].strip()
            else:
                json_str = content.strip()

            result = json.loads(json_str)
            result["original_prompt"] = original_prompt
            return result
        except:
            return {
                "original_prompt": original_prompt,
                "improved_prompt": original_prompt,
                "explanation_en": "Unable to generate improvements. Please check API access.",
                "explanation_ja": "改善案を生成できませんでした。APIアクセスを確認してください。",
                "best_practice_references": []
            }

    def analyze_prompt_token_patterns(self, summary: Dict, top_turns: List[Dict], period_days: int) -> Dict:
        """プロンプト単位のトークン帰属データから、高消費パターンと改善示唆を分析"""
        # LLMに渡す上位消費ターンの要約（プロンプトは300文字に切り詰め）
        turns_payload = [
            {
                "prompt": t["prompt"][:300],
                "project": t.get("project"),
                "is_command": t["is_command"],
                "total_tokens": t["total_tokens"],
                "output_tokens": t["output_tokens"],
                "cache_read_tokens": t["cache_read_tokens"],
                "estimated_cost_usd": t["estimated_cost_usd"],
                "assistant_messages": t["assistant_messages"],
                "tool_use_count": t["tool_use_count"],
                "duration_seconds": t["duration_seconds"],
            }
            for t in top_turns
        ]

        perspectives = " / ".join(ADVICE_PERSPECTIVES)

        analysis_prompt = f"""
You are an expert in Claude Code usage. Your advice must be grounded in the
official Anthropic best practices reference below (official guidance takes
priority over community lore).
Below is per-prompt token attribution data: each user prompt is paired 1:1 with
ALL tokens consumed by the assistant turn it triggered (until the next user prompt).

Period statistics ({period_days} days):
- Total prompts: {summary['total_prompts']} (slash commands: {summary['command_prompts']})
- Total attributed tokens (input+output): {summary['total_tokens']:,}
- Total estimated cost: ${summary['total_cost_usd']:.2f} USD
- Tokens per prompt: avg={summary['avg_tokens_per_prompt']:,.0f}, median={summary['median_tokens_per_prompt']:,.0f}, p90={summary['p90_tokens_per_prompt']:,.0f}, max={summary['max_tokens_per_prompt']:,}
- Distribution: {json.dumps([(b['label'], b['count']) for b in summary['histogram']], ensure_ascii=False)}

Top token-consuming prompts (actual user prompts with their attributed consumption):
{json.dumps(turns_payload, indent=2, ensure_ascii=False)}

<best_practices_reference>
{BEST_PRACTICES}
</best_practices_reference>

<signal_mapping>
{DATA_SIGNAL_MAPPING}
</signal_mapping>

Advice perspectives (use these as category labels): {perspectives}

Analysis tasks:
- Ground EVERY finding in the actual prompts above (quote or paraphrase them).
- Use the signal mapping to connect what you see in the data (tool_use_count,
  cache_read, duration, assistant_messages) to the right perspective.
- Prefix EVERY item in tasks 1-3 with its perspective label in square brackets,
  e.g. "[Specificity] ..." — same label on both the English and Japanese lines.
- When a suggestion comes from official guidance, say so naturally (e.g. "the
  official docs recommend /clear between unrelated tasks").

1. high_cost_patterns: 3-5 patterns describing WHAT KINDS of prompts consumed the most
   tokens (e.g. vague continuation prompts like "続きをやって" forcing broad re-exploration,
   unscoped "read everything" requests, etc.). Each in "[Perspective] English\\n[Perspective] 日本語"
   format (English first line, Japanese second line).
2. efficiency_observations: 2-4 observations contrasting efficient vs inefficient prompts
   in this data (e.g. relation between prompt specificity and tool_use_count / tokens).
   Each in "[Perspective] English\\n[Perspective] 日本語" format.
3. improvement_suggestions: 3-5 actionable suggestions to reduce consumption, each tied to
   a specific OFFICIAL best practice AND to a pattern actually observed in this data.
   Cover different perspectives rather than repeating one. Each in
   "[Perspective] English\\n[Perspective] 日本語" format.
4. example_rewrites: pick up to 2 of the ACTUAL expensive prompts above and rewrite them
   applying the best practices (add scope/files, verification criteria, delegation hints
   as appropriate). Array of objects with keys: original (the actual prompt), improved
   (rewritten version in the same language as the original), explanation_en, explanation_ja
   (explanations must name the applied best practices).
5. reflection: a comprehensive 2-3 paragraph reflection in Japanese on how this user's
   prompting style drives token consumption and how to improve it, referencing the
   perspectives that matter most for this user.

Return JSON with keys:
- high_cost_patterns (array of strings)
- efficiency_observations (array of strings)
- improvement_suggestions (array of strings)
- example_rewrites (array of objects)
- reflection (string in Japanese)
"""

        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=4000,
            messages=[{"role": "user", "content": analysis_prompt}]
        )

        try:
            content = response.choices[0].message.content
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0].strip()
            else:
                json_str = content.strip()

            result = json.loads(json_str)

            rewrites = []
            for item in result.get("example_rewrites", []):
                if isinstance(item, dict) and item.get("original") and item.get("improved"):
                    rewrites.append({
                        "original": item["original"],
                        "improved": item["improved"],
                        "explanation_en": item.get("explanation_en", ""),
                        "explanation_ja": item.get("explanation_ja", ""),
                    })

            return {
                "period_days": period_days,
                "analyzed_prompts": len(top_turns),
                "high_cost_patterns": result.get("high_cost_patterns", []),
                "efficiency_observations": result.get("efficiency_observations", []),
                "improvement_suggestions": result.get("improvement_suggestions", []),
                "example_rewrites": rewrites,
                "reflection": result.get("reflection", ""),
            }
        except Exception as e:
            return {
                "period_days": period_days,
                "analyzed_prompts": len(top_turns),
                "high_cost_patterns": ["Analysis unavailable\n分析データを生成できませんでした"],
                "efficiency_observations": [],
                "improvement_suggestions": ["Check OpenAI API access\nOpenAI APIアクセスを確認してください"],
                "example_rewrites": [],
                "reflection": f"詳細な分析を生成できませんでした。エラー: {str(e)}",
            }

    def analyze_token_consumption(self, stats: Dict, sample_messages: List[str], period_days: int) -> Dict:
        """トークン消費を分析して振り返りを提供（最適化版）"""
        # 統計データから取得
        total_input = stats.get("total_input_tokens", 0)
        total_output = stats.get("total_output_tokens", 0)
        cache_creation = stats.get("cache_creation_tokens", 0)
        cache_read = stats.get("cache_read_tokens", 0)
        total_sessions = stats.get("total_sessions", 0)

        total_tokens = total_input + total_output

        # Claude Sonnet 3.5のコスト計算 (per million tokens)
        # Input: $3/MTok, Output: $15/MTok, Cache Write: $3.75/MTok, Cache Read: $0.30/MTok
        input_cost = (total_input / 1_000_000) * 3.0
        output_cost = (total_output / 1_000_000) * 15.0
        cache_write_cost = (cache_creation / 1_000_000) * 3.75
        cache_read_cost = (cache_read / 1_000_000) * 0.30
        total_cost = input_cost + output_cost + cache_write_cost + cache_read_cost

        # 統計値を計算
        avg_per_session = total_tokens / max(total_sessions, 1)
        avg_per_day = total_tokens / max(period_days, 1)
        io_ratio = total_output / max(total_input, 1)

        # サンプルメッセージから改善例を取得
        sample_prompt_for_improvement = None
        for msg in sample_messages:
            if len(msg.strip()) > 10 and len(msg.strip()) < 500:
                sample_prompt_for_improvement = msg.strip()
                break

        # LLMに分析を依頼
        analysis_prompt = f"""
Analyze this Claude Code token consumption data and provide insights:

Token Usage Statistics:
- Total Input Tokens: {total_input:,}
- Total Output Tokens: {total_output:,}
- Total Tokens: {total_tokens:,}
- Cache Creation Tokens: {cache_creation:,}
- Cache Read Tokens: {cache_read:,}
- Total Cost: ${total_cost:.2f} USD
- Period: {period_days} days
- Total Sessions: {total_sessions}
- Avg Tokens per Session: {avg_per_session:.1f}
- Avg Tokens per Day: {avg_per_day:.1f}
- Input/Output Ratio: {io_ratio:.2f}

Sample User Messages:
{json.dumps(sample_messages[:5], indent=2)}

{f'''
Sample Prompt for Improvement Example:
"{sample_prompt_for_improvement}"
''' if sample_prompt_for_improvement else ''}

Please provide a comprehensive reflection and analysis based on Claude Code Best Practices (https://www.anthropic.com/engineering/claude-code-best-practices):

Key Best Practices to Consider:
- Be Specific: Provide clear, detailed instructions upfront
- Use "Explore, Plan, Code, Commit" workflow: Ask Claude to read files first, request a plan, then implement
- Reference Files: Use tab-completion and file paths explicitly
- Use Images: Provide screenshots for visual tasks
- Course Correct Early: Ask for a plan before coding
- Use /clear: Reset context between unrelated tasks
- Provide URLs: Share specific documentation links
- Checklists: Break large tasks into steps
- CLAUDE.md: Document project-specific guidelines and commands

Analysis Tasks:

1. Efficiency Score (0-100): Rate how efficiently tokens are being used
2. Token Usage Pattern: Describe the overall pattern (e.g., "heavy batch processing", "frequent short interactions", etc.) in Japanese
3. Most Token-Intensive Activities: List 3-5 specific activities that consumed the most tokens. Each item should be in format "English description\n日本語の説明" (English on first line, Japanese translation on second line)
4. Cost Optimization Suggestions: Provide 3-5 actionable suggestions to reduce token consumption based on Claude Code best practices. Each item should be in format "English suggestion\n日本語の提案" (English on first line, Japanese translation on second line)
5. Next Steps: Provide 3-5 specific action items for improvement. Each item should be in format "English action\n日本語のアクション" (English on first line, Japanese translation on second line). {f'IMPORTANT: Include ONE specific example showing how to improve the sample prompt above following Claude Code best practices. Show the original prompt and an improved version with explanation.' if sample_prompt_for_improvement else ''}
6. Overall Reflection: A comprehensive 2-3 paragraph reflection on the token usage in Japanese, what went well, what could be improved, and specific recommendations

Return JSON with:
- efficiency_score (float 0-100)
- token_usage_pattern (string, in Japanese)
- most_token_intensive_activities (array of strings, each with "English\n日本語" format)
- cost_optimization_suggestions (array of strings, each with "English\n日本語" format)
- next_steps (array of strings, each with "English\n日本語" format)
- prompt_improvement_example (object with "original", "improved", "explanation_en", "explanation_ja" fields) if sample prompt exists, otherwise null
- reflection (string, the comprehensive reflection in Japanese)
"""

        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=4000,
            messages=[{"role": "user", "content": analysis_prompt}]
        )

        try:
            content = response.choices[0].message.content
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0].strip()
            else:
                json_str = content.strip()

            analysis_result = json.loads(json_str)

            # 完全なレスポンスを構築
            return {
                "period_days": period_days,
                "summary": {
                    "total_input_tokens": total_input,
                    "total_output_tokens": total_output,
                    "total_tokens": total_tokens,
                    "cache_creation_tokens": cache_creation,
                    "cache_read_tokens": cache_read,
                    "estimated_cost_usd": round(total_cost, 2),
                    "avg_tokens_per_session": round(avg_per_session, 1),
                    "avg_tokens_per_day": round(avg_per_day, 1),
                    "input_output_ratio": round(io_ratio, 2)
                },
                "analysis": {
                    "efficiency_score": analysis_result.get("efficiency_score", 70.0),
                    "token_usage_pattern": analysis_result.get("token_usage_pattern", "Moderate usage"),
                    "most_token_intensive_activities": analysis_result.get("most_token_intensive_activities", []),
                    "cost_optimization_suggestions": analysis_result.get("cost_optimization_suggestions", []),
                    "next_steps": analysis_result.get("next_steps", []),
                    "prompt_improvement_example": analysis_result.get("prompt_improvement_example")
                },
                "reflection": analysis_result.get("reflection", "Token usage analysis completed.")
            }
        except Exception as e:
            # フォールバック
            return {
                "period_days": period_days,
                "summary": {
                    "total_input_tokens": total_input,
                    "total_output_tokens": total_output,
                    "total_tokens": total_tokens,
                    "cache_creation_tokens": cache_creation,
                    "cache_read_tokens": cache_read,
                    "estimated_cost_usd": round(total_cost, 2),
                    "avg_tokens_per_session": round(avg_per_session, 1),
                    "avg_tokens_per_day": round(avg_per_day, 1),
                    "input_output_ratio": round(io_ratio, 2)
                },
                "analysis": {
                    "efficiency_score": 70.0,
                    "token_usage_pattern": "Standard usage pattern",
                    "most_token_intensive_activities": ["Code generation", "Analysis tasks"],
                    "cost_optimization_suggestions": ["Use more specific prompts", "Leverage context caching"],
                    "next_steps": ["Review high-token sessions", "Optimize prompt structure"],
                    "prompt_improvement_example": None
                },
                "reflection": f"Unable to generate detailed reflection. Error: {str(e)}"
            }
