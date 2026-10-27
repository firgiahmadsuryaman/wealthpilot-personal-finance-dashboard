const state = {
  overview: null,
  transactions: [],
  goldHistory: [],
  spyHistory: [],
  spyChartRange: '1D',
  goldChartRange: '1D',
  market: null,
};

const $ = (id) => document.getElementById(id);
const fmtIDR = (n, compact = false) => {
  if (n === null || n === undefined || !Number.isFinite(Number(n))) return '—';
  return new Intl.NumberFormat('id-ID', {
    style: 'currency', currency: 'IDR', maximumFractionDigits: 0,
    notation: compact ? 'compact' : 'standard', compactDisplay: 'short'
  }).format(Number(n));
};
const fmtUSD = (n) => {
  if (n === null || n === undefined || !Number.isFinite(Number(n))) return '—';
  return new Intl.NumberFormat('en-US', {style:'currency',currency:'USD',maximumFractionDigits:2}).format(Number(n));
};
const fmtNum = (n, max = 6) => {
  if (n === null || n === undefined || !Number.isFinite(Number(n))) return '—';
  return new Intl.NumberFormat('id-ID', {maximumFractionDigits:max}).format(Number(n));
};
const fmtPct = (n, decimals = 2) => {
  if (n === null || n === undefined || !Number.isFinite(Number(n))) return '—';
  const v = Number(n);
  return `${v > 0 ? '+' : ''}${v.toFixed(decimals)}%`;
};
const fmtDate = (s, withTime = true) => {
  if (!s) return '—';
  const d = new Date(s);
  if (Number.isNaN(d.getTime())) return String(s);
  return new Intl.DateTimeFormat('id-ID', withTime
    ? {day:'2-digit',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit'}
    : {day:'2-digit',month:'short',year:'numeric'}).format(d);
};
const setText = (id, value) => { const el = $(id); if (el) el.textContent = value; };
const signedClass = (n) => Number(n) > 0 ? 'positive' : Number(n) < 0 ? 'negative' : 'muted';
const escapeHtml = (s='') => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

async function api(url, opts = {}) {
  const res = await fetch(url, {headers:{'Content-Type':'application/json', ...(opts.headers||{})}, ...opts});
  let body = {};
  try { body = await res.json(); } catch (_) {}
  if (!res.ok) throw new Error(body.detail || body.message || `Request gagal (${res.status})`);
  return body;
}
function toast(message, type='success') {
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.textContent = message;
  $('toastRegion').appendChild(el);
  setTimeout(() => el.remove(), 4200);
}
function setGlobalStatus(ok, label, sub) {
  const dot = $('globalStatusDot');
  dot.className = `status-dot ${ok === true ? '' : ok === false ? 'bad' : 'warn'}`;
  setText('globalStatus', label);
  setText('lastChecked', sub);
}
function openModal(id) {
  const el = $(id);
  if (!el) return;
  el.classList.add('open'); el.setAttribute('aria-hidden','false');
  if (id === 'transactionModal') {
    if (!$('txDate').value) $('txDate').value = localDatetimeInput();
    updateTxFields();
  }
}
function closeModal(id) {
  const el = $(id); if (!el) return;
  el.classList.remove('open'); el.setAttribute('aria-hidden','true');
}
function localDatetimeInput() {
  const d = new Date();
  const off = d.getTimezoneOffset();
  return new Date(d.getTime() - off*60000).toISOString().slice(0,16);
}
function localDateToISO(value) { if (!value) return null; const d = new Date(value); return Number.isNaN(d.getTime()) ? value : d.toISOString(); }
function txTypeLabel(type) {
  return ({DEPOSIT:'Setoran modal',WITHDRAW:'Penarikan',BUY:'Pembelian',SELL:'Penjualan',OPENING:'Saldo awal aset',DIVIDEND:'Dividen / pendapatan'})[type] || type;
}
function txBadge(type) { return `<span class="tx-pill ${String(type).toLowerCase()}">${escapeHtml(txTypeLabel(type))}</span>`; }
function assetLabel(asset) { return ({GOLD:'Emas digital (benchmark XAU)',SPY:'SPY · S&P 500 ETF',CASH:'Kas portofolio'})[asset] || asset; }
function formatTxQuantity(tx) {
  if (['DEPOSIT','WITHDRAW','DIVIDEND'].includes(tx.tx_type)) return fmtIDR(tx.amount_idr);
  return `${fmtNum(tx.quantity,8)} ${tx.asset==='GOLD'?'gram':tx.asset==='SPY'?'unit':''}`;
}
function formatUnitPrice(tx) {
  if (['DEPOSIT','WITHDRAW','DIVIDEND'].includes(tx.tx_type)) return '—';
  if (tx.currency === 'USD') return `${fmtUSD(tx.unit_price_entered ?? tx.unit_price)}/unit`;
  const raw = tx.unit_price_entered ?? tx.unit_price;
  const unit = tx.price_unit === '0.01G' ? '/ 0,01 g' : '/ gram';
  return `${fmtIDR(raw)} ${unit}`;
}
function transactionGrossIdr(tx) {
  if (['DEPOSIT','WITHDRAW','DIVIDEND'].includes(tx.tx_type)) return Number(tx.amount_idr || 0);
  return Number(tx.quantity || 0) * Number(tx.unit_price || 0) * (tx.currency==='USD'?Number(tx.fx_rate||0):1);
}
function renderTransactionRows(items, target, allowDelete=false) {
  const tbody = $(target);
  if (!items.length) {
    tbody.innerHTML = `<tr><td colspan="${allowDelete?8:5}"><div class="table-empty">Belum ada transaksi yang tercatat.</div></td></tr>`;
    return;
  }
  tbody.innerHTML = items.map(tx => {
    const gross = transactionGrossIdr(tx);
    if (allowDelete) return `<tr>
      <td>${escapeHtml(fmtDate(tx.occurred_at))}</td><td>${txBadge(tx.tx_type)}</td><td>${escapeHtml(assetLabel(tx.asset))}</td>
      <td>${escapeHtml(formatTxQuantity(tx))}</td><td>${escapeHtml(formatUnitPrice(tx))}</td><td>${fmtIDR(gross)}</td><td>${escapeHtml(tx.memo||'—')}</td>
      <td><div class="tx-actions"><button class="edit-button" data-edit-tx="${tx.id}" title="Ubah transaksi">Ubah</button><button class="tx-delete" data-delete-tx="${tx.id}" title="Hapus transaksi">Hapus</button></div></td></tr>`;
    return `<tr><td>${escapeHtml(fmtDate(tx.occurred_at))}</td><td>${txBadge(tx.tx_type)}</td><td>${escapeHtml(assetLabel(tx.asset))}</td><td>${escapeHtml(formatTxQuantity(tx))}</td><td>${escapeHtml(formatUnitPrice(tx))}</td></tr>`;
  }).join('');
}
function renderMarket(market) {
  state.market = market;
  const goldWrap = market?.gold || {};
  const gold = goldWrap.data || {};
  const hasGoldAsk = Number.isFinite(Number(gold.customer_buy_idr_g)) && gold.customer_buy_idr_g != null;
  const hasGoldBid = Number.isFinite(Number(gold.customer_sell_idr_g)) && gold.customer_sell_idr_g != null;
  const goldStatus = gold.status || goldWrap.status || 'error';
  const goldTime = gold.timestamp || gold.captured_at;
  if (hasGoldAsk || hasGoldBid) {
    const ask = hasGoldAsk ? Number(gold.customer_buy_idr_g) : null;
    const bid = hasGoldBid ? Number(gold.customer_sell_idr_g) : null;
    const mid = gold.spot_mid_idr_g != null ? Number(gold.spot_mid_idr_g) : (ask != null && bid != null ? (ask + bid) / 2 : null);
    $('goldSpotPrice').innerHTML = `${escapeHtml(fmtIDR(mid))} <small>/ gram (spot · acuan)</small>`;
    setText('goldBuyPrice', `${fmtIDR(ask)} / gram`);
    setText('goldSellPriceSmall', `${fmtIDR(bid)} / gram`);
    setText('goldSource', `${gold.source || 'Standard Bullion'} · XAU/USD × USD/IDR`);
    setText('goldUpdated', `Quote sumber ${fmtDate(goldTime)}`);
    const delta = gold.change_today_pct ?? gold.sellback_change_pct;
    const changeText = delta == null ? 'Perubahan harian XAU/USD tidak diberikan provider' : `XAU/USD ${Number(delta)>=0?'▲':'▼'} ${fmtPct(delta)} hari ini`;
    setText('goldChange', changeText);
    $('goldChange').className = `asset-delta ${delta==null?'':signedClass(delta)}`;
    const isStale = goldStatus === 'stale' || gold.freshness_status === 'stale' || gold.fx_status === 'stale';
    setText('goldStatus', isStale ? 'Quote terakhir · periksa waktu' : 'Bid/ask pasar tersedia');
    $('goldStatus').className = isStale ? 'pill pill-neutral' : 'pill pill-good';
    setText('settingGoldBuy', fmtIDR(ask));
    setText('settingGoldSell', fmtIDR(bid));
    setText('settingGoldTime', fmtDate(goldTime));
    setText('goldSourceStatus', isStale ? 'Quote lama / kurs lama' : 'Terhubung');
    $('goldSourceStatus').className = isStale ? 'pill pill-neutral' : 'pill pill-good';
    if (gold.valuation_note) setText('goldChartMessage', `${gold.valuation_note} ${gold.attribution || ''}`.trim());
  } else {
    $('goldSpotPrice').innerHTML = `— <small>/ gram (spot · acuan)</small>`;
    setText('goldBuyPrice','—'); setText('goldSellPriceSmall','—');
    setText('goldSource','Sumber: Standard Bullion · harga spot emas');
    setText('goldUpdated', 'Quote emas atau kurs USD/IDR belum tersedia');
    setText('goldChange', gold.message || goldWrap.message || 'Periksa sumber harga emas dan quote USD/IDR.');
    $('goldChange').className='asset-delta';
    setText('goldStatus', goldStatus==='error'?'Data tidak tersedia':'Kurs belum tersedia');
    $('goldStatus').className='pill pill-neutral';
    setText('settingGoldBuy','—'); setText('settingGoldSell','—'); setText('settingGoldTime','—');
    setText('goldSourceStatus','Belum tersedia'); $('goldSourceStatus').className='pill pill-neutral';
  }

  const spy = market?.spy || {};
  const fx = market?.fx || {};
  const fxRate = (['ok','stale'].includes(fx.status) && fx.price) ? Number(fx.price) : null;
  if (['ok','stale'].includes(spy.status) && spy.price != null) {
    $('spyPrice').innerHTML = `${escapeHtml(fmtUSD(spy.price))} <small>USD / unit</small>`;
    const pct = spy.percent_change;
    setText('spyChange', pct == null ? 'Quote tersedia; perubahan harian tidak diberikan provider.' : `${Number(pct)>=0?'▲':'▼'} ${fmtPct(pct)} hari ini · ${spy.change!=null?fmtUSD(spy.change):''}`);
    $('spyChange').className = `asset-delta ${pct==null?'':signedClass(pct)}`;
    setText('spyPriceIdr', fxRate ? fmtIDR(Number(spy.price)*fxRate) : '—');
    const timeLabel = spy.timestamp_precision === 'exact_quote' ? `Waktu quote ${fmtDate(spy.timestamp)}`
      : spy.timestamp_precision === 'session_date' ? `Tanggal sesi ${fmtDate(spy.timestamp, false)}`
      : spy.timestamp_precision === 'provider_datetime' ? `Waktu dari provider ${fmtDate(spy.timestamp)}`
      : spy.timestamp_precision === 'provider_timestamp' ? `Timestamp provider ${fmtDate(spy.timestamp)}`
      : 'Waktu quote tidak disediakan provider';
    setText('spyUpdated', timeLabel);
    const quoteIsStale = spy.status === 'stale';
    setText('spyStatus', quoteIsStale ? 'Data tersimpan · basi' : (spy.market_open === true ? 'Pasar buka · quote provider' : spy.market_open === false ? 'Pasar tutup · quote terakhir' : 'Quote provider tersedia'));
    $('spyStatus').className = quoteIsStale ? 'pill pill-neutral' : 'pill pill-good';
    setText('settingSpyStatus', quoteIsStale ? 'Quote lama · provider gagal' : 'Quote tersedia');
    $('spySourceStatus').className = quoteIsStale ? 'pill pill-neutral' : 'pill pill-good';
    setText('spySourceStatus', quoteIsStale ? 'Data tersimpan · basi' : 'Terhubung');
  } else {
    $('spyPrice').innerHTML = `— <small>USD / unit</small>`;
    setText('spyChange', spy.message || 'Isi API key penyedia market-data untuk mengambil harga asli.');
    $('spyChange').className='asset-delta'; setText('spyPriceIdr','—'); setText('spyUpdated',spy.timestamp?`Cek ${fmtDate(spy.timestamp)}`:'Belum ada timestamp');
    setText('spyStatus',spy.status==='not_configured'?'API key belum diisi':'Data tidak tersedia'); $('spyStatus').className='pill pill-neutral';
    setText('settingSpyStatus','Belum tersambung'); $('spySourceStatus').className='pill pill-neutral'; setText('spySourceStatus','Belum tersambung');
  }
  if (fxRate) { setText('usdIdr',`Rp${fmtNum(fxRate,2)}`); setText('settingFxStatus',`Rp${fmtNum(fxRate,2)}`); }
  else { setText('usdIdr','—'); setText('settingFxStatus','Belum tersambung'); }
  setText('settingRefresh',`Emas ${market.refresh_seconds?.gold||'—'} dtk · SPY ${market.refresh_seconds?.spy||'—'} dtk · FX ${market.refresh_seconds?.fx||'—'} dtk`);
}

function renderPortfolio(pf) {
  setText('metricCapital', fmtIDR(pf.net_contributions_idr));
  setText('metricValue', pf.portfolio_value_idr == null ? 'Belum lengkap' : fmtIDR(pf.portfolio_value_idr));
  setText('metricCash', fmtIDR(pf.cash_balance_idr));
  if (pf.total_pnl_idr == null) {
    setText('metricPnl','—'); setText('metricPnlPct','Menunggu harga pasar semua aset');
    $('metricPnl').className='metric-value';
    setText('metricValueFoot', 'Valuasi sebagian: '+fmtIDR(pf.partial_portfolio_value_idr));
  } else {
    setText('metricPnl',`${pf.total_pnl_idr>0?'+':''}${fmtIDR(pf.total_pnl_idr)}`);
    $('metricPnl').className=`metric-value ${signedClass(pf.total_pnl_idr)}`;
    setText('metricPnlPct',pf.total_pnl_pct==null?'—':fmtPct(pf.total_pnl_pct));
    $('metricPnlPct').className=`metric-help ${signedClass(pf.total_pnl_idr)}`;
    setText('metricValueFoot', (pf.market_data_warnings||[]).length ? 'Nilai memakai data yang mungkin sudah basi; periksa peringatan.' : 'Valuasi lengkap berdasarkan quote terbaru yang tersedia');
  }
  const note = $('valuationNotice');
  const missingWarnings = pf.valuation_warnings || [];
  const freshnessWarnings = pf.market_data_warnings || [];
  const allWarnings = [...missingWarnings, ...freshnessWarnings];
  if (allWarnings.length) {
    note.hidden = false;
    setText('valuationNoticeTitle', missingWarnings.length ? 'Valuasi belum lengkap' : 'Periksa kesegaran data harga');
    const extra = missingWarnings.length ? ' Nilai total dan P/L lengkap disembunyikan agar tidak keliru.' : '';
    setText('valuationNoticeText', allWarnings.join('. ') + '.' + extra);
  } else note.hidden = true;
  renderAllocation(pf);
  renderHoldings(pf);
  setText('cashPageBalance',fmtIDR(pf.cash_balance_idr));
  setText('cashPageContrib',fmtIDR(pf.net_contributions_idr));
  const divs = state.transactions.filter(t=>t.tx_type==='DIVIDEND').reduce((n,t)=>n+Number(t.amount_idr||0)-Number(t.fee_idr||0),0);
  setText('cashPageIncome',fmtIDR(divs));
}
function renderAllocation(pf) {
  const rows = [];
  const entries = [
    {key:'GOLD',label:'Emas digital · benchmark XAU',color:'#f0be4f'},
    {key:'SPY',label:'SPY · S&P 500 ETF',color:'#519cff'}
  ];
  entries.forEach(x=>{
    const h=pf.holdings[x.key];
    if (h && h.quantity>0) rows.push({...x,qty:h.quantity,value:h.current_value_idr,cost:h.cost_basis_idr,pnl:h.unrealized_pnl_idr,status:h.valuation_status});
  });
  if (!rows.length) {
    $('allocationArea').innerHTML = `<div class="empty-state"><div class="empty-symbol">◉</div><b>Belum ada aset tercatat</b><p>Tambahkan saldo awal atau transaksi pembelian untuk melihat komposisi portofolio.</p><button class="btn btn-secondary btn-small" data-open="transactionModal">Catat aset pertama</button></div>`;
    $('addTxEmpty')?.addEventListener('click',()=>openModal('transactionModal'));
    return;
  }
  const total = rows.reduce((n,r)=>n+(r.value||0),0);
  const degs = rows.map(r=>total>0 && r.value!=null ? r.value/total*360:0);
  let cursor=0; const stops=[];
  rows.forEach((r,i)=>{stops.push(`${r.color} ${cursor}deg ${cursor+degs[i]}deg`);cursor+=degs[i];});
  $('allocationArea').innerHTML=`<div class="allocation-layout"><div class="donut" style="background:conic-gradient(${stops.join(',')})"><div class="donut-center"><small>Nilai aset</small><b>${fmtIDR(total,true)}</b></div></div><div class="allocation-legend">${rows.map(r=>`<div class="legend-row"><i style="background:${r.color}"></i><div><b>${escapeHtml(r.label)}</b><small>${fmtNum(r.qty,8)} ${r.key==='GOLD'?'gram':'unit'}</small></div><strong>${r.value==null?'—':fmtIDR(r.value,true)}</strong></div>`).join('')}</div></div>`;
}
function renderHoldings(pf) {
  const names = {GOLD:'Emas digital · benchmark XAU',SPY:'SPY · S&P 500 ETF'};
  const icons = {GOLD:'Au',SPY:'SPY'};
  const classes = {GOLD:'gold-brand',SPY:'spy-brand'};
  $('holdingsCards').innerHTML = Object.keys(names).map(key=>{
    const h=pf.holdings[key]; const qty=Number(h.quantity||0);
    const curr = h.current_value_idr;
    const pnl = h.unrealized_pnl_idr;
    const subtitle = key==='GOLD' ? `${fmtNum(qty,8)} gram · valuasi bid spot indikatif, bukan buyback Pegadaian` : `${fmtNum(qty,8)} unit · harga pasar × kurs USD/IDR`;
    return `<article class="holding-card"><div class="holding-head"><div class="asset-brand ${classes[key]}">${icons[key]}</div><div><b>${names[key]}</b><small>${subtitle}</small></div><span class="pill ${h.valuation_status==='ok'?'pill-good':'pill-neutral'}">${qty>0?(h.valuation_status==='ok'?'Tercatat':'Harga belum ada'):'Kosong'}</span></div><div class="holding-value">${qty>0?(curr==null?'Belum lengkap':fmtIDR(curr)):'Rp0'}</div><div class="holding-sub">Nilai pasar saat ini</div><div class="holding-stats"><div><small>Dasar modal tersisa</small><b>${fmtIDR(h.cost_basis_idr)}</b></div><div><small>Untung/rugi belum terealisasi</small><b class="${pnl==null?'muted':signedClass(pnl)}">${pnl==null?'—':`${pnl>0?'+':''}${fmtIDR(pnl)}`}</b></div></div></article>`;
  }).join('');
}
function resetGoalForm() {
  const form = $('goalForm');
  if (form) form.reset();
  $('goalId').value = '';
  $('goalCurrent').value = '0';
  setText('goalModalTitle', 'Buat target');
  setText('goalModalSubtitle', 'Tambahkan tujuan dan progres awal.');
  setText('saveGoalBtn', 'Simpan target');
}
function resetTransactionForm() {
  const form = $('transactionForm');
  if (form) form.reset();
  $('txId').value = '';
  $('txFee').value = '0';
  $('txDate').value = localDatetimeInput();
  $('txPriceUnit').value = '0.01G';
  $('txPrice').dataset.touched = '';
  setText('transactionModalTitle', 'Catat transaksi');
  setText('transactionModalSubtitle', 'Masukkan data dari transaksi atau riwayat sebenarnya.');
  setText('saveTxBtn', 'Simpan transaksi');
  updateTxFields();
}
function editTransaction(tx) {
  resetTransactionForm();
  $('txId').value = String(tx.id);
  $('txType').value = tx.tx_type;
  $('txAsset').value = tx.asset;
  $('txQuantity').value = tx.quantity || '';
  $('txPrice').value = tx.unit_price_entered ?? tx.unit_price ?? '';
  $('txPrice').dataset.touched = '1';
  $('txPriceUnit').value = tx.price_unit || (tx.asset === 'GOLD' ? 'GRAM' : 'UNIT');
  $('txCurrency').value = tx.currency || 'IDR';
  $('txFx').value = tx.fx_rate || '';
  $('txFee').value = tx.fee_idr ?? 0;
  $('txAmount').value = tx.amount_idr || '';
  $('txMemo').value = tx.memo || '';
  if (tx.occurred_at) {
    const dt = new Date(tx.occurred_at);
    if (!Number.isNaN(dt.getTime())) {
      const offset = dt.getTimezoneOffset();
      $('txDate').value = new Date(dt.getTime() - offset * 60000).toISOString().slice(0, 16);
    }
  }
  updateTxFields();
  setText('transactionModalTitle', 'Ubah transaksi');
  setText('transactionModalSubtitle', 'Perubahan hanya disimpan jika urutan kas dan kepemilikan tetap valid.');
  setText('saveTxBtn', 'Simpan perubahan');
  openModal('transactionModal');
}

function renderGoals(goals) {
  state.goals=goals;
  const preview = $('goalsPreview');
  if (!goals.length) {
    const html = `<div class="empty-state compact"><div class="empty-symbol">◎</div><b>Target belum dibuat</b><p>Tentukan nama, nominal, dan tanggal target yang kamu inginkan.</p><button class="btn btn-secondary btn-small" data-page-link="goals">Buat target</button></div>`;
    preview.innerHTML=html;
    $('goalCards').innerHTML=`<div class="empty-state"><div class="empty-symbol">◎</div><b>Belum ada target finansial</b><p>Buat target apa pun yang penting bagimu dan pantau progresnya.</p><button class="btn btn-primary btn-small" data-open="goalModal">＋ Buat target</button></div>`;
    return;
  }
  const makeCard = (g, previewMode=false) => {
    const pct = g.target_idr>0 ? Math.min(100,Number(g.current_saved_idr||0)/Number(g.target_idr)*100):0;
    return `<div class="goal-card"><div class="goal-card-head"><div class="goal-symbol">◎</div><div><b>${escapeHtml(g.name)}</b><small>${g.target_date?`Target ${fmtDate(g.target_date,false)}`:'Tanggal belum ditentukan'}</small></div>${previewMode?'':`<div class="goal-actions"><button class="edit-button" data-edit-goal="${g.id}">Ubah</button><button class="delete-button" data-delete-goal="${g.id}">Hapus</button></div>`}</div><div class="goal-amount">${fmtIDR(g.current_saved_idr)}<small>dari target ${fmtIDR(g.target_idr)}</small></div><div class="goal-progress-label"><span>Progres</span><b>${pct.toFixed(1)}%</b></div><div class="progress-track"><div class="progress-bar" style="width:${pct}%"></div></div><div class="goal-bottom"><span>Sisa ${fmtIDR(Math.max(0,g.target_idr-g.current_saved_idr))}</span><span>${g.notes?escapeHtml(g.notes):'Target pribadi'}</span></div></div>`;
  };
  preview.innerHTML = goals.slice(0,2).map(g=>makeCard(g,true)).join('');
  $('goalCards').innerHTML = goals.map(g=>makeCard(g,false)).join('');
}
function renderCashRows(items) {
  const arr=items.filter(t=>['DEPOSIT','WITHDRAW','DIVIDEND'].includes(t.tx_type));
  $('cashRows').innerHTML = arr.length ? arr.map(t=>`<tr><td>${escapeHtml(fmtDate(t.occurred_at))}</td><td>${txBadge(t.tx_type)}</td><td>${fmtIDR(t.amount_idr)}</td><td>${escapeHtml(t.memo||'—')}</td></tr>`).join('') : `<tr><td colspan="4"><div class="table-empty">Belum ada setoran, penarikan, atau dividen.</div></td></tr>`;
}
function chartTickLabel(item, rangeKey='1D') {
  const raw = String(item.datetime || item.captured_at || item.timestamp || '');
  // Waktu candle saham diberikan dalam waktu lokal bursa oleh provider; jangan menggesernya ke zona waktu browser.
  const intraday = raw.match(/^(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2})/);
  if (intraday) return rangeKey === '1D' ? intraday[2] : `${intraday[1].slice(5)} ${intraday[2]}`;
  const d = new Date(raw);
  return Number.isNaN(d.getTime()) ? raw.slice(0, 10) : new Intl.DateTimeFormat('id-ID', {day:'2-digit',month:'short'}).format(d);
}
function chartTimestampLabel(item, rangeKey='1D') {
  const raw=String(item.datetime||item.captured_at||item.timestamp||'').replace('T',' ');
  const match=raw.match(/^(\d{4}-\d{2}-\d{2})(?: (\d{2}:\d{2}))?/);
  if(!match)return raw||'waktu tidak disediakan';
  return rangeKey==='1M'||rangeKey==='1Y'||!match[2]?match[1]:`${match[1]} ${match[2]}`;
}
function drawLineChart(canvasId, items, valueKey, color='#46d6b0', rangeKey='1D') {
  const canvas=$(canvasId); if (!canvas) return;
  const parent=canvas.parentElement; const ratio=window.devicePixelRatio||1;
  const width=Math.max(260,canvas.clientWidth||parent.clientWidth||400); const height=220;
  canvas.width=width*ratio; canvas.height=height*ratio; canvas.style.height=`${height}px`;
  const ctx=canvas.getContext('2d'); ctx.setTransform(ratio,0,0,ratio,0,0); ctx.clearRect(0,0,width,height);
  const valid=(items||[]).map(item=>({...item,_value:Number(item[valueKey])})).filter(item=>Number.isFinite(item._value)).sort((a,b)=>String(a.datetime||a.captured_at||'').localeCompare(String(b.datetime||b.captured_at||'')));
  const m={l:54,r:14,t:16,b:32}; const plotW=width-m.l-m.r; const plotH=height-m.t-m.b;
  if(valid.length<2){ctx.fillStyle='#6a839d';ctx.font='11px DM Sans';ctx.textAlign='center';ctx.fillText('Belum cukup titik harga untuk menggambar garis',width/2,height/2);return;}
  const vals=valid.map(i=>i._value); const min=Math.min(...vals),max=Math.max(...vals),range=(max-min)||Math.max(Math.abs(max)*.001,0.01);
  for(let i=0;i<4;i++){
    const y=m.t+i*plotH/3; const v=max-i*range/3;
    ctx.beginPath();ctx.strokeStyle='rgba(100,133,164,.17)';ctx.lineWidth=1;ctx.moveTo(m.l,y);ctx.lineTo(width-m.r,y);ctx.stroke();
    ctx.fillStyle='#7890a9';ctx.font='9px DM Sans';ctx.textAlign='right';ctx.fillText(fmtNum(v, v>=1000?0:2),m.l-7,y+3);
  }
  const points=valid.map((it,i)=>({x:m.l+(i/(valid.length-1))*plotW,y:m.t+(1-(it._value-min)/range)*plotH}));
  const grd=ctx.createLinearGradient(0,m.t,0,height-m.b);grd.addColorStop(0,color+'35');grd.addColorStop(1,color+'00');
  ctx.beginPath();points.forEach((p,i)=>i?ctx.lineTo(p.x,p.y):ctx.moveTo(p.x,p.y));ctx.lineTo(points[points.length-1].x,height-m.b);ctx.lineTo(points[0].x,height-m.b);ctx.closePath();ctx.fillStyle=grd;ctx.fill();
  ctx.beginPath();points.forEach((p,i)=>i?ctx.lineTo(p.x,p.y):ctx.moveTo(p.x,p.y));ctx.strokeStyle=color;ctx.lineWidth=2;ctx.lineJoin='round';ctx.lineCap='round';ctx.stroke();
  const last=points[points.length-1];ctx.beginPath();ctx.arc(last.x,last.y,3.5,0,Math.PI*2);ctx.fillStyle=color;ctx.fill();
  [0,Math.floor((valid.length-1)/2),valid.length-1].forEach((index,i)=>{
    const x=points[index].x;ctx.fillStyle='#7890a9';ctx.font='9px DM Sans';ctx.textAlign=i===0?'left':i===2?'right':'center';
    ctx.fillText(chartTickLabel(valid[index],rangeKey),x,height-9);
  });
}
function renderGoldHistory(series) {
  const payload = Array.isArray(series) ? {items:series, status:'ok'} : (series || {});
  state.goldHistory = payload.items || [];
  state.goldChartRange = payload.range || $('goldChartRange')?.value || state.goldChartRange || '1D';
  const enough = state.goldHistory.length >= 2;
  $('goldHistoryEmpty').classList.toggle('hidden', enough);
  if (payload.status === 'error') setText('goldHistoryEmpty', payload.message || 'Histori harga spot emas tidak tersedia.');
  else if (payload.status === 'stale') setText('goldHistoryEmpty', payload.message || 'Histori lama ditampilkan karena sumber tidak dapat diperbarui.');
  else setText('goldHistoryEmpty', state.goldHistory.length === 0 ? (payload.message || 'Belum ada histori harga spot emas dari provider.') : 'Baru satu titik histori tersedia; grafik memerlukan minimal dua titik.');
  setText('goldChartStatus', state.goldHistory.length ? `${state.goldHistory.length} titik · ${payload.interval || 'historis'} · ${payload.cache_status || 'provider'}` : (payload.status === 'error' ? 'Histori tidak tersedia' : 'Menunggu histori'));
  $('goldChartStatus').className = payload.status === 'ok' && enough ? 'pill pill-good' : 'pill pill-neutral';
  setText('goldChartMessage', payload.note || payload.message || 'Harga historis dalam IDR merupakan estimasi spot XAU/USD dikonversi menggunakan USD/IDR terkini.');
  const valid = state.goldHistory.map(item => ({...item, _price:Number(item.price)})).filter(item => Number.isFinite(item._price) && item._price > 0).sort((a,b)=>String(a.datetime||'').localeCompare(String(b.datetime||'')));
  if (valid.length) {
    const first=valid[0]._price, last=valid[valid.length-1]._price;
    const pct=first>0?(last/first-1)*100:null;
    setText('goldRangeChange',pct==null?'Perubahan rentang: —':`Perubahan rentang: ${pct>0?'+':''}${fmtPct(pct)}`);
    $('goldRangeChange').className=`asset-delta ${pct==null?'':signedClass(pct)}`;
    setText('goldLastPrice',`Harga terakhir: ${fmtIDR(last)}/gram · ${chartTimestampLabel(valid[valid.length-1],state.goldChartRange)}`);
  } else {
    setText('goldRangeChange','Perubahan rentang: —'); $('goldRangeChange').className='asset-delta';
    setText('goldLastPrice','Harga terakhir: —');
  }
  drawLineChart('goldHistoryChart',state.goldHistory,'price','#f1bd4c',state.goldChartRange);
}

function renderSpySeries(series) {
  const items=series?.items||[];
  state.spyHistory=items;
  state.spyChartRange=series?.range||$('spyChartRange')?.value||'1D';
  const enough=items.length>=2;
  $('spyHistoryEmpty').classList.toggle('hidden',enough);
  if(series?.status==='not_configured') setText('spyHistoryEmpty',series.message||'API key Twelve Data belum diisi di .env.');
  else if(series?.status==='stale') setText('spyHistoryEmpty','Histori tersimpan ditampilkan di bawah; provider belum berhasil memberikan pembaruan terbaru.');
  else if(series?.status==='error') setText('spyHistoryEmpty',series.message||'Provider belum mengembalikan histori harga.');
  else setText('spyHistoryEmpty',items.length===0?'Tidak ada candle tersedia untuk rentang ini. Periksa API key, paket data, kuota, dan izin SPY.':'Belum cukup candle untuk membentuk grafik.');

  if(series?.status==='ok') {
    const cacheLabel=series.cache_status==='cached'?'cache server':'respons provider';
    setText('spyChartStatus',`${items.length} candle · ${series.interval} · ${cacheLabel}`);
    $('spyChartStatus').className='pill pill-good';
    setText('spyChartMessage',series.note||`Data candle diterima dari ${series.source||'provider'}. Periksa waktu candle terakhir di bawah; status respons bukan jaminan data tick-by-tick.`);
  } else if(series?.status==='stale') {
    setText('spyChartStatus',`Histori tersimpan · ${items.length} candle`);
    $('spyChartStatus').className='pill pill-neutral';
    setText('spyChartMessage',series.message||'Histori berasal dari database lokal dan belum berhasil diperbarui dari provider.');
  } else {
    setText('spyChartStatus',series?.status==='not_configured'?'API belum dikonfigurasi':'Histori tidak tersedia');
    $('spyChartStatus').className='pill pill-neutral';
    setText('spyChartMessage',series?.message||'Tidak ada data asli yang diterima. Periksa koneksi, API key, kuota, izin simbol SPY, dan lisensi data.');
  }

  const valid=items.map(item=>({...item,_price:Number(item.price ?? item.close)})).filter(item=>Number.isFinite(item._price)&&item._price>0).sort((a,b)=>String(a.datetime||'').localeCompare(String(b.datetime||'')));
  if(valid.length) {
    const first=valid[0]._price, last=valid[valid.length-1]._price;
    const deltaPct=first>0?(last/first-1)*100:null;
    setText('spyRangeChange',deltaPct==null?'Perubahan rentang: —':`Perubahan rentang: ${deltaPct>0?'+':''}${fmtPct(deltaPct)}`);
    $('spyRangeChange').className=`asset-delta ${deltaPct==null?'':signedClass(deltaPct)}`;
    setText('spyLastClose',`Close candle terakhir: ${fmtUSD(last)} · ${chartTimestampLabel(valid[valid.length-1],state.spyChartRange)} waktu bursa`);
  } else {
    setText('spyRangeChange','Perubahan rentang: —');
    $('spyRangeChange').className='asset-delta';
    setText('spyLastClose','Close candle terakhir: —');
  }
  drawLineChart('spyHistoryChart',items,'price','#479cff',state.spyChartRange);
}
async function loadHistories(force=false) {
  try {
    const goldRange=$('goldChartRange')?.value||state.goldChartRange||'1D';
    const spyRange=$('spyChartRange')?.value||state.spyChartRange||'1D';
    const goldUrl=`/api/market/gold/series?range=${encodeURIComponent(goldRange)}${force?'&force=true':''}`;
    const spyUrl=`/api/market/series/SPY?range=${encodeURIComponent(spyRange)}${force?'&force=true':''}`;
    const [gold,spy]=await Promise.all([api(goldUrl),api(spyUrl)]);
    renderGoldHistory(gold);
    renderSpySeries(spy);
  } catch(e) {
    console.warn('Gagal memuat histori Market Monitor:',e);
    setText('goldChartStatus','Gagal memuat histori');
    setText('goldHistoryEmpty',`Tidak dapat memuat grafik emas: ${e.message}`);
    $('goldHistoryEmpty').classList.remove('hidden');
    setText('spyChartStatus','Gagal memuat histori');
    setText('spyHistoryEmpty',`Tidak dapat memuat grafik SPY: ${e.message}`);
    $('spyHistoryEmpty').classList.remove('hidden');
  }
}
async function refreshAll(showToast=false, forceMarket=false) {
  try {
    const data=await api(forceMarket?'/api/overview?force_market=true':'/api/overview');
    state.overview=data;
    state.transactions=data.recent_transactions||[];
    renderMarket(data.market);
    renderPortfolio(data.portfolio);
    renderGoals(data.goals||[]);
    await loadTransactions();
    renderCashRows(state.transactionsAll||[]);
    setGlobalStatus(data.market.spy.status==='ok', data.market.spy.status==='ok'?'Sumber pasar tersambung':'Dashboard aktif · cek sumber data',`Terakhir dicek ${fmtDate(data.generated_at)}`);
    await loadHistories(forceMarket);
    if(showToast) toast(forceMarket?'Permintaan refresh sumber pasar dikirim. Periksa timestamp dan status sumber.':'Dashboard diperbarui.','success');
  } catch (e) {
    setGlobalStatus(false,'Backend tidak tersedia','Periksa apakah server WealthPilot berjalan.');
    if(showToast)toast(`Gagal memperbarui: ${e.message}`,'error');
  }
}
async function loadTransactions() {
  const data=await api('/api/transactions?limit=500');
  state.transactionsAll=data.items||[];
  renderTransactionRows(state.transactionsAll.slice(0,8),'recentTxRows',false);
  applyTxFilter();
  renderCashRows(state.transactionsAll);
}
function applyTxFilter() {
  const filter=$('txFilter')?.value||'ALL';
  let items=state.transactionsAll||[];
  if(filter==='CASH')items=items.filter(t=>['DEPOSIT','WITHDRAW','DIVIDEND'].includes(t.tx_type));
  if(filter==='ASSET')items=items.filter(t=>['OPENING','BUY','SELL'].includes(t.tx_type));
  const q=($('globalSearch')?.value||'').trim().toLowerCase();
  if(q)items=items.filter(t=>[t.tx_type,t.asset,t.memo,String(t.quantity),String(t.amount_idr)].join(' ').toLowerCase().includes(q));
  renderTransactionRows(items,'allTxRows',true);
}
function updateTxFields() {
  const type=$('txType').value;
  let asset=$('txAsset').value;
  const isCash=['DEPOSIT','WITHDRAW','DIVIDEND'].includes(type);
  $('amountField').classList.toggle('hidden',!isCash);
  $('qtyField').classList.toggle('hidden',isCash);
  $('priceField').classList.toggle('hidden',isCash);
  $('currencyField').classList.toggle('hidden',isCash);
  $('priceUnitField').classList.toggle('hidden',isCash);
  $('fxField').classList.toggle('hidden',isCash || asset!=='SPY');
  $('feeField').classList.toggle('hidden',type==='DEPOSIT'||type==='WITHDRAW');
  $('txAsset').disabled=isCash;
  if(isCash){$('txAsset').value='CASH';asset='CASH';}
  else if(asset==='CASH'){$('txAsset').value='GOLD';asset='GOLD';}
  $('txCurrency').disabled=isCash||asset==='GOLD';
  if(!isCash)$('txCurrency').value=asset==='SPY'?'USD':'IDR';
  $('txPriceUnit').disabled=isCash || asset==='SPY';
  if(asset==='SPY') $('txPriceUnit').value='UNIT';
  else if(asset==='GOLD' && $('txPriceUnit').value==='UNIT') $('txPriceUnit').value='0.01G';
  $('txQuantity').required=!isCash;
  $('txPrice').required=!isCash;
  $('txAmount').required=isCash;
  $('txFx').required=!isCash&&asset==='SPY';
  $('qtyLabel').textContent=asset==='GOLD'?'Kuantitas (gram)':'Kuantitas (unit SPY)';
  if(asset==='GOLD') $('priceLabel').textContent=type==='OPENING'?'Harga modal per gram':type==='SELL'?'Harga jual aktual per gram':'Harga beli aktual per gram';
  else $('priceLabel').textContent=type==='OPENING'?'Harga biaya per unit (USD)':type==='SELL'?'Harga jual eksekusi per unit (USD)':'Harga beli eksekusi per unit (USD)';
  if(isCash){$('txHint').textContent=type==='DEPOSIT'?'Setoran modal menambah kas dan modal bersih.':type==='WITHDRAW'?'Penarikan mengurangi kas serta modal bersih; saldo kas harus cukup.':'Dividen menambah kas dan hasil investasi, bukan modal baru.';}
  else if(type==='OPENING'){$('txHint').textContent='Untuk aset yang sudah dimiliki sebelum mulai memakai WealthPilot. Masukkan biaya per unit rata-rata dari catatanmu; saldo awal menambah modal tercatat tetapi tidak mengubah kas.';}
  else if(type==='BUY'){$('txHint').textContent='Harga harus sesuai transaksi/riwayat aplikasi. Pembelian mengurangi saldo kas dan menambah aset; transaksi ditolak jika kas tidak cukup.';}
  else {$('txHint').textContent=asset==='GOLD'?'Gunakan harga eksekusi aktual dari penyedia tempat kamu membeli/menjual emas; quote spot dashboard hanya benchmark dan tidak mewakili harga Tring!.':'Gunakan harga eksekusi dari riwayat Pluang dan kurs IDR/USD yang berlaku saat transaksi.';}
  if(asset==='SPY'){
    const fx=state.market?.fx;
    if(fx?.status==='ok'&&fx.price&&(!$('txFx').value||$('txFx').value==='1'))$('txFx').value=fx.price;
  }
}
function initEvents() {
  document.querySelectorAll('[data-page]').forEach(btn=>btn.addEventListener('click',()=>showPage(btn.dataset.page)));
  document.querySelectorAll('[data-page-link]').forEach(btn=>btn.addEventListener('click',()=>showPage(btn.dataset.pageLink)));
  document.querySelectorAll('[data-open]').forEach(btn=>btn.addEventListener('click',()=>openModal(btn.dataset.open)));
  document.querySelectorAll('[data-close]').forEach(btn=>btn.addEventListener('click',()=>closeModal(btn.dataset.close)));
  document.querySelectorAll('.modal-backdrop').forEach(bg=>bg.addEventListener('click',e=>{if(e.target===bg)closeModal(bg.id)}));
  $('refreshBtn').addEventListener('click',()=>refreshAll(true,true));
  $('refreshMarketBtn').addEventListener('click',()=>refreshAll(true,true));
  $('spyChartRange')?.addEventListener('change',()=>loadHistories(true));
  $('goldChartRange')?.addEventListener('change',()=>loadHistories(true));
  $('addTxTop').addEventListener('click',()=>openModal('transactionModal'));
  $('addTxEmpty')?.addEventListener('click',()=>openModal('transactionModal'));
  $('txType').addEventListener('change',()=>{$('txPrice').dataset.touched='';updateTxFields();});$('txAsset').addEventListener('change',()=>{$('txPrice').dataset.touched='';updateTxFields();});
  $('txPriceUnit').addEventListener('change',()=>{$('txPrice').dataset.touched='';updateTxFields();});
  $('txPrice').addEventListener('input',()=>{$('txPrice').dataset.touched='1';});
  $('txFilter').addEventListener('change',applyTxFilter);$('globalSearch').addEventListener('input',applyTxFilter);
  $('transactionForm').addEventListener('submit',submitTransaction);
  $('goalForm').addEventListener('submit',submitGoal);
  document.body.addEventListener('click', async e=>{
    const dynamicOpen=e.target.closest('[data-open]');
    if(dynamicOpen && !dynamicOpen.dataset.listenerAttached){
      if(dynamicOpen.dataset.open==='goalModal') resetGoalForm();
      openModal(dynamicOpen.dataset.open);
    }
    const dynamicPage=e.target.closest('[data-page-link]');
    if(dynamicPage){ showPage(dynamicPage.dataset.pageLink); }
    const editTx=e.target.closest('[data-edit-tx]');
    if(editTx){
      const tx=(state.transactionsAll||[]).find(item=>String(item.id)===String(editTx.dataset.editTx));
      if(!tx){toast('Transaksi tidak ditemukan. Muat ulang halaman.','error');return;}
      editTransaction(tx);
    }
    const delTx=e.target.closest('[data-delete-tx]');
    if(delTx){if(!confirm('Hapus transaksi ini? Ini dapat mengubah saldo, modal, dan P/L.'))return;try{await api(`/api/transactions/${delTx.dataset.deleteTx}`,{method:'DELETE'});toast('Transaksi dihapus.','success');await refreshAll();}catch(err){toast(err.message,'error');}}
    const editGoal=e.target.closest('[data-edit-goal]');
    if(editGoal){
      const goal=state.goals.find(item=>String(item.id)===String(editGoal.dataset.editGoal));
      if(!goal){toast('Target tidak ditemukan. Muat ulang halaman.','error');return;}
      $('goalId').value=String(goal.id);
      $('goalName').value=goal.name||'';
      $('goalTarget').value=String(goal.target_idr??'');
      $('goalCurrent').value=String(goal.current_saved_idr??0);
      $('goalDate').value=goal.target_date||'';
      $('goalNotes').value=goal.notes||'';
      setText('goalModalTitle','Ubah target');
      setText('goalModalSubtitle','Perbarui nama, nominal, progres awal, atau tenggat target.');
      setText('saveGoalBtn','Simpan perubahan');
      openModal('goalModal');
    }
    const delGoal=e.target.closest('[data-delete-goal]');
    if(delGoal){if(!confirm('Hapus target ini?'))return;try{await api(`/api/goals/${delGoal.dataset.deleteGoal}`,{method:'DELETE'});toast('Target dihapus.');await refreshAll();}catch(err){toast(err.message,'error');}}
  });
}
function showPage(name) {
  document.querySelectorAll('.page-view').forEach(p=>p.classList.toggle('active',p.id===`page-${name}`));
  document.querySelectorAll('.nav-link').forEach(b=>b.classList.toggle('active',b.dataset.page===name));
  if(name==='transactions') loadTransactions();
  if(name==='market') loadHistories();
  if(name==='goals') api('/api/goals').then(d=>renderGoals(d.items||[])).catch(()=>{});
  window.scrollTo({top:0,behavior:'smooth'});
}
async function submitTransaction(e) {
  e.preventDefault(); const form=$('transactionForm'); const type=$('txType').value; const isCash=['DEPOSIT','WITHDRAW','DIVIDEND'].includes(type); const asset=isCash?'CASH':$('txAsset').value;
  const payload={occurred_at:localDateToISO($('txDate').value),tx_type:type,asset,
    quantity:isCash?0:Number($('txQuantity').value||0),unit_price:isCash?0:Number($('txPrice').value||0),
    currency:isCash?'IDR':(asset==='SPY'?'USD':'IDR'),price_unit:isCash?null:(asset==='SPY'?'UNIT':$('txPriceUnit').value),fx_rate:asset==='SPY'?Number($('txFx').value||0):1,
    fee_idr:Number($('txFee').value||0),amount_idr:isCash?Number($('txAmount').value||0):0,memo:$('txMemo').value.trim()};
  const btn=$('saveTxBtn');btn.disabled=true;btn.textContent='Menyimpan...';
  const txId=$('txId').value.trim();
  try {
    await api(txId?`/api/transactions/${encodeURIComponent(txId)}`:'/api/transactions',{method:txId?'PUT':'POST',body:JSON.stringify(payload)});
    closeModal('transactionModal');resetTransactionForm();
    toast(txId?'Transaksi diperbarui. Modal dan P/L dihitung ulang.':'Transaksi tersimpan. Modal dan P/L dihitung ulang.','success');
    await refreshAll();
  } catch(err){toast(err.message,'error');}
  finally{btn.disabled=false;btn.textContent=$('txId').value?'Simpan perubahan':'Simpan transaksi';}
}
async function submitGoal(e) {
  e.preventDefault();
  const goalId=$('goalId').value.trim();
  const payload={name:$('goalName').value.trim(),target_idr:Number($('goalTarget').value),current_saved_idr:Number($('goalCurrent').value||0),target_date:$('goalDate').value||null,notes:$('goalNotes').value.trim()};
  const button=$('saveGoalBtn');
  button.disabled=true;
  try{
    await api(goalId?`/api/goals/${encodeURIComponent(goalId)}`:'/api/goals',{method:goalId?'PUT':'POST',body:JSON.stringify(payload)});
    closeModal('goalModal');resetGoalForm();toast(goalId?'Target berhasil diperbarui.':'Target berhasil dibuat.','success');await refreshAll();
  } catch(err){toast(err.message,'error');}
  finally{button.disabled=false;}
}

window.addEventListener('resize',()=>{if(state.goldHistory.length)drawLineChart('goldHistoryChart',state.goldHistory,'price','#f1bd4c',state.goldChartRange);if(state.spyHistory.length)drawLineChart('spyHistoryChart',state.spyHistory,'price','#479cff',state.spyChartRange);});
initEvents();
$('txDate').value=localDatetimeInput();updateTxFields();
refreshAll();
// UI can refresh more frequently than source providers; provider cache and market-session permissions control actual upstream requests.
setInterval(()=>refreshAll(false),30000);
