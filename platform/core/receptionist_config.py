"""
Janovum Platform — AI Receptionist Configuration
Loads business config and generates the system prompt for the receptionist LLM.
"""

import json
from pathlib import Path
from datetime import datetime, date
from typing import Optional

PLATFORM_DIR = Path(__file__).parent.parent
CONFIG_PATH = PLATFORM_DIR / "data" / "receptionist_config.json"

# Default config used if file doesn't exist
DEFAULT_CONFIG = {
    "business_name": "Our Business",
    "business_type": "General",
    "phone_number": "",
    "timezone": "America/New_York",
    "business_hours": {
        "monday": {"open": "09:00", "close": "17:00"},
        "tuesday": {"open": "09:00", "close": "17:00"},
        "wednesday": {"open": "09:00", "close": "17:00"},
        "thursday": {"open": "09:00", "close": "17:00"},
        "friday": {"open": "09:00", "close": "17:00"},
        "saturday": "closed",
        "sunday": "closed",
    },
    "services": [],
    "staff": [],
    "personality": {
        "tone": "warm and professional",
        "speaking_style": "conversational",
        "greeting": "Hi there! Thanks for calling. How can I help you today?",
        "farewell": "Thanks for calling! Have a great day.",
        "hold_message": "Just a moment while I look that up.",
        "voicemail_prompt": "Please leave a message after the tone.",
    },
    "appointment_rules": {
        "min_notice_hours": 2,
        "max_advance_days": 30,
        "slot_duration_minutes": 30,
    },
    "telnyx": {"api_key": "", "phone_number": ""},
    "cartesia": {"api_key": "", "voice_id": ""},
    "notifications": {
        "email_enabled": False,
        "email_to": "",
        "email_from": "",
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "smtp_user": "",
        "smtp_password": "",
    },
}


def load_config() -> dict:
    """Load the receptionist config from JSON, falling back to defaults."""
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                config = json.load(f)
            # Merge with defaults so missing keys get filled in
            merged = {**DEFAULT_CONFIG, **config}
            return merged
        except (json.JSONDecodeError, IOError) as e:
            print(f"[receptionist_config] Error loading config: {e}, using defaults")
    return DEFAULT_CONFIG.copy()


def save_config(config: dict) -> bool:
    """Save config back to JSON file."""
    try:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        return True
    except IOError as e:
        print(f"[receptionist_config] Error saving config: {e}")
        return False


def get_current_day_hours(config: dict) -> Optional[dict]:
    """Get today's business hours. Returns None if closed today."""
    day_name = date.today().strftime("%A").lower()
    hours = config.get("business_hours", {}).get(day_name, "closed")
    if hours == "closed":
        return None
    return hours


def is_business_open(config: dict) -> bool:
    """Check if the business is currently open."""
    hours = get_current_day_hours(config)
    if not hours:
        return False
    now = datetime.now().strftime("%H:%M")
    return hours["open"] <= now <= hours["close"]


def format_hours_for_prompt(config: dict) -> str:
    """Format business hours into a readable string for the system prompt."""
    hours = config.get("business_hours", {})
    lines = []
    for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
        h = hours.get(day, "closed")
        if h == "closed":
            lines.append(f"  {day.capitalize()}: Closed")
        else:
            lines.append(f"  {day.capitalize()}: {h['open']} - {h['close']}")
    return "\n".join(lines)


def format_services_for_prompt(config: dict) -> str:
    """Format services into a readable string for the system prompt."""
    services = config.get("services", [])
    if not services:
        return "  No specific services listed."
    lines = []
    for svc in services:
        line = f"  - {svc['name']}: {svc.get('description', '')} ({svc.get('duration_minutes', 30)} min, {svc.get('price', 'Contact for pricing')})"
        lines.append(line)
    return "\n".join(lines)


def format_staff_for_prompt(config: dict) -> str:
    """Format staff into a readable string for the system prompt."""
    staff = config.get("staff", [])
    if not staff:
        return "  No specific staff listed."
    lines = []
    for person in staff:
        avail = "available for appointments" if person.get("available_for_appointments") else "not taking appointments"
        lines.append(f"  - {person['name']} ({person.get('role', 'Staff')}) — {avail}")
    return "\n".join(lines)


def generate_system_prompt(config: dict) -> str:
    """
    Generate the full system prompt for the receptionist LLM.
    This is the core personality and knowledge of the AI receptionist.
    """
    business_name = config.get("business_name", "Our Business")
    business_type = config.get("business_type", "Business")
    personality = config.get("personality", {})
    tone = personality.get("tone", "warm and professional")
    speaking_style = personality.get("speaking_style", "conversational")
    currently_open = is_business_open(config)
    open_status = "currently OPEN" if currently_open else "currently CLOSED"

    now = datetime.now()
    current_time = now.strftime("%I:%M %p")
    current_day = now.strftime("%A")
    current_date = now.strftime("%B %d, %Y")

    prompt = f"""You are the AI receptionist for {business_name}, a {business_type}. You answer phone calls and help callers with appointments, questions, and messages.

CURRENT STATUS:
  Today is {current_day}, {current_date}. The time is {current_time}.
  The business is {open_status}.

YOUR PERSONALITY:
  Tone: {tone}
  Style: {speaking_style}
  You sound like a REAL person on the phone — not robotic. Use contractions (I'm, we're, you'll, etc.).
  Keep responses SHORT — this is a phone call, not an essay. 1-3 sentences max per turn.
  Never use special characters, markdown, bullet points, or formatting — your words will be spoken aloud.
  Never say "as an AI" or reveal you are artificial unless directly asked.

BUSINESS HOURS:
{format_hours_for_prompt(config)}

SERVICES OFFERED:
{format_services_for_prompt(config)}

STAFF:
{format_staff_for_prompt(config)}

YOUR CAPABILITIES (use these tool functions when appropriate):
  1. book_appointment — Book an appointment for the caller. Collect: caller name, phone number, preferred date/time, service type, and any notes. ALWAYS confirm all details before booking.
  2. check_availability — Check if a specific date/time slot is available.
  3. take_message — Take a message when you can't help directly. Collect: caller name, phone number, message content.
  4. end_call — End the call politely when the conversation is done.

CALL FLOW:
  1. Greet the caller warmly.
  2. Ask how you can help.
  3. If they want an appointment: ask what service, when they'd like to come in, get their name and number. Confirm everything, then book it.
  4. If they have a question you can answer from the info above, answer it.
  5. If they have a question you CAN'T answer, offer to take a message for someone to call them back.
  6. If the business is closed, let them know the hours and offer to book an appointment or take a message.
  7. When done, say goodbye warmly and end the call.

IMPORTANT RULES:
  - NEVER make up information about the business that isn't listed above.
  - If you don't know something, say "I'm not sure about that, but I can take a message and have someone get back to you."
  - Don't book appointments outside business hours.
  - Don't book appointments with less than {config.get('appointment_rules', {}).get('min_notice_hours', 2)} hours notice.
  - Keep the conversation flowing naturally — don't interrogate the caller with rapid-fire questions.
  - If the caller is rude or abusive, stay professional and offer to take a message or end the call."""

    return prompt
