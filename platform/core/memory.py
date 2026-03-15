"""
Janovum Platform — Memory System
Stores persistent context per client as Markdown files.
Inspired by OpenClaw's memory system — simple, readable, no database needed.

Each client gets their own memory folder:
  platform/clients/[client_name]/memory/
    - context.md     → business info, preferences, how they like things done
    - history.md     → key interactions and decisions (not every message)
    - contacts.md    → important people, leads, vendors
    - notes.md       → anything else the agent should remember
"""

import os
from datetime import datetime

CLIENTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "clients")


def get_memory_dir(client_id):
    """Get or create the memory directory for a client."""
    mem_dir = os.path.join(CLIENTS_DIR, client_id, "memory")
    os.makedirs(mem_dir, exist_ok=True)
    return mem_dir


def read_memory(client_id, file_name="context.md"):
    """Read a memory file for a client. Returns empty string if not found."""
    path = os.path.join(get_memory_dir(client_id), file_name)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return ""


def write_memory(client_id, file_name, content):
    """Write/overwrite a memory file for a client."""
    path = os.path.join(get_memory_dir(client_id), file_name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def append_memory(client_id, file_name, entry):
    """Append an entry to a memory file with timestamp."""
    path = os.path.join(get_memory_dir(client_id), file_name)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"\n\n## {timestamp}\n{entry}")


def get_all_memory(client_id):
    """Load all memory files for a client into a single context string."""
    mem_dir = get_memory_dir(client_id)
    memory_text = ""

    for filename in ["context.md", "contacts.md", "notes.md"]:
        content = read_memory(client_id, filename)
        if content.strip():
            label = filename.replace(".md", "").upper()
            memory_text += f"\n\n--- {label} ---\n{content}"

    # Only include last 50 lines of history to keep context manageable
    history = read_memory(client_id, "history.md")
    if history.strip():
        lines = history.strip().split("\n")
        recent = "\n".join(lines[-50:])
        memory_text += f"\n\n--- RECENT HISTORY ---\n{recent}"

    return memory_text.strip()


def init_client_memory(client_id, client_name, client_context=""):
    """Initialize memory files for a new client."""
    mem_dir = get_memory_dir(client_id)

    context_path = os.path.join(mem_dir, "context.md")
    if not os.path.exists(context_path):
        write_memory(client_id, "context.md", f"""# {client_name}

## Business Info
{client_context}

## Preferences
- (Add how the client likes to communicate)
- (Add any special instructions)

## Services Active
- (List which Janovum modules are enabled)
""")

    for f in ["history.md", "contacts.md", "notes.md"]:
        path = os.path.join(mem_dir, f)
        if not os.path.exists(path):
            write_memory(client_id, f, f"# {client_name} — {f.replace('.md', '').title()}\n")

    return mem_dir


def save_interaction(client_id, summary):
    """Save a key interaction to history (not every message — just important ones)."""
    append_memory(client_id, "history.md", summary)


def save_contact(client_id, name, info):
    """Save a contact to the client's contact list."""
    append_memory(client_id, "contacts.md", f"**{name}**: {info}")


def save_note(client_id, note):
    """Save a note to the client's notes."""
    append_memory(client_id, "notes.md", note)
