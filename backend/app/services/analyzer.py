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

    def analyze_performance(self, sessions: List[Dict]) -> Dict:
        """セッションデータからパフォーマンスを分析"""
        # セッションの基本統計を計算
        total_sessions = len(set(s.get("sessionId") for s in sessions if s.get("sessionId")))
        user_messages = [s for s in sessions if s.get("type") == "user"]
        assistant_messages = [s for s in sessions if s.get("type") == "assistant"]

        # エラーメッセージを検出
        error_count = 0
        for msg in assistant_messages:
            content = str(msg.get("message", {}).get("content", ""))
            if "error" in content.lower() or "failed" in content.lower():
                error_count += 1

        # LLMに分析を依頼
        prompt = f"""
Analyze the following Claude Code usage statistics and provide feedback:

Total Sessions: {total_sessions}
Total User Messages: {len(user_messages)}
Total Assistant Messages: {len(assistant_messages)}
Detected Errors: {error_count}

Recent user messages (sample):
{json.dumps([m.get("message", {}).get("content", "")[:200] for m in user_messages[:5]], indent=2)}

Please provide:
1. An overall performance score (0-100)
2. Task completion rate estimate
3. Average communication quality
4. Error handling effectiveness
5. Top 3 strengths
6. Top 3 areas for improvement
7. Specific feedback and actionable advice

Return your analysis in JSON format with these keys:
- overall_score (float)
- task_completion_rate (float)
- avg_turns_per_task (float)
- error_rate (float)
- feedback (string)
- strengths (array of strings)
- areas_for_improvement (array of strings)
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
                "avg_turns_per_task": len(user_messages) / max(total_sessions, 1),
                "error_rate": error_count / max(len(assistant_messages), 1),
                "feedback": "Unable to generate detailed analysis. Please check your API key and try again.",
                "strengths": ["Using Claude Code regularly"],
                "areas_for_improvement": ["Analysis unavailable"]
            }

    def check_best_practices(self, sessions: List[Dict]) -> Dict:
        """ベストプラクティスに沿っているかチェック"""
        user_messages = [s for s in sessions if s.get("type") == "user"]

        # サンプルメッセージを取得
        sample_messages = []
        for msg in user_messages[:10]:
            content = msg.get("message", {})
            if isinstance(content, dict):
                content = content.get("content", "")
            sample_messages.append(str(content)[:300])

        prompt = f"""
Based on Claude Code best practices, analyze these user interactions:

Best Practices Reference:
{BEST_PRACTICES}

Sample User Messages:
{json.dumps(sample_messages, indent=2)}

Evaluate how well the user follows best practices. Return JSON with:
- score (0-100)
- passed_checks (array of best practices being followed)
- failed_checks (array of best practices not being followed)
- recommendations (array of specific actionable recommendations)
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
                "passed_checks": ["Basic usage"],
                "failed_checks": ["Analysis unavailable"],
                "recommendations": ["Enable API access for detailed analysis"]
            }

    def suggest_prompt_improvements(self, original_prompt: str) -> Dict:
        """プロンプトの改善案を提案"""
        prompt = f"""
As an expert in Claude Code usage following official best practices (https://www.anthropic.com/engineering/claude-code-best-practices), improve this user prompt:

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
- explanation (detailed explanation in English of why these changes improve the prompt, referencing specific best practices)
- best_practice_references (array of strings listing which specific best practices from the official guide apply, e.g., ["Be Specific", "Explore, Plan, Code, Commit", "Reference Files"])
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
                "explanation": "Unable to generate improvements. Please check API access.",
                "best_practice_references": []
            }

    def analyze_token_consumption(self, sessions: List[Dict], period_days: int) -> Dict:
        """トークン消費を分析して振り返りを提供"""
        # トークン統計を計算
        total_input = 0
        total_output = 0
        cache_creation = 0
        cache_read = 0
        session_ids = set()

        # セッションごとのトークン使用量を追跡
        session_tokens = {}

        for session in sessions:
            session_id = session.get("sessionId")
            if session_id:
                session_ids.add(session_id)
                if session_id not in session_tokens:
                    session_tokens[session_id] = 0

            if session.get("type") == "assistant":
                message = session.get("message", {})
                usage = message.get("usage", {})

                input_tokens = usage.get("input_tokens", 0)
                output_tokens = usage.get("output_tokens", 0)

                total_input += input_tokens
                total_output += output_tokens
                cache_creation += usage.get("cache_creation_input_tokens", 0)
                cache_read += usage.get("cache_read_input_tokens", 0)

                if session_id:
                    session_tokens[session_id] += input_tokens + output_tokens

        total_tokens = total_input + total_output
        total_sessions = len(session_ids)

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

        # トップ5のトークン消費セッションを取得
        top_sessions = sorted(session_tokens.items(), key=lambda x: x[1], reverse=True)[:5]

        # サンプルメッセージを取得（分析用）
        user_messages = []
        sample_prompt_for_improvement = None

        for session in sessions:
            if session.get("type") == "user":
                message = session.get("message", {})
                content = message.get("content", "")

                # contentが文字列の場合
                if isinstance(content, str) and len(content.strip()) > 10:
                    user_messages.append(content[:200])
                    # 改善例として使えそうなプロンプトを1つ保存
                    if not sample_prompt_for_improvement and len(content.strip()) < 500:
                        sample_prompt_for_improvement = content.strip()

                # contentがリストの場合
                elif isinstance(content, list):
                    # tool_resultを含むアイテムがあればスキップ
                    has_tool_result = any(
                        isinstance(item, dict) and item.get("type") == "tool_result"
                        for item in content
                    )
                    if has_tool_result:
                        continue

                    # textタイプのものを探す
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "text":
                            text = item.get("text", "")
                            if len(text.strip()) > 10:
                                user_messages.append(text[:200])
                                if not sample_prompt_for_improvement and len(text.strip()) < 500:
                                    sample_prompt_for_improvement = text.strip()
                                break

                if len(user_messages) >= 10:
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
{json.dumps(user_messages[:5], indent=2)}

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
