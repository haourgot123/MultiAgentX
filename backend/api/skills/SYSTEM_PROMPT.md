# Agent Skill System — Claude CLI Sandbox

## Architecture

Skills are executed inside Docker sandbox containers using **Claude CLI** (`claude -p --dangerously-skip-permissions`).
Claude CLI runs in print mode with full autonomous permissions — no user confirmation needed.

## Sandbox Structure

```
/workspace/             → Working directory (rw)
/workspace/output/      → MANDATORY: All generated files saved here
/workspace/user_task.txt → User's task/prompt
/workspace/CLAUDE.md    → Project instructions (read by Claude CLI automatically)
/workspace/.claude/
    settings.json       → Claude CLI permissions config
    skills/             → Skill .md files (read by Claude CLI automatically)
/skill/                 → Original skill folder (read-only mount)
```

## Execution Flow

1. User selects skill(s) and types a task
2. Backend creates Docker container with:
   - Skill `.md` files copied to `/workspace/.claude/skills/`
   - User task written to `/workspace/user_task.txt`
   - `CLAUDE.md` with environment instructions
3. Claude CLI runs: `claude -p "<task>" --dangerously-skip-permissions --output-format stream-json`
4. Claude CLI reads skills from `~/.claude/skills/` automatically
5. Output streams back via SSE to frontend
6. Files in `/workspace/output/` are collected and made downloadable

## Key Points

- Claude CLI has **full autonomy** (`--dangerously-skip-permissions`) — safe because it runs inside an isolated Docker container
- Skills are placed in `~/.claude/skills/` so Claude CLI discovers them automatically
- Output format is `stream-json` for parseable streaming
- All generated files MUST go to `/workspace/output/`
- Container is destroyed after execution completes
