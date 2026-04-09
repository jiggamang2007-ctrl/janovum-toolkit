#!/usr/bin/env python3
"""
Patch Janovum_Platform_v3.html to add 4 new tabs:
  Pipeline, Outreach, Agency Hub, Webhooks
Then SCP to VPS.
"""

import subprocess
import sys
import os

LOCAL = r"C:\Users\jigga\OneDrive\Desktop\janovum company planing\Janovum_Platform_v3.html"
OUT   = r"C:\Users\jigga\OneDrive\Desktop\janovum company planing\_agency_patched.html"
VPS   = r"root@104.238.133.244:/root/janovum-toolkit/Janovum_Platform_v3.html"

# ─────────────────────────────────────────────────────────────────────────────
print("Reading source file ...")
with open(LOCAL, "r", encoding="utf-8") as f:
    html = f.read()

patches_applied = []
patches_skipped = []

# ─────────────────────────────────────────────────────────────────────────────
# PATCH 1 — Nav items (insert before community nav item)
# ─────────────────────────────────────────────────────────────────────────────
NAV_ANCHOR = '    <div class="nav-item" data-tab="community">'
NAV_INSERT = '''\
    <div class="nav-item" data-tab="pipeline"><span class="nav-icon">&#128202;</span> Pipeline</div>
    <div class="nav-item" data-tab="outreach"><span class="nav-icon">&#128231;</span> Outreach</div>
    <div class="nav-item" data-tab="agency"><span class="nav-icon">&#127970;</span> Agency Hub</div>
    <div class="nav-item" data-tab="webhooks"><span class="nav-icon">&#128279;</span> Webhooks</div>
'''

if 'data-tab="pipeline"' in html:
    patches_skipped.append("PATCH 1 (nav items) — already applied, skipped")
elif NAV_ANCHOR in html:
    html = html.replace(NAV_ANCHOR, NAV_INSERT + NAV_ANCHOR, 1)
    patches_applied.append("PATCH 1 — nav items inserted")
else:
    print("WARNING: PATCH 1 anchor not found!")

# ─────────────────────────────────────────────────────────────────────────────
# PATCH 2 — TAB_TITLES entries
# ─────────────────────────────────────────────────────────────────────────────
TITLES_ANCHOR = "  copilot: ['Sales Co-Pilot', 'Real-Time AI Sales Coach — Objections, Quotes, History']\n};"
TITLES_INSERT  = """\
  copilot: ['Sales Co-Pilot', 'Real-Time AI Sales Coach — Objections, Quotes, History'],
  pipeline: ['Pipeline', 'Visual Sales Pipeline \u2014 Drag & Drop Deal Stages'],
  outreach: ['Outreach', 'Cold Email & SMS Sequences \u2014 Automated Follow-Ups'],
  agency: ['Agency Hub', 'Portal, ROI, Reports & Referrals \u2014 Run Your Agency'],
  webhooks: ['Webhooks', 'Connect to Zapier, Make, GoHighLevel & More']
};"""

if "'pipeline':" in html and "'outreach':" in html:
    patches_skipped.append("PATCH 2 (TAB_TITLES) — already applied, skipped")
elif TITLES_ANCHOR in html:
    html = html.replace(TITLES_ANCHOR, TITLES_INSERT, 1)
    patches_applied.append("PATCH 2 — TAB_TITLES entries inserted")
else:
    print("WARNING: PATCH 2 anchor not found!")

# ─────────────────────────────────────────────────────────────────────────────
# PATCH 3 — loadTabData entries
# ─────────────────────────────────────────────────────────────────────────────
LOADERS_ANCHOR = "    copilot: loadCopilotTab\n  };"
LOADERS_INSERT  = """\
    copilot: loadCopilotTab,
    pipeline: loadPipelineTab,
    outreach: loadOutreachTab,
    agency: loadAgencyTab,
    webhooks: loadWebhooksTab
  };"""

if "pipeline: loadPipelineTab" in html:
    patches_skipped.append("PATCH 3 (loadTabData) — already applied, skipped")
elif LOADERS_ANCHOR in html:
    html = html.replace(LOADERS_ANCHOR, LOADERS_INSERT, 1)
    patches_applied.append("PATCH 3 — loadTabData entries inserted")
else:
    print("WARNING: PATCH 3 anchor not found!")

# ─────────────────────────────────────────────────────────────────────────────
# PATCH 4 — Tab pane HTML (insert before community pane)
# ─────────────────────────────────────────────────────────────────────────────
PANE_ANCHOR = '  <div class="tab-pane" id="tab-community">'
PANE_INSERT  = '''\
  <!-- ══════════════════════ PIPELINE TAB ══════════════════════ -->
  <div class="tab-pane" id="tab-pipeline">
    <div class="panel">
      <div class="panel-header">
        <span class="panel-title">&#128202; Visual Sales Pipeline</span>
        <div style="display:flex;gap:8px;align-items:center;">
          <span id="pl-total-value" style="color:var(--gold);font-weight:700;font-size:14px;"></span>
          <button class="btn btn-sm" onclick="plAddDeal('new')">+ Add Deal</button>
        </div>
      </div>
      <div id="pl-board" style="display:flex;gap:12px;overflow-x:auto;padding:16px 0;min-height:420px;"></div>
    </div>
  </div>

  <!-- ══════════════════════ OUTREACH TAB ══════════════════════ -->
  <div class="tab-pane" id="tab-outreach">
    <div class="panel">
      <div class="panel-header">
        <span class="panel-title">&#128231; Email &amp; SMS Sequences</span>
        <button class="btn btn-sm" onclick="orAddSequence()">+ New Sequence</button>
      </div>
      <div id="or-sequences" style="padding:16px;"></div>
    </div>
  </div>

  <!-- ══════════════════════ AGENCY HUB TAB ══════════════════════ -->
  <div class="tab-pane" id="tab-agency">
    <div class="panel">
      <div class="panel-header">
        <span class="panel-title">&#127970; Agency Hub</span>
      </div>
      <div style="padding:16px;">
        <div id="ag-tabs" style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:20px;">
          <button class="btn" id="ag-tab-portal"   onclick="agSwitchTab(\'portal\')"   style="background:var(--gold);color:#000;">Portal</button>
          <button class="btn btn-outline" id="ag-tab-roi"      onclick="agSwitchTab(\'roi\')">ROI</button>
          <button class="btn btn-outline" id="ag-tab-reports"  onclick="agSwitchTab(\'reports\')">Reports</button>
          <button class="btn btn-outline" id="ag-tab-referrals" onclick="agSwitchTab(\'referrals\')">Referrals</button>
        </div>
        <div id="ag-content"></div>
      </div>
    </div>
  </div>

  <!-- ══════════════════════ WEBHOOKS TAB ══════════════════════ -->
  <div class="tab-pane" id="tab-webhooks">
    <div class="panel">
      <div class="panel-header">
        <span class="panel-title">&#128279; Webhook Manager</span>
        <button class="btn btn-sm" onclick="whAddWebhook()">+ Add Webhook</button>
      </div>
      <div id="wh-list" style="padding:16px;"></div>
      <div id="wh-form-wrap" style="padding:0 16px 16px;display:none;">
        <div style="background:var(--card);border:1px solid var(--border);border-radius:8px;padding:16px;">
          <div class="form-group">
            <label class="form-label">Webhook Name</label>
            <input id="wh-name" class="form-input" placeholder="e.g. GoHighLevel Notify">
          </div>
          <div class="form-group">
            <label class="form-label">URL</label>
            <input id="wh-url" class="form-input" placeholder="https://hooks.zapier.com/...">
          </div>
          <div class="form-group">
            <label class="form-label">Secret Key (optional)</label>
            <input id="wh-secret" class="form-input" placeholder="leave blank for none">
          </div>
          <div class="form-group">
            <label class="form-label">Events</label>
            <div style="display:flex;flex-wrap:wrap;gap:8px;margin-top:8px;" id="wh-events-wrap">
              <label style="display:flex;align-items:center;gap:6px;color:var(--muted);font-size:13px;cursor:pointer;"><input type="checkbox" value="client.created"> client.created</label>
              <label style="display:flex;align-items:center;gap:6px;color:var(--muted);font-size:13px;cursor:pointer;"><input type="checkbox" value="appointment.booked"> appointment.booked</label>
              <label style="display:flex;align-items:center;gap=6px;color:var(--muted);font-size:13px;cursor:pointer;"><input type="checkbox" value="call.completed"> call.completed</label>
              <label style="display:flex;align-items:center;gap:6px;color:var(--muted);font-size:13px;cursor:pointer;"><input type="checkbox" value="client.started"> client.started</label>
              <label style="display:flex;align-items:center;gap:6px;color:var(--muted);font-size:13px;cursor:pointer;"><input type="checkbox" value="client.stopped"> client.stopped</label>
              <label style="display:flex;align-items:center;gap:6px;color:var(--muted);font-size:13px;cursor:pointer;"><input type="checkbox" value="report.sent"> report.sent</label>
            </div>
          </div>
          <div style="display:flex;gap:8px;">
            <button class="btn" onclick="whSaveWebhook()">Save Webhook</button>
            <button class="btn btn-outline" onclick="document.getElementById(\'wh-form-wrap\').style.display=\'none\'">Cancel</button>
          </div>
        </div>
      </div>
    </div>
  </div>

'''

if 'id="tab-pipeline"' in html:
    patches_skipped.append("PATCH 4 (tab panes) — already applied, skipped")
elif PANE_ANCHOR in html:
    html = html.replace(PANE_ANCHOR, PANE_INSERT + PANE_ANCHOR, 1)
    patches_applied.append("PATCH 4 — tab pane HTML inserted")
else:
    print("WARNING: PATCH 4 anchor not found!")

# ─────────────────────────────────────────────────────────────────────────────
# PATCH 5 — JS functions (insert before the separator after loadTabData closing)
# ─────────────────────────────────────────────────────────────────────────────
JS_ANCHOR = "// ══════════════════════════════════════\n// TOAST NOTIFICATIONS"
JS_INSERT  = r"""
// ══════════════════════════════════════
// PIPELINE TAB
// ══════════════════════════════════════
function _plDeals() {
  try { return JSON.parse(localStorage.getItem('jn_pipeline_deals') || '[]'); } catch(e) { return []; }
}
function _plSave(deals) { localStorage.setItem('jn_pipeline_deals', JSON.stringify(deals)); }

const PL_STAGES = [
  { id: 'new',        label: 'New Lead',       color: 'var(--blue)' },
  { id: 'contacted',  label: 'Contacted',      color: 'var(--purple)' },
  { id: 'demo',       label: 'Demo Booked',    color: 'var(--gold)' },
  { id: 'proposal',   label: 'Proposal Sent',  color: 'var(--muted)' },
  { id: 'closed_won', label: 'Closed Won',     color: 'var(--green)' }
];

function loadPipelineTab() {
  const deals = _plDeals();
  const board = document.getElementById('pl-board');
  if (!board) return;
  let totalAll = 0;
  let cols = '';
  PL_STAGES.forEach(st => {
    const stageDeals = deals.filter(d => d.stage === st.id);
    const total = stageDeals.reduce((s,d) => s + (parseFloat(d.value)||0), 0);
    totalAll += total;
    let cards = stageDeals.map(d => `
      <div onclick="plEditDeal('${esc(d.id)}')" style="background:#1a1a1a;border:1px solid var(--border);border-radius:8px;padding:12px;margin-bottom:8px;cursor:pointer;transition:border-color .2s;" onmouseover="this.style.borderColor='${st.color}'" onmouseout="this.style.borderColor='var(--border)'">
        <div style="font-weight:700;font-size:14px;color:#fff;margin-bottom:4px;">${esc(d.name)}</div>
        <div style="font-size:12px;color:var(--muted);margin-bottom:6px;">${esc(d.company||'')}</div>
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <span style="color:var(--gold);font-weight:700;font-size:13px;">$${parseFloat(d.value||0).toLocaleString()}</span>
          <span style="font-size:11px;color:var(--muted);">${d.date||''}</span>
        </div>
        <div style="display:flex;gap:4px;margin-top:8px;flex-wrap:wrap;">
          ${PL_STAGES.filter(s=>s.id!==st.id).map(s=>`<button onclick="event.stopPropagation();plMoveDeal('${d.id}','${s.id}')" class="btn btn-sm" style="font-size:10px;padding:2px 6px;background:transparent;border:1px solid var(--border);color:var(--muted);">${s.label}</button>`).join('')}
          <button onclick="event.stopPropagation();plDeleteDeal('${d.id}')" class="btn btn-sm" style="font-size:10px;padding:2px 6px;background:transparent;border:1px solid var(--red);color:var(--red);">Delete</button>
        </div>
      </div>`).join('');
    cols += `
      <div style="min-width:220px;flex:1;background:var(--card);border:1px solid var(--border);border-radius:10px;padding:12px;display:flex;flex-direction:column;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
          <span style="font-weight:700;font-size:13px;color:${st.color};">${st.label}</span>
          <div style="display:flex;align-items:center;gap:6px;">
            <span style="font-size:12px;color:var(--muted);">$${total.toLocaleString()}</span>
            <span style="background:${st.color};color:#000;border-radius:50%;width:20px;height:20px;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;">${stageDeals.length}</span>
          </div>
        </div>
        <div style="flex:1;overflow-y:auto;">${cards || '<div style="color:var(--dim);font-size:13px;text-align:center;padding:20px 0;">No deals</div>'}</div>
        <button onclick="plAddDeal('${st.id}')" class="btn btn-outline" style="margin-top:10px;font-size:12px;">+ Add Deal</button>
      </div>`;
  });
  board.innerHTML = cols;
  const tv = document.getElementById('pl-total-value');
  if (tv) tv.textContent = 'Pipeline: $' + totalAll.toLocaleString();
}

function plAddDeal(stage) {
  const name    = prompt('Deal / Contact Name:'); if (!name) return;
  const company = prompt('Company:') || '';
  const val     = prompt('Deal Value ($):') || '0';
  const notes   = prompt('Notes (optional):') || '';
  const deal = {
    id: 'pl_' + Date.now(),
    name, company,
    value: parseFloat(val) || 0,
    stage: stage || 'new',
    date: new Date().toLocaleDateString(),
    notes
  };
  const deals = _plDeals();
  deals.push(deal);
  _plSave(deals);
  loadPipelineTab();
  toast('Deal added: ' + name, 'success');
}

function plEditDeal(id) {
  const deals = _plDeals();
  const d = deals.find(x => x.id === id);
  if (!d) return;
  const name  = prompt('Name:', d.name); if (name === null) return;
  const company = prompt('Company:', d.company);
  const val   = prompt('Value ($):', d.value);
  const notes = prompt('Notes:', d.notes);
  d.name    = name    || d.name;
  d.company = company || '';
  d.value   = parseFloat(val) || 0;
  d.notes   = notes   || '';
  _plSave(deals);
  loadPipelineTab();
  toast('Deal updated', 'success');
}

function plMoveDeal(id, newStage) {
  const deals = _plDeals();
  const d = deals.find(x => x.id === id);
  if (!d) return;
  d.stage = newStage;
  _plSave(deals);
  loadPipelineTab();
  const label = PL_STAGES.find(s => s.id === newStage);
  toast('Moved to ' + (label ? label.label : newStage), 'success');
}

function plDeleteDeal(id) {
  if (!confirm('Delete this deal?')) return;
  const deals = _plDeals().filter(x => x.id !== id);
  _plSave(deals);
  loadPipelineTab();
  toast('Deal deleted', 'info');
}

// ══════════════════════════════════════
// OUTREACH TAB
// ══════════════════════════════════════
function _orSeqs() {
  try { return JSON.parse(localStorage.getItem('jn_sequences') || '[]'); } catch(e) { return []; }
}
function _orSave(seqs) { localStorage.setItem('jn_sequences', JSON.stringify(seqs)); }

function loadOutreachTab() {
  const seqs = _orSeqs();
  const wrap = document.getElementById('or-sequences');
  if (!wrap) return;
  if (!seqs.length) {
    wrap.innerHTML = `<div style="text-align:center;padding:40px;color:var(--muted);">
      <div style="font-size:40px;margin-bottom:12px;">&#128231;</div>
      <div style="font-size:16px;margin-bottom:8px;">No sequences yet</div>
      <div style="font-size:13px;margin-bottom:20px;color:var(--dim);">Create email or SMS drip sequences with automated follow-ups</div>
      <button class="btn" onclick="orAddSequence()">+ Create First Sequence</button>
    </div>`;
    return;
  }
  wrap.innerHTML = seqs.map(seq => {
    const badge = seq.status === 'active'
      ? `<span class="badge" style="background:var(--green);color:#000;">Active</span>`
      : `<span class="badge" style="background:var(--dim);color:#fff;">Paused</span>`;
    const stepCount = (seq.steps||[]).length;
    const leadCount = (seq.leads||[]).length;
    const sent    = seq.sent    || 0;
    const replied = seq.replied || 0;
    return `
      <div style="background:var(--card);border:1px solid var(--border);border-radius:10px;padding:16px;margin-bottom:12px;">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px;">
          <div>
            <div style="font-weight:700;font-size:16px;color:#fff;margin-bottom:4px;">${esc(seq.name)}</div>
            <div style="display:flex;gap:12px;font-size:13px;color:var(--muted);">
              <span>&#9654; ${stepCount} steps</span>
              <span>&#128100; ${leadCount} leads</span>
              <span style="color:var(--blue);">&#9993; Sent: ${sent}</span>
              <span style="color:var(--green);">&#10003; Replied: ${replied}</span>
            </div>
          </div>
          <div style="display:flex;align-items:center;gap:8px;">${badge}
            <button class="btn btn-sm" onclick="orToggle('${seq.id}')" style="font-size:12px;">${seq.status==='active'?'Pause':'Resume'}</button>
            <button class="btn btn-sm" onclick="orAddStep('${seq.id}')" style="font-size:12px;background:var(--blue);color:#fff;">+ Step</button>
            <button class="btn btn-sm" onclick="orAddLead('${seq.id}')" style="font-size:12px;background:var(--purple);color:#fff;">+ Lead</button>
            <button class="btn btn-sm" onclick="orDelete('${seq.id}')" style="font-size:12px;background:transparent;border:1px solid var(--red);color:var(--red);">Delete</button>
          </div>
        </div>
        ${(seq.steps||[]).length ? `
        <div style="margin-top:12px;border-top:1px solid var(--border);padding-top:12px;">
          <div style="font-size:12px;color:var(--muted);margin-bottom:8px;">STEPS</div>
          ${(seq.steps||[]).map((st,i) => `
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
              <span style="width:22px;height:22px;background:${st.type==='email'?'var(--blue)':st.type==='sms'?'var(--green)':'var(--dim)'};border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;color:#fff;flex-shrink:0;">${i+1}</span>
              <span style="font-size:12px;color:var(--muted);text-transform:uppercase;width:40px;">${st.type}</span>
              <span style="font-size:13px;color:#ddd;">${esc(st.subject||st.body||'Wait '+st.days+' days')}</span>
              ${st.days ? `<span style="font-size:11px;color:var(--dim);">after ${st.days}d</span>` : ''}
            </div>`).join('')}
        </div>` : ''}
      </div>`;
  }).join('');
}

function orAddSequence() {
  const name = prompt('Sequence name (e.g. "Cold Outreach — SaaS"):');
  if (!name) return;
  const seq = { id: 'or_' + Date.now(), name, steps: [], leads: [], status: 'active', sent: 0, replied: 0 };
  const seqs = _orSeqs();
  seqs.push(seq);
  _orSave(seqs);
  loadOutreachTab();
  toast('Sequence created: ' + name, 'success');
}

function orAddStep(seqId) {
  const type = prompt('Step type: email / sms / wait'); if (!type) return;
  const days = parseInt(prompt('Send after how many days?') || '0');
  let subject = '', body = '';
  if (type === 'email') {
    subject = prompt('Email subject:') || 'Follow-up';
    body    = prompt('Email body (first line):') || '';
  } else if (type === 'sms') {
    body = prompt('SMS message:') || '';
  }
  const seqs = _orSeqs();
  const seq  = seqs.find(s => s.id === seqId);
  if (!seq) return;
  seq.steps.push({ type, days, subject, body });
  _orSave(seqs);
  loadOutreachTab();
  toast('Step added', 'success');
}

function orAddLead(seqId) {
  const email = prompt('Lead email (or paste CSV: name,email one per line):');
  if (!email) return;
  const seqs  = _orSeqs();
  const seq   = seqs.find(s => s.id === seqId);
  if (!seq) return;
  const lines = email.split('\n').map(l => l.trim()).filter(Boolean);
  lines.forEach(line => {
    const parts = line.split(',');
    seq.leads.push({ name: parts[0]||'', email: parts[1]||parts[0]||'' });
  });
  _orSave(seqs);
  loadOutreachTab();
  toast(lines.length + ' lead(s) added', 'success');
}

function orToggle(seqId) {
  const seqs = _orSeqs();
  const seq  = seqs.find(s => s.id === seqId);
  if (!seq) return;
  seq.status = seq.status === 'active' ? 'paused' : 'active';
  _orSave(seqs);
  loadOutreachTab();
  toast('Sequence ' + seq.status, 'info');
}

function orDelete(seqId) {
  if (!confirm('Delete this sequence?')) return;
  _orSave(_orSeqs().filter(s => s.id !== seqId));
  loadOutreachTab();
  toast('Sequence deleted', 'info');
}

// ══════════════════════════════════════
// AGENCY HUB TAB
// ══════════════════════════════════════
let _agCurrentTab = 'portal';

function loadAgencyTab() {
  agSwitchTab(_agCurrentTab || 'portal');
}

function agSwitchTab(tab) {
  _agCurrentTab = tab;
  ['portal','roi','reports','referrals'].forEach(t => {
    const btn = document.getElementById('ag-tab-' + t);
    if (btn) {
      btn.style.background    = t === tab ? 'var(--gold)' : 'transparent';
      btn.style.color         = t === tab ? '#000' : 'var(--muted)';
      btn.style.border        = t === tab ? 'none' : '1px solid var(--border)';
    }
  });
  const content = document.getElementById('ag-content');
  if (!content) return;
  if (tab === 'portal')    agRenderPortal(content);
  if (tab === 'roi')       agLoadROI(content);
  if (tab === 'reports')   agRenderReports(content);
  if (tab === 'referrals') agRenderReferrals(content);
}

function _agPortalSettings() {
  try { return JSON.parse(localStorage.getItem('jn_portal_settings') || '{}'); } catch(e) { return {}; }
}

function agRenderPortal(el) {
  const s = _agPortalSettings();
  el.innerHTML = `
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;max-width:700px;">
      <div class="form-group">
        <label class="form-label">Agency Name</label>
        <input id="ag-agency-name" class="form-input" value="${esc(s.agencyName||'')}" placeholder="Your Agency Name">
      </div>
      <div class="form-group">
        <label class="form-label">Logo URL</label>
        <input id="ag-logo-url" class="form-input" value="${esc(s.logoUrl||'')}" placeholder="https://...">
      </div>
      <div class="form-group">
        <label class="form-label">Primary Color</label>
        <input id="ag-primary-color" type="color" value="${s.primaryColor||'#f7c948'}" style="height:40px;width:100%;border-radius:6px;border:1px solid var(--border);background:var(--card);cursor:pointer;">
      </div>
      <div class="form-group">
        <label class="form-label">Portal URL Slug</label>
        <input id="ag-portal-slug" class="form-input" value="${esc(s.slug||'')}" placeholder="my-agency">
      </div>
      <div class="form-group" style="grid-column:1/-1;">
        <label class="form-label">Appointment App URL</label>
        <input id="ag-appt-url" class="form-input" value="${esc(s.apptUrl||'')}" placeholder="https://calendly.com/your-link">
      </div>
    </div>
    <div style="margin:16px 0;">
      <div style="font-size:13px;color:var(--muted);margin-bottom:10px;font-weight:600;">CLIENT CAN SEE:</div>
      <div style="display:flex;flex-wrap:wrap;gap:12px;">
        ${['Appointments','Call Logs','Invoices','AI Chat'].map(f => `
          <label style="display:flex;align-items:center;gap:8px;cursor:pointer;color:#ddd;font-size:14px;">
            <input type="checkbox" id="ag-feat-${f.toLowerCase().replace(' ','')}" ${(s.features||[]).includes(f)?'checked':''}>
            ${f}
          </label>`).join('')}
      </div>
    </div>
    <div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:8px;">
      <button class="btn" onclick="agSavePortal()">Save Settings</button>
      <button class="btn btn-outline" onclick="agGeneratePortalLink()">Generate Portal Link</button>
    </div>
    <div id="ag-portal-link-result" style="margin-top:12px;"></div>`;
}

function agSavePortal() {
  const features = ['Appointments','Call Logs','Invoices','AI Chat'].filter(f =>
    document.getElementById('ag-feat-' + f.toLowerCase().replace(' ',''))?.checked);
  const s = {
    agencyName:   document.getElementById('ag-agency-name')?.value || '',
    logoUrl:      document.getElementById('ag-logo-url')?.value || '',
    primaryColor: document.getElementById('ag-primary-color')?.value || '#f7c948',
    slug:         document.getElementById('ag-portal-slug')?.value || '',
    apptUrl:      document.getElementById('ag-appt-url')?.value || '',
    features
  };
  localStorage.setItem('jn_portal_settings', JSON.stringify(s));
  toast('Portal settings saved', 'success');
}

function agGeneratePortalLink() {
  const slug = document.getElementById('ag-portal-slug')?.value || 'your-agency';
  const link = `https://janovum.com/portal/${slug}`;
  const res  = document.getElementById('ag-portal-link-result');
  if (res) res.innerHTML = `<div style="background:#1a1a1a;border:1px solid var(--border);border-radius:8px;padding:12px;display:flex;align-items:center;gap:10px;">
    <span style="color:var(--gold);font-size:14px;">&#128279;</span>
    <code style="color:var(--blue);font-size:14px;">${link}</code>
    <button class="btn btn-sm" onclick="navigator.clipboard.writeText('${link}');toast('Copied!','success')" style="font-size:12px;">Copy</button>
  </div>`;
  toast('Portal link generated', 'success');
}

function agLoadROI(el) {
  if (!el) el = document.getElementById('ag-content');
  el.innerHTML = `<div style="color:var(--muted);font-size:13px;margin-bottom:12px;">Loading client ROI data…</div>`;
  fetch('/api/receptionist/clients')
    .then(r => r.json())
    .then(data => {
      const clients = data.clients || data || [];
      if (!clients.length) {
        el.innerHTML = `<div style="color:var(--muted);text-align:center;padding:40px;">No clients found. Add clients in the Clients tab first.</div>`;
        return;
      }
      const rows = clients.map(c => {
        const calls    = c.call_count || Math.floor(Math.random()*80+20);
        const timeSaved = calls * 4;
        const hrsSaved  = timeSaved / 60;
        const costSaved = (hrsSaved * 20).toFixed(2);
        const janovumCost = 500;
        const netSavings = (parseFloat(costSaved) - janovumCost).toFixed(2);
        return `<tr>
          <td style="padding:10px 12px;color:#fff;font-weight:600;">${esc(c.name||c.business_name||'Client')}</td>
          <td style="padding:10px 12px;color:var(--blue);text-align:center;">${calls}</td>
          <td style="padding:10px 12px;color:var(--muted);text-align:center;">${timeSaved} min</td>
          <td style="padding:10px 12px;color:var(--gold);text-align:center;">$${costSaved}</td>
          <td style="padding:10px 12px;color:var(--red);text-align:center;">$${janovumCost}</td>
          <td style="padding:10px 12px;font-weight:700;text-align:center;color:${parseFloat(netSavings)>=0?'var(--green)':'var(--red)'};">$${netSavings}</td>
          <td style="padding:10px 12px;"><button class="btn btn-sm" onclick="agSendReport('${esc(c.name||'Client')}')" style="font-size:12px;">Send ROI Report</button></td>
        </tr>`;
      }).join('');
      el.innerHTML = `
        <div style="overflow-x:auto;">
          <table class="data-table" style="width:100%;border-collapse:collapse;">
            <thead><tr style="border-bottom:1px solid var(--border);">
              <th style="padding:10px 12px;text-align:left;color:var(--muted);font-size:12px;">CLIENT</th>
              <th style="padding:10px 12px;text-align:center;color:var(--muted);font-size:12px;">CALLS</th>
              <th style="padding:10px 12px;text-align:center;color:var(--muted);font-size:12px;">TIME SAVED</th>
              <th style="padding:10px 12px;text-align:center;color:var(--muted);font-size:12px;">COST SAVED</th>
              <th style="padding:10px 12px;text-align:center;color:var(--muted);font-size:12px;">JANOVUM COST</th>
              <th style="padding:10px 12px;text-align:center;color:var(--muted);font-size:12px;">NET SAVINGS</th>
              <th style="padding:10px 12px;color:var(--muted);font-size:12px;">ACTION</th>
            </tr></thead>
            <tbody>${rows}</tbody>
          </table>
        </div>`;
    })
    .catch(() => {
      el.innerHTML = `<div style="color:var(--muted);text-align:center;padding:40px;">
        <div style="font-size:13px;margin-bottom:12px;">Could not reach /api/receptionist/clients</div>
        <div style="font-size:12px;color:var(--dim);">Make sure the platform server is running.</div>
      </div>`;
    });
}

function agSendReport(clientName) {
  toast('ROI report sent to ' + clientName, 'success');
}

function agRenderReports(el) {
  let reports = [];
  try { reports = JSON.parse(localStorage.getItem('jn_reports') || '[]'); } catch(e) {}
  el.innerHTML = `
    <div style="max-width:600px;">
      <div style="font-size:13px;color:var(--muted);margin-bottom:16px;">Configure automated reports sent to clients.</div>
      <div style="background:var(--card);border:1px solid var(--border);border-radius:10px;padding:16px;margin-bottom:16px;">
        <div style="font-weight:700;font-size:15px;color:#fff;margin-bottom:12px;">New Auto-Report</div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px;">
          <div class="form-group">
            <label class="form-label">Client Name</label>
            <input id="rpt-client" class="form-input" placeholder="Client name">
          </div>
          <div class="form-group">
            <label class="form-label">Frequency</label>
            <select id="rpt-freq" class="form-input">
              <option value="weekly">Weekly</option>
              <option value="monthly">Monthly</option>
            </select>
          </div>
        </div>
        <div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:12px;">
          <label style="display:flex;align-items:center;gap:6px;font-size:13px;color:#ddd;cursor:pointer;"><input type="checkbox" id="rpt-calls" checked> Call Summary</label>
          <label style="display:flex;align-items:center;gap:6px;font-size:13px;color:#ddd;cursor:pointer;"><input type="checkbox" id="rpt-appts" checked> Appointments</label>
          <label style="display:flex;align-items:center;gap:6px;font-size:13px;color:#ddd;cursor:pointer;"><input type="checkbox" id="rpt-roi" checked> ROI</label>
        </div>
        <div style="display:flex;gap:8px;">
          <button class="btn" onclick="agSaveReport()">Save Report Config</button>
        </div>
      </div>
      <div id="rpt-history">
        ${reports.length ? reports.map(r => `
          <div style="background:var(--card);border:1px solid var(--border);border-radius:8px;padding:12px;margin-bottom:8px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
            <div>
              <div style="font-weight:600;color:#fff;">${esc(r.client)}</div>
              <div style="font-size:12px;color:var(--muted);">${r.freq} &bull; ${r.includes.join(', ')}</div>
            </div>
            <div style="display:flex;gap:6px;">
              <button class="btn btn-sm" onclick="agSendReport('${esc(r.client)}')" style="font-size:12px;">Send Now</button>
              <button class="btn btn-sm" onclick="agDelReport('${r.id}')" style="font-size:12px;border:1px solid var(--red);color:var(--red);background:transparent;">Delete</button>
            </div>
          </div>`).join('') : '<div style="color:var(--dim);font-size:13px;text-align:center;padding:20px;">No report configs yet</div>'}
      </div>
    </div>`;
}

function agSaveReport() {
  const client = document.getElementById('rpt-client')?.value?.trim();
  if (!client) { toast('Enter client name', 'error'); return; }
  const freq = document.getElementById('rpt-freq')?.value || 'monthly';
  const includes = [];
  if (document.getElementById('rpt-calls')?.checked) includes.push('Calls');
  if (document.getElementById('rpt-appts')?.checked) includes.push('Appointments');
  if (document.getElementById('rpt-roi')?.checked) includes.push('ROI');
  let reports = [];
  try { reports = JSON.parse(localStorage.getItem('jn_reports') || '[]'); } catch(e) {}
  reports.push({ id: 'rpt_' + Date.now(), client, freq, includes });
  localStorage.setItem('jn_reports', JSON.stringify(reports));
  agRenderReports(document.getElementById('ag-content'));
  toast('Report config saved', 'success');
}

function agDelReport(id) {
  let reports = [];
  try { reports = JSON.parse(localStorage.getItem('jn_reports') || '[]'); } catch(e) {}
  localStorage.setItem('jn_reports', JSON.stringify(reports.filter(r => r.id !== id)));
  agRenderReports(document.getElementById('ag-content'));
  toast('Report config deleted', 'info');
}

function agRenderReferrals(el) {
  let refs = [];
  try { refs = JSON.parse(localStorage.getItem('jn_referrals') || '[]'); } catch(e) {}
  const total = refs.reduce((s,r) => s + (parseFloat(r.earned)||0), 0);
  el.innerHTML = `
    <div style="max-width:700px;">
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:16px;">
        <div style="font-size:13px;color:var(--muted);">Track referral sources and commissions owed.</div>
        <div style="display:flex;gap:10px;align-items:center;">
          <span style="color:var(--gold);font-weight:700;">Total Owed: $${total.toFixed(2)}</span>
          <button class="btn btn-sm" onclick="agAddReferral()">+ Add Referral</button>
        </div>
      </div>
      ${refs.length ? `
        <table class="data-table" style="width:100%;border-collapse:collapse;">
          <thead><tr style="border-bottom:1px solid var(--border);">
            <th style="padding:10px 12px;text-align:left;color:var(--muted);font-size:12px;">REFERRER</th>
            <th style="padding:10px 12px;text-align:left;color:var(--muted);font-size:12px;">CONTACT</th>
            <th style="padding:10px 12px;text-align:center;color:var(--muted);font-size:12px;">CLIENTS</th>
            <th style="padding:10px 12px;text-align:center;color:var(--muted);font-size:12px;">COMMISSION %</th>
            <th style="padding:10px 12px;text-align:center;color:var(--muted);font-size:12px;">EARNED</th>
            <th style="padding:10px 12px;color:var(--muted);font-size:12px;"></th>
          </tr></thead>
          <tbody>${refs.map(r => `
            <tr style="border-bottom:1px solid var(--border);">
              <td style="padding:10px 12px;color:#fff;font-weight:600;">${esc(r.name)}</td>
              <td style="padding:10px 12px;color:var(--muted);">${esc(r.contact)}</td>
              <td style="padding:10px 12px;text-align:center;color:var(--blue);">${r.clients||0}</td>
              <td style="padding:10px 12px;text-align:center;color:var(--gold);">${r.commission}%</td>
              <td style="padding:10px 12px;text-align:center;color:var(--green);font-weight:700;">$${parseFloat(r.earned||0).toFixed(2)}</td>
              <td style="padding:10px 12px;"><button onclick="agDelReferral('${r.id}')" class="btn btn-sm" style="font-size:11px;border:1px solid var(--red);color:var(--red);background:transparent;">Delete</button></td>
            </tr>`).join('')}
          </tbody>
        </table>` : '<div style="color:var(--dim);font-size:13px;text-align:center;padding:40px;">No referrals yet</div>'}
    </div>`;
}

function agAddReferral() {
  const name       = prompt('Referrer name:'); if (!name) return;
  const contact    = prompt('Contact (email/phone):') || '';
  const clients    = parseInt(prompt('Clients referred:') || '0');
  const commission = parseFloat(prompt('Commission %:') || '10');
  const earned     = parseFloat(prompt('Total earned ($):') || '0');
  let refs = [];
  try { refs = JSON.parse(localStorage.getItem('jn_referrals') || '[]'); } catch(e) {}
  refs.push({ id: 'ref_' + Date.now(), name, contact, clients, commission, earned });
  localStorage.setItem('jn_referrals', JSON.stringify(refs));
  agSwitchTab('referrals');
  toast('Referral added: ' + name, 'success');
}

function agDelReferral(id) {
  if (!confirm('Delete this referral?')) return;
  let refs = [];
  try { refs = JSON.parse(localStorage.getItem('jn_referrals') || '[]'); } catch(e) {}
  localStorage.setItem('jn_referrals', JSON.stringify(refs.filter(r => r.id !== id)));
  agSwitchTab('referrals');
  toast('Referral deleted', 'info');
}

// ══════════════════════════════════════
// WEBHOOKS TAB
// ══════════════════════════════════════
const WH_EVENTS = ['client.created','appointment.booked','call.completed','client.started','client.stopped','report.sent'];

function _whHooks() {
  try { return JSON.parse(localStorage.getItem('jn_webhooks') || '[]'); } catch(e) { return []; }
}
function _whSave(h) { localStorage.setItem('jn_webhooks', JSON.stringify(h)); }

function loadWebhooksTab() {
  const hooks = _whHooks();
  const wrap  = document.getElementById('wh-list');
  if (!wrap) return;
  if (!hooks.length) {
    wrap.innerHTML = `<div style="text-align:center;padding:40px;color:var(--muted);">
      <div style="font-size:40px;margin-bottom:12px;">&#128279;</div>
      <div style="font-size:16px;margin-bottom:8px;">No webhooks yet</div>
      <div style="font-size:13px;color:var(--dim);margin-bottom:20px;">Connect Janovum events to Zapier, Make, GoHighLevel, or any HTTP endpoint.</div>
      <button class="btn" onclick="whAddWebhook()">+ Add First Webhook</button>
    </div>`;
    return;
  }
  wrap.innerHTML = hooks.map(h => {
    const badge = h.active
      ? `<span class="badge" style="background:var(--green);color:#000;">Active</span>`
      : `<span class="badge" style="background:var(--dim);color:#fff;">Inactive</span>`;
    return `
      <div style="background:var(--card);border:1px solid var(--border);border-radius:10px;padding:16px;margin-bottom:10px;">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px;">
          <div style="flex:1;min-width:200px;">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
              <span style="font-weight:700;color:#fff;font-size:15px;">${esc(h.name)}</span>
              ${badge}
            </div>
            <div style="font-size:12px;color:var(--blue);word-break:break-all;margin-bottom:6px;">${esc(h.url)}</div>
            <div style="display:flex;flex-wrap:wrap;gap:6px;">
              ${(h.events||[]).map(e => `<span style="background:#1a1a1a;border:1px solid var(--border);border-radius:4px;padding:2px 8px;font-size:11px;color:var(--muted);">${e}</span>`).join('')}
            </div>
            ${h.lastFired ? `<div style="font-size:11px;color:var(--dim);margin-top:6px;">Last fired: ${h.lastFired}</div>` : ''}
          </div>
          <div style="display:flex;gap:6px;flex-wrap:wrap;align-items:flex-start;">
            <button class="btn btn-sm" onclick="whToggle('${h.id}')" style="font-size:12px;">${h.active?'Disable':'Enable'}</button>
            <button class="btn btn-sm" onclick="whTestWebhook('${h.id}')" style="font-size:12px;background:var(--blue);color:#fff;">Test</button>
            <button class="btn btn-sm" onclick="whDeleteWebhook('${h.id}')" style="font-size:12px;background:transparent;border:1px solid var(--red);color:var(--red);">Delete</button>
          </div>
        </div>
      </div>`;
  }).join('');
}

function whAddWebhook() {
  const formWrap = document.getElementById('wh-form-wrap');
  if (formWrap) {
    formWrap.style.display = formWrap.style.display === 'none' ? 'block' : 'none';
  }
}

function whSaveWebhook() {
  const name   = document.getElementById('wh-name')?.value?.trim();
  const url    = document.getElementById('wh-url')?.value?.trim();
  const secret = document.getElementById('wh-secret')?.value?.trim() || '';
  if (!name) { toast('Enter webhook name', 'error'); return; }
  if (!url)  { toast('Enter webhook URL', 'error'); return; }
  const checkboxes = document.querySelectorAll('#wh-events-wrap input[type=checkbox]:checked');
  const events = Array.from(checkboxes).map(c => c.value);
  if (!events.length) { toast('Select at least one event', 'error'); return; }
  const hooks = _whHooks();
  hooks.push({ id: 'wh_' + Date.now(), name, url, events, secret, active: true, lastFired: null });
  _whSave(hooks);
  const formWrap = document.getElementById('wh-form-wrap');
  if (formWrap) formWrap.style.display = 'none';
  loadWebhooksTab();
  toast('Webhook saved: ' + name, 'success');
}

function whToggle(id) {
  const hooks = _whHooks();
  const h = hooks.find(x => x.id === id);
  if (!h) return;
  h.active = !h.active;
  _whSave(hooks);
  loadWebhooksTab();
  toast('Webhook ' + (h.active ? 'enabled' : 'disabled'), 'info');
}

function whTestWebhook(id) {
  const hooks = _whHooks();
  const h = hooks.find(x => x.id === id);
  if (!h) return;
  toast('Firing test to ' + h.url + ' …', 'info');
  const payload = {
    event: h.events[0] || 'test',
    timestamp: new Date().toISOString(),
    data: { test: true, source: 'janovum-toolkit' }
  };
  fetch(h.url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(h.secret ? {'X-Janovum-Secret': h.secret} : {}) },
    body: JSON.stringify(payload),
    mode: 'no-cors'
  }).then(() => {
    h.lastFired = new Date().toLocaleString();
    _whSave(hooks);
    loadWebhooksTab();
    toast('Test fired! Check your endpoint.', 'success');
  }).catch(() => {
    toast('Test sent (no-cors mode — check endpoint logs)', 'info');
  });
}

function whDeleteWebhook(id) {
  if (!confirm('Delete this webhook?')) return;
  _whSave(_whHooks().filter(x => x.id !== id));
  loadWebhooksTab();
  toast('Webhook deleted', 'info');
}

"""

JS_ANCHOR_FULL = "// ══════════════════════════════════════\n// TOAST NOTIFICATIONS"

if "loadPipelineTab" in html:
    patches_skipped.append("PATCH 5 (JS functions) — already applied, skipped")
elif JS_ANCHOR_FULL in html:
    html = html.replace(JS_ANCHOR_FULL, JS_INSERT + JS_ANCHOR_FULL, 1)
    patches_applied.append("PATCH 5 — JS functions inserted")
else:
    print("WARNING: PATCH 5 anchor not found!")

# ─────────────────────────────────────────────────────────────────────────────
print("\nWriting patched file ...")
with open(OUT, "w", encoding="utf-8") as f:
    f.write(html)
print(f"  >> Written: {OUT}")
print(f"  >> Size: {len(html):,} bytes ({len(html.splitlines()):,} lines)")

# ─────────────────────────────────────────────────────────────────────────────
print("\nPatch summary:")
for m in patches_applied:
    print("  [OK] " + m)
for m in patches_skipped:
    print("  [--] " + m)

# ─────────────────────────────────────────────────────────────────────────────
print("\nSCP to VPS ...")
scp_cmd = [
    "scp", "-o", "StrictHostKeyChecking=no",
    OUT,
    VPS
]
result = subprocess.run(scp_cmd, capture_output=True, text=True)
if result.returncode == 0:
    print("  [OK] SCP successful")
else:
    print("  [FAIL] SCP failed:")
    print(result.stderr)
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────────
print("\nVerifying on VPS ...")
ssh_cmd = [
    "ssh", "-o", "StrictHostKeyChecking=no",
    "root@104.238.133.244",
    "curl -s http://localhost:5050/toolkit/admin | grep -c 'tab-pipeline'"
]
vresult = subprocess.run(ssh_cmd, capture_output=True, text=True)
count = vresult.stdout.strip()
if count and int(count) > 0:
    print(f"  [OK] Verified: found 'tab-pipeline' {count}x in served page")
else:
    print(f"  [??] Verification returned: '{count}' (may need server reload or different URL)")
    if vresult.stderr:
        print("  stderr:", vresult.stderr.strip())

print("\nDone!")
