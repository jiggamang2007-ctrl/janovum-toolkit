content = open('/root/janovum-toolkit/Janovum_Platform_v3.html').read()

old = '''function loadAgencyTab() {
  const el = document.getElementById('tab-agency');
  if (el && !el.querySelector('.loaded-indicator')) {
    el.insertAdjacentHTML('afterbegin', '<div class="loaded-indicator" style="display:none"></div>');
  }
}'''

new = r'''function agSwitchTab(tab) {
  document.querySelectorAll('#ag-tabs .btn').forEach(b => {
    b.style.background = '';
    b.style.color = '';
  });
  const active = document.getElementById('ag-tab-' + tab);
  if (active) { active.style.background = 'var(--gold)'; active.style.color = '#000'; }
  const el = document.getElementById('ag-content');
  if (tab === 'portal') agRenderPortals(el);
  else if (tab === 'roi') el.innerHTML = '<div style="color:var(--muted);padding:30px;text-align:center">ROI calculator coming soon.</div>';
  else if (tab === 'reports') el.innerHTML = '<div style="color:var(--muted);padding:30px;text-align:center">Client reports coming soon.</div>';
  else if (tab === 'referrals') el.innerHTML = '<div style="color:var(--muted);padding:30px;text-align:center">Referral system coming soon.</div>';
}

async function agRenderPortals(el) {
  el.innerHTML = '<div style="color:var(--muted);font-size:0.85em;padding:10px 0">Loading clients...</div>';
  let clients = [];
  try {
    const r = await fetch(API + '/api/receptionist/clients');
    const d = await r.json();
    clients = d.clients || [];
  } catch(e) {}

  const origin = window.location.origin;
  let html = '<div style="font-size:0.83em;color:var(--muted);margin-bottom:18px;line-height:1.5">Each client gets a branded mobile portal they can add to their home screen. Share the link after setup.</div>';

  if (clients.length === 0) {
    html += '<div style="text-align:center;padding:40px;color:var(--muted)">No clients yet. Deploy a client first.</div>';
  } else {
    clients.forEach(c => {
      const url = origin + '/portal/' + c.client_id;
      const running = c.running;
      html += '<div style="background:#0d0d0d;border:1px solid var(--border);border-radius:14px;padding:20px;margin-bottom:14px">';
      html += '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;flex-wrap:wrap;gap:8px">';
      html += '<div><div style="font-weight:700;font-size:1em">' + esc(c.business_name) + '</div>';
      html += '<div style="font-size:0.72em;color:var(--muted);margin-top:2px">' + esc(c.client_id) + ' &bull; Port ' + c.port + '</div></div>';
      html += '<span class="badge ' + (running ? 'badge-running' : 'badge-stopped') + '">' + (running ? 'RUNNING' : 'STOPPED') + '</span></div>';
      html += '<div style="background:#111;border:1px solid var(--border);border-radius:8px;padding:10px 14px;margin-bottom:12px;display:flex;align-items:center;justify-content:space-between;gap:8px;flex-wrap:wrap">';
      html += '<span style="font-family:monospace;font-size:0.75em;color:var(--gold);word-break:break-all">' + esc(url) + '</span>';
      html += '<button class="btn-sm btn-outline" onclick="navigator.clipboard.writeText(\'' + esc(url) + '\').then(()=>toast(\'Link copied!\',\'success\'))">Copy</button></div>';
      html += '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px">';
      html += '<a href="' + esc(url) + '" target="_blank" class="btn-sm btn-green" style="text-decoration:none">&#128279; Open Portal</a>';
      html += '<button class="btn-sm btn-outline" onclick="agShowQR(\'' + esc(url) + '\',\'' + esc(c.business_name) + '\')">&#9726; QR Code</button>';
      html += '<button class="btn-sm btn-outline" onclick="agEditPortal(\'' + esc(c.client_id) + '\')">&#9998; Customize</button></div>';
      html += '<div id="ag-edit-' + esc(c.client_id) + '" style="display:none;background:#0a0a0a;border:1px solid var(--border);border-radius:10px;padding:16px">';
      html += '<div style="font-size:0.78em;font-weight:700;color:var(--gold);margin-bottom:12px">Customize Portal</div>';
      html += '<div style="margin-bottom:10px"><label style="font-size:0.72em;color:var(--muted);display:block;margin-bottom:4px">Welcome Message</label>';
      html += '<input class="form-input" id="ag-msg-' + esc(c.client_id) + '" placeholder="Message shown at top of portal..." style="font-size:0.82em"></div>';
      html += '<div style="margin-bottom:14px"><label style="font-size:0.72em;color:var(--muted);display:block;margin-bottom:4px">Brand Color</label>';
      html += '<div style="display:flex;align-items:center;gap:10px"><input type="color" id="ag-color-' + esc(c.client_id) + '" value="#D4AF37" style="width:44px;height:34px;border:1px solid var(--border);border-radius:6px;cursor:pointer;padding:2px">';
      html += '<span style="font-size:0.78em;color:var(--muted)">Portal accent color</span></div></div>';
      html += '<div style="display:flex;gap:8px">';
      html += '<button class="btn-sm btn-green" onclick="agSavePortal(\'' + esc(c.client_id) + '\')">Save Changes</button>';
      html += '<button class="btn-sm btn-outline" onclick="document.getElementById(\'ag-edit-' + esc(c.client_id) + '\').style.display=\'none\'">Cancel</button></div></div></div>';
    });
  }

  html += '<div id="ag-qr-modal" style="display:none;position:fixed;inset:0;background:#000000cc;z-index:9999;align-items:center;justify-content:center;flex-direction:column">';
  html += '<div style="background:#111;border:1px solid var(--border);border-radius:16px;padding:28px;text-align:center;max-width:300px;width:90%">';
  html += '<div id="ag-qr-title" style="font-weight:700;margin-bottom:16px;font-size:0.95em"></div>';
  html += '<img id="ag-qr-img" src="" style="width:200px;height:200px;border-radius:8px;background:#fff;padding:8px" alt="QR Code">';
  html += '<div style="margin-top:12px;font-size:0.73em;color:var(--muted)">Scan to open client portal</div>';
  html += '<button class="btn btn-outline" style="margin-top:14px;width:100%" onclick="document.getElementById(\'ag-qr-modal\').style.display=\'none\'">Close</button>';
  html += '</div></div>';

  el.innerHTML = html;
}

function agEditPortal(clientId) {
  const wrap = document.getElementById('ag-edit-' + clientId);
  if (!wrap) return;
  const isOpen = wrap.style.display !== 'none';
  wrap.style.display = isOpen ? 'none' : 'block';
  if (!isOpen) {
    fetch(API + '/portal/' + clientId + '/api/data').then(r => r.json()).then(d => {
      const msgEl = document.getElementById('ag-msg-' + clientId);
      const colorEl = document.getElementById('ag-color-' + clientId);
      if (msgEl && d.portal_message) msgEl.value = d.portal_message;
      if (colorEl && d.portal_color) colorEl.value = d.portal_color;
    }).catch(() => {});
  }
}

async function agSavePortal(clientId) {
  const msg = document.getElementById('ag-msg-' + clientId)?.value || '';
  const color = document.getElementById('ag-color-' + clientId)?.value || '#D4AF37';
  try {
    const r = await fetch(API + '/portal/' + clientId + '/api/save', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ portal_message: msg, portal_color: color })
    });
    const d = await r.json();
    if (d.status === 'ok') { toast('Portal updated!', 'success'); document.getElementById('ag-edit-' + clientId).style.display = 'none'; }
    else toast('Save failed', 'error');
  } catch(e) { toast('Save failed', 'error'); }
}

function agShowQR(url, name) {
  const modal = document.getElementById('ag-qr-modal');
  if (!modal) return;
  document.getElementById('ag-qr-title').textContent = name + ' Portal';
  document.getElementById('ag-qr-img').src = 'https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=' + encodeURIComponent(url);
  modal.style.display = 'flex';
}

function loadAgencyTab() {
  agSwitchTab('portal');
}'''

if old in content:
    content = content.replace(old, new)
    open('/root/janovum-toolkit/Janovum_Platform_v3.html', 'w').write(content)
    print('Done, size:', len(content))
else:
    print('NOT FOUND - checking...')
    idx = content.find('function loadAgencyTab')
    print('loadAgencyTab at index:', idx)
    print(repr(content[idx:idx+200]))
