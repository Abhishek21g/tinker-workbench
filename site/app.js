/* Tinker DX Dashboard — composes tinker-status (platform) + Workbench run data. */

const SB_URL = "https://fbtndmrbruifjdeaydjh.supabase.co";
const SB_KEY =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZidG5kbXJicnVpZmpkZWF5ZGpoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzYyODQzOTUsImV4cCI6MjA5MTg2MDM5NX0.n2tlq1Vbq4RqVKVHLHCY_OykV5Sq3bCP_GOxrUKHvu8";

const PLATFORM_SVCS = [
  { key: "reachability", name: "API" },
  { key: "sampling", name: "Inference" },
  { key: "openai_compatible", name: "OpenAI-compatible" },
  { key: "training_infra", name: "Training" },
];

const WINDOWS = [
  { key: "24h", label: "24h" },
  { key: "7d", label: "7d" },
  { key: "30d", label: "30d" },
];

const CHECK_INTERVAL_MIN = 10;

let platformData = null;
let runData = null;
let platformLoading = true;
let activeWindow = "24h";

function pctStr(p) {
  return p === null || p === undefined ? "\u2014" : `${p.toFixed(2)}%`;
}

function pctCls(p) {
  return p === null || p === undefined ? "na" : p >= 99.5 ? "good" : p >= 95 ? "warn" : "bad";
}

function fmtTime(ts) {
  if (!ts) return "\u2014";
  return new Date(ts).toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function fmtNum(n, digits = 4) {
  if (n === null || n === undefined) return "\u2014";
  if (typeof n === "number") return n.toFixed(digits);
  return String(n);
}

function fmtUsd(n) {
  if (n === null || n === undefined) return "\u2014";
  return `$${Number(n).toFixed(2)}`;
}

function fmtTokens(n) {
  if (n === null || n === undefined) return "\u2014";
  return Number(n).toLocaleString();
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
  if (platformLoading) return { text: "Loading tinker status…", cls: "degraded" };
  if (!platformData) return { text: "Tinker status unavailable", cls: "degraded" };
  const sts = PLATFORM_SVCS.map((s) => platformData.latest[s.key]?.status);
  const allUp = sts.every((s) => s === "up");
  const allDown = sts.every((s) => s === "down" || !s);
  if (allUp) return { text: "Tinker API operational", cls: "" };
  if (allDown) return { text: "Tinker API outage", cls: "down" };
  return { text: "Tinker API degraded", cls: "degraded" };
}

function runOverall(run) {
  if (!run) return { text: "No run loaded", cls: "degraded" };
  const critical = (run.findings || []).some((f) => f.severity === "critical");
  if (run.status === "failed" || critical) return { text: "Run unhealthy", cls: "down" };
  if (run.status === "completed" && !(run.findings || []).length) {
    return { text: "Run healthy", cls: "" };
  }
  if ((run.findings || []).some((f) => f.severity === "warning")) {
    return { text: "Run has warnings", cls: "degraded" };
  }
  if (run.status === "completed") return { text: "Run healthy", cls: "" };
  return { text: "Run in progress", cls: "degraded" };
}

function combinedOverall(platform, run) {
  if (platform.cls === "down") return { text: "Tinker down — not your code", cls: "down" };
  if (run.cls === "down" && platform.cls === "") {
    return { text: "Tinker up — run needs attention", cls: "degraded" };
  }
  if (platform.cls === "degraded" && run.cls === "") {
    return { text: "Tinker degraded — run looks fine", cls: "degraded" };
  }
  if (platform.cls === "" && run.cls === "") {
    return { text: "Tinker up · run healthy", cls: "" };
  }
  return { text: `${platform.text} · ${run.text}`, cls: run.cls || platform.cls };
}

function lossSparkline(metrics) {
  if (!metrics || !metrics.length) {
    return `<div class="no-items">No loss metrics recorded.</div>`;
  }
  const w = 640;
  const h = 120;
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
      <svg viewBox="0 0 ${w} ${h}" role="img" aria-label="Training loss curve">
        <path d="M${fill}" fill="rgba(45,164,78,0.12)" stroke="none"/>
        <polyline points="${line}" fill="none" stroke="#2da44e" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
      <div class="sparkline-meta">
        <span>step ${first.step} → ${last.step}</span>
        <span>loss ${fmtNum(first.loss)} → ${fmtNum(last.loss)}</span>
      </div>
    </div>`;
}

function renderPlatformSection() {
  if (platformLoading) {
    return `
      <section class="section-block" id="tinker-status">
        <div class="section-head">
          <div class="section-title">Tinker Status</div>
          <div class="section-sub">live from tinker-status</div>
        </div>
        <div class="no-items">Loading tinker status from Shrinav's uptime monitor…</div>
      </section>`;
  }

  if (!platformData) {
    return `
      <section class="section-block" id="tinker-status">
        <div class="section-head">
          <div class="section-title">Tinker Status</div>
          <div class="section-sub">tinker-status</div>
        </div>
        <div class="no-items">Could not load tinker status. <a href="https://lokashrinav.github.io/tinker-status/" target="_blank" rel="noopener">Open tinker-status directly</a>.</div>
      </section>`;
  }

  const { ticks, uptime, latest } = platformData;
  const win = WINDOWS.find((w) => w.key === activeWindow);
  const lastCheck = latest[PLATFORM_SVCS[0].key]?.checked_at;

  return `
    <section class="section-block" id="tinker-status">
      <div class="section-head">
        <div class="section-title">Tinker Status</div>
        <div class="section-sub">
          live via <a href="https://lokashrinav.github.io/tinker-status/" target="_blank" rel="noopener">tinker-status</a>
        </div>
      </div>
      <p class="section-note">Same checks as <a href="https://lokashrinav.github.io/tinker-status/" target="_blank" rel="noopener">lokashrinav.github.io/tinker-status</a> — API, inference, OpenAI-compatible, training — every ${CHECK_INTERVAL_MIN} min. Last check ${fmtTime(lastCheck)}.</p>
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
      <div class="tabs" style="margin-top:24px">
        ${WINDOWS.map(
          (w) =>
            `<button class="tab ${w.key === activeWindow ? "active" : ""}" data-window="${w.key}">${w.label}</button>`
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
    </section>`;
}

function renderRunSection(run) {
  const ro = runOverall(run);
  return `
    <section class="section-block" id="run">
      <div class="section-head">
        <div class="section-title">My run</div>
        <div class="section-sub">workbench doctor</div>
      </div>
      <dl class="run-meta">
        <div><dt>Run</dt><dd>${run.run_id}</dd></div>
        <div><dt>Status</dt><dd class="${ro.cls === "down" ? "bad" : ro.cls === "degraded" ? "warn" : "good"}">${run.status}</dd></div>
        <div><dt>Backend</dt><dd>${run.backend || "\u2014"}</dd></div>
        <div><dt>Method</dt><dd>${run.method || "\u2014"}</dd></div>
        <div><dt>Steps</dt><dd>${run.steps_completed ?? "\u2014"}/${run.steps_planned ?? "\u2014"}</dd></div>
        <div><dt>Final loss</dt><dd>${fmtNum(run.final_loss)}</dd></div>
      </dl>
      ${lossSparkline(run.metrics)}
      ${
        !(run.findings || []).length
          ? `<div class="no-items">No issues detected by doctor.</div>`
          : (run.findings || [])
              .map(
                (f) => `<div class="finding">
          <div class="finding-dot ${f.severity}"></div>
          <div class="finding-body">
            <div class="finding-code">${f.severity} · ${f.code}</div>
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
  const plannedTrain = budget.planned_train_tokens;
  const plannedSample = budget.planned_sample_tokens;
  const actualTrain = tokens.train;
  const actualSample = tokens.sample;
  const estUsd = budget.estimated_usd;
  const maxUsd = budget.max_usd;

  return `
    <section class="section-block" id="budget">
      <div class="section-head">
        <div class="section-title">Budget</div>
        <div class="section-sub">pre-run plan vs actual</div>
      </div>
      <p class="section-note">Account balance requires upstream API (<a href="https://github.com/thinking-machines-lab/tinker-cookbook/issues/781" target="_blank" rel="noopener">#781</a>). Estimates use config-supplied rates.</p>
      <table class="uptime-table">
        <thead><tr>
          <th>Metric</th><th>Planned</th><th>Actual</th>
        </tr></thead>
        <tbody>
          <tr><td>Train tokens</td><td>${fmtTokens(plannedTrain)}</td><td>${fmtTokens(actualTrain)}</td></tr>
          <tr><td>Sample tokens</td><td>${fmtTokens(plannedSample)}</td><td>${fmtTokens(actualSample)}</td></tr>
          <tr><td>Checkpoints</td><td>${budget.checkpoints ?? "\u2014"}</td><td>${(run.checkpoints || []).length}</td></tr>
          <tr><td>Storage (est.)</td><td>${budget.checkpoint_storage_gb ?? "\u2014"} GB</td><td>\u2014</td></tr>
          <tr><td>Cost (est.)</td><td>${fmtUsd(estUsd)}</td><td>\u2014</td></tr>
          <tr><td>Budget cap</td><td>${fmtUsd(maxUsd)}</td><td>\u2014</td></tr>
        </tbody>
      </table>
    </section>`;
}

function renderCheckpointSection(run) {
  const probe = run.probe || {};
  const ok = probe.native_sampling_ok;
  const st = ok ? "up" : probe.sampler_ready ? "warn" : "down";
  const label = ok ? "Sampler verified" : probe.sampler_ready ? "Sampler ready, unverified" : "Not ready";

  return `
    <section class="section-block" id="checkpoint">
      <div class="section-head">
        <div class="section-title">Checkpoint</div>
        <div class="section-sub">sampler probe</div>
      </div>
      <p class="section-note">Artifact-based probe aligned with <a href="https://github.com/thinking-machines-lab/tinker/issues/44" target="_blank" rel="noopener">tinker#44</a>. Eval samples at checkpoint step prove native sampling worked.</p>
      <div class="service">
        <div class="service-name">Step ${probe.step ?? "\u2014"}</div>
        <span class="status ${st}"><span class="dot"></span>${label}</span>
      </div>
      <table class="uptime-table" style="margin-top:16px">
        <tbody>
          <tr><td>Sampler ready</td><td>${probe.sampler_ready ? "yes" : "no"}</td></tr>
          <tr><td>Adapter applied</td><td>${probe.adapter_applied === null ? "\u2014" : probe.adapter_applied ? "yes" : "no"}</td></tr>
          <tr><td>Eval samples at step</td><td>${probe.eval_samples_at_step ?? 0}</td></tr>
          <tr><td>Path</td><td style="word-break:break-all;font-size:0.72rem">${probe.checkpoint_path || "\u2014"}</td></tr>
        </tbody>
      </table>
      ${probe.error && !ok ? `<div class="finding" style="margin-top:16px;border-top:1px solid var(--border)"><div class="finding-dot warning"></div><div class="finding-body"><div class="finding-msg">${probe.error}</div></div></div>` : ""}
    </section>`;
}

function renderRunsList(runs, selectedId) {
  if (!runs || runs.length <= 1) return "";
  const rows = runs
    .slice(0, 8)
    .map(
      (r) => `<tr>
      <td>${r.name || r.run_id}</td>
      <td>${r.backend || "\u2014"}</td>
      <td class="${r.status === "completed" ? "good" : r.status === "failed" ? "bad" : "warn"}">${r.status}</td>
      <td>${fmtNum(r.final_loss)}</td>
    </tr>`
    )
    .join("");
  return `
    <section class="section-block">
      <div class="section-head">
        <div class="section-title">Recent runs</div>
        <div class="section-sub">exported: ${selectedId}</div>
      </div>
      <p class="section-note">Re-export with <code>tinker-workbench export-dashboard &lt;run-id&gt;</code> to change the featured run.</p>
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
    <nav class="top-nav">
      <a href="#tinker-status">Status</a>
      <a href="#run">Run</a>
      <a href="#budget">Budget</a>
      <a href="#checkpoint">Checkpoint</a>
      <a href="./about.html">About</a>
      <a href="https://github.com/Abhishek21g/tinker-workbench" target="_blank" rel="noopener">GitHub</a>
    </nav>
    <header>
      <h1>Tinker Workbench</h1>
      <div class="overall">
        <div class="dot ${combined.cls}"></div>
        ${combined.text}
        <span class="ts">Updated ${fmtTime(generated)}</span>
      </div>
    </header>
    ${renderPlatformSection()}
    ${run ? renderRunSection(run) : `<div class="no-items">No run data. Run <code>tinker-workbench export-dashboard</code>.</div>`}
    ${run ? renderBudgetSection(run) : ""}
    ${run ? renderCheckpointSection(run) : ""}
    ${renderRunsList(runData?.runs, run?.run_id)}
    <footer>
      Tinker Status uptime by <a href="https://lokashrinav.github.io/tinker-status/" target="_blank" rel="noopener">tinker-status</a> (Shrinav).<br>
      Run health, budget, and checkpoint data from <a href="https://github.com/Abhishek21g/tinker-workbench" target="_blank" rel="noopener">Tinker Workbench</a>.
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
    /* keep last good platform snapshot */
  }
}, 60000);
