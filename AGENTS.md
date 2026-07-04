# Codex Project Instructions

## Mission

Help build this project with small, correct, verified changes. Read the project context before making decisions.

Start by reading:

- `agent/PROJECT_CONTEXT.md`
- `agent/WORKFLOW.md`
- `agent/TOOL_REGISTRY.md`
- relevant source files

## Working Agreements

- Inspect files before editing.
- Prefer existing project patterns over new abstractions.
- Keep edits focused on the current task.
- Do not overwrite user changes.
- Use `rg` for search when available.
- Explain tradeoffs when the path is ambiguous.
- Run relevant verification before finishing.

## Commands

```sh
# install
python3 -m pip install -e '.[dev]'

# dev
python3 -m tinker_workbench.cli --help

# test
python3 -m pytest

# lint
python3 -m ruff check .

# format
python3 -m ruff format .

# build/package
python3 -m build
```

## Verification

- Behavior change: run tests.
- Frontend change: run browser or screenshot verification when possible.
- TypeScript/JavaScript change: run lint/typecheck if configured.
- Dependency/config change: run build.
- If a check cannot run, say exactly why.

## Agent Stack

Use the project stack in this order:

1. `PROJECT_CONTEXT.md` for project intent.
2. `AGENTS.md` for Codex behavior.
3. Skills for repeatable workflows.
4. Subagents for parallel research, review, and tests.
5. MCP/tools for external systems.
6. Hooks for deterministic checks.
7. Evals/traces for quality improvement.

## Future Tools

When a new tool, agent, MCP server, plugin, or workflow becomes useful, add it to `agent/TOOL_REGISTRY.md` before relying on it.
