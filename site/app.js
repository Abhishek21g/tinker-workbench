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

let platformData = null;
let runData = null;
let platformLoading = true;
let activeWindow = "24h";

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

function combinedOverall(platform, run) {
  if (platform.cls === "down") return { text: "Tinker down - not your code", cls: "down" };
  if (run.cls === "down" && platform.cls === "") {
    return { text: "Tinker up - run needs attention", cls: "degraded" };
  }
  if (platform.cls === "degraded" && run.cls === "") {
    return { text: "Tinker degraded - run looks fine", cls: "degraded" };
  }
  if (platform.cls === "" && run.cls === "") {
    return { text: "Tinker up, run healthy", cls: "" };
  }
  return { text: `${platform.text}, ${run.text}`, cls: run.cls || platform.cls };
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
      <div class="platform-section" id="tinker-status">
        <div class="loading" style="padding:48px 0"><div class="spinner"></div>fetching status</div>
      </div>`;
  }

  if (!platformData) {
    return `
      <div class="platform-section" id="tinker-status">
        <div class="no-items">Could not load platform status. <a href="https://lokashrinav.github.io/tinker-status/" target="_blank" rel="noopener">Open tinker-status</a>.</div>
      </div>`;
  }

  const { ticks, uptime, latency, latest, incidents: rawIncidents } = platformData;
  const win = BAR_WINDOWS.find((w) => w.key === activeWindow);
  const lastCheck = latest[PLATFORM_SVCS[0].key]?.checked_at;
  const incidents = buildIncidents(rawIncidents || []);

  return `
    <div class="platform-section" id="tinker-status">
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
          <div class="section-sub">90d window</div>
        </div>
        ${
          incidents.length === 0
            ? `<div class="no-incidents">No incidents in the last 90d.</div>`
            : incidents
                .map((inc) => {
                  const svc = PLATFORM_SVCS.find((s) => s.key === inc.service);
                  const dur = fmtDuration(inc.lastSeen - inc.start);
                  return `<div class="incident">
              <div class="incident-dot"></div>
              <div class="incident-body">
                <div class="incident-svc">${svc?.name || inc.service}</div>
                <div class="incident-meta">${fmtTime(inc.start)}${inc.count > 1 ? ` | ${dur} | ${inc.count} failed checks` : ""}</div>
                <div class="incident-err">${inc.error || "Unknown error"}</div>
              </div>
            </div>`;
                })
                .join("")
        }
      </div>
      <p class="section-note">Last checked ${fmtTime(lastCheck)} | powered by <a href="https://lokashrinav.github.io/tinker-status/" target="_blank" rel="noopener">tinker-status</a></p>
    </div>`;
}

function renderRunSection(run) {
  const statusCls = run.status === "failed" ? "bad" : run.status === "completed" ? "good" : "warn";
  return `
    <section class="run-section" id="run">
      <div class="section-head">
        <div class="section-title">My Run</div>
        <div class="section-sub">workbench doctor</div>
      </div>
      <table class="uptime-table">
        <tbody>
          <tr><td>Run</td><td>${run.run_id}</td></tr>
          <tr><td>Status</td><td class="${statusCls}">${run.status}</td></tr>
          <tr><td>Backend</td><td>${run.backend || NA}</td></tr>
          <tr><td>Method</td><td>${run.method || NA}</td></tr>
          <tr><td>Steps</td><td>${run.steps_completed ?? NA}/${run.steps_planned ?? NA}</td></tr>
          <tr><td>Final loss</td><td>${fmtNum(run.final_loss)}</td></tr>
        </tbody>
      </table>
      ${lossSparkline(run.metrics)}
      ${
        !(run.findings || []).length
          ? `<div class="no-incidents">No issues detected by doctor.</div>`
          : (run.findings || [])
              .map(
                (f) => `<div class="finding">
          <div class="finding-dot ${f.severity}"></div>
          <div class="finding-body">
            <div class="finding-code">${f.severity} | ${f.code}</div>
            <div class="finding-msg">${f.message}</div>
            <div class="finding-hint">${f.suggestion}</div>
          </div>
        </div>`
              )
              .join("")
      }
    </section>`;
}

function renderBudgetSection(run) {
  const budget = run.budget || {};
  const tokens = run.tokens || {};
  return `
    <section class="budget-section" id="budget">
      <div class="section-head">
        <div class="section-title">Budget</div>
        <div class="section-sub">plan vs actual</div>
      </div>
      <p class="section-note">Account balance needs upstream API (<a href="https://github.com/thinking-machines-lab/tinker-cookbook/issues/781" target="_blank" rel="noopener">#781</a>).</p>
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
    .slice(0, 6)
    .map(
      (r) => `<tr>
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
        <div class="section-sub">${selectedId}</div>
      </div>
      <table class="uptime-table">
        <thead><tr><th>Run</th><th>Backend</th><th>Status</th><th>Loss</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </section>`;
}

function render() {
  const run = runData?.selected_run;
  const platform = platformOverall();
  const runO = runOverall(run);
  const combined = combinedOverall(platform, runO);
  const generated = runData?.generated_at;

  document.getElementById("app").innerHTML = `
    <header>
      <h1>Tinker Workbench</h1>
      <div class="overall">
        <div class="dot ${combined.cls}"></div>
        ${combined.text}
        <span class="ts">Updated ${fmtTime(generated)}</span>
      </div>
    </header>
    <p class="jump-links">
      <a href="#tinker-status">Status</a> |
      <a href="#run">Run</a> |
      <a href="#budget">Budget</a> |
      <a href="#checkpoint">Checkpoint</a> |
      <a href="./about.html">About</a> |
      <a href="https://github.com/Abhishek21g/tinker-workbench" target="_blank" rel="noopener">GitHub</a>
    </p>
    ${renderPlatformSection()}
    ${run ? renderRunSection(run) : `<div class="no-items">No run data. Run <code>tinker-workbench export-dashboard</code>.</div>`}
    ${run ? renderBudgetSection(run) : ""}
    ${run ? renderCheckpointSection(run) : ""}
    ${renderRunsList(runData?.runs, run?.run_id)}
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

  document.querySelector(".ink-blob")?.classList.add("visible");
}

async function load() {
  try {
    runData = await fetchRunData();
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
