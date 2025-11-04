from openai import OpenAI
from typing import List, Dict
import json


BEST_PRACTICES = """
# Claude Code Best Practices

1. Customize Your Setup
- Create CLAUDE.md files with bash commands, code style, and setup instructions
- Keep content concise and iterate on effectiveness
- Curate allowed tools through settings

2. Use bash tools effectively
- Explain tool names and usage
- Run --help for documentation

3. Recommended Workflows
a. Explore, Plan, Code, Commit
- Read relevant files first
- Use "think" modes for deeper analysis
- Create a plan before coding
- Implement solution
- Commit and create pull request

b. Test-Driven Development
- Write tests first
- Confirm tests fail
- Commit tests
- Implement code to pass tests

c. Visual Iteration
- Take screenshots
- Provide visual mocks
- Implement design
- Iterate with screenshots

4. Optimization Techniques
- Be specific in instructions
- Use images and URLs for context
- Mention specific files to work on
- Course-correct early
- Use /clear to maintain context focus
- Use checklists for complex tasks

5. Safety
- Be cautious with --dangerously-skip-permissions
- Prefer containerized environments
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
As an expert in Claude Code usage, improve this user prompt:

Original prompt:
"{original_prompt}"

Best Practices to consider:
{BEST_PRACTICES}

Provide an improved version that:
1. Is more specific and actionable
2. Follows Claude Code best practices
3. Includes relevant context
4. Uses clear, structured instructions

Return JSON with:
- improved_prompt (the improved version)
- explanation (why these changes improve the prompt)
- best_practice_references (which best practices apply)
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
