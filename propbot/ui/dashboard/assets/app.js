const state = {
  safeMode: true,
  venues: [],
  lastOpportunities: [],
};

function formatTimestamp(date = new Date()) {
  return date.toLocaleString();
}

async function fetchJSON(url, options = {}) {
  const response = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    credentials: 'same-origin',
    ...options,
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`${url} → ${response.status}: ${detail}`);
  }
  const text = await response.text();
  return text ? JSON.parse(text) : {};
}

function setTimestamp(id) {
  const el = document.getElementById(id);
  if (el) {
    el.textContent = `Updated ${formatTimestamp()}`;
  }
}

function updateHeader(mode, safeMode, readiness) {
  const modeEl = document.getElementById('header-mode');
  const safeModeEl = document.getElementById('header-safe-mode');
  const readinessEl = document.getElementById('header-readiness');
  if (modeEl) modeEl.textContent = mode ? mode.toUpperCase() : '—';
  if (safeModeEl) {
    safeModeEl.textContent = safeMode ? 'SAFE MODE: ON' : 'SAFE MODE: OFF';
    safeModeEl.classList.toggle('warn', safeMode);
  }
  if (readinessEl) {
    readinessEl.textContent = readiness ? 'READY' : 'ON HOLD';
  }
}

function renderSetupWizard(overview, health) {
  const list = document.getElementById('setup-steps');
  if (!list) return;
  list.innerHTML = '';
  const steps = [
    `Profile <strong>${overview.mode.toUpperCase()}</strong> loaded`,
    `SAFE_MODE is <strong>${health.safe_mode ? 'ON' : 'OFF'}</strong>`,
    `Venues detected: <strong>${state.venues.join(', ') || '—'}</strong>`,
    `Run <code>./scripts/01_bootstrap_and_check.sh</code> for acceptance checks`,
  ];
  steps.forEach((content) => {
    const li = document.createElement('li');
    li.innerHTML = content;
    list.appendChild(li);
  });
  setTimestamp('setup-updated');
}

function renderRiskLimits(limits) {
  const dl = document.getElementById('risk-limits');
  if (!dl) return;
  dl.innerHTML = '';
  Object.entries(limits || {}).forEach(([key, value]) => {
    const wrapper = document.createElement('div');
    const dt = document.createElement('dt');
    dt.textContent = key.replace(/_/g, ' ');
    const dd = document.createElement('dd');
    dd.textContent = typeof value === 'number' ? value.toLocaleString(undefined, { maximumFractionDigits: 2 }) : value;
    wrapper.appendChild(dt);
    wrapper.appendChild(dd);
    dl.appendChild(wrapper);
  });
}

function renderStatus(overview, readiness) {
  document.getElementById('hold-reason').textContent = overview.hold_reason || 'None';
  document.getElementById('safe-mode-flag').textContent = overview.safe_mode ? 'Enabled' : 'Disabled';
  document.getElementById('readiness-flag').textContent = readiness.ready ? 'Ready' : readiness.hold_reason || 'On hold';
  document.getElementById('pnl-realized').textContent = overview.pnl?.realized?.toFixed(2) ?? '0.00';
  document.getElementById('pnl-unrealized').textContent = overview.pnl?.unrealized?.toFixed(2) ?? '0.00';
  document.getElementById('order-books').textContent = JSON.stringify(overview.order_books || {}, null, 2);
  renderRiskLimits(overview.limits || {});
  setTimestamp('status-updated');
}

function renderOpportunities(opportunities) {
  const tbody = document.getElementById('opportunities-body');
  if (!tbody) return;
  tbody.innerHTML = '';
  if (!opportunities.length) {
    const row = document.createElement('tr');
    const cell = document.createElement('td');
    cell.colSpan = 6;
    cell.textContent = 'No qualifying spreads right now — waiting for next tick.';
    row.appendChild(cell);
    tbody.appendChild(row);
    setTimestamp('arb-updated');
    return;
  }

  opportunities.forEach((opp) => {
    const row = document.createElement('tr');
    row.innerHTML = `
      <td>${opp.symbol}</td>
      <td>${opp.buy_venue}</td>
      <td>${opp.sell_venue}</td>
      <td>${opp.spread_bps.toFixed(2)}</td>
      <td>${opp.notional.toLocaleString(undefined, { maximumFractionDigits: 2 })}</td>
      <td class="actions"></td>
    `;
    const actionCell = row.querySelector('.actions');
    const button = document.createElement('button');
    button.className = 'execute';
    button.textContent = state.safeMode ? 'Dry-run only' : 'Execute';
    button.disabled = state.safeMode;
    button.addEventListener('click', () => executeOpportunity(opp, actionCell, button));
    actionCell.appendChild(button);
    const status = document.createElement('div');
    status.className = 'muted';
    actionCell.appendChild(status);
    tbody.appendChild(row);
  });
  setTimestamp('arb-updated');
}

async function executeOpportunity(opp, container, button) {
  try {
    button.disabled = true;
    const result = await fetchJSON('/api/arb/execute', {
      method: 'POST',
      body: JSON.stringify({
        symbol: opp.symbol,
        buy_venue: opp.buy_venue,
        sell_venue: opp.sell_venue,
      }),
    });
    const status = container.querySelector('div');
    if (status) {
      status.textContent = `Status: ${result.status}${result.dry_run ? ' (dry-run)' : ''}`;
    }
  } catch (error) {
    const status = container.querySelector('div');
    if (status) {
      status.textContent = error.message;
    }
  } finally {
    button.disabled = state.safeMode;
  }
}

function renderAccountsCards(accounts) {
  const grid = document.getElementById('accounts-grid');
  if (!grid) return;
  grid.innerHTML = '';
  if (!accounts.length) {
    grid.textContent = 'No venues configured.';
    return;
  }
  accounts.forEach((entry) => {
    const card = document.createElement('div');
    card.className = 'account-card';
    const title = document.createElement('h3');
    title.innerHTML = `${entry.venue.toUpperCase()} <small>${entry.credentials_configured ? 'API ready' : entry.simulate ? 'Simulated' : 'Keys missing'}</small>`;
    card.appendChild(title);
    if (entry.message) {
      const note = document.createElement('p');
      note.textContent = entry.message;
      card.appendChild(note);
    }
    const table = document.createElement('table');
    const tbody = document.createElement('tbody');
    const balances = entry.balances || {};
    if (!Object.keys(balances).length) {
      const row = document.createElement('tr');
      const cell = document.createElement('td');
      cell.textContent = 'Balances unavailable';
      row.appendChild(cell);
      tbody.appendChild(row);
    } else {
      Object.entries(balances).forEach(([asset, value]) => {
        const row = document.createElement('tr');
        const assetCell = document.createElement('td');
        assetCell.textContent = asset;
        const valueCell = document.createElement('td');
        valueCell.textContent = value.toLocaleString(undefined, { maximumFractionDigits: 4 });
        row.appendChild(assetCell);
        row.appendChild(valueCell);
        tbody.appendChild(row);
      });
    }
    table.appendChild(tbody);
    card.appendChild(table);
    grid.appendChild(card);
  });
  setTimestamp('accounts-updated');
}

async function loadHealth() {
  const health = await fetchJSON('/api/health');
  state.safeMode = Boolean(health.safe_mode);
  updateHeader(health.mode || 'paper', state.safeMode, !health.hold);
  return health;
}

async function loadReadiness() {
  return fetchJSON('/live-readiness');
}

async function loadOverview() {
  const overview = await fetchJSON('/api/ui/status/overview');
  state.safeMode = Boolean(overview.safe_mode);
  state.venues = Object.keys(overview.venues || {});
  return overview;
}

async function loadOpportunities() {
  const payload = await fetchJSON('/api/arb/opportunities');
  state.lastOpportunities = payload.opportunities || [];
  renderOpportunities(state.lastOpportunities);
}

async function loadAccounts() {
  const accounts = [];
  for (const venue of state.venues) {
    try {
      const data = await fetchJSON(`/api/live/${venue}/account`);
      accounts.push(data);
    } catch (error) {
      accounts.push({ venue, balances: {}, message: error.message, simulate: false, credentials_configured: false });
    }
  }
  renderAccountsCards(accounts);
}

async function refresh() {
  try {
    const [health, overview, readiness] = await Promise.all([
      loadHealth(),
      loadOverview(),
      loadReadiness(),
    ]);
    updateHeader(overview.mode, state.safeMode, readiness.ready);
    renderSetupWizard(overview, health);
    renderStatus(overview, readiness);
    document.getElementById('safe-mode-banner').hidden = !state.safeMode;
    await Promise.all([loadOpportunities(), loadAccounts()]);
  } catch (error) {
    console.error('Dashboard refresh failed:', error);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  refresh();
  setInterval(refresh, 5000);
});
