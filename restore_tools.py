#!/usr/bin/env python3
"""Restore original loadToolsTab on VPS, removing the broken lazy-load version."""

HTML_PATH = '/root/janovum-toolkit/Janovum_Platform_v3.html'

with open(HTML_PATH, 'r', encoding='utf-8') as f:
    html = f.read()

# Find start of current loadToolsTab (lazy-load version)
START_MARKER = 'async function loadToolsTab() {'
# Find end — stop right before function testTool
END_MARKER = '\nfunction testTool('

if START_MARKER not in html:
    print("ERROR: loadToolsTab not found"); exit(1)

start = html.index(START_MARKER)
end = html.index(END_MARKER, start)

# Also remove the helper functions we added (_toolsCatData, _toolsCatOpen, _expandToolCat, _toggleToolDetail)
# They come right after loadToolsTab and before testTool — already included in the slice

ORIGINAL = r'''var _toolsDetailCache = null;
async function loadToolsTab() {
  try {
    // Fetch both summary and detailed data
    const [sumRes, detRes] = await Promise.all([
      fetch(API + '/api/tools'),
      fetch(API + '/api/tools/detailed')
    ]);
    const summary = await sumRes.json();
    const detailed = await detRes.json();
    _toolsDetailCache = detailed;

    const stats = document.getElementById('toolStats');
    const totalCats = Object.keys(detailed).length;
    const totalTools = summary.total_tools || Object.values(detailed).reduce((s,arr)=>s+arr.length,0);
    stats.innerHTML = `
      <div class="stat-card"><div class="stat-label">Total Tools</div><div class="stat-value blue">${totalTools}</div></div>
      <div class="stat-card"><div class="stat-label">Categories</div><div class="stat-value purple">${totalCats}</div></div>
      <div class="stat-card"><div class="stat-label">Pre-Built Workflows</div><div class="stat-value green">${totalTools}</div><div class="stat-sub">Every tool has a workflow</div></div>
      <div class="stat-card"><div class="stat-label">Status</div><div class="stat-value gold">Ready</div><div class="stat-sub">All tools loaded</div></div>
    `;

    const cats = document.getElementById('toolCategories');
    cats.innerHTML = Object.entries(detailed).sort((a,b)=>b[1].length-a[1].length).map(([cat, tools]) => `
      <div class="panel" style="margin-bottom:10px">
        <div style="display:flex;align-items:center;justify-content:space-between;cursor:pointer;padding:4px 0" onclick="this.nextElementSibling.style.display=this.nextElementSibling.style.display==='none'?'block':'none'">
          <div style="display:flex;align-items:center;gap:10px">
            <span style="color:var(--gold);font-weight:700;font-size:0.85em">${esc(cat)}</span>
            <span style="background:var(--gold);color:#000;font-size:0.65em;font-weight:800;padding:2px 8px;border-radius:4px">${tools.length}</span>
          </div>
          <span style="color:var(--dim);font-size:0.8em;transition:transform 0.2s" id="arrow-${cat.replace(/[^a-zA-Z]/g,'')}">&#9654;</span>
        </div>
        <div style="display:none;margin-top:10px;padding-top:10px;border-top:1px solid var(--border)">
          ${tools.map(t => `
            <div style="background:#0a0a0a;border:1px solid var(--border);border-radius:10px;padding:14px 16px;margin-bottom:8px;cursor:pointer;transition:border-color 0.2s" onmouseover="this.style.borderColor='var(--gold)'" onmouseout="this.style.borderColor='var(--border)'" onclick="this.querySelector('.tool-workflow').style.display=this.querySelector('.tool-workflow').style.display==='none'?'block':'none'">
              <div style="display:flex;align-items:center;justify-content:space-between">
                <div>
                  <span style="font-family:monospace;font-size:0.85em;font-weight:700;color:var(--green)">${esc(t.name)}</span>
                  <div style="font-size:0.75em;color:var(--muted);margin-top:3px">${esc(t.description)}</div>
                </div>
                <span style="font-size:0.68em;color:var(--dim);white-space:nowrap;margin-left:10px">${t.params.length} params &#9660;</span>
              </div>
              <div class="tool-workflow" style="display:none;margin-top:12px;padding-top:12px;border-top:1px solid #1a1a1a">
                <!-- Workflow Map -->
                <div style="font-size:0.72em;color:var(--gold);font-weight:700;text-transform:uppercase;letter-spacing:1px;margin-bottom:10px">Workflow Map</div>
                <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-bottom:14px">
                  <div style="background:#111;border:1px solid var(--border);border-radius:6px;padding:6px 12px;font-size:0.72em">
                    <span style="color:var(--blue)">&#9654;</span> <span style="color:var(--muted)">Input</span>
                  </div>
                  <span style="color:var(--dim)">&#10230;</span>
                  ${t.params.filter(p=>p.required).map(p => `
                    <div style="background:#0d1a0d;border:1px solid #1a3a1a;border-radius:6px;padding:6px 12px;font-size:0.72em">
                      <span style="color:var(--green);font-weight:700">${esc(p.name)}</span>
                    </div>
                    <span style="color:var(--dim)">&#10230;</span>
                  `).join('')}
                  <div style="background:#111;border:1px solid var(--gold);border-radius:6px;padding:6px 12px;font-size:0.72em">
                    <span style="color:var(--gold)">&#9881;</span> <span style="color:var(--gold);font-weight:700">${esc(t.name)}</span>
                  </div>
                  <span style="color:var(--dim)">&#10230;</span>
                  <div style="background:#111;border:1px solid var(--border);border-radius:6px;padding:6px 12px;font-size:0.72em">
                    <span style="color:var(--green)">&#9989;</span> <span style="color:var(--muted)">Result</span>
                  </div>
                </div>
                <!-- Parameters Table -->
                <div style="font-size:0.72em;color:var(--blue);font-weight:700;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px">Parameters</div>
                <table style="width:100%;border-collapse:collapse;font-size:0.78em">
                  <thead><tr style="border-bottom:1px solid #2a2a2a">
                    <th style="text-align:left;padding:6px;color:var(--muted);font-weight:600">Name</th>
                    <th style="text-align:left;padding:6px;color:var(--muted);font-weight:600">Type</th>
                    <th style="text-align:left;padding:6px;color:var(--muted);font-weight:600">Required</th>
                    <th style="text-align:left;padding:6px;color:var(--muted);font-weight:600">Description</th>
                  </tr></thead>
                  <tbody>${t.params.map(p => `
                    <tr style="border-bottom:1px solid #1a1a1a">
                      <td style="padding:6px;font-family:monospace;color:var(--green);font-weight:600">${esc(p.name)}</td>
                      <td style="padding:6px;color:var(--purple)">${esc(p.type)}</td>
                      <td style="padding:6px">${p.required ? '<span style="color:var(--red);font-weight:700">Required</span>' : '<span style="color:var(--dim)">Optional</span>'}</td>
                      <td style="padding:6px;color:var(--muted)">${esc(p.description)}${p.default !== undefined && p.default !== null ? ' <span style="color:var(--dim)">(default: '+esc(String(p.default))+')</span>' : ''}</td>
                    </tr>
                  `).join('')}</tbody>
                </table>
                <!-- Quick Test -->
                <div style="margin-top:12px;display:flex;gap:8px">
                  <button class="btn-sm btn-green" onclick="event.stopPropagation();testTool('${esc(t.name)}')">Test Tool</button>
                  <button class="btn-sm btn-outline" onclick="event.stopPropagation();copyToolName('${esc(t.name)}')">Copy Name</button>
                  <button class="btn-sm btn-outline" onclick="event.stopPropagation();addToolToWorkflow('${esc(t.name)}')">Add to Workflow</button>
                </div>
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    `).join('');
  } catch (e) {
    document.getElementById('toolStats').innerHTML = '<div class="empty-state"><p>Start the toolkit server to see tools</p></div>';
  }
}'''

# Also need to find the var _toolsDetailCache line before the function
# The current VPS has it starting at START_MARKER without the var line before
# Find where it starts (could have var _toolsDetailCache on the line before)
var_line = 'var _toolsDetailCache = null;\n'
if html[start - len(var_line):start] == var_line:
    start = start - len(var_line)

old_block = html[start:end]
print(f"Replacing {len(old_block)} chars ({old_block.count(chr(10))} lines)")

html_new = html[:start] + ORIGINAL + html[end:]

with open(HTML_PATH, 'w', encoding='utf-8') as f:
    f.write(html_new)

print(f"Done. New file: {len(html_new)} bytes")
assert 'Workflow Map' in html_new
assert 'tool-workflow' in html_new
assert 'var _toolsDetailCache' in html_new
print("Checks passed.")
