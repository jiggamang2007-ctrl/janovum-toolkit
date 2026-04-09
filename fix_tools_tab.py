#!/usr/bin/env python3
"""Fix loadToolsTab in Janovum_Platform_v3.html on VPS — lazy-load rewrite."""

HTML_PATH = '/root/janovum-toolkit/Janovum_Platform_v3.html'

with open(HTML_PATH, 'r', encoding='utf-8') as f:
    html = f.read()

OLD_START = 'async function loadToolsTab() {'
END_MARKER = '\nfunction testTool('

if OLD_START not in html:
    print("ERROR: loadToolsTab not found")
    exit(1)

start = html.index(OLD_START)
end_pos = html.index(END_MARKER, start)
print(f"Replacing loadToolsTab at lines {html[:start].count(chr(10))+1} to {html[:end_pos].count(chr(10))+1}")

# Build new JS without any problematic Python/JS quoting conflicts
# Uses data-* attributes to avoid passing strings in onclick
lines = [
    "async function loadToolsTab() {",
    "  var stats = document.getElementById('toolStats');",
    "  var cats = document.getElementById('toolCategories');",
    "  try {",
    "    var sumRes = await fetch(API + '/api/tools');",
    "    var detRes = await fetch(API + '/api/tools/detailed');",
    "    if (!sumRes.ok || !detRes.ok) throw new Error('API ' + sumRes.status);",
    "    var summary = await sumRes.json();",
    "    var detailed = await detRes.json();",
    "    _toolsDetailCache = detailed;",
    "    var totalCats = Object.keys(detailed).length;",
    "    var totalTools = summary.total_tools || Object.values(detailed).reduce(function(s,a){return s+a.length;},0);",
    "    stats.innerHTML = '<div class=\"stat-card\"><div class=\"stat-label\">Total Tools</div><div class=\"stat-value blue\">' + totalTools + '</div></div>'",
    "      + '<div class=\"stat-card\"><div class=\"stat-label\">Categories</div><div class=\"stat-value purple\">' + totalCats + '</div></div>'",
    "      + '<div class=\"stat-card\"><div class=\"stat-label\">Pre-Built Workflows</div><div class=\"stat-value green\">' + totalTools + '</div><div class=\"stat-sub\">Every tool has a workflow</div></div>'",
    "      + '<div class=\"stat-card\"><div class=\"stat-label\">Status</div><div class=\"stat-value gold\">Ready</div><div class=\"stat-sub\">All tools loaded</div></div>';",
    "    var sorted = Object.entries(detailed).sort(function(a,b){return b[1].length-a[1].length;});",
    "    var catHtml = '';",
    "    for (var i = 0; i < sorted.length; i++) {",
    "      var cat = sorted[i][0];",
    "      var catTools = sorted[i][1];",
    "      var safeKey = 'tc' + i;",
    "      catHtml += '<div class=\"panel\" style=\"margin-bottom:10px\">'",
    "        + '<div style=\"display:flex;align-items:center;justify-content:space-between;cursor:pointer;padding:4px 0\"'",
    "        + ' data-cat=\"' + safeKey + '\" onclick=\"_expandToolCat(this.dataset.cat)\">'",
    "        + '<div style=\"display:flex;align-items:center;gap:10px\">'",
    "        + '<span style=\"color:var(--gold);font-weight:700;font-size:0.85em\">' + esc(cat) + '</span>'",
    "        + '<span style=\"background:var(--gold);color:#000;font-size:0.65em;font-weight:800;padding:2px 8px;border-radius:4px\">' + catTools.length + '</span>'",
    "        + '</div>'",
    "        + '<span style=\"color:var(--dim);font-size:0.8em\" id=\"arrow_' + safeKey + '\">&#9654;</span>'",
    "        + '</div>'",
    "        + '<div id=\"cat_' + safeKey + '\" style=\"display:none;margin-top:10px;padding-top:10px;border-top:1px solid var(--border)\"></div>'",
    "        + '</div>';",
    "    }",
    "    cats.innerHTML = catHtml;",
    "    _toolsCatData = {};",
    "    for (var j = 0; j < sorted.length; j++) {",
    "      _toolsCatData['tc' + j] = { name: sorted[j][0], tools: sorted[j][1] };",
    "    }",
    "  } catch(e) {",
    "    console.error('loadToolsTab error:', e);",
    "    if (stats) stats.innerHTML = '<div class=\"empty-state\"><p>Could not load tools. Error: ' + e.message + '</p></div>';",
    "  }",
    "}",
    "",
    "var _toolsCatData = {};",
    "var _toolsCatOpen = {};",
    "",
    "function _expandToolCat(safeKey) {",
    "  var el = document.getElementById('cat_' + safeKey);",
    "  var arrow = document.getElementById('arrow_' + safeKey);",
    "  if (!el) return;",
    "  if (_toolsCatOpen[safeKey]) {",
    "    el.style.display = 'none';",
    "    if (arrow) arrow.innerHTML = '&#9654;';",
    "    _toolsCatOpen[safeKey] = false;",
    "    return;",
    "  }",
    "  _toolsCatOpen[safeKey] = true;",
    "  el.style.display = 'block';",
    "  if (arrow) arrow.innerHTML = '&#9660;';",
    "  if (el.dataset.rendered) return;",
    "  el.dataset.rendered = '1';",
    "  var catInfo = _toolsCatData[safeKey] || { name: '', tools: [] };",
    "  var tools = catInfo.tools;",
    "  var html = '';",
    "  for (var i = 0; i < tools.length; i++) {",
    "    var t = tools[i];",
    "    var tid = safeKey + '_t' + i;",
    "    html += '<div id=\"' + tid + '\" style=\"background:#0a0a0a;border:1px solid var(--border);border-radius:10px;padding:14px 16px;margin-bottom:8px;cursor:pointer\"'",
    "      + ' data-tid=\"' + tid + '\" onclick=\"_toggleToolDetail(this.dataset.tid)\">'",
    "      + '<div style=\"display:flex;align-items:center;justify-content:space-between\">'",
    "      + '<div><span style=\"font-family:monospace;font-size:0.85em;font-weight:700;color:var(--green)\">' + esc(t.name) + '</span>'",
    "      + '<div style=\"font-size:0.75em;color:var(--muted);margin-top:3px\">' + esc(t.description) + '</div></div>'",
    "      + '<span style=\"font-size:0.68em;color:var(--dim);white-space:nowrap;margin-left:10px\">' + t.params.length + ' params &#9660;</span>'",
    "      + '</div>'",
    "      + '<div id=\"' + tid + '_detail\" style=\"display:none;margin-top:12px;padding-top:12px;border-top:1px solid #1a1a1a\">'",
    "      + '<div style=\"font-size:0.72em;color:var(--blue);font-weight:700;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px\">Parameters</div>'",
    "      + '<table style=\"width:100%;border-collapse:collapse;font-size:0.78em\"><thead><tr style=\"border-bottom:1px solid #2a2a2a\">'",
    "      + '<th style=\"text-align:left;padding:6px;color:var(--muted)\">Name</th>'",
    "      + '<th style=\"text-align:left;padding:6px;color:var(--muted)\">Type</th>'",
    "      + '<th style=\"text-align:left;padding:6px;color:var(--muted)\">Required</th>'",
    "      + '<th style=\"text-align:left;padding:6px;color:var(--muted)\">Description</th>'",
    "      + '</tr></thead><tbody>';",
    "    for (var p = 0; p < t.params.length; p++) {",
    "      var pm = t.params[p];",
    "      var reqCell = pm.required ? '<span style=\"color:var(--red);font-weight:700\">Required</span>' : '<span style=\"color:var(--dim)\">Optional</span>';",
    "      var defCell = (pm.default !== undefined && pm.default !== null) ? ' <span style=\"color:var(--dim)\">(default: ' + esc(String(pm.default)) + ')</span>' : '';",
    "      html += '<tr style=\"border-bottom:1px solid #1a1a1a\">'",
    "        + '<td style=\"padding:6px;font-family:monospace;color:var(--green);font-weight:600\">' + esc(pm.name) + '</td>'",
    "        + '<td style=\"padding:6px;color:var(--purple)\">' + esc(pm.type) + '</td>'",
    "        + '<td style=\"padding:6px\">' + reqCell + '</td>'",
    "        + '<td style=\"padding:6px;color:var(--muted)\">' + esc(pm.description) + defCell + '</td>'",
    "        + '</tr>';",
    "    }",
    "    html += '</tbody></table>'",
    "      + '<div style=\"margin-top:12px;display:flex;gap:8px\">'",
    "      + '<button class=\"btn-sm btn-green\" data-tname=\"' + esc(t.name) + '\" onclick=\"event.stopPropagation();testTool(this.dataset.tname)\">Test Tool</button>'",
    "      + '<button class=\"btn-sm btn-outline\" data-tname=\"' + esc(t.name) + '\" onclick=\"event.stopPropagation();copyToolName(this.dataset.tname)\">Copy Name</button>'",
    "      + '</div></div></div>';",
    "  }",
    "  el.innerHTML = html;",
    "}",
    "",
    "function _toggleToolDetail(tid) {",
    "  var d = document.getElementById(tid + '_detail');",
    "  if (d) d.style.display = d.style.display === 'none' ? 'block' : 'none';",
    "}",
]

NEW_FUNC = '\n'.join(lines)

html_new = html[:start] + NEW_FUNC + html[end_pos:]

with open(HTML_PATH, 'w', encoding='utf-8') as f:
    f.write(html_new)

print("Done! loadToolsTab replaced with lazy-load version (data-* attributes).")
print(f"New file size: {len(html_new)} bytes")

# Quick sanity check
assert '_expandToolCat' in html_new
assert 'loadToolsTab' in html_new
assert 'testTool' in html_new
print("Sanity checks passed.")
