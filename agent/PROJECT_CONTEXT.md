# Project Context

## Project Name

Tinker Workbench

## One-Sentence Goal

Build a Thinking Machines-native post-training lab assistant that plans, runs, observes, debugs, and evaluates Tinker fine-tuning experiments.

## User / Customer

- Primary: Abhishek, building a recruiting-grade artifact for Thinking Machines Lab.
- Secondary: Tinker users who need better experiment planning, checkpoint sanity checks, cost visibility, and reproducible reports.
- Audience to impress: Thinking Machines Lab Tinker, research infrastructure, developer experience, and systems teams.

## What This Project Should Do

- Ingest Tinker/Tinker Cookbook experiment configs.
- Produce a pre-run plan: model, method, data, evals, estimated tokens/cost/storage, risks.
- Run in mock mode without a Tinker API key.
- Later run real Tinker jobs when `TINKER_API_KEY` is available.
- Track runs, logs, metrics, checkpoints, sampler readiness, evals, anomalies, and reproducibility metadata.
- Generate a clean markdown/html experiment report.
- Implement at least one official `thinking-machines-lab/tinker-project-ideas` project, starting with the memorization empirical study.
- Maintain a GitHub contribution board for upstream issues, PRs, and discussions.

## What This Project Should Not Do

- Do not become a generic Jarvis clone detached from Tinker.
- Do not depend on production deployment before the local proof works.
- Do not require expensive real Tinker runs for the core demo.
- Do not silently use or leak API keys, private datasets, or credentials.
- Do not overbuild an agent framework before the research/product artifact is credible.

## Tech Stack

- Language: Python first, TypeScript/React only if a dashboard becomes necessary.
- Framework: CLI-first local workbench; optional FastAPI or static dashboard later.
- Package manager: plain `python3` works first; use `uv` when installed.
- Database: local SQLite or JSONL run store initially.
- Hosting: local only until user approves any deployment.
- Testing: `pytest`, plus small fixture-based tests for planners, estimators, reports, and mock runs.

## Important Commands

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

## Key Files And Directories

- `THINKING_MACHINES_RESEARCH.md` - research brief and build strategy.
- `agent/EXECUTION_BOARD.md` - current day/night sprint board for Codex and Cursor.
- `agent/GITHUB_CONTRIBUTION_TARGETS.md` - upstream issues, discussions, and PR angles.
- `agent/PROJECT_CONTEXT.md` - this source of truth for agents.
- `upstream/` - shallow clones of Thinking Machines public repos for reference only.
- `tinker_workbench/` - planned Python package for the product.
- `configs/` - planned sample experiment configs.
- `runs/` - planned local run outputs; generated files should be gitignored later.
- `reports/` - planned generated reports.

## Design / Product Taste

- Serious research-infrastructure product, not a marketing demo.
- CLI should feel precise and useful to researchers.
- Reports should be concise, reproducible, and credible.
- Dashboard, if built, should be dense and operational: runs, costs, checkpoints, evals, warnings.

## Constraints

- Time: compressed sprint; keep shipping useful artifacts continuously.
- Budget: default to mock/local mode; ask before real paid Tinker usage.
- Security: never commit API keys or private credentials.
- Performance: keep local runs fast; expensive simulation/eval should be optional.
- Compatibility: target macOS local development and Python 3.11+ unless repo constraints say otherwise.

## Definition Of Done

- A local workbench can plan and mock-run a Tinker-style experiment.
- A memorization-study scaffold exists with reproducible data generation and metrics.
- A report can be generated from a run directory.
- At least one credible upstream issue/PR/comment path is selected and prepared.
- Relevant checks pass.
- Important docs/context are updated.
- Remaining risks are called out.

## Open Questions

- Do we have Tinker API access and credits?
- Should the first public artifact be a repo, blog post, GitHub issue comment, or upstream PR?
- Should Cursor focus on UI/dashboard while Codex focuses on CLI/research core?
