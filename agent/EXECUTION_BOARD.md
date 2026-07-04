# Execution Board

Updated: 2026-07-04

## Sprint Rule

Work continuously in small verified slices. Split work between Codex and Cursor by ownership, not by both editing the same file at once.

## Shared Workspace

Use this folder as the single shared place:

```text
/Users/enaguthiabhishek/Documents/tinker
```

Open this exact folder in Cursor. Codex is already operating here.

GitHub source of truth:

```text
https://github.com/Abhishek21g/tinker-workbench
```

Shared issue board:

- `#1` Build plan/run/report CLI into real Workbench core.
- `#2` Prepare upstream collaboration path for Tinker checkpoint/cost tooling.
- `#3` Implement memorization empirical study simulator.

## Agent Ownership

### Codex Lane

- Own product/research architecture.
- Own CLI core and Python package structure.
- Own mock Tinker experiment runner.
- Own generated reports.
- Own upstream issue/PR research.

### Cursor Lane

- Own UI/dashboard only after CLI contracts exist.
- Own README polish, screenshots, demo script, and visual presentation.
- Own small frontend/static report improvements.
- Avoid editing `agent/PROJECT_CONTEXT.md` unless coordinating.

## Immediate Priority Order

1. Create real package skeleton for `tinker_workbench`.
2. Implement `plan` command against a local YAML config.
3. Implement mock `run` command that writes structured run artifacts.
4. Implement `report` command that turns run artifacts into markdown.
5. Scaffold memorization empirical study experiment.
6. Pick one upstream contribution target and prepare a comment/PR.

## First Product Slice

Command shape:

```bash
tinker-workbench plan configs/memorization_mock.yaml
tinker-workbench run configs/memorization_mock.yaml --mock
tinker-workbench report runs/latest
```

Required output artifacts:

- `runs/<run_id>/config.json`
- `runs/<run_id>/plan.json`
- `runs/<run_id>/events.jsonl`
- `runs/<run_id>/metrics.jsonl`
- `runs/<run_id>/checkpoints.jsonl`
- `reports/<run_id>.md`

## Parallel Work Rules

- Before editing a shared file, check `git status --short`.
- Keep commits/slices small.
- Generated run outputs should be ignored unless intentionally captured as a demo fixture.
- Upstream repos in `upstream/` are reference clones; do not treat them as product source.
- When using real Tinker API or paid resources, ask first.

## Current Product Thesis

Tinker Workbench should make post-training runs observable, reproducible, and debuggable. It should look like something a Tinker research infrastructure or developer experience engineer would want internally.
