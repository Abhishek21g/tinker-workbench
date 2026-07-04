# Tinker Workbench Progress Report - 2026-07-04

## Goal

Build a Thinking Machines-native artifact that makes us useful before anyone
asks: upstream fixes where they already work, plus a Tinker Workbench product
that plans, runs, observes, debugs, compares, and reports post-training
experiments.

## What We Built

- Created and pushed `tinker-workbench`, a local-first lab assistant for Tinker
  experiments.
- Implemented the core loop: `plan`, `run`, `status`, `doctor`, `compare`, and
  `report`.
- Added reliability tooling: baselines, drift checks, and renderer conformance
  checks for recipe regression testing.
- Added a real no-credit `local` backend: a tiny character-level neural LM that
  trains with Adam, writes real checkpoints, and exposes genuine loss/eval
  dynamics through the same Workbench protocol as the mock and Tinker backends.
- Started the memorization empirical study from `tinker-project-ideas` using
  Workbench configs and artifacts.

## Upstream PRs

| Repo | PR | Contribution | Current status |
| --- | --- | --- | --- |
| `thinking-machines-lab/tinker-cookbook` | [#798](https://github.com/thinking-machines-lab/tinker-cookbook/pull/798) | Add `TrainingRunStore.summarize()` for lightweight run artifact summaries | CI green, review required |
| `thinking-machines-lab/tinker` | [#48](https://github.com/thinking-machines-lab/tinker/pull/48) | Return JSON for empty checkpoint delete results | Open, mergeable |
| `thinking-machines-lab/batch_invariant_ops` | [#25](https://github.com/thinking-machines-lab/batch_invariant_ops/pull/25) | Correct Python version metadata to match 3.10 syntax | Open, mergeable |
| `thinking-machines-lab/tinker-cookbook` | [#799](https://github.com/thinking-machines-lab/tinker-cookbook/pull/799) | Skip blank lines when reading JSONL files | CI green, review required |

We also left a focused review comment on
[`tinker-cookbook#797`](https://github.com/thinking-machines-lab/tinker-cookbook/pull/797#issuecomment-4881621904)
with the exact CI failures and fix direction.

## Memorization Study Snapshot

Initial runs compared the local real-neural backend against deterministic mock
SFT/RL arms:

Run ids:

- `20260704T184217Z-memorization-local`
- `20260704T184225Z-memorization-sft`
- `20260704T184226Z-memorization-rl-dense`
- `20260704T184226Z-memorization-rl-terminal`

| Arm | Backend | Steps | Final loss | Best bits recovered | Best exact match |
| --- | --- | ---: | ---: | ---: | ---: |
| Local SFT | `local` | 200/200 | 0.0026 | 1.0000 | 1.0000 |
| Mock SFT | `mock` | 40/40 | 0.3819 | 0.9812 | 0.8438 |
| Mock dense reward RL | `mock` | 40/40 | 0.7330 | 0.9281 | 0.5000 |
| Mock terminal reward RL | `mock` | 40/40 | 1.2702 | 0.8719 | 0.2812 |

The local SFT run is the most important signal: it proves Workbench can produce
a real training artifact, not just simulated dashboards. That gives us a cheap
way to develop reports, doctor findings, and regression checks before spending
Tinker credits.

## Why This Matters

- The upstream PRs are small, concrete, and easy to review.
- The Workbench product is aligned with Tinker: it wraps post-training into a
  reproducible lab loop instead of a generic assistant.
- The memorization study creates a public research artifact that can evolve
  into a real Tinker API experiment once access and budget are available.

## Next Moves

1. Watch `tinker-cookbook#798` and `#799`, then respond quickly to review.
2. Do not ping `#798` yet; add a short follow-up only if it sits for a few days.
3. Turn the memorization snapshot into a cleaner report with charts and exact
   run artifacts.
4. Run the same Workbench config with `mode: tinker` once API access is ready.
5. Keep looking for small, real `tinker-cookbook` PRs because that repo has the
   best external-contributor review path.
