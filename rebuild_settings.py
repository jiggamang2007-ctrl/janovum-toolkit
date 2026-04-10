"""
1. Rebuild Settings tab as organized accordion sections
2. Clean sidebar - remove 17 bloat/duplicate tabs
3. Remove Crypto Trading
"""

content = open('/root/janovum-toolkit/Janovum_Platform_v3.html').read()

# ─────────────────────────────────────────────────────────────────────────────
# 1. ADD ACCORDION CSS (inject after existing .panel-title style)
# ─────────────────────────────────────────────────────────────────────────────
ACCORDION_CSS = """
  /* Settings Accordion */
  .st-section { background:var(--card);border:1px solid var(--border);border-radius:14px;margin-bottom:12px;overflow:hidden; }
  .st-section-hdr { display:flex;align-items:center;justify-content:space-between;padding:16px 20px;cursor:pointer;user-select:none;transition:background 0.15s; }
  .st-section-hdr:hover { background:rgba(255,255,255,0.02); }
  .st-section-hdr .st-hdr-left { display:flex;align-items:center;gap:12px; }
  .st-section-hdr .st-icon { font-size:1.15em;width:26px;text-align:center; }
  .st-section-hdr .st-title { font-size:0.88em;font-weight:700;color:var(--text); }
  .st-section-hdr .st-sub { font-size:0.72em;color:var(--muted);margin-top:2px; }
  .st-section-hdr .st-chevron { font-size:0.7em;color:var(--muted);transition:transform 0.2s; }
  .st-section-hdr.open .st-chevron { transform:rotate(180deg); }
  .st-section-hdr.open .st-title { color:var(--gold); }
  .st-section-body { display:none;padding:0 20px 20px;border-top:1px solid var(--border); }
  .st-section-body.open { display:block; }
  .st-row { display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px; }
  .st-row.single { grid-template-columns:1fr; }
  .st-field label { display:block;font-size:0.68em;text-transform:uppercase;letter-spacing:1px;color:var(--muted);margin-bottom:6px; }
  .st-divider { border:none;border-top:1px solid var(--border);margin:16px 0; }
  .st-toggle-row { display:flex;justify-content:space-between;align-items:flex-start;padding:14px 0;border-bottom:1px solid #111; }
  .st-toggle-row:last-child { border-bottom:none;padding-bottom:0; }
  .st-toggle-label { font-size:0.85em;font-weight:600;margin-bottom:3px; }
  .st-toggle-sub { font-size:0.72em;color:var(--muted);line-height:1.5; }
  .st-toggle { display:flex;align-items:center;gap:8px;cursor:pointer;flex-shrink:0;margin-left:12px; }
  .st-toggle input[type=checkbox] { width:18px;height:18px;accent-color:var(--gold);cursor:pointer; }
"""

old_panel_title_style = '  .panel-title { font-size: 0.82em; color: var(--gold); text-transform: uppercase; letter-spacing: 1.2px; font-weight: 700; }'
if old_panel_title_style in content:
    content = content.replace(old_panel_title_style, old_panel_title_style + '\n' + ACCORDION_CSS)
    print('Accordion CSS added')
else:
    print('WARNING: panel-title style not found')

# ─────────────────────────────────────────────────────────────────────────────
# 2. ADD ACCORDION JS FUNCTION (inject near toggleSection or before loadSettings)
# ─────────────────────────────────────────────────────────────────────────────
ACCORDION_JS = """
function toggleSection(id, forceOpen) {
  const hdr = document.getElementById('sthdr-' + id);
  const body = document.getElementById('stbody-' + id);
  if (!hdr || !body) return;
  const isOpen = body.classList.contains('open');
  if (forceOpen === true || (!isOpen && forceOpen !== false)) {
    hdr.classList.add('open');
    body.classList.add('open');
  } else {
    hdr.classList.remove('open');
    body.classList.remove('open');
  }
}

"""

old_load_settings_fn = 'async function loadSettings() {'
if old_load_settings_fn in content:
    content = content.replace(old_load_settings_fn, ACCORDION_JS + old_load_settings_fn)
    print('Accordion JS added')
else:
    print('WARNING: loadSettings fn not found')

# ─────────────────────────────────────────────────────────────────────────────
# 3. REPLACE ENTIRE SETTINGS TAB CONTENT
# ─────────────────────────────────────────────────────────────────────────────
old_settings_start = '    <div class="tab-pane" id="tab-settings">'
old_settings_end = '    <!-- ═══ AI EMPLOYEES TAB ═══ -->'

if old_settings_start in content and old_settings_end in content:
    start_idx = content.index(old_settings_start)
    end_idx = content.index(old_settings_end)
    old_settings_block = content[start_idx:end_idx]

    NEW_SETTINGS = '''    <div class="tab-pane" id="tab-settings">
      <div style="margin-bottom:20px">
        <h2 style="font-size:1.3em;font-weight:800;margin-bottom:4px">Settings</h2>
        <p style="font-size:0.82em;color:var(--muted)">Everything in one place, organized so you can find it fast.</p>
      </div>

      <!-- ══ 1. BUSINESS PROFILE ══ -->
      <div class="st-section">
        <div class="st-section-hdr open" id="sthdr-biz" onclick="toggleSection('biz')">
          <div class="st-hdr-left">
            <span class="st-icon">&#127970;</span>
            <div><div class="st-title">Business Profile</div><div class="st-sub">Your business name, hours, and contact info</div></div>
          </div>
          <span class="st-chevron">&#9660;</span>
        </div>
        <div class="st-section-body open" id="stbody-biz">
          <div style="margin-top:16px">
            <div class="st-row">
              <div class="st-field"><label>Business Name</label><input class="form-input" id="biz-name" placeholder="e.g. Mike's Auto Shop"></div>
              <div class="st-field"><label>Industry / Type</label><input class="form-input" id="biz-type" placeholder="e.g. Auto Repair"></div>
            </div>
            <div class="st-row">
              <div class="st-field"><label>Business Phone</label><input class="form-input" id="biz-phone" placeholder="+1 (555) 000-0000"></div>
              <div class="st-field"><label>Business Email</label><input class="form-input" id="biz-email" type="email" placeholder="hello@yourbiz.com"></div>
            </div>
            <div class="st-row single">
              <div class="st-field"><label>Business Address</label><input class="form-input" id="biz-address" placeholder="123 Main St, City, State"></div>
            </div>
            <div class="st-row single">
              <div class="st-field"><label>Business Hours</label><input class="form-input" id="biz-hours" placeholder="Mon-Fri 9am-6pm, Sat 10am-4pm, Closed Sunday"></div>
            </div>
            <div class="st-row single">
              <div class="st-field"><label>Short Description (what you do)</label><textarea class="form-input" id="biz-desc" rows="2" placeholder="We specialize in..."></textarea></div>
            </div>
            <button class="btn" onclick="saveBizProfile()">Save Profile</button>
            <div id="bizSaveStatus" style="margin-top:8px;font-size:0.78em"></div>
          </div>
        </div>
      </div>

      <!-- ══ 2. AI & RECEPTIONIST ══ -->
      <div class="st-section">
        <div class="st-section-hdr open" id="sthdr-ai" onclick="toggleSection('ai')">
          <div class="st-hdr-left">
            <span class="st-icon">&#129302;</span>
            <div><div class="st-title">AI & Receptionist</div><div class="st-sub">API keys, model, voice, personality</div></div>
          </div>
          <span class="st-chevron">&#9660;</span>
        </div>
        <div class="st-section-body open" id="stbody-ai">
          <div style="margin-top:16px">
            <div style="font-size:0.72em;text-transform:uppercase;letter-spacing:1px;color:var(--gold);font-weight:700;margin-bottom:12px">Anthropic API Key</div>
            <div class="st-row">
              <div class="st-field"><label>API Key (sk-ant-...)</label><input class="form-input" id="set-apikey" type="password" placeholder="sk-ant-..."></div>
              <div class="st-field"><label>Model</label>
                <select class="form-select" id="set-model">
                  <option value="haiku">Claude Haiku (fastest, cheapest)</option>
                  <option value="sonnet" selected>Claude Sonnet (recommended)</option>
                  <option value="opus">Claude Opus (most capable)</option>
                </select>
              </div>
            </div>
            <div class="st-row">
              <div class="st-field"><label>Monthly Spend Limit ($)</label><input class="form-input" id="set-limit" type="number" value="50" placeholder="50.00"></div>
            </div>
            <button class="btn" onclick="saveConfig()">Save API Config</button>

            <hr class="st-divider">

            <div style="font-size:0.72em;text-transform:uppercase;letter-spacing:1px;color:var(--gold);font-weight:700;margin-bottom:12px">Sign In with Claude (OAuth)</div>
            <p style="font-size:0.82em;color:var(--muted);margin-bottom:14px">Users with a Claude Pro/Max/Team subscription can connect their account — no separate API key needed.</p>
            <div id="oauthStatusBox" style="margin-bottom:14px"><div class="loading"><div class="spinner"></div> Checking auth...</div></div>
            <div style="display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:14px">
              <div class="st-field" style="flex:1;min-width:160px;margin:0"><label>Client ID</label><input class="form-input" id="oauth-client-id" placeholder="default" value="default"></div>
              <button class="btn" onclick="oauthLogin()" id="oauthLoginBtn" style="margin-top:20px">&#9889; Connect Claude Account</button>
              <button class="btn-red btn-sm" onclick="oauthDisconnect()" id="oauthDisconnectBtn" style="margin-top:20px;display:none">Disconnect</button>
            </div>

            <hr class="st-divider">

            <div style="font-size:0.72em;text-transform:uppercase;letter-spacing:1px;color:var(--gold);font-weight:700;margin-bottom:12px">Personality & Voice</div>
            <div class="st-row">
              <div class="st-field"><label>Receptionist Name</label><input class="form-input" id="soul-name" placeholder="e.g. Alex"></div>
              <div class="st-field"><label>Tone / Style</label>
                <select class="form-input" id="soul-tone" style="appearance:auto">
                  <option value="professional">Professional & Friendly</option>
                  <option value="warm">Warm & Casual</option>
                  <option value="formal">Formal & Precise</option>
                  <option value="energetic">Energetic & Upbeat</option>
                </select>
              </div>
            </div>
            <div class="st-row single">
              <div class="st-field"><label>Custom Instructions (how the AI should behave)</label>
                <textarea class="form-input" id="soul-instructions" rows="3" placeholder="Always greet callers by name. Never discuss competitors. Always try to book an appointment before ending the call..."></textarea>
              </div>
            </div>
            <button class="btn-outline" onclick="saveSoulConfig()">Save Personality</button>

            <hr class="st-divider">

            <div style="font-size:0.72em;text-transform:uppercase;letter-spacing:1px;color:var(--gold);font-weight:700;margin-bottom:12px">System Status</div>
            <div style="display:flex;gap:10px;align-items:center;margin-bottom:12px">
              <button class="btn-green btn-sm" onclick="heartbeatAction('start')">&#9654; Start Heartbeat</button>
              <button class="btn-red btn-sm" onclick="heartbeatAction('stop')">&#9632; Stop</button>
              <span style="font-size:0.78em;color:var(--muted)" id="hbStatus">--</span>
            </div>
            <div id="failoverStatus" style="margin-bottom:10px"></div>
            <div id="costOverview"></div>
          </div>
        </div>
      </div>

      <!-- ══ 3. AUTOMATION ══ -->
      <div class="st-section">
        <div class="st-section-hdr" id="sthdr-auto" onclick="toggleSection('auto')">
          <div class="st-hdr-left">
            <span class="st-icon">&#9889;</span>
            <div><div class="st-title">Automation</div><div class="st-sub">Missed call texts, follow-ups, reminders, reviews, deposits</div></div>
          </div>
          <span class="st-chevron">&#9660;</span>
        </div>
        <div class="st-section-body" id="stbody-auto">
          <div style="margin-top:16px">

            <!-- Missed Call Text-Back -->
            <div style="background:#0a0a0a;border:1px solid var(--border);border-radius:10px;padding:16px;margin-bottom:12px">
              <div class="st-toggle-row" style="border:none;padding-bottom:12px;padding-top:0">
                <div><div class="st-toggle-label">&#128241; Missed Call Text-Back</div><div class="st-toggle-sub">Auto-text anyone who hangs up before the AI answers</div></div>
                <label class="st-toggle"><input type="checkbox" id="mc-enabled"><span style="font-size:0.75em;color:var(--muted)">On</span></label>
              </div>
              <div class="st-field" style="margin-bottom:10px"><label>Message</label><textarea class="form-input" id="mc-message" rows="2" style="resize:vertical"></textarea></div>
              <button class="btn-sm btn-outline" onclick="saveAutomationSection('missed-call')">Save</button>
            </div>

            <!-- Smart Follow-Ups -->
            <div style="background:#0a0a0a;border:1px solid var(--border);border-radius:10px;padding:16px;margin-bottom:12px">
              <div class="st-toggle-row" style="border:none;padding-bottom:12px;padding-top:0">
                <div><div class="st-toggle-label">&#128172; Smart Follow-Ups</div><div class="st-toggle-sub">Auto-text callers who didn't book an appointment</div></div>
                <label class="st-toggle"><input type="checkbox" id="fu-enabled"><span style="font-size:0.75em;color:var(--muted)">On</span></label>
              </div>
              <div class="st-row">
                <div class="st-field"><label>Send after (hours)</label><input class="form-input" id="fu-hours" type="number" value="2" min="0" max="72"></div>
                <div class="st-field"><label>Message</label><textarea class="form-input" id="fu-message" rows="2" style="resize:vertical"></textarea></div>
              </div>
              <button class="btn-sm btn-outline" onclick="saveAutomationSection('followup')">Save</button>
            </div>

            <!-- Appointment Reminders -->
            <div style="background:#0a0a0a;border:1px solid var(--border);border-radius:10px;padding:16px;margin-bottom:12px">
              <div class="st-toggle-row" style="border:none;padding-bottom:12px;padding-top:0">
                <div><div class="st-toggle-label">&#9200; Appointment Reminders</div><div class="st-toggle-sub">Auto-text customers before their appointment to cut no-shows</div></div>
                <label class="st-toggle"><input type="checkbox" id="rm-enabled"><span style="font-size:0.75em;color:var(--muted)">On</span></label>
              </div>
              <div class="st-row">
                <div class="st-field"><label>Hours before</label><input class="form-input" id="rm-hours" type="number" value="24" min="1"></div>
                <div class="st-field"><label>Message (use {time}, {name}, {business})</label><textarea class="form-input" id="rm-message" rows="2" style="resize:vertical"></textarea></div>
              </div>
              <div style="display:flex;gap:8px">
                <button class="btn-sm btn-outline" onclick="saveAutomationSection('reminder')">Save</button>
                <button class="btn-sm btn-outline" onclick="api('/api/reminders/run-check',{method:'POST'}).then(r=>toast('Sent: '+r.sent+' reminders','success'))">Run Now</button>
              </div>
            </div>

            <!-- Review Collection -->
            <div style="background:#0a0a0a;border:1px solid var(--border);border-radius:10px;padding:16px;margin-bottom:12px">
              <div class="st-toggle-row" style="border:none;padding-bottom:12px;padding-top:0">
                <div><div class="st-toggle-label">&#11088; Review Collection</div><div class="st-toggle-sub">Auto-text customers after appointments asking for a Google review</div></div>
                <label class="st-toggle"><input type="checkbox" id="rv-enabled"><span style="font-size:0.75em;color:var(--muted)">On</span></label>
              </div>
              <div class="st-field" style="margin-bottom:10px"><label>Google Review Link</label><input class="form-input" id="rv-link" placeholder="https://g.page/r/YOURLINK/review"></div>
              <div class="st-field" style="margin-bottom:10px"><label>Message (use {name} and {link})</label><textarea class="form-input" id="rv-message" rows="2" style="resize:vertical"></textarea></div>
              <button class="btn-sm btn-outline" onclick="saveAutomationSection('review')">Save</button>
            </div>

            <!-- Deposits -->
            <div style="background:#0a0a0a;border:1px solid var(--border);border-radius:10px;padding:16px">
              <div class="st-toggle-row" style="border:none;padding-bottom:12px;padding-top:0">
                <div><div class="st-toggle-label">&#128178; Appointment Deposits</div><div class="st-toggle-sub">Send a Stripe payment link when the AI books an appointment (requires Stripe key)</div></div>
                <label class="st-toggle"><input type="checkbox" id="dp-enabled"><span style="font-size:0.75em;color:var(--muted)">On</span></label>
              </div>
              <div class="st-field" style="margin-bottom:10px"><label>Deposit Amount ($)</label><input class="form-input" id="dp-amount" type="number" value="50" min="1" style="width:120px"></div>
              <button class="btn-sm btn-outline" onclick="saveAutomationSection('deposit')">Save</button>
            </div>
          </div>
        </div>
      </div>

      <!-- ══ 4. INTEGRATIONS ══ -->
      <div class="st-section">
        <div class="st-section-hdr" id="sthdr-integrations" onclick="toggleSection('integrations')">
          <div class="st-hdr-left">
            <span class="st-icon">&#128268;</span>
            <div><div class="st-title">Integrations</div><div class="st-sub">Stripe, Twilio, server domain, webhooks</div></div>
          </div>
          <span class="st-chevron">&#9660;</span>
        </div>
        <div class="st-section-body" id="stbody-integrations">
          <div style="margin-top:16px">

            <div style="font-size:0.72em;text-transform:uppercase;letter-spacing:1px;color:var(--gold);font-weight:700;margin-bottom:12px">Stripe</div>
            <p style="font-size:0.8em;color:var(--muted);margin-bottom:12px">Required for invoice payment links and appointment deposits. Add your secret key once — all payment features activate.</p>
            <div class="st-field" style="margin-bottom:12px"><label>Stripe Secret Key (sk_live_... or sk_test_...)</label><input class="form-input" id="stripe-sk" type="password" placeholder="sk_live_..." style="font-family:monospace"></div>
            <button class="btn-sm btn-outline" onclick="saveStripeKey()" style="margin-bottom:20px">Save Stripe Key</button>

            <hr class="st-divider">

            <div style="font-size:0.72em;text-transform:uppercase;letter-spacing:1px;color:var(--gold);font-weight:700;margin-bottom:12px">Phone / Twilio</div>
            <div id="serverSetupStatus" style="margin-bottom:12px"></div>
            <div class="st-field" style="margin-bottom:12px"><label>Domain / Tunnel URL (no https://)</label><input class="form-input" id="tk-domain" placeholder="janovum.com or abc123.ngrok.io" style="font-family:monospace"></div>
            <div class="st-row" style="margin-bottom:12px">
              <div class="st-field"><label>Twilio Account SID</label><input class="form-input" id="tk-twilio-sid" placeholder="AC..." style="font-family:monospace;font-size:0.85em"></div>
              <div class="st-field"><label>Twilio Auth Token</label><input class="form-input" id="tk-twilio-token" type="password" placeholder="Auth token" style="font-family:monospace;font-size:0.85em"></div>
            </div>
            <div class="st-field" style="margin-bottom:12px">
              <label>Phone Provider</label>
              <select class="form-input" id="tk-phone-provider" onchange="tkUpdateProviderFields()" style="appearance:auto">
                <option value="twilio">Twilio</option>
                <option value="telnyx">Telnyx</option>
                <option value="plivo">Plivo</option>
                <option value="vonage">Vonage</option>
                <option value="signalwire">SignalWire</option>
              </select>
            </div>
            <div id="tk-provider-fields" style="display:none"></div>
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:14px">
              <input type="checkbox" id="tk-auto-webhooks" checked style="width:16px;height:16px;accent-color:var(--gold)">
              <label for="tk-auto-webhooks" style="font-size:0.8em;color:var(--muted);cursor:pointer">Auto-update webhooks when domain changes</label>
            </div>
            <div style="display:flex;gap:8px">
              <button class="btn" onclick="saveToolkitConfig()">Save Server Config</button>
              <button class="btn-outline" onclick="forceUpdateAllWebhooks()">Update All Webhooks Now</button>
            </div>
            <div id="toolkitSaveResult" style="margin-top:10px;font-size:0.78em"></div>

            <hr class="st-divider">

            <div style="font-size:0.72em;text-transform:uppercase;letter-spacing:1px;color:var(--gold);font-weight:700;margin-bottom:12px">Webhooks</div>
            <div id="whSettingsContainer">
              <p style="font-size:0.8em;color:var(--muted);margin-bottom:12px">Outbound webhooks fire when events happen (appointment booked, call ended, etc.).</p>
              <button class="btn-sm btn-outline" onclick="whAddWebhook()">+ Add Webhook</button>
              <div id="wh-list-settings" style="margin-top:12px"></div>
            </div>
          </div>
        </div>
      </div>

      <!-- ══ 5. REFERRAL PROGRAM ══ -->
      <div class="st-section" style="border-color:#D4AF3744;background:linear-gradient(135deg,#1a1200 0%,#0d0d0d 100%)">
        <div class="st-section-hdr" id="sthdr-referral" onclick="toggleSection('referral')">
          <div class="st-hdr-left">
            <span class="st-icon">&#127873;</span>
            <div><div class="st-title">Referral Program</div><div class="st-sub">Earn 20% of every referred client's monthly spend</div></div>
          </div>
          <span class="st-chevron">&#9660;</span>
        </div>
        <div class="st-section-body" id="stbody-referral">
          <div style="margin-top:16px">
            <div style="font-size:0.78em;color:var(--muted);margin-bottom:16px;line-height:1.6">
              Share your referral link. Every time someone you refer pays their monthly bill, <strong style="color:var(--gold)">you earn 20% of what they spend</strong> — automatically, every month.
            </div>
            <div id="stRefLoading" style="color:var(--muted);font-size:0.82em">Loading your referral link...</div>
            <div id="stRefContent" style="display:none">
              <div style="background:#0a0a0a;border:1px solid var(--border);border-radius:10px;padding:14px 16px;margin-bottom:14px">
                <div style="font-size:0.68em;text-transform:uppercase;letter-spacing:1px;color:var(--muted);margin-bottom:8px">Your Referral Link</div>
                <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
                  <span id="stRefLink" style="font-family:monospace;font-size:0.82em;color:var(--gold);flex:1;word-break:break-all"></span>
                  <button class="btn-sm btn-outline" onclick="stCopyRef()">Copy</button>
                  <button class="btn-sm btn-outline" onclick="stShareRef()">Share</button>
                </div>
              </div>
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
            </div>
            <div id="stRefNoCode" style="display:none">
              <button class="btn" onclick="stGenerateRef()" style="width:100%">Generate My Referral Link</button>
            </div>
          </div>
        </div>
      </div>

      <!-- ══ 6. BILLING & PLAN ══ -->
      <div class="st-section">
        <div class="st-section-hdr" id="sthdr-billing" onclick="toggleSection('billing')">
          <div class="st-hdr-left">
            <span class="st-icon">&#128179;</span>
            <div><div class="st-title">Billing & Plan</div><div class="st-sub">Your current plan and payment method</div></div>
          </div>
          <span class="st-chevron">&#9660;</span>
        </div>
        <div class="st-section-body" id="stbody-billing">
          <div style="margin-top:16px">
            <div style="background:linear-gradient(135deg,#111,#0d0d0d);border:1px solid rgba(247,201,72,0.2);border-radius:12px;padding:18px 22px;margin-bottom:16px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px">
              <div>
                <div style="font-size:0.7em;color:var(--muted);text-transform:uppercase;letter-spacing:1px;margin-bottom:4px">Current Plan</div>
                <div style="font-size:1.1em;font-weight:700" id="stBillingPlanName">Self-Hosted (Free)</div>
              </div>
              <button class="btn-outline btn-sm" onclick="switchTab('billing')">View Plans</button>
            </div>
            <!-- Wallet section kept for payment method storage -->
            <div id="stWalletSection">
              <div style="font-size:0.72em;text-transform:uppercase;letter-spacing:1px;color:var(--gold);font-weight:700;margin-bottom:12px">Payment Method</div>
              <div id="stWalletContent"><div class="loading"><div class="spinner"></div> Loading...</div></div>
            </div>
          </div>
        </div>
      </div>

      <!-- ══ 7. APPEARANCE ══ -->
      <div class="st-section">
        <div class="st-section-hdr" id="sthdr-appearance" onclick="toggleSection('appearance')">
          <div class="st-hdr-left">
            <span class="st-icon">&#127912;</span>
            <div><div class="st-title">Appearance & Notifications</div><div class="st-sub">Theme, accent color, alerts</div></div>
          </div>
          <span class="st-chevron">&#9660;</span>
        </div>
        <div class="st-section-body" id="stbody-appearance">
          <div style="margin-top:16px">
            <div class="st-row">
              <div class="st-field"><label>Theme</label>
                <select class="form-select" id="stTheme" onchange="stSaveAppearance()">
                  <option value="dark">Dark (Default)</option>
                  <option value="midnight">Midnight</option>
                  <option value="carbon">Carbon</option>
                </select>
              </div>
              <div class="st-field"><label>Accent Color</label>
                <select class="form-select" id="stAccent" onchange="stSaveAppearance()">
                  <option value="gold">Gold (Default)</option>
                  <option value="blue">Blue</option>
                  <option value="green">Green</option>
                  <option value="purple">Purple</option>
                </select>
              </div>
            </div>
            <div class="st-field" style="margin-bottom:14px"><label>Font Size</label>
              <select class="form-select" id="stFontSize" onchange="stSaveAppearance()">
                <option value="small">Small</option>
                <option value="medium" selected>Medium (Default)</option>
                <option value="large">Large</option>
              </select>
            </div>
            <hr class="st-divider">
            <div style="font-size:0.72em;text-transform:uppercase;letter-spacing:1px;color:var(--gold);font-weight:700;margin-bottom:12px">Notifications</div>
            <div class="st-toggle-row">
              <div><div class="st-toggle-label">Browser Notifications</div><div class="st-toggle-sub">Alerts when appointments are booked or calls come in</div></div>
              <label class="st-toggle"><input type="checkbox" id="stNotifBrowser" onchange="stSaveNotifs()"><span style="font-size:0.75em;color:var(--muted)">On</span></label>
            </div>
            <div class="st-toggle-row">
              <div><div class="st-toggle-label">Sound Alerts</div><div class="st-toggle-sub">Play a sound when new activity arrives</div></div>
              <label class="st-toggle"><input type="checkbox" id="stNotifSound" onchange="stSaveNotifs()"><span style="font-size:0.75em;color:var(--muted)">On</span></label>
            </div>
          </div>
        </div>
      </div>

      <!-- ══ 8. ADVANCED ══ -->
      <div class="st-section">
        <div class="st-section-hdr" id="sthdr-advanced" onclick="toggleSection('advanced')">
          <div class="st-hdr-left">
            <span class="st-icon">&#9881;</span>
            <div><div class="st-title">Advanced</div><div class="st-sub">VPS deployment, data management, version info</div></div>
          </div>
          <span class="st-chevron">&#9660;</span>
        </div>
        <div class="st-section-body" id="stbody-advanced">
          <div style="margin-top:16px">
            <div style="font-size:0.72em;text-transform:uppercase;letter-spacing:1px;color:var(--gold);font-weight:700;margin-bottom:12px">VPS Deployment Guide</div>
            <details style="margin-bottom:8px"><summary style="font-size:0.84em;color:var(--gold);cursor:pointer;font-weight:600;padding:8px 0">1. Install Dependencies</summary>
              <pre style="background:#0a0a0a;padding:14px;border-radius:8px;font-size:0.75em;overflow-x:auto;margin-top:8px;color:#ccc;border:1px solid #1a1a1a"><code>sudo apt update && sudo apt upgrade -y
sudo apt install python3 python3-pip python3-venv -y
python3 -m venv /opt/janovum/venv
source /opt/janovum/venv/bin/activate
pip install flask requests pillow aiohttp</code></pre>
            </details>
            <details style="margin-bottom:8px"><summary style="font-size:0.84em;color:var(--gold);cursor:pointer;font-weight:600;padding:8px 0">2. Systemd Service (auto-start)</summary>
              <pre style="background:#0a0a0a;padding:14px;border-radius:8px;font-size:0.75em;overflow-x:auto;margin-top:8px;color:#ccc;border:1px solid #1a1a1a"><code>sudo tee /etc/systemd/system/janovum.service &lt;&lt;EOF
[Unit]
Description=Janovum Platform
After=network.target
[Service]
WorkingDirectory=/opt/janovum/platform
ExecStart=/opt/janovum/venv/bin/python server_v2.py
Restart=always
[Install]
WantedBy=multi-user.target
EOF
sudo systemctl enable janovum && sudo systemctl start janovum</code></pre>
            </details>
            <details><summary style="font-size:0.84em;color:var(--gold);cursor:pointer;font-weight:600;padding:8px 0">3. Nginx + SSL</summary>
              <pre style="background:#0a0a0a;padding:14px;border-radius:8px;font-size:0.75em;overflow-x:auto;margin-top:8px;color:#ccc;border:1px solid #1a1a1a"><code>sudo apt install nginx certbot python3-certbot-nginx -y
# Configure nginx to proxy port 5050
sudo certbot --nginx -d YOUR_DOMAIN</code></pre>
            </details>

            <hr class="st-divider">

            <div style="font-size:0.72em;text-transform:uppercase;letter-spacing:1px;color:var(--gold);font-weight:700;margin-bottom:12px">Data Management</div>
            <div style="display:flex;gap:8px;flex-wrap:wrap">
              <button class="btn-outline" onclick="stExportData()">&#8681; Export All Data</button>
              <button class="btn-outline" onclick="stImportData()">&#8679; Import Data</button>
              <button class="btn-outline" style="color:#ef5350;border-color:#5a2a2a" onclick="stResetAll()">Reset All Data</button>
            </div>
            <div id="stDataStatus" style="margin-top:10px;font-size:0.78em"></div>

            <hr class="st-divider">

            <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;font-size:0.84em">
              <div><span style="color:var(--muted)">Version:</span> <span style="color:var(--gold);font-weight:700">Platform v9.2</span></div>
              <div><span style="color:var(--muted)">Build:</span> <span>April 2026</span></div>
              <div><span style="color:var(--muted)">Status:</span> <span style="color:var(--green);font-weight:600">Operational</span></div>
              <div><span style="color:var(--muted)">Server:</span> <span id="advServerInfo">janovum.com</span></div>
            </div>
          </div>
        </div>
      </div>

    </div>

    <!-- ═══ AI EMPLOYEES TAB ═══ -->
'''

    content = content[:start_idx] + NEW_SETTINGS + content[end_idx:]
    print('Settings tab rebuilt, new content length:', len(NEW_SETTINGS))
else:
    print('ERROR: settings tab markers not found')

# ─────────────────────────────────────────────────────────────────────────────
# 4. ADD saveBizProfile + saveSoulConfig JS functions
# ─────────────────────────────────────────────────────────────────────────────
BIZ_SOUL_JS = """
async function saveBizProfile() {
  const data = {
    business_name: document.getElementById('biz-name')?.value?.trim()||'',
    business_type: document.getElementById('biz-type')?.value?.trim()||'',
    business_phone: document.getElementById('biz-phone')?.value?.trim()||'',
    business_email: document.getElementById('biz-email')?.value?.trim()||'',
    business_address: document.getElementById('biz-address')?.value?.trim()||'',
    business_hours: document.getElementById('biz-hours')?.value?.trim()||'',
    business_description: document.getElementById('biz-desc')?.value?.trim()||'',
  };
  try {
    await api('/api/toolkit/update-config', {method:'POST', body:JSON.stringify(data)});
    const el = document.getElementById('bizSaveStatus');
    if (el) { el.textContent = 'Saved!'; el.style.color='var(--green)'; setTimeout(()=>{el.textContent=''},3000); }
    toast('Business profile saved!', 'success');
  } catch(e) { toast('Error saving profile', 'error'); }
}

async function saveSoulConfig() {
  const data = {
    soul_name: document.getElementById('soul-name')?.value?.trim()||'',
    soul_tone: document.getElementById('soul-tone')?.value||'professional',
    soul_instructions: document.getElementById('soul-instructions')?.value?.trim()||'',
  };
  try {
    await api('/api/toolkit/update-config', {method:'POST', body:JSON.stringify(data)});
    toast('Personality saved!', 'success');
  } catch(e) { toast('Error saving personality', 'error'); }
}

async function loadBizProfile() {
  try {
    const cfg = await api('/api/toolkit/config');
    const fields = {
      'biz-name': cfg.business_name,
      'biz-type': cfg.business_type,
      'biz-phone': cfg.business_phone,
      'biz-email': cfg.business_email,
      'biz-address': cfg.business_address,
      'biz-hours': cfg.business_hours,
      'biz-desc': cfg.business_description,
      'soul-name': cfg.soul_name,
      'soul-instructions': cfg.soul_instructions,
    };
    for (const [id, val] of Object.entries(fields)) {
      const el = document.getElementById(id);
      if (el && val) el.value = val;
    }
    const tone = document.getElementById('soul-tone');
    if (tone && cfg.soul_tone) tone.value = cfg.soul_tone;
  } catch(e) {}
}

"""

marker_biz = 'async function loadAutomationSettings'
if marker_biz in content:
    content = content.replace(marker_biz, BIZ_SOUL_JS + marker_biz)
    print('saveBizProfile + saveSoulConfig added')
else:
    print('WARNING: loadAutomationSettings marker not found for biz/soul JS injection')

# ─────────────────────────────────────────────────────────────────────────────
# 5. Patch loadSettings to also call loadBizProfile
# ─────────────────────────────────────────────────────────────────────────────
old_load_s = '''async function loadSettings() {
  stLoadSettings();
  loadAuthStatus();
  loadToolkitConfig();
  stLoadReferral();
  loadAutomationSettings();
  loadStripeKey();'''

new_load_s = '''async function loadSettings() {
  stLoadSettings();
  loadAuthStatus();
  loadToolkitConfig();
  stLoadReferral();
  loadAutomationSettings();
  loadStripeKey();
  loadBizProfile();'''

if old_load_s in content:
    content = content.replace(old_load_s, new_load_s)
    print('loadSettings patched with loadBizProfile')
else:
    print('WARNING: loadSettings not found for biz patch')

# ─────────────────────────────────────────────────────────────────────────────
# 6. CLEAN SIDEBAR — remove bloat tabs
# ─────────────────────────────────────────────────────────────────────────────
tabs_to_remove = [
    "data-tab=\"crypto\"",
    "data-tab=\"pipeline\"",          # dup — in Agency Hub
    "data-tab=\"outreach\"",
    "data-tab=\"community\"",
    "data-tab=\"skills\"",
    "data-tab=\"director\"",
    "data-tab=\"bots\"",
    "data-tab=\"agents\"",
    "data-tab=\"multiagent\"",
    "data-tab=\"tracing\"",
    "data-tab=\"approvals\"",
    "data-tab=\"events\"",
    "data-tab=\"soul\"",
    "data-tab=\"healing\"",
    "data-tab=\"mcp\"",
    "data-tab=\"sandbox\"",
    "data-tab=\"webhooks\"",
    "data-tab=\"crm\"",               # dup — in Agency Hub
]

import re
removed = []
for tab_attr in tabs_to_remove:
    pattern = r'    <div class="nav-item[^>]*' + re.escape(tab_attr) + r'[^<]*(?:<[^>]*>[^<]*</[^>]*>)*[^<]*</div>\n'
    new_content, n = re.subn(pattern, '', content)
    if n > 0:
        content = new_content
        removed.append(tab_attr)
    else:
        # try simpler match
        pattern2 = r'    <div[^>]*' + re.escape(tab_attr) + r'[^>]*>.*?</div>\n'
        new_content, n = re.subn(pattern2, '', content)
        if n > 0:
            content = new_content
            removed.append(tab_attr + ' (simple)')

print(f'Removed {len(removed)} sidebar tabs:', removed)

open('/root/janovum-toolkit/Janovum_Platform_v3.html', 'w').write(content)
print('Done, final size:', len(content))
