"""
Build all feature UIs in Agency Hub and Settings:
- Invoicing tab (Agency Hub)
- Pipeline/CRM tab (Agency Hub)
- Call Summaries tab (Agency Hub)
- Missed Call Text-Back (Settings)
- Smart Follow-Ups (Settings)
- Review Collection (Settings)
- Appointment Reminders (Settings)
- Deposits (Settings)
- Analytics tab (Agency Hub)
"""

content = open('/root/janovum-toolkit/Janovum_Platform_v3.html').read()

# ─────────────────────────────────────────────────────────────
# 1. Add tabs to Agency Hub
# ─────────────────────────────────────────────────────────────
old_tabs = '          <button class="btn btn-outline" id="ag-tab-proposals" onclick="agSwitchTab(\'proposals\')">&#128221; Proposals</button>'
new_tabs = '''          <button class="btn btn-outline" id="ag-tab-proposals" onclick="agSwitchTab('proposals')">&#128221; Proposals</button>
          <button class="btn btn-outline" id="ag-tab-invoices" onclick="agSwitchTab('invoices')">&#128181; Invoices</button>
          <button class="btn btn-outline" id="ag-tab-pipeline" onclick="agSwitchTab('pipeline')">&#128200; Pipeline</button>
          <button class="btn btn-outline" id="ag-tab-calls" onclick="agSwitchTab('calls')">&#128222; Call Logs</button>
          <button class="btn btn-outline" id="ag-tab-analytics" onclick="agSwitchTab('analytics')">&#128202; Analytics</button>'''

if old_tabs in content:
    content = content.replace(old_tabs, new_tabs)
    print('Agency hub tabs added')
else:
    print('WARNING: agency tab marker not found')

# ─────────────────────────────────────────────────────────────
# 2. Add switch cases
# ─────────────────────────────────────────────────────────────
old_switch = "  else if (tab === 'proposals') agRenderProposals(el);"
new_switch = """  else if (tab === 'proposals') agRenderProposals(el);
  else if (tab === 'invoices') agRenderInvoices(el);
  else if (tab === 'pipeline') agRenderPipeline(el);
  else if (tab === 'calls') agRenderCallLogs(el);
  else if (tab === 'analytics') agRenderAnalytics(el);"""

if old_switch in content:
    content = content.replace(old_switch, new_switch)
    print('Switch cases added')
else:
    print('WARNING: switch case marker not found')

# ─────────────────────────────────────────────────────────────
# 3. Big JS injection — all feature UIs
# ─────────────────────────────────────────────────────────────
FEATURE_JS = r"""
// ═══════════════════════════════════
// INVOICING UI
// ═══════════════════════════════════
async function agRenderInvoices(el) {
  el.innerHTML = '<div style="color:var(--muted);font-size:0.85em;padding:10px 0">Loading invoices...</div>';
  let invs = [];
  try { invs = await api('/api/invoices'); } catch(e) {}

  const total = invs.reduce((s,i) => s + (i.amount||0), 0);
  const paid = invs.filter(i => i.status === 'paid').reduce((s,i) => s + (i.amount||0), 0);
  const unpaid = total - paid;
  const overdue = invs.filter(i => i.status === 'unpaid' && new Date(i.due_date+'Z') < new Date()).length;

  let html = '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:20px">';
  html += '<div class="stat-card"><div class="stat-label">Total Invoiced</div><div class="stat-value gold">$' + total.toLocaleString() + '</div></div>';
  html += '<div class="stat-card"><div class="stat-label">Collected</div><div class="stat-value green">$' + paid.toLocaleString() + '</div></div>';
  html += '<div class="stat-card"><div class="stat-label">Outstanding</div><div class="stat-value blue">$' + unpaid.toLocaleString() + '</div></div>';
  html += '<div class="stat-card"><div class="stat-label">Overdue</div><div class="stat-value" style="color:' + (overdue > 0 ? '#ef5350' : 'var(--muted)') + '">' + overdue + '</div></div>';
  html += '</div>';

  // Create invoice form
  html += '<div style="background:#0d0d0d;border:1px solid var(--border);border-radius:12px;padding:20px;margin-bottom:20px">';
  html += '<div style="font-size:0.8em;font-weight:700;color:var(--gold);margin-bottom:16px;text-transform:uppercase;letter-spacing:1px">&#43; New Invoice</div>';
  html += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px">';
  html += '<div><div style="font-size:0.68em;color:var(--muted);margin-bottom:5px;text-transform:uppercase;letter-spacing:1px">Client Name</div><input class="form-input" id="inv-name" placeholder="Business name"></div>';
  html += '<div><div style="font-size:0.68em;color:var(--muted);margin-bottom:5px;text-transform:uppercase;letter-spacing:1px">Email</div><input class="form-input" id="inv-email" type="email" placeholder="client@email.com"></div>';
  html += '<div><div style="font-size:0.68em;color:var(--muted);margin-bottom:5px;text-transform:uppercase;letter-spacing:1px">Description</div><input class="form-input" id="inv-desc" placeholder="Monthly AI Services" value="Monthly AI Services"></div>';
  html += '<div><div style="font-size:0.68em;color:var(--muted);margin-bottom:5px;text-transform:uppercase;letter-spacing:1px">Amount ($)</div><input class="form-input" id="inv-amount" type="number" value="500"></div>';
  html += '<div><div style="font-size:0.68em;color:var(--muted);margin-bottom:5px;text-transform:uppercase;letter-spacing:1px">Due in (days)</div><input class="form-input" id="inv-due" type="number" value="7"></div>';
  html += '</div>';
  html += '<div style="display:flex;gap:8px">';
  html += '<button class="btn" onclick="agCreateInvoice()" style="flex:1">Create Invoice</button>';
  html += '<button class="btn btn-outline" onclick="agCreateInvoice(true)" style="flex:1">Create + Send Email</button>';
  html += '</div></div>';

  if (invs.length === 0) {
    html += '<div style="text-align:center;padding:30px;color:var(--muted);font-size:0.85em">No invoices yet.</div>';
  } else {
    html += '<div style="font-size:0.72em;text-transform:uppercase;letter-spacing:1px;color:var(--muted);font-weight:700;margin-bottom:12px">All Invoices</div>';
    invs.forEach(inv => {
      const isPaid = inv.status === 'paid';
      const isOverdue = !isPaid && new Date(inv.due_date+'Z') < new Date();
      const statusColor = isPaid ? '#00c853' : (isOverdue ? '#ef5350' : '#42a5f5');
      const statusText = isPaid ? 'PAID' : (isOverdue ? 'OVERDUE' : 'UNPAID');
      html += '<div style="background:#0d0d0d;border:1px solid var(--border);border-radius:12px;padding:16px;margin-bottom:10px">';
      html += '<div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px;margin-bottom:10px">';
      html += '<div><div style="font-weight:700">' + esc(inv.client_name) + '</div>';
      html += '<div style="font-size:0.75em;color:var(--muted);margin-top:2px">' + esc(inv.description) + ' &bull; Due ' + (inv.due_date||'').slice(0,10) + '</div></div>';
      html += '<div style="text-align:right"><div style="font-size:1.2em;font-weight:800;color:var(--gold)">$' + (inv.amount||0).toLocaleString() + '</div>';
      html += '<div style="font-size:0.7em;font-weight:700;color:' + statusColor + ';margin-top:2px">' + statusText + '</div></div>';
      html += '</div>';
      html += '<div style="display:flex;gap:6px;flex-wrap:wrap">';
      if (!isPaid) html += '<button class="btn-sm btn-green" onclick="agMarkPaid(\'' + inv.id + '\')">&#10003; Mark Paid</button>';
      if (inv.client_email && !isPaid) html += '<button class="btn-sm btn-outline" onclick="agSendInvoice(\'' + inv.id + '\')">&#128231; Send Email</button>';
      if (inv.stripe_link) html += '<button class="btn-sm btn-outline" onclick="navigator.clipboard.writeText(\'' + esc(inv.stripe_link) + '\').then(()=>toast(\'Payment link copied!\',\'success\'))">Copy Pay Link</button>';
      if (!isPaid) html += '<button class="btn-sm btn-outline" onclick="agDeleteInvoice(\'' + inv.id + '\')">Delete</button>';
      html += '</div>';
      if (inv.sent_at) html += '<div style="font-size:0.7em;color:var(--muted);margin-top:8px">Sent ' + new Date(inv.sent_at+'Z').toLocaleString() + '</div>';
      if (inv.paid_at) html += '<div style="font-size:0.7em;color:#00c853;margin-top:4px">Paid ' + new Date(inv.paid_at+'Z').toLocaleString() + '</div>';
      html += '</div>';
    });
  }
  el.innerHTML = html;
}

async function agCreateInvoice(sendEmail) {
  const name = document.getElementById('inv-name')?.value?.trim();
  const email = document.getElementById('inv-email')?.value?.trim();
  const amount = parseFloat(document.getElementById('inv-amount')?.value || 500);
  if (!name) { toast('Client name required', 'error'); return; }
  const body = {
    client_name: name, client_email: email,
    description: document.getElementById('inv-desc')?.value?.trim() || 'Monthly AI Services',
    amount, due_days: parseInt(document.getElementById('inv-due')?.value || 7),
  };
  try {
    const inv = await api('/api/invoices/create', {method:'POST', body:JSON.stringify(body)});
    if (inv.id) {
      toast('Invoice created!', 'success');
      if (sendEmail && email) {
        await api('/api/invoices/' + inv.id + '/send', {method:'POST'});
        toast('Invoice emailed to ' + email, 'success');
      }
      agRenderInvoices(document.getElementById('ag-content'));
    }
  } catch(e) { toast('Error', 'error'); }
}

async function agMarkPaid(iid) {
  await api('/api/invoices/' + iid + '/mark-paid', {method:'POST'});
  toast('Marked as paid!', 'success');
  agRenderInvoices(document.getElementById('ag-content'));
}

async function agSendInvoice(iid) {
  const r = await api('/api/invoices/' + iid + '/send', {method:'POST'});
  if (r.status === 'ok') toast('Invoice sent!', 'success');
  else toast('Send failed: ' + (r.error||''), 'error');
  agRenderInvoices(document.getElementById('ag-content'));
}

async function agDeleteInvoice(iid) {
  if (!confirm('Delete invoice?')) return;
  await api('/api/invoices/' + iid + '/delete', {method:'POST'});
  agRenderInvoices(document.getElementById('ag-content'));
}

// ═══════════════════════════════════
// PIPELINE / CRM UI
// ═══════════════════════════════════
const STAGE_COLORS = {cold:'#555', contacted:'#42a5f5', demo:'#7c4dff', proposal:'#D4AF37', negotiation:'#ff9800', signed:'#00c853', lost:'#ef5350'};
const STAGE_LABELS = {cold:'Cold', contacted:'Contacted', demo:'Demo', proposal:'Proposal', negotiation:'Negotiating', signed:'Signed', lost:'Lost'};

async function agRenderPipeline(el) {
  el.innerHTML = '<div style="color:var(--muted);font-size:0.85em;padding:10px 0">Loading pipeline...</div>';
  let leads = [];
  try { leads = await api('/api/pipeline'); } catch(e) {}

  const byStage = {};
  const stages = ['cold','contacted','demo','proposal','negotiation','signed','lost'];
  stages.forEach(s => { byStage[s] = leads.filter(l => l.stage === s); });

  const totalValue = leads.filter(l => l.stage !== 'lost').reduce((s,l) => s + (l.value||0), 0);
  const signedValue = byStage['signed'].reduce((s,l) => s + (l.value||0), 0);

  let html = '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:20px">';
  html += '<div class="stat-card"><div class="stat-label">Pipeline Value</div><div class="stat-value gold">$' + totalValue.toLocaleString() + '</div></div>';
  html += '<div class="stat-card"><div class="stat-label">Signed</div><div class="stat-value green">$' + signedValue.toLocaleString() + '</div></div>';
  html += '<div class="stat-card"><div class="stat-label">Active Leads</div><div class="stat-value blue">' + leads.filter(l=>l.stage!=='lost'&&l.stage!=='signed').length + '</div></div>';
  html += '</div>';

  // Add lead form
  html += '<div style="background:#0d0d0d;border:1px solid var(--border);border-radius:12px;padding:20px;margin-bottom:20px">';
  html += '<div style="font-size:0.8em;font-weight:700;color:var(--gold);margin-bottom:16px;text-transform:uppercase;letter-spacing:1px">&#43; Add Lead</div>';
  html += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px">';
  html += '<div><div style="font-size:0.68em;color:var(--muted);margin-bottom:5px;text-transform:uppercase;letter-spacing:1px">Business Name *</div><input class="form-input" id="pl-biz" placeholder="Business name"></div>';
  html += '<div><div style="font-size:0.68em;color:var(--muted);margin-bottom:5px;text-transform:uppercase;letter-spacing:1px">Industry</div><input class="form-input" id="pl-type" placeholder="e.g. Auto Repair"></div>';
  html += '<div><div style="font-size:0.68em;color:var(--muted);margin-bottom:5px;text-transform:uppercase;letter-spacing:1px">Contact</div><input class="form-input" id="pl-contact" placeholder="Owner name"></div>';
  html += '<div><div style="font-size:0.68em;color:var(--muted);margin-bottom:5px;text-transform:uppercase;letter-spacing:1px">Phone</div><input class="form-input" id="pl-phone" placeholder="+1..."></div>';
  html += '<div><div style="font-size:0.68em;color:var(--muted);margin-bottom:5px;text-transform:uppercase;letter-spacing:1px">Email</div><input class="form-input" id="pl-email" placeholder="owner@business.com"></div>';
  html += '<div><div style="font-size:0.68em;color:var(--muted);margin-bottom:5px;text-transform:uppercase;letter-spacing:1px">Deal Value ($)</div><input class="form-input" id="pl-value" type="number" value="1500"></div>';
  html += '</div>';
  html += '<div style="display:flex;gap:8px;align-items:center;margin-bottom:12px">';
  html += '<div style="flex:1"><div style="font-size:0.68em;color:var(--muted);margin-bottom:5px;text-transform:uppercase;letter-spacing:1px">Stage</div>';
  html += '<select class="form-input" id="pl-stage" style="appearance:auto">';
  stages.forEach(s => html += '<option value="' + s + '">' + STAGE_LABELS[s] + '</option>');
  html += '</select></div>';
  html += '<div style="flex:1"><div style="font-size:0.68em;color:var(--muted);margin-bottom:5px;text-transform:uppercase;letter-spacing:1px">Source</div>';
  html += '<select class="form-input" id="pl-source" style="appearance:auto"><option value="manual">Manual</option><option value="outreach">Cold Outreach</option><option value="referral">Referral</option><option value="inbound">Inbound</option></select></div>';
  html += '</div>';
  html += '<button class="btn" onclick="agAddLead()" style="width:100%">Add to Pipeline</button>';
  html += '</div>';

  // Kanban view
  html += '<div style="display:flex;gap:12px;overflow-x:auto;padding-bottom:8px">';
  stages.forEach(s => {
    const sLeads = byStage[s];
    const color = STAGE_COLORS[s];
    html += '<div style="min-width:200px;flex-shrink:0">';
    html += '<div style="font-size:0.7em;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:' + color + ';margin-bottom:10px;display:flex;justify-content:space-between">';
    html += '<span>' + STAGE_LABELS[s] + '</span><span style="color:var(--muted)">' + sLeads.length + '</span></div>';
    sLeads.forEach(l => {
      html += '<div style="background:#0d0d0d;border:1px solid ' + color + '33;border-left:3px solid ' + color + ';border-radius:10px;padding:12px;margin-bottom:8px">';
      html += '<div style="font-weight:700;font-size:0.88em;margin-bottom:4px">' + esc(l.business_name) + '</div>';
      html += '<div style="font-size:0.72em;color:var(--muted);margin-bottom:8px">' + esc(l.contact_name||'') + (l.contact_phone ? ' &bull; ' + esc(l.contact_phone) : '') + '</div>';
      html += '<div style="font-size:0.82em;font-weight:700;color:var(--gold);margin-bottom:8px">$' + (l.value||0).toLocaleString() + '</div>';
      html += '<div style="display:flex;gap:4px;flex-wrap:wrap">';
      html += '<button class="btn-sm btn-outline" onclick="agLeadNote(\'' + l.id + '\')" style="font-size:0.68em">Note</button>';
      stages.filter(s2 => s2 !== s).slice(0,2).forEach(s2 => {
        html += '<button class="btn-sm btn-outline" onclick="agMoveStage(\'' + l.id + '\',\'' + s2 + '\')" style="font-size:0.68em;border-color:' + STAGE_COLORS[s2] + '55;color:' + STAGE_COLORS[s2] + '">' + STAGE_LABELS[s2] + '</button>';
      });
      html += '<button class="btn-sm btn-outline" onclick="agDeleteLead(\'' + l.id + '\')" style="font-size:0.68em;color:#ef5350;border-color:#ef535033">X</button>';
      html += '</div></div>';
    });
    if (sLeads.length === 0) html += '<div style="text-align:center;padding:20px;color:#333;font-size:0.75em">Empty</div>';
    html += '</div>';
  });
  html += '</div>';

  el.innerHTML = html;
}

async function agAddLead() {
  const biz = document.getElementById('pl-biz')?.value?.trim();
  if (!biz) { toast('Business name required', 'error'); return; }
  const body = {
    business_name: biz,
    business_type: document.getElementById('pl-type')?.value?.trim()||'',
    contact_name: document.getElementById('pl-contact')?.value?.trim()||'',
    contact_phone: document.getElementById('pl-phone')?.value?.trim()||'',
    contact_email: document.getElementById('pl-email')?.value?.trim()||'',
    value: parseFloat(document.getElementById('pl-value')?.value||1500),
    stage: document.getElementById('pl-stage')?.value||'cold',
    source: document.getElementById('pl-source')?.value||'manual',
  };
  const r = await api('/api/pipeline/add', {method:'POST', body:JSON.stringify(body)});
  if (r.id) { toast('Lead added!', 'success'); agRenderPipeline(document.getElementById('ag-content')); }
  else toast('Error', 'error');
}

async function agMoveStage(lid, stage) {
  await api('/api/pipeline/' + lid + '/stage', {method:'POST', body:JSON.stringify({stage})});
  toast('Moved to ' + STAGE_LABELS[stage], 'success');
  agRenderPipeline(document.getElementById('ag-content'));
}

async function agLeadNote(lid) {
  const note = prompt('Add a note to this lead:');
  if (!note) return;
  await api('/api/pipeline/' + lid + '/note', {method:'POST', body:JSON.stringify({note})});
  toast('Note saved', 'success');
}

async function agDeleteLead(lid) {
  if (!confirm('Remove this lead?')) return;
  await api('/api/pipeline/' + lid + '/delete', {method:'POST'});
  agRenderPipeline(document.getElementById('ag-content'));
}

// ═══════════════════════════════════
// CALL LOGS UI
// ═══════════════════════════════════
async function agRenderCallLogs(el) {
  el.innerHTML = '<div style="color:var(--muted);font-size:0.85em;padding:10px 0">Loading call logs...</div>';
  let summaries = [];
  try { summaries = await api('/api/call-summaries'); } catch(e) {}
  summaries = summaries.reverse();

  const total = summaries.length;
  const booked = summaries.filter(s => s.appointment_booked).length;
  const convRate = total > 0 ? Math.round((booked/total)*100) : 0;

  let html = '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:20px">';
  html += '<div class="stat-card"><div class="stat-label">Calls Logged</div><div class="stat-value blue">' + total + '</div></div>';
  html += '<div class="stat-card"><div class="stat-label">Appts Booked</div><div class="stat-value green">' + booked + '</div></div>';
  html += '<div class="stat-card"><div class="stat-label">Conversion Rate</div><div class="stat-value gold">' + convRate + '%</div></div>';
  html += '</div>';

  const outcomeColor = {booked:'#00c853', info_only:'#42a5f5', missed:'#ef5350', transferred:'#D4AF37', unknown:'#555'};
  const outcomeLabel = {booked:'Booked', info_only:'Info Only', missed:'Missed', transferred:'Transferred', unknown:'Unknown'};

  if (summaries.length === 0) {
    html += '<div style="text-align:center;padding:40px;color:var(--muted);font-size:0.85em">No call logs yet. Calls are logged automatically by the AI receptionist.</div>';
  } else {
    summaries.forEach(s => {
      const oc = s.outcome || 'unknown';
      const color = outcomeColor[oc] || '#555';
      html += '<div style="background:#0d0d0d;border:1px solid var(--border);border-left:3px solid ' + color + ';border-radius:12px;padding:16px;margin-bottom:10px">';
      html += '<div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px;margin-bottom:8px">';
      html += '<div><div style="font-weight:700;font-size:0.9em">' + esc(s.caller_name||'Unknown Caller') + '</div>';
      html += '<div style="font-size:0.72em;color:var(--muted);margin-top:2px">' + esc(s.caller_number||'') + ' &bull; ' + (s.created_at||'').slice(0,16).replace('T',' ') + '</div></div>';
      html += '<div style="display:flex;align-items:center;gap:8px">';
      html += '<span style="font-size:0.7em;font-weight:700;color:' + color + '">' + (outcomeLabel[oc]||oc) + '</span>';
      if (s.duration_seconds) html += '<span style="font-size:0.7em;color:var(--muted)">' + Math.round(s.duration_seconds/60) + 'm</span>';
      html += '</div></div>';
      if (s.summary) html += '<div style="font-size:0.82em;color:#aaa;line-height:1.6;margin-bottom:8px;background:#111;border-radius:8px;padding:10px">' + esc(s.summary) + '</div>';
      if ((s.tags||[]).length) html += '<div style="display:flex;gap:6px;flex-wrap:wrap">' + s.tags.map(t => '<span style="background:#1a1a1a;border-radius:12px;padding:3px 10px;font-size:0.7em;color:var(--muted)">' + esc(t) + '</span>').join('') + '</div>';
      html += '</div>';
    });
  }
  el.innerHTML = html;
}

// ═══════════════════════════════════
// ANALYTICS UI
// ═══════════════════════════════════
async function agRenderAnalytics(el) {
  el.innerHTML = '<div style="color:var(--muted);font-size:0.85em;padding:10px 0">Loading analytics...</div>';
  let calls = [], invs = [], pipeline = [], props = [];
  try {
    [calls, invs, pipeline, props] = await Promise.all([
      api('/api/call-summaries'),
      api('/api/invoices'),
      api('/api/pipeline'),
      api('/api/proposals'),
    ]);
  } catch(e) {}

  const now = new Date();
  const day7 = new Date(now - 7*24*3600*1000);
  const day30 = new Date(now - 30*24*3600*1000);

  const calls7 = calls.filter(c => new Date(c.created_at+'Z') > day7).length;
  const calls30 = calls.filter(c => new Date(c.created_at+'Z') > day30).length;
  const revenue30 = invs.filter(i => i.status==='paid' && new Date(i.paid_at+'Z') > day30).reduce((s,i) => s + (i.amount||0), 0);
  const pipeline_value = pipeline.filter(l => !['lost','signed'].includes(l.stage)).reduce((s,l) => s + (l.value||0), 0);
  const closed_value = pipeline.filter(l => l.stage==='signed').reduce((s,l) => s + (l.value||0), 0);
  const conv_rate = calls.length > 0 ? Math.round((calls.filter(c=>c.appointment_booked).length/calls.length)*100) : 0;

  let html = '<div style="font-size:0.72em;text-transform:uppercase;letter-spacing:1px;color:var(--muted);font-weight:700;margin-bottom:16px">Overview</div>';
  html += '<div style="display:grid;grid-template-columns:repeat(2,1fr);gap:12px;margin-bottom:24px">';
  html += agStatBig('Calls This Week', calls7, 'blue');
  html += agStatBig('Calls This Month', calls30, 'blue');
  html += agStatBig('Revenue (30 days)', '$' + revenue30.toLocaleString(), 'gold');
  html += agStatBig('Pipeline Value', '$' + pipeline_value.toLocaleString(), 'gold');
  html += agStatBig('Total Closed', '$' + closed_value.toLocaleString(), 'green');
  html += agStatBig('Call → Booking Rate', conv_rate + '%', conv_rate > 30 ? 'green' : 'blue');
  html += '</div>';

  // Revenue trend (last 7 days bar chart)
  html += '<div style="background:#0d0d0d;border:1px solid var(--border);border-radius:12px;padding:20px;margin-bottom:20px">';
  html += '<div style="font-size:0.8em;font-weight:700;color:var(--gold);margin-bottom:16px">Invoice Status Breakdown</div>';
  const paid_cnt = invs.filter(i=>i.status==='paid').length;
  const unpaid_cnt = invs.filter(i=>i.status!=='paid').length;
  const total_cnt = invs.length || 1;
  html += '<div style="display:flex;gap:4px;height:20px;border-radius:6px;overflow:hidden;margin-bottom:8px">';
  if (paid_cnt > 0) html += '<div style="background:#00c853;flex:' + paid_cnt + '" title="Paid"></div>';
  if (unpaid_cnt > 0) html += '<div style="background:#333;flex:' + unpaid_cnt + '" title="Unpaid"></div>';
  html += '</div>';
  html += '<div style="display:flex;gap:16px;font-size:0.75em"><span style="color:#00c853">&#9632; Paid (' + paid_cnt + ')</span><span style="color:#555">&#9632; Unpaid (' + unpaid_cnt + ')</span></div>';
  html += '</div>';

  // Pipeline funnel
  html += '<div style="background:#0d0d0d;border:1px solid var(--border);border-radius:12px;padding:20px">';
  html += '<div style="font-size:0.8em;font-weight:700;color:var(--gold);margin-bottom:16px">Pipeline Funnel</div>';
  const stages = ['cold','contacted','demo','proposal','negotiation','signed'];
  const maxCount = Math.max(...stages.map(s => pipeline.filter(l=>l.stage===s).length), 1);
  stages.forEach(s => {
    const cnt = pipeline.filter(l => l.stage === s).length;
    const pct = Math.max((cnt/maxCount)*100, 2);
    html += '<div style="margin-bottom:8px"><div style="display:flex;justify-content:space-between;font-size:0.75em;margin-bottom:4px"><span style="color:' + (STAGE_COLORS[s]||'#555') + '">' + (STAGE_LABELS[s]||s) + '</span><span style="color:var(--muted)">' + cnt + '</span></div>';
    html += '<div style="background:#1a1a1a;border-radius:4px;height:8px"><div style="background:' + (STAGE_COLORS[s]||'#555') + ';width:' + pct + '%;height:100%;border-radius:4px;transition:width 0.5s"></div></div></div>';
  });
  html += '</div>';

  el.innerHTML = html;
}

function agStatBig(label, value, color) {
  const colors = {gold:'var(--gold)', green:'#00c853', blue:'#42a5f5'};
  return '<div style="background:#0d0d0d;border:1px solid var(--border);border-radius:12px;padding:18px"><div style="font-size:0.68em;text-transform:uppercase;letter-spacing:1px;color:var(--muted);margin-bottom:6px">' + label + '</div><div style="font-size:1.6em;font-weight:900;color:' + (colors[color]||'#e8e8e8') + '">' + value + '</div></div>';
}

// ═══════════════════════════════════
// SETTINGS PANELS (Automation Suite)
// ═══════════════════════════════════
async function loadAutomationSettings() {
  // Load all automation configs
  try {
    const [missedCfg, followCfg, reviewCfg, reminderCfg, depositCfg] = await Promise.all([
      api('/api/missed-call/config'),
      api('/api/followups/config'),
      api('/api/reviews/config'),
      api('/api/reminders/config'),
      api('/api/deposits/config'),
    ]);
    // Missed call
    const mc = document.getElementById('mc-enabled'); if(mc) mc.checked = missedCfg.enabled;
    const mm = document.getElementById('mc-message'); if(mm) mm.value = missedCfg.message;
    // Follow-ups
    const fe = document.getElementById('fu-enabled'); if(fe) fe.checked = followCfg.enabled;
    const fm = document.getElementById('fu-message'); if(fm) fm.value = followCfg.message;
    const fh = document.getElementById('fu-hours'); if(fh) fh.value = followCfg.delay_hours;
    // Reviews
    const re = document.getElementById('rv-enabled'); if(re) re.checked = reviewCfg.enabled;
    const rl = document.getElementById('rv-link'); if(rl) rl.value = reviewCfg.google_review_link;
    const rm = document.getElementById('rv-message'); if(rm) rm.value = reviewCfg.message;
    // Reminders
    const ren = document.getElementById('rm-enabled'); if(ren) ren.checked = reminderCfg.enabled;
    const rhb = document.getElementById('rm-hours'); if(rhb) rhb.value = reminderCfg.hours_before;
    const rmm = document.getElementById('rm-message'); if(rmm) rmm.value = reminderCfg.sms_message;
    // Deposits
    const den = document.getElementById('dp-enabled'); if(den) den.checked = depositCfg.enabled;
    const dam = document.getElementById('dp-amount'); if(dam) dam.value = depositCfg.amount;
  } catch(e) { console.log('Automation settings load error', e); }
}

async function saveAutomationSection(section) {
  const configs = {
    'missed-call': { endpoint: '/api/missed-call/config', fields: {enabled: 'mc-enabled', message: 'mc-message'} },
    'followup': { endpoint: '/api/followups/config', fields: {enabled: 'fu-enabled', message: 'fu-message', delay_hours: 'fu-hours'} },
    'review': { endpoint: '/api/reviews/config', fields: {enabled: 'rv-enabled', google_review_link: 'rv-link', message: 'rv-message'} },
    'reminder': { endpoint: '/api/reminders/config', fields: {enabled: 'rm-enabled', hours_before: 'rm-hours', sms_message: 'rm-message', sms_enabled: null} },
    'deposit': { endpoint: '/api/deposits/config', fields: {enabled: 'dp-enabled', amount: 'dp-amount'} },
  };
  const cfg = configs[section];
  if (!cfg) return;
  const data = {};
  for (const [key, id] of Object.entries(cfg.fields)) {
    if (!id) continue;
    const el = document.getElementById(id);
    if (!el) continue;
    if (el.type === 'checkbox') data[key] = el.checked;
    else if (el.type === 'number') data[key] = parseFloat(el.value)||0;
    else data[key] = el.value;
  }
  if (section === 'reminder') data['sms_enabled'] = true;
  try {
    await api(cfg.endpoint, {method:'POST', body:JSON.stringify(data)});
    toast('Saved!', 'success');
  } catch(e) { toast('Error saving', 'error'); }
}

"""

marker = 'async function agRenderProposals'
if marker in content:
    content = content.replace(marker, FEATURE_JS + marker)
    print('Feature JS injected')
else:
    print('WARNING: agRenderProposals not found')
    # fallback
    marker2 = 'function agRenderReferrals'
    if marker2 in content:
        content = content.replace(marker2, FEATURE_JS + marker2, 1)
        print('Feature JS injected (fallback)')

# ─────────────────────────────────────────────────────────────
# 4. Add Automation Suite section to Settings tab
# ─────────────────────────────────────────────────────────────
AUTOMATION_SETTINGS_HTML = '''
      <!-- ── AUTOMATION SUITE ── -->
      <div class="panel" style="margin-bottom:16px">
        <div class="panel-header">
          <div class="panel-title" style="font-size:0.95em">&#9889; Automation Suite</div>
        </div>
        <div style="font-size:0.78em;color:var(--muted);margin-bottom:20px;line-height:1.6">
          Configure automatic texts and emails that fire based on call events and appointments. All powered by your Twilio number.
        </div>

        <!-- Missed Call Text-Back -->
        <div style="background:#0a0a0a;border:1px solid var(--border);border-radius:12px;padding:18px;margin-bottom:14px">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px">
            <div>
              <div style="font-weight:700;font-size:0.88em">&#128241; Missed Call Text-Back</div>
              <div style="font-size:0.72em;color:var(--muted);margin-top:2px">Auto-text anyone who hangs up before the AI answers</div>
            </div>
            <label style="display:flex;align-items:center;gap:6px;cursor:pointer">
              <input type="checkbox" id="mc-enabled" style="accent-color:var(--gold);width:16px;height:16px">
              <span style="font-size:0.78em;color:var(--muted)">Enabled</span>
            </label>
          </div>
          <div style="margin-bottom:12px">
            <div style="font-size:0.68em;color:var(--muted);margin-bottom:5px;text-transform:uppercase;letter-spacing:1px">Message</div>
            <textarea class="form-input" id="mc-message" rows="3" style="resize:vertical" placeholder="Hey! We missed your call..."></textarea>
          </div>
          <button class="btn-sm btn-outline" onclick="saveAutomationSection('missed-call')">Save</button>
        </div>

        <!-- Smart Follow-Ups -->
        <div style="background:#0a0a0a;border:1px solid var(--border);border-radius:12px;padding:18px;margin-bottom:14px">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px">
            <div>
              <div style="font-weight:700;font-size:0.88em">&#128172; Smart Follow-Ups</div>
              <div style="font-size:0.72em;color:var(--muted);margin-top:2px">Auto-text callers who didn't book an appointment</div>
            </div>
            <label style="display:flex;align-items:center;gap:6px;cursor:pointer">
              <input type="checkbox" id="fu-enabled" style="accent-color:var(--gold);width:16px;height:16px">
              <span style="font-size:0.78em;color:var(--muted)">Enabled</span>
            </label>
          </div>
          <div style="display:grid;grid-template-columns:1fr 2fr;gap:12px;margin-bottom:12px">
            <div>
              <div style="font-size:0.68em;color:var(--muted);margin-bottom:5px;text-transform:uppercase;letter-spacing:1px">Send after (hrs)</div>
              <input class="form-input" id="fu-hours" type="number" value="2" min="0" max="72">
            </div>
            <div>
              <div style="font-size:0.68em;color:var(--muted);margin-bottom:5px;text-transform:uppercase;letter-spacing:1px">Message</div>
              <textarea class="form-input" id="fu-message" rows="2" style="resize:vertical"></textarea>
            </div>
          </div>
          <button class="btn-sm btn-outline" onclick="saveAutomationSection('followup')">Save</button>
        </div>

        <!-- Review Collection -->
        <div style="background:#0a0a0a;border:1px solid var(--border);border-radius:12px;padding:18px;margin-bottom:14px">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px">
            <div>
              <div style="font-weight:700;font-size:0.88em">&#11088; Review Collection</div>
              <div style="font-size:0.72em;color:var(--muted);margin-top:2px">Auto-text customers after appointments to collect Google reviews</div>
            </div>
            <label style="display:flex;align-items:center;gap:6px;cursor:pointer">
              <input type="checkbox" id="rv-enabled" style="accent-color:var(--gold);width:16px;height:16px">
              <span style="font-size:0.78em;color:var(--muted)">Enabled</span>
            </label>
          </div>
          <div style="margin-bottom:12px">
            <div style="font-size:0.68em;color:var(--muted);margin-bottom:5px;text-transform:uppercase;letter-spacing:1px">Google Review Link</div>
            <input class="form-input" id="rv-link" placeholder="https://g.page/r/YOURLINK/review">
          </div>
          <div style="margin-bottom:12px">
            <div style="font-size:0.68em;color:var(--muted);margin-bottom:5px;text-transform:uppercase;letter-spacing:1px">Message (use {name} and {link})</div>
            <textarea class="form-input" id="rv-message" rows="2" style="resize:vertical"></textarea>
          </div>
          <button class="btn-sm btn-outline" onclick="saveAutomationSection('review')">Save</button>
        </div>

        <!-- Appointment Reminders -->
        <div style="background:#0a0a0a;border:1px solid var(--border);border-radius:12px;padding:18px;margin-bottom:14px">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px">
            <div>
              <div style="font-weight:700;font-size:0.88em">&#9200; Appointment Reminders</div>
              <div style="font-size:0.72em;color:var(--muted);margin-top:2px">Auto-text customers before their appointment to reduce no-shows</div>
            </div>
            <label style="display:flex;align-items:center;gap:6px;cursor:pointer">
              <input type="checkbox" id="rm-enabled" style="accent-color:var(--gold);width:16px;height:16px">
              <span style="font-size:0.78em;color:var(--muted)">Enabled</span>
            </label>
          </div>
          <div style="display:grid;grid-template-columns:1fr 2fr;gap:12px;margin-bottom:12px">
            <div>
              <div style="font-size:0.68em;color:var(--muted);margin-bottom:5px;text-transform:uppercase;letter-spacing:1px">Hours Before</div>
              <input class="form-input" id="rm-hours" type="number" value="24" min="1" max="168">
            </div>
            <div>
              <div style="font-size:0.68em;color:var(--muted);margin-bottom:5px;text-transform:uppercase;letter-spacing:1px">SMS Message (use {time}, {name}, {business})</div>
              <textarea class="form-input" id="rm-message" rows="2" style="resize:vertical"></textarea>
            </div>
          </div>
          <div style="display:flex;gap:8px">
            <button class="btn-sm btn-outline" onclick="saveAutomationSection('reminder')">Save</button>
            <button class="btn-sm btn-outline" onclick="api('/api/reminders/run-check',{method:'POST'}).then(r=>toast('Check done. Sent: '+r.sent,'success'))">Run Check Now</button>
          </div>
        </div>

        <!-- Deposits -->
        <div style="background:#0a0a0a;border:1px solid var(--border);border-radius:12px;padding:18px">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px">
            <div>
              <div style="font-weight:700;font-size:0.88em">&#128178; Appointment Deposits</div>
              <div style="font-size:0.72em;color:var(--muted);margin-top:2px">Collect a deposit when the AI books an appointment (requires Stripe key)</div>
            </div>
            <label style="display:flex;align-items:center;gap:6px;cursor:pointer">
              <input type="checkbox" id="dp-enabled" style="accent-color:var(--gold);width:16px;height:16px">
              <span style="font-size:0.78em;color:var(--muted)">Enabled</span>
            </label>
          </div>
          <div style="margin-bottom:12px">
            <div style="font-size:0.68em;color:var(--muted);margin-bottom:5px;text-transform:uppercase;letter-spacing:1px">Deposit Amount ($)</div>
            <input class="form-input" id="dp-amount" type="number" value="50" min="1" style="width:120px">
          </div>
          <button class="btn-sm btn-outline" onclick="saveAutomationSection('deposit')">Save</button>
        </div>
      </div>

      <!-- ── STRIPE KEY ── -->
      <div class="panel" style="margin-bottom:16px">
        <div class="panel-header">
          <div class="panel-title" style="font-size:0.95em">&#9889; Stripe Integration</div>
        </div>
        <div style="font-size:0.78em;color:var(--muted);margin-bottom:16px;line-height:1.6">
          Add your Stripe secret key to enable payment links on invoices and deposits. Keys are stored securely on your server.
        </div>
        <div style="margin-bottom:12px">
          <div style="font-size:0.68em;color:var(--muted);margin-bottom:5px;text-transform:uppercase;letter-spacing:1px">Stripe Secret Key (sk_live_... or sk_test_...)</div>
          <input class="form-input" id="stripe-sk" type="password" placeholder="sk_live_..." style="font-family:monospace">
        </div>
        <button class="btn-sm btn-outline" onclick="saveStripeKey()">Save Key</button>
      </div>

'''

# Insert before toolkit wallet section in settings
old_settings_marker = '      <!-- ── TOOLKIT WALLET — Central Payment Method ── -->'
if old_settings_marker in content:
    content = content.replace(old_settings_marker, AUTOMATION_SETTINGS_HTML + old_settings_marker)
    print('Automation settings HTML added')
else:
    print('WARNING: settings wallet marker not found')

# ─────────────────────────────────────────────────────────────
# 5. Add loadAutomationSettings call + saveStripeKey fn
# ─────────────────────────────────────────────────────────────
old_load_settings = '''async function loadSettings() {
  stLoadSettings();
  loadAuthStatus();
  loadToolkitConfig();
  stLoadReferral();'''

new_load_settings = '''async function loadSettings() {
  stLoadSettings();
  loadAuthStatus();
  loadToolkitConfig();
  stLoadReferral();
  loadAutomationSettings();
  loadStripeKey();'''

if old_load_settings in content:
    content = content.replace(old_load_settings, new_load_settings)
    print('loadSettings patched')
else:
    print('WARNING: loadSettings not found')

# ─────────────────────────────────────────────────────────────
# 6. Add saveStripeKey / loadStripeKey functions
# ─────────────────────────────────────────────────────────────
STRIPE_FNS = """
async function loadStripeKey() {
  try {
    const r = await fetch(API + '/api/toolkit/config');
    const d = await r.json();
    if (d.stripe_secret_key) {
      const el = document.getElementById('stripe-sk');
      if (el) el.placeholder = 'sk_*** (saved)';
    }
  } catch(e) {}
}

async function saveStripeKey() {
  const key = document.getElementById('stripe-sk')?.value?.trim();
  if (!key) { toast('Enter a key first', 'error'); return; }
  try {
    await api('/api/toolkit/update-config', {method:'POST', body:JSON.stringify({stripe_secret_key: key})});
    toast('Stripe key saved!', 'success');
    document.getElementById('stripe-sk').value = '';
    document.getElementById('stripe-sk').placeholder = 'sk_*** (saved)';
  } catch(e) { toast('Error saving key', 'error'); }
}

"""

marker_stripe = 'async function loadAutomationSettings'
if marker_stripe in content:
    content = content.replace(marker_stripe, STRIPE_FNS + marker_stripe)
    print('Stripe functions added')
else:
    print('WARNING: loadAutomationSettings not found for stripe fn injection')

open('/root/janovum-toolkit/Janovum_Platform_v3.html', 'w').write(content)
print('All UI patches done, size:', len(content))
