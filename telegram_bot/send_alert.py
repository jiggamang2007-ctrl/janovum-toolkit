"""
JANOVUM TELEGRAM BOT — SEND ALERTS
Beautiful, formatted alert messages for your Janovum Alerts channel.

Usage:
  python send_alert.py --test                    (send test alert)
  python send_alert.py --type system_down        (system down alert)
  python send_alert.py --type custom -m "Hello"  (custom message)

Or import in your own scripts:
  from send_alert import alert
  alert.system_online("Client XYZ Chatbot")
"""
import requests
import sys
import os
import argparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import BOT_TOKEN, CHANNEL_ID, OWNER_NAME, COMPANY_NAME

API = f"https://api.telegram.org/bot{BOT_TOKEN}"


def send(text):
    """Send a formatted HTML message to the alerts channel."""
    if not CHANNEL_ID:
        print("❌ Channel ID not set. Run setup.py first.")
        return False
    r = requests.post(f"{API}/sendMessage", json={
        "chat_id": CHANNEL_ID,
        "text": text.strip(),
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    })
    if r.status_code == 200 and r.json().get("ok"):
        return True
    print(f"❌ Failed: {r.json()}")
    return False


def timestamp():
    return datetime.now().strftime("%m/%d/%Y %I:%M %p")


# ═══════════════════════════════════════════════════════════════
# ALERT TEMPLATES — All the nice formatted messages
# ═══════════════════════════════════════════════════════════════

class JanovumAlerts:
    """Beautiful alert templates for Janovum."""

    # ── SYSTEM ALERTS ──────────────────────────────────────
    def system_online(self, system_name, client=""):
        client_line = f"\n👤 Client: <b>{client}</b>" if client else ""
        send(f"""
🟢 <b>SYSTEM ONLINE</b>
━━━━━━━━━━━━━━━━━━━━━━
🖥 {system_name} is up and running{client_line}
🕐 {timestamp()}
━━━━━━━━━━━━━━━━━━━━━━
◈ <i>{COMPANY_NAME}</i>
""")

    def system_down(self, system_name, client="", details=""):
        client_line = f"\n👤 Client: <b>{client}</b>" if client else ""
        details_line = f"\n📝 {details}" if details else ""
        send(f"""
🔴 <b>SYSTEM DOWN</b>
━━━━━━━━━━━━━━━━━━━━━━
⚠️ {system_name} is offline!{client_line}{details_line}
🕐 {timestamp()}

🔧 <i>Action required — check immediately</i>
━━━━━━━━━━━━━━━━━━━━━━
◈ <i>{COMPANY_NAME}</i>
""")

    def system_warning(self, system_name, warning, client=""):
        client_line = f"\n👤 Client: <b>{client}</b>" if client else ""
        send(f"""
🟡 <b>WARNING</b>
━━━━━━━━━━━━━━━━━━━━━━
⚡ {system_name}{client_line}
📝 {warning}
🕐 {timestamp()}
━━━━━━━━━━━━━━━━━━━━━━
◈ <i>{COMPANY_NAME}</i>
""")

    def system_recovered(self, system_name, downtime="", client=""):
        client_line = f"\n👤 Client: <b>{client}</b>" if client else ""
        down_line = f"\n⏱ Downtime: {downtime}" if downtime else ""
        send(f"""
🟢 <b>RECOVERED</b>
━━━━━━━━━━━━━━━━━━━━━━
✅ {system_name} is back online{client_line}{down_line}
🕐 {timestamp()}
━━━━━━━━━━━━━━━━━━━━━━
◈ <i>{COMPANY_NAME}</i>
""")

    # ── CLIENT ALERTS ──────────────────────────────────────
    def new_client(self, client_name, business_type="", services=""):
        biz_line = f"\n🏪 Business: {business_type}" if business_type else ""
        svc_line = f"\n📋 Services: {services}" if services else ""
        send(f"""
🎉 <b>NEW CLIENT</b>
━━━━━━━━━━━━━━━━━━━━━━
🤝 Welcome <b>{client_name}</b>!{biz_line}{svc_line}
🕐 {timestamp()}
━━━━━━━━━━━━━━━━━━━━━━
◈ <i>{COMPANY_NAME}</i>
""")

    def client_setup_complete(self, client_name, systems=""):
        sys_line = f"\n🖥 Systems: {systems}" if systems else ""
        send(f"""
✅ <b>SETUP COMPLETE</b>
━━━━━━━━━━━━━━━━━━━━━━
🏁 <b>{client_name}</b> is fully set up!{sys_line}
📡 Monitoring active
🕐 {timestamp()}
━━━━━━━━━━━━━━━━━━━━━━
◈ <i>{COMPANY_NAME}</i>
""")

    # ── PAYMENT ALERTS ─────────────────────────────────────
    def payment_received(self, client_name, amount, description=""):
        desc_line = f"\n📝 {description}" if description else ""
        send(f"""
💰 <b>PAYMENT RECEIVED</b>
━━━━━━━━━━━━━━━━━━━━━━
💵 <b>${amount:.2f}</b> from <b>{client_name}</b>{desc_line}
🕐 {timestamp()}
━━━━━━━━━━━━━━━━━━━━━━
◈ <i>{COMPANY_NAME}</i>
""")

    def payment_due(self, client_name, amount, due_date=""):
        due_line = f"\n📅 Due: {due_date}" if due_date else ""
        send(f"""
🔔 <b>PAYMENT DUE</b>
━━━━━━━━━━━━━━━━━━━━━━
💳 <b>${amount:.2f}</b> from <b>{client_name}</b>{due_line}
🕐 {timestamp()}
━━━━━━━━━━━━━━━━━━━━━━
◈ <i>{COMPANY_NAME}</i>
""")

    def payment_overdue(self, client_name, amount, days_late=0):
        send(f"""
🚨 <b>PAYMENT OVERDUE</b>
━━━━━━━━━━━━━━━━━━━━━━
❗ <b>${amount:.2f}</b> from <b>{client_name}</b>
📅 {days_late} days overdue
🕐 {timestamp()}

<i>Follow up with client</i>
━━━━━━━━━━━━━━━━━━━━━━
◈ <i>{COMPANY_NAME}</i>
""")

    # ── DAILY SUMMARY ──────────────────────────────────────
    def daily_summary(self, total_clients=0, systems_online=0, systems_total=0, revenue_month=0, alerts_today=0):
        status = "🟢 All systems operational" if systems_online == systems_total else f"🟡 {systems_total - systems_online} system(s) need attention"
        send(f"""
📊 <b>DAILY SUMMARY</b>
━━━━━━━━━━━━━━━━━━━━━━
📅 {datetime.now().strftime("%A, %B %d, %Y")}

👥 Active Clients: <b>{total_clients}</b>
🖥 Systems: <b>{systems_online}/{systems_total}</b> online
💰 Monthly Revenue: <b>${revenue_month:,.2f}</b>
🔔 Alerts Today: <b>{alerts_today}</b>

{status}
━━━━━━━━━━━━━━━━━━━━━━
◈ <i>{COMPANY_NAME} — The Doorway to New Creation.</i>
""")

    # ── SERVICE ALERTS ─────────────────────────────────────
    def service_call_scheduled(self, client_name, date, reason=""):
        reason_line = f"\n📝 Reason: {reason}" if reason else ""
        send(f"""
🔧 <b>SERVICE CALL SCHEDULED</b>
━━━━━━━━━━━━━━━━━━━━━━
👤 Client: <b>{client_name}</b>
📅 Date: <b>{date}</b>{reason_line}
🕐 {timestamp()}
━━━━━━━━━━━━━━━━━━━━━━
◈ <i>{COMPANY_NAME}</i>
""")

    def service_call_complete(self, client_name, summary=""):
        sum_line = f"\n📝 {summary}" if summary else ""
        send(f"""
✅ <b>SERVICE CALL COMPLETE</b>
━━━━━━━━━━━━━━━━━━━━━━
👤 Client: <b>{client_name}</b>{sum_line}
🕐 {timestamp()}
━━━━━━━━━━━━━━━━━━━━━━
◈ <i>{COMPANY_NAME}</i>
""")

    # ── MILESTONES ─────────────────────────────────────────
    def milestone(self, title, details=""):
        det_line = f"\n📝 {details}" if details else ""
        send(f"""
🏆 <b>MILESTONE</b>
━━━━━━━━━━━━━━━━━━━━━━
🎯 <b>{title}</b>{det_line}
🕐 {timestamp()}
━━━━━━━━━━━━━━━━━━━━━━
◈ <i>{COMPANY_NAME} — The Doorway to New Creation.</i>
""")

    # ── CUSTOM MESSAGE ─────────────────────────────────────
    def custom(self, message, title="UPDATE"):
        send(f"""
📌 <b>{title}</b>
━━━━━━━━━━━━━━━━━━━━━━
{message}
🕐 {timestamp()}
━━━━━━━━━━━━━━━━━━━━━━
◈ <i>{COMPANY_NAME}</i>
""")

    # ── GOOD MORNING ───────────────────────────────────────
    def good_morning(self, total_clients=0, tasks=""):
        task_line = f"\n\n📋 <b>Today's Focus:</b>\n{tasks}" if tasks else ""
        send(f"""
☀️ <b>GOOD MORNING, {OWNER_NAME.upper()}</b>
━━━━━━━━━━━━━━━━━━━━━━
📅 {datetime.now().strftime("%A, %B %d, %Y")}
👥 {total_clients} active client(s)
🟢 All systems checked{task_line}

<i>Let's get it. 💪</i>
━━━━━━━━━━━━━━━━━━━━━━
◈ <i>{COMPANY_NAME} — The Doorway to New Creation.</i>
""")


# Create global instance
alert = JanovumAlerts()


# ═══════════════════════════════════════════════════════════════
# COMMAND LINE USAGE
# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Janovum Telegram Alerts")
    parser.add_argument("--test", action="store_true", help="Send a test alert")
    parser.add_argument("--type", type=str, help="Alert type: system_down, system_online, payment, new_client, daily, morning, custom")
    parser.add_argument("-m", "--message", type=str, help="Custom message text")
    parser.add_argument("--client", type=str, default="", help="Client name")
    parser.add_argument("--system", type=str, default="", help="System name")
    parser.add_argument("--amount", type=float, default=0, help="Payment amount")
    args = parser.parse_args()

    if args.test:
        print("📤 Sending test alerts...")
        alert.custom(f"🧪 Test alert sent successfully!\n\n{OWNER_NAME}, your Janovum alert system is working perfectly.", "TEST ALERT")
        print("✅ Test alert sent! Check your Telegram channel.")

    elif args.type == "system_down":
        alert.system_down(args.system or "Unknown System", args.client)
    elif args.type == "system_online":
        alert.system_online(args.system or "Unknown System", args.client)
    elif args.type == "payment":
        alert.payment_received(args.client or "Unknown", args.amount)
    elif args.type == "new_client":
        alert.new_client(args.client or "New Client")
    elif args.type == "daily":
        alert.daily_summary()
    elif args.type == "morning":
        alert.good_morning()
    elif args.type == "custom" and args.message:
        alert.custom(args.message)
    else:
        print("Janovum Alert System")
        print("Usage:")
        print("  python send_alert.py --test")
        print("  python send_alert.py --type system_down --system 'Chatbot' --client 'Miami Bakery'")
        print("  python send_alert.py --type payment --client 'Miami Bakery' --amount 300")
        print("  python send_alert.py --type custom -m 'Your message here'")
        print("  python send_alert.py --type morning")
        print("  python send_alert.py --type daily")
