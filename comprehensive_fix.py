#!/usr/bin/env python3
"""Comprehensive fix for Janovum Platform v3 on VPS."""

HTML_PATH = '/root/janovum-toolkit/Janovum_Platform_v3.html'

with open(HTML_PATH, 'r', encoding='utf-8') as f:
    html = f.read()

fixes_applied = []
warnings = []

def replace_or_warn(name, old, new):
    global html
    if old in html:
        html = html.replace(old, new)
        fixes_applied.append(name)
    else:
        warnings.append(f"NOT FOUND: {name}")

# ─────────────────────────────────────────────────────────────────
# FIX 1: Always auto-login as admin + set janovum_user
# ─────────────────────────────────────────────────────────────────
# Find checkTkSession and replace the whole function regardless of form
import re
pattern = r'(// (?:Check session on load|Auto-login on load)\n\(function checkTkSession\(\) \{.*?\}\)\(\);)'
match = re.search(pattern, html, re.DOTALL)
if match:
    old_cs = match.group(0)
    new_cs = """// Auto-login as admin — private toolkit page
(function checkTkSession() {
  tkLoginAs(ADMIN_USER, { displayName: 'Jaden', role: 'admin' });
  if (!localStorage.getItem('janovum_user')) {
    localStorage.setItem('janovum_user', JSON.stringify({name:'Jaden',email:'jaden@janovum.com',role:'admin',plan:'paid'}));
  }
})();"""
    html = html.replace(old_cs, new_cs)
    fixes_applied.append("FIX 1: Always auto-login as admin + set janovum_user")
else:
    warnings.append("FIX 1: checkTkSession not found via regex")

# ─────────────────────────────────────────────────────────────────
# FIX 2: Nav cursor grab -> pointer
# ─────────────────────────────────────────────────────────────────
html = html.replace('cursor: grab;', 'cursor: pointer;', 1)  # only nav-item
fixes_applied.append("FIX 2: Nav cursor pointer")

# ─────────────────────────────────────────────────────────────────
# FIX 3: Nav click — protect from drag interference
# ─────────────────────────────────────────────────────────────────
replace_or_warn(
    "FIX 3: Nav drag flag in click handler",
    """// Desktop sidebar clicks
document.querySelectorAll('.nav-item').forEach(item => {
  item.addEventListener('click', () => {
    const tab = item.dataset.tab;
    switchTab(tab);
  });
});""",
    """// Desktop sidebar clicks — protected from drag interference
var _navDragActive = false;
document.querySelectorAll('.nav-item').forEach(item => {
  item.addEventListener('click', (e) => {
    if (_navDragActive) return;
    const tab = item.dataset.tab;
    if (tab) switchTab(tab);
  });
});"""
)

replace_or_warn(
    "FIX 3b: ondragend sets _navDragActive timeout",
    """    item.ondragend = function() {
      item.classList.remove('drag-ghost');
      document.querySelectorAll('.drag-target,.drag-hover,.drag-over-group').forEach(el => el.classList.remove('drag-target','drag-hover','drag-over-group'));
      dragTab = null;
    };""",
    """    item.ondragend = function() {
      item.classList.remove('drag-ghost');
      document.querySelectorAll('.drag-target,.drag-hover,.drag-over-group').forEach(el => el.classList.remove('drag-target','drag-hover','drag-over-group'));
      dragTab = null;
      _navDragActive = true;
      setTimeout(() => { _navDragActive = false; }, 150);
    };"""
)

# ─────────────────────────────────────────────────────────────────
# FIX 4: Add workflow pipeline back to tool detail view
# ─────────────────────────────────────────────────────────────────
old4 = (
    "      + '<div id=\"' + tid + '_detail\" style=\"display:none;margin-top:12px;padding-top:12px;border-top:1px solid #1a1a1a\">'\n"
    "      + '<div style=\"font-size:0.72em;color:var(--blue);font-weight:700;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px\">Parameters</div>'\n"
    "      + '<table style=\"width:100%;border-collapse:collapse;font-size:0.78em\"><thead><tr style=\"border-bottom:1px solid #2a2a2a\">'")

new4 = (
    "    var reqPms = t.params.filter(function(p){return p.required;});\n"
    "    var wfHtml = '<div style=\"font-size:0.72em;color:var(--gold);font-weight:700;text-transform:uppercase;letter-spacing:1px;margin-bottom:10px\">Workflow Pipeline</div>';\n"
    "    wfHtml += '<div style=\"display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-bottom:14px\">';\n"
    "    wfHtml += '<div style=\"background:#111;border:1px solid var(--border);border-radius:6px;padding:6px 12px;font-size:0.72em\"><span style=\"color:var(--blue)\">&#9654;</span> <span style=\"color:var(--muted)\">Input</span></div>';\n"
    "    wfHtml += '<span style=\"color:var(--dim)\">&#10230;</span>';\n"
    "    for (var rp = 0; rp < reqPms.length; rp++) { wfHtml += '<div style=\"background:#0d1a0d;border:1px solid #1a3a1a;border-radius:6px;padding:6px 12px;font-size:0.72em\"><span style=\"color:var(--green);font-weight:700\">' + esc(reqPms[rp].name) + '</span></div><span style=\"color:var(--dim)\">&#10230;</span>'; }\n"
    "    wfHtml += '<div style=\"background:#111;border:1px solid var(--gold);border-radius:6px;padding:6px 12px;font-size:0.72em\"><span style=\"color:var(--gold)\">&#9881;</span> <span style=\"color:var(--gold);font-weight:700\">' + esc(t.name) + '</span></div>';\n"
    "    wfHtml += '<span style=\"color:var(--dim)\">&#10230;</span><div style=\"background:#111;border:1px solid var(--border);border-radius:6px;padding:6px 12px;font-size:0.72em\"><span style=\"color:var(--green)\">&#9989;</span> <span style=\"color:var(--muted)\">Result</span></div></div>';\n"
    "      + '<div id=\"' + tid + '_detail\" style=\"display:none;margin-top:12px;padding-top:12px;border-top:1px solid #1a1a1a\">'\n"
    "      + wfHtml\n"
    "      + '<div style=\"font-size:0.72em;color:var(--blue);font-weight:700;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px\">Parameters</div>'\n"
    "      + '<table style=\"width:100%;border-collapse:collapse;font-size:0.78em\"><thead><tr style=\"border-bottom:1px solid #2a2a2a\">'")

if old4 in html:
    html = html.replace(old4, new4)
    fixes_applied.append("FIX 4: Workflow Pipeline added to tool detail")
else:
    warnings.append("FIX 4: tool detail section not matched exactly")
    # Try to find it
    idx = html.find("tid + '_detail'")
    if idx >= 0:
        print("CONTEXT around tid+_detail:", repr(html[idx-10:idx+200]))

# ─────────────────────────────────────────────────────────────────
# FIX 5: badge null guard
# ─────────────────────────────────────────────────────────────────
replace_or_warn(
    "FIX 5: badge null guard",
    "    const badge = document.getElementById('clientBadgeCount');\n    if (badge && data.total_clients > 0) { badge.textContent = data.total_clients; badge.style.display = ''; } else { badge.style.display = 'none'; }",
    "    const badge = document.getElementById('clientBadgeCount');\n    if (badge) { if (data.total_clients > 0) { badge.textContent = data.total_clients; badge.style.display = ''; } else { badge.style.display = 'none'; } }"
)

# ─────────────────────────────────────────────────────────────────
# FIX 6: initSetupLock — suppress guest banner for admin
# ─────────────────────────────────────────────────────────────────
replace_or_warn(
    "FIX 6: initSetupLock admin mode",
    """// Apply on load — NEVER hard-lock nav, just show appropriate banner
(function initSetupLock() {
  const state = getUserState();
  // Always unlock nav — browsing is always allowed
  unlockNav();
  // Hide setup banner if user is set up or is admin/paid/trial
  const banner = document.getElementById('setupLockBanner');
  if (banner) {
    banner.style.display = (state === 'guest' && !isSetupComplete()) ? 'flex' : 'none';
  }
  // Show appropriate auth banner + topbar buttons
  setTimeout(() => { renderAuthBanner(); renderTopbarAuth(); }, 100);
})();""",
    """// Always admin on this private page — suppress all guest banners
(function initSetupLock() {
  unlockNav();
  const banner = document.getElementById('setupLockBanner');
  if (banner) banner.style.display = 'none';
  localStorage.setItem('janovum_setup_complete', '1');
  setTimeout(() => { try { renderTopbarAuth(); } catch(e){} }, 100);
})();"""
)

# ─────────────────────────────────────────────────────────────────
# Write result
# ─────────────────────────────────────────────────────────────────
with open(HTML_PATH, 'w', encoding='utf-8') as f:
    f.write(html)

print("\n=== APPLIED FIXES ===")
for fix in fixes_applied:
    print("  OK", fix)

if warnings:
    print("\n=== WARNINGS ===")
    for w in warnings:
        print("  !!", w)

print(f"\nFile size: {len(html)} bytes")
assert 'tkLoginAs(ADMIN_USER' in html, "tkLoginAs not found!"
assert '_navDragActive' in html, "_navDragActive not found!"
print("Sanity checks passed.")
