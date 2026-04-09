content = open('/root/janovum-toolkit/Janovum_Platform_v3.html').read()

REFERRAL_FN = r"""
async function agRenderReferrals(el) {
  el.innerHTML = '<div style="color:var(--muted);font-size:0.85em;padding:10px 0">Loading referrals...</div>';
  let refs = [], clients = [];
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

  const totalClicks = refs.reduce((s,r) => s + r.clicks, 0);
  const totalConversions = refs.reduce((s,r) => s + r.conversions, 0);
  const totalEarnings = refs.reduce((s,r) => s + r.earnings, 0);

  let html = '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:20px">';
  html += '<div class="stat-card"><div class="stat-label">Total Clicks</div><div class="stat-value blue">' + totalClicks + '</div></div>';
  html += '<div class="stat-card"><div class="stat-label">Conversions</div><div class="stat-value green">' + totalConversions + '</div></div>';
  html += '<div class="stat-card"><div class="stat-label">Rewards Earned</div><div class="stat-value gold">$' + totalEarnings + '</div></div>';
  html += '</div>';

  html += '<div style="background:#0d0d0d;border:1px solid var(--border);border-radius:12px;padding:16px;margin-bottom:20px">';
  html += '<div style="font-size:0.8em;font-weight:700;color:var(--gold);margin-bottom:10px">&#9881; Global Reward Setting</div>';
  html += '<div style="font-size:0.78em;color:var(--muted);margin-bottom:12px">How much a client earns when someone they refer signs up and pays.</div>';
  html += '<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">';
  html += '<span style="font-size:0.82em;color:var(--muted)">$</span><input class="form-input" id="ag-global-reward" type="number" value="100" min="0" style="width:90px;font-size:0.85em">';
  html += '<span style="font-size:0.78em;color:var(--muted)">per referral</span>';
  html += '<button class="btn-sm btn-green" onclick="agSetGlobalReward()">Apply to All</button>';
  html += '</div></div>';

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
        html += '<span>&#128199; ' + ref.clicks + '</span>';
        html += '<span style="color:var(--green)">&#10003; ' + ref.conversions + '</span>';
        html += '<span style="color:var(--gold)">$' + ref.earnings + '</span>';
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
        html += '<button class="btn-sm btn-outline" onclick="agUpdateReward(\'' + esc(c.client_id) + '\')">Update</button>';
        html += '<button class="btn-sm btn-green" onclick="agMarkConverted(\'' + esc(ref.code) + '\')">+ Mark Converted</button>';
        html += '</div>';
      } else {
        html += '<button class="btn btn-outline" style="width:100%;font-size:0.82em" onclick="agGenerateReferral(\'' + esc(c.client_id) + '\')">&#128279; Generate Referral Link</button>';
      }
      html += '</div>';
    });
  }

  html += '<div style="background:#0d0d0d;border:1px solid var(--border);border-radius:12px;padding:16px;margin-top:8px">';
  html += '<div style="font-size:0.8em;font-weight:700;color:var(--gold);margin-bottom:10px">&#128161; How It Works</div>';
  html += '<div style="display:flex;flex-direction:column;gap:8px;font-size:0.78em;color:var(--muted)">';
  ['1. Generate a unique link for each client',
   '2. Client shares it with businesses they know',
   '3. Someone signs up through the link — mark it as converted',
   '4. Client earns their reward off their next bill',
   '5. You get a new paying client with zero outreach cost'].forEach(s => {
     html += '<div>' + s + '</div>';
   });
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
    if (d.code) { toast('Referral link created!', 'success'); agRenderReferrals(document.getElementById('ag-content')); }
    else toast('Failed', 'error');
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
    else toast('Failed', 'error');
  } catch(e) { toast('Error', 'error'); }
}

async function agMarkConverted(code) {
  if (!confirm('Mark this as a paid conversion? This credits the reward to the client.')) return;
  try {
    const r = await fetch(API + '/api/referral/convert', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ code })
    });
    const d = await r.json();
    if (d.status === 'ok') { toast('Conversion recorded! $' + d.earnings + ' total earned', 'success'); agRenderReferrals(document.getElementById('ag-content')); }
    else toast('Error: ' + (d.error||'failed'), 'error');
  } catch(e) { toast('Error', 'error'); }
}

async function agSetGlobalReward() {
  const reward = parseInt(document.getElementById('ag-global-reward')?.value || 100);
  try {
    const cRes = await fetch(API + '/api/receptionist/clients');
    const cd = await cRes.json();
    for (const c of (cd.clients||[])) {
      await fetch(API + '/api/referral/set-reward', {
        method: 'POST', headers: {'Content-Type':'application/json'},
        body: JSON.stringify({ client_id: c.client_id, reward })
      });
    }
    toast('Reward updated for all clients', 'success');
    agRenderReferrals(document.getElementById('ag-content'));
  } catch(e) { toast('Error', 'error'); }
}

"""

# Insert before agEditPortal
marker = 'function agEditPortal(clientId) {'
if marker in content:
    content = content.replace(marker, REFERRAL_FN + marker)
    print('Referral function injected')
else:
    print('ERROR: marker not found')

# Now patch the client portal template
portal = open('/root/janovum-toolkit/platform/templates/client_portal.html').read()

old_powered = '<div class="powered">Powered by <a href="https://janovum.com">Janovum AI</a></div>'
new_powered = '''<div id="referralSection" style="display:none;margin:0 20px 16px;background:#111;border:1px solid #D4AF3733;border-radius:14px;padding:16px">
  <div style="font-size:0.8em;font-weight:700;color:{{COLOR}};margin-bottom:8px">&#127873; Refer a Friend &mdash; Earn Rewards</div>
  <div style="font-size:0.75em;color:#888;margin-bottom:12px;line-height:1.5">Know another business that could use an AI receptionist? Share your link and earn rewards when they sign up.</div>
  <div style="background:#0a0a0a;border:1px solid #1e1e1e;border-radius:8px;padding:10px 14px;margin-bottom:10px;display:flex;align-items:center;justify-content:space-between;gap:8px;flex-wrap:wrap">
    <span id="refLinkText" style="font-family:monospace;font-size:0.72em;color:{{COLOR}};word-break:break-all"></span>
    <button onclick="copyRefLink(this)" style="background:none;border:1px solid #333;border-radius:6px;color:#888;font-size:0.72em;padding:5px 12px;cursor:pointer">Copy</button>
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
      <div id="refEarnings" style="font-size:1.3em;font-weight:800;color:{{COLOR}}">$0</div>
      <div style="font-size:0.65em;color:#888;margin-top:2px">Earned</div>
    </div>
  </div>
</div>
<div class="powered">Powered by <a href="https://janovum.com">Janovum AI</a></div>'''

if old_powered in portal:
    portal = portal.replace(old_powered, new_powered)
    print('Portal: referral section added')
else:
    print('WARNING: portal powered line not found')

# Add loadReferral call inside loadPortal
old_end = "    document.getElementById('mainContent').innerHTML = html;\n  } catch(e) {\n    document.getElementById('mainContent').innerHTML = '<div class=\"empty\">Could not load portal.<br>Please try again later.</div>';\n  }\n}\n\nloadPortal();"
new_end = """    document.getElementById('mainContent').innerHTML = html;
    loadReferral();
  } catch(e) {
    document.getElementById('mainContent').innerHTML = '<div class="empty">Could not load portal.<br>Please try again later.</div>';
  }
}

async function loadReferral() {
  try {
    var r = await fetch('/api/referral/stats/' + CLIENT_ID);
    var d = await r.json();
    if (d.code) {
      document.getElementById('referralSection').style.display = 'block';
      document.getElementById('refLinkText').textContent = 'janovum.com/refer/' + d.code;
      document.getElementById('refClicks').textContent = d.clicks || 0;
      document.getElementById('refConversions').textContent = d.conversions || 0;
      document.getElementById('refEarnings').textContent = '$' + (d.earnings || 0);
    }
  } catch(e) {}
}

function copyRefLink(btn) {
  var txt = document.getElementById('refLinkText').textContent;
  if (txt) navigator.clipboard.writeText('https://' + txt).then(function() {
    btn.textContent = 'Copied!';
    setTimeout(function() { btn.textContent = 'Copy'; }, 2000);
  });
}

loadPortal();"""

if old_end in portal:
    portal = portal.replace(old_end, new_end)
    print('Portal: loadReferral added')
else:
    print('WARNING: portal loadPortal end not found')
    # Try to find it
    idx = portal.find("document.getElementById('mainContent').innerHTML = html;")
    print('mainContent assignment at:', idx)

open('/root/janovum-toolkit/platform/templates/client_portal.html', 'w').write(portal)
open('/root/janovum-toolkit/Janovum_Platform_v3.html', 'w').write(content)
print('All done, HTML size:', len(content), 'Portal size:', len(portal))
