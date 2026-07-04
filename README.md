# Tinker Workbench

A local-first lab assistant for [Tinker](https://github.com/thinking-machines-lab/tinker)
post-training experiments: it **plans** a run before any tokens are spent,
**runs** it with a complete artifact trail, then **observes**, **debugs**, and
**evaluates** entirely from those artifacts.

```
plan ──► run ──► status / doctor / compare / report
tokens & cost      artifact trail       post-hoc, re-run nothing
```

- **Plan before you pay.** Token, checkpoint-storage, and cost estimates plus
  a risk list, from the same config that runs the experiment.
- **Every run leaves a trail.** Ordered events, per-step metrics, checkpoints,
  eval scores, and a final summary — enough to debug or reproduce any run.
- **`doctor` finds the failure.** NaN losses, divergence, stalls, checkpoint
  gaps, budget overruns, and eval regressions, each with a suggested action
  and a CI-friendly exit code.
- **Deterministic mock backend.** Develop and test the whole workflow (with
  injectable failure modes) without spending Tinker credits; the real SDK
  adapter implements the same five-method protocol.
- **Reliability layer.** Pin a blessed run as a `baseline`, re-run it later,
  and `drift` flags regressions (loss, evals, cost) with CI exit codes —
  recipe-regression testing for post-training. `conformance` catches silent
  renderer mismatches (token-exact, adversarial probe corpus) before a
  distillation run wastes money.

## Quick start

```bash
python3 -m venv .venv && .venv/bin/pip install -e . pyyaml
source .venv/bin/activate

# 1. Plan: tokens, storage, cost, risks — nothing runs yet
tinker-workbench plan configs/memorization_sft.yaml

# 2. Run the three-arm memorization study (mock backend, deterministic)
tinker-workbench run configs/memorization_sft.yaml \
                     configs/memorization_rl_dense.yaml \
                     configs/memorization_rl_terminal.yaml

# 3. Compare the arms
tinker-workbench compare runs/*memorization*

# 4. Full report for one run
tinker-workbench report latest
```

Debugging workflow:

```bash
tinker-workbench run configs/failure_divergence.yaml
tinker-workbench doctor latest
# [CRITICAL] loss_divergence: Loss is diverging: best 1.2743 around step 15, ...
#     -> Lower training.learning_rate or switch lr_schedule to cosine/linear decay ...
```

Real Tinker runs use the same configs with `mode: tinker` (or `--backend
tinker`) and require the `tinker` SDK plus `TINKER_API_KEY`.

## The memorization study

The shipped configs implement the workflow for the
[tinker-project-ideas](https://github.com/thinking-machines-lab/tinker-project-ideas)
memorization empirical study: identical data and budget across SFT, dense-reward
RL, and terminal-reward RL arms, with `bits_recovered` and `exact_match`
evals at every checkpoint and `compare` as the study readout.

## Docs

- [docs/commands.md](docs/commands.md) — full command reference
- [docs/architecture.md](docs/architecture.md) — design and rationale
- [docs/upstream-collab.md](docs/upstream-collab.md) — Tinker upstream collaboration targets

## Development

```bash
.venv/bin/pip install -e . pytest ruff pyyaml
pytest tests/ -q       # 61 tests
ruff check tinker_workbench/ tests/
```

CI runs lint, tests, and a CLI smoke test on Python 3.11–3.13.

Project coordination lives in `agent/EXECUTION_BOARD.md` and the
[issue tracker](https://github.com/Abhishek21g/tinker-workbench/issues).
