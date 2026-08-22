/* Renders data.json into the dashboard. No framework, no build step. */

const esc = s => String(s ?? '').replace(/[&<>"]/g, c =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

function fmtPct(v) {
  if (v === null || v === undefined) return 'n/a';
  return `${v > 0 ? '+' : ''}${v.toFixed(1)}%`;
}

function metricLine(m) {
  if ('change_pts' in m) {
    return `${esc(m.metric)}: ${m.change_pts > 0 ? '+' : ''}${m.change_pts.toFixed(1)} points `
         + `(${m.from_pct.toFixed(1)}% &rarr; ${m.to_pct.toFixed(1)}%)`;
  }
  return `${esc(m.metric)}: ${fmtPct(m.change_pct)}`;
}

function column(label, items, cls) {
  const body = items.length
    ? items.map(m => `<div class="metric-line ${cls}">${metricLine(m)}</div>`).join('')
    : `<div class="metric-empty">Nothing here</div>`;
  return `<div><div class="col-lbl">${label}</div>${body}</div>`;
}

const SEVERITY_COLOR = { high: 'var(--red)', medium: 'var(--orange)', low: 'var(--yellow)' };

function flagsBlock(flags) {
  if (!flags.length) {
    return `<div class="flags"><div class="no-flags">No red flags detected.</div></div>`;
  }
  const order = { high: 0, medium: 1, low: 2 };
  const sorted = [...flags].sort((a, b) => order[a.severity] - order[b.severity]);
  const rows = sorted.map(f => `
    <div class="flag">
      <span class="flag-dot" style="background:${SEVERITY_COLOR[f.severity]}"></span>
      <div>
        <div class="flag-title">${esc(f.flag)}</div>
        <div class="flag-detail">${esc(f.detail)}</div>
      </div>
    </div>`).join('');
  return `<div class="flags">${rows}</div>`;
}

/* Card accent + badge follow the worst flag present — a company with any
   HIGH flag reads as critical at a glance, without having to read further. */
function statusFor(company) {
  const flags = company.red_flags || [];
  if (flags.some(f => f.severity === 'high')) return { color: 'var(--red)', label: 'Flagged' };
  if (flags.some(f => f.severity === 'medium')) return { color: 'var(--orange)', label: 'Watch' };
  return { color: 'var(--green)', label: 'Clean' };
}

function companyCard(company) {
  if (company.error) {
    return `<section class="card"><div class="card-head"><h2>${esc(company.ticker)}</h2></div>
      <div class="error-card">${esc(company.error)}</div></section>`;
  }
  if (company.insufficient_data) {
    return `<section class="card"><div class="card-head"><h2>${esc(company.ticker)}</h2></div>
      <div class="error-card">Only ${company.quarters_available} quarter(s) available — need at least 2 to compare.</div></section>`;
  }

  const s = statusFor(company);
  const gapNote = !company.is_quarterly_comparison
    ? `<div class="gap-note">Only ${company.gap_days}-day span between the two most recent
       filings (~${Math.round(company.gap_days / 30.4)} months) — common for a recently-public
       company. Treat this as a longer-term change, not quarter over quarter.</div>`
    : '';

  const reaction = company.analyst_reaction
    ? `<div class="reaction">EPS ${esc(company.analyst_reaction.eps)} &middot; `
      + `Consensus ${esc(company.analyst_reaction.consensus)} &middot; `
      + `Surprise ${esc(company.analyst_reaction.surprise)}</div>`
    : '';

  return `<section class="card" style="--s:${s.color}">
    <div class="card-head">
      <div>
        <h2>${esc(company.ticker)}</h2>
        <div class="period">Quarter ending ${esc(company.period_end)} vs. ${esc(company.compared_to)}</div>
      </div>
      <span class="badge">${s.label}</span>
    </div>
    ${gapNote}
    <div class="cols">
      ${column('The Good', company.good, 'good')}
      ${column('The Bad', company.bad, 'bad')}
      ${column('The Ugly', company.ugly, 'ugly')}
    </div>
    ${flagsBlock(company.red_flags)}
    ${reaction}
  </section>`;
}

function render(data) {
  document.getElementById('grid').innerHTML =
    (data.companies || []).map(companyCard).join('');
}

async function boot() {
  try {
    const r = await fetch('data.json?t=' + Date.now(), { cache: 'no-store' });
    const data = await r.json();
    render(data);
  } catch (e) {
    document.getElementById('grid').innerHTML =
      `<div class="error-card">Couldn't load data: ${esc(e.message)}</div>`;
  }

  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('sw.js').catch(() => {});
  }
}

function toast(msg) {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.classList.add('show');
  setTimeout(() => el.classList.remove('show'), 1800);
}

document.getElementById('share').addEventListener('click', async () => {
  const shareData = {
    title: 'Earnings Tracker',
    text: 'My earnings watchlist',
    url: location.href,
  };
  if (navigator.share) {
    try { await navigator.share(shareData); }
    catch (e) { /* user cancelled the share sheet — not an error */ }
  } else if (navigator.clipboard) {
    await navigator.clipboard.writeText(location.href);
    toast('Link copied');
  } else {
    toast(location.href);
  }
});

boot();
