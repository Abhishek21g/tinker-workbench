# Tinker Workbench

Tinker Workbench is a local-first lab assistant for Thinking Machines-style post-training experiments. It plans runs, estimates cost/storage risk, executes mock or real integrations, records structured artifacts, and generates reproducible reports.

The first target is a clean mock implementation of the `tinker-project-ideas` memorization empirical study, then a path toward real Tinker Cookbook integration.

GitHub: https://github.com/Abhishek21g/tinker-workbench

## Quick Start

```bash
python3 -m tinker_workbench.cli plan configs/memorization_mock.yaml
python3 -m tinker_workbench.cli run configs/memorization_mock.yaml --mock
python3 -m tinker_workbench.cli report runs/latest
```

Read the active coordination docs:

- `agent/PROJECT_CONTEXT.md`
- `agent/EXECUTION_BOARD.md`
- `agent/GITHUB_CONTRIBUTION_TARGETS.md`
- `CURSOR.md`

Current task board:

- https://github.com/Abhishek21g/tinker-workbench/issues/1
- https://github.com/Abhishek21g/tinker-workbench/issues/2
- https://github.com/Abhishek21g/tinker-workbench/issues/3
