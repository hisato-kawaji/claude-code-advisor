"""Versioned, evidence-limited guidance reviewed 2026-10-31.

Sources: https://code.claude.com/docs/en/best-practices
https://code.claude.com/docs/en/features-overview
https://code.claude.com/docs/en/monitoring-usage
"""
ADVICE_PERSPECTIVES = ["Specificity", "Verification", "Context", "Setup", "Delegation"]
CLAUDE_PROMPTING_KNOWLEDGE = """
Provide information Claude cannot discover, an appropriate way to verify work,
and deterministic controls for requirements that must always hold. A short
prompt may be sufficient; do not demand a plan, file paths or tests for every task.
CLAUDE.md, scoped rules, skills, hooks, MCP and subagents serve different purposes;
choose based on the task and do not assume any is universally preferable. Subagents
isolate context but may add total cost. Context compaction or a new session can
lose useful context. Cache-read totals are not context occupancy. High token use,
long duration or repeated messages do not alone prove waste, failure or causes.
A missing item in a sample does not establish it was absent in the actual workflow.
"""
DATA_SIGNAL_MAPPING = """Treat usage signals as observations, not causal evidence.
A suggestion to investigate must identify what further evidence is needed."""
