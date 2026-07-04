# Claude Project Memory

## Mission

Help build this project with careful context gathering, small changes, and real verification.

At the start of a session, read:

- `agent/PROJECT_CONTEXT.md`
- `agent/WORKFLOW.md`
- `agent/TOOL_REGISTRY.md`
- relevant source files

## Workflow

1. Understand the user request.
2. Inspect the relevant files.
3. Make a short plan for substantial work.
4. Edit the smallest useful surface area.
5. Run the relevant checks.
6. Summarize changes and residual risk.

## Preferences

- Prefer evidence from files, tests, docs, logs, and command output.
- Do not invent project architecture.
- Do not add dependencies unless clearly justified.
- Avoid unrelated cleanup.
- Promote repeated instructions into skills.
- Add durable project lessons to the appropriate project file.

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

## Quality Bar

A task is done when the implementation, verification, and explanation all match the requested outcome.
