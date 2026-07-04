# GitHub Contribution Targets

Updated: 2026-07-04

## Where To Engage

### Highest Value

- `thinking-machines-lab/tinker`
- `thinking-machines-lab/tinker-cookbook`
- `thinking-machines-lab/tinker-feedback`
- `thinking-machines-lab/batch_invariant_ops`

### Lower Direct PR Value

- `thinking-machines-lab/tinker-project-ideas`

That repo currently has no open issues. The best way to engage is to implement one of the ideas, write it up, and then open a precise issue/comment pointing to results or literature.

## Best Issue Targets

### Product/DX Fit

- `tinker#44` - `tinker checkpoint probe <path>` to verify a sampler actually serves.
- `tinker#7` - rate limit transparency.
- `tinker-cookbook#781` - account-level usage and balance query via API/CLI.
- `tinker-feedback#119` - org-level spend controls, especially checkpoint storage spend.
- `tinker-feedback#113` - API endpoint to get credits left.
- `tinker-feedback#91` - better way to delete checkpoints.

These map directly to Tinker Workbench: planning, cost visibility, checkpoint health, and operational trust.

### Systems/GPU Fit

- `batch_invariant_ops#23` - fp32 inputs may run through TF32 in persistent matmul.
- `batch_invariant_ops#14` - incompatibility with public PyTorch/Triton releases.
- `batch_invariant_ops#12` - low matmul performance.
- `batch_invariant_ops#13` - log_softmax determinism.

These map to Abhishek's compilers/GPU/HPC strengths. A careful reproduction, benchmark, or minimal failing test could be high-signal.

### Research Fit

- `tinker-project-ideas/memorization-empirical-study.md` - compare information acquisition rates for SFT and RL.
- `tinker-project-ideas/on-policy-context-distillation.md` - compare off-policy and on-policy context distillation.
- `tinker-project-ideas/direct-rl-on-pairwise-judge.md` - compare direct and indirect RLAIF.

Best first research choice: memorization empirical study.

## Recommended Public Sequence

1. Build local Tinker Workbench mock mode.
2. Use it to run the memorization empirical study locally or with a small model.
3. Produce a report with clear metrics and limitations.
4. Open a polished issue/comment in `tinker-project-ideas` linking the implementation and asking whether this result format would be useful for featured projects.
5. Open a small PR to `tinker-cookbook` if we can extract a reusable helper, doc improvement, or report utility.
6. Comment on `tinker#44` or `tinker-feedback#119` with a concrete design sketch backed by our workbench prototype.

## Candidate Comment For `tinker#44`

Do not post yet. Use after we have a small prototype.

```md
I prototyped a local checkpoint probe flow while building an experiment workbench around Tinker runs. The useful checks were:

1. resolve checkpoint path and metadata
2. create or reuse a sampler
3. run a tiny deterministic prompt through native SamplingClient
4. optionally hit the OpenAI-compatible endpoint
5. verify the response is adapter-backed, not base-model only
6. emit machine-readable JSON for CI/reporting

Would a PR adding a `tinker checkpoint probe <path> --json` client-side command be welcome, or is sampler readiness mostly server-side today?
```

## Candidate Comment For Spend/Usage Issues

Do not post yet. Use after cost planner exists.

```md
I am building a small local planning/reporting tool for Tinker experiments and hit the same need: before launching a run, I want to estimate and later reconcile train tokens, sample tokens, checkpoint storage, and remaining credits.

Even a minimal read-only endpoint plus CLI JSON output would unlock:

- pre-run budget checks
- checkpoint storage alerts
- generated experiment reports with cost provenance
- CI guards for accidental large runs

If useful, I can share a concrete JSON shape from the prototype.
```

