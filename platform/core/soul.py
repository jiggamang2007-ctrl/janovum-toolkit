"""
Janovum Platform — SOUL System
Defines agent personality, values, and behavioral guidelines.
Like OpenClaw's SOUL.md but per-client and per-agent.

Each agent/client can have their own:
  - SOUL.md: Agent personality, tone, values
  - RULES.md: Hard rules the agent must follow
  - CONTEXT.md: Business context and background info
"""

import os
from pathlib import Path

PLATFORM_DIR = Path(__file__).parent.parent
SOULS_DIR = PLATFORM_DIR / "souls"
CLIENTS_DIR = PLATFORM_DIR / "clients"

DEFAULT_SOUL = """# Janovum Agent

## Personality
- Professional but approachable
- Efficient and action-oriented
- Honest about limitations
- Proactive — suggest next steps

## Values
- Client success comes first
- Be cost-conscious — don't waste API calls
- Privacy matters — never leak client data
- Quality over speed — get it right

## Communication Style
- Clear, concise responses
- Use bullet points for lists
- Confirm before taking irreversible actions
- Explain reasoning when making decisions
"""

DEFAULT_RULES = """# Agent Rules

## Always
- Check budget before making API calls
- Log important actions to client history
- Confirm before sending external communications
- Use the cheapest model that can handle the task

## Never
- Share client data between different clients
- Send emails/messages without approval (unless auto-approved)
- Make purchases or financial transactions without explicit approval
- Ignore error messages — always report them
- Store passwords or API keys in plain text
"""


class SoulSystem:
    """Manages agent personality and rules."""

    def __init__(self):
        SOULS_DIR.mkdir(parents=True, exist_ok=True)

    def get_soul(self, agent_id=None, client_id=None):
        """Get the SOUL.md content for an agent or client."""
        # Priority: agent-specific > client-specific > default
        if agent_id:
            path = SOULS_DIR / f"{agent_id}_soul.md"
            if path.exists():
                return path.read_text(encoding="utf-8")

        if client_id:
            path = CLIENTS_DIR / client_id / "SOUL.md"
            if path.exists():
                return path.read_text(encoding="utf-8")

        default_path = SOULS_DIR / "default_soul.md"
        if default_path.exists():
            return default_path.read_text(encoding="utf-8")

        return DEFAULT_SOUL

    def set_soul(self, content, agent_id=None, client_id=None):
        """Set the SOUL.md for an agent or client."""
        if agent_id:
            path = SOULS_DIR / f"{agent_id}_soul.md"
        elif client_id:
            client_dir = CLIENTS_DIR / client_id
            client_dir.mkdir(parents=True, exist_ok=True)
            path = client_dir / "SOUL.md"
        else:
            path = SOULS_DIR / "default_soul.md"

        path.write_text(content, encoding="utf-8")

    def get_rules(self, agent_id=None, client_id=None):
        """Get the RULES.md for an agent or client."""
        if agent_id:
            path = SOULS_DIR / f"{agent_id}_rules.md"
            if path.exists():
                return path.read_text(encoding="utf-8")

        if client_id:
            path = CLIENTS_DIR / client_id / "RULES.md"
            if path.exists():
                return path.read_text(encoding="utf-8")

        default_path = SOULS_DIR / "default_rules.md"
        if default_path.exists():
            return default_path.read_text(encoding="utf-8")

        return DEFAULT_RULES

    def set_rules(self, content, agent_id=None, client_id=None):
        """Set the RULES.md for an agent or client."""
        if agent_id:
            path = SOULS_DIR / f"{agent_id}_rules.md"
        elif client_id:
            client_dir = CLIENTS_DIR / client_id
            client_dir.mkdir(parents=True, exist_ok=True)
            path = client_dir / "RULES.md"
        else:
            path = SOULS_DIR / "default_rules.md"

        path.write_text(content, encoding="utf-8")

    def build_system_prompt(self, agent_id=None, client_id=None, skill_content=""):
        """Build a complete system prompt combining soul + rules + skill."""
        soul = self.get_soul(agent_id, client_id)
        rules = self.get_rules(agent_id, client_id)

        prompt = f"You are an AI assistant created by Janovum.\n\n"
        prompt += f"## Your Personality & Values\n{soul}\n\n"
        prompt += f"## Rules You Must Follow\n{rules}\n\n"
        if skill_content:
            prompt += f"## Your Current Task Instructions\n{skill_content}\n"

        return prompt

    def list_souls(self):
        """List all custom soul configurations."""
        souls = []
        if SOULS_DIR.exists():
            for f in SOULS_DIR.iterdir():
                if f.name.endswith("_soul.md"):
                    agent_id = f.name.replace("_soul.md", "")
                    souls.append({"agent_id": agent_id, "type": "agent", "path": str(f)})
        if CLIENTS_DIR.exists():
            for d in CLIENTS_DIR.iterdir():
                if d.is_dir():
                    soul_path = d / "SOUL.md"
                    if soul_path.exists():
                        souls.append({"client_id": d.name, "type": "client", "path": str(soul_path)})
        return souls


_soul = None
def get_soul_system():
    global _soul
    if _soul is None:
        _soul = SoulSystem()
    return _soul
