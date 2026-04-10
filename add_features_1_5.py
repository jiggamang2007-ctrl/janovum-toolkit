"""
Add Features 1-5:
1. Auto Invoicing + Stripe payment links
2. Missed Call Text-Back
3. Client ROI Reports (auto-email)
4. Smart Follow-Ups (auto-text non-bookers)
5. Review Collection (post-appointment texts)
"""

content = open('/root/janovum-toolkit/platform/server_v2.py').read()

FEATURES_1_5 = r'''
# ══════════════════════════════════════════════════════════════
# FEATURE 1: INVOICING (with optional Stripe payment links)
# ══════════════════════════════════════════════════════════════

INVOICES_FILE = os.path.join(PLATFORM_DIR, 'data', 'invoices.json')

def _load_invoices():
    if os.path.exists(INVOICES_FILE):
        with open(INVOICES_FILE) as f:
            return json.load(f)
    return {}

def _save_invoices(data):
    with open(INVOICES_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def _get_stripe_key():
    cfg_path = os.path.join(PLATFORM_DIR, 'data', 'toolkit_config.json')
    if os.path.exists(cfg_path):
        with open(cfg_path) as f:
            return json.load(f).get('stripe_secret_key', '')
    return ''

@app.route('/api/invoices', methods=['GET'])
def list_invoices():
    invs = _load_invoices()
    result = list(invs.values())
    result.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    return jsonify(result)

@app.route('/api/invoices/create', methods=['POST'])
def create_invoice():
    data = request.json or {}
    from datetime import datetime as _dt2
    import uuid as _uuid2
    iid = str(_uuid2.uuid4())[:8]
    now = _dt2.utcnow().isoformat()
    due_days = data.get('due_days', 7)
    due_date = (_dt2.utcnow().__class__.utcnow() if False else _dt2.utcnow()).isoformat()
    # simple due date
    import datetime as _dtt
    due_dt = _dtt.datetime.utcnow() + _dtt.timedelta(days=int(due_days))
    invoice = {
        'id': iid,
        'client_id': data.get('client_id', ''),
        'client_name': data.get('client_name', ''),
        'client_email': data.get('client_email', ''),
        'description': data.get('description', 'Monthly AI Services'),
        'amount': float(data.get('amount', 0)),
        'currency': 'usd',
        'status': 'unpaid',
        'created_at': now,
        'due_date': due_dt.isoformat(),
        'paid_at': None,
        'stripe_link': None,
        'notes': data.get('notes', ''),
        'recurring': data.get('recurring', False),
        'recurring_interval': data.get('recurring_interval', 'monthly'),
    }
    # Try to create Stripe payment link if key exists
    sk = _get_stripe_key()
    if sk and invoice['amount'] > 0:
        try:
            import requests as _req2
            # Create Stripe price (one-time)
            price_resp = _req2.post(
                'https://api.stripe.com/v1/prices',
                auth=(sk, ''),
                data={
                    'unit_amount': int(invoice['amount'] * 100),
                    'currency': 'usd',
                    'product_data[name]': invoice['description'],
                }
            )
            price_data = price_resp.json()
            if price_data.get('id'):
                # Create payment link
                link_resp = _req2.post(
                    'https://api.stripe.com/v1/payment_links',
                    auth=(sk, ''),
                    data={'line_items[0][price]': price_data['id'], 'line_items[0][quantity]': 1}
                )
                link_data = link_resp.json()
                if link_data.get('url'):
                    invoice['stripe_link'] = link_data['url']
        except Exception as e:
            print('Stripe error:', e)
    invs = _load_invoices()
    invs[iid] = invoice
    _save_invoices(invs)
    return jsonify(invoice)

@app.route('/api/invoices/<iid>/mark-paid', methods=['POST'])
def mark_invoice_paid(iid):
    from datetime import datetime as _dt3
    invs = _load_invoices()
    if iid not in invs:
        return jsonify({'error': 'Not found'}), 404
    invs[iid]['status'] = 'paid'
    invs[iid]['paid_at'] = _dt3.utcnow().isoformat()
    _save_invoices(invs)
    return jsonify({'status': 'ok'})

@app.route('/api/invoices/<iid>/delete', methods=['POST'])
def delete_invoice(iid):
    invs = _load_invoices()
    if iid in invs:
        del invs[iid]
        _save_invoices(invs)
    return jsonify({'status': 'ok'})

@app.route('/api/invoices/<iid>/send', methods=['POST'])
def send_invoice(iid):
    """Send invoice email to client"""
    invs = _load_invoices()
    inv = invs.get(iid)
    if not inv:
        return jsonify({'error': 'Not found'}), 404
    email = inv.get('client_email', '')
    if not email:
        return jsonify({'error': 'No email on file'}), 400
    try:
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        link = inv.get('stripe_link') or 'Reply to this email to arrange payment.'
        link_html = f'<a href="{link}" style="display:inline-block;background:#D4AF37;color:#000;padding:14px 28px;border-radius:8px;font-weight:700;text-decoration:none;margin-top:12px">Pay Now — ${inv["amount"]:,.2f}</a>' if inv.get('stripe_link') else f'<p style="color:#888">Amount due: <strong>${inv["amount"]:,.2f}</strong> — reply to arrange payment.</p>'
        body = f"""
        <div style="background:#0a0a0a;min-height:100vh;padding:40px 20px;font-family:sans-serif">
        <div style="max-width:520px;margin:0 auto;background:#111;border:1px solid #1e1e1e;border-radius:16px;overflow:hidden">
          <div style="background:linear-gradient(135deg,#1a1200,#0d0d0d);padding:28px;border-bottom:1px solid #1e1e1e">
            <div style="font-size:1.4em;font-weight:900;color:#D4AF37">Janovum<span style="color:#fff">.ai</span></div>
            <div style="color:#888;font-size:0.82em;margin-top:4px">Invoice #{iid}</div>
          </div>
          <div style="padding:28px">
            <p style="color:#e8e8e8;margin-bottom:8px">Hi {inv.get('client_name','there')},</p>
            <p style="color:#aaa;font-size:0.9em;line-height:1.7;margin-bottom:20px">Your invoice for <strong style="color:#e8e8e8">{inv['description']}</strong> is ready.</p>
            <div style="background:#0d0d0d;border:1px solid #1e1e1e;border-radius:10px;padding:20px;margin-bottom:20px">
              <div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #1a1a1a">
                <span style="color:#888;font-size:0.85em">Description</span><span style="color:#e8e8e8;font-size:0.85em">{inv['description']}</span>
              </div>
              <div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #1a1a1a">
                <span style="color:#888;font-size:0.85em">Amount Due</span><span style="color:#D4AF37;font-weight:700">${inv['amount']:,.2f}</span>
              </div>
              <div style="display:flex;justify-content:space-between;padding:8px 0">
                <span style="color:#888;font-size:0.85em">Due Date</span><span style="color:#e8e8e8;font-size:0.85em">{inv.get('due_date','')[:10]}</span>
              </div>
            </div>
            {link_html}
          </div>
          <div style="padding:20px 28px;border-top:1px solid #1e1e1e;color:#555;font-size:0.75em">Janovum AI &bull; hello@janovum.com &bull; janovum.com</div>
        </div></div>
        """
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f'Invoice #{iid} — ${inv["amount"]:,.2f} due {inv.get("due_date","")[:10]}'
        msg['From'] = 'Janovum AI <myfriendlyagent12@gmail.com>'
        msg['To'] = email
        msg.attach(MIMEText(body, 'html'))
        with smtplib.SMTP('smtp.gmail.com', 587) as s:
            s.starttls()
            s.login('myfriendlyagent12@gmail.com', 'pdcvjroclstugncx')
            s.send_message(msg)
        invs[iid]['sent_at'] = __import__('datetime').datetime.utcnow().isoformat()
        _save_invoices(invs)
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ══════════════════════════════════════════════════════════════
# FEATURE 2: MISSED CALL TEXT-BACK
# ══════════════════════════════════════════════════════════════

MISSED_CALL_CONFIG_FILE = os.path.join(PLATFORM_DIR, 'data', 'missed_call_config.json')
MISSED_CALL_LOG_FILE = os.path.join(PLATFORM_DIR, 'data', 'missed_call_log.json')

def _load_missed_cfg():
    if os.path.exists(MISSED_CALL_CONFIG_FILE):
        with open(MISSED_CALL_CONFIG_FILE) as f:
            return json.load(f)
    return {'enabled': False, 'message': "Hey! We missed your call. We'd love to help — when's a good time to chat? Reply here or call us back!", 'delay_seconds': 30}

def _save_missed_cfg(data):
    with open(MISSED_CALL_CONFIG_FILE, 'w') as f:
        json.dump(data, f, indent=2)

@app.route('/api/missed-call/config', methods=['GET'])
def get_missed_call_config():
    return jsonify(_load_missed_cfg())

@app.route('/api/missed-call/config', methods=['POST'])
def save_missed_call_config():
    data = request.json or {}
    cfg = _load_missed_cfg()
    cfg.update(data)
    _save_missed_cfg(cfg)
    return jsonify({'status': 'ok'})

@app.route('/api/missed-call/log', methods=['GET'])
def get_missed_call_log():
    if os.path.exists(MISSED_CALL_LOG_FILE):
        with open(MISSED_CALL_LOG_FILE) as f:
            log = json.load(f)
    else:
        log = []
    return jsonify(log[-50:])

@app.route('/api/missed-call/trigger', methods=['POST'])
def trigger_missed_call_textback():
    """Called by receptionist when a call is missed/hung up early"""
    data = request.json or {}
    caller_number = data.get('caller_number', '')
    client_id = data.get('client_id', '')
    if not caller_number:
        return jsonify({'error': 'caller_number required'}), 400
    cfg = _load_missed_cfg()
    if not cfg.get('enabled'):
        return jsonify({'status': 'disabled'})
    # Load client config for Twilio credentials and from-number
    tk_path = os.path.join(PLATFORM_DIR, 'data', 'toolkit_config.json')
    client_path = os.path.join(PLATFORM_DIR, 'data', 'clients', f'{client_id}.json') if client_id else None
    try:
        with open(tk_path) as f:
            tk = json.load(f)
        from_number = tk.get('twilio_phone_number', '')
        if client_path and os.path.exists(client_path):
            with open(client_path) as f:
                client_cfg = json.load(f)
            from_number = client_cfg.get('twilio_phone_number', from_number)
        import requests as _req3
        resp = _req3.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{tk['twilio_account_sid']}/Messages.json",
            auth=(tk['twilio_account_sid'], tk['twilio_auth_token']),
            data={'From': from_number, 'To': caller_number, 'Body': cfg['message']}
        )
        result = resp.json()
        # Log it
        if os.path.exists(MISSED_CALL_LOG_FILE):
            with open(MISSED_CALL_LOG_FILE) as f:
                log = json.load(f)
        else:
            log = []
        log.append({
            'caller': caller_number,
            'client_id': client_id,
            'sent_at': __import__('datetime').datetime.utcnow().isoformat(),
            'message': cfg['message'],
            'status': 'sent' if result.get('sid') else 'failed',
            'twilio_sid': result.get('sid', '')
        })
        with open(MISSED_CALL_LOG_FILE, 'w') as f:
            json.dump(log, f, indent=2)
        return jsonify({'status': 'ok', 'sid': result.get('sid')})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ══════════════════════════════════════════════════════════════
# FEATURE 3: CLIENT ROI REPORTS (auto-email)
# ══════════════════════════════════════════════════════════════

@app.route('/api/roi-report/preview/<client_id>', methods=['GET'])
def roi_report_preview(client_id):
    """Return stats for a client's ROI report"""
    import glob as _glob
    import datetime as _dttm
    calls_handled = 0
    appts_booked = 0
    # Count from call logs if they exist
    call_log_path = os.path.join(PLATFORM_DIR, 'data', 'clients', f'{client_id}_calls.json')
    if os.path.exists(call_log_path):
        with open(call_log_path) as f:
            calls = json.load(f)
        week_ago = (_dttm.datetime.utcnow() - _dttm.timedelta(days=7)).isoformat()
        calls_handled = sum(1 for c in calls if c.get('timestamp', '') >= week_ago)
    # Count appointments from last 7 days
    appt_path = os.path.join(PLATFORM_DIR, 'data', 'clients', f'{client_id}_appointments.json')
    if not os.path.exists(appt_path):
        appt_path = os.path.join(PLATFORM_DIR, 'data', 'clients', 'janovum_appointments.json')
    if os.path.exists(appt_path):
        with open(appt_path) as f:
            appts = json.load(f)
        week_ago = (_dttm.datetime.utcnow() - _dttm.timedelta(days=7)).isoformat()
        appts_booked = sum(1 for a in appts if a.get('created_at', '') >= week_ago)
    # Estimate hours saved (avg 4 min per call)
    hours_saved = round((calls_handled * 4) / 60, 1)
    monthly_fee = 500  # default
    # Try to get from client config
    client_cfg_path = os.path.join(PLATFORM_DIR, 'data', 'clients', f'{client_id}.json')
    biz_name = client_id
    if os.path.exists(client_cfg_path):
        with open(client_cfg_path) as f:
            cfg = json.load(f)
        biz_name = cfg.get('business_name', client_id)
        monthly_fee = cfg.get('monthly_fee', 500)
    cost_per_call = round(monthly_fee / max(calls_handled, 1), 2)
    return jsonify({
        'client_id': client_id,
        'business_name': biz_name,
        'calls_handled': calls_handled,
        'appts_booked': appts_booked,
        'hours_saved': hours_saved,
        'monthly_fee': monthly_fee,
        'cost_per_call': cost_per_call,
        'week_of': _dttm.datetime.utcnow().strftime('%B %d, %Y'),
    })

@app.route('/api/roi-report/send/<client_id>', methods=['POST'])
def send_roi_report(client_id):
    """Send weekly ROI report email to client"""
    data = request.json or {}
    email = data.get('email', '')
    # Get stats
    import requests as _req4
    try:
        stats_resp = _req4.get(f'http://localhost:5050/api/roi-report/preview/{client_id}')
        stats = stats_resp.json()
    except:
        stats = {'calls_handled': 0, 'appts_booked': 0, 'hours_saved': 0, 'monthly_fee': 500, 'business_name': client_id, 'week_of': 'this week'}
    if not email:
        # Try client config
        client_cfg_path = os.path.join(PLATFORM_DIR, 'data', 'clients', f'{client_id}.json')
        if os.path.exists(client_cfg_path):
            with open(client_cfg_path) as f:
                cfg = json.load(f)
            email = cfg.get('contact_email', '')
    if not email:
        return jsonify({'error': 'No email found for client'}), 400
    try:
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        body = f"""
        <div style="background:#0a0a0a;min-height:100vh;padding:40px 20px;font-family:sans-serif">
        <div style="max-width:520px;margin:0 auto;background:#111;border:1px solid #1e1e1e;border-radius:16px;overflow:hidden">
          <div style="background:linear-gradient(135deg,#1a1200,#0d0d0d);padding:28px;border-bottom:1px solid #1e1e1e">
            <div style="font-size:1.4em;font-weight:900;color:#D4AF37">Janovum<span style="color:#fff">.ai</span></div>
            <div style="color:#888;font-size:0.82em;margin-top:4px">Weekly AI Performance Report</div>
          </div>
          <div style="padding:28px">
            <p style="color:#e8e8e8;margin-bottom:6px">Hi {stats['business_name']},</p>
            <p style="color:#aaa;font-size:0.88em;line-height:1.7;margin-bottom:24px">Here's what your AI receptionist handled this week (ending {stats['week_of']}):</p>
            <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-bottom:24px">
              <div style="background:#0d0d0d;border:1px solid #1e1e1e;border-radius:10px;padding:16px;text-align:center">
                <div style="font-size:2em;font-weight:900;color:#42a5f5">{stats['calls_handled']}</div>
                <div style="font-size:0.7em;color:#666;margin-top:4px;text-transform:uppercase;letter-spacing:1px">Calls Handled</div>
              </div>
              <div style="background:#0d0d0d;border:1px solid #1e1e1e;border-radius:10px;padding:16px;text-align:center">
                <div style="font-size:2em;font-weight:900;color:#00c853">{stats['appts_booked']}</div>
                <div style="font-size:0.7em;color:#666;margin-top:4px;text-transform:uppercase;letter-spacing:1px">Appts Booked</div>
              </div>
              <div style="background:#0d0d0d;border:1px solid #1e1e1e;border-radius:10px;padding:16px;text-align:center">
                <div style="font-size:2em;font-weight:900;color:#D4AF37">{stats['hours_saved']}h</div>
                <div style="font-size:0.7em;color:#666;margin-top:4px;text-transform:uppercase;letter-spacing:1px">Hours Saved</div>
              </div>
            </div>
            <div style="background:linear-gradient(135deg,#1a1200,#0d0d0d);border:1px solid #D4AF3733;border-radius:10px;padding:16px;margin-bottom:20px">
              <div style="font-size:0.78em;color:#D4AF37;font-weight:700;margin-bottom:8px">YOUR ROI THIS WEEK</div>
              <div style="color:#aaa;font-size:0.85em;line-height:1.8">
                At your monthly plan of <strong style="color:#e8e8e8">${stats['monthly_fee']}/mo</strong>, your AI handled each call for roughly <strong style="color:#D4AF37">${stats['cost_per_call']:.2f}</strong> — a fraction of what a receptionist costs.<br><br>
                <strong style="color:#e8e8e8">{stats['hours_saved']} hours</strong> saved this week alone — time you can spend growing your business.
              </div>
            </div>
            <p style="color:#555;font-size:0.78em;text-align:center">Questions? Reply to this email — we're always here.</p>
          </div>
          <div style="padding:20px 28px;border-top:1px solid #1e1e1e;color:#555;font-size:0.75em">Janovum AI &bull; hello@janovum.com &bull; janovum.com</div>
        </div></div>
        """
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Your AI handled {stats['calls_handled']} calls this week — {stats['business_name']} Report"
        msg['From'] = 'Janovum AI <myfriendlyagent12@gmail.com>'
        msg['To'] = email
        msg.attach(MIMEText(body, 'html'))
        with smtplib.SMTP('smtp.gmail.com', 587) as s:
            s.starttls()
            s.login('myfriendlyagent12@gmail.com', 'pdcvjroclstugncx')
            s.send_message(msg)
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/roi-report/config', methods=['GET', 'POST'])
def roi_report_config():
    cfg_path = os.path.join(PLATFORM_DIR, 'data', 'roi_report_config.json')
    if request.method == 'POST':
        data = request.json or {}
        with open(cfg_path, 'w') as f:
            json.dump(data, f, indent=2)
        return jsonify({'status': 'ok'})
    if os.path.exists(cfg_path):
        with open(cfg_path) as f:
            return jsonify(json.load(f))
    return jsonify({'auto_send': False, 'day': 'monday', 'time': '09:00'})

# ══════════════════════════════════════════════════════════════
# FEATURE 4: SMART FOLLOW-UPS
# ══════════════════════════════════════════════════════════════

FOLLOWUPS_FILE = os.path.join(PLATFORM_DIR, 'data', 'followups.json')
FOLLOWUP_CONFIG_FILE = os.path.join(PLATFORM_DIR, 'data', 'followup_config.json')

def _load_followups():
    if os.path.exists(FOLLOWUPS_FILE):
        with open(FOLLOWUPS_FILE) as f:
            return json.load(f)
    return []

def _load_followup_cfg():
    if os.path.exists(FOLLOWUP_CONFIG_FILE):
        with open(FOLLOWUP_CONFIG_FILE) as f:
            return json.load(f)
    return {
        'enabled': False,
        'delay_hours': 2,
        'message': "Hey! We saw you called earlier but didn't get a chance to connect. We'd love to help — want to schedule something? Reply here or call us back anytime!"
    }

@app.route('/api/followups/config', methods=['GET'])
def get_followup_config():
    return jsonify(_load_followup_cfg())

@app.route('/api/followups/config', methods=['POST'])
def save_followup_config():
    data = request.json or {}
    cfg = _load_followup_cfg()
    cfg.update(data)
    with open(FOLLOWUP_CONFIG_FILE, 'w') as f:
        json.dump(cfg, f, indent=2)
    return jsonify({'status': 'ok'})

@app.route('/api/followups/log', methods=['GET'])
def get_followups_log():
    return jsonify(_load_followups()[-50:])

@app.route('/api/followups/trigger', methods=['POST'])
def trigger_followup():
    """Called when a call ends without booking — schedule a follow-up"""
    data = request.json or {}
    caller_number = data.get('caller_number', '')
    client_id = data.get('client_id', '')
    reason = data.get('reason', 'no_booking')
    if not caller_number:
        return jsonify({'error': 'caller_number required'}), 400
    cfg = _load_followup_cfg()
    if not cfg.get('enabled'):
        return jsonify({'status': 'disabled'})
    # Send immediately (in production would use a queue/delay)
    tk_path = os.path.join(PLATFORM_DIR, 'data', 'toolkit_config.json')
    try:
        with open(tk_path) as f:
            tk = json.load(f)
        from_number = tk.get('twilio_phone_number', '')
        import requests as _req5
        resp = _req5.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{tk['twilio_account_sid']}/Messages.json",
            auth=(tk['twilio_account_sid'], tk['twilio_auth_token']),
            data={'From': from_number, 'To': caller_number, 'Body': cfg['message']}
        )
        result = resp.json()
        followups = _load_followups()
        followups.append({
            'caller': caller_number,
            'client_id': client_id,
            'reason': reason,
            'sent_at': __import__('datetime').datetime.utcnow().isoformat(),
            'status': 'sent' if result.get('sid') else 'failed',
            'sid': result.get('sid', '')
        })
        with open(FOLLOWUPS_FILE, 'w') as f:
            json.dump(followups, f, indent=2)
        return jsonify({'status': 'ok', 'sid': result.get('sid')})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ══════════════════════════════════════════════════════════════
# FEATURE 5: REVIEW COLLECTION
# ══════════════════════════════════════════════════════════════

REVIEW_CONFIG_FILE = os.path.join(PLATFORM_DIR, 'data', 'review_config.json')
REVIEW_LOG_FILE = os.path.join(PLATFORM_DIR, 'data', 'review_log.json')

def _load_review_cfg():
    if os.path.exists(REVIEW_CONFIG_FILE):
        with open(REVIEW_CONFIG_FILE) as f:
            return json.load(f)
    return {
        'enabled': False,
        'google_review_link': '',
        'send_after_hours': 2,
        'message': "Hi {name}! Thanks for visiting us today. If you had a great experience, we'd really appreciate a quick Google review — it helps us a lot! {link}"
    }

def _save_review_cfg(data):
    with open(REVIEW_CONFIG_FILE, 'w') as f:
        json.dump(data, f, indent=2)

@app.route('/api/reviews/config', methods=['GET'])
def get_review_config():
    return jsonify(_load_review_cfg())

@app.route('/api/reviews/config', methods=['POST'])
def save_review_config():
    data = request.json or {}
    cfg = _load_review_cfg()
    cfg.update(data)
    _save_review_cfg(cfg)
    return jsonify({'status': 'ok'})

@app.route('/api/reviews/log', methods=['GET'])
def get_review_log():
    if os.path.exists(REVIEW_LOG_FILE):
        with open(REVIEW_LOG_FILE) as f:
            return jsonify(json.load(f)[-50:])
    return jsonify([])

@app.route('/api/reviews/send', methods=['POST'])
def send_review_request():
    """Send review request SMS after appointment"""
    data = request.json or {}
    phone = data.get('phone', '')
    name = data.get('name', 'there')
    client_id = data.get('client_id', '')
    if not phone:
        return jsonify({'error': 'phone required'}), 400
    cfg = _load_review_cfg()
    if not cfg.get('enabled'):
        return jsonify({'status': 'disabled'})
    link = cfg.get('google_review_link', '')
    message = cfg['message'].replace('{name}', name).replace('{link}', link)
    tk_path = os.path.join(PLATFORM_DIR, 'data', 'toolkit_config.json')
    try:
        with open(tk_path) as f:
            tk = json.load(f)
        from_number = tk.get('twilio_phone_number', '')
        import requests as _req6
        resp = _req6.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{tk['twilio_account_sid']}/Messages.json",
            auth=(tk['twilio_account_sid'], tk['twilio_auth_token']),
            data={'From': from_number, 'To': phone, 'Body': message}
        )
        result = resp.json()
        # Log
        if os.path.exists(REVIEW_LOG_FILE):
            with open(REVIEW_LOG_FILE) as f:
                log = json.load(f)
        else:
            log = []
        log.append({
            'phone': phone,
            'name': name,
            'client_id': client_id,
            'sent_at': __import__('datetime').datetime.utcnow().isoformat(),
            'status': 'sent' if result.get('sid') else 'failed',
        })
        with open(REVIEW_LOG_FILE, 'w') as f:
            json.dump(log, f, indent=2)
        return jsonify({'status': 'ok', 'sid': result.get('sid')})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

'''

marker = '# ══════════════════════════════════════════════════════════════\n# PROPOSALS & CONTRACTS'
if marker in content:
    content = content.replace(marker, FEATURES_1_5 + marker)
    open('/root/janovum-toolkit/platform/server_v2.py', 'w').write(content)
    print('Features 1-5 added, size:', len(content))
else:
    print('ERROR: marker not found')
    # Show what markers exist
    import re
    markers = re.findall(r'# ══+\n# [^\n]+', content)
    for m in markers[:5]:
        print(repr(m))
