# Upstream Collaboration Plan

Updated: 2026-07-04

## Target 1: Tinker Cookbook Cost And Usage Visibility

Issues:

- `thinking-machines-lab/tinker-cookbook#551`
- `thinking-machines-lab/tinker-cookbook#781`
- `thinking-machines-lab/tinker-cookbook#298`

Why this is the first lane:

- Users are already asking for usage, balance, cost, and checkpoint storage visibility.
- Adjacent tools exist (`tinkpad`, `tinker-cost`), so Workbench should add a report/export layer rather than another TUI.
- A concrete JSON report shape can help upstream discussions before any server-side API is public.

Prototype command:

```bash
python3 -m tinker_workbench.cli collab \
  --target tinker-cookbook-cost \
  --run-dir runs/latest
```

## Target 2: Tinker Checkpoint Probe

Issues:

- `thinking-machines-lab/tinker#44`
- `thinking-machines-lab/tinker#25`
- `thinking-machines-lab/tinker#41`

Why this matters:

- Tinker users need to know if checkpoints can actually serve before they spend time on evals.
- A JSON checkpoint probe result fits Workbench reports and CI.
- This is a cleaner technical PR target than broad billing questions because much of it can be client-side.

Prototype command:

```bash
python3 -m tinker_workbench.cli collab \
  --target tinker-checkpoint-probe \
  --run-dir runs/latest
```

## Posting Rule

Do not post upstream comments until the prototype command output is included and the user explicitly approves the public comment.

