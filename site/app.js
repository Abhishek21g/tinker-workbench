/* Tinker DX Dashboard - tinker-status UX + Workbench run panels. */

const NA = "-";

const SB_URL = "https://fbtndmrbruifjdeaydjh.supabase.co";
const SB_KEY =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZidG5kbXJicnVpZmpkZWF5ZGpoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzYyODQzOTUsImV4cCI6MjA5MTg2MDM5NX0.n2tlq1Vbq4RqVKVHLHCY_OykV5Sq3bCP_GOxrUKHvu8";

const PLATFORM_SVCS = [
  { key: "reachability", name: "API" },
  { key: "sampling", name: "Inference" },
  { key: "openai_compatible", name: "OpenAI-compatible" },
  { key: "training_infra", name: "Training" },
];

const BAR_WINDOWS = [
  { key: "24h", label: "24h" },
  { key: "7d", label: "7d" },
  { key: "30d", label: "30d" },
];

const UPTIME_WINDOWS = [
  { key: "24h", label: "24h" },
  { key: "7d", label: "7d" },
  { key: "30d", label: "30d" },
  { key: "90d", label: "90d" },
];

const CHECK_INTERVAL_MIN = 10;
const INCIDENT_MERGE_MS = CHECK_INTERVAL_MIN * 2.5 * 60 * 1000;
const INCIDENTS_PREVIEW = 3;
const FINDINGS_PREVIEW = 2;

let platformData = null;
let runData = null;
let platformLoading = true;
let activeWindow = "24h";
let incidentsExpanded = false;
let findingsExpanded = false;
let platformDetailsExpanded = false;
let storyExpanded = false;
let activeTour = "start";
let selectedRunId = null;
let lastPlatformCls = null;
let notifyPermissionAsked = false;

const TOUR_STEPS = {
  start: {
    title: "The problem",
    body: `<p>After a Tinker post-training run you get artifacts everywhere — metrics, checkpoints, eval JSON — but no single place answers the four questions that matter before you spend again.</p>
      <ul class="tour-list">
        <li><strong>Platform</strong> — is Tinker down or is it my code?</li>
        <li><strong>Run health</strong> — divergence, NaN, stalled loss?</li>
        <li><strong>Budget</strong> — can I afford the next step?</li>
        <li><strong>Checkpoint</strong> — will sampling actually work?</li>
      </ul>`,
  },
  plan: {
    title: "Plan before credits",
    body: `<p><code>tinker-workbench plan</code> estimates train/sample tokens, checkpoint storage, and cost <em>before</em> you launch.</p>
      <p>Same YAML you will run — no duplicate config.</p>`,
  },
  run: {
    title: "Run with receipts",
    body: `<p><code>tinker-workbench run</code> writes a full artifact trail: events, metrics, checkpoints, evals.</p>
      <p>Mock, local neural LM, or Tinker SDK backends.</p>`,
  },
  doctor: {
    title: "Doctor classifies failures",
    body: `<p><code>tinker-workbench doctor</code> scans artifacts for divergence, NaN loss, checkpoint gaps, and budget overruns.</p>
      <p>Separates <strong>your experiment</strong> from <strong>platform outages</strong> (via tinker-status).</p>`,
  },
  dashboard: {
    title: "This dashboard",
    body: `<p><code>tinker-workbench export-dashboard</code> compiles your run into this page — workbench panels up top, live Tinker Status below.</p>
      <p>Click any recent run to switch. No re-export needed when panels are cached.</p>`,
  },
};

function getRunIdFromUrl() {
  return new URLSearchParams(window.location.search).get("run");
}

function setRunIdInUrl(runId) {
  const url = new URL(window.location.href);
  if (runId) url.searchParams.set("run", runId);
  else url.searchParams.delete("run");
  history.replaceState(null, "", url);
}

function getSelectedRun() {
  if (!runData) return null;
  const id = selectedRunId || getRunIdFromUrl() || runData.selected_run_id || runData.selected_run?.run_id;
  if (id && runData.run_panels?.[id]) return runData.run_panels[id];
  return runData.selected_run;
}

function maybeNotifyPlatform(platform) {
  if (platformLoading || !platform) return;
  const cls = platform.cls;
  if (lastPlatformCls !== "down" && cls === "down") {
    if (Notification.permission === "granted") {
      new Notification("Tinker platform outage", {
        body: platform.text,
        icon: "./favicon.svg",
      });
    } else if (!notifyPermissionAsked && Notification.permission === "default") {
      notifyPermissionAsked = true;
    }
  }
  lastPlatformCls = cls;
}

function renderSiteTop() {
  return `
    <nav class="site-top" aria-label="Site">
      <a class="site-back" href="https://enaguthi.com/">← enaguthi.com</a>
      <span class="site-eyebrow">Built by Abhishek Enaguthi</span>
      <div class="site-top-links">
        <a href="#story">Story</a>
        <a href="#run">Dashboard</a>
        <a href="https://github.com/Abhishek21g/tinker-workbench" target="_blank" rel="noopener">GitHub</a>
      </div>
    </nav>`;
}

function renderStorySection() {
  return `
    <section class="story-section" id="story">
      <button type="button" class="expand-btn expand-btn-block story-toggle" data-toggle="story">
        ${storyExpanded ? "Hide problem & solution" : "What is this? Problem, solution & walkthrough"}
      </button>
      <div class="${storyExpanded ? "" : "is-hidden"}">
        <div class="story-grid">
          <article class="story-card">
            <span class="story-label">Problem</span>
            <p>Tinker runs scatter signal across files. You burn credits re-running because you cannot tell if the platform, your loss curve, budget, or checkpoint is the blocker.</p>
          </article>
          <article class="story-card">
            <span class="story-label">Solution</span>
            <p><strong>Tinker Workbench</strong> is a local-first harness: plan, run, doctor, probe, export. This dashboard composes your run with live <a href="https://lokashrinav.github.io/tinker-status/" target="_blank" rel="noopener">tinker-status</a> so you know what to do next.</p>
          </article>
        </div>
        <div class="onboarding">
          <div class="section-head">
            <div class="section-title">Walkthrough</div>
            <div class="section-sub">5 steps</div>
          </div>
          <div class="tabs tour-tabs">
            ${Object.keys(TOUR_STEPS)
              .map(
                (key) =>
                  `<button type="button" class="tab tour-tab ${key === activeTour ? "active" : ""}" data-tour="${key}">${TOUR_STEPS[key].title}</button>`
              )
              .join("")}
          </div>
          <div class="tour-pane">
            <h3 class="tour-pane-title">${TOUR_STEPS[activeTour].title}</h3>
            <div class="tour-pane-body">${TOUR_STEPS[activeTour].body}</div>
          </div>
        </div>
      </div>
    </section>`;
}

function renderNotifyBanner(platform) {
  if (Notification.permission !== "default" || !platform || platform.cls === "") return "";
  return `<p class="notify-banner">
      <button type="button" class="expand-btn" data-action="notify">Enable alerts</button>
      when Tinker platform goes down.
    </p>`;
}

function pctStr(p) {
  return p === null || p === undefined ? NA : `${p.toFixed(2)}%`;
}

function pctCls(p) {
  return p === null || p === undefined ? "na" : p >= 99.5 ? "good" : p >= 95 ? "warn" : "bad";
}

function fmtTime(ts) {
  if (!ts) return NA;
  return new Date(ts).toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function fmtMs(ms) {
  if (ms === null || ms === undefined) return NA;
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function fmtDuration(ms) {
  const m = Math.round(ms / 60000);
  if (m < 60) return `${m}m`;
  const h = Math.floor(m / 60);
  return `${h}h ${m % 60}m`;
}

function fmtNum(n, digits = 4) {
  if (n === null || n === undefined) return NA;
  if (typeof n === "number") return n.toFixed(digits);
  return String(n);
}

function fmtUsd(n) {
  if (n === null || n === undefined) return NA;
  return `$${Number(n).toFixed(2)}`;
}

function fmtTokens(n) {
  if (n === null || n === undefined) return NA;
  return Number(n).toLocaleString();
}

function buildIncidents(downRows) {
  const incidents = [];
  let current = null;
  for (const row of downRows) {
    const t = new Date(row.checked_at).getTime();
    if (current && current.service === row.service && t - current.lastSeen < INCIDENT_MERGE_MS) {
      current.lastSeen = t;
      current.count += 1;
    } else {
      if (current) incidents.push(current);
      current = {
        service: row.service,
        error: row.error,
        start: t,
        lastSeen: t,
        count: 1,
      };
    }
  }
  if (current) incidents.push(current);
  return incidents.reverse();
}

async function fetchPlatformSummary() {
  const r = await fetch(`${SB_URL}/rest/v1/rpc/get_status_summary`, {
    method: "POST",
    headers: {
      apikey: SB_KEY,
      Authorization: `Bearer ${SB_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ check_interval_min: CHECK_INTERVAL_MIN }),
  });
  if (!r.ok) throw new Error(`Platform status HTTP ${r.status}`);
  return r.json();
}

async function fetchRunData() {
  const r = await fetch("./data/dashboard.json", { cache: "no-store" });
  if (!r.ok) throw new Error(`Run data HTTP ${r.status}`);
  return r.json();
}

function platformOverall() {
  if (platformLoading) return { text: "Loading...", cls: "degraded", short: "..." };
  if (!platformData) return { text: "Unavailable", cls: "degraded", short: "n/a" };
  const sts = PLATFORM_SVCS.map((s) => platformData.latest[s.key]?.status);
  const upCount = sts.filter((s) => s === "up").length;
  const allUp = sts.every((s) => s === "up");
  const allDown = sts.every((s) => s === "down" || !s);
  if (allUp) return { text: "All systems operational", cls: "", short: "operational" };
  if (allDown) return { text: "Major outage", cls: "down", short: "outage" };
  return { text: "Experiencing issues", cls: "degraded", short: `${upCount}/4 up` };
}

function runOverall(run) {
  if (!run) return { text: "No run", cls: "degraded", short: "n/a" };
  const critical = (run.findings || []).some((f) => f.severity === "critical");
  if (run.status === "failed" || critical) {
    return { text: "Unhealthy", cls: "down", short: "failed" };
  }
  if (run.status === "completed" && !(run.findings || []).length) {
    return { text: "Healthy", cls: "", short: run.status };
  }
  if ((run.findings || []).some((f) => f.severity === "warning")) {
    return { text: "Warnings", cls: "degraded", short: "warnings" };
  }
  return { text: run.status || "unknown", cls: "degraded", short: run.status || "?" };
}

function budgetOverall(run) {
  if (!run) return { text: NA, cls: "degraded", short: "n/a" };
  const budget = run.budget || {};
  const tokens = run.tokens || {};
  const est = budget.estimated_usd;
  const train = tokens.train;
  const planned = budget.planned_train_tokens;
  let cls = "";
  if (planned && train && train > planned * 1.05) cls = "degraded";
  const short = est != null ? fmtUsd(est) : `${fmtTokens(train)} tok`;
  return { text: est != null ? `Est. ${fmtUsd(est)}` : `${fmtTokens(train)} tokens`, cls, short };
}

function checkpointOverall(run) {
  if (!run?.probe) return { text: NA, cls: "degraded", short: "n/a" };
  const probe = run.probe;
  if (probe.native_sampling_ok) {
    return { text: "Sampler verified", cls: "", short: "verified" };
  }
  if (probe.sampler_ready) {
    return { text: "Ready, unverified", cls: "degraded", short: "unverified" };
  }
  return { text: "Not ready", cls: "down", short: "fail" };
}

function workbenchHeaderOverall(run, platform) {
  if (!run) return { text: "Export a run to get started", cls: "degraded" };
  const ro = runOverall(run);
  if (ro.cls === "down") return { text: `Run needs attention: ${ro.text}`, cls: "down" };
  if (ro.cls === "degraded") return { text: `Run: ${ro.text}`, cls: "degraded" };
  if (platform.cls === "down") return { text: "Run healthy, platform outage", cls: "degraded" };
  if (platform.cls === "degraded") return { text: "Run healthy", cls: "" };
  return { text: "Run healthy", cls: "" };
}

function platformStatusClass(cls) {
  if (cls === "down") return "down";
  if (cls === "degraded") return "warn";
  return "up";
}

function renderWorkbenchSummary(run, runO, budgetO, checkpointO, platform) {
  if (!run) {
    return `<div class="no-items">No run data. Run <code>tinker-workbench export-dashboard</code>.</div>`;
  }
  const runDetail = `${run.method || NA} | loss ${fmtNum(run.final_loss)}`;
  const budgetDetail = budgetO.short || "plan vs actual";
  const checkpointDetail = checkpointO.short || "sampler probe";
  return `
    <div class="services workbench-summary">
      <a class="service service-link" href="#run">
        <div class="service-name">My Run</div>
        <span class="status ${platformStatusClass(runO.cls)}"><span class="dot"></span>${runO.text}</span>
      </a>
      <div class="service-meta">${runDetail}</div>
      <a class="service service-link" href="#budget">
        <div class="service-name">Budget</div>
        <span class="status ${platformStatusClass(budgetO.cls)}"><span class="dot"></span>${budgetO.text}</span>
      </a>
      <div class="service-meta">${budgetDetail}</div>
      <a class="service service-link" href="#checkpoint">
        <div class="service-name">Checkpoint</div>
        <span class="status ${platformStatusClass(checkpointO.cls)}"><span class="dot"></span>${checkpointO.text}</span>
      </a>
      <div class="service-meta">${checkpointDetail}</div>
      <a class="service service-link" href="#tinker-status">
        <div class="service-name">Tinker Platform</div>
        <span class="status ${platformStatusClass(platform.cls)}"><span class="dot"></span>${platform.short}</span>
      </a>
      <div class="service-meta">${platform.text}</div>
    </div>`;
}

function renderIncidentRow(inc, hidden = false) {
  const svc = PLATFORM_SVCS.find((s) => s.key === inc.service);
  const dur = fmtDuration(inc.lastSeen - inc.start);
  return `<div class="incident${hidden ? " is-hidden" : ""}">
    <div class="incident-dot"></div>
    <div class="incident-body">
      <div class="incident-svc">${svc?.name || inc.service}</div>
      <div class="incident-meta">${fmtTime(inc.start)}${inc.count > 1 ? ` | ${dur} | ${inc.count} failed checks` : ""}</div>
      <div class="incident-err">${inc.error || "Unknown error"}</div>
    </div>
  </div>`;
}

function renderCollapsibleBlock(items, renderItem, previewCount, expanded, toggleKey) {
  if (!items.length) return "";
  const hiddenCount = Math.max(0, items.length - previewCount);
  const html = items
    .map((item, i) => renderItem(item, !expanded && i >= previewCount))
    .join("");
  const toggle =
    hiddenCount > 0
      ? `<button type="button" class="expand-btn" data-toggle="${toggleKey}">
          ${expanded ? "Show less" : `Show ${hiddenCount} more`}
        </button>`
      : "";
  return `${html}${toggle}`;
}

function renderProgressBar(pct, label) {
  const clamped = Math.max(0, Math.min(100, pct));
  const cls = clamped > 105 ? "over" : clamped >= 95 ? "warn" : "";
  return `
    <div class="progress-block">
      <div class="progress-label">
        <span>${label}</span>
        <span class="progress-pct">${clamped.toFixed(0)}%</span>
      </div>
      <div class="progress-track">
        <div class="progress-fill ${cls}" style="width:${Math.min(clamped, 100)}%"></div>
      </div>
    </div>`;
}

function renderNextSteps(run, platform, runO, checkpointO) {
  const steps = [];
  if (!run) {
    steps.push({
      text: "Export your latest run to populate the dashboard.",
      cmd: "tinker-workbench export-dashboard latest",
    });
  } else {
    if (runO.cls === "down") {
      steps.push({
        text: "Investigate run health with doctor.",
        cmd: `tinker-workbench doctor --run ${run.run_id}`,
      });
    }
    if (checkpointO.cls === "degraded" || checkpointO.cls === "down") {
      steps.push({
        text: "Verify checkpoint sampling before the next run.",
        cmd: `tinker-workbench probe --run ${run.run_id}`,
      });
    }
    const budget = run.budget || {};
    const tokens = run.tokens || {};
    if (budget.planned_train_tokens && tokens.train > budget.planned_train_tokens * 1.05) {
      steps.push({
        text: "Train tokens exceeded plan - replan before scaling up.",
        cmd: "tinker-workbench plan --help",
      });
    }
    if (platform.cls === "down") {
      steps.push({
        text: "Platform outage detected - pause spend until Tinker is back.",
        link: "https://lokashrinav.github.io/tinker-status/",
        linkLabel: "tinker-status",
      });
    }
    if (!steps.length) {
      steps.push({
        text: "Run looks good - plan the next experiment.",
        cmd: "tinker-workbench plan memorization --backend mock",
      });
    }
  }

  return `
    <section class="next-steps">
      <div class="section-head">
        <div class="section-title">Next</div>
        <div class="section-sub">suggested</div>
      </div>
      ${steps
        .map(
          (s) => `<div class="next-step">
        <div class="next-step-text">${s.text}</div>
        ${
          s.cmd
            ? `<code class="next-step-cmd">${s.cmd}</code>`
            : `<a href="${s.link}" target="_blank" rel="noopener">${s.linkLabel}</a>`
        }
      </div>`
        )
        .join("")}
    </section>`;
}

function lossSparkline(metrics) {
  if (!metrics || !metrics.length) {
    return `<div class="no-items">No loss metrics recorded.</div>`;
  }
  const w = 640;
  const h = 100;
  const pad = 8;
  const losses = metrics.map((m) => m.loss);
  const min = Math.min(...losses);
  const max = Math.max(...losses);
  const span = max - min || 1;
  const pts = metrics.map((m, i) => {
    const x = pad + (i / Math.max(metrics.length - 1, 1)) * (w - pad * 2);
    const y = pad + (1 - (m.loss - min) / span) * (h - pad * 2);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  const line = pts.join(" ");
  const fill = `${pad},${h - pad} ${line} ${w - pad},${h - pad}`;
  const first = metrics[0];
  const last = metrics[metrics.length - 1];
  return `
    <div class="sparkline-wrap">
      <div class="sparkline-label">Loss curve</div>
      <svg viewBox="0 0 ${w} ${h}" role="img" aria-label="Training loss curve">
        <path d="M${fill}" fill="rgba(45,164,78,0.14)" stroke="none"/>
        <polyline points="${line}" fill="none" stroke="#2da44e" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
      <div class="sparkline-meta">
        <span>step ${first.step} to ${last.step}</span>
        <span>${fmtNum(first.loss)} to ${fmtNum(last.loss)}</span>
      </div>
    </div>`;
}

function renderPlatformSection() {
  if (platformLoading) {
    return `
      <div class="platform-section platform-appendix" id="tinker-status">
        <div class="section-head">
          <div class="section-title">Tinker Status</div>
          <div class="section-sub">fetching...</div>
        </div>
        <div class="loading" style="padding:48px 0"><div class="spinner"></div>fetching status</div>
      </div>`;
  }

  if (!platformData) {
    return `
      <div class="platform-section platform-appendix" id="tinker-status">
        <div class="section-head">
          <div class="section-title">Tinker Status</div>
          <div class="section-sub">offline</div>
        </div>
        <div class="no-items">Could not load platform status. <a href="https://lokashrinav.github.io/tinker-status/" target="_blank" rel="noopener">Open tinker-status</a>.</div>
      </div>`;
  }

  const { ticks, uptime, latency, latest, incidents: rawIncidents } = platformData;
  const win = BAR_WINDOWS.find((w) => w.key === activeWindow);
  const lastCheck = latest[PLATFORM_SVCS[0].key]?.checked_at;
  const incidents = buildIncidents(rawIncidents || []);

  return `
    <div class="platform-section platform-appendix" id="tinker-status">
      <div class="section-head">
        <div class="section-title">Tinker Status</div>
        <div class="section-sub"><a href="https://lokashrinav.github.io/tinker-status/" target="_blank" rel="noopener">full page</a></div>
      </div>
      <div class="services">
        ${PLATFORM_SVCS.map((s) => {
          const d = latest[s.key];
          const st = d?.status || "down";
          return `<div class="service">
            <div class="service-name">${s.name}</div>
            <span class="status ${st}"><span class="dot"></span>${st === "up" ? "Operational" : "Outage"}</span>
          </div>`;
        }).join("")}
      </div>

      <div class="platform-details ${platformDetailsExpanded ? "" : "is-hidden"}">
      <div class="bar-section">
        <div class="section-head">
          <div class="section-title">Last ${win.label}</div>
          <div class="section-sub">1 bar / ${CHECK_INTERVAL_MIN} min</div>
        </div>
        <div class="tabs">
          ${BAR_WINDOWS.map(
            (w) =>
              `<button type="button" class="tab ${w.key === activeWindow ? "active" : ""}" data-window="${w.key}">${w.label}</button>`
          ).join("")}
        </div>
        ${PLATFORM_SVCS.map((s) => {
          const tk = ticks[s.key]?.[win.key] || [];
          const u = uptime[s.key]?.[win.key] ?? null;
          return `<div class="bar-row">
            <div class="bar-label">
              <span class="bar-name">${s.name}</span>
              <span class="bar-pct ${pctCls(u)}">${pctStr(u)}</span>
            </div>
            <div class="bar">${tk.map((t) => `<div class="t ${t}"></div>`).join("")}</div>
          </div>`;
        }).join("")}
        <div class="bar-range"><span>${win.label} ago</span><span>now</span></div>
      </div>

      <div class="uptime-section">
        <div class="section-head">
          <div class="section-title">Uptime</div>
        </div>
        <table class="uptime-table">
          <thead><tr><th></th>${UPTIME_WINDOWS.map((w) => `<th>${w.label}</th>`).join("")}</tr></thead>
          <tbody>
            ${PLATFORM_SVCS.map(
              (s) => `<tr>
              <td>${s.name}</td>
              ${UPTIME_WINDOWS.map((w) => {
                const u = uptime[s.key]?.[w.key] ?? null;
                return `<td class="${pctCls(u)}">${pctStr(u)}</td>`;
              }).join("")}
            </tr>`
            ).join("")}
          </tbody>
        </table>
      </div>

      <div class="latency-section">
        <div class="section-head">
          <div class="section-title">Response time</div>
          <div class="section-sub">90d window</div>
        </div>
        <p class="latency-note">Checks every ${CHECK_INTERVAL_MIN} min from one GitHub Actions runner. Latency is a trend, not a benchmark.</p>
        <table class="uptime-table">
          <thead><tr><th></th><th>p50</th><th>p95</th><th>p99</th></tr></thead>
          <tbody>
            ${PLATFORM_SVCS.map((s) => {
              const l = latency[s.key] || {};
              return `<tr>
                <td>${s.name}</td>
                <td>${fmtMs(l.p50)}</td>
                <td>${fmtMs(l.p95)}</td>
                <td>${fmtMs(l.p99)}</td>
              </tr>`;
            }).join("")}
          </tbody>
        </table>
      </div>

      <div class="incidents-section">
        <div class="section-head">
          <div class="section-title">Incidents</div>
          <div class="section-sub">${incidents.length ? `${incidents.length} in 90d` : "90d window"}</div>
        </div>
        ${
          incidents.length === 0
            ? `<div class="no-incidents">No incidents in the last 90d.</div>`
            : renderCollapsibleBlock(
                incidents,
                renderIncidentRow,
                INCIDENTS_PREVIEW,
                incidentsExpanded,
                "incidents"
              )
        }
      </div>
      </div>
      ${
        !platformDetailsExpanded
          ? `<button type="button" class="expand-btn expand-btn-block" data-toggle="platform">Show platform details</button>`
          : `<button type="button" class="expand-btn expand-btn-block" data-toggle="platform">Hide platform details</button>`
      }
      <p class="section-note">Last checked ${fmtTime(lastCheck)} | powered by <a href="https://lokashrinav.github.io/tinker-status/" target="_blank" rel="noopener">tinker-status</a></p>
    </div>`;
}

function renderRunSection(run) {
  const statusCls = run.status === "failed" ? "bad" : run.status === "completed" ? "good" : "warn";
  const stepPct =
    run.steps_planned && run.steps_completed != null
      ? (run.steps_completed / run.steps_planned) * 100
      : 0;
  const findings = run.findings || [];
  return `
    <section class="run-section" id="run">
      <div class="section-head">
        <div class="section-title">My Run</div>
        <div class="section-sub">workbench doctor</div>
      </div>
      <table class="uptime-table">
        <tbody>
          <tr><td>Run</td><td><span class="run-id">${run.run_id}</span> <button type="button" class="copy-btn" data-copy="${run.run_id}" title="Copy run ID">copy</button></td></tr>
          <tr><td>Status</td><td class="${statusCls}">${run.status}</td></tr>
          <tr><td>Backend</td><td>${run.backend || NA}</td></tr>
          <tr><td>Method</td><td>${run.method || NA}</td></tr>
          <tr><td>Steps</td><td>${run.steps_completed ?? NA}/${run.steps_planned ?? NA}</td></tr>
          <tr><td>Final loss</td><td>${fmtNum(run.final_loss)}</td></tr>
        </tbody>
      </table>
      ${renderProgressBar(stepPct, "Training steps")}
      ${lossSparkline(run.metrics)}
      ${
        !findings.length
          ? `<div class="no-incidents">No issues detected by doctor.</div>`
          : renderCollapsibleBlock(
              findings,
              (f, hidden) => `<div class="finding${hidden ? " is-hidden" : ""}">
          <div class="finding-dot ${f.severity}"></div>
          <div class="finding-body">
            <div class="finding-code">${f.severity} | ${f.code}</div>
            <div class="finding-msg">${f.message}</div>
            <div class="finding-hint">${f.suggestion}</div>
          </div>
        </div>`,
              FINDINGS_PREVIEW,
              findingsExpanded,
              "findings"
            )
      }
    </section>`;
}

function renderBudgetSection(run) {
  const budget = run.budget || {};
  const tokens = run.tokens || {};
  const trainPct =
    budget.planned_train_tokens && tokens.train
      ? (tokens.train / budget.planned_train_tokens) * 100
      : 0;
  return `
    <section class="budget-section" id="budget">
      <div class="section-head">
        <div class="section-title">Budget</div>
        <div class="section-sub">plan vs actual</div>
      </div>
      <p class="section-note">Account balance needs upstream API (<a href="https://github.com/thinking-machines-lab/tinker-cookbook/issues/781" target="_blank" rel="noopener">#781</a>).</p>
      ${budget.planned_train_tokens ? renderProgressBar(trainPct, "Train tokens vs plan") : ""}
      <table class="uptime-table">
        <thead><tr><th>Metric</th><th>Planned</th><th>Actual</th></tr></thead>
        <tbody>
          <tr><td>Train tokens</td><td>${fmtTokens(budget.planned_train_tokens)}</td><td>${fmtTokens(tokens.train)}</td></tr>
          <tr><td>Sample tokens</td><td>${fmtTokens(budget.planned_sample_tokens)}</td><td>${fmtTokens(tokens.sample)}</td></tr>
          <tr><td>Checkpoints</td><td>${budget.checkpoints ?? NA}</td><td>${(run.checkpoints || []).length}</td></tr>
          <tr><td>Storage (est.)</td><td>${budget.checkpoint_storage_gb ?? NA} GB</td><td>${NA}</td></tr>
          <tr><td>Cost (est.)</td><td>${fmtUsd(budget.estimated_usd)}</td><td>${NA}</td></tr>
          <tr><td>Budget cap</td><td>${fmtUsd(budget.max_usd)}</td><td>${NA}</td></tr>
        </tbody>
      </table>
    </section>`;
}

function renderCheckpointSection(run) {
  const probe = run.probe || {};
  const ok = probe.native_sampling_ok;
  const st = ok ? "up" : probe.sampler_ready ? "warn" : "down";
  const label = ok ? "Sampler verified" : probe.sampler_ready ? "Ready, unverified" : "Not ready";
  return `
    <section class="checkpoint-section" id="checkpoint">
      <div class="section-head">
        <div class="section-title">Checkpoint</div>
        <div class="section-sub">sampler probe</div>
      </div>
      <div class="service">
        <div class="service-name">Step ${probe.step ?? NA}</div>
        <span class="status ${st}"><span class="dot"></span>${label}</span>
      </div>
      <table class="uptime-table" style="margin-top:12px">
        <tbody>
          <tr><td>Sampler ready</td><td>${probe.sampler_ready ? "yes" : "no"}</td></tr>
          <tr><td>Adapter applied</td><td>${probe.adapter_applied === null ? NA : probe.adapter_applied ? "yes" : "no"}</td></tr>
          <tr><td>Eval samples</td><td>${probe.eval_samples_at_step ?? 0}</td></tr>
          <tr><td>Path</td><td style="word-break:break-all">${probe.checkpoint_path || NA}</td></tr>
        </tbody>
      </table>
    </section>`;
}

function renderRunsList(runs, selectedId) {
  if (!runs || runs.length <= 1) return "";
  const rows = runs
    .slice(0, 8)
    .map(
      (r) => `<tr class="run-row ${r.run_id === selectedId ? "selected-run" : ""}" data-run-id="${r.run_id}" role="button" tabindex="0">
      <td>${r.name || r.run_id}</td>
      <td>${r.backend || NA}</td>
      <td class="${r.status === "completed" ? "good" : r.status === "failed" ? "bad" : "warn"}">${r.status}</td>
      <td>${fmtNum(r.final_loss)}</td>
    </tr>`
    )
    .join("");
  return `
    <section class="runs-section">
      <div class="section-head">
        <div class="section-title">Recent runs</div>
        <div class="section-sub">click to switch</div>
      </div>
      <table class="uptime-table">
        <thead><tr><th>Run</th><th>Backend</th><th>Status</th><th>Loss</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </section>`;
}

function render() {
  const run = getSelectedRun();
  const platform = platformOverall();
  maybeNotifyPlatform(platform);
  const runO = runOverall(run);
  const budgetO = budgetOverall(run);
  const checkpointO = checkpointOverall(run);
  const header = workbenchHeaderOverall(run, platform);
  const generated = runData?.generated_at;
  const platformNote = platformLoading
    ? "Platform loading..."
    : platform.cls === ""
      ? "Platform operational"
      : platform.text;

  document.getElementById("app").innerHTML = `
    ${renderSiteTop()}
    <header>
      <h1>Tinker Workbench</h1>
      <p class="tagline">Is my run healthy? Can I afford the next step? Can I trust this checkpoint? Is Tinker up?</p>
      <div class="overall">
        <div class="dot ${header.cls}"></div>
        ${header.text}
        <span class="ts">Updated ${fmtTime(generated)} | ${platformNote}</span>
      </div>
    </header>
    ${renderNotifyBanner(platform)}
    ${renderStorySection()}
    ${renderWorkbenchSummary(run, runO, budgetO, checkpointO, platform)}
    ${renderNextSteps(run, platform, runO, checkpointO)}
    <p class="jump-links">
      <a href="#run">Run</a> |
      <a href="#budget">Budget</a> |
      <a href="#checkpoint">Checkpoint</a> |
      <a href="#tinker-status">Platform</a> |
      <a href="./about.html">About</a> |
      <a href="https://github.com/Abhishek21g/tinker-workbench" target="_blank" rel="noopener">GitHub</a>
    </p>
    ${run ? renderRunSection(run) : ""}
    ${run ? renderBudgetSection(run) : ""}
    ${run ? renderCheckpointSection(run) : ""}
    ${renderRunsList(runData?.runs, run?.run_id)}
    ${renderPlatformSection()}
    <footer>
      Tinker Status by <a href="https://lokashrinav.github.io/tinker-status/" target="_blank" rel="noopener">Shrinav</a> |
      Workbench by <a href="https://github.com/Abhishek21g/tinker-workbench" target="_blank" rel="noopener">Abhishek Enaguthi</a>
    </footer>`;

  document.querySelectorAll(".tab[data-window]").forEach((btn) => {
    btn.addEventListener("click", () => {
      activeWindow = btn.dataset.window;
      render();
    });
  });

  document.querySelectorAll("[data-toggle]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const key = btn.dataset.toggle;
      if (key === "incidents") incidentsExpanded = !incidentsExpanded;
      if (key === "findings") findingsExpanded = !findingsExpanded;
      if (key === "platform") platformDetailsExpanded = !platformDetailsExpanded;
      if (key === "story") storyExpanded = !storyExpanded;
      render();
    });
  });

  document.querySelectorAll("[data-tour]").forEach((btn) => {
    btn.addEventListener("click", () => {
      activeTour = btn.dataset.tour;
      render();
    });
  });

  document.querySelectorAll(".run-row[data-run-id]").forEach((row) => {
    const pick = () => {
      selectedRunId = row.dataset.runId;
      setRunIdInUrl(selectedRunId);
      render();
    };
    row.addEventListener("click", pick);
    row.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        pick();
      }
    });
  });

  document.querySelector("[data-action='notify']")?.addEventListener("click", async () => {
    await Notification.requestPermission();
    render();
  });

  document.querySelectorAll("[data-copy]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(btn.dataset.copy);
        btn.textContent = "copied";
        setTimeout(() => {
          btn.textContent = "copy";
        }, 1500);
      } catch {
        btn.textContent = "fail";
      }
    });
  });

  document.querySelector(".ink-blob")?.classList.add("visible");
}

async function load() {
  try {
    runData = await fetchRunData();
    selectedRunId = getRunIdFromUrl();
    render();
    fetchPlatformSummary()
      .then((data) => {
        platformData = data;
        platformLoading = false;
        render();
      })
      .catch(() => {
        platformData = null;
        platformLoading = false;
        render();
      });
  } catch (e) {
    document.getElementById("app").innerHTML =
      `<div class="loading" style="color:var(--red)">Failed to load: ${e.message}</div>`;
  }
}

load();
setInterval(async () => {
  try {
    platformData = await fetchPlatformSummary();
    render();
  } catch {
    /* keep last snapshot */
  }
}, 60000);
