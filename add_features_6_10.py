"""
Add Features 6-10:
6. Appointment Reminders (auto-text/email day before)
7. Appointment Deposits (Stripe link on booking)
8. Pipeline / CRM (lead tracking)
9. Call Summaries (transcription + AI summary storage)
10. Onboarding Automation (auto-setup after proposal signed)
"""

content = open('/root/janovum-toolkit/platform/server_v2.py').read()

FEATURES_6_10 = r'''
# ══════════════════════════════════════════════════════════════
# FEATURE 6: APPOINTMENT REMINDERS
# ══════════════════════════════════════════════════════════════

REMINDER_CONFIG_FILE = os.path.join(PLATFORM_DIR, 'data', 'reminder_config.json')
REMINDER_LOG_FILE = os.path.join(PLATFORM_DIR, 'data', 'reminder_log.json')

def _load_reminder_cfg():
    if os.path.exists(REMINDER_CONFIG_FILE):
        with open(REMINDER_CONFIG_FILE) as f:
            return json.load(f)
    return {
        'enabled': False,
        'hours_before': 24,
        'sms_enabled': True,
        'sms_message': "Reminder: You have an appointment tomorrow at {time}. Reply CONFIRM to confirm or CANCEL to cancel. - {business}",
        'email_enabled': False,
        'email_subject': "Appointment Reminder — {time}",
    }

def _save_reminder_cfg(data):
    with open(REMINDER_CONFIG_FILE, 'w') as f:
        json.dump(data, f, indent=2)

@app.route('/api/reminders/config', methods=['GET'])
def get_reminder_config():
    return jsonify(_load_reminder_cfg())

@app.route('/api/reminders/config', methods=['POST'])
def save_reminder_config():
    cfg = _load_reminder_cfg()
    cfg.update(request.json or {})
    _save_reminder_cfg(cfg)
    return jsonify({'status': 'ok'})

@app.route('/api/reminders/send', methods=['POST'])
def send_appointment_reminder():
    """Send reminder for a specific appointment"""
    data = request.json or {}
    phone = data.get('phone', '')
    name = data.get('name', 'there')
    appt_time = data.get('time', '')
    client_id = data.get('client_id', '')
    business_name = data.get('business_name', 'us')
    if not phone:
        return jsonify({'error': 'phone required'}), 400
    cfg = _load_reminder_cfg()
    if not cfg.get('enabled'):
        return jsonify({'status': 'disabled'})
    message = cfg['sms_message'].replace('{time}', appt_time).replace('{name}', name).replace('{business}', business_name)
    tk_path = os.path.join(PLATFORM_DIR, 'data', 'toolkit_config.json')
    try:
        with open(tk_path) as f:
            tk = json.load(f)
        from_number = tk.get('twilio_phone_number', '')
        import requests as _rreq
        resp = _rreq.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{tk['twilio_account_sid']}/Messages.json",
            auth=(tk['twilio_account_sid'], tk['twilio_auth_token']),
            data={'From': from_number, 'To': phone, 'Body': message}
        )
        result = resp.json()
        # Log
        if os.path.exists(REMINDER_LOG_FILE):
            with open(REMINDER_LOG_FILE) as f:
                log = json.load(f)
        else:
            log = []
        log.append({
            'phone': phone, 'name': name, 'time': appt_time,
            'client_id': client_id,
            'sent_at': __import__('datetime').datetime.utcnow().isoformat(),
            'status': 'sent' if result.get('sid') else 'failed',
        })
        with open(REMINDER_LOG_FILE, 'w') as f:
            json.dump(log, f, indent=2)
        return jsonify({'status': 'ok', 'sid': result.get('sid')})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reminders/log', methods=['GET'])
def get_reminder_log():
    if os.path.exists(REMINDER_LOG_FILE):
        with open(REMINDER_LOG_FILE) as f:
            return jsonify(json.load(f)[-50:])
    return jsonify([])

@app.route('/api/reminders/run-check', methods=['POST'])
def reminders_run_check():
    """Check all upcoming appointments and send reminders for ones due"""
    import datetime as _rdt
    cfg = _load_reminder_cfg()
    if not cfg.get('enabled'):
        return jsonify({'status': 'disabled', 'sent': 0})
    hours_before = cfg.get('hours_before', 24)
    now = _rdt.datetime.utcnow()
    target_window_start = now + _rdt.timedelta(hours=hours_before - 0.5)
    target_window_end = now + _rdt.timedelta(hours=hours_before + 0.5)
    # Load all client appointments
    sent = 0
    clients_dir = os.path.join(PLATFORM_DIR, 'data', 'clients')
    if not os.path.exists(clients_dir):
        return jsonify({'status': 'ok', 'sent': 0})
    for fname in os.listdir(clients_dir):
        if not fname.endswith('_appointments.json'):
            continue
        client_id = fname.replace('_appointments.json', '')
        appt_path = os.path.join(clients_dir, fname)
        with open(appt_path) as f:
            appts = json.load(f)
        cfg_path2 = os.path.join(clients_dir, f'{client_id}.json')
        biz_name = client_id
        if os.path.exists(cfg_path2):
            with open(cfg_path2) as f2:
                biz_name = json.load(f2).get('business_name', client_id)
        for appt in appts:
            if appt.get('reminder_sent'):
                continue
            appt_dt_str = appt.get('date', '') + ' ' + appt.get('time', '')
            try:
                appt_dt = _rdt.datetime.strptime(appt_dt_str.strip(), '%Y-%m-%d %H:%M')
            except:
                continue
            if target_window_start <= appt_dt <= target_window_end:
                phone = appt.get('customer_phone', '')
                if phone:
                    import requests as _rreq2
                    r2 = _rreq2.post('http://localhost:5050/api/reminders/send', json={
                        'phone': phone,
                        'name': appt.get('customer_name', 'there'),
                        'time': appt.get('time', ''),
                        'client_id': client_id,
                        'business_name': biz_name,
                    })
                    if r2.json().get('status') == 'ok':
                        appt['reminder_sent'] = True
                        sent += 1
        with open(appt_path, 'w') as f:
            json.dump(appts, f, indent=2)
    return jsonify({'status': 'ok', 'sent': sent})

# ══════════════════════════════════════════════════════════════
# FEATURE 7: APPOINTMENT DEPOSITS
# ══════════════════════════════════════════════════════════════

@app.route('/api/deposits/config', methods=['GET', 'POST'])
def deposit_config():
    cfg_path = os.path.join(PLATFORM_DIR, 'data', 'deposit_config.json')
    if request.method == 'POST':
        data = request.json or {}
        with open(cfg_path, 'w') as f:
            json.dump(data, f, indent=2)
        return jsonify({'status': 'ok'})
    if os.path.exists(cfg_path):
        with open(cfg_path) as f:
            return jsonify(json.load(f))
    return jsonify({'enabled': False, 'amount': 50, 'label': 'Appointment Deposit'})

@app.route('/api/deposits/create-link', methods=['POST'])
def create_deposit_link():
    """Create a Stripe payment link for an appointment deposit"""
    data = request.json or {}
    amount = data.get('amount', 50)
    label = data.get('label', 'Appointment Deposit')
    customer_name = data.get('customer_name', '')
    appt_time = data.get('appt_time', '')
    sk = _get_stripe_key()
    if not sk:
        return jsonify({'error': 'Stripe key not configured. Add it in Settings.'}), 400
    try:
        import requests as _dreq
        price_resp = _dreq.post(
            'https://api.stripe.com/v1/prices',
            auth=(sk, ''),
            data={
                'unit_amount': int(float(amount) * 100),
                'currency': 'usd',
                'product_data[name]': f'{label} — {appt_time}' if appt_time else label,
            }
        )
        price_data = price_resp.json()
        if not price_data.get('id'):
            return jsonify({'error': 'Stripe price creation failed', 'detail': price_data}), 500
        link_resp = _dreq.post(
            'https://api.stripe.com/v1/payment_links',
            auth=(sk, ''),
            data={'line_items[0][price]': price_data['id'], 'line_items[0][quantity]': 1}
        )
        link_data = link_resp.json()
        if link_data.get('url'):
            return jsonify({'url': link_data['url'], 'amount': amount})
        return jsonify({'error': 'Failed to create payment link', 'detail': link_data}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ══════════════════════════════════════════════════════════════
# FEATURE 8: PIPELINE / CRM
# ══════════════════════════════════════════════════════════════

PIPELINE_FILE = os.path.join(PLATFORM_DIR, 'data', 'pipeline.json')

PIPELINE_STAGES = ['cold', 'contacted', 'demo', 'proposal', 'negotiation', 'signed', 'lost']

def _load_pipeline():
    if os.path.exists(PIPELINE_FILE):
        with open(PIPELINE_FILE) as f:
            return json.load(f)
    return {}

def _save_pipeline(data):
    with open(PIPELINE_FILE, 'w') as f:
        json.dump(data, f, indent=2)

@app.route('/api/pipeline', methods=['GET'])
def list_pipeline():
    pipe = _load_pipeline()
    result = list(pipe.values())
    result.sort(key=lambda x: x.get('updated_at', ''), reverse=True)
    return jsonify(result)

@app.route('/api/pipeline/add', methods=['POST'])
def add_pipeline_lead():
    data = request.json or {}
    import uuid as _uuid3
    from datetime import datetime as _dt4
    lid = str(_uuid3.uuid4())[:8]
    now = _dt4.utcnow().isoformat()
    lead = {
        'id': lid,
        'business_name': data.get('business_name', ''),
        'contact_name': data.get('contact_name', ''),
        'contact_email': data.get('contact_email', ''),
        'contact_phone': data.get('contact_phone', ''),
        'business_type': data.get('business_type', ''),
        'stage': data.get('stage', 'cold'),
        'value': float(data.get('value', 1500)),
        'notes': data.get('notes', ''),
        'source': data.get('source', 'manual'),
        'created_at': now,
        'updated_at': now,
        'activity': [{'action': 'Lead added', 'at': now}],
    }
    pipe = _load_pipeline()
    pipe[lid] = lead
    _save_pipeline(pipe)
    return jsonify(lead)

@app.route('/api/pipeline/<lid>/stage', methods=['POST'])
def update_pipeline_stage(lid):
    data = request.json or {}
    from datetime import datetime as _dt5
    pipe = _load_pipeline()
    if lid not in pipe:
        return jsonify({'error': 'Not found'}), 404
    old_stage = pipe[lid]['stage']
    new_stage = data.get('stage', old_stage)
    pipe[lid]['stage'] = new_stage
    pipe[lid]['updated_at'] = _dt5.utcnow().isoformat()
    pipe[lid]['activity'].append({'action': f'Moved from {old_stage} to {new_stage}', 'at': _dt5.utcnow().isoformat()})
    if data.get('note'):
        pipe[lid]['activity'].append({'action': data['note'], 'at': _dt5.utcnow().isoformat()})
    _save_pipeline(pipe)
    return jsonify({'status': 'ok'})

@app.route('/api/pipeline/<lid>/note', methods=['POST'])
def add_pipeline_note(lid):
    data = request.json or {}
    from datetime import datetime as _dt6
    pipe = _load_pipeline()
    if lid not in pipe:
        return jsonify({'error': 'Not found'}), 404
    pipe[lid]['activity'].append({'action': data.get('note', ''), 'at': _dt6.utcnow().isoformat()})
    pipe[lid]['updated_at'] = _dt6.utcnow().isoformat()
    if data.get('email'):
        pipe[lid]['contact_email'] = data['email']
    if data.get('phone'):
        pipe[lid]['contact_phone'] = data['phone']
    _save_pipeline(pipe)
    return jsonify({'status': 'ok'})

@app.route('/api/pipeline/<lid>/delete', methods=['POST'])
def delete_pipeline_lead(lid):
    pipe = _load_pipeline()
    if lid in pipe:
        del pipe[lid]
        _save_pipeline(pipe)
    return jsonify({'status': 'ok'})

# ══════════════════════════════════════════════════════════════
# FEATURE 9: CALL SUMMARIES
# ══════════════════════════════════════════════════════════════

CALL_SUMMARIES_FILE = os.path.join(PLATFORM_DIR, 'data', 'call_summaries.json')

def _load_call_summaries():
    if os.path.exists(CALL_SUMMARIES_FILE):
        with open(CALL_SUMMARIES_FILE) as f:
            return json.load(f)
    return []

@app.route('/api/call-summaries', methods=['GET'])
def list_call_summaries():
    summaries = _load_call_summaries()
    client_id = request.args.get('client_id')
    if client_id:
        summaries = [s for s in summaries if s.get('client_id') == client_id]
    return jsonify(summaries[-100:])

@app.route('/api/call-summaries/add', methods=['POST'])
def add_call_summary():
    """Called by receptionist after each call with transcript + summary"""
    data = request.json or {}
    import uuid as _uuid4
    from datetime import datetime as _dt7
    summary_id = str(_uuid4.uuid4())[:8]
    now = _dt7.utcnow().isoformat()
    # Generate AI summary from transcript if provided
    transcript = data.get('transcript', '')
    ai_summary = data.get('summary', '')
    if not ai_summary and transcript:
        # Simple rule-based summary extraction
        lines = transcript.strip().split('\n')
        caller_lines = [l for l in lines if l.lower().startswith('caller:')]
        ai_summary = f"Call with {len(caller_lines)} caller messages. " + (caller_lines[0].replace('Caller:', '').strip()[:100] if caller_lines else '')
    entry = {
        'id': summary_id,
        'client_id': data.get('client_id', ''),
        'caller_number': data.get('caller_number', ''),
        'caller_name': data.get('caller_name', 'Unknown'),
        'duration_seconds': data.get('duration_seconds', 0),
        'outcome': data.get('outcome', 'unknown'),  # booked, info_only, missed, transferred
        'summary': ai_summary,
        'transcript': transcript[:3000] if transcript else '',  # cap at 3000 chars
        'tags': data.get('tags', []),
        'created_at': now,
        'appointment_booked': data.get('appointment_booked', False),
    }
    summaries = _load_call_summaries()
    summaries.append(entry)
    # Keep last 500
    if len(summaries) > 500:
        summaries = summaries[-500:]
    with open(CALL_SUMMARIES_FILE, 'w') as f:
        json.dump(summaries, f, indent=2)
    return jsonify({'status': 'ok', 'id': summary_id})

@app.route('/api/call-summaries/<sid>/delete', methods=['POST'])
def delete_call_summary(sid):
    summaries = _load_call_summaries()
    summaries = [s for s in summaries if s['id'] != sid]
    with open(CALL_SUMMARIES_FILE, 'w') as f:
        json.dump(summaries, f, indent=2)
    return jsonify({'status': 'ok'})

# ══════════════════════════════════════════════════════════════
# FEATURE 10: ONBOARDING AUTOMATION
# ══════════════════════════════════════════════════════════════

@app.route('/api/onboarding/start', methods=['POST'])
def start_onboarding():
    """Auto-triggered after proposal is signed. Sets up client account and sends welcome."""
    data = request.json or {}
    proposal_id = data.get('proposal_id', '')
    # Load proposal
    props = _load_proposals()
    p = props.get(proposal_id)
    if not p:
        return jsonify({'error': 'Proposal not found'}), 404
    if p.get('status') != 'signed':
        return jsonify({'error': 'Proposal not yet signed'}), 400
    biz_name = p.get('business_name', '')
    contact_email = p.get('contact_email', '')
    contact_name = p.get('client_name', '')
    services = p.get('services', [])
    results = []
    # 1. Create invoice for setup fee + first month
    try:
        import requests as _oreq
        inv_resp = _oreq.post('http://localhost:5050/api/invoices/create', json={
            'client_name': contact_name,
            'client_email': contact_email,
            'description': f'Setup Fee + First Month — {biz_name}',
            'amount': p.get('total', 1500),
            'due_days': 3,
        })
        inv_data = inv_resp.json()
        results.append({'step': 'invoice_created', 'id': inv_data.get('id'), 'stripe_link': inv_data.get('stripe_link')})
    except Exception as e:
        results.append({'step': 'invoice_created', 'error': str(e)})
    # 2. Send welcome email
    if contact_email:
        try:
            import smtplib
            from email.mime.multipart import MIMEMultipart2
            from email.mime.text import MIMEText2
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText
            inv_link = results[0].get('stripe_link', '') if results else ''
            pay_section = f'<a href="{inv_link}" style="display:inline-block;background:#D4AF37;color:#000;padding:14px 28px;border-radius:8px;font-weight:700;text-decoration:none">Pay Setup Invoice</a>' if inv_link else ''
            services_html = ''.join(f'<li style="padding:4px 0;color:#aaa">{s}</li>' for s in services)
            body = f"""
            <div style="background:#0a0a0a;min-height:100vh;padding:40px 20px;font-family:sans-serif">
            <div style="max-width:540px;margin:0 auto;background:#111;border:1px solid #1e1e1e;border-radius:16px;overflow:hidden">
              <div style="background:linear-gradient(135deg,#1a1200,#0d0d0d);padding:32px;border-bottom:1px solid #1e1e1e">
                <div style="font-size:1.5em;font-weight:900;color:#D4AF37">Janovum<span style="color:#fff">.ai</span></div>
                <div style="color:#888;font-size:0.82em;margin-top:4px">Welcome to the team.</div>
              </div>
              <div style="padding:32px">
                <h2 style="color:#e8e8e8;margin-bottom:8px">You're in, {contact_name or biz_name}!</h2>
                <p style="color:#aaa;font-size:0.88em;line-height:1.8;margin-bottom:24px">
                  Your proposal has been signed and we're ready to get started. Here's what happens next:
                </p>
                <div style="background:#0d0d0d;border:1px solid #1e1e1e;border-radius:10px;padding:20px;margin-bottom:24px">
                  <div style="font-size:0.72em;text-transform:uppercase;letter-spacing:1px;color:#D4AF37;font-weight:700;margin-bottom:12px">Your Services</div>
                  <ul style="list-style:none;padding:0;margin:0">{services_html}</ul>
                </div>
                <div style="background:#0d0d0d;border:1px solid #1e1e1e;border-radius:10px;padding:20px;margin-bottom:24px">
                  <div style="font-size:0.72em;text-transform:uppercase;letter-spacing:1px;color:#D4AF37;font-weight:700;margin-bottom:12px">Next Steps</div>
                  <div style="color:#aaa;font-size:0.85em;line-height:1.8">
                    <div style="display:flex;gap:10px;margin-bottom:8px"><span style="color:#D4AF37;font-weight:700">1.</span><span>Complete your setup invoice below</span></div>
                    <div style="display:flex;gap:10px;margin-bottom:8px"><span style="color:#D4AF37;font-weight:700">2.</span><span>We'll reach out within 24 hours to schedule onboarding</span></div>
                    <div style="display:flex;gap:10px;margin-bottom:8px"><span style="color:#D4AF37;font-weight:700">3.</span><span>Your AI receptionist goes live within 48 hours of payment</span></div>
                  </div>
                </div>
                {pay_section}
              </div>
              <div style="padding:20px 28px;border-top:1px solid #1e1e1e;color:#555;font-size:0.75em">
                Questions? Reply to this email or reach us at hello@janovum.com
              </div>
            </div></div>
            """
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"Welcome to Janovum, {biz_name}! Here's what's next."
            msg['From'] = 'Janovum AI <myfriendlyagent12@gmail.com>'
            msg['To'] = contact_email
            msg.attach(MIMEText(body, 'html'))
            with smtplib.SMTP('smtp.gmail.com', 587) as s:
                s.starttls()
                s.login('myfriendlyagent12@gmail.com', 'pdcvjroclstugncx')
                s.send_message(msg)
            results.append({'step': 'welcome_email_sent', 'to': contact_email})
        except Exception as e:
            results.append({'step': 'welcome_email_sent', 'error': str(e)})
    # 3. Add to pipeline as signed
    try:
        import requests as _oreq2
        _oreq2.post('http://localhost:5050/api/pipeline/add', json={
            'business_name': biz_name,
            'contact_name': contact_name,
            'contact_email': contact_email,
            'business_type': p.get('business_type', ''),
            'stage': 'signed',
            'value': p.get('total', 1500),
            'source': 'proposal',
            'notes': f'Signed proposal #{proposal_id}',
        })
        results.append({'step': 'added_to_pipeline'})
    except Exception as e:
        results.append({'step': 'added_to_pipeline', 'error': str(e)})
    return jsonify({'status': 'ok', 'proposal_id': proposal_id, 'results': results})

@app.route('/api/onboarding/checklist', methods=['GET'])
def get_onboarding_checklist():
    """Default checklist of steps to onboard a new client"""
    return jsonify([
        {'id': 1, 'label': 'Collect Twilio phone number for client', 'done': False},
        {'id': 2, 'label': 'Set up client AI receptionist config', 'done': False},
        {'id': 3, 'label': 'Configure business hours and services', 'done': False},
        {'id': 4, 'label': 'Test receptionist with a live call', 'done': False},
        {'id': 5, 'label': 'Send client their portal link', 'done': False},
        {'id': 6, 'label': 'Schedule first check-in call (7 days)', 'done': False},
    ])

'''

marker = '# ══════════════════════════════════════════════════════════════\n# PROPOSALS & CONTRACTS'
if marker in content:
    content = content.replace(marker, FEATURES_6_10 + marker)
    open('/root/janovum-toolkit/platform/server_v2.py', 'w').write(content)
    print('Features 6-10 added, size:', len(content))
else:
    print('ERROR: marker not found')
