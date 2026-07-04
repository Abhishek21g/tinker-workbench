# Thinking Machines Lab Research And Build Strategy

Last researched: 2026-07-04

## Executive Read

Thinking Machines Lab is not just building another chatbot company. Their public thesis is:

- Make AI systems more widely understood, customizable, and generally capable.
- Move customization power from top labs to researchers and builders.
- Treat human-AI interaction as a first-class model capability, not a UI wrapper.
- Build infrastructure that makes model training, evaluation, and real-time collaboration practical.

The strongest "make them call me" project is not a generic Jarvis clone. It should be a Thinking Machines-native research/product artifact:

**Tinker Workbench: an interactive post-training lab assistant that plans, runs, observes, debugs, and evaluates Tinker fine-tuning experiments.**

This product would sit exactly between their public Tinker platform, their developer-experience hiring needs, their research-infrastructure hiring needs, and their interaction-model thesis.

## What They Publicly Care About

### 1. Tinker: training API for researchers

Tinker is their first public product. It lets researchers control model training and fine-tuning while Thinking Machines handles the infrastructure. The core API is intentionally small:

- `forward_backward`
- `optim_step`
- `sample`
- `save_state`

The public positioning is very clear: Tinker should let researchers focus on data, algorithms, environments, and evals instead of GPU orchestration.

Supported models include Qwen, GPT-OSS, DeepSeek, Kimi, and NVIDIA Nemotron variants, including large MoE models. Tinker uses LoRA and emphasizes flexible training over turnkey fine-tuning.

### 2. Tinker Cookbook: examples, recipes, and abstractions

The cookbook is the center of the public developer surface. It contains:

- supervised fine-tuning recipes
- RL recipes
- DPO and RLHF pipelines
- distillation recipes
- tool-use and retrieval RL
- multi-agent RL
- evaluation framework with GSM8K, MATH-500, MMLU-Pro, GPQA, MBPP, IFEval, AIME, and experimental benchmarks
- Claude Code skills for Tinker research/debug workflows

The design philosophy is low barrier to entry, extensible configs, sweep-friendly serialization, async RL environments, and research-friendly evaluation.

### 3. Interaction Models

Their 2026 interaction-model work argues that AI interfaces are currently bottlenecked by turn-based interaction. They want models that can continuously process audio, video, and text while responding in real time.

Key architectural ideas:

- time-aligned micro-turns, around 200ms chunks
- continuous input/output streams instead of rigid turns
- interaction model plus asynchronous background model
- shared context between real-time interaction and slower reasoning/tool-use work
- simultaneous tool calls, search, browsing, and generated UI while talking/listening

This is very close to a serious version of Jarvis, but their framing is not "personal assistant." It is **scalable human-AI collaboration**.

### 4. Determinism, numerics, and kernels

Their `batch_invariant_ops` repo supports work on defeating nondeterminism in LLM inference. It provides batch-invariant PyTorch kernels and a vLLM deterministic inference proof of concept.

Open issues reveal sharp systems problems:

- silent TF32 precision loss in matmul
- incompatibility with public PyTorch/Triton releases
- low matmul performance
- vLLM replication failures
- log_softmax determinism questions

This aligns strongly with low-level systems, numerics, GPU programming, and reproducibility.

### 5. Research Infrastructure

Their jobs explicitly call for people who build:

- evaluation libraries
- RL training libraries
- experiment tracking platforms
- visualization tools
- reproducibility, traceability, quality control
- monitoring and observability for research experiments
- high-throughput distributed evaluation and reward modeling pipelines

This is the highest-fit framing for a portfolio project.

## Public GitHub Map

| Repo | Role | Signal |
|---|---|---|
| `tinker` | Python SDK and CLI | Main product surface; open issues around checkpointing, endpoints, model support, rate limits |
| `tinker-cookbook` | recipes, evals, abstractions | Best contribution target; active, high stars, examples matter |
| `tinker-feedback` | public feedback tracker | User pain inventory; many product opportunities |
| `tinker-project-ideas` | official project suggestions | Research directions they want to see |
| `batch_invariant_ops` | deterministic inference kernels | Strong systems/GPU/numerics fit |
| `manifolds` | modular manifolds research code | Optimizer/math research artifact |
| `redis-rs` | fork | Likely infra dependency, lower public signal |

## Open Pain Points From Issues

High-signal problems:

- Need account-level usage and balance query via API/CLI.
- Need better org-level spend controls, especially checkpoint storage spend.
- Need checkpoint probing to verify sampler readiness.
- Checkpoint deletion performance and argument handling have issues.
- OpenAI-compatible endpoints have LoRA/checkpoint/model edge cases.
- Sampler checkpoints can hang or serve base models instead of adapters.
- Model support/documentation mismatch creates user confusion.
- Users want GitHub releases aligned with PyPI releases.
- Batch-invariant ops have public reproducibility and compatibility problems.

The strongest product opportunity is therefore:

**Tinker observability and experiment control.**

## Best Product To Build

### Product Name

**Tinker Workbench**

### One-liner

An interactive research cockpit for Tinker that turns post-training from "run a script and hope" into a reproducible, observable, debuggable experiment loop.

### Why This Fits Them

It directly maps to:

- Tinker's mission: let researchers focus on data, algorithms, and evals.
- Tinker DX role: recipes, demos, user debugging, product improvements.
- Research acceleration role: experiment tracking, evals, visualization, observability.
- Interaction-model thesis: a real-time foreground assistant plus async background work.
- Your strengths: systems, low-level debugging, compilers/HPC instincts, agent orchestration.

### MVP Scope

Build a local-first app/CLI that can:

1. Parse a Tinker cookbook recipe/config.
2. Estimate run cost from model, train/sample/prefill tokens, LoRA rank, checkpoint cadence, and storage.
3. Launch or wrap a training run.
4. Stream structured logs and metrics.
5. Track checkpoints, sampler readiness, and adapter/base-model sanity checks.
6. Run evals at checkpoints using cookbook eval APIs.
7. Produce a reproducible experiment report: config, git SHA, model, dataset, hyperparams, evals, cost, anomalies.
8. Include an "interaction" layer: user asks questions while background tasks keep running.

### Demo Scenario

Use a small Tinker-compatible recipe or local mock mode:

"Train a Qwen adapter on a small instruction-following or code-repair dataset. The Workbench shows estimated cost, starts training, watches gradient/loss/eval metrics, validates sampler checkpoint behavior, runs GSM8K/IFEval-style evals, and writes a final report."

If Tinker API access is not available, build a realistic offline simulator first:

- same config shape
- mocked training loop
- fake sampler/checkpoint endpoints
- real eval/reporting pipeline
- optional integration points ready for real `TINKER_API_KEY`

That still demonstrates product taste and systems design.

## Contribution Plan

### Fast PRs

1. Improve cookbook docs around experiment tracking and checkpoint lifecycle.
2. Add a small utility around checkpoint/sampler validation if it can be done client-side.
3. Add reproducibility metadata capture to recipe outputs.
4. Add or improve tests for a cookbook edge case.
5. Contribute compatibility notes or fixes to `batch_invariant_ops`.

### Medium PRs

1. Add a `tinker-cookbook` experiment report helper.
2. Add a benchmark result writer with normalized JSON output.
3. Add a cost-estimation CLI based on public pricing and token counts.
4. Add better smoke-test coverage for a tutorial/recipe.

### Research Artifact

Pick one of their official project ideas and implement it with a polished writeup:

- On-policy context distillation for many-shot/code-style tasks.
- Memorization rate comparison between SFT and RL.
- Direct RL on pairwise prompted judges.

Best fit for you: **memorization empirical study**, because it can become a crisp systems/research benchmark with information-theoretic framing and reproducible plots.

## Portfolio Narrative

The positioning should be:

"I studied Thinking Machines Lab's public Tinker ecosystem and built a research workbench that attacks the exact friction Tinker is trying to remove: experiment observability, checkpoint trust, cost visibility, and reproducibility. The workbench treats AI collaboration as a foreground/background interaction problem, matching your interaction-model thesis while solving concrete Tinker user pain."

## 30-Day Attack Plan

### Week 1: Public map and local prototype

- Clone and study Tinker, cookbook, feedback, batch-invariant ops.
- Build `tinker-workbench` skeleton.
- Implement config ingestion, run registry, cost model, and report generation.
- Mock Tinker API integration.

### Week 2: Real cookbook integration

- Wrap one cookbook recipe.
- Capture logs, metrics, checkpoints, eval configs, and git metadata.
- Add local dashboard or terminal UI.
- Write "How I debug Tinker runs" doc.

### Week 3: Research/demo run

- Implement one official project idea in miniature.
- Prefer memorization empirical study or on-policy context distillation.
- Generate plots and final experiment report.
- Open one small upstream PR if a clean improvement appears.

### Week 4: Public packaging

- Publish repo with screenshots, demo video, architecture notes, and technical report.
- Write a short blog post: "A Workbench for Observable Post-Training with Tinker."
- Email or tag Thinking Machines/Tinker with a concise note.

## What Not To Build

Avoid a generic desktop assistant that says "Jarvis" but does not touch their real ecosystem. It will look like fan fiction.

Avoid trying to train a frontier model. The impressive move is infrastructure taste, not scale.

Avoid a huge agent framework. Build a narrow, credible tool that researchers would actually use.

## Best First Commit

Create a new repo/app with:

- `README.md`: thesis, demo, architecture
- `tinker_workbench/`: Python package
- `configs/`: example experiment configs
- `runs/`: local run metadata format
- `reports/`: generated markdown reports
- `web/` or `ui/`: optional dashboard
- `tests/`: config parser, cost estimator, report generator

Core commands:

```bash
tinker-workbench plan configs/math_rl.yaml
tinker-workbench run configs/math_rl.yaml --mock
tinker-workbench inspect runs/latest
tinker-workbench report runs/latest
```

