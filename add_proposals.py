content = open('/root/janovum-toolkit/platform/server_v2.py').read()

PROPOSAL_ROUTES = r'''
# ══════════════════════════════════════════════════════════════
# PROPOSALS & CONTRACTS
# ══════════════════════════════════════════════════════════════

import uuid as _uuid
from datetime import datetime as _dt

PROPOSALS_FILE = os.path.join(PLATFORM_DIR, 'data', 'proposals.json')

def _load_proposals():
    if os.path.exists(PROPOSALS_FILE):
        with open(PROPOSALS_FILE) as f:
            return json.load(f)
    return {}

def _save_proposals(data):
    with open(PROPOSALS_FILE, 'w') as f:
        json.dump(data, f, indent=2)

@app.route('/api/proposals', methods=['GET'])
def list_proposals():
    props = _load_proposals()
    result = []
    for pid, p in props.items():
        result.append({
            'id': pid,
            'client_name': p.get('client_name', ''),
            'business_name': p.get('business_name', ''),
            'status': p.get('status', 'draft'),
            'total': p.get('total', 0),
            'created_at': p.get('created_at', ''),
            'signed_at': p.get('signed_at', ''),
            'viewed_at': p.get('viewed_at', ''),
        })
    result.sort(key=lambda x: x['created_at'], reverse=True)
    return jsonify(result)

@app.route('/api/proposals/generate', methods=['POST'])
def generate_proposal():
    data = request.json or {}
    business_name = data.get('business_name', '')
    business_type = data.get('business_type', '')
    contact_name = data.get('contact_name', '')
    contact_email = data.get('contact_email', '')
    contact_phone = data.get('contact_phone', '')
    services = data.get('services', [])
    notes = data.get('notes', '')
    setup_fee = data.get('setup_fee', 1000)
    monthly_fee = data.get('monthly_fee', 500)

    pid = str(_uuid.uuid4())[:8]
    now = _dt.utcnow().isoformat()

    # Build proposal content
    services_list = services if services else ['AI Receptionist', 'Appointment Booking', '24/7 Call Handling']

    proposal = {
        'id': pid,
        'client_name': contact_name,
        'business_name': business_name,
        'business_type': business_type,
        'contact_email': contact_email,
        'contact_phone': contact_phone,
        'services': services_list,
        'setup_fee': setup_fee,
        'monthly_fee': monthly_fee,
        'total': setup_fee + monthly_fee,
        'notes': notes,
        'status': 'draft',
        'created_at': now,
        'viewed_at': None,
        'signed_at': None,
        'signed_by': None,
        'signature_data': None,
        'valid_days': 30,
    }

    props = _load_proposals()
    props[pid] = proposal
    _save_proposals(props)

    return jsonify({'id': pid, 'status': 'ok'})

@app.route('/api/proposals/<pid>', methods=['GET'])
def get_proposal(pid):
    props = _load_proposals()
    p = props.get(pid)
    if not p:
        return jsonify({'error': 'Not found'}), 404
    return jsonify(p)

@app.route('/api/proposals/<pid>', methods=['POST'])
def update_proposal(pid):
    data = request.json or {}
    props = _load_proposals()
    if pid not in props:
        return jsonify({'error': 'Not found'}), 404
    props[pid].update(data)
    _save_proposals(props)
    return jsonify({'status': 'ok'})

@app.route('/api/proposals/<pid>/delete', methods=['POST'])
def delete_proposal(pid):
    props = _load_proposals()
    if pid in props:
        del props[pid]
        _save_proposals(props)
    return jsonify({'status': 'ok'})

@app.route('/proposal/<pid>')
def view_proposal(pid):
    from flask import Response
    props = _load_proposals()
    p = props.get(pid)
    if not p:
        return '<h2 style="font-family:sans-serif;padding:40px;color:#fff;background:#0a0a0a">Proposal not found</h2>', 404
    # Mark as viewed
    if not p.get('viewed_at'):
        p['viewed_at'] = _dt.utcnow().isoformat()
        _save_proposals(props)
    template = open(os.path.join(PLATFORM_DIR, 'templates', 'proposal.html')).read()
    template = template.replace('{{PROPOSAL_ID}}', pid)
    resp = Response(template, mimetype='text/html')
    resp.headers['Cache-Control'] = 'no-store'
    return resp

@app.route('/api/proposals/<pid>/sign', methods=['POST'])
def sign_proposal(pid):
    data = request.json or {}
    props = _load_proposals()
    if pid not in props:
        return jsonify({'error': 'Not found'}), 404
    props[pid]['status'] = 'signed'
    props[pid]['signed_at'] = _dt.utcnow().isoformat()
    props[pid]['signed_by'] = data.get('signed_by', '')
    props[pid]['signature_data'] = data.get('signature', '')
    _save_proposals(props)
    return jsonify({'status': 'ok'})

'''

marker = '# ══════════════════════════════════════════════════════════════\n# REFERRAL PROGRAM'
if marker in content:
    content = content.replace(marker, PROPOSAL_ROUTES + marker)
    open('/root/janovum-toolkit/platform/server_v2.py', 'w').write(content)
    print('Proposal routes added, size:', len(content))
else:
    print('ERROR: marker not found')
