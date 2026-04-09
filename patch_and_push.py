#!/usr/bin/env python3
"""Patch local Janovum_Platform_v3.html and push to VPS."""

import subprocess

LOCAL = r'C:\Users\jigga\OneDrive\Desktop\janovum company planing\Janovum_Platform_v3.html'
VPS_PATH = '/root/janovum-toolkit/Janovum_Platform_v3.html'

with open(LOCAL, 'r', encoding='utf-8') as f:
    html = f.read()

applied = []

def patch(name, old, new):
    global html
    if old in html:
        html = html.replace(old, new)
        applied.append(f'OK: {name}')
    else:
        applied.append(f'SKIP (already applied?): {name}')

# ── 1. let → var for _toolsDetailCache (fixes TDZ error) ──────────────────
patch('_toolsDetailCache let→var',
    'let _toolsDetailCache = null;',
    'var _toolsDetailCache = null;')

# ── 2. checkTkSession: show login form, auto-login from localStorage ────────
patch('checkTkSession login form',
    '''(function checkTkSession() {
  const saved = localStorage.getItem('janovum_tk_user');
  if (saved) {
    // Admin auto-login
    if (saved === ADMIN_USER) {
      tkLoginAs(saved, { displayName: 'Jaden', role: 'admin' });
      return;
    }
    const accounts = getTkAccounts();
    if (accounts[saved]) {''',
    '''(function checkTkSession() {
  const saved = localStorage.getItem('janovum_tk_user');
  if (saved) {
    if (saved === ADMIN_USER) {
      tkLoginAs(saved, { displayName: 'Jaden', role: 'admin' });
      return;
    }
    const accounts = getTkAccounts();
    if (accounts[saved]) {''')

# ── 3. tkLoginAs: set janovum_user as admin so trial system works ──────────
patch('tkLoginAs sets janovum_user',
    "  localStorage.setItem('janovum_tk_user', username);\n  document.getElementById('authScreen').classList.add('hidden');",
    "  localStorage.setItem('janovum_tk_user', username);\n  if (username === 'jaden') {\n    localStorage.setItem('janovum_user', JSON.stringify({name:'Jaden',email:'jaden@janovum.com',role:'admin',plan:'paid'}));\n    localStorage.setItem('janovum_setup_complete','1');\n  }\n  document.getElementById('authScreen').classList.add('hidden');")

# ── 4. Nav: prevent wrong-tab click after drag ─────────────────────────────
patch('nav drag _navDragActive',
    '''// Desktop sidebar clicks
document.querySelectorAll('.nav-item').forEach(item => {
  item.addEventListener('click', () => {
    const tab = item.dataset.tab;
    switchTab(tab);
  });
});''',
    '''// Desktop sidebar clicks — protected from drag interference
var _navDragActive = false;
document.querySelectorAll('.nav-item').forEach(item => {
  item.addEventListener('click', (e) => {
    if (_navDragActive) return;
    const tab = item.dataset.tab;
    if (tab) switchTab(tab);
  });
});''')

# ── 5. ondragend sets _navDragActive flag ──────────────────────────────────
patch('ondragend _navDragActive flag',
    '''    item.ondragend = function() {
      item.classList.remove('drag-ghost');
      document.querySelectorAll('.drag-target,.drag-hover,.drag-over-group').forEach(el => el.classList.remove('drag-target','drag-hover','drag-over-group'));
      dragTab = null;
    };''',
    '''    item.ondragend = function() {
      item.classList.remove('drag-ghost');
      document.querySelectorAll('.drag-target,.drag-hover,.drag-over-group').forEach(el => el.classList.remove('drag-target','drag-hover','drag-over-group'));
      dragTab = null;
      _navDragActive = true;
      setTimeout(() => { _navDragActive = false; }, 150);
    };''')

# ── 6. Nav cursor: grab → pointer ─────────────────────────────────────────
patch('nav cursor pointer',
    'cursor: grab;',
    'cursor: pointer;')

print('\n'.join(applied))

# Write patched file to temp location
TEMP = r'C:\Users\jigga\OneDrive\Desktop\janovum company planing\_patched_v3.html'
with open(TEMP, 'w', encoding='utf-8') as f:
    f.write(html)
print(f'\nPatched file: {len(html)} bytes')

# SCP to VPS
result = subprocess.run(
    ['scp', '-o', 'StrictHostKeyChecking=no', TEMP, f'root@104.238.133.244:{VPS_PATH}'],
    capture_output=True, text=True
)
if result.returncode == 0:
    print('Pushed to VPS successfully.')
else:
    print('SCP error:', result.stderr)
