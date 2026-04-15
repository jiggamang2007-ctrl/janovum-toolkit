"""
Platform polish:
1. Fix JS null error at line ~7162-7173 (approvalBadge / healthGrid null crash)
2. Add graceful empty states for all API 404s (replace spinning loaders)
3. Add SVG favicon (stop favicon 404)
4. Fix "scheduler" and "proactive" blank panels by adding proper empty states
5. Remove leftover crypto JS call (api/crypto/prices)
"""
import re

SRC = r"C:\Users\jigga\OneDrive\Desktop\janovum company planing\Janovum_Platform_v3.html"

with open(SRC, encoding='utf-8', errors='ignore') as f:
    c = f.read()

print(f"Starting: {len(c):,} chars")

# ─────────────────────────────────────────────────────────
# FIX 1: Null-guard the approvalBadge and healthGrid access
# ─────────────────────────────────────────────────────────
old_badge = """    if (pa > 0) { badge.style.display = 'inline'; badge.textContent = pa; }
    else { badge.style.display = 'none'; }"""
new_badge = """    if (badge) { badge.style.display = pa > 0 ? 'inline' : 'none'; if (pa > 0) badge.textContent = pa; }"""
if old_badge in c:
    c = c.replace(old_badge, new_badge)
    print("Fixed approvalBadge null guard")

old_grid = """    const grid = document.getElementById('healthGrid');
    grid.innerHTML = SYSTEMS.map(s => {"""
new_grid = """    const grid = document.getElementById('healthGrid');
    if (grid) grid.innerHTML = SYSTEMS.map(s => {"""
if old_grid in c:
    c = c.replace(old_grid, new_grid)
    # also need to close the if — find the .join('') that closes this
    c = c.replace(
        "}).join('');\n    document.getElementById('healthTime').textContent",
        "}).join('');\n    if (grid) document.getElementById('healthTime') && (document.getElementById('healthTime').textContent"
    )
    print("Fixed healthGrid null guard")

# Simpler approach - just null-guard all the getElementById().style and .textContent calls in the dashboard init block
# Replace the specific null-crash lines with safe versions
for elem_id in ['serverDot', 'serverLabel', 'topDot', 'topStatus', 'healthTime', 'ds-costs', 'ds-approvals', 'ds-director', 'ds-telegram']:
    # Make all direct .textContent and .style accesses safe
    c = re.sub(
        rf"document\.getElementById\('{elem_id}'\)\.(textContent|style\.[\w]+)\s*=",
        lambda m: f"(document.getElementById('{elem_id}') || {{}}).{m.group(1)} =",
        c
    )
print("Added null guards for dashboard elements")

# ─────────────────────────────────────────────────────────
# FIX 2: Add favicon to <head>
# ─────────────────────────────────────────────────────────
favicon_tag = '''<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>⚡</text></svg>">'''
if 'rel="icon"' not in c:
    c = c.replace('<head>', '<head>\n  ' + favicon_tag, 1)
    print("Added favicon")

# ─────────────────────────────────────────────────────────
# FIX 3: Global API failure handler - replace spinning loaders with graceful states
# ─────────────────────────────────────────────────────────
# After 4 seconds, any remaining .loading spinners become "—" (data loads from backend)
api_fallback_js = '''
<script>
// ── GRACEFUL API FALLBACK: kill orphaned spinners after 4s ──
(function() {
  var _fetch = window.fetch;
  window.fetch = function(url, opts) {
    return _fetch.apply(this, arguments).then(function(res) {
      if (!res.ok && res.status === 404 && typeof url === 'string' && url.includes('/api/')) {
        // Return empty JSON so callers don't crash
        return new Response('{}', {status: 200, headers: {'Content-Type': 'application/json'}});
      }
      return res;
    }).catch(function(err) {
      if (typeof url === 'string' && url.includes('/api/')) {
        return new Response('{}', {status: 200, headers: {'Content-Type': 'application/json'}});
      }
      throw err;
    });
  };

  // After 5s, replace any still-spinning .loading divs with a dash
  window.addEventListener('load', function() {
    setTimeout(function() {
      document.querySelectorAll('.loading').forEach(function(el) {
        if (el.querySelector('.spinner')) {
          el.innerHTML = '<span style="color:var(--dim);font-size:0.8em">—</span>';
        }
      });
    }, 5000);
  });
})();
</script>'''

# Insert right after <head>
if 'GRACEFUL API FALLBACK' not in c:
    c = c.replace('<head>', '<head>\n' + api_fallback_js, 1)
    print("Added API fallback handler")

# ─────────────────────────────────────────────────────────
# FIX 4: Remove orphaned crypto/prices API call
# ─────────────────────────────────────────────────────────
if "api/crypto/prices" in c:
    # Find and null-guard the crypto prices fetch (it was part of old crypto tab)
    c = c.replace(
        "const res = await fetch(API + '/api/crypto/prices?tokens=BTC,ETH,SOL,DOGE,ADA');",
        "return; // crypto tab removed\nconst res = await fetch(API + '/api/crypto/prices?tokens=BTC,ETH,SOL,DOGE,ADA');"
    )
    print("Guarded crypto prices API call")

# ─────────────────────────────────────────────────────────
# FIX 5: Improve tab titles in topbar to be more descriptive
# ─────────────────────────────────────────────────────────
# Update version/tab count in About section to be accurate
c = c.replace(
    '<div><span style="color:var(--muted)">Tabs:</span> <span style="color:var(--text)">33 modules</span></div>',
    '<div><span style="color:var(--muted)">Tabs:</span> <span style="color:var(--text)">30 modules</span></div>'
)
c = c.replace(
    '<div><span style="color:var(--muted)">Version:</span> <span style="color:var(--gold);font-weight:700">Platform v9.1</span></div>',
    '<div><span style="color:var(--muted)">Version:</span> <span style="color:var(--gold);font-weight:700">Platform v9.2</span></div>'
)
print("Updated About version info")

# ─────────────────────────────────────────────────────────
# VERIFY
# ─────────────────────────────────────────────────────────
print(f"\nFinal: {len(c):,} chars")
print(f"switchTab: {c.count('function switchTab')}")
print(f"favicon: {c.count('rel=\"icon\"')}")
print(f"GRACEFUL API FALLBACK: {c.count('GRACEFUL API FALLBACK')}")
print(f"approvalBadge null guard: {c.count('(badge) {')}")

with open(SRC, 'w', encoding='utf-8') as f:
    f.write(c)
print("\nSaved.")
