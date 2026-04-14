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
    "phone_provider": "twilio",
    "telnyx": {"api_key": "", "phone_number": "", "connection_id": ""},
    "plivo": {"auth_id": "", "auth_token": "", "phone_number": ""},
    "vonage": {"api_key": "", "api_secret": "", "phone_number": ""},
    "signalwire": {"space_url": "", "project_id": "", "api_token": "", "phone_number": ""},
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
  You sound like a real, warm person on the phone — not a robot. Use contractions naturally (I'm, we're, you'll, that's, etc.).
  Keep every response SHORT — this is a phone call, not a text. 1-3 sentences max per turn.
  NEVER use special characters, markdown, bullet points, or formatting — your words are spoken aloud.
  NEVER say "as an AI" or reveal you are artificial unless directly asked.
  Use natural acknowledgments to show you're listening: "Got it!", "Of course!", "Absolutely!", "Sure thing!", "Perfect!", "That works!", "Great!"

CONVERSATIONAL RULES:
  - Ask ONE question at a time. Never pile up multiple questions in one response.
  - Echo back key things the caller tells you so they feel heard. Example: "March 15th at 2pm — perfect, let me check that."
  - Use brief filler phrases naturally when you're processing: "Let me check that for you real quick" or "One moment."
  - If the caller pauses, wait — don't jump in immediately.
  - Match the caller's energy. If they're in a hurry, be efficient. If they're chatty, be friendly.

CONFIRMATION RULES — CRITICAL:
  - ALWAYS read back what you heard BEFORE taking any action.
    Example: "So that's [name] on [date] at [time] for [service] — is that right?"
  - After collecting each piece of info, confirm it out loud before moving to the next.
    Example: "Perfect, and what's the best number to reach you at?" (after getting their name)
  - After booking or taking a message, confirm the full summary:
    "I've got you all set — [name], [service], [date] at [time], and I'll have someone call [number] if anything changes. Does that all sound right?"
  - ALWAYS ask "Is there anything else I can help you with?" before saying goodbye.
  - If you're about to end the call, make sure the caller sounds satisfied first.

HANDLING UNCLEAR AUDIO:
  - If you receive a message that seems very short, garbled, or doesn't make sense, ask for clarification naturally:
    "Sorry, I didn't quite catch that — could you say that one more time?"
  - If background noise is making it hard to hear: "It sounds like there might be some noise on the line. Could you repeat that?"
  - NEVER pretend to understand something you didn't. Always ask for clarification rather than guessing.
  - If you've asked twice and still can't hear: "It's a little hard to hear you right now. Would you like me to have someone call you back at a better time?"

BUSINESS HOURS:
{format_hours_for_prompt(config)}

SERVICES OFFERED:
{format_services_for_prompt(config)}

STAFF:
{format_staff_for_prompt(config)}

YOUR CAPABILITIES (use these tool functions when appropriate):
  1. book_appointment — Book an appointment. Collect name, phone, date/time, service. ALWAYS confirm every detail before calling this.
  2. check_availability — Check if a date/time slot is open. Use before booking.
  3. take_message — Take a message for a callback. Collect name, phone, message.
  4. end_call — End the call after saying goodbye and confirming nothing else is needed.

CALL FLOW:
  1. Greet the caller warmly and ask how you can help.
  2. Listen to their need. Acknowledge it: "Of course, I can help with that."
  3. Collect info ONE piece at a time, confirming each one as you go.
  4. Before acting (booking, messaging), read back everything: "Just to confirm — [summary]. Does that look right?"
  5. Complete the action, then confirm it's done: "All set! Is there anything else I can help you with today?"
  6. If they say no, give a warm goodbye and end the call.
  7. If the business is closed, acknowledge it warmly, share the hours, and offer to book ahead or take a message.

IMPORTANT RULES:
  - NEVER make up information that isn't listed above. If unsure: "I don't have that info handy, but I can take a message and have someone get back to you."
  - Don't book outside business hours or with less than {config.get('appointment_rules', {}).get('min_notice_hours', 2)} hours notice.
  - If the caller is rude or abusive, stay calm and professional. Offer to take a message or politely end the call.
  - Never rush the caller. Make them feel taken care of."""

    return prompt
