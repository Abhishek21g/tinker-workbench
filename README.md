# Tinker Workbench

**Operational dashboard + experiment harness for [Tinker](https://github.com/thinking-machines-lab/tinker) post-training.**

[![CI](https://github.com/Abhishek21g/tinker-workbench/actions/workflows/ci.yml/badge.svg)](https://github.com/Abhishek21g/tinker-workbench/actions/workflows/ci.yml)
[![Live dashboard](https://img.shields.io/badge/dashboard-live-2da44e)](https://enaguthi.com/tinker-workbench/site/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)

### [→ Live dashboard](https://enaguthi.com/tinker-workbench/site/) · [About](https://enaguthi.com/tinker-workbench/site/about.html) · [Issues](https://github.com/Abhishek21g/tinker-workbench/issues)

---

## What it answers

| Question | Layer | How |
|----------|-------|-----|
| Is **my run** healthy? | Workbench | `doctor`, loss metrics, findings |
| Can I **afford** the next step? | Workbench | `plan`, token/cost estimates |
| Can I **trust** this checkpoint? | Workbench | `probe` (sampler readiness, [tinker#44](https://github.com/thinking-machines-lab/tinker/issues/44)) |
| Is **Tinker** up? | [tinker-status](https://lokashrinav.github.io/tinker-status/) | Live integration — we compose, not duplicate |

**Stack completion**, not "you don't have this." Workbench composes with [tinker-status](https://lokashrinav.github.io/tinker-status/), [tinkpad](https://github.com/thinking-machines-lab/tinker-cookbook/issues/551), and cookbook tooling into one pre-spend → mid-run → post-run loop.

---

## What we built

```
plan ──► run ──► doctor / probe / report ──► export-dashboard ──► live site
```

| Piece | What it does |
|-------|----------------|
| **CLI** | `plan`, `run`, `status`, `doctor`, `probe`, `compare`, `report`, `baseline`, `drift` |
| **Backends** | Mock (no credits), local neural LM, Tinker SDK adapter |
| **Artifacts** | Events, metrics, checkpoints, evals — full trail per run |
| **Dashboard** | Static export + live tinker-status; [enaguthi.com/tinker-workbench/site/](https://enaguthi.com/tinker-workbench/site/) |

---

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[local]" pyyaml

# Plan before you pay
tinker-workbench plan configs/memorization_sft.yaml

# Run (mock backend — no API key)
tinker-workbench run configs/memorization_sft.yaml

# Debug + checkpoint trust
tinker-workbench doctor latest
tinker-workbench probe latest

# Publish to the live dashboard
tinker-workbench export-dashboard latest
```

Real Tinker runs: set `mode: tinker` in config + `TINKER_API_KEY`.

---

## Live dashboard

**https://enaguthi.com/tinker-workbench/site/**

- Workbench panels first (run, budget, checkpoint)
- Live [tinker-status](https://lokashrinav.github.io/tinker-status/) appendix (uptime, incidents)
- Run switching, next-step CLI hints, collapsible platform details

Refresh local data then publish:

```bash
tinker-workbench export-dashboard latest
./scripts/publish-site.sh   # syncs to enaguthi.com
```

---

## Memorization study

Shipped configs for the [tinker-project-ideas](https://github.com/thinking-machines-lab/tinker-project-ideas) memorization empirical study — SFT vs dense RL vs terminal RL, same budget, `compare` readout.

---

## Docs

| Doc | Contents |
|-----|----------|
| [docs/commands.md](docs/commands.md) | Full CLI reference |
| [docs/architecture.md](docs/architecture.md) | Design and rationale |
| [docs/upstream-collab.md](docs/upstream-collab.md) | Upstream issue/PR targets |
| [site/about.html](site/about.html) | Product overview |

---

## Development

```bash
pip install -e ".[local]" pytest ruff pyyaml
pytest tests/ -q
ruff check tinker_workbench/ tests/
```

CI: lint + tests + CLI smoke (including `probe` + `export-dashboard`) on Python 3.11–3.13.

---

## Collaborate

Feedback welcome — especially from the Tinker team on dashboard UX, `probe` vs [tinker#44](https://github.com/thinking-machines-lab/tinker/issues/44), and cookbook export shape.

- [Open an issue](https://github.com/Abhishek21g/tinker-workbench/issues)
- Comment on upstream with a link to the [live dashboard](https://enaguthi.com/tinker-workbench/site/)

Platform uptime data from [tinker-status](https://lokashrinav.github.io/tinker-status/) (community monitor; integrated, not duplicated).

---

Built by [Abhishek Enaguthi](https://enaguthi.com/) · BS/MS CS & AI, Oregon State University
