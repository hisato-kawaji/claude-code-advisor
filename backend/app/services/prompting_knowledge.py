"""Claude Code プロンプティング・ベストプラクティスのナレッジ（LLM分析用）。

公式ドキュメントに比重を置いて整理したもの。人間向けの日本語版と
ソース一覧は docs/claude-prompting-best-practices.md を参照。

Sources (weighted):
- [Official] https://code.claude.com/docs/en/best-practices  (canonical, 2026)
- [Official] https://code.claude.com/docs/en/costs#reduce-token-usage
- [Official] https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices
- [Community, supplementary] 2026 practitioner articles

最終調査日: 2026-07-17
"""

# アドバイス観点の一覧。AI分析の指摘・提案はこのラベルで分類する
ADVICE_PERSPECTIVES = [
    "Specificity",        # タスクの具体性とスコープ
    "Workflow",           # Explore → Plan → Code → Commit の段階分離
    "Verification",       # 検証手段の提供
    "Context Hygiene",    # /clear・/compact・訂正ループ回避
    "Rich Input",         # @ファイル参照・画像・URL・パイプ
    "Delegation",         # サブエージェント委譲・並列化
    "Setup",              # CLAUDE.md・skills・hooks・CLIツール
    "Cost Efficiency",    # モデル選択・thinking・インクリメンタル
    "Communication",      # 明確さ・理由の提示・例示
]

CLAUDE_PROMPTING_KNOWLEDGE = """
# Claude Code Prompting Best Practices (official-weighted, current as of 2026)

FOUNDING CONSTRAINT (official): "Most best practices are based on one constraint:
Claude's context window fills up fast, and performance degrades as it fills."
Token-consumption problems almost always trace back to managing this constraint.

## 1. Specificity — task scoping [Official]
- Reference specific files, scenarios, constraints, and expected output.
  Before: "add tests for foo.py" / After: "write a test for foo.py covering the
  edge case where the user is logged out. avoid mocks."
- Bug reports: give the symptom + likely location + definition of "fixed".
  Before: "fix the login bug" / After: "users report login fails after session
  timeout. check src/auth/, especially token refresh. write a failing test that
  reproduces it, then fix."
- Point to existing patterns: "look at how existing widgets are implemented;
  HotDogWidget.php is a good example. follow that pattern."
- Vague prompts are acceptable only for open-ended exploration, never for
  implementation instructions.
- Token impact: "improve this codebase" triggers broad scanning; "add input
  validation to the login function in auth.ts" needs minimal file reads.

## 2. Workflow — explore, plan, code, commit [Official]
- Separate research/planning from implementation (plan mode). Jumping straight
  to code risks solving the wrong problem = expensive rework.
- BUT don't over-apply: "If you could describe the diff in one sentence, skip
  the plan." Planning pays off when the approach is uncertain, multiple files
  change, or the code is unfamiliar.
- For larger features: have Claude interview you first and write a SPEC, then
  execute the spec in a FRESH session with clean context.

## 3. Verification — give Claude a check it can run [Official]
- "Give Claude a check it can run: tests, a build, a screenshot to compare.
  It's the difference between a session you watch and one you walk away from."
- Include verification criteria in the prompt (example inputs/outputs, "run the
  tests after implementing").
- Ask for evidence, not claims of success: test output, the command run and its
  result, screenshots.
- Address root causes: "the build fails with this error: [paste]. fix it and
  verify the build succeeds. address the root cause, don't suppress the error."
- Without a check, the human becomes the verification loop — every mistake
  costs another correction turn (more tokens).

## 4. Context Hygiene [Official]
- /clear between unrelated tasks. The "kitchen sink session" (mixing unrelated
  tasks) degrades performance and wastes tokens on every subsequent message.
- "If you've corrected Claude more than twice on the same issue, run /clear and
  start fresh with a more specific prompt that incorporates what you learned.
  A clean session with a better prompt almost always outperforms a long session
  with accumulated corrections."
- /compact <instructions> to control what survives summarization.
- Unscoped investigation ("look into X") reads hundreds of files (infinite
  exploration). Scope it narrowly or delegate to subagents.
- Course-correct early: Esc to stop, /rewind to restore a checkpoint. Letting
  Claude continue down a wrong path is the biggest token waste.
- Very large cache_read on a turn suggests a long-running session that was
  never cleared.

## 5. Rich Input [Official]
- Reference files with @ instead of describing where code lives.
- Paste screenshots/images directly (especially UI work).
- Give documentation URLs.
- Pipe data in: cat error.log | claude.
- Point to the source that can answer: "look through ExecutionFactory's git
  history and summarize how its api came to be."

## 6. Delegation [Official; community agrees]
- Delegate research that reads many files to subagents; only summaries return
  to the main conversation. One of the most powerful context-saving tools.
- Delegate verbose operations (test runs, log processing, doc fetching) too.
- Review with fresh context: Writer/Reviewer pattern, adversarial review
  subagent ("report gaps, not style preferences").
- [Community] Focused subagents outperform bloated all-purpose ones.

## 7. Setup — persistent environment [Official]
- CLAUDE.md: keep it short (aim under 200 lines). For each line ask "would
  removing this cause Claude to make mistakes?" Bloated CLAUDE.md files cause
  Claude to ignore your actual instructions.
- Move workflow-specific knowledge to skills (loaded on demand, keeps base
  context small).
- Use hooks for actions that must happen every time (deterministic, unlike
  advisory CLAUDE.md instructions).
- Prefer CLI tools (gh, aws, gcloud) over MCP servers — more context-efficient.

## 8. Cost Efficiency [Official]
- Match the model to the job: Sonnet for most coding; reserve the top model for
  complex architecture; haiku for simple subagent tasks.
- Tune extended-thinking effort to task complexity.
- Test incrementally: write one file, test it, continue — catches issues while
  they're cheap.
- [Community] Treat tokens/duration/session complexity as design constraints,
  not afterthoughts.

## 9. Communication fundamentals [Official platform docs]
- Be clear and direct. Think of Claude as a brilliant but brand-new employee.
- Golden rule: "Show your prompt to a colleague with minimal context and ask
  them to follow it. If they'd be confused, Claude will be too."
- Explain WHY behind instructions — Claude generalizes from the motivation.
- Use numbered steps when order/completeness matters.
- Use 3-5 examples to lock output format/tone.

## Official failure patterns (anti-patterns)
- Kitchen sink session → /clear between tasks.
- Correcting over and over → after two failed corrections, /clear + a better
  initial prompt.
- Over-specified CLAUDE.md → ruthlessly prune.
- Trust-then-verify gap → always provide verification; if you can't verify it,
  don't ship it.
- Infinite exploration → scope investigations or use subagents.
"""

# トークン帰属データ上のシグナルと観点のマッピング（AI分析の判断材料）
DATA_SIGNAL_MAPPING = """
# How to read per-prompt token-attribution signals (map observations to perspectives)

- Short/vague prompt + high total tokens + high tool_use_count
  → broad scanning triggered (Specificity, Context Hygiene)
- Continuation prompts ("続きをやって", "continue") with heavy consumption
  → forced re-exploration; the prompt should restate scope/files (Specificity, Workflow)
- Several similar corrective prompts in the same session
  → correction loop / polluted context; should /clear + better prompt (Context Hygiene)
- A turn with disproportionately large cache_read tokens
  → long session carried over without /clear (Context Hygiene)
- Progression like "できた？" / "直して" with no verification criteria anywhere
  → the human is the verification loop (Verification)
- Research-style prompts consuming heavily in the main conversation
  → should be delegated to subagents (Delegation)
- One prompt bundling multiple unrelated requests
  → kitchen sink (Context Hygiene)
- Task instructions that never mention file paths
  → Claude pays exploration cost to locate targets (Specificity, Rich Input)
- High assistant_messages + long duration on a simple-sounding ask
  → under-specified acceptance criteria (Specificity, Verification)
"""
