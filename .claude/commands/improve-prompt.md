---
description: 最近のプロンプトを改善提案する
---

You are helping the user improve their Claude Code prompts using the analytics backend.

## Task

1. First, fetch the recent prompts from the analytics API:
   ```bash
   curl -s http://localhost:8000/api/analysis/recent-prompts?limit=10
   ```

2. Display the recent prompts to the user in a numbered list, showing:
   - Prompt number (for selection)
   - First 100 characters of the prompt
   - Timestamp

3. Ask the user which prompt they want to improve (or if they want to enter a custom prompt).

4. Once the user selects a prompt or provides a custom one, call the improve-prompt API:
   ```bash
   curl -s -X POST "http://localhost:8000/api/analysis/improve-prompt?prompt=<URL_ENCODED_PROMPT>"
   ```

5. Parse the JSON response and display:
   - **Original Prompt**: The prompt that was analyzed
   - **Improved Prompt**: The suggested improvement
   - **Reasoning**: Why the improvements were suggested
   - **Best Practice References**: Links or notes to Claude best practices

## Important Notes

- Make sure to URL-encode the prompt before sending it to the API
- Handle any API errors gracefully and inform the user
- The analytics backend must be running (docker-compose up)
- Display the results in a clear, well-formatted manner

## Example Output Format

```
Recent Prompts:
1. [2025-10-30 15:30] "Write a function to calculate..."
2. [2025-10-30 14:20] "Help me debug this error..."
...

Which prompt would you like to improve? (1-10, or type 'custom' for a new prompt)
```

After user selection:

```
## Original Prompt
[original prompt text]

## Improved Prompt
[improved prompt text]

## Reasoning
[explanation of improvements]

## Best Practice References
[relevant best practices]
```
