const badgeBase = "px-2 py-0.5 text-xs rounded border transition-colors";
const badgeVariants = {
  idle: "border-slate-700 text-slate-300",
  ok: "border-emerald-500/50 bg-emerald-500/10 text-emerald-300",
  warn: "border-amber-500/50 bg-amber-500/10 text-amber-300",
  danger: "border-rose-500/50 bg-rose-500/10 text-rose-300",
};

const state = {
  health: null,
  readiness: null,
  polling: null,
  refreshing: false,
};

function setBadge(element, variant, text) {
  if (!element) return;
  const classes = badgeVariants[variant] || badgeVariants.idle;
  element.className = `${badgeBase} ${classes}`;
  element.textContent = text;
}

function asTime(ts) {
  if (!ts && ts !== 0) return "—";
  try {
    const date = new Date(ts * 1000);
    return isNaN(date.getTime()) ? `${ts}` : date.toLocaleTimeString();
  } catch (err) {
    return `${ts}`;
  }
}

function updateHealthCard(data) {
  const statusEl = document.getElementById("health-status");
  const modeEl = document.getElementById("health-mode");
  const safeBadge = document.getElementById("safe-mode-badge");
  const holdBadge = document.getElementById("hold-badge");
  const detailsEl = document.getElementById("health-details");

  if (!data) {
    setBadge(statusEl, "danger", "Offline");
    modeEl.textContent = "—";
    setBadge(safeBadge, "danger", "Unknown");
    setBadge(holdBadge, "danger", "Unknown");
    detailsEl.textContent = "No data";
    return;
  }

  const statusVariant = data.status === "ok" ? "ok" : "warn";
  setBadge(statusEl, statusVariant, data.status ?? "Unknown");
  modeEl.textContent = data.mode ?? "—";

  setBadge(safeBadge, data.safe_mode ? "warn" : "ok", data.safe_mode ? "Enabled" : "Disabled");

  if (data.hold) {
    setBadge(holdBadge, "warn", data.hold);
  } else {
    setBadge(holdBadge, "ok", "None");
  }

  detailsEl.textContent = JSON.stringify(data.metrics ?? {}, null, 2);
}

function updateReadinessCard(data) {
  const statusEl = document.getElementById("readiness-status");
  const holdEl = document.getElementById("readiness-hold");
  const listEl = document.getElementById("order-books");

  listEl.innerHTML = "";

  if (!data) {
    setBadge(statusEl, "danger", "Offline");
    holdEl.textContent = "—";
    return;
  }

  setBadge(statusEl, data.ready ? "ok" : "warn", data.ready ? "Ready" : "Not Ready");
  holdEl.textContent = data.hold_reason || "None";

  const books = data.order_books || {};
  if (Object.keys(books).length === 0) {
    const li = document.createElement("li");
    li.textContent = "No order books";
    listEl.appendChild(li);
    return;
  }

  Object.entries(books).slice(0, 6).forEach(([symbol, book]) => {
    const li = document.createElement("li");
    if (book && typeof book === "object") {
      const bid = book.bid ?? book.best_bid ?? "?";
      const ask = book.ask ?? book.best_ask ?? "?";
      li.textContent = `${symbol}: bid ${bid} / ask ${ask}`;
    } else {
      li.textContent = `${symbol}: ${JSON.stringify(book)}`;
    }
    listEl.appendChild(li);
  });
}

function updateOpportunitiesTable(payload) {
  const bodyEl = document.getElementById("opportunities-body");
  const countEl = document.getElementById("opportunity-count");
  bodyEl.innerHTML = "";

  const rows = (payload && Array.isArray(payload.opportunities)) ? payload.opportunities : [];
  countEl.textContent = rows.length ? `${rows.length} open` : "No data";

  if (rows.length === 0) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 6;
    cell.className = "px-3 py-3 text-center text-slate-400";
    cell.textContent = "No opportunities";
    row.appendChild(cell);
    bodyEl.appendChild(row);
    return;
  }

  rows.slice(0, 10).forEach((row) => {
    const tr = document.createElement("tr");
    tr.className = "hover:bg-slate-900/50";
    tr.innerHTML = `
      <td class="px-3 py-2">${row.symbol ?? ""}</td>
      <td class="px-3 py-2">${row.buy_venue ?? ""}</td>
      <td class="px-3 py-2">${row.sell_venue ?? ""}</td>
      <td class="px-3 py-2">${row.spread_bps ?? ""}</td>
      <td class="px-3 py-2">${row.notional ?? ""}</td>
      <td class="px-3 py-2">${asTime(row.timestamp)}</td>
    `;
    bodyEl.appendChild(tr);
  });
}

function setControlStatus(text, tone = "info") {
  const statusEl = document.getElementById("control-status");
  const messageEl = document.getElementById("control-message");
  statusEl.textContent = text;
  if (tone === "error") {
    statusEl.className = "text-xs text-rose-300";
  } else if (tone === "success") {
    statusEl.className = "text-xs text-emerald-300";
  } else if (tone === "warn") {
    statusEl.className = "text-xs text-amber-300";
  } else {
    statusEl.className = "text-xs text-slate-500";
  }
  if (messageEl) {
    messageEl.textContent = text;
  }
}

function updateControlButtons() {
  const safeBtn = document.getElementById("safe-mode-toggle");
  if (!safeBtn) return;

  const safeMode = Boolean(state.health && state.health.safe_mode);
  safeBtn.textContent = safeMode ? "Safe Mode: ON" : "Safe Mode: OFF";
  if (safeMode) {
    safeBtn.className = "px-4 py-2 rounded bg-amber-600/80 hover:bg-amber-500 text-sm font-medium transition";
  } else {
    safeBtn.className = "px-4 py-2 rounded bg-emerald-600/80 hover:bg-emerald-500 text-sm font-medium transition";
  }
}

async function fetchJson(url, options) {
  try {
    const response = await fetch(url, { cache: "no-store", ...options });
    let data = null;
    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
      data = await response.json();
    }
    return { ok: response.ok, status: response.status, data };
  } catch (err) {
    console.error("Request failed", err);
    return { ok: false, status: 0, data: null };
  }
}

async function refresh() {
  if (state.refreshing) {
    return;
  }
  state.refreshing = true;
  try {
    const [health, readiness, opportunities] = await Promise.all([
      fetchJson("/api/health"),
      fetchJson("/live-readiness"),
      fetchJson("/api/opportunities"),
    ]);

    state.health = health.data || null;
    state.readiness = readiness.data || null;

    updateHealthCard(state.health);
    updateReadinessCard(state.readiness);
    updateOpportunitiesTable(opportunities.data || { opportunities: [] });
    updateControlButtons();

    const ts = new Date().toLocaleTimeString();
    const refreshEl = document.getElementById("last-refresh");
    if (refreshEl) {
      refreshEl.textContent = `Last updated ${ts}`;
    }
  } finally {
    state.refreshing = false;
  }
}

async function toggleSafeMode() {
  if (!state.health) {
    await refresh();
  }
  const enable = !(state.health && state.health.safe_mode);
  setControlStatus(enable ? "Enabling safe mode…" : "Disabling safe mode…", "warn");
  const result = await fetchJson("/api/ui/control-state/safe-mode", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ enabled: enable }),
  });

  if (result.ok) {
    const enabled = result.data && result.data.safe_mode;
    setControlStatus(enabled ? "Safe mode enabled" : "Safe mode disabled", "success");
  } else {
    setControlStatus(`Safe mode update failed (${result.status})`, "error");
  }
  await refresh();
}

async function holdTrading() {
  setControlStatus("Placing system on hold…", "warn");
  const result = await fetchJson("/api/ui/control-state/hold", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reason: "manual" }),
  });
  if (result.ok) {
    setControlStatus("System hold enabled", "success");
  } else {
    setControlStatus(`Hold failed (${result.status})`, "error");
  }
  await refresh();
}

async function resumeTrading() {
  setControlStatus("Attempting resume…", "warn");
  const result = await fetchJson("/api/ui/control-state/resume", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
  if (result.ok) {
    setControlStatus("Trading resumed", "success");
  } else if (result.status === 409) {
    setControlStatus("Resume requires confirmation", "warn");
  } else {
    setControlStatus(`Resume failed (${result.status})`, "error");
  }
  await refresh();
}

function attachHandlers() {
  const safeBtn = document.getElementById("safe-mode-toggle");
  const holdBtn = document.getElementById("hold-btn");
  const resumeBtn = document.getElementById("resume-btn");

  if (safeBtn) safeBtn.addEventListener("click", toggleSafeMode);
  if (holdBtn) holdBtn.addEventListener("click", holdTrading);
  if (resumeBtn) resumeBtn.addEventListener("click", resumeTrading);
}

function startPolling() {
  if (state.polling) {
    clearInterval(state.polling);
  }
  state.polling = setInterval(refresh, 2000);
}

attachHandlers();
refresh();
startPolling();
