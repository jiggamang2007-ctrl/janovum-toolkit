content = open('/root/janovum-toolkit/Janovum_Platform_v3.html').read()

# 1. Add Crypto Trader to AI_EMPLOYEES
old_last_emp = "{id:'travel_agent',cat:'industry',icon:'&#9992;',name:'AI Travel Agent',desc:'Trip planning, flight/hotel search, itineraries, budget optimization',tags:['travel','booking'],fields:[{k:'business_name',l:'Business Name',r:true},{k:'specialization',l:'Specialization (luxury, budget, adventure)'}]},"

new_last_emp = old_last_emp + """
  // Trading
  {id:'crypto_trader',cat:'trading',icon:'&#9670;',name:'AI Crypto Trader',desc:'AI-powered memecoin trading on Solana. Smart entries, rug protection, auto profit-taking. Uses the S1 pump.fun retrace strategy — finds coins that pumped and crashed but still have active trading.',tags:['crypto','trading','solana','memecoin'],type:'launcher',launcher_tab:'crypto',fields:[]},"""

if old_last_emp in content:
    content = content.replace(old_last_emp, new_last_emp)
    print('Crypto trader added to AI_EMPLOYEES')
else:
    print('ERROR: travel_agent entry not found')

# 2. Add 'trading' to the employee category filter buttons
old_cat_btns = "filterEmployeesCat('executive')\">Executive</button>"
new_cat_btns = "filterEmployeesCat('executive')\">Executive</button>\n          <button class=\"emp-cat-btn\" onclick=\"filterEmployeesCat('trading')\">&#9670; Trading</button>"

if old_cat_btns in content:
    content = content.replace(old_cat_btns, new_cat_btns)
    print('Trading category button added')
else:
    print('WARNING: executive cat button not found, skipping')

# 3. Patch the employee card render to handle 'launcher' type
old_footer = """      <div class="market-footer">
        <span class="market-price">${e.fields.length} config fields</span>
        <button class="btn-sm btn-green" onclick="openEmpSetup('${e.id}')">Deploy</button>
      </div>"""

new_footer = """      <div class="market-footer">
        ${e.type === 'launcher'
          ? '<span class="market-price" style="color:var(--purple)">&#9670; Specialized Module</span><button class="btn-sm" style="background:linear-gradient(135deg,#9333ea,#ec4899);border:none;color:#fff" onclick="switchTab(\\'' + e.launcher_tab + '\\')">Launch</button>'
          : '<span class="market-price">' + e.fields.length + ' config fields</span><button class="btn-sm btn-green" onclick="openEmpSetup(\\'' + e.id + '\\')">Deploy</button>'
        }
      </div>"""

if old_footer in content:
    content = content.replace(old_footer, new_footer)
    print('Render footer patched for launcher type')
else:
    # The template literal might be formatted differently, search for just the button part
    old_btn = "        <button class=\"btn-sm btn-green\" onclick=\"openEmpSetup('${e.id}')\">Deploy</button>"
    new_btn = "        ${e.type === 'launcher' ? '<button class=\"btn-sm\" style=\"background:linear-gradient(135deg,#9333ea,#ec4899);border:none;color:#fff\" onclick=\"switchTab(\\'' + e.launcher_tab + '\\')\">' + '&#9670; Launch</button>' : '<button class=\"btn-sm btn-green\" onclick=\"openEmpSetup(\\'' + e.id + '\\')\">Deploy</button>'}"
    if old_btn in content:
        content = content.replace(old_btn, new_btn)
        print('Footer button patched (alt)')
    else:
        print('WARNING: footer button not found')

# 4. Also add trading category to filterEmployeesCat so cards show
old_cat_filter = "cards.forEach(c => c.style.display = (cat === 'all' || c.dataset.cat === cat) ? '' : 'none');"
# This is fine as-is since it uses data-cat attribute which we set in the employee object

open('/root/janovum-toolkit/Janovum_Platform_v3.html', 'w').write(content)
print('Done, size:', len(content))
