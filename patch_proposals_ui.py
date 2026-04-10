content = open('/root/janovum-toolkit/Janovum_Platform_v3.html').read()

# 1. Add Proposals button to agency hub tab bar
old_tabs = "          <button class=\"btn btn-outline\" id=\"ag-tab-referrals\" onclick=\"agSwitchTab('referrals')\">Referrals</button>"
new_tabs = "          <button class=\"btn btn-outline\" id=\"ag-tab-referrals\" onclick=\"agSwitchTab('referrals')\">Referrals</button>\n          <button class=\"btn btn-outline\" id=\"ag-tab-proposals\" onclick=\"agSwitchTab('proposals')\">&#128221; Proposals</button>"

if old_tabs in content:
    content = content.replace(old_tabs, new_tabs)
    print('Tab button added')
else:
    print('WARNING: tab button not found')

# 2. Add proposals case to agSwitchTab
old_switch = "    if (tab === 'referrals') { agRenderReferrals(el); return; }"
new_switch = """    if (tab === 'referrals') { agRenderReferrals(el); return; }
    if (tab === 'proposals') { agRenderProposals(el); return; }"""

if old_switch in content:
    content = content.replace(old_switch, new_switch)
    print('Switch case added')
else:
    # Try alternate
    old_switch2 = "    if (tab === 'referrals') agRenderReferrals(el);"
    new_switch2 = "    if (tab === 'referrals') agRenderReferrals(el);\n    if (tab === 'proposals') { agRenderProposals(el); return; }"
    if old_switch2 in content:
        content = content.replace(old_switch2, new_switch2)
        print('Switch case added (alt)')
    else:
        print('WARNING: switch case not found')

# 3. Add full proposals UI function — inject before agRenderReferrals
PROPOSALS_JS = r"""
async function agRenderProposals(el) {
  el.innerHTML = '<div style="color:var(--muted);font-size:0.85em;padding:10px 0">Loading proposals...</div>';

  let props = [];
  try {
    const r = await fetch(API + '/api/proposals');
    props = await r.json();
  } catch(e) {}

  const statusColor = { draft: 'var(--muted)', sent: '#42a5f5', viewed: '#D4AF37', signed: '#00c853' };
  const statusIcon = { draft: '&#9998;', sent: '&#128231;', viewed: '&#128065;', signed: '&#10003;' };

  let html = '';

  // Summary stats
  const total = props.length;
  const signed = props.filter(p => p.status === 'signed').length;
  const viewed = props.filter(p => p.status === 'viewed').length;
  const totalValue = props.filter(p => p.status === 'signed').reduce((s,p) => s + (p.total||0), 0);

  html += '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:20px">';
  html += '<div class="stat-card"><div class="stat-label">Total</div><div class="stat-value">' + total + '</div></div>';
  html += '<div class="stat-card"><div class="stat-label">Viewed</div><div class="stat-value blue">' + viewed + '</div></div>';
  html += '<div class="stat-card"><div class="stat-label">Signed</div><div class="stat-value green">' + signed + '</div></div>';
  html += '<div class="stat-card"><div class="stat-label">Revenue</div><div class="stat-value gold">$' + totalValue.toLocaleString() + '</div></div>';
  html += '</div>';

  // Create proposal form
  html += '<div style="background:#0d0d0d;border:1px solid var(--border);border-radius:12px;padding:20px;margin-bottom:20px">';
  html += '<div style="font-size:0.8em;font-weight:700;color:var(--gold);margin-bottom:16px;text-transform:uppercase;letter-spacing:1px">&#43; New Proposal</div>';
  html += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px">';
  html += '<div><div style="font-size:0.68em;color:var(--muted);margin-bottom:5px;text-transform:uppercase;letter-spacing:1px">Business Name *</div><input class="form-input" id="prop-biz" placeholder="e.g. Mike\'s Auto Shop"></div>';
  html += '<div><div style="font-size:0.68em;color:var(--muted);margin-bottom:5px;text-transform:uppercase;letter-spacing:1px">Industry</div><input class="form-input" id="prop-type" placeholder="e.g. Auto Repair"></div>';
  html += '<div><div style="font-size:0.68em;color:var(--muted);margin-bottom:5px;text-transform:uppercase;letter-spacing:1px">Contact Name</div><input class="form-input" id="prop-name" placeholder="Owner\'s name"></div>';
  html += '<div><div style="font-size:0.68em;color:var(--muted);margin-bottom:5px;text-transform:uppercase;letter-spacing:1px">Email</div><input class="form-input" id="prop-email" type="email" placeholder="owner@business.com"></div>';
  html += '<div><div style="font-size:0.68em;color:var(--muted);margin-bottom:5px;text-transform:uppercase;letter-spacing:1px">Setup Fee ($)</div><input class="form-input" id="prop-setup" type="number" value="1000"></div>';
  html += '<div><div style="font-size:0.68em;color:var(--muted);margin-bottom:5px;text-transform:uppercase;letter-spacing:1px">Monthly Fee ($)</div><input class="form-input" id="prop-monthly" type="number" value="500"></div>';
  html += '</div>';
  html += '<div style="margin-bottom:12px"><div style="font-size:0.68em;color:var(--muted);margin-bottom:5px;text-transform:uppercase;letter-spacing:1px">Services (comma-separated)</div>';
  html += '<input class="form-input" id="prop-services" placeholder="AI Receptionist, Appointment Booking, 24/7 Call Handling"></div>';
  html += '<div style="margin-bottom:16px"><div style="font-size:0.68em;color:var(--muted);margin-bottom:5px;text-transform:uppercase;letter-spacing:1px">Notes</div>';
  html += '<input class="form-input" id="prop-notes" placeholder="Any special terms or notes for this client..."></div>';
  html += '<button class="btn" onclick="agCreateProposal()" style="width:100%">Generate Proposal Link</button>';
  html += '</div>';

  // Proposal list
  if (props.length === 0) {
    html += '<div style="text-align:center;padding:30px;color:var(--muted);font-size:0.85em">No proposals yet — create one above.</div>';
  } else {
    html += '<div style="font-size:0.72em;text-transform:uppercase;letter-spacing:1px;color:var(--muted);font-weight:700;margin-bottom:12px">All Proposals</div>';
    props.forEach(p => {
      const sc = statusColor[p.status] || 'var(--muted)';
      const si = statusIcon[p.status] || '&#9998;';
      const url = 'https://janovum.com/proposal/' + p.id;
      html += '<div style="background:#0d0d0d;border:1px solid var(--border);border-radius:12px;padding:16px;margin-bottom:12px">';
      html += '<div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px;margin-bottom:12px">';
      html += '<div><div style="font-weight:700;font-size:0.95em">' + esc(p.business_name) + '</div>';
      html += '<div style="font-size:0.72em;color:var(--muted);margin-top:2px">' + esc(p.client_name || '') + (p.client_name ? ' &mdash; ' : '') + '$' + (p.total||0).toLocaleString() + ' total</div></div>';
      html += '<div style="display:flex;align-items:center;gap:6px;font-size:0.75em;font-weight:700;color:' + sc + '">' + si + ' ' + p.status.toUpperCase() + '</div>';
      html += '</div>';
      html += '<div style="background:#111;border:1px solid var(--border);border-radius:8px;padding:10px 14px;display:flex;align-items:center;justify-content:space-between;gap:8px;flex-wrap:wrap;margin-bottom:10px">';
      html += '<span style="font-family:monospace;font-size:0.72em;color:var(--gold)">' + esc(url) + '</span>';
      html += '<div style="display:flex;gap:6px">';
      html += '<button class="btn-sm btn-outline" onclick="navigator.clipboard.writeText(\'' + esc(url) + '\').then(()=>toast(\'Copied!\',\'success\'))">Copy</button>';
      html += '<button class="btn-sm btn-outline" onclick="window.open(\'' + esc(url) + '\',\'_blank\')">View</button>';
      if (p.status !== 'signed') html += '<button class="btn-sm btn-outline" onclick="agDeleteProposal(\'' + p.id + '\')">Delete</button>';
      html += '</div></div>';
      if (p.viewed_at) html += '<div style="font-size:0.7em;color:var(--muted)">&#128065; Viewed: ' + new Date(p.viewed_at+'Z').toLocaleString() + '</div>';
      if (p.signed_at) html += '<div style="font-size:0.7em;color:#00c853;margin-top:3px">&#10003; Signed by ' + esc(p.signed_by) + ' on ' + new Date(p.signed_at+'Z').toLocaleString() + '</div>';
      html += '</div>';
    });
  }

  el.innerHTML = html;
}

async function agCreateProposal() {
  const biz = document.getElementById('prop-biz')?.value?.trim();
  if (!biz) { toast('Business name required', 'error'); return; }
  const servicesRaw = document.getElementById('prop-services')?.value?.trim();
  const services = servicesRaw ? servicesRaw.split(',').map(s => s.trim()).filter(Boolean) : [];
  const body = {
    business_name: biz,
    business_type: document.getElementById('prop-type')?.value?.trim() || '',
    contact_name: document.getElementById('prop-name')?.value?.trim() || '',
    contact_email: document.getElementById('prop-email')?.value?.trim() || '',
    services,
    setup_fee: parseInt(document.getElementById('prop-setup')?.value || 1000),
    monthly_fee: parseInt(document.getElementById('prop-monthly')?.value || 500),
    notes: document.getElementById('prop-notes')?.value?.trim() || '',
  };
  try {
    const r = await fetch(API + '/api/proposals/generate', {
      method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(body)
    });
    const d = await r.json();
    if (d.id) {
      const url = 'https://janovum.com/proposal/' + d.id;
      navigator.clipboard.writeText(url).catch(()=>{});
      toast('Proposal created! Link copied: ' + url, 'success');
      agRenderProposals(document.getElementById('ag-content'));
    } else toast('Failed to create proposal', 'error');
  } catch(e) { toast('Error', 'error'); }
}

async function agDeleteProposal(pid) {
  if (!confirm('Delete this proposal?')) return;
  try {
    await fetch(API + '/api/proposals/' + pid + '/delete', { method: 'POST' });
    toast('Deleted', 'success');
    agRenderProposals(document.getElementById('ag-content'));
  } catch(e) { toast('Error', 'error'); }
}

"""

# Inject before agRenderReferrals
marker = 'async function agRenderReferrals'
if marker in content:
    content = content.replace(marker, PROPOSALS_JS + marker)
    print('Proposals JS injected')
else:
    print('WARNING: agRenderReferrals not found — trying alternate marker')
    marker2 = 'function agRenderReferrals'
    if marker2 in content:
        content = content.replace(marker2, PROPOSALS_JS + marker2, 1)
        print('Proposals JS injected (alt)')
    else:
        print('ERROR: no marker found')

open('/root/janovum-toolkit/Janovum_Platform_v3.html', 'w').write(content)
print('Done, size:', len(content))
