# Command Reference

All commands accept a run reference where noted: a run directory path, a run id
under `runs/`, or the literal `latest`.

## `plan <config.yaml>`

Validates the config and prints the pre-run plan as JSON: planned train/sample
tokens, checkpoint count and storage estimate, cost estimate (when pricing
rates are supplied in `budget`), and a list of risks. Nothing is executed.

## `run <config.yaml> [more configs...] [--backend mock|tinker] [--quiet]`

Executes each config in order and records the full artifact trail per run:

| artifact | contents |
|---|---|
| `config.json` | the resolved experiment config |
| `plan.json` | the pre-run plan, kept for reconciliation |
| `events.jsonl` | ordered lifecycle events (start, steps, checkpoints, evals, completion/failure) |
| `metrics.jsonl` | per-step loss, learning rate, token counts |
| `checkpoints.jsonl` | saved checkpoints and sampler readiness |
| `evals.jsonl` | eval scores per checkpoint |
| `summary.json` | final status, totals, wall time |

The run stops early with status `failed` on non-finite loss, or
`stopped_budget` when `budget.max_train_tokens` is hit. Exit code is 2 if any
run failed.

`--backend` overrides the config's `mode`. The `tinker` backend requires the
`tinker` SDK and `TINKER_API_KEY`.

## `runs [--limit N]`

Lists recorded runs with method, status, steps, and final loss.

## `status <run>`

Shows the current state of a run. Works on interrupted runs (no
`summary.json` yet) by falling back to the metrics tail.

## `doctor <run> [--json]`

Post-hoc diagnostics. Detects, among others:

- `non_finite_loss` — NaN/inf loss (critical)
- `loss_divergence` — tail of the loss curve well above the best loss and rising (critical)
- `insufficient_progress` / `plateau_second_half` — stalls and wasted steps
- `loss_spike` — transient instability
- `no_checkpoints` / `checkpoint_gap` — unsaved progress, resume risk
- `token_overrun` — actual usage exceeded the plan
- `eval_regression` — best checkpoint is not the final one

Each finding carries a suggested action. Exit code is 2 when any critical
finding is present, so it can gate CI or scripts.

## `eval` behavior

Evals run automatically at every checkpoint during `run`, using the eval set
defined by `data` and the graders in `evals` (`exact_match`, `contains`,
`regex`, `bits_recovered`).

## `compare <run> <run> ...`

Markdown table across runs: status, steps, final loss, train tokens, and best
score per eval, plus a per-eval leaderboard. This is the study-level view —
e.g. the three memorization arms side by side.

## `report <run> [--out PATH]`

Full markdown experiment report: summary, loss sparkline, eval table,
checkpoints, plan-vs-actual budget reconciliation, doctor diagnostics, and a
reproduce section.

## `collab --target tinker-cookbook-cost|tinker-checkpoint-probe [--run-dir RUN]`

Exports the upstream-facing proposal JSON shapes used in our collaboration
with the Tinker repos.
