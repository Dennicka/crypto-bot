async function refresh() {
  const statusResp = await fetch('/api/health');
  const status = await statusResp.json();
  document.getElementById('status').textContent = `Mode: ${status.mode} | HOLD: ${status.hold || 'no'} | Safe: ${status.safe_mode}`;

  const oppResp = await fetch('/api/opportunities');
  const opportunities = await oppResp.json();
  const tbody = document.querySelector('#opportunities tbody');
  tbody.innerHTML = '';
  opportunities.opportunities.forEach((opp) => {
    const row = document.createElement('tr');
    row.innerHTML = `<td>${opp.symbol}</td><td>${opp.buy_venue}</td><td>${opp.sell_venue}</td><td>${opp.spread_bps.toFixed(2)}</td>`;
    tbody.appendChild(row);
  });

  const pnlResp = await fetch('/api/ui/pnl');
  const pnl = await pnlResp.json();
  document.getElementById('pnl').textContent = JSON.stringify(pnl, null, 2);
}

document.getElementById('hold').addEventListener('click', async () => {
  await fetch('/api/ui/control-state/hold', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({reason: 'ui'})});
  await refresh();
});

document.getElementById('resume').addEventListener('click', async () => {
  await fetch('/api/ui/control-state/resume', {method: 'POST'});
  await refresh();
});

setInterval(refresh, 2000);
refresh();
