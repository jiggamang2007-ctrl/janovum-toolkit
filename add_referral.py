import json, os, random, string

content = open('/root/janovum-toolkit/platform/server_v2.py').read()

REFERRAL_ROUTES = r'''
# ══════════════════════════════════════════════════════════════
# REFERRAL PROGRAM
# ══════════════════════════════════════════════════════════════

REFERRAL_FILE = os.path.join(PLATFORM_DIR, 'data', 'referrals.json')

def _load_referrals():
    if os.path.exists(REFERRAL_FILE):
        with open(REFERRAL_FILE) as f:
            return json.load(f)
    return {}

def _save_referrals(data):
    with open(REFERRAL_FILE, 'w') as f:
        json.dump(data, f, indent=2)

@app.route('/refer/<code>')
def referral_redirect(code):
    from flask import redirect
    refs = _load_referrals()
    # Find which client owns this code
    for client_id, info in refs.items():
        if info.get('code') == code:
            # Track the click
            info['clicks'] = info.get('clicks', 0) + 1
            from datetime import datetime
            info.setdefault('click_log', []).append(datetime.utcnow().isoformat())
            _save_referrals(refs)
            break
    # Redirect to main site with referral param
    return redirect('https://janovum.com/?ref=' + code, code=302)

@app.route('/api/referral/generate', methods=['POST'])
def referral_generate():
    data = request.json or {}
    client_id = data.get('client_id', '')
    if not client_id:
        return jsonify({'error': 'client_id required'}), 400
    refs = _load_referrals()
    # Return existing code if already has one
    if client_id in refs and refs[client_id].get('code'):
        return jsonify({'code': refs[client_id]['code'], 'existing': True})
    # Generate new code
    import random, string
    code = client_id[:4].lower() + ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    refs[client_id] = {
        'code': code,
        'client_id': client_id,
        'clicks': 0,
        'conversions': 0,
        'earnings': 0,
        'reward_per_conversion': data.get('reward', 100),
        'click_log': [],
        'conversions_log': [],
        'created_at': __import__('datetime').datetime.utcnow().isoformat()
    }
    _save_referrals(refs)
    return jsonify({'code': code, 'existing': False})

@app.route('/api/referral/stats/<client_id>')
def referral_stats(client_id):
    refs = _load_referrals()
    info = refs.get(client_id)
    if not info:
        return jsonify({'code': None, 'clicks': 0, 'conversions': 0, 'earnings': 0})
    origin = request.host_url.rstrip('/')
    return jsonify({
        'code': info.get('code'),
        'url': 'https://janovum.com/refer/' + info.get('code', ''),
        'clicks': info.get('clicks', 0),
        'conversions': info.get('conversions', 0),
        'earnings': info.get('earnings', 0),
        'reward_per_conversion': info.get('reward_per_conversion', 100),
        'click_log': info.get('click_log', [])[-10:],
    })

@app.route('/api/referral/all')
def referral_all():
    refs = _load_referrals()
    result = []
    for client_id, info in refs.items():
        result.append({
            'client_id': client_id,
            'code': info.get('code'),
            'url': 'https://janovum.com/refer/' + info.get('code', ''),
            'clicks': info.get('clicks', 0),
            'conversions': info.get('conversions', 0),
            'earnings': info.get('earnings', 0),
        })
    return jsonify(result)

@app.route('/api/referral/convert', methods=['POST'])
def referral_convert():
    data = request.json or {}
    code = data.get('code', '')
    refs = _load_referrals()
    for client_id, info in refs.items():
        if info.get('code') == code:
            info['conversions'] = info.get('conversions', 0) + 1
            info['earnings'] = info.get('earnings', 0) + info.get('reward_per_conversion', 100)
            from datetime import datetime
            info.setdefault('conversions_log', []).append(datetime.utcnow().isoformat())
            _save_referrals(refs)
            return jsonify({'status': 'ok', 'client_id': client_id, 'earnings': info['earnings']})
    return jsonify({'error': 'Code not found'}), 404

@app.route('/api/referral/set-reward', methods=['POST'])
def referral_set_reward():
    data = request.json or {}
    client_id = data.get('client_id', '')
    reward = data.get('reward', 100)
    refs = _load_referrals()
    if client_id in refs:
        refs[client_id]['reward_per_conversion'] = reward
        _save_referrals(refs)
        return jsonify({'status': 'ok'})
    return jsonify({'error': 'Client not found'}), 404

'''

marker = '# ══════════════════════════════════════════════════════════════\n# CLIENT PORTAL'
if marker in content:
    content = content.replace(marker, REFERRAL_ROUTES + marker)
    open('/root/janovum-toolkit/platform/server_v2.py', 'w').write(content)
    print('Referral routes added, size:', len(content))
else:
    print('ERROR: marker not found')
