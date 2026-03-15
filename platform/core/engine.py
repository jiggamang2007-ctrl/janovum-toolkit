"""
Janovum Platform — Core AI Engine
Connects to Claude API, sends prompts, handles tool calls.
Auto-routes to the cheapest model that can handle each task.
Loads skill MD files for each module + client memory for context.
"""

import json
import os
import re
import requests
from .config import get_api_key

API_URL = "https://api.anthropic.com/v1/messages"

# Model tiers — cheapest first
MODELS = {
    "haiku":  "claude-haiku-4-5-20251001",     # $0.25/$1.25 per 1M tokens — fast, simple tasks
    "sonnet": "claude-sonnet-4-20250514",       # $3/$15 per 1M tokens — balanced, most tasks
    "opus":   "claude-opus-4-20250514",         # $15/$75 per 1M tokens — complex reasoning
}


# ── SKILL LOADER ──
# Each module has a .md file in modules/skills/ that tells Claude how to do the job.
# Just like OpenClaw's SKILL.md system — simple, readable, powerful.

SKILLS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "modules", "skills")


def load_skill(skill_name):
    """Load a skill MD file by name. Returns the content or empty string."""
    path = os.path.join(SKILLS_DIR, f"{skill_name}.md")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return ""


def build_system_prompt(skill_name, client_name="", client_context="", client_memory=""):
    """
    Build a complete system prompt by combining:
    1. The skill instructions (from .md file)
    2. Client info (name, context)
    3. Client memory (persistent context from previous interactions)
    """
    skill = load_skill(skill_name)

    prompt = f"You are an AI assistant created by Janovum.\n"

    if skill:
        prompt += f"\n{skill}\n"

    if client_name:
        prompt += f"\n## Current Client\nClient: {client_name}\n"
    if client_context:
        prompt += f"Context: {client_context}\n"
    if client_memory:
        prompt += f"\n## Client Memory (persistent context)\n{client_memory}\n"

    return prompt


# ── SMART ROUTER (the director) ──
# Python decides which model to use — this is FREE, no API call needed

# Keywords that suggest simple tasks (Haiku)
SIMPLE_KEYWORDS = [
    "hi", "hello", "hey", "thanks", "thank you", "ok", "okay", "yes", "no",
    "start", "stop", "status", "help", "what time", "how much", "price",
    "list", "show", "send", "forward", "reply", "confirm", "cancel",
    "schedule", "book", "remind", "notify", "alert", "check",
]

# Keywords that suggest complex tasks (Opus)
COMPLEX_KEYWORDS = [
    "analyze", "compare", "strategy", "plan", "design", "architect",
    "debug", "refactor", "optimize", "evaluate", "research",
    "business plan", "pitch deck", "market research", "financial model",
    "write a full", "create a detailed", "comprehensive",
    "multiple steps", "step by step",
]


def pick_model(text, has_tools=False):
    """
    Automatically pick the cheapest model that can handle the task.
    Pure Python — costs nothing.

    Logic:
      - Short simple messages → Haiku (cheapest)
      - Medium tasks, some reasoning needed → Sonnet
      - Complex multi-step analysis → Opus
      - Tasks with tools always get at least Sonnet
    """
    if not text:
        return MODELS["haiku"]

    text_lower = text.lower().strip()
    word_count = len(text_lower.split())

    # If tools are involved, minimum Sonnet (tool use needs reasoning)
    min_tier = "sonnet" if has_tools else "haiku"

    # Check for complex keywords → Opus
    for kw in COMPLEX_KEYWORDS:
        if kw in text_lower:
            return MODELS["opus"]

    # Very long messages or multiple questions → Sonnet or Opus
    if word_count > 200:
        return MODELS["opus"]
    if word_count > 80:
        return MODELS["sonnet"]

    # Short simple messages → Haiku
    if word_count <= 15:
        # Check if it's a simple command/greeting
        for kw in SIMPLE_KEYWORDS:
            if kw in text_lower:
                return MODELS["haiku"]

    # Multiple sentences with questions → Sonnet
    question_marks = text_lower.count("?")
    sentences = len(re.split(r'[.!?]+', text_lower))
    if question_marks >= 2 or sentences >= 4:
        return MODELS["sonnet"]

    # Medium length, some content → Sonnet
    if word_count > 30:
        return MODELS["sonnet"]

    # Default: Haiku for short, Sonnet for medium
    if min_tier == "sonnet":
        return MODELS["sonnet"]

    return MODELS["haiku"] if word_count <= 25 else MODELS["sonnet"]


def get_model_name(model_id):
    """Get friendly name from model ID."""
    for name, mid in MODELS.items():
        if mid == model_id:
            return name.capitalize()
    return model_id


def call_claude(messages, system_prompt=None, tools=None, max_tokens=4096, force_model=None):
    """
    Send a message to Claude API and get a response.
    Automatically picks the cheapest model unless force_model is set.

    Args:
        messages: list of {"role": "user"/"assistant", "content": "..."}
        system_prompt: optional system prompt string
        tools: optional list of tool definitions
        max_tokens: max response length
        force_model: override auto-routing with a specific model ID

    Returns:
        dict with 'text', 'tool_calls', 'model_used', 'usage'
    """
    api_key = get_api_key()
    if not api_key:
        return {"error": "No API key set. Go to Toolkit > Settings and enter your Claude API key."}

    # Auto-pick model based on the latest user message
    if force_model:
        model = force_model
    else:
        last_user_msg = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                content = m.get("content", "")
                if isinstance(content, str):
                    last_user_msg = content
                elif isinstance(content, list):
                    last_user_msg = " ".join(
                        b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"
                    )
                break
        model = pick_model(last_user_msg, has_tools=bool(tools))

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }

    body = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": messages
    }

    if system_prompt:
        body["system"] = system_prompt

    if tools:
        body["tools"] = tools

    try:
        resp = requests.post(API_URL, headers=headers, json=body, timeout=120)
        data = resp.json()

        if resp.status_code != 200:
            error_msg = data.get("error", {}).get("message", f"API error {resp.status_code}")
            return {"error": error_msg}

        # Parse response
        result = {"text": "", "tool_calls": [], "model_used": get_model_name(model)}
        for block in data.get("content", []):
            if block["type"] == "text":
                result["text"] += block["text"]
            elif block["type"] == "tool_use":
                result["tool_calls"].append({
                    "id": block["id"],
                    "name": block["name"],
                    "input": block["input"]
                })

        result["usage"] = data.get("usage", {})
        result["stop_reason"] = data.get("stop_reason", "")
        return result

    except requests.exceptions.Timeout:
        return {"error": "Request timed out — Claude took too long to respond."}
    except requests.exceptions.ConnectionError:
        return {"error": "Connection error — check your internet."}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}


def quick_ask(prompt, system_prompt=None, force_model=None):
    """Simple one-shot question to Claude. Auto-picks cheapest model."""
    result = call_claude(
        messages=[{"role": "user", "content": prompt}],
        system_prompt=system_prompt,
        force_model=force_model
    )
    if "error" in result:
        return f"[ERROR] {result['error']}"
    return result.get("text", "")


def agent_loop(messages, system_prompt, tools, tool_executor, max_turns=10):
    """
    Run an agent loop — Claude picks tools, we execute them, repeat until done.
    Uses at least Sonnet for tool-based reasoning.
    """
    for turn in range(max_turns):
        result = call_claude(messages, system_prompt=system_prompt, tools=tools)

        if "error" in result:
            return f"[ERROR] {result['error']}"

        if result["stop_reason"] == "end_turn" or not result["tool_calls"]:
            return result.get("text", "")

        # Build assistant message
        assistant_content = []
        if result["text"]:
            assistant_content.append({"type": "text", "text": result["text"]})
        for tc in result["tool_calls"]:
            assistant_content.append({
                "type": "tool_use",
                "id": tc["id"],
                "name": tc["name"],
                "input": tc["input"]
            })
        messages.append({"role": "assistant", "content": assistant_content})

        # Execute tools
        tool_results = []
        for tc in result["tool_calls"]:
            try:
                tool_output = tool_executor(tc["name"], tc["input"])
            except Exception as e:
                tool_output = f"Tool error: {str(e)}"

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tc["id"],
                "content": str(tool_output)
            })

        messages.append({"role": "user", "content": tool_results})

    return result.get("text", "[Agent reached max turns]")


def test_api_key(api_key=None):
    """Test if the API key works using Haiku (cheapest)."""
    key = api_key or get_api_key()
    if not key:
        return False, "No API key set."

    headers = {
        "x-api-key": key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }

    body = {
        "model": MODELS["haiku"],
        "max_tokens": 10,
        "messages": [{"role": "user", "content": "Say OK"}]
    }

    try:
        resp = requests.post(API_URL, headers=headers, json=body, timeout=30)
        if resp.status_code == 200:
            return True, "API key is valid!"
        elif resp.status_code == 401:
            return False, "Invalid API key."
        else:
            data = resp.json()
            msg = data.get("error", {}).get("message", f"Error {resp.status_code}")
            return False, msg
    except Exception as e:
        return False, f"Connection error: {str(e)}"
