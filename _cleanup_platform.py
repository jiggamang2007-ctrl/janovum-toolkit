"""
Platform cleanup:
1. Add VISIBLE group labels to sidebar (currently invisible HTML comments)
2. Remove these tabs from sidebar → condense into Settings accordion:
   models, mcp, security, healing, tracing, approvals, soul, howto, deploy
3. Reorganize remaining tabs into clean groups
4. Add Settings accordion sections for each condensed tab
"""
import re

SRC_BASE = r"C:\Users\jigga\OneDrive\Desktop\janovum company planing\Janovum_Platform_v3.html"
# Use the clean crypto-removed version as input
# (This was already saved by _fix_platform.py)
import os
SRC = SRC_BASE

with open(SRC, encoding='utf-8', errors='ignore') as f:
    c = f.read()

print(f"Starting: {len(c):,} chars, {c.count('data-tab=') } tabs total")

# ─────────────────────────────────────────────────────────
# STEP 1: Rebuild the entire sidebar nav with visible groups
# ─────────────────────────────────────────────────────────

# Find sidebar nav start and end
nav_start = c.find('<nav class="sidebar-nav" id="sidebarNav">')
nav_end = c.find('</nav>', nav_start) + len('</nav>')
old_nav = c[nav_start:nav_end]
print(f"Old nav length: {len(old_nav):,}")

# Helper to find a nav-item by data-tab and extract it
def get_nav_item(html, tab_id):
    pattern = rf'<div class="nav-item"[^>]*data-tab="{tab_id}"[^>]*>.*?</div>'
    m = re.search(pattern, html, re.DOTALL)
    return m.group(0) if m else None

# Extract all existing nav items
nav_items = {}
for m in re.finditer(r'<div class="nav-item[^"]*"[^>]*data-tab="([\w-]+)"[^>]*>.*?</div>', old_nav, re.DOTALL):
    tab_id = re.search(r'data-tab="([\w-]+)"', m.group(0)).group(1)
    # Normalize — remove 'active' class so dashboard doesn't start highlighted
    item_html = re.sub(r'class="nav-item active"', 'class="nav-item"', m.group(0))
    nav_items[tab_id] = item_html

print(f"Extracted {len(nav_items)} nav items")

# Group label style (visible separator with label)
def group_label(text):
    return f'\n    <div class="nav-group-label">{text}</div>'

# Tabs to REMOVE from sidebar (will live in Settings accordion)
CONDENSE_TO_SETTINGS = {'models', 'mcp', 'security', 'healing', 'tracing', 'approvals', 'soul', 'howto', 'deploy'}

# New sidebar layout
SIDEBAR_LAYOUT = [
    ('BUSINESS ESSENTIALS', ['dashboard', 'clients', 'crm', 'receptionist', 'copilot', 'payments', 'analytics', 'scheduler']),
    ('GROWTH', ['idealab', 'proposals', 'community', 'skills']),
    ('AGENTS & AUTOMATION', ['employees', 'multiagent', 'workflows', 'proactive', 'director']),
    ('COMMUNICATION', ['channels', 'social', 'voice']),
    ('POWER TOOLS', ['chat', 'computer', 'browser', 'media', 'files', 'knowledge', 'tools']),
    ('SETUP & BILLING', ['billing', 'setup', 'settings']),
]

new_nav_html = '<nav class="sidebar-nav" id="sidebarNav">\n'
new_nav_html += '    <!-- CUSTOM GROUPS (populated by JS) -->\n'

for group_name, tab_ids in SIDEBAR_LAYOUT:
    new_nav_html += group_label(group_name) + '\n'
    for tab_id in tab_ids:
        if tab_id in nav_items:
            new_nav_html += '    ' + nav_items[tab_id] + '\n'
        else:
            print(f"  WARNING: tab '{tab_id}' not found in nav items")

new_nav_html += '</nav>'

c = c[:nav_start] + new_nav_html + c[nav_end:]
print(f"New nav: {new_nav_html.count('data-tab=')} tabs")

# ─────────────────────────────────────────────────────────
# STEP 2: Add .nav-group-label CSS
# ─────────────────────────────────────────────────────────
group_label_css = """
  /* ── NAV GROUP LABELS ── */
  .nav-group-label {
    font-size: 0.6em;
    font-weight: 700;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: var(--dim);
    padding: 14px 16px 4px;
    margin-top: 4px;
    user-select: none;
    pointer-events: none;
  }
  .nav-group-label:first-child { padding-top: 6px; margin-top: 0; }
"""

# Insert before first occurrence of /* ── SCROLLBAR ── */ or similar
insert_before = c.find('/* ── SCROLLBAR ──')
if insert_before == -1:
    insert_before = c.find('.sidebar-nav {')
if insert_before != -1:
    c = c[:insert_before] + group_label_css + c[insert_before:]
    print("Inserted group label CSS")

# ─────────────────────────────────────────────────────────
# STEP 3: Add condensed sections to Settings tab
# ─────────────────────────────────────────────────────────

# Sections to add to settings (title, icon, tab_id, description)
SETTINGS_SECTIONS = [
    ('AI Models', '🤖', 'models', 'Configure which AI models power your agents. Switch between Claude, GPT-4, Groq, Gemini and more.'),
    ('MCP Servers', '🔌', 'mcp', 'Connect external tools and data sources via Model Context Protocol servers.'),
    ('Security', '🔒', 'security', 'API key management, access controls, and security audit logs.'),
    ('Auto-Healing', '🔧', 'healing', 'Configure automatic error recovery and system health monitoring.'),
    ('Request Tracing', '📊', 'tracing', 'Debug and trace agent requests, tool calls, and API activity.'),
    ('Approvals', '✅', 'approvals', 'Set up approval workflows for high-stakes agent actions before they execute.'),
    ('Agent Soul', '💜', 'soul', 'Define your agent\'s core personality, tone, and behavioral guidelines.'),
    ('Deploy / VPS', '🚀', 'deploy', 'Manage your VPS deployment, domain, and server configuration.'),
]

# Build the settings accordion HTML to append
accordion_html = '\n      <!-- ════ CONDENSED SETTINGS ACCORDION ════ -->\n'
accordion_html += '      <div style="margin-top:24px">\n'
accordion_html += '        <div style="font-size:0.7em;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--dim);margin-bottom:16px;padding-bottom:8px;border-bottom:1px solid var(--border)">ADVANCED CONFIGURATION</div>\n'

for title, icon, tab_id, desc in SETTINGS_SECTIONS:
    section_id = f'settingsAccordion_{tab_id}'
    accordion_html += f"""
      <div class="panel" style="margin-bottom:8px">
        <div class="panel-header" onclick="toggleSettingsPanel('{section_id}')" style="cursor:pointer;display:flex;align-items:center;justify-content:space-between">
          <div class="panel-title" style="font-size:0.88em">{icon} {title}</div>
          <div id="{section_id}_chevron" style="color:var(--dim);font-size:0.8em;transition:transform 0.2s">▼</div>
        </div>
        <div style="font-size:0.75em;color:var(--muted);margin-bottom:12px">{desc}</div>
        <div id="{section_id}" style="display:none">
          <div style="background:var(--bg);border-radius:8px;padding:16px;border:1px solid var(--border)">
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px">
              <span style="font-size:1.5em">{icon}</span>
              <div>
                <div style="font-weight:700;font-size:0.9em">{title}</div>
                <div style="font-size:0.72em;color:var(--muted)">{desc}</div>
              </div>
            </div>
            <button class="btn" onclick="switchTab('{tab_id}');document.getElementById('{section_id}').style.display='none'">
              Open {title} →
            </button>
          </div>
        </div>
      </div>
"""

accordion_html += '      </div>\n'

# Add the toggleSettingsPanel JS function
toggle_js = """
<script>
function toggleSettingsPanel(id) {
  var el = document.getElementById(id);
  var chevron = document.getElementById(id + '_chevron');
  if (!el) return;
  var open = el.style.display !== 'none';
  el.style.display = open ? 'none' : 'block';
  if (chevron) chevron.style.transform = open ? '' : 'rotate(180deg)';
}
</script>
"""

# Find settings tab pane and append accordion before closing div
settings_pane_start = c.find('<div class="tab-pane" id="tab-settings">')
if settings_pane_start != -1:
    # Find the closing </div> of this tab-pane
    # Count divs to find the matching close
    pos = settings_pane_start
    depth = 0
    pane_end = -1
    for i in range(settings_pane_start, min(len(c), settings_pane_start + 300000)):
        if c[i:i+4] == '<div':
            depth += 1
        elif c[i:i+6] == '</div>':
            depth -= 1
            if depth == 0:
                pane_end = i
                break
    print(f"Settings pane: {settings_pane_start} to {pane_end}")
    if pane_end != -1:
        c = c[:pane_end] + accordion_html + c[pane_end:]
        print("Injected settings accordion")
else:
    print("ERROR: Could not find settings tab pane")

# Add toggle JS before the LAST </body> (not inside JS strings)
last_body = c.rfind('</body>')
if last_body != -1:
    c = c[:last_body] + toggle_js + c[last_body:]

# ─────────────────────────────────────────────────────────
# STEP 4: Fix TAB_TITLES for any tabs we might have renamed
# ─────────────────────────────────────────────────────────
# (TAB_TITLES defines the topbar heading when you switch tabs)
# Tabs are already in the file so no change needed here

# ─────────────────────────────────────────────────────────
# VERIFY & SAVE
# ─────────────────────────────────────────────────────────
print(f"\nFinal size: {len(c):,} chars")
new_tab_count = len(re.findall(r'<div class="nav-item"[^>]*data-tab=', c[:c.find('</nav>', c.find('id="sidebarNav"'))]))
print(f"Sidebar tabs: {new_tab_count}")
print(f"Crypto Trading: {c.count('Crypto Trading')}")
print(f"function switchTab: {c.count('function switchTab')}")
print(f"nav-group-label: {c.count('nav-group-label')}")
print(f"Settings accordion panels: {c.count('settingsAccordion_')}")
print(f"BUSINESS ESSENTIALS (group label): {c.count('>BUSINESS ESSENTIALS<')}")

with open(SRC, 'w', encoding='utf-8') as f:
    f.write(c)
print(f"\nSaved.")
