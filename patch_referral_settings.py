content = open('/root/janovum-toolkit/Janovum_Platform_v3.html').read()

# ── 1. Add referral panel to top of Settings tab ─────────────────────────────
old_settings_start = '''    <div class="tab-pane" id="tab-settings">

      <!-- ── TOOLKIT WALLET — Central Payment Method ── -->'''

new_settings_start = '''    <div class="tab-pane" id="tab-settings">

      <!-- ── REFERRAL PROGRAM ── -->
      <div class="panel" style="border-color:#D4AF3744;background:linear-gradient(135deg,#1a1200 0%,#0d0d0d 100%);margin-bottom:16px">
        <div class="panel-header">
          <div class="panel-title" style="font-size:0.95em">&#127873; Referral Program — Earn 20% Monthly</div>
        </div>
        <div style="font-size:0.78em;color:var(--muted);margin-bottom:16px;line-height:1.6">
          Share your referral link. Every time someone you refer pays their monthly bill, <strong style="color:var(--gold)">you earn 20% of what they spend</strong> — automatically, every month, for as long as they stay a client.
        </div>
        <div id="stRefLoading" style="color:var(--muted);font-size:0.82em">Loading your referral link...</div>
        <div id="stRefContent" style="display:none">
          <!-- Link box -->
          <div style="background:#0a0a0a;border:1px solid var(--border);border-radius:10px;padding:14px 16px;margin-bottom:14px">
            <div style="font-size:0.68em;text-transform:uppercase;letter-spacing:1px;color:var(--muted);margin-bottom:8px">Your Referral Link</div>
            <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
              <span id="stRefLink" style="font-family:monospace;font-size:0.82em;color:var(--gold);flex:1;word-break:break-all"></span>
              <button class="btn-sm btn-outline" onclick="stCopyRef()">Copy</button>
              <button class="btn-sm btn-outline" onclick="stShareRef()">Share</button>
            </div>
          </div>
          <!-- Stats row -->
          <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:14px">
            <div style="background:#0a0a0a;border:1px solid var(--border);border-radius:10px;padding:14px;text-align:center">
              <div id="stRefClicks" style="font-size:1.4em;font-weight:800;color:var(--blue)">0</div>
              <div style="font-size:0.65em;color:var(--muted);margin-top:3px;text-transform:uppercase;letter-spacing:.5px">Link Clicks</div>
            </div>
            <div style="background:#0a0a0a;border:1px solid var(--border);border-radius:10px;padding:14px;text-align:center">
              <div id="stRefConversions" style="font-size:1.4em;font-weight:800;color:var(--green)">0</div>
              <div style="font-size:0.65em;color:var(--muted);margin-top:3px;text-transform:uppercase;letter-spacing:.5px">Clients Referred</div>
            </div>
            <div style="background:#0a0a0a;border:1px solid var(--border);border-radius:10px;padding:14px;text-align:center">
              <div id="stRefEarnings" style="font-size:1.4em;font-weight:800;color:var(--gold)">$0</div>
              <div style="font-size:0.65em;color:var(--muted);margin-top:3px;text-transform:uppercase;letter-spacing:.5px">Total Earned</div>
            </div>
          </div>
          <!-- How it works -->
          <div style="background:#0a0a0a;border:1px solid var(--border);border-radius:10px;padding:14px 16px">
            <div style="font-size:0.72em;font-weight:700;color:var(--gold);margin-bottom:10px;text-transform:uppercase;letter-spacing:1px">How It Works</div>
            <div style="display:flex;flex-direction:column;gap:8px;font-size:0.78em;color:var(--muted)">
              <div style="display:flex;gap:10px"><span style="color:var(--gold);font-weight:700;min-width:20px">1.</span><span>Share your link with other business owners</span></div>
              <div style="display:flex;gap:10px"><span style="color:var(--gold);font-weight:700;min-width:20px">2.</span><span>They sign up and start using Janovum</span></div>
              <div style="display:flex;gap:10px"><span style="color:var(--gold);font-weight:700;min-width:20px">3.</span><span>You earn <strong style="color:var(--gold)">20% of their monthly spend</strong> every month they stay</span></div>
              <div style="display:flex;gap:10px"><span style="color:var(--gold);font-weight:700;min-width:20px">4.</span><span>Earnings are credited to your account — cash or bill discount</span></div>
            </div>
          </div>
        </div>
        <div id="stRefNoCode" style="display:none">
          <button class="btn" onclick="stGenerateRef()" style="width:100%">Generate My Referral Link</button>
        </div>
      </div>

      <!-- ── TOOLKIT WALLET — Central Payment Method ── -->'''

# ── 2. Add loadSettings referral loader at end of loadSettings call ──────────
old_load_settings = '''async function loadSettings() {
  stLoadSettings();
  loadAuthStatus();
  loadToolkitConfig();'''

new_load_settings = '''async function loadSettings() {
  stLoadSettings();
  loadAuthStatus();
  loadToolkitConfig();
  stLoadReferral();'''

# ── 3. Add referral helper functions near end of file, before loadAgencyTab ──
old_load_agency = 'function loadAgencyTab() {'

new_load_agency = '''async function stLoadReferral() {
  try {
    // Use the admin user (jaden) as the referral client
    const clientId = (typeof tkUser !== 'undefined' && tkUser) ? tkUser : 'jaden';
    let d = await api('/api/referral/stats/' + clientId);
    if (!d || !d.code) {
      // Auto-generate
      const g = await api('/api/referral/generate', {
        method: 'POST',
        body: JSON.stringify({ client_id: clientId, reward_pct: 20 })
      });
      if (g && g.code) d = await api('/api/referral/stats/' + clientId);
    }
    document.getElementById('stRefLoading').style.display = 'none';
    if (d && d.code) {
      document.getElementById('stRefContent').style.display = 'block';
      document.getElementById('stRefLink').textContent = 'janovum.com/refer/' + d.code;
      document.getElementById('stRefClicks').textContent = d.clicks || 0;
      document.getElementById('stRefConversions').textContent = d.conversions || 0;
      document.getElementById('stRefEarnings').textContent = '$' + (d.earnings || 0);
      window._stRefUrl = 'https://janovum.com/refer/' + d.code;
    } else {
      document.getElementById('stRefNoCode').style.display = 'block';
    }
  } catch(e) {
    document.getElementById('stRefLoading').textContent = 'Could not load referral info.';
  }
}

function stCopyRef() {
  const url = window._stRefUrl || document.getElementById('stRefLink')?.textContent;
  if (url) {
    navigator.clipboard.writeText(url.startsWith('http') ? url : 'https://' + url)
      .then(() => toast('Referral link copied!', 'success'));
  }
}

function stShareRef() {
  const url = window._stRefUrl || 'https://' + document.getElementById('stRefLink')?.textContent;
  const text = 'Check out Janovum — AI receptionist, automation tools, and more. Sign up through my link:';
  if (navigator.share) {
    navigator.share({ title: 'Janovum AI', text, url }).catch(() => {});
  } else {
    navigator.clipboard.writeText(url).then(() => toast('Link copied — share it anywhere!', 'success'));
  }
}

async function stGenerateRef() {
  const clientId = (typeof tkUser !== 'undefined' && tkUser) ? tkUser : 'jaden';
  const g = await api('/api/referral/generate', {
    method: 'POST', body: JSON.stringify({ client_id: clientId, reward_pct: 20 })
  });
  if (g && g.code) { stLoadReferral(); document.getElementById('stRefNoCode').style.display = 'none'; }
  else toast('Could not generate link', 'error');
}

function loadAgencyTab() {'''

applied = []

if old_settings_start in content:
    content = content.replace(old_settings_start, new_settings_start)
    applied.append('Referral panel added to Settings tab')
else:
    print('WARNING: settings start not found')

if old_load_settings in content:
    content = content.replace(old_load_settings, new_load_settings)
    applied.append('stLoadReferral() called in loadSettings')
else:
    print('WARNING: loadSettings start not found')

if old_load_agency in content:
    content = content.replace(old_load_agency, new_load_agency, 1)
    applied.append('stLoadReferral + helpers injected')
else:
    print('WARNING: loadAgencyTab not found')

open('/root/janovum-toolkit/Janovum_Platform_v3.html', 'w').write(content)
print('Done:', ', '.join(applied))
print('Size:', len(content))
