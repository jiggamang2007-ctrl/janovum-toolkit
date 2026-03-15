═══════════════════════════════════════════════════════════════
  JANOVUM TELEGRAM BOT — QUICK START
═══════════════════════════════════════════════════════════════

  SETUP (5 minutes, one time):

  1. Open Telegram → search @BotFather → send /newbot
     - Name: Janovum Bot
     - Username: JanovumBot (or janovum_llc_bot)
     - Copy the token he gives you

  2. Create a channel in Telegram:
     - Name: Janovum Alerts
     - Set to Private
     - Add your bot as Admin

  3. Send any message in the channel (just type "hello")

  4. Open config.py → paste your token

  5. Run:  python setup.py
     (this finds your channel and sends a welcome message)

  6. Test it:  python send_alert.py --test


  SENDING ALERTS:

  python send_alert.py --test
  python send_alert.py --type system_down --system "Chatbot" --client "Miami Bakery"
  python send_alert.py --type system_online --system "Chatbot" --client "Miami Bakery"
  python send_alert.py --type payment --client "Miami Bakery" --amount 300
  python send_alert.py --type new_client --client "Joe's Pizza"
  python send_alert.py --type morning
  python send_alert.py --type daily
  python send_alert.py --type custom -m "Whatever you want to say"


  USE IN YOUR OWN SCRIPTS:

  from send_alert import alert

  alert.system_down("AI Chatbot", client="Miami Bakery")
  alert.payment_received("Miami Bakery", 300.00)
  alert.new_client("Joe's Pizza", "Restaurant", "Chatbot + Scheduling")
  alert.daily_summary(total_clients=5, systems_online=5, systems_total=5)
  alert.good_morning(total_clients=3, tasks="- Follow up with Joe's Pizza\n- Check bakery chatbot")
  alert.milestone("First Client Signed!", "Miami Bakery - $300/mo + $200 setup")
  alert.custom("Any message you want", "CUSTOM TITLE")

═══════════════════════════════════════════════════════════════
