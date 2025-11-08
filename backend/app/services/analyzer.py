from openai import OpenAI
from typing import List, Dict
import json


BEST_PRACTICES = """
# Claude Code Best Practices (https://www.anthropic.com/engineering/claude-code-best-practices)

1. Customize Your Setup
- Create CLAUDE.md files documenting bash commands, code style guidelines, testing instructions, repository etiquette, and developer environment setup
- Place in repo root, parent directories, child directories, or home folder (~/.claude/CLAUDE.md)
- Keep concise and human-readable; treat like a frequently-used prompt requiring iteration
- Manage tool allowlist with /permissions command or settings.json
- Install gh CLI for GitHub integration

2. Enhance Claude's Capabilities
- Document custom bash tools with usage examples
- Direct Claude to run --help for documentation
- Configure Model Context Protocol (MCP) for extended functionality
- Create custom slash commands in .claude/commands folder with $ARGUMENTS keyword

3. Effective Workflows

a. Explore, Plan, Code, Commit
- Ask Claude to read relevant files without writing code yet
- Request a detailed plan (use "think" to trigger extended thinking)
- Have Claude implement the solution
- Ask to commit and create pull requests

b. Test-Driven Development
- Write tests based on expected inputs/outputs
- Confirm tests fail
- Commit the tests
- Have Claude implement code to pass tests
- Commit the passing code

c. Visual Iteration
- Provide browser screenshots (via Puppeteer MCP or manual copy/paste)
- Share visual design mocks
- Have Claude implement designs and iterate until matches

4. Workflow Optimization
- Be Specific: Provide clear, detailed instructions upfront to reduce course corrections
- Use Images: Paste screenshots (macOS: cmd+ctrl+shift+4, then ctrl+v), drag and drop, or provide file paths
- Reference Files: Use tab-completion to quickly reference files or folders
- Provide URLs: Paste specific URLs and add domains to allowlist with /permissions
- Course Correct Early: Ask for a plan before coding, press Escape to interrupt, double-tap Escape to explore alternatives
- Use /clear Command: Reset context window between tasks to maintain performance
- Checklists and Scratchpads: Use Markdown files or GitHub issues for large, multi-step tasks
- Data Input: Copy/paste, pipe data (cat foo.txt | claude), have Claude pull via bash/MCP, or ask Claude to read files/URLs

5. Multi-Claude Workflows
- Run parallel verification: one Claude writes code, another reviews
- Create multiple git checkouts or use git worktrees for parallel tasks
- Use headless mode (-p flag) for automation in CI, pre-commit hooks, and build scripts

6. Safety First
- Conservative permission defaults protect your system
- Only use --dangerously-skip-permissions in isolated containers
- Always review Claude's work
"""


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
        prompt = f"""
Based on Claude Code best practices, analyze these user interactions and provide results in both English and Japanese:

Best Practices Reference:
{BEST_PRACTICES}

Sample User Messages:
{json.dumps(sample_messages[:10], indent=2)}

Evaluate how well the user follows best practices. Return JSON with:
- score (0-100)
- passed_checks (array of strings, each in "English\\n日本語" format - English on first line, Japanese translation on second line)
- failed_checks (array of strings, each in "English\\n日本語" format - English on first line, Japanese translation on second line)
- recommendations (array of strings, each in "English\\n日本語" format - English on first line, Japanese translation on second line)
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
        prompt = f"""
As an expert in Claude Code usage following official best practices (https://www.anthropic.com/engineering/claude-code-best-practices), improve this user prompt and provide bilingual explanations:

Original prompt:
"{original_prompt}"

Claude Code Best Practices Reference:
{BEST_PRACTICES}

Analyze the original prompt and provide an improved version that:
1. Is more specific and actionable (e.g., "create a login form" → "create a React login form with email/password fields, validation, and submit button")
2. Follows the "Explore, Plan, Code, Commit" workflow when appropriate (e.g., "First read the existing auth files, then create a plan for the login feature")
3. References specific files or paths when relevant (e.g., "Update src/components/Auth.tsx")
4. Uses clear, structured instructions (e.g., numbered steps or bullet points)
5. Includes relevant context about the project or requirements
6. Suggests using images/screenshots for visual tasks
7. Recommends /clear if switching between unrelated tasks
8. Breaks large tasks into checklists when appropriate

Return JSON with:
- improved_prompt (the complete improved version with all enhancements)
- explanation_en (detailed explanation in English of why these changes improve the prompt, referencing specific best practices)
- explanation_ja (detailed explanation in Japanese of why these changes improve the prompt, referencing specific best practices)
- best_practice_references (array of strings, each in "English\\n日本語" format - English on first line, Japanese translation on second line. For example: ["Be Specific\\n具体的に指示する", "Explore, Plan, Code, Commit\\n探索、計画、コード、コミットのワークフロー"])
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
