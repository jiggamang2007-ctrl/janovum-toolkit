"""
Janovum AI Receptionist — Client Instance
Config-driven receptionist that reads from a client JSON config file.
Usage: python receptionist_client.py /path/to/client_config.json
"""

import os
import sys
import json
import asyncio
from pathlib import Path

import uvicorn
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import Response, HTMLResponse
from loguru import logger

logger.remove(0)
logger.add(sys.stderr, level="DEBUG")

PLATFORM_DIR = Path(__file__).parent
sys.path.insert(0, str(PLATFORM_DIR))

# Load client config from command line argument
if len(sys.argv) < 2:
    print("Usage: python receptionist_client.py <client_config.json>")
    sys.exit(1)

CONFIG_PATH = Path(sys.argv[1])
if not CONFIG_PATH.exists():
    print(f"Config not found: {CONFIG_PATH}")
    sys.exit(1)

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CLIENT_CONFIG = json.load(f)

CLIENT_ID = CLIENT_CONFIG["client_id"]
BUSINESS_NAME = CLIENT_CONFIG["business_name"]
PORT = CLIENT_CONFIG["port"]
TWILIO_PHONE = CLIENT_CONFIG["twilio_phone_number"]

# Shared API keys (loaded from config or fallback)
TWILIO_ACCOUNT_SID = CLIENT_CONFIG.get("twilio_account_sid", "AC2d50767d64e32c3b57b56a57c11c3849")
TWILIO_AUTH_TOKEN = CLIENT_CONFIG.get("twilio_auth_token", "94c74007b62652b5b14c7bea70a5792c")
DEEPGRAM_KEY = CLIENT_CONFIG.get("deepgram_api_key", "6e304c8a16d16deae3ec7694e60212c4f610ba96")
GROQ_KEY = CLIENT_CONFIG.get("groq_api_key", "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")
CARTESIA_KEY = CLIENT_CONFIG.get("cartesia_api_key", "sk_car_7QqSF9RbebzaELHtggdw3E")
CARTESIA_VOICE = CLIENT_CONFIG.get("cartesia_voice_id", "9626c31c-bec5-4cca-baa8-f8ba9e84c8bc")

# Tunnel URL — reads from tunnel_url.txt (written by start_tunnel.py), env var, or fallback
def _read_tunnel_url():
    tunnel_file = PLATFORM_DIR / "data" / "tunnel_url.txt"
    if tunnel_file.exists():
        try:
            url = tunnel_file.read_text().strip()
            if url:
                return url
        except Exception:
            pass
    # Check toolkit_config.json for domain (VPS deployment)
    try:
        import json as _json
        tk_path = Path(__file__).parent / "data" / "toolkit_config.json"
        if tk_path.exists():
            tk = _json.loads(tk_path.read_text())
            domain = tk.get("domain", "")
            if domain:
                return domain
    except Exception:
        pass
    return os.environ.get("PUBLIC_URL", f"localhost:{PORT}")

PUBLIC_URL = _read_tunnel_url()

# Safety
BLOCKED_OUTBOUND = True
DAILY_SPEND_CAP = CLIENT_CONFIG.get("daily_spend_cap", 5.00)
DAILY_CALL_LIMIT = CLIENT_CONFIG.get("daily_call_limit", 50)
COST_PER_MINUTE = 0.023

import time
from datetime import date, datetime

app = FastAPI()

# Appointments file for this client
APPTS_PATH = Path(CONFIG_PATH).parent / f"{CLIENT_ID}_appointments.json"


class DailyTracker:
    def __init__(self):
        self.reset()

    def reset(self):
        self.date = date.today()
        self.call_count = 0
        self.total_minutes = 0.0
        self.total_cost = 0.0

    def check_new_day(self):
        if date.today() != self.date:
            logger.info(f"[{CLIENT_ID}] New day — resetting. Yesterday: {self.call_count} calls, ${self.total_cost:.2f}")
            self.reset()

    def can_accept(self):
        self.check_new_day()
        if self.call_count >= DAILY_CALL_LIMIT:
            return False, "daily_call_limit"
        if self.total_cost >= DAILY_SPEND_CAP:
            return False, "daily_spend_cap"
        return True, "ok"

    def register_call(self):
        self.check_new_day()
        self.call_count += 1

    def add_minutes(self, minutes):
        self.total_minutes += minutes
        self.total_cost += minutes * COST_PER_MINUTE

    def get_status(self):
        self.check_new_day()
        return {
            "date": str(self.date),
            "calls_today": self.call_count,
            "max_calls": DAILY_CALL_LIMIT,
            "minutes_today": round(self.total_minutes, 1),
            "cost_today": round(self.total_cost, 2),
            "daily_cap": DAILY_SPEND_CAP,
            "remaining_budget": round(DAILY_SPEND_CAP - self.total_cost, 2),
        }

daily_tracker = DailyTracker()


@app.post("/")
@app.post("/incoming")
async def incoming_call(request: Request):
    try:
        form_data = await request.form()
        from_number = form_data.get("From", form_data.get("Caller", "unknown"))
    except Exception:
        from_number = "unknown"

    can_accept, reason = daily_tracker.can_accept()
    if not can_accept:
        logger.warning(f"[{CLIENT_ID}] Rejecting call from {from_number}: {reason}")
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="Polly.Joanna">We're sorry, {BUSINESS_NAME} is unavailable right now. Please try again tomorrow.</Say>
  <Hangup/>
</Response>"""
        return Response(content=twiml, media_type="application/xml")

    daily_tracker.register_call()

    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Connect>
    <Stream url="wss://{PUBLIC_URL}/ws">
      <Parameter name="from_number" value="{from_number}"/>
    </Stream>
  </Connect>
  <Pause length="40"/>
</Response>"""
    logger.info(f"[{CLIENT_ID}] Call from {from_number}")
    return Response(content=twiml, media_type="application/xml")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info(f"[{CLIENT_ID}] WebSocket accepted")
    call_start = time.time()

    try:
        start_data = websocket.iter_text()
        first_msg = await start_data.__anext__()
        second_msg = await start_data.__anext__()
        call_data = json.loads(second_msg)
        stream_sid = call_data["start"]["streamSid"]
        call_sid = call_data["start"].get("callSid", "")
        account_sid = call_data["start"].get("accountSid", TWILIO_ACCOUNT_SID)

        custom_params = call_data["start"].get("customParameters", {})
        from_number = custom_params.get("from_number", "unknown")

        await run_bot(websocket, stream_sid, call_sid, account_sid, from_number)

    except Exception as e:
        logger.error(f"[{CLIENT_ID}] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        call_duration = (time.time() - call_start) / 60.0
        daily_tracker.add_minutes(call_duration)
        logger.info(f"[{CLIENT_ID}] Call ended. Duration: {call_duration:.1f} min")


def check_availability(date_str, time_str):
    if not APPTS_PATH.exists():
        return True, []
    try:
        with open(APPTS_PATH, "r", encoding="utf-8") as f:
            existing = json.load(f)
    except Exception:
        return True, []
    conflicts = [a for a in existing if a.get("status") == "confirmed"
                 and a.get("date", "").lower() == date_str.lower()
                 and a.get("time", "").lower() == time_str.lower()]
    return len(conflicts) == 0, conflicts


def save_appointment(appointment):
    APPTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    existing = []
    if APPTS_PATH.exists():
        try:
            with open(APPTS_PATH, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            existing = []
    existing.append(appointment)
    with open(APPTS_PATH, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2)
    logger.info(f"[{CLIENT_ID}] Appointment: {appointment['name']} on {appointment['date']} at {appointment['time']}")


def send_sms(to_number, message):
    import requests
    try:
        resp = requests.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json",
            auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN),
            data={"From": TWILIO_PHONE, "To": to_number, "Body": message},
        )
        logger.info(f"[{CLIENT_ID}] SMS to {to_number}: {resp.status_code}")
        return resp.status_code == 201
    except Exception as e:
        logger.error(f"[{CLIENT_ID}] SMS failed: {e}")
        return False


def send_email(to_email, subject, body):
    smtp_user = CLIENT_CONFIG.get("smtp_user", "myfriendlyagent12@gmail.com")
    smtp_pass = CLIENT_CONFIG.get("smtp_password", "pdcvjroclstugncx")
    import smtplib
    from email.mime.text import MIMEText
    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = smtp_user
        msg["To"] = to_email
        with smtplib.SMTP("smtp.gmail.com", 587) as s:
            s.starttls()
            s.login(smtp_user, smtp_pass)
            s.send_message(msg)
        logger.info(f"[{CLIENT_ID}] Email sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"[{CLIENT_ID}] Email failed: {e}")
        return False


async def run_bot(websocket, stream_sid, call_sid="", account_sid="", from_number="unknown"):
    from pipecat.audio.vad.silero import SileroVADAnalyzer
    from pipecat.pipeline.pipeline import Pipeline
    from pipecat.pipeline.runner import PipelineRunner
    from pipecat.pipeline.task import PipelineParams, PipelineTask
    from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
    from pipecat.serializers.twilio import TwilioFrameSerializer
    from pipecat.services.cartesia.tts import CartesiaTTSService
    from pipecat.services.openai.llm import OpenAILLMService
    from pipecat.transports.websocket.fastapi import (
        FastAPIWebsocketParams,
        FastAPIWebsocketTransport,
    )

    transport = FastAPIWebsocketTransport(
        websocket=websocket,
        params=FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            add_wav_header=False,
            vad_enabled=True,
            vad_analyzer=SileroVADAnalyzer(),
            vad_audio_passthrough=True,
            serializer=TwilioFrameSerializer(
                stream_sid=stream_sid,
                call_sid=call_sid,
                account_sid=account_sid,
                auth_token=TWILIO_AUTH_TOKEN,
            ),
        ),
    )

    from pipecat.services.deepgram.stt import DeepgramSTTService
    stt = DeepgramSTTService(api_key=DEEPGRAM_KEY, audio_passthrough=True)

    llm = OpenAILLMService(
        api_key=GROQ_KEY,
        model="llama-3.3-70b-versatile",
        base_url="https://api.groq.com/openai/v1",
    )

    tts = CartesiaTTSService(api_key=CARTESIA_KEY, voice_id=CARTESIA_VOICE)

    # Build services list from config
    services_text = ""
    for svc in CLIENT_CONFIG.get("services", []):
        name = svc.get("name", "")
        dur = svc.get("duration_minutes", 30)
        price = svc.get("price", "")
        services_text += f"- {name} ({dur} min)"
        if price:
            services_text += f" — {price}"
        services_text += ". "

    # Build hours text
    hours_text = ""
    for day, hrs in CLIENT_CONFIG.get("business_hours", {}).items():
        if hrs == "closed":
            hours_text += f"{day.title()}: Closed. "
        elif isinstance(hrs, dict):
            hours_text += f"{day.title()}: {hrs['open']} - {hrs['close']}. "

    # Build staff text
    staff_text = ""
    for s in CLIENT_CONFIG.get("staff", []):
        staff_text += f"{s.get('name', '')} ({s.get('role', '')}). "

    personality = CLIENT_CONFIG.get("personality", {})
    greeting = personality.get("greeting", f"Hi there! Thanks for calling {BUSINESS_NAME}. How can I help you today?")
    tone = personality.get("tone", "warm and professional")

    # System prompt — fully customized per client
    system_prompt = (
        f"You are the AI receptionist for {BUSINESS_NAME}, a {CLIENT_CONFIG.get('business_type', 'business')}. "
        f"You sound exactly like a real human receptionist on the phone. Your tone is {tone}. "
        "RULES FOR HOW YOU SPEAK: "
        "Keep every response to 1-2 short sentences. "
        "Use contractions like I'm, we're, you'll, that's. "
        "NEVER read out phone numbers digit by digit. NEVER say numbers like three zero five. "
        "NEVER narrate what you're doing. Don't say things like let me check or I'm looking that up. Just do it silently and respond naturally. "
        "NEVER repeat information the caller already told you. "
        "When using tools, do NOT tell the caller you're using a tool or checking a system. Just pause briefly and respond with the result naturally. "
        "NEVER read back raw data, IDs, or technical info. "
        f"Your job: greet callers, book appointments, answer questions about {BUSINESS_NAME}. "
    )

    if services_text:
        system_prompt += f"Services offered: {services_text} "
    if hours_text:
        system_prompt += f"Business hours: {hours_text} "
    if staff_text:
        system_prompt += f"Staff: {staff_text} "

    # Knowledge — custom facts the business owner added
    knowledge = CLIENT_CONFIG.get("knowledge", [])
    if knowledge:
        system_prompt += "Important things to remember: "
        for item in knowledge:
            system_prompt += f"- {item} "


    system_prompt += (
        "To book: get their name, what service, and when. Check availability with check_time_slot, then book with book_appointment. "
        "After booking, ask if they want confirmation by text or email. "
        f"Caller's phone is {from_number}. Use send_confirmation_sms for text, send_confirmation_email for email. "
        "NEVER say underscores, function names, tool names, or any technical terms out loud. "
        "NEVER say words like send underscore confirmation or book underscore appointment. Those are internal tool names the caller should never hear. "
        "If you can't help, offer to take a message. Be warm, natural, and brief."
    )

    tools = [
        {
            "type": "function",
            "function": {
                "name": "book_appointment",
                "description": "Book an appointment. ALWAYS use this tool when the caller confirms they want to book.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Caller's name"},
                        "phone": {"type": "string", "description": "Caller's phone number"},
                        "date": {"type": "string", "description": "Appointment date"},
                        "time": {"type": "string", "description": "Appointment time"},
                        "service": {"type": "string", "description": "Service booked"},
                        "notes": {"type": "string", "description": "Any additional notes"},
                    },
                    "required": ["name", "date", "time", "service"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "check_time_slot",
                "description": "Check if a specific date and time is available for booking.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "date": {"type": "string", "description": "Date to check"},
                        "time": {"type": "string", "description": "Time to check"},
                    },
                    "required": ["date", "time"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "send_confirmation_sms",
                "description": "Send appointment confirmation via text message",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "phone_number": {"type": "string"},
                        "name": {"type": "string"},
                        "date": {"type": "string"},
                        "time": {"type": "string"},
                        "service": {"type": "string"},
                    },
                    "required": ["phone_number", "name", "date", "time", "service"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "send_confirmation_email",
                "description": "Send appointment confirmation via email",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "email": {"type": "string"},
                        "name": {"type": "string"},
                        "date": {"type": "string"},
                        "time": {"type": "string"},
                        "service": {"type": "string"},
                    },
                    "required": ["email", "name", "date", "time", "service"],
                },
            },
        },
    ]

    async def handle_send_sms(function_name, tool_call_id, arguments, llm, context, result_callback):
        args = arguments
        msg = (
            f"Appointment Confirmed!\n"
            f"Name: {args['name']}\n"
            f"Date: {args['date']}\n"
            f"Time: {args['time']}\n"
            f"Service: {args['service']}\n"
            f"See you then! - {BUSINESS_NAME}"
        )
        success = send_sms(args["phone_number"], msg)
        await result_callback({"status": "sent" if success else "failed"})

    async def handle_send_email(function_name, tool_call_id, arguments, llm, context, result_callback):
        args = arguments
        body = (
            f"Hi {args['name']},\n\n"
            f"Your appointment is confirmed!\n\n"
            f"Date: {args['date']}\n"
            f"Time: {args['time']}\n"
            f"Service: {args['service']}\n\n"
            f"See you then!\n- {BUSINESS_NAME}"
        )
        success = send_email(args["email"], f"Appointment Confirmation - {BUSINESS_NAME}", body)
        await result_callback({"status": "sent" if success else "failed"})

    async def handle_check_time_slot(function_name, tool_call_id, arguments, llm, context, result_callback):
        args = arguments
        available, conflicts = check_availability(args["date"], args["time"])
        if available:
            await result_callback({"available": True, "message": "That time slot is open!"})
        else:
            await result_callback({"available": False, "message": "That time is already booked. Please suggest a different time."})

    async def handle_book_appointment(function_name, tool_call_id, arguments, llm, context, result_callback):
        args = arguments
        available, conflicts = check_availability(args.get("date", ""), args.get("time", ""))
        if not available:
            await result_callback({"status": "conflict", "message": "That time slot is already booked."})
            return
        import uuid as _uuid
        appointment = {
            "id": str(_uuid.uuid4())[:8],
            "client_id": CLIENT_ID,
            "business_name": BUSINESS_NAME,
            "name": args.get("name", "Unknown"),
            "phone": args.get("phone", from_number),
            "date": args.get("date", ""),
            "time": args.get("time", ""),
            "service": args.get("service", ""),
            "notes": args.get("notes", ""),
            "status": "confirmed",
            "booked_at": datetime.now().isoformat(),
            "booked_by": "AI Receptionist",
        }
        save_appointment(appointment)
        await result_callback({"status": "booked", "id": appointment["id"]})

    llm.register_function("check_time_slot", handle_check_time_slot)
    llm.register_function("book_appointment", handle_book_appointment)
    llm.register_function("send_confirmation_sms", handle_send_sms)
    llm.register_function("send_confirmation_email", handle_send_email)

    messages = [{"role": "system", "content": system_prompt}]
    context = OpenAILLMContext(messages, tools)
    context_aggregator = llm.create_context_aggregator(context)

    pipeline = Pipeline([
        transport.input(),
        stt,
        context_aggregator.user(),
        llm,
        tts,
        transport.output(),
        context_aggregator.assistant(),
    ])

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            audio_in_sample_rate=8000,
            audio_out_sample_rate=8000,
            allow_interruptions=True,
        ),
    )

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info(f"[{CLIENT_ID}] Client connected — greeting")
        messages.append({"role": "system", "content": f"Greet the caller. Say something like: {greeting}"})
        await task.queue_frames([context_aggregator.user().get_context_frame()])

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info(f"[{CLIENT_ID}] Client disconnected")
        await task.cancel()

    logger.info(f"[{CLIENT_ID}] Starting pipeline...")
    runner = PipelineRunner(handle_sigint=False, force_gc=True)
    await runner.run(task)
    logger.info(f"[{CLIENT_ID}] Pipeline finished")


@app.get("/status")
async def status():
    return {
        "status": "running",
        "client_id": CLIENT_ID,
        "business_name": BUSINESS_NAME,
        "phone": TWILIO_PHONE,
        "port": PORT,
        "daily_limits": daily_tracker.get_status(),
    }

@app.get("/app")
async def appointments_app():
    """Mobile-friendly appointments dashboard for the client."""
    from fastapi.responses import HTMLResponse
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="{BUSINESS_NAME}">
<title>{BUSINESS_NAME} — Schedule</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, 'Segoe UI', sans-serif; background: #0f0f13; color: #e0e0e0; min-height: 100vh; padding-bottom: 80px; }}
.header {{ background: linear-gradient(135deg, #1a1a24, #252535); padding: 16px 20px; border-bottom: 1px solid #2a2a3a; display: flex; justify-content: space-between; align-items: center; }}
.header h1 {{ font-size: 1.2em; font-weight: 800; letter-spacing: 2px; background: linear-gradient(135deg, #ff6b35, #f7c948); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
.header .status {{ font-size: 0.7em; color: #22c55e; display: flex; align-items: center; gap: 5px; }}
.header .status .dot {{ width: 6px; height: 6px; border-radius: 50%; background: #22c55e; }}
.cost-bar {{ padding: 6px 16px; background: #151520; font-size: 0.72em; color: #666; display: flex; justify-content: space-between; border-bottom: 1px solid #1a1a24; }}
.day-tabs {{ display: flex; overflow-x: auto; padding: 10px 12px; gap: 6px; background: #111118; border-bottom: 1px solid #2a2a3a; -webkit-overflow-scrolling: touch; }}
.day-tabs::-webkit-scrollbar {{ display: none; }}
.day-tab {{ flex-shrink: 0; padding: 8px 14px; border-radius: 8px; background: #1a1a24; border: 1px solid #2a2a3a; cursor: pointer; text-align: center; min-width: 65px; transition: all 0.2s; }}
.day-tab.active {{ background: linear-gradient(135deg, rgba(255,107,53,0.15), rgba(247,201,72,0.15)); border-color: #f7c948; }}
.day-tab.today {{ border-color: #ff6b35; }}
.day-tab .day-name {{ font-size: 0.65em; color: #888; text-transform: uppercase; letter-spacing: 1px; }}
.day-tab.active .day-name {{ color: #f7c948; }}
.day-tab .day-num {{ font-size: 1.1em; font-weight: 800; color: #ccc; margin-top: 2px; }}
.day-tab.active .day-num {{ color: #fff; }}
.day-tab .day-count {{ font-size: 0.6em; color: #555; margin-top: 2px; }}
.day-tab.active .day-count {{ color: #f7c948; }}
.day-tab.has-appts .day-count {{ color: #22c55e; }}
.stats {{ display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 8px; padding: 12px 16px; }}
.stat {{ background: #1a1a24; border: 1px solid #2a2a3a; border-radius: 8px; padding: 10px; text-align: center; }}
.stat .num {{ font-size: 1.3em; font-weight: 800; color: #f7c948; }}
.stat .lbl {{ font-size: 0.6em; color: #888; margin-top: 2px; }}
.section {{ padding: 8px 16px 16px; }}
.section-title {{ font-size: 0.85em; font-weight: 700; color: #aaa; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; }}
.section-title .date-label {{ font-size: 0.85em; color: #f7c948; }}
.card {{ background: #1a1a24; border: 1px solid #2a2a3a; border-radius: 10px; padding: 14px; margin-bottom: 8px; }}
.card.today-card {{ border-left: 3px solid #ff6b35; }}
.card .top {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }}
.card .name {{ font-weight: 700; font-size: 0.92em; }}
.card .time-badge {{ font-size: 0.75em; padding: 3px 10px; border-radius: 6px; font-weight: 700; background: rgba(59,130,246,0.15); color: #3b82f6; }}
.card .badge {{ font-size: 0.6em; padding: 2px 7px; border-radius: 5px; font-weight: 700; text-transform: uppercase; }}
.badge.confirmed {{ background: rgba(34,197,94,0.12); color: #22c55e; }}
.card .details {{ font-size: 0.78em; color: #999; line-height: 1.7; }}
.card .details span {{ color: #ccc; }}
.empty {{ text-align: center; padding: 30px; color: #444; font-size: 0.82em; }}
.refresh {{ position: fixed; bottom: 20px; right: 20px; width: 48px; height: 48px; border-radius: 50%; background: linear-gradient(135deg, #ff6b35, #f7c948); border: none; color: #fff; font-size: 1.2em; cursor: pointer; box-shadow: 0 4px 15px rgba(255,107,53,0.3); z-index: 10; }}
</style>
</head>
<body>
<div class="header">
  <h1>{BUSINESS_NAME.upper()}</h1>
  <div class="status"><div class="dot"></div> Live</div>
</div>
<div class="cost-bar">
  <span id="costInfo">Loading...</span>
  <span id="callInfo"></span>
</div>
<div class="day-tabs" id="dayTabs"></div>
<div class="stats">
  <div class="stat"><div class="num" id="todayCount">-</div><div class="lbl">Today</div></div>
  <div class="stat"><div class="num" id="tomorrowCount">-</div><div class="lbl">Tomorrow</div></div>
  <div class="stat"><div class="num" id="weekCount">-</div><div class="lbl">This Week</div></div>
  <div class="stat"><div class="num" id="totalCount">-</div><div class="lbl">All Time</div></div>
</div>
<div class="section">
  <div class="section-title">
    <span id="sectionLabel">Today's Schedule</span>
    <span class="date-label" id="dateLabel"></span>
  </div>
  <div id="apptList"><div class="empty">Loading...</div></div>
</div>
<button class="refresh" onclick="loadData()">&#8635;</button>
<script>
let allAppts = [];
let selectedDate = null;

function getWeekDates() {{
  const dates = [];
  const now = new Date();
  for (let i = 0; i < 7; i++) {{ const d = new Date(now); d.setDate(now.getDate() + i); dates.push(d); }}
  return dates;
}}
function dateStr(d) {{ return d.toISOString().split('T')[0]; }}
function matchDate(apptDate, targetDate) {{
  if (!apptDate) return false;
  const target = targetDate.toLowerCase(), appt = apptDate.toLowerCase();
  if (appt === target) return true;
  if (appt.includes('today') && target === dateStr(new Date())) return true;
  if (appt.includes('tomorrow')) {{ const tom = new Date(); tom.setDate(tom.getDate()+1); return target === dateStr(tom); }}
  try {{ const parsed = new Date(appt); if (!isNaN(parsed)) return dateStr(parsed) === target; }} catch(e) {{}}
  return appt.includes(target);
}}
function countForDate(date) {{ const ds = dateStr(date); return allAppts.filter(a => a.status === 'confirmed' && matchDate(a.date, ds)).length; }}

function renderTabs() {{
  const tabs = document.getElementById('dayTabs');
  const days = getWeekDates();
  const dayNames = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
  const todayStr = dateStr(new Date());
  tabs.innerHTML = days.map((d, i) => {{
    const ds = dateStr(d), count = countForDate(d), isToday = ds === todayStr, isActive = ds === selectedDate, hasAppts = count > 0;
    return '<div class="day-tab' + (isActive ? ' active' : '') + (isToday ? ' today' : '') + (hasAppts ? ' has-appts' : '') + '" onclick="selectDay(\\''+ds+'\\')"><div class="day-name">' + (isToday ? 'Today' : (i===1 ? 'Tmrw' : dayNames[d.getDay()])) + '</div><div class="day-num">' + d.getDate() + '</div><div class="day-count">' + (count > 0 ? count + ' appt' + (count>1?'s':'') : '-') + '</div></div>';
  }}).join('');
}}

function selectDay(ds) {{ selectedDate = ds; renderTabs(); renderAppts(); }}

function renderAppts() {{
  const container = document.getElementById('apptList');
  const todayStr = dateStr(new Date());
  const isToday = selectedDate === todayStr;
  const filtered = allAppts.filter(a => a.status === 'confirmed' && matchDate(a.date, selectedDate));
  const d = new Date(selectedDate + 'T12:00:00');
  document.getElementById('dateLabel').textContent = d.toLocaleDateString('en-US', {{ weekday: 'long', month: 'long', day: 'numeric' }});
  document.getElementById('sectionLabel').textContent = isToday ? "Today's Schedule" : d.toLocaleDateString('en-US', {{weekday: 'long'}}) + "'s Schedule";
  if (filtered.length === 0) {{
    container.innerHTML = '<div class="empty">' + (isToday ? 'No appointments today.' : 'No appointments for this day.') + '</div>';
    return;
  }}
  container.innerHTML = filtered.map(a => '<div class="card' + (isToday ? ' today-card' : '') + '"><div class="top"><span class="name">' + (a.name||'Unknown') + '</span><span class="time-badge">' + (a.time||'TBD') + '</span></div><div class="top" style="margin-bottom:0"><span style="font-size:0.78em;color:#999">' + (a.service||'') + '</span><span class="badge confirmed">CONFIRMED</span></div><div class="details" style="margin-top:6px">' + (a.phone ? '<div>&#128222; <span>' + a.phone + '</span></div>' : '') + (a.notes ? '<div>&#128221; <span>' + a.notes + '</span></div>' : '') + '</div></div>').join('');
}}

async function loadData() {{
  try {{
    const [appts, status] = await Promise.all([fetch('/appointments').then(r => r.json()), fetch('/status').then(r => r.json())]);
    allAppts = appts.appointments || [];
    if (!selectedDate) selectedDate = dateStr(new Date());
    const todayStr = dateStr(new Date()), tomStr = dateStr(new Date(Date.now() + 86400000));
    document.getElementById('todayCount').textContent = allAppts.filter(a => a.status==='confirmed' && matchDate(a.date, todayStr)).length;
    document.getElementById('tomorrowCount').textContent = allAppts.filter(a => a.status==='confirmed' && matchDate(a.date, tomStr)).length;
    let weekCount = 0; getWeekDates().forEach(d => {{ weekCount += countForDate(d); }});
    document.getElementById('weekCount').textContent = weekCount;
    document.getElementById('totalCount').textContent = allAppts.length;
    if (status.daily_limits) {{
      const dl = status.daily_limits;
      document.getElementById('costInfo').textContent = 'Today: $' + dl.cost_today.toFixed(2) + ' / $' + dl.daily_cap + ' cap';
      document.getElementById('callInfo').textContent = dl.calls_today + ' calls | ' + dl.minutes_today + ' min';
    }}
    renderTabs(); renderAppts();
  }} catch(e) {{
    document.getElementById('apptList').innerHTML = '<div class="empty">Could not load. Is the server running?</div>';
  }}
}}
loadData();
setInterval(loadData, 15000);
</script>
</body>
</html>"""
    return HTMLResponse(content=html)

@app.get("/appointments")
async def get_appointments():
    if APPTS_PATH.exists():
        with open(APPTS_PATH, "r", encoding="utf-8") as f:
            appts = json.load(f)
    else:
        appts = []
    return {"client_id": CLIENT_ID, "total": len(appts), "appointments": appts}

@app.get("/appointments/today")
async def get_today_appointments():
    if APPTS_PATH.exists():
        with open(APPTS_PATH, "r", encoding="utf-8") as f:
            appts = json.load(f)
    else:
        appts = []
    today = str(date.today())
    today_appts = [a for a in appts if today in a.get("date", "")]
    return {"client_id": CLIENT_ID, "date": today, "total": len(today_appts), "appointments": today_appts}


if __name__ == "__main__":
    print()
    print("=" * 55)
    print(f"  JANOVUM AI RECEPTIONIST — {BUSINESS_NAME.upper()}")
    print("=" * 55)
    print(f"  Client ID: {CLIENT_ID}")
    print(f"  Phone:     {TWILIO_PHONE}")
    print(f"  Port:      {PORT}")
    print(f"  Tunnel:    {PUBLIC_URL}")
    print("=" * 55)
    print()
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")
