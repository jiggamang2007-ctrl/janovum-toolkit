"""
Surgical fix: start fresh from VPS download, remove ONLY the crypto trading content.
Uses precise byte positions found by inspection.
"""
import re

SRC = r"C:\Users\jigga\OneDrive\Desktop\janovum company planing\Janovum_Platform_v3_vps_download.html"
OUT = r"C:\Users\jigga\OneDrive\Desktop\janovum company planing\Janovum_Platform_v3.html"

with open(SRC, encoding='utf-8', errors='ignore') as f:
    c = f.read()

print(f"Starting from VPS download: {len(c):,} chars")
print(f"switchTab before: {c.count('function switchTab')}")

# ── 1. Remove sidebar nav item for crypto ──────────────────────────────
c = re.sub(
    r'\s*<div class="nav-item" data-tab="crypto"[^>]*>.*?</div>',
    '',
    c,
    flags=re.DOTALL
)
print(f"After nav removal: Crypto Trading={c.count('Crypto Trading')}, switchTab={c.count('function switchTab')}")

# ── 2. Remove crypto tab pane ──────────────────────────────────────────
# Find the crypto section comment
crypto_section = c.find('<!-- ??? CRYPTO TRADING TAB')
if crypto_section == -1:
    crypto_section = c.find('<!-- CRYPTO TRADING TAB')
if crypto_section == -1:
    crypto_section = c.find('<div class="tab-pane" id="tab-crypto">')

print(f"Crypto tab pane at: {crypto_section}")

if crypto_section != -1:
    # Find end: next tab-pane div
    next_pane = c.find('<div class="tab-pane"', crypto_section + 100)
    print(f"Next tab pane at: {next_pane}")
    if next_pane != -1:
        # Walk back to get any preceding whitespace
        start = crypto_section
        while start > 0 and c[start-1] in ' \t\n\r':
            start -= 1
        removed = c[start:next_pane]
        print(f"Removing {len(removed):,} chars of tab pane")
        c = c[:start] + c[next_pane:]

print(f"After tab pane removal: Crypto Trading={c.count('Crypto Trading')}, switchTab={c.count('function switchTab')}")

# ── 3. Remove crypto from TAB_TITLES registry ──────────────────────────
c = re.sub(
    r"\s*crypto:\s*\['Crypto Trading'[^\]]*\],?",
    '',
    c
)
print(f"After registry removal: Crypto Trading={c.count('Crypto Trading')}, switchTab={c.count('function switchTab')}")

# ── 4. SURGICALLY remove ONLY the crypto JS section ─────────────────────
# The crypto JS section has a specific block comment: // ??? CRYPTO TRADING TAB
# Find it precisely
ct_js_comment = c.find('// CRYPTO TRADING TAB')
if ct_js_comment == -1:
    # Try finding the variable declarations specific to crypto trading
    ct_js_comment = c.find('let ctRefreshInterval')

print(f"Crypto JS at: {ct_js_comment}")

if ct_js_comment != -1:
    # Walk back to find the start of the comment block (including preceding ??? line)
    line_start = c.rfind('\n', 0, ct_js_comment)
    prev_line_start = c.rfind('\n', 0, line_start)
    prev_line = c[prev_line_start:line_start]

    if '???' in prev_line or '//' in prev_line:
        block_start = prev_line_start
    else:
        block_start = line_start

    # Find the END precisely: look for 'function switchTab' which comes AFTER crypto
    switch_tab_pos = c.find('function switchTab', ct_js_comment)

    if switch_tab_pos != -1:
        # Find the line before switchTab to be the end boundary
        end_boundary = c.rfind('\n', 0, switch_tab_pos)
        # Also look for preceding comment before switchTab
        prev_line_start2 = c.rfind('\n', 0, end_boundary)
        prev_line2 = c[prev_line_start2:end_boundary]
        if '//' in prev_line2 or '???' in prev_line2:
            end_boundary = prev_line_start2

        removed = c[block_start:end_boundary]
        print(f"Removing {len(removed):,} chars of crypto JS (up to switchTab)")
        print(f"  Block start text: {repr(removed[:80])}")
        print(f"  Block end text: {repr(removed[-80:])}")
        c = c[:block_start] + c[end_boundary:]
    else:
        print("WARNING: switchTab not found after crypto JS — using fallback end detection")
        # Fallback: find next major function or section
        end_markers = ['function refreshCurrentTab', 'function loadClientBanner', '\n// ===']
        end_pos = -1
        for em in end_markers:
            pos = c.find(em, ct_js_comment + 100)
            if pos != -1:
                end_pos = pos
                break
        if end_pos != -1:
            end_boundary = c.rfind('\n', 0, end_pos)
            c = c[:block_start] + c[end_boundary:]
            print(f"  Used fallback end at {end_pos}")

print(f"After crypto JS removal: Crypto Trading={c.count('Crypto Trading')}, switchTab={c.count('function switchTab')}")

# ── Verify ────────────────────────────────────────────────────────────────
print(f"\nFinal size: {len(c):,} chars")
print(f"Crypto Trading remaining: {c.count('Crypto Trading')}")
print(f"function switchTab: {c.count('function switchTab')}")
print(f"function tkLoginAs: {c.count('function tkLoginAs')}")
print(f"function enterGuest: {c.count('function enterGuest')}")
print(f"Referral: {c.count('Referral')}")
print(f"plan-card: {c.count('plan-card')}")
print(f"Deploy New Client: {c.count('Deploy New Client')}")
print(f"BUSINESS ESSENTIALS: {c.count('BUSINESS ESSENTIALS')}")
print(f"data-tab='crypto': {c.count('data-tab=\"crypto\"')}")

required = {
    'Crypto Trading': 0,
    'function switchTab': 1,
    'Referral': 4,
    'plan-card': 9,
    'Deploy New Client': 1,
    'BUSINESS ESSENTIALS': 1,
}

all_ok = True
for key, expected_count in required.items():
    actual = c.count(key)
    if expected_count == 0:
        ok = actual == 0
    else:
        ok = actual >= expected_count
    status = 'OK' if ok else 'FAIL'
    if not ok:
        all_ok = False
    print(f"  {status} {key}: {actual} (expected {'0' if expected_count==0 else '>= '+str(expected_count)})")

if all_ok:
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write(c)
    print(f"\nSaved to {OUT}")
else:
    print("\nFAILED - not saving")
