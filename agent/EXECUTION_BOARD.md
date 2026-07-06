# Tinker DX Dashboard — Execution Board

Updated: 2026-07-05  
Phase: **1 — Research & gap analysis** (no code until plan is signed off)

## North Star

One operational dashboard that answers four questions every Tinker researcher asks mid-run:

| # | Question | Layer | Primary owner today |
|---|----------|-------|---------------------|
| 1 | Is the **platform** up? | Status / uptime | [tinker-status](https://github.com/soumith/tinker-status) (Shrinav) |
| 2 | Is **my run** healthy? | Workbench doctor / status | Tinker Workbench (built) |
| 3 | Can I **afford** the next run? | Cost / budget | Workbench planner + upstream #551 / #781 |
| 4 | Can I **trust** this checkpoint? | Sampler probe | Upstream tinker#44 (not built anywhere yet) |

**Pitch:** stack completion, not "you don't have this."  
Acknowledge and integrate `tinker-status`, `tinkpad`, `tinker-cost`, and cookbook tooling. Position the DX Dashboard as the **experiment cockpit** that composes them into one pre-spend → mid-run → post-run loop.

## Shared Workspace

```text
/Users/enaguthiabhishek/Documents/tinker          ← Workbench + dashboard MVP
https://github.com/Abhishek21g/tinker-workbench   ← product repo
https://github.com/Abhishek21g/interaction-bench  ← adjacent artifact (not in dashboard v1)
```

Launch target: **enaguthi.com** (Phase 4), linking Workbench, Interaction Bench, upstream PRs, and the unified dashboard.

---

## Phase 1 Gap Analysis (complete — no code yet)

### What is already built

#### Tinker Workbench (local-first, 82 tests, CI green)

| Capability | Status | Dashboard relevance |
|------------|--------|---------------------|
| `plan` — token/cost/storage estimates, risk list | ✅ | Pillar 3 pre-run |
| `run` — full artifact trail (events, metrics, checkpoints, evals) | ✅ | All pillars read artifacts |
| `status` — works on interrupted runs | ✅ | Pillar 2 live-ish state |
| `doctor` — divergence, NaN, stalls, checkpoint gaps, budget | ✅ + `--json` | Pillar 2 health |
| `compare`, `report`, `baseline`, `drift`, `conformance` | ✅ | Reliability story, not v1 dashboard |
| `collab --target tinker-cookbook-cost` | ✅ design JSON only | Pillar 3 upstream pitch |
| `collab --target tinker-checkpoint-probe` | ✅ design JSON only | Pillar 4 upstream pitch |
| Static product page (`site/index.html`) | ✅ marketing mock | Not operational; replace in Phase 3 |
| Real backends: mock, local neural LM, tinker SDK adapter | ✅ | Demo without credits |

#### tinker-status (Shrinav — do not duplicate)

- Live: [lokashrinav.github.io/tinker-status](https://lokashrinav.github.io/tinker-status)
- Checks every 10 min: API reachability, inference sample, OpenAI-compatible endpoint, training client init
- Architecture: GitHub Actions → `check.py` → Supabase → `get_status_summary()` RPC → static GitHub Pages
- Known gaps (from upstream README): single US region, no alerting, hardcoded OpenAI URL, training check is init-only

#### Upstream PRs in flight

| Repo | PR | Role for dashboard |
|------|-----|-------------------|
| tinker-cookbook | [#798](https://github.com/thinking-machines-lab/tinker-cookbook/pull/798) | Run artifact summarize — feeds Pillar 2 + cookbook-native runs |
| tinker-cookbook | [#799](https://github.com/thinking-machines-lab/tinker-cookbook/pull/799) | JSONL robustness — artifact ingestion reliability |
| tinker | [#48](https://github.com/thinking-machines-lab/tinker/pull/48) | Checkpoint delete JSON — adjacent DX polish |
| batch_invariant_ops | [#25](https://github.com/thinking-machines-lab/batch_invariant_ops/pull/25) | Systems credibility, not dashboard v1 |

#### Interaction Bench

Separate recruiting artifact (voice interactivity trilemma). Mention on enaguthi.com; **out of dashboard v1 scope**.

---

### Gap analysis by pillar

#### Pillar 1 — Is the platform up?

| Have | Need |
|------|------|
| Full third-party uptime page + Supabase RPC | Embed or consume `get_status_summary` in our dashboard (link + live panel) |
| Independent 10-min checks | "Platform vs me" banner when platform red but doctor green (or vice versa) |
| | Document integration contract (anon Supabase key + RPC shape) — **contribution target to tinker-status** |
| | Optional: incident webhook / RSS (their README lists "no alerting" as limitation) |

**Decision:** integrate, don't rebuild. First outreach target: Shrinav.

#### Pillar 2 — Is my run healthy?

| Have | Need |
|------|------|
| `doctor` + `status` CLI with `--json` | Dashboard panel: selected run → findings, loss sparkline, run state |
| Artifact schema stable (`runs/<id>/…`) | `export-dashboard` or static JSON bundle the frontend reads |
| #798 summarize for cookbook log dirs | Adapter: ingest cookbook `log_path` alongside Workbench runs |

**Decision:** thinnest path — JSON export from existing CLI, no new diagnosis logic in v1.

#### Pillar 3 — Can I afford the next run?

| Have | Need |
|------|------|
| Pre-run estimates in `plan.json` (manual rates) | Dashboard: planned tokens/USD, budget caps, risk flags |
| In-run budget stop (`stopped_budget`) | Post-run planned vs actual token reconciliation in report |
| collab JSON shape for upstream | |
| **No** account balance API (#781) | Manual "credits remaining" field in dashboard until upstream ships |
| **No** per-run actual cost API (#551) | Show estimates + token actuals; label cost as estimated until API exists |

**Decision:** Phase 2 PR should advance **cost visibility** (cookbook-side JSON/report helper extending #798 theme) rather than blocking dashboard on billing API.

#### Pillar 4 — Can I trust this checkpoint?

| Have | Need |
|------|------|
| `sampler_ready` bool in checkpoint artifacts | Not sufficient — no liveness probe |
| Evals call `backend.sample()` at checkpoint time | Post-hoc only; no standalone probe command |
| collab proposal matching tinker#44 | **`tinker-workbench probe <checkpoint>`** (or upstream `tinker checkpoint probe`) |
| | Checks: native sample, latency, adapter-vs-base signal, optional OpenAI endpoint |
| | JSON output for dashboard + CI |

**Decision:** implement probe in Workbench first (Phase 2 alternate track or Phase 3 blocker), upstream PR to tinker#44 follows prototype.

---

### Composition map (stack completion)

```text
                    ┌─────────────────────────────────────┐
                    │     Tinker DX Dashboard (Option C)   │
                    │  enaguthi.com / workbench dashboard    │
                    └──────────┬──────────────────────────┘
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
  tinker-status          Tinker Workbench      tinker-cost / tinkpad
  (platform up?)         (my run healthy?)     (referenced, not replaced)
         │                    │                    │
         │              plan / doctor / probe      │
         │              artifact JSON export       │
         └────────────────────┴────────────────────┘
                         cookbook #798 summarize
                         upstream #551 / #781 / #44
```

---

## Phase Plan

| Phase | Deliverable | Exit criteria |
|-------|-------------|---------------|
| **1** Research | This board + gap analysis | Plan signed off; pillar owners clear |
| **2** Upstream PR | **Pick one:** tinker-status contribution **OR** cost-visibility PR | Merged or substantive review thread |
| **3** Dashboard MVP | 4-panel static/semistatic app reading JSON + tinker-status RPC | All four questions visible with real data |
| **4** Launch | enaguthi.com page: Workbench + Interaction Bench + dashboard + PR links | Public URL live |
| **5** Outreach | Shrinav (integration), tinker-feedback (cost/probe threads) | At least one external reply |

---

## Phase 2 — PR fork (decide before coding)

Two credible first PRs; **pick one** to avoid split focus:

### Option A — tinker-status integration PR (recommended if relationship-first)

**Goal:** make tinker-status embeddable by third-party dashboards.

| Task | Notes |
|------|-------|
| Read `get_status_summary` RPC + anon key pattern | Already public on GitHub Pages |
| Propose `EMBED.md` or `/docs/integration.md` | Document RPC, CORS, rate limits, attribution |
| Optional: `?format=json` landing or shared widget CSS | Low-scope; ask Shrinav before large UI changes |
| Optional: webhook on status transition | Addresses their "no alerting" gap |

**Why first:** proves collaboration mindset; Pillar 1 done without duplicating infra; fast review surface.

### Option B — Cost visibility PR (recommended if upstream-merge-first)

**Goal:** extend cookbook run introspection toward #551 / #781.

| Task | Notes |
|------|-------|
| Build on #798 `TrainingRunStore.summarize()` | Add token/cost-relevant fields where artifacts allow |
| Export stable JSON schema (from `collab --target tinker-cookbook-cost`) | Same shape Workbench already proposed |
| Comment on #551 with concrete example output | After PR or prototype lands |

**Why first:** #798 already open and CI green; directly feeds Pillar 3 dashboard panel.

### Option C — Checkpoint probe (defer unless tinker#44 gets maintainer ACK)

Implement `tinker-workbench probe` locally → PR to `thinking-machines-lab/tinker` per #44.  
Higher effort, needs `TINKER_API_KEY`. Best as Phase 2b after A or B.

---

## Phase 3 — Dashboard MVP spec (plan only)

**Principle:** CLI contracts first; dashboard is a reader.

### Layout (single page, dense, operational)

```text
┌─ Platform ─────────────────┬─ My Run ────────────────────┐
│ tinker-status summary      │ run picker + status badge   │
│ 24h uptime bars            │ doctor findings (severity)  │
│ latest incident            │ loss sparkline              │
├─ Budget ───────────────────┼─ Checkpoint ────────────────┤
│ plan.json estimates        │ latest checkpoint path      │
│ credits remaining (manual) │ probe result / sampler_ready│
│ planned vs actual tokens   │ [Run probe] when CLI exists │
└────────────────────────────┴─────────────────────────────┘
```

### Data sources (v1)

| Panel | Source | Refresh |
|-------|--------|---------|
| Platform | tinker-status Supabase RPC (read-only anon) | poll 60s |
| My run | `runs/latest/` or user-selected run dir | on load + manual |
| Budget | `plan.json` + `summary.json` | static per run |
| Checkpoint | `checkpoints.jsonl` + probe JSON | after probe |

### Tech choice (tentative)

- **Static HTML + JS** in `site/dashboard/` (matches existing `site/`, no new deps)
- Python **`tinker-workbench export-dashboard --run latest --out site/dashboard/data/`** generates JSON bundle (Phase 3 first code)
- CORS: tinker-status RPC must allow browser origin OR use thin static proxy at deploy time — verify in Phase 2 integration spike

### Explicit non-goals for v1

- No auth, no multi-user server
- No live WebSocket training stream
- No replacement of tinker Console for billing
- No Interaction Bench widgets

---

## Phase 4 — enaguthi.com launch checklist

- [ ] Hero: "Tinker DX stack" — Workbench + Dashboard + upstream contributions
- [ ] Link Interaction Bench as parallel systems artifact
- [ ] Live dashboard embed or link
- [ ] Open PR badges (#798, #799, #48, #25) with status
- [ ] Hiring brief alignment: reproducibility, cost visibility, checkpoint trust
- [ ] Contact + GitHub links

---

## Phase 5 — Outreach scripts (draft, do not send until MVP exists)

### Shrinav (tinker-status)

> Built a Tinker experiment dashboard that composes Workbench run health with your uptime page instead of duplicating checks. Happy to contribute an integration doc or small embed hook to tinker-status — what would be welcome?

### tinker-feedback (cost + probe)

> Prototyping a unified DX dashboard; pre-run cost uses the JSON shape from our Workbench collab proposal. Attaching example output from #798 summarize + plan reconciliation. Same for checkpoint probe JSON aligned with tinker#44.

---

## Agent ownership (Option C)

| Lane | Owns |
|------|------|
| **Codex** | Phase 2 PR (Python/upstream), `export-dashboard`, probe CLI, artifact adapters |
| **Cursor** | Dashboard UI (`site/dashboard/`), enaguthi.com, screenshots, integration spike with tinker-status RPC |

**Rule:** Codex lands JSON contracts; Cursor builds the reader. Don't edit the same file concurrently.

---

## Immediate next actions (Phase 1 → 2 gate)

1. **User decision:** Phase 2 PR fork — **A (tinker-status)** vs **B (cost/#798)** vs **C (probe/#44)**.
2. **Spike (1 hour):** fetch `get_status_summary` from browser; confirm CORS feasibility.
3. **Watch open PRs:** #798 / #799 review responses; merge #48 / #25 if easy wins.
4. **Do not code dashboard** until Phase 2 target is chosen and JSON shapes are frozen.

---

## Risk register

| Risk | Mitigation |
|------|------------|
| #781 balance API doesn't exist | Manual credits field; label as estimate |
| tinker-status CORS blocks browser | Link out to Shrinav's page in v1; proxy later |
| Probe needs paid API key | Demo probe on mock/local; real probe documented as opt-in |
| Scope creep (Interaction Bench, memorization charts) | v1 = four panels only |
| "Not invented here" vs tinkpad/tinker-cost | Credits in UI copy and README |

---

## Definition of done — Phase 1

- [x] Gap analysis across four pillars
- [x] Integration strategy for tinker-status (no duplication)
- [x] Phase 2–5 plan with explicit fork decision
- [x] MVP wireframe and data contracts sketched
- [ ] User sign-off on Phase 2 PR choice → then code
