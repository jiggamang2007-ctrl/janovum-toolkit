"""
Janovum Platform — AI Receptionist Voice Pipeline
Production-ready Pipecat pipeline for handling inbound phone calls via Telnyx.

Stack:
  - Telnyx WebSocket transport (telephony)
  - Cartesia Sonic TTS (40ms latency)
  - faster-whisper STT (local, free)
  - Pollinations LLM (free, OpenAI-compatible) for the brain
  - Pipecat for pipeline orchestration
  - Silero VAD for voice activity detection

Features:
  - Barge-in support (stop TTS when caller speaks)
  - Tool calling: book_appointment, check_availability, take_message, end_call
  - Appointment booking with JSON persistence
  - Message taking with JSON persistence
  - Email notifications on appointment booking
  - Audio caching for greeting message
  - Integration with receptionist_guards for call protection
"""

import os
import json
import asyncio
import hashlib
import smtplib
import uuid
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from loguru import logger

# Pipecat imports
from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import (
    EndFrame,
    LLMRunFrame,
    TTSSpeakFrame,
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.serializers.twilio import TwilioFrameSerializer
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.services.whisper.stt import WhisperSTTService
from pipecat.services.llm_service import FunctionCallParams
from pipecat.transports.websocket.fastapi import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)

# Local imports
from core.receptionist_config import load_config, generate_system_prompt
from core.receptionist_guards import get_guards

# Paths
PLATFORM_DIR = Path(__file__).parent.parent
DATA_DIR = PLATFORM_DIR / "data"
APPOINTMENTS_PATH = DATA_DIR / "appointments.json"

# Pre-load Whisper model at import time so it's ready when calls come in
logger.info("[receptionist] Pre-loading Whisper model...")
_WHISPER_MODEL = None
try:
    from faster_whisper import WhisperModel
    _WHISPER_MODEL = WhisperModel("base", device="cpu", compute_type="int8")
    logger.info("[receptionist] Whisper model loaded and ready")
except Exception as e:
    logger.error(f"[receptionist] Failed to pre-load Whisper: {e}")
MESSAGES_PATH = DATA_DIR / "messages.json"
AUDIO_CACHE_DIR = DATA_DIR / "audio_cache"


# ---------------------------------------------------------------------------
# Data persistence helpers
# ---------------------------------------------------------------------------

def _ensure_data_dirs():
    """Create data directories if they don't exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    AUDIO_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _load_json(path: Path) -> list:
    """Load a JSON array file, returning empty list if missing/corrupt."""
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except (json.JSONDecodeError, IOError):
            pass
    return []


def _save_json(path: Path, data: list):
    """Save data to a JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


# ---------------------------------------------------------------------------
# Tool function implementations
# ---------------------------------------------------------------------------

async def _book_appointment(params: FunctionCallParams):
    """
    Book an appointment. Called by the LLM via tool calling.
    Expected arguments: caller_name, phone_number, date, time, service, notes (optional)
    """
    args = params.arguments
    caller_name = args.get("caller_name", "Unknown")
    phone_number = args.get("phone_number", "Unknown")
    appt_date = args.get("date", "")
    appt_time = args.get("time", "")
    service = args.get("service", "General")
    notes = args.get("notes", "")

    config = load_config()

    # Validate we have required fields
    if not appt_date or not appt_time:
        await params.result_callback({
            "success": False,
            "message": "I need both a date and time to book the appointment. Could you provide those?"
        })
        return

    # Create appointment record
    appointment = {
        "id": str(uuid.uuid4())[:8],
        "caller_name": caller_name,
        "phone_number": phone_number,
        "date": appt_date,
        "time": appt_time,
        "service": service,
        "notes": notes,
        "booked_at": datetime.now().isoformat(),
        "status": "confirmed",
    }

    # Save to appointments.json
    appointments = _load_json(APPOINTMENTS_PATH)
    appointments.append(appointment)
    _save_json(APPOINTMENTS_PATH, appointments)

    logger.info(f"[receptionist] Appointment booked: {appointment}")

    # Send email notification
    _send_appointment_email(appointment, config)

    await params.result_callback({
        "success": True,
        "message": (
            f"I've booked the appointment for {caller_name} on {appt_date} at {appt_time} "
            f"for {service}. Confirmation number is {appointment['id']}."
        ),
        "appointment_id": appointment["id"],
    })


async def _check_availability(params: FunctionCallParams):
    """
    Check if a specific date/time slot is available.
    Expected arguments: date, time
    """
    args = params.arguments
    check_date = args.get("date", "")
    check_time = args.get("time", "")

    if not check_date:
        await params.result_callback({
            "available": False,
            "message": "I need a date to check availability. What day were you thinking?"
        })
        return

    # Load existing appointments and check for conflicts
    appointments = _load_json(APPOINTMENTS_PATH)
    conflicts = [
        a for a in appointments
        if a.get("date") == check_date
        and a.get("time") == check_time
        and a.get("status") != "cancelled"
    ]

    config = load_config()

    if conflicts:
        # Find nearby available slots
        await params.result_callback({
            "available": False,
            "message": (
                f"That slot on {check_date} at {check_time} is already booked. "
                "Would you like to try a different time?"
            ),
        })
    else:
        await params.result_callback({
            "available": True,
            "message": f"Great news! {check_date} at {check_time} is available. Want me to book it?",
        })


async def _take_message(params: FunctionCallParams):
    """
    Take a message from the caller.
    Expected arguments: caller_name, phone_number, message
    """
    args = params.arguments
    caller_name = args.get("caller_name", "Unknown")
    phone_number = args.get("phone_number", "Unknown")
    message_text = args.get("message", "")

    if not message_text:
        await params.result_callback({
            "success": False,
            "message": "I didn't catch the message. Could you repeat what you'd like me to pass along?"
        })
        return

    message_record = {
        "id": str(uuid.uuid4())[:8],
        "caller_name": caller_name,
        "phone_number": phone_number,
        "message": message_text,
        "received_at": datetime.now().isoformat(),
        "read": False,
    }

    # Save to messages.json
    messages = _load_json(MESSAGES_PATH)
    messages.append(message_record)
    _save_json(MESSAGES_PATH, messages)

    logger.info(f"[receptionist] Message taken: {message_record}")

    # Send email notification
    config = load_config()
    _send_message_email(message_record, config)

    await params.result_callback({
        "success": True,
        "message": (
            f"Got it! I've taken down the message from {caller_name}. "
            "Someone will get back to you as soon as possible."
        ),
    })


async def _end_call(params: FunctionCallParams):
    """
    End the call politely.
    """
    config = load_config()
    farewell = config.get("personality", {}).get("farewell", "Thanks for calling! Have a great day.")

    await params.result_callback({
        "success": True,
        "message": farewell,
        "action": "end_call",
    })


# ---------------------------------------------------------------------------
# Email notification helpers
# ---------------------------------------------------------------------------

def _send_appointment_email(appointment: dict, config: dict):
    """Send email notification when an appointment is booked."""
    notif = config.get("notifications", {})
    if not notif.get("email_enabled"):
        return

    try:
        subject = f"New Appointment: {appointment['caller_name']} on {appointment['date']}"
        body = f"""New appointment booked via AI Receptionist:

Caller: {appointment['caller_name']}
Phone: {appointment['phone_number']}
Date: {appointment['date']}
Time: {appointment['time']}
Service: {appointment['service']}
Notes: {appointment.get('notes', 'None')}
Confirmation #: {appointment['id']}
Booked at: {appointment['booked_at']}
"""
        _send_email(subject, body, notif)
        logger.info(f"[receptionist] Appointment email sent for {appointment['id']}")
    except Exception as e:
        logger.error(f"[receptionist] Failed to send appointment email: {e}")


def _send_message_email(message: dict, config: dict):
    """Send email notification when a message is taken."""
    notif = config.get("notifications", {})
    if not notif.get("email_enabled"):
        return

    try:
        subject = f"New Message from {message['caller_name']}"
        body = f"""New message taken by AI Receptionist:

From: {message['caller_name']}
Phone: {message['phone_number']}
Message: {message['message']}
Received at: {message['received_at']}
"""
        _send_email(subject, body, notif)
        logger.info(f"[receptionist] Message email sent for {message['id']}")
    except Exception as e:
        logger.error(f"[receptionist] Failed to send message email: {e}")


def _send_email(subject: str, body: str, notif_config: dict):
    """Send an email via SMTP."""
    msg = MIMEMultipart()
    msg["From"] = notif_config.get("email_from", "")
    msg["To"] = notif_config.get("email_to", "")
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    server = smtplib.SMTP(
        notif_config.get("smtp_server", "smtp.gmail.com"),
        notif_config.get("smtp_port", 587),
    )
    server.starttls()
    server.login(
        notif_config.get("smtp_user", ""),
        notif_config.get("smtp_password", ""),
    )
    server.send_message(msg)
    server.quit()


# ---------------------------------------------------------------------------
# Tool schema definitions for the LLM
# ---------------------------------------------------------------------------

RECEPTIONIST_TOOLS = ToolsSchema(
    standard_tools=[
        FunctionSchema(
            name="book_appointment",
            description=(
                "Book an appointment for the caller. Use this when the caller wants to "
                "schedule a visit or meeting. You MUST confirm all details with the caller "
                "before calling this function."
            ),
            properties={
                "caller_name": {
                    "type": "string",
                    "description": "The caller's full name",
                },
                "phone_number": {
                    "type": "string",
                    "description": "The caller's phone number for callback",
                },
                "date": {
                    "type": "string",
                    "description": "The appointment date (e.g. 'March 15, 2026' or '2026-03-15')",
                },
                "time": {
                    "type": "string",
                    "description": "The appointment time (e.g. '2:00 PM' or '14:00')",
                },
                "service": {
                    "type": "string",
                    "description": "The service or type of appointment",
                },
                "notes": {
                    "type": "string",
                    "description": "Any additional notes from the caller",
                },
            },
            required=["caller_name", "phone_number", "date", "time", "service"],
        ),
        FunctionSchema(
            name="check_availability",
            description=(
                "Check if a specific date and time slot is available for booking. "
                "Use this before booking to verify the slot is open."
            ),
            properties={
                "date": {
                    "type": "string",
                    "description": "The date to check (e.g. 'March 15, 2026')",
                },
                "time": {
                    "type": "string",
                    "description": "The time to check (e.g. '2:00 PM')",
                },
            },
            required=["date"],
        ),
        FunctionSchema(
            name="take_message",
            description=(
                "Take a message from the caller to be passed along to the business. "
                "Use this when you can't directly help and need someone to call back."
            ),
            properties={
                "caller_name": {
                    "type": "string",
                    "description": "The caller's name",
                },
                "phone_number": {
                    "type": "string",
                    "description": "The caller's phone number",
                },
                "message": {
                    "type": "string",
                    "description": "The message content",
                },
            },
            required=["caller_name", "phone_number", "message"],
        ),
        FunctionSchema(
            name="end_call",
            description=(
                "End the phone call. Use this when the conversation is naturally "
                "concluding and you've said goodbye."
            ),
            properties={},
            required=[],
        ),
    ]
)


# ---------------------------------------------------------------------------
# Main pipeline builder
# ---------------------------------------------------------------------------

async def create_receptionist_pipeline(
    websocket,
    call_data: dict,
    call_id: str,
):
    """
    Create and run a full receptionist pipeline for an inbound call.

    Args:
        websocket: The FastAPI WebSocket connection from Telnyx
        call_data: Parsed call data with stream_id, call_control_id, encodings, from/to
        call_id: Unique identifier for this call
    """
    _ensure_data_dirs()
    config = load_config()
    guards = get_guards()

    from_number = call_data.get("from", "unknown")
    logger.info(f"[receptionist] Creating pipeline for call {call_id} from {from_number}")

    # --- Twilio serializer ---
    serializer = TwilioFrameSerializer(
        stream_sid=call_data.get("twilio_stream_sid", call_data.get("stream_sid", "")),
        call_sid=call_data.get("twilio_call_sid", call_data.get("call_sid", "")),
        account_sid=call_data.get("twilio_account_sid", "AC2d50767d64e32c3b57b56a57c11c3849"),
        auth_token=call_data.get("twilio_auth_token", "94c74007b62652b5b14c7bea70a5792c"),
    )

    # --- Transport ---
    transport = FastAPIWebsocketTransport(
        websocket=websocket,
        params=FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            add_wav_header=False,
            serializer=serializer,
        ),
    )

    # --- STT (faster-whisper, local) ---
    stt = WhisperSTTService(
        model="base",
        device="cpu",
        compute_type="int8",
        no_speech_prob=0.4,
    )

    # --- LLM (Pollinations, free, OpenAI-compatible) ---
    system_prompt = generate_system_prompt(config)
    llm = OpenAILLMService(
        api_key="pollinations",  # Pollinations doesn't need a real key
        model="openai",
        base_url="https://text.pollinations.ai/openai/v1",
        settings=OpenAILLMService.Settings(
            system_instruction=system_prompt,
        ),
    )

    # Register tool functions
    llm.register_function("book_appointment", _book_appointment)
    llm.register_function("check_availability", _check_availability)
    llm.register_function("take_message", _take_message)
    llm.register_function("end_call", _end_call)

    # --- TTS (Cartesia Sonic, 40ms latency) ---
    cartesia_config = config.get("cartesia", {})
    tts = CartesiaTTSService(
        api_key=cartesia_config.get("api_key", ""),
        settings=CartesiaTTSService.Settings(
            voice=cartesia_config.get("voice_id", ""),
        ),
        sample_rate=8000,  # telephony standard
        encoding="pcm_mulaw",
    )

    # --- LLM Context with tools ---
    context = LLMContext(tools=RECEPTIONIST_TOOLS)
    user_aggregator, assistant_aggregator = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(
            vad_analyzer=SileroVADAnalyzer(),
        ),
    )

    # --- Pipeline ---
    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            user_aggregator,
            llm,
            tts,
            transport.output(),
            assistant_aggregator,
        ]
    )

    # --- Task ---
    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            audio_in_sample_rate=8000,
            audio_out_sample_rate=8000,
            enable_metrics=True,
        ),
    )

    # Call is already registered by the server — just update with pipeline task reference
    logger.info(f"[receptionist] Pipeline ready for call {call_id}")

    # --- Cancel callback for guard monitors ---
    async def cancel_call(reason: str):
        logger.info(f"[receptionist] Cancelling call {call_id}, reason: {reason}")
        if reason == "silence":
            # Say something before hanging up
            await task.queue_frames([
                TTSSpeakFrame("I haven't heard anything for a bit, so I'm going to hang up. Feel free to call back anytime!"),
            ])
            await asyncio.sleep(3)  # let the TTS play
        elif reason == "max_duration":
            await task.queue_frames([
                TTSSpeakFrame("We've been on the call for a while. I'm going to let you go, but feel free to call back if you need anything else!"),
            ])
            await asyncio.sleep(4)
        await task.queue_frames([EndFrame()])

    # --- Event handlers ---
    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info(f"[receptionist] Client connected: call {call_id}")
        # Send the greeting
        greeting = config.get("personality", {}).get(
            "greeting",
            "Hi there! Thanks for calling. How can I help you today?"
        ).replace("{business_name}", config.get("business_name", "our business"))

        context.add_message({"role": "system", "content": system_prompt})
        context.add_message({"role": "user", "content": "The caller just connected. Greet them warmly."})
        await task.queue_frames([LLMRunFrame()])

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info(f"[receptionist] Client disconnected: call {call_id}")
        await guards.unregister_call(call_id, completed_normally=True)
        await task.cancel()

    # --- VAD event for guard silence tracking ---
    @user_aggregator.event_handler("on_voice_started")
    async def on_voice_started(aggregator):
        guards.update_voice_activity(call_id)

    @user_aggregator.event_handler("on_voice_stopped")
    async def on_voice_stopped(aggregator):
        guards.update_voice_activity(call_id)

    # --- Handle end_call tool result ---
    @llm.event_handler("on_function_calls_started")
    async def on_function_calls_started(service, function_calls):
        """Provide filler speech while tool calls execute."""
        # Only add filler for longer operations
        for fc in function_calls:
            if fc.function_name in ("book_appointment", "check_availability"):
                await tts.queue_frame(TTSSpeakFrame("Just a moment while I look that up for you."))

    # --- Run ---
    runner = PipelineRunner(handle_sigint=False)

    # Start the guard monitor in background
    monitor_task = asyncio.create_task(
        guards.start_call_monitor(call_id, cancel_call)
    )

    try:
        await runner.run(task)
    except Exception as e:
        logger.error(f"[receptionist] Pipeline error for call {call_id}: {e}")
    finally:
        # Cleanup
        await guards.unregister_call(call_id, completed_normally=True)
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass
        logger.info(f"[receptionist] Pipeline finished for call {call_id}")
