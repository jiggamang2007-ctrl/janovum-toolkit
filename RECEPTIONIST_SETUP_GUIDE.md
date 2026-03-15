# Janovum AI Receptionist — Full Setup Guide (From Zero)

Use this guide to deploy an AI receptionist for any client on any VPS or PC.
Total cost: ~$10-20/mo per client. Sell at $197-300/mo.

---

## What You'll Have When Done

- A real phone number that anyone can call 24/7
- AI answers, sounds like a real person (Cartesia Sonic, 40ms)
- Books appointments with conflict detection
- Sends confirmations (SMS/email)
- Mobile app page to see all bookings
- Daily spend cap + call limits
- All safeguards built in

---

## The Stack

| Part | Service | Cost |
|---|---|---|
| Phone | Twilio | $1.15/mo + $0.0085/min |
| Voice (TTS) | Cartesia Sonic | ~$0.01/min |
| Hearing (STT) | Deepgram | $0.0043/min |
| Brain (LLM) | Groq | FREE |
| Pipeline | Pipecat | FREE |
| Tunnel | Cloudflare | FREE |

---

## Step 1: Accounts You Need (One-Time)

Sign up for all of these. You only do this ONCE — all clients share the same accounts.

### 1a. Twilio (phone numbers)
1. Go to https://www.twilio.com/try-twilio
2. Sign up with your business email
3. Get your **Account SID** and **Auth Token** from the dashboard
4. Buy a phone number for each client ($1.15/mo each)

### 1b. Cartesia (voice)
1. Go to https://play.cartesia.ai
2. Sign up, verify email
3. Get your **API Key** (starts with `sk_car_...`)
4. Pick a **Voice ID** from the voices page

### 1c. Deepgram (speech-to-text)
1. Go to https://console.deepgram.com
2. Sign up — $200 free credit
3. Get your **API Key**

### 1d. Groq (AI brain)
1. Go to https://console.groq.com
2. Sign up (Google login works)
3. Get your **API Key** (starts with `gsk_...`)

---

## Step 2: Get the Toolkit

```bash
# On your VPS or PC
git clone https://github.com/jiggamang2007-ctrl/janovum-toolkit.git
cd janovum-toolkit/platform

# Install dependencies
pip install "pipecat-ai[cartesia,deepgram,silero]" fastapi uvicorn loguru websockets requests
```

---

## Step 3: Configure for a Client

Open `receptionist_simple.py` and update these values:

```python
# Line ~32: Your tunnel URL (update each time tunnel restarts)
PUBLIC_URL = "your-tunnel-url.trycloudflare.com"

# In run_bot function:
# Twilio auth token (same for all clients)
auth_token = "YOUR_TWILIO_AUTH_TOKEN"

# Deepgram API key
api_key = "YOUR_DEEPGRAM_KEY"

# Groq API key
api_key = "YOUR_GROQ_KEY"

# Cartesia API key + voice
api_key = "YOUR_CARTESIA_KEY"
voice_id = "YOUR_VOICE_ID"

# System prompt — customize per client:
# Change business name, services, hours, etc.
```

---

## Step 4: Buy a Phone Number for the Client

1. Log into Twilio console
2. Phone Numbers > Buy a Number
3. Pick a LOCAL number (not toll-free) in their area code
4. Set the Voice webhook to: `https://YOUR-TUNNEL-URL/incoming` (POST)

---

## Step 5: Start the Server

```bash
# Start the receptionist
cd platform
python receptionist_simple.py

# In another terminal, start the tunnel
cloudflared tunnel --url http://localhost:5051
# Copy the URL it gives you (like https://xxx.trycloudflare.com)
```

---

## Step 6: Set Twilio Webhook

1. Go to Twilio console > Phone Numbers > Active Numbers
2. Click the number
3. Under "A call comes in", set:
   - Webhook URL: `https://YOUR-TUNNEL-URL/incoming`
   - Method: POST

---

## Step 7: Test It

1. Call the phone number
2. Press any key (Twilio trial thing — goes away when you upgrade)
3. AI should greet you
4. Try booking an appointment
5. Check appointments at: `https://YOUR-TUNNEL-URL/app`

---

## Step 8: Keep Running on VPS

```bash
# Create a systemd service
sudo nano /etc/systemd/system/janovum-receptionist.service
```

```ini
[Unit]
Description=Janovum AI Receptionist
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/janovum-toolkit/platform
ExecStart=/usr/bin/python3 receptionist_simple.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable janovum-receptionist
sudo systemctl start janovum-receptionist
```

For the tunnel on VPS, use a permanent Cloudflare tunnel:
```bash
# Install cloudflared
curl -sL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee /usr/share/keyrings/cloudflare-main.gpg
echo 'deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared jammy main' | sudo tee /etc/apt/sources.list.d/cloudflared.list
sudo apt update && sudo apt install cloudflared

# Or point janovum.com to the VPS IP and use nginx
```

---

## Adding a New Client

1. Buy a new Twilio number in their area code ($1.15/mo)
2. Copy the system prompt section and change:
   - Business name
   - Services, prices, durations
   - Staff names
   - Business hours
3. Set the new number's webhook to your server
4. Done — they're live

---

## Endpoints

| URL | What |
|---|---|
| `/app` | Mobile-friendly appointment dashboard |
| `/appointments` | All appointments (JSON) |
| `/appointments/today` | Today's appointments (JSON) |
| `/status` | Server status + daily spend |
| `/incoming` | Twilio webhook (don't touch) |

---

## Safeguards

| Protection | Setting |
|---|---|
| Daily spend cap | $5/day (configurable) |
| Max calls per day | 50 (configurable) |
| Max call duration | 5 minutes |
| Conflict detection | Auto-checks before booking |
| Never dials out | Safety block in code |
| Spam protection | Cooldown per number |

---

## Cost Per Client (Monthly)

| Calls/day | Minutes/mo | Cost/mo | You Charge | Profit |
|---|---|---|---|---|
| 5 | 750 | ~$18 | $197 | $179 |
| 10 | 1,500 | ~$36 | $197 | $161 |
| 20 | 3,000 | ~$70 | $300 | $230 |

---

## Troubleshooting

| Problem | Fix |
|---|---|
| No greeting on call | Check tunnel is alive, check server logs |
| AI doesn't respond to speech | Make sure Deepgram key is valid |
| Slow responses | Check Groq key, don't use Pollinations |
| SMS not sending | Twilio trial can only text verified numbers. Upgrade to fix |
| Tunnel URL changed | Update Twilio webhook + PUBLIC_URL in code |
| Appointments not saving | Check data/ directory exists |

---

*Janovum AI Agent Toolkit — Built by Jaden*
