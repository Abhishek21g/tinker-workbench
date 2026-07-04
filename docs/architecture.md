# Architecture

Tinker Workbench is a local-first lab assistant for post-training experiments:
it plans a run before any tokens are spent, executes it with a full artifact
trail, and then observes, debugs, and evaluates from those artifacts alone.

```
config.yaml
    │  load_config() — typed schema, strict validation
    ▼
ExperimentConfig ──► planner.build_plan() ──► plan.json (tokens, cost, risks)
    │
    ▼
runner.execute_run()                      ← owns the loop, LR schedule,
    │                                        budget stops, artifact writing
    ├─► backends/  (TrainingBackend protocol)
    │     ├─ mock.py        deterministic simulator + failure injection
    │     ├─ local.py       REAL training: tiny char-level neural LM (numpy),
    │     │                 hand-derived gradients + Adam, real .npz checkpoints
    │     └─ tinker_api.py  real Tinker SDK adapter (LoRA client)
    │
    ├─► datasets.py   builtin:memorization or JSONL prompt/completion
    ├─► evals.py      graders run at every checkpoint via backend.sample()
    │
    ▼
runs/<run_id>/  config.json · plan.json · events.jsonl · metrics.jsonl
               checkpoints.jsonl · evals.jsonl · summary.json
    │
    ├─► store.RunStore     registry (runs/index.jsonl), latest symlink, loaders
    ├─► doctor.diagnose()  post-hoc failure analysis, severity-ranked findings
    ├─► compare.py         study-level table across runs
    └─► report.py          full markdown report (sparkline, reconciliation, diagnostics)
```

## Design decisions

**Backends are dumb, the runner is smart.** The `TrainingBackend` protocol is
five methods (`start`, `train_step`, `save_checkpoint`, `sample`, `close`).
Everything an experimenter cares about — schedules, budget enforcement, event
ordering, artifact shape — lives in the runner and is therefore identical
between mock and real runs. A workflow debugged for free against the mock
backend transfers unchanged to a paid Tinker run.

**Artifacts are the API.** `status`, `doctor`, `compare`, and `report` never
re-run anything; they only read the run directory. This makes them safe on
live, interrupted, and failed runs, and it means artifacts can be shared (or
committed) and analyzed elsewhere.

**Determinism by construction.** The mock backend derives every loss value and
sample from `(seed, step)` or `(seed, step, prompt)` — no hidden RNG state.
Identical config in, identical artifacts out; the test suite asserts this.

**Failure modes are first-class.** `mock.inject` can produce NaN losses,
divergence, stalls, and spikes at chosen steps. That is what lets `doctor`'s
rules be developed and regression-tested honestly instead of being untested
heuristics.

**The local backend is real training, not simulation.** A character-level MLP
language model (embedding → tanh → softmax, hand-derived gradients, Adam)
genuinely memorizes the study's bitstrings on your machine in under a second,
saves real weight files as checkpoints, and genuinely diverges when the
learning rate is too high (`configs/failure_divergence_local.yaml`). The
doctor and drift rules are therefore validated against true optimization
dynamics — chaotic Adam blow-ups included — before ever touching a paid run.

**Costs are planned, never invented.** The planner only computes dollar
estimates from rates the config owner supplies (`budget.usd_per_1m_*`);
pricing tables are not hardcoded because they go stale. Every plan is kept in
the run dir and reconciled against actuals in the report.

## The memorization study

`configs/memorization_{sft,rl_dense,rl_terminal}.yaml` implement the
tinker-project-ideas memorization empirical study workflow: identical data and
budgets, three training methods, `bits_recovered` and `exact_match` evals at
every checkpoint, and `compare` as the study-level readout. The mock
simulator's method-efficiency ordering (SFT > dense RL > terminal RL) is an
assumption to exercise the tooling, not a result; the same configs run against
the real backend once an API key is available.

## Real Tinker runs

`backends/tinker_api.py` maps the protocol onto the Tinker SDK's LoRA training
client (`forward_backward` + `optim_step` futures, `save_weights_for_sampler`,
sampling clients). It fails fast with actionable errors when the SDK or
`TINKER_API_KEY` is missing. It has not yet been exercised against the live
API from this machine; that is gated on an API key and explicit approval,
since it spends real money.
