"""
1. Convert all Settings tab panels to collapsible dropdowns (via injected JS)
2. Add Referral Program panel to Settings tab
3. Clean up the ADVANCED CONFIGURATION section - make it match the same dropdown style
"""
import re

SRC = r"C:\Users\jigga\OneDrive\Desktop\janovum company planing\Janovum_Platform_v3.html"

with open(SRC, encoding='utf-8', errors='ignore') as f:
    c = f.read()

print(f"Starting: {len(c):,} chars")

# ─────────────────────────────────────────────────────────
# STEP 1: Add Referral Program panel to Settings tab
# ─────────────────────────────────────────────────────────

referral_panel = '''
      <!-- ── REFERRAL PROGRAM ── -->
      <div class="panel" style="border-color:#f7c94844;background:linear-gradient(135deg,#120f00 0%,#0d0d0d 100%)">
        <div class="panel-header"><div class="panel-title" style="font-size:0.95em">&#127775; Referral Program — Earn 20% Monthly</div></div>
        <div style="font-size:0.78em;color:var(--muted);margin-bottom:18px">Refer businesses to Janovum and earn <strong style="color:var(--gold)">20% of their monthly subscription</strong> — every month they stay. No cap, no expiry.</div>

        <!-- Stats row -->
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-bottom:20px">
          <div style="background:#0a0a0a;border:1px solid var(--border);border-radius:10px;padding:14px;text-align:center">
            <div style="font-size:0.65em;color:var(--muted);text-transform:uppercase;letter-spacing:1px">Your Referrals</div>
            <div style="font-size:1.8em;font-weight:900;color:var(--gold);margin:4px 0" id="refCount">0</div>
            <div style="font-size:0.65em;color:var(--dim)">active clients</div>
          </div>
          <div style="background:#0a0a0a;border:1px solid var(--border);border-radius:10px;padding:14px;text-align:center">
            <div style="font-size:0.65em;color:var(--muted);text-transform:uppercase;letter-spacing:1px">Monthly Earnings</div>
            <div style="font-size:1.8em;font-weight:900;color:var(--green);margin:4px 0" id="refEarnings">$0</div>
            <div style="font-size:0.65em;color:var(--dim)">recurring / mo</div>
          </div>
          <div style="background:#0a0a0a;border:1px solid var(--border);border-radius:10px;padding:14px;text-align:center">
            <div style="font-size:0.65em;color:var(--muted);text-transform:uppercase;letter-spacing:1px">Total Earned</div>
            <div style="font-size:1.8em;font-weight:900;color:var(--blue);margin:4px 0" id="refTotal">$0</div>
            <div style="font-size:0.65em;color:var(--dim)">all time</div>
          </div>
          <div style="background:#0a0a0a;border:1px solid var(--border);border-radius:10px;padding:14px;text-align:center">
            <div style="font-size:0.65em;color:var(--muted);text-transform:uppercase;letter-spacing:1px">Commission Rate</div>
            <div style="font-size:1.8em;font-weight:900;color:var(--gold);margin:4px 0">20%</div>
            <div style="font-size:0.65em;color:var(--dim)">of monthly plan</div>
          </div>
        </div>

        <!-- Referral link -->
        <div style="background:#0d0d0d;border:1px solid var(--gold)33;border-radius:10px;padding:16px;margin-bottom:16px">
          <div style="font-size:0.78em;font-weight:700;color:var(--gold);margin-bottom:8px">Your Referral Link</div>
          <div style="display:flex;gap:8px;align-items:center">
            <input class="form-input" id="refLink" value="https://janovum.com/?ref=YOUR_CODE" readonly style="font-family:monospace;font-size:0.82em;color:var(--dim);flex:1">
            <button class="btn-sm btn" onclick="copyRefLink()" style="white-space:nowrap">Copy Link</button>
          </div>
          <div style="font-size:0.7em;color:var(--dim);margin-top:6px">Share this link. When a business signs up and pays their first month, you earn 20% every month they stay active.</div>
        </div>

        <!-- Payout settings -->
        <div style="border-top:1px solid var(--border);padding-top:14px;margin-top:4px">
          <div style="font-size:0.78em;font-weight:700;color:var(--gold);margin-bottom:10px">Payout Method</div>
          <div class="form-row">
            <div class="form-group">
              <label class="form-label">Payout Method</label>
              <select class="form-select" id="refPayoutMethod" style="font-size:0.85em">
                <option>PayPal</option>
                <option>Stripe</option>
                <option>Crypto (USDC)</option>
                <option>Bank Transfer (ACH)</option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">Payout Email / Address</label>
              <input class="form-input" id="refPayoutAddress" placeholder="paypal@youremail.com" style="font-size:0.85em">
            </div>
          </div>
          <div style="font-size:0.72em;color:var(--dim);margin-bottom:10px">Payouts are processed on the 1st of each month for balances over $25.</div>
          <button class="btn" onclick="saveRefPayout()">Save Payout Info</button>
          <span id="refPayoutSaved" style="font-size:0.8em;color:var(--green);margin-left:10px"></span>
        </div>

        <!-- Referred clients list -->
        <div style="border-top:1px solid var(--border);padding-top:14px;margin-top:14px">
          <div style="font-size:0.78em;font-weight:700;color:var(--gold);margin-bottom:10px">Referred Clients</div>
          <div id="refClientList" style="font-size:0.8em;color:var(--dim)">No referrals yet. Share your link to start earning!</div>
        </div>
      </div>
'''

# Insert referral panel before the ADVANCED CONFIGURATION accordion (which we added last session)
insert_before = c.find('<!-- ════ CONDENSED SETTINGS ACCORDION ════ -->')
if insert_before == -1:
    # Try inserting before closing of settings pane
    insert_before = c.find('<!-- ── ABOUT ──')
    if insert_before == -1:
        # Insert just before the settings pane closes
        settings_pane_start = c.find('<div class="tab-pane" id="tab-settings">')
        # Find a good insertion point - before last div closing
        print("Could not find insertion point for referral panel")
    else:
        c = c[:insert_before] + referral_panel + c[insert_before:]
        print("Inserted referral panel before ABOUT section")
else:
    c = c[:insert_before] + referral_panel + c[insert_before:]
    print("Inserted referral panel before Advanced Configuration accordion")

# ─────────────────────────────────────────────────────────
# STEP 2: Inject JS to convert all Settings panels to collapsible
# and add referral helper functions
# ─────────────────────────────────────────────────────────

settings_accordion_js = '''
<script>
// ── SETTINGS TAB: Convert all panels to collapsible dropdowns ──
function initSettingsAccordions() {
  var settingsTab = document.getElementById('tab-settings');
  if (!settingsTab) return;

  var panels = settingsTab.querySelectorAll(':scope > .panel');
  panels.forEach(function(panel, i) {
    var header = panel.querySelector('.panel-header');
    if (!header || header.dataset.stgInit) return;
    header.dataset.stgInit = '1';

    var bodyId = 'stg_body_' + i;

    // Collect all children after the panel-header
    var allChildren = Array.from(panel.children);
    var headerIdx = allChildren.indexOf(header);
    var toWrap = allChildren.slice(headerIdx + 1);

    // Create collapsible body wrapper
    var bodyDiv = document.createElement('div');
    bodyDiv.id = bodyId;
    bodyDiv.className = 'stg-body';
    bodyDiv.style.display = 'none';
    bodyDiv.style.paddingTop = '4px';
    toWrap.forEach(function(child) {
      bodyDiv.appendChild(child);
    });
    panel.appendChild(bodyDiv);

    // Add chevron to header
    var chevron = document.createElement('span');
    chevron.id = bodyId + '_chev';
    chevron.style.cssText = 'color:var(--dim);font-size:0.8em;transition:transform 0.25s;margin-left:auto;padding-left:12px;flex-shrink:0';
    chevron.textContent = '▼';
    header.style.cursor = 'pointer';
    header.style.userSelect = 'none';
    if (header.style.display !== 'flex') {
      header.style.display = 'flex';
      header.style.justifyContent = 'space-between';
      header.style.alignItems = 'center';
    }
    header.appendChild(chevron);

    header.addEventListener('click', function() {
      var body = document.getElementById(bodyId);
      var chev = document.getElementById(bodyId + '_chev');
      var isOpen = body.style.display !== 'none';
      body.style.display = isOpen ? 'none' : 'block';
      if (chev) chev.style.transform = isOpen ? '' : 'rotate(180deg)';
    });
  });

  // Open the first panel (Wallet) by default
  var firstBody = document.getElementById('stg_body_0');
  var firstChev = document.getElementById('stg_body_0_chev');
  if (firstBody) firstBody.style.display = 'block';
  if (firstChev) firstChev.style.transform = 'rotate(180deg)';
}

// ── REFERRAL PROGRAM helpers ──
function copyRefLink() {
  var inp = document.getElementById('refLink');
  if (!inp) return;
  inp.select();
  document.execCommand('copy');
  var btn = inp.nextElementSibling;
  if (btn) { btn.textContent = 'Copied!'; setTimeout(function(){ btn.textContent = 'Copy Link'; }, 2000); }
}
function saveRefPayout() {
  var method = document.getElementById('refPayoutMethod')?.value;
  var addr = document.getElementById('refPayoutAddress')?.value;
  if (!addr) return;
  localStorage.setItem('jnv_ref_payout', JSON.stringify({method, addr}));
  var saved = document.getElementById('refPayoutSaved');
  if (saved) { saved.textContent = 'Saved!'; setTimeout(function(){ saved.textContent=''; }, 2000); }
}
function loadRefData() {
  var d = JSON.parse(localStorage.getItem('jnv_ref_data') || '{}');
  if (d.code) {
    var inp = document.getElementById('refLink');
    if (inp) inp.value = 'https://janovum.com/?ref=' + d.code;
  }
  if (document.getElementById('refCount')) document.getElementById('refCount').textContent = d.count || 0;
  if (document.getElementById('refEarnings')) document.getElementById('refEarnings').textContent = '$' + (d.monthly || 0);
  if (document.getElementById('refTotal')) document.getElementById('refTotal').textContent = '$' + (d.total || 0);
  var p = JSON.parse(localStorage.getItem('jnv_ref_payout') || '{}');
  if (p.method && document.getElementById('refPayoutMethod')) document.getElementById('refPayoutMethod').value = p.method;
  if (p.addr && document.getElementById('refPayoutAddress')) document.getElementById('refPayoutAddress').value = p.addr;
}

window.addEventListener('load', function() {
  initSettingsAccordions();
  loadRefData();
});
</script>
'''

# Insert before last </body>
last_body = c.rfind('</body>')
if last_body != -1:
    c = c[:last_body] + settings_accordion_js + c[last_body:]
    print("Injected settings accordion + referral JS")

# ─────────────────────────────────────────────────────────
# STEP 3: Verify
# ─────────────────────────────────────────────────────────
print(f"\nFinal size: {len(c):,} chars")
print(f"Referral Program panel: {c.count('Referral Program — Earn 20%')}")
print(f"initSettingsAccordions: {c.count('initSettingsAccordions')}")
print(f"stg_body: {c.count('stg_body_')}")
print(f"copyRefLink: {c.count('copyRefLink')}")
print(f"switchTab: {c.count('function switchTab')}")

with open(SRC, 'w', encoding='utf-8') as f:
    f.write(c)
print("\nSaved.")
