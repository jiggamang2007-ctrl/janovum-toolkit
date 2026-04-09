content = open('/root/janovum-toolkit/Janovum_Platform_v3.html').read()

# ── 1. Replace agRenderReferrals stub with full UI ──────────────────────────
old_referrals = "function agRenderReferrals(el) {\n  el.innerHTML = '<div style=\"color:var(--muted);padding:30px;text-align:center\">Referral system coming soon.</div>';\n}"

new_referrals = r"""function agRenderReferrals(el) {
  el.innerHTML = '<div style="color:var(--muted);font-size:0.85em;padding:10px 0">Loading referrals...</div>';
  agLoadReferrals(el);
}

async function agLoadReferrals(el) {
  // Load all client referral data
  let refs = [];
  let clients = [];
  try {
    const [rRes, cRes] = await Promise.all([
      fetch(API + '/api/referral/all'),
      fetch(API + '/api/receptionist/clients')
    ]);
    refs = await rRes.json();
    const cd = await cRes.json();
    clients = cd.clients || [];
  } catch(e) {}

  const refMap = {};
  refs.forEach(r => { refMap[r.client_id] = r; });

  let html = '';

  // Summary stats
  const totalClicks = refs.reduce((s,r) => s + r.clicks, 0);
  const totalConversions = refs.reduce((s,r) => s + r.conversions, 0);
  const totalEarnings = refs.reduce((s,r) => s + r.earnings, 0);

  html += '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:20px">';
  html += '<div class="stat-card"><div class="stat-label">Total Clicks</div><div class="stat-value blue">' + totalClicks + '</div></div>';
  html += '<div class="stat-card"><div class="stat-label">Conversions</div><div class="stat-value green">' + totalConversions + '</div></div>';
  html += '<div class="stat-card"><div class="stat-label">Rewards Earned</div><div class="stat-value gold">$' + totalEarnings + '</div></div>';
  html += '</div>';

  // Global reward setting
  html += '<div style="background:#0d0d0d;border:1px solid var(--border);border-radius:12px;padding:16px;margin-bottom:20px">';
  html += '<div style="font-size:0.8em;font-weight:700;color:var(--gold);margin-bottom:10px">&#9881; Reward Settings</div>';
  html += '<div style="font-size:0.78em;color:var(--muted);margin-bottom:12px">Set how much a referrer earns when someone they refer signs up and pays.</div>';
  html += '<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">';
  html += '<div style="display:flex;align-items:center;gap:6px"><span style="font-size:0.82em;color:var(--muted)">$</span><input class="form-input" id="ag-global-reward" type="number" value="100" min="0" style="width:90px;font-size:0.85em"> <span style="font-size:0.78em;color:var(--muted)">per conversion</span></div>';
  html += '<button class="btn-sm btn-green" onclick="agSetGlobalReward()">Apply to All</button>';
  html += '<span style="font-size:0.72em;color:var(--muted)">Or set per-client below</span>';
  html += '</div></div>';

  // Per-client referral cards
  html += '<div style="font-size:0.72em;text-transform:uppercase;letter-spacing:1px;color:var(--muted);font-weight:700;margin-bottom:12px">Client Referral Links</div>';

  if (clients.length === 0) {
    html += '<div style="text-align:center;padding:30px;color:var(--muted)">No clients yet.</div>';
  } else {
    clients.forEach(c => {
      const ref = refMap[c.client_id];
      const hasCode = ref && ref.code;
      html += '<div style="background:#0d0d0d;border:1px solid var(--border);border-radius:12px;padding:16px;margin-bottom:12px">';
      html += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;flex-wrap:wrap;gap:8px">';
      html += '<div><div style="font-weight:700">' + esc(c.business_name) + '</div>';
      html += '<div style="font-size:0.72em;color:var(--muted)">' + esc(c.client_id) + '</div></div>';
      if (hasCode) {
        html += '<div style="display:flex;gap:16px;font-size:0.78em">';
        html += '<span>&#128199; ' + ref.clicks + ' clicks</span>';
        html += '<span style="color:var(--green)">&#10003; ' + ref.conversions + ' conversions</span>';
        html += '<span style="color:var(--gold)">$' + ref.earnings + ' earned</span>';
        html += '</div>';
      }
      html += '</div>';

      if (hasCode) {
        const url = 'https://janovum.com/refer/' + ref.code;
        html += '<div style="background:#111;border:1px solid var(--border);border-radius:8px;padding:10px 14px;margin-bottom:10px;display:flex;align-items:center;justify-content:space-between;gap:8px;flex-wrap:wrap">';
        html += '<span style="font-family:monospace;font-size:0.75em;color:var(--gold)">' + esc(url) + '</span>';
        html += '<div style="display:flex;gap:6px">';
        html += '<button class="btn-sm btn-outline" onclick="navigator.clipboard.writeText(\'' + esc(url) + '\').then(()=>toast(\'Copied!\',\'success\'))">Copy</button>';
        html += '<button class="btn-sm btn-outline" onclick="agShowQR(\'' + esc(url) + '\',\'' + esc(c.business_name) + ' Referral\')">QR</button>';
        html += '</div></div>';
        html += '<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">';
        html += '<span style="font-size:0.75em;color:var(--muted)">Reward: $</span>';
        html += '<input class="form-input" id="ag-reward-' + esc(c.client_id) + '" type="number" value="' + (ref.reward_per_conversion||100) + '" min="0" style="width:80px;font-size:0.82em">';
        html += '<span style="font-size:0.75em;color:var(--muted)">per signup</span>';
        html += '<button class="btn-sm btn-outline" onclick="agUpdateReward(\'' + esc(c.client_id) + '\')">Update</button>';
        html += '<button class="btn-sm btn-outline" onclick="agMarkConverted(\'' + ref.code + '\')">+ Mark Converted</button>';
        html += '</div>';
      } else {
        html += '<button class="btn btn-outline" style="width:100%;font-size:0.82em" onclick="agGenerateReferral(\'' + esc(c.client_id) + '\')">&#128279; Generate Referral Link</button>';
      }
      html += '</div>';
    });
  }

  // How it works
  html += '<div style="background:#0d0d0d;border:1px solid var(--border);border-radius:12px;padding:16px;margin-top:8px">';
  html += '<div style="font-size:0.8em;font-weight:700;color:var(--gold);margin-bottom:12px">&#128161; How It Works</div>';
  html += '<div style="display:flex;flex-direction:column;gap:8px;font-size:0.78em;color:var(--muted)">';
  html += '<div>1. Generate a unique referral link for each client</div>';
  html += '<div>2. Client shares it with other businesses they know</div>';
  html += '<div>3. When someone signs up through the link, you mark it as converted</div>';
  html += '<div>4. The client earns their reward — discount off their bill or cash</div>';
  html += '<div>5. You get a new paying client with zero outreach cost</div>';
  html += '</div></div>';

  el.innerHTML = html;
}

async function agGenerateReferral(clientId) {
  try {
    const r = await fetch(API + '/api/referral/generate', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ client_id: clientId, reward: 100 })
    });
    const d = await r.json();
    if (d.code) {
      toast('Referral link created!', 'success');
      agRenderReferrals(document.getElementById('ag-content'));
    } else toast('Failed to generate', 'error');
  } catch(e) { toast('Error', 'error'); }
}

async function agUpdateReward(clientId) {
  const reward = parseInt(document.getElementById('ag-reward-' + clientId)?.value || 100);
  try {
    const r = await fetch(API + '/api/referral/set-reward', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ client_id: clientId, reward })
    });
    const d = await r.json();
    if (d.status === 'ok') toast('Reward updated!', 'success');
    else toast('Update failed', 'error');
  } catch(e) { toast('Error', 'error'); }
}

async function agMarkConverted(code) {
  if (!confirm('Mark this referral as converted? This adds +1 conversion and credits the reward.')) return;
  try {
    const r = await fetch(API + '/api/referral/convert', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ code })
    });
    const d = await r.json();
    if (d.status === 'ok') {
      toast('Conversion recorded! $' + d.earnings + ' total earned', 'success');
      agRenderReferrals(document.getElementById('ag-content'));
    } else toast('Error: ' + (d.error||'failed'), 'error');
  } catch(e) { toast('Error', 'error'); }
}

async function agSetGlobalReward() {
  const reward = parseInt(document.getElementById('ag-global-reward')?.value || 100);
  try {
    const cRes = await fetch(API + '/api/receptionist/clients');
    const cd = await cRes.json();
    const clients = cd.clients || [];
    for (const c of clients) {
      await fetch(API + '/api/referral/set-reward', {
        method: 'POST', headers: {'Content-Type':'application/json'},
        body: JSON.stringify({ client_id: c.client_id, reward })
      });
    }
    toast('Reward updated for all clients', 'success');
    agRenderReferrals(document.getElementById('ag-content'));
  } catch(e) { toast('Error', 'error'); }
}"""

# ── 2. Add referral section to client portal ──────────────────────────────
old_portal_powered = '''<div class="powered">Powered by <a href="https://janovum.com">Janovum AI</a></div>

<script>
var CLIENT_ID = '{{CLIENT_ID}}';'''

new_portal_powered = '''<div id="referralSection" style="display:none;margin:0 20px 16px;background:#111;border:1px solid #D4AF3733;border-radius:14px;padding:16px">
  <div style="font-size:0.8em;font-weight:700;color:#D4AF37;margin-bottom:8px">&#127873; Refer a Friend — Earn Rewards</div>
  <div style="font-size:0.75em;color:#888;margin-bottom:12px;line-height:1.5">Know another business that could use an AI receptionist? Share your link — when they sign up, you earn a reward off your bill.</div>
  <div style="background:#0a0a0a;border:1px solid #1e1e1e;border-radius:8px;padding:10px 14px;margin-bottom:10px;display:flex;align-items:center;justify-content:space-between;gap:8px;flex-wrap:wrap">
    <span id="refLinkText" style="font-family:monospace;font-size:0.72em;color:#D4AF37;word-break:break-all"></span>
    <button onclick="copyRefLink()" style="background:none;border:1px solid #333;border-radius:6px;color:#888;font-size:0.72em;padding:5px 12px;cursor:pointer">Copy</button>
  </div>
  <div style="display:flex;gap:8px">
    <div style="flex:1;text-align:center;background:#0a0a0a;border:1px solid #1e1e1e;border-radius:8px;padding:10px">
      <div id="refClicks" style="font-size:1.3em;font-weight:800;color:#42a5f5">0</div>
      <div style="font-size:0.65em;color:#888;margin-top:2px">Clicks</div>
    </div>
    <div style="flex:1;text-align:center;background:#0a0a0a;border:1px solid #1e1e1e;border-radius:8px;padding:10px">
      <div id="refConversions" style="font-size:1.3em;font-weight:800;color:#00c853">0</div>
      <div style="font-size:0.65em;color:#888;margin-top:2px">Referrals</div>
    </div>
    <div style="flex:1;text-align:center;background:#0a0a0a;border:1px solid #1e1e1e;border-radius:8px;padding:10px">
      <div id="refEarnings" style="font-size:1.3em;font-weight:800;color:#D4AF37">$0</div>
      <div style="font-size:0.65em;color:#888;margin-top:2px">Earned</div>
    </div>
  </div>
</div>

<div class="powered">Powered by <a href="https://janovum.com">Janovum AI</a></div>

<script>
var CLIENT_ID = '{{CLIENT_ID}}';'''

old_portal_loadportal_end = """    document.getElementById('mainContent').innerHTML = html;
  } catch(e) {
    document.getElementById('mainContent').innerHTML = '<div class="empty">Could not load portal.<br>Please try again later.</div>';
  }
}

loadPortal();"""

new_portal_loadportal_end = """    document.getElementById('mainContent').innerHTML = html;

    // Load referral info
    loadReferral();
  } catch(e) {
    document.getElementById('mainContent').innerHTML = '<div class="empty">Could not load portal.<br>Please try again later.</div>';
  }
}

async function loadReferral() {
  try {
    const r = await fetch('/api/referral/stats/' + CLIENT_ID);
    const d = await r.json();
    if (d.code) {
      document.getElementById('referralSection').style.display = 'block';
      document.getElementById('refLinkText').textContent = 'janovum.com/refer/' + d.code;
      document.getElementById('refClicks').textContent = d.clicks || 0;
      document.getElementById('refConversions').textContent = d.conversions || 0;
      document.getElementById('refEarnings').textContent = '$' + (d.earnings || 0);
    }
  } catch(e) {}
}

function copyRefLink() {
  const txt = document.getElementById('refLinkText')?.textContent;
  if (txt) navigator.clipboard.writeText('https://' + txt).then(() => {
    const btn = event.target;
    btn.textContent = 'Copied!';
    setTimeout(() => btn.textContent = 'Copy', 2000);
  });
}

loadPortal();"""

# Apply patches
applied = []

if old_referrals in content:
    content = content.replace(old_referrals, new_referrals)
    applied.append('Referral UI in agency tab')
else:
    print('WARNING: agRenderReferrals stub not found')

if old_portal_powered in content:
    content = content.replace(old_portal_powered, new_portal_powered)
    applied.append('Referral section in client portal template')
else:
    print('WARNING: portal powered section not found')

if old_portal_loadportal_end in content:
    content = content.replace(old_portal_loadportal_end, new_portal_loadportal_end)
    applied.append('loadReferral() call in portal')
else:
    print('WARNING: portal loadPortal end not found')

open('/root/janovum-toolkit/Janovum_Platform_v3.html', 'w').write(content)
print('Done:', ', '.join(applied) if applied else 'Nothing applied')
print('Size:', len(content))
