"""
Fix the cache corruption bug:
1. Inject _safeLS() helper + localStorage quota/error protection at page top
2. Replace ALL JSON.parse(localStorage.getItem(...)) patterns with _safeLS()
3. Wrap all localStorage.setItem calls to catch QuotaExceededError
4. Add startup integrity check — auto-clears any key with corrupted JSON
"""
import re

SRC = r"C:\Users\jigga\OneDrive\Desktop\janovum company planing\Janovum_Platform_v3.html"

with open(SRC, encoding='utf-8', errors='ignore') as f:
    c = f.read()

print(f"Starting: {len(c):,} chars")

# ─────────────────────────────────────────────────────────
# STEP 1: Inject the safe localStorage wrapper into <head>
# ─────────────────────────────────────────────────────────

safe_ls_script = '''
<script>
// ════════════════════════════════════════════════════════════
// SAFE LOCALSTORAGE — prevents cache corruption from crashing the app
// ════════════════════════════════════════════════════════════

// _safeLS(key, fallback) — safe JSON read, auto-heals corrupted keys
function _safeLS(key, fallback) {
  try {
    var raw = localStorage.getItem(key);
    if (raw === null || raw === undefined || raw === '') return JSON.parse(fallback);
    // Detect clearly invalid values
    if (raw === 'undefined' || raw === 'null' && fallback !== 'null') {
      localStorage.removeItem(key);
      return JSON.parse(fallback);
    }
    return JSON.parse(raw);
  } catch(e) {
    console.warn('[SafeLS] Corrupted key removed:', key, raw ? raw.slice(0,80) : '(empty)');
    try { localStorage.removeItem(key); } catch(e2) {}
    try { return JSON.parse(fallback); } catch(e3) { return null; }
  }
}

// Wrap Storage.prototype.setItem — catch QuotaExceededError, clear non-critical cache
(function() {
  var _orig = Storage.prototype.setItem;
  var _lowPriority = [
    'janovum_media_gallery','janovum_access_logs','janovum_job_history',
    'janovum_proactive_log','janovum_browser_history','janovum_transcriptions',
    'janovum_social_calendar','janovum_social_posts'
  ];
  Storage.prototype.setItem = function(key, value) {
    try {
      _orig.call(this, key, value);
    } catch(e) {
      if (e.name === 'QuotaExceededError' || e.code === 22) {
        console.warn('[SafeLS] Quota hit — clearing low-priority cache');
        _lowPriority.forEach(function(k) {
          try { localStorage.removeItem(k); } catch(e2) {}
        });
        try { _orig.call(this, key, value); } catch(e2) {
          console.warn('[SafeLS] Still full after cleanup, skipping write for:', key);
        }
      } else {
        console.warn('[SafeLS] setItem error for', key, e.message);
      }
    }
  };
})();

// Startup integrity check — scan all janovum_ keys and remove any with bad JSON
(function() {
  var keys = [];
  try {
    for (var i = 0; i < localStorage.length; i++) {
      var k = localStorage.key(i);
      if (k && k.startsWith('janovum_')) keys.push(k);
    }
  } catch(e) {}
  keys.forEach(function(key) {
    try {
      var raw = localStorage.getItem(key);
      if (raw && raw !== 'undefined') JSON.parse(raw); // just test if parseable
    } catch(e) {
      console.warn('[SafeLS] Startup: removing corrupted key:', key);
      try { localStorage.removeItem(key); } catch(e2) {}
    }
  });
})();
</script>
'''

# Insert right after <head>
if '_safeLS' not in c:
    c = c.replace('<head>', '<head>\n' + safe_ls_script, 1)
    print("Injected _safeLS + quota protection + startup integrity check")
else:
    print("_safeLS already present — skipping injection")

# ─────────────────────────────────────────────────────────
# STEP 2: Replace all JSON.parse(localStorage.getItem(...) || 'X') with _safeLS()
# Pattern: JSON.parse(localStorage.getItem('KEY') || 'FALLBACK')
# Also handles double quotes and spaces
# ─────────────────────────────────────────────────────────

# Count before
before = len(re.findall(r"JSON\.parse\(localStorage\.getItem\(", c))
print(f"Unguarded JSON.parse(localStorage reads before: {before}")

# Replace pattern: JSON.parse(localStorage.getItem('x') || 'y')
# Handles both single and double quotes for key and fallback
def replace_safe_ls(match):
    key = match.group(1)
    fallback = match.group(2)
    return f'_safeLS({key}, {fallback})'

c = re.sub(
    r"JSON\.parse\(localStorage\.getItem\((['\"][\w_-]+['\"])\)\s*\|\|\s*(['\"][^'\"]*['\"])\)",
    replace_safe_ls,
    c
)

# Also handle the pattern without fallback (just bare JSON.parse(localStorage.getItem('x')))
# These need null as fallback
def replace_safe_ls_no_fallback(match):
    key = match.group(1)
    return f'_safeLS({key}, \'null\')'

c = re.sub(
    r"JSON\.parse\(localStorage\.getItem\((['\"][\w_-]+['\"])\)\)",
    replace_safe_ls_no_fallback,
    c
)

after = len(re.findall(r"JSON\.parse\(localStorage\.getItem\(", c))
print(f"Remaining unguarded reads after: {after}")
print(f"Replaced: {before - after}")

# ─────────────────────────────────────────────────────────
# STEP 3: Sanitize the deployed_clients write — strip non-serializable junk
# The agentConfig object might have bad fields
# ─────────────────────────────────────────────────────────
# Wrap the clientPayload stringify to ensure clean serialization
old_deploy_save = "localClients.unshift({ ...clientPayload, status: 'deploying', deployed_at: new Date().toISOString() });"
new_deploy_save = """try {
    var _clean = JSON.parse(JSON.stringify({ ...clientPayload, status: 'deploying', deployed_at: new Date().toISOString() }));
    localClients.unshift(_clean);
  } catch(_e) {
    localClients.unshift({ name: clientPayload.business_name || 'Client', status: 'deploying', deployed_at: new Date().toISOString() });
  }"""
if old_deploy_save in c:
    c = c.replace(old_deploy_save, new_deploy_save)
    print("Fixed deploy client payload serialization")

# ─────────────────────────────────────────────────────────
# SAVE FIRST, then verify
# ─────────────────────────────────────────────────────────
with open(SRC, 'w', encoding='utf-8') as f:
    f.write(c)
print("\nSaved.")
print(f"Final: {len(c):,} chars")
print(f"_safeLS calls: {c.count('_safeLS(')}")
print(f"switchTab: {c.count('function switchTab')}")
