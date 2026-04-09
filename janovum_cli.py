#!/usr/bin/env python3
"""
JANOVUM CLI — Create tools, AI employees, and pipelines from the terminal.
Usage:
  python3 janovum.py create tool
  python3 janovum.py create employee
  python3 janovum.py list tools
  python3 janovum.py list employees
  python3 janovum.py run tool <name>
  python3 janovum.py delete tool <name>
  python3 janovum.py delete employee <name>
"""

import sys
import os
import json
import time
import uuid
from datetime import datetime
from pathlib import Path

# ── Paths ───────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
TOOLS_FILE = BASE_DIR / "data" / "custom_tools.json"
EMPLOYEES_FILE = BASE_DIR / "data" / "custom_employees.json"
TOOLS_FILE.parent.mkdir(parents=True, exist_ok=True)

# ── Colors ──────────────────────────────────────────────────────────────────
R  = "\033[0m"
G  = "\033[92m"
Y  = "\033[93m"
B  = "\033[94m"
P  = "\033[95m"
C  = "\033[96m"
DIM= "\033[2m"
W  = "\033[1m"

def clr(text, color): return f"{color}{text}{R}"
def bold(text): return f"{W}{text}{R}"
def dim(text):  return f"{DIM}{text}{R}"

def header(title):
    print()
    print(clr("━" * 52, Y))
    print(clr(f"  {title}", Y + W))
    print(clr("━" * 52, Y))
    print()

RED = "\033[91m"
def success(msg): print(f"  {clr('✓', G)} {msg}")
def warn(msg):    print(f"  {clr('!', Y)} {msg}")
def info(msg):    print(f"  {clr('→', B)} {msg}")
def error(msg):   print(f"  {clr('✗', RED)} {msg}")

def ask(prompt, default=None, options=None):
    """Prompt user for input with optional default and options list."""
    suffix = ""
    if options:
        suffix = f" [{'/'.join(options)}]"
    elif default:
        suffix = f" {dim(f'(default: {default})')}"
    val = input(f"  {clr('?', C)} {prompt}{suffix}: ").strip()
    if not val and default:
        return default
    return val

def ask_multi(prompt, options, preselect=None):
    """Let user pick multiple options by number."""
    print(f"\n  {clr('?', C)} {prompt}")
    for i, opt in enumerate(options, 1):
        marker = clr("●", G) if preselect and opt in preselect else clr("○", DIM)
        print(f"    {marker} {i}. {opt}")
    print(dim("    Enter numbers separated by commas, or 'all', or press Enter to skip"))
    raw = input("  > ").strip()
    if raw.lower() == 'all':
        return options[:]
    if not raw:
        return preselect or []
    selected = []
    for part in raw.split(','):
        part = part.strip()
        if part.isdigit():
            idx = int(part) - 1
            if 0 <= idx < len(options):
                selected.append(options[idx])
    return selected

def ask_choice(prompt, options):
    """Let user pick one option by number."""
    print(f"\n  {clr('?', C)} {prompt}")
    for i, opt in enumerate(options, 1):
        print(f"    {i}. {opt}")
    while True:
        raw = input("  > ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1]
        warn("Enter a number from the list")

def load_json(path):
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return []

def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

# ════════════════════════════════════════════════════════════════════════════
#  CREATE TOOL
# ════════════════════════════════════════════════════════════════════════════
def create_tool():
    header("🔧  JANOVUM TOOL BUILDER")
    print(dim("  Build any custom tool. It'll appear in your toolkit immediately.\n"))

    # Step 1 — Identity
    name = ask("Tool name", default=None)
    while not name:
        error("Name is required")
        name = ask("Tool name")

    desc = ask("What does this tool do? (one sentence)")
    icon = ask("Icon/emoji", default="🔧")
    category = ask_choice("Category", [
        "Automation", "Sales & Marketing", "Customer Service",
        "Analytics", "Email & Outreach", "CRM", "Finance",
        "Content & Writing", "Data & Scraping", "Social Media",
        "E-Commerce", "Developer Tools", "Custom"
    ])

    # Step 2 — Pipeline type
    pipeline = ask_choice("Pipeline type — how does this tool work?", [
        "AI Prompt  — sends a prompt to an LLM, returns the response",
        "API Call   — calls an external REST API or webhook",
        "Workflow   — chains multiple steps (AI → API → AI → output)",
        "Hybrid     — AI decides what API to call, then executes it",
        "Script     — custom logic defined in pseudocode",
    ])
    pipeline_id = pipeline.split()[0].lower().replace(" ", "_")

    pipeline_config = {}

    if "AI Prompt" in pipeline:
        print()
        info("Write the system prompt. Use {input} for the user's input.")
        info("Example: 'You are a sales analyst. Given {input}, score the lead 1-10 and explain why.'")
        print()
        lines = []
        print(dim("  (Type your prompt. Press Enter twice when done)"))
        blank_count = 0
        while True:
            line = input("  ")
            if line == "":
                blank_count += 1
                if blank_count >= 2:
                    break
            else:
                blank_count = 0
            lines.append(line)
        pipeline_config["prompt"] = "\n".join(lines).strip()
        pipeline_config["model"] = ask_choice("AI Model", [
            "claude-sonnet-4-6  (best balance — recommended)",
            "claude-opus-4-6    (most powerful, complex tasks)",
            "claude-haiku-4-5   (fastest, cheapest, simple tasks)",
            "groq-llama         (free tier, very fast)",
            "openai-gpt4o       (GPT-4o)",
        ]).split()[0]

    elif "API Call" in pipeline:
        pipeline_config["url"] = ask("API endpoint URL", default="https://")
        pipeline_config["method"] = ask("HTTP method", default="POST", options=["GET","POST","PUT","DELETE"])
        auth = ask_choice("Auth type", ["None", "Bearer Token", "API Key Header", "Basic Auth"])
        pipeline_config["auth"] = auth
        if auth != "None":
            pipeline_config["auth_value"] = ask(f"Auth value (will be stored locally)")
        print(dim("  Body template (use {param_name} for inputs). Press Enter to skip:"))
        body = input("  ").strip()
        if body:
            pipeline_config["body_template"] = body

    elif "Workflow" in pipeline:
        print()
        info("Define your pipeline steps. Each step gets the output of the previous one.")
        steps = []
        step_types = ["AI Prompt", "API Call", "Transform Data", "Send Email", "Update CRM",
                      "Condition/Branch", "Wait", "Done"]
        i = 1
        while True:
            print(f"\n  {clr(f'Step {i}', Y)}")
            step_type = ask_choice("Step type", step_types)
            if step_type == "Done":
                break
            step_desc = ask("Describe what this step does")
            steps.append({"step": i, "type": step_type, "description": step_desc})
            i += 1
        pipeline_config["steps"] = steps

    elif "Hybrid" in pipeline:
        print()
        info("AI will decide which action to take based on the input.")
        pipeline_config["decision_prompt"] = ask("Decision prompt (how should AI choose the action?)")
        pipeline_config["available_apis"] = ask("Available APIs (comma-separated URLs)")

    else:  # Script
        print()
        info("Write pseudocode for your tool logic.")
        info("Available functions: ai_prompt(text), call_api(url, body), send_email(to, subject, body),")
        info("  update_crm(contact, field, value), get_input(name), return_result(value)")
        print()
        lines = []
        print(dim("  (Type your script. Press Enter twice when done)"))
        blank_count = 0
        while True:
            line = input("  ")
            if line == "":
                blank_count += 1
                if blank_count >= 2:
                    break
            else:
                blank_count = 0
            lines.append(line)
        pipeline_config["script"] = "\n".join(lines).strip()

    # Step 3 — Inputs
    print()
    header_short = lambda t: print(f"\n  {clr('──', Y)} {bold(t)}\n")
    header_short("Inputs")
    inputs = []
    add_more = True
    while add_more:
        add = ask("Add an input parameter?", default="no", options=["yes","no"])
        if add.lower() not in ("yes", "y"):
            break
        inp_name = ask("  Parameter name (e.g. email, lead_name, message)")
        inp_type = ask_choice("  Type", ["text", "email", "number", "url", "boolean", "select"])
        inp_required = ask("  Required?", default="yes", options=["yes","no"])
        inp_desc = ask("  Description (what is this input?)")
        inputs.append({
            "name": inp_name,
            "type": inp_type,
            "required": inp_required.lower() in ("yes", "y"),
            "description": inp_desc,
        })
        success(f"Input '{inp_name}' added")

    # Step 4 — Triggers
    triggers = ask_multi("When should this tool run?", [
        "Manual (run on demand)",
        "Scheduled (cron)",
        "On New Lead in CRM",
        "On Missed Call",
        "On Appointment Booked",
        "Webhook Received",
        "AI-Triggered (orchestrator decides)",
        "On New Email Received",
    ], preselect=["Manual (run on demand)"])

    output_fmt = ask_choice("Output format", [
        "text     — returns plain text",
        "json     — returns structured data",
        "email    — sends an email as output",
        "action   — triggers an action, no direct output",
        "list     — returns a list of items",
    ]).split()[0]

    # Step 5 — Share
    print()
    publish = ask("Publish to Janovum Community so others can install it?", default="no", options=["yes","no"])

    # Save
    tool = {
        "id": f"ctool_{uuid.uuid4().hex[:8]}",
        "name": name,
        "icon": icon,
        "description": desc,
        "category": category,
        "pipeline": pipeline_id,
        "pipeline_config": pipeline_config,
        "inputs": inputs,
        "triggers": triggers,
        "output_format": output_fmt,
        "is_public": publish.lower() in ("yes", "y"),
        "created_at": datetime.now().isoformat(),
        "installs": 0,
    }

    tools = load_json(TOOLS_FILE)
    tools.insert(0, tool)
    save_json(TOOLS_FILE, tools)

    print()
    print(clr("━" * 52, G))
    success(bold(f'Tool "{name}" created and saved!'))
    info(f"Pipeline: {pipeline_id}")
    info(f"Inputs:   {len(inputs)} defined")
    info(f"Triggers: {', '.join(triggers[:2]) or 'Manual'}")
    if publish.lower() in ("yes","y"):
        success("Published to Janovum Community")
    print(clr("━" * 52, G))
    print()
    info("It will appear in your toolkit under Tools → My Custom Tools")
    print()


# ════════════════════════════════════════════════════════════════════════════
#  CREATE EMPLOYEE
# ════════════════════════════════════════════════════════════════════════════
def create_employee():
    header("⚡  JANOVUM AI EMPLOYEE BUILDER")
    print(dim("  Build a custom AI employee with your own pipeline.\n"))

    # Identity
    name = ask("Employee name (e.g. Nova, Aria, Rex)")
    while not name:
        error("Name is required")
        name = ask("Employee name")

    role = ask("Job title (e.g. Lead Closer, Email Manager, Data Analyst)")
    avatar = ask("Avatar emoji", default="🤖")
    job = ask("Main job in one sentence (e.g. 'Qualifies new leads and sends follow-up emails')")

    # Personality
    personality = ask_multi("Personality traits", [
        "Professional", "Friendly", "Concise", "Enthusiastic",
        "Analytical", "Empathetic", "Direct", "Formal", "Casual",
    ], preselect=["Professional", "Friendly"])

    # AI Model
    model = ask_choice("AI Model", [
        "claude-sonnet-4-6  — best balance (recommended)",
        "claude-opus-4-6    — most powerful, complex reasoning",
        "claude-haiku-4-5   — fastest + cheapest, simple tasks",
        "groq-llama         — free tier, very fast",
        "openai-gpt4o       — GPT-4o",
    ]).split()[0]

    # System Prompt
    print()
    info("Write the system prompt — this is how your employee thinks.")
    info(f"Example: 'You are {name}, a {role}. When given a lead, you score them 1-10")
    info("  and draft a personalized follow-up email. Always be concise and direct.'")
    info("Use {{business_name}}, {{client_name}}, {{date}}, {{input}} as variables.")
    print()
    lines = []
    print(dim("  (Type your system prompt. Press Enter twice when done)"))
    blank_count = 0
    while True:
        line = input("  ")
        if line == "":
            blank_count += 1
            if blank_count >= 2:
                break
        else:
            blank_count = 0
        lines.append(line)
    system_prompt = "\n".join(lines).strip()

    # If no prompt given, auto-generate a starter
    if not system_prompt:
        system_prompt = (f"You are {name}, a {role}. {job} "
                         f"Tone: {', '.join(personality[:2]) if personality else 'professional'}. "
                         f"Always be helpful and get results.")
        warn(f"No prompt entered — using auto-generated starter:")
        print(f"  {dim(system_prompt[:120])}")

    # Tools / capabilities
    tools = ask_multi("What tools can this employee use?", [
        "Send Email", "Send SMS", "Update CRM", "Book Appointment",
        "Search Web", "Read Calendar", "Write to Spreadsheet",
        "Call External API", "Generate AI Content", "Run Custom Tool",
        "Escalate to Human", "Send Telegram Message", "Read Emails",
        "Scrape Website", "Post to Social Media",
    ])

    # Channels
    channels = ask_multi("What channels does this employee work on?", [
        "Email", "SMS", "Phone Calls", "Live Chat / Website",
        "Telegram", "Slack", "WhatsApp", "API / Webhook", "Internal Only",
    ])

    # Triggers
    triggers = ask_multi("What triggers this employee to start working?", [
        "New Lead in CRM", "Missed Call", "Appointment Booked",
        "Appointment Cancelled", "New Email Received",
        "Daily at 9 AM", "Every Hour", "Webhook Received",
        "New Form Submission", "Manual Only",
    ], preselect=["Manual Only"])

    # Schedule
    schedule = ask_choice("Work schedule", [
        "24/7 Always On",
        "Business Hours Only (9am-6pm)",
        "On-Demand Only",
        "Custom Schedule",
    ])

    # Memory
    memory = ask_choice("Memory mode", [
        "session    — remembers within one conversation only",
        "persistent — remembers everything across all interactions",
        "per-client — separate memory per client/contact",
        "none       — always starts fresh",
    ]).split()[0]

    # Escalation
    escalation = ask_choice("Escalation rule", [
        "never      — always handle autonomously",
        "ask        — ask me before taking important actions",
        "high_value — escalate when value > $500 or very complex",
        "always     — notify me and I approve every action",
    ]).split()[0]

    # Knowledge base
    print()
    add_kb = ask("Add knowledge base? (facts, FAQs, products this employee knows)", default="no", options=["yes","no"])
    knowledge = ""
    if add_kb.lower() in ("yes","y"):
        print()
        info("Enter knowledge (press Enter twice when done):")
        lines = []
        blank_count = 0
        while True:
            line = input("  ")
            if line == "":
                blank_count += 1
                if blank_count >= 2:
                    break
            else:
                blank_count = 0
            lines.append(line)
        knowledge = "\n".join(lines).strip()

    # Share
    print()
    publish = ask("Publish to Janovum Community so others can install this employee?", default="no", options=["yes","no"])

    # Save
    employee = {
        "id": f"cemp_{uuid.uuid4().hex[:8]}",
        "name": name,
        "role": role,
        "avatar": avatar,
        "job": job,
        "personality": personality,
        "model": model,
        "system_prompt": system_prompt,
        "tools": tools,
        "channels": channels,
        "triggers": triggers,
        "schedule": schedule,
        "memory": memory,
        "escalation": escalation,
        "knowledge": knowledge,
        "status": "active",
        "is_public": publish.lower() in ("yes", "y"),
        "created_at": datetime.now().isoformat(),
        "messages_handled": 0,
        "installs": 0,
    }

    employees = load_json(EMPLOYEES_FILE)
    employees.insert(0, employee)
    save_json(EMPLOYEES_FILE, employees)

    print()
    print(clr("━" * 52, G))
    success(bold(f'{name} ({role}) is now deployed!'))
    info(f"Model:    {model}")
    info(f"Channels: {', '.join(channels[:3]) or 'None set'}")
    info(f"Tools:    {len(tools)} available")
    info(f"Memory:   {memory}")
    info(f"Schedule: {schedule}")
    if publish.lower() in ("yes","y"):
        success("Published to Janovum Community")
    print(clr("━" * 52, G))
    print()
    info(f"{name} will appear in your toolkit under AI Employees → My Custom Employees")
    info(f"Chat with them in the toolkit or trigger them via API:")
    info(f"  POST /api/employees/{employee['id']}/chat  {{\"message\": \"...\"}}")
    print()


# ════════════════════════════════════════════════════════════════════════════
#  LIST
# ════════════════════════════════════════════════════════════════════════════
def list_tools():
    tools = load_json(TOOLS_FILE)
    header(f"🔧  Custom Tools  ({len(tools)})")
    if not tools:
        warn("No custom tools yet. Run: python3 janovum.py create tool")
        return
    for t in tools:
        print(f"  {t.get('icon','🔧')}  {bold(t['name'])}  {dim(t.get('pipeline','?'))}  {clr('PUBLIC' if t.get('is_public') else 'private', G if t.get('is_public') else DIM)}")
        print(f"     {dim(t.get('description',''))}")
        print()

def list_employees():
    employees = load_json(EMPLOYEES_FILE)
    header(f"⚡  AI Employees  ({len(employees)})")
    if not employees:
        warn("No custom employees yet. Run: python3 janovum.py create employee")
        return
    for e in employees:
        status_color = G if e.get('status') == 'active' else Y
        print(f"  {e.get('avatar','🤖')}  {bold(e['name'])}  —  {clr(e.get('role','?'), P)}")
        print(f"     Model: {dim(e.get('model','?'))} | Memory: {dim(e.get('memory','?'))} | Status: {clr(e.get('status','?'), status_color)}")
        print(f"     {dim(e.get('job',''))}")
        print()


# ════════════════════════════════════════════════════════════════════════════
#  RUN TOOL
# ════════════════════════════════════════════════════════════════════════════
def run_tool(name_arg=None):
    tools = load_json(TOOLS_FILE)
    if not tools:
        error("No custom tools found. Create one first."); return

    if name_arg:
        tool = next((t for t in tools if t['name'].lower() == name_arg.lower()), None)
    else:
        names = [t['name'] for t in tools]
        choice = ask_choice("Which tool to run?", names)
        tool = next(t for t in tools if t['name'] == choice)

    if not tool:
        error(f"Tool '{name_arg}' not found"); return

    header(f"▶  Running: {tool['name']}")

    # Collect inputs
    inputs = {}
    for inp in tool.get('inputs', []):
        val = ask(f"{inp['name']} ({inp['type']}): {inp.get('description','')}")
        inputs[inp['name']] = val

    pipeline = tool.get('pipeline', '')
    config = tool.get('pipeline_config', {})

    if pipeline in ('ai_prompt',):
        try:
            import requests
            prompt = config.get('prompt', '')
            for k, v in inputs.items():
                prompt = prompt.replace(f'{{{k}}}', v).replace('{input}', list(inputs.values())[0] if inputs else '')
            info("Sending to AI...")
            r = requests.post('http://localhost:5050/api/ai/chat',
                json={'message': prompt, 'model': config.get('model', 'claude-sonnet-4-6')},
                timeout=30)
            result = r.json()
            print()
            print(clr("━" * 52, G))
            print(f"  {bold('Result:')}")
            print()
            response = result.get('response') or result.get('content') or str(result)
            for line in response.split('\n'):
                print(f"  {line}")
            print(clr("━" * 52, G))
        except Exception as e:
            warn(f"Could not reach local server: {e}")
            warn("Start the server first: python3 server_v2.py")

    elif pipeline == 'api_call':
        try:
            import requests
            url = config.get('url', '')
            method = config.get('method', 'POST')
            info(f"Calling {method} {url}")
            r = requests.request(method, url, json=inputs, timeout=15)
            print()
            success(f"Status: {r.status_code}")
            print(f"  {dim(r.text[:500])}")
        except Exception as e:
            error(f"API call failed: {e}")

    else:
        info(f"Pipeline '{pipeline}' — sending to toolkit server to execute")
        try:
            import requests
            r = requests.post('http://localhost:5050/api/tools/custom/run',
                json={'tool_id': tool['id'], 'inputs': inputs}, timeout=30)
            print(f"  {clr('Result:', G)} {r.text[:300]}")
        except:
            warn("Toolkit server not running. Start with: python3 server_v2.py")


# ════════════════════════════════════════════════════════════════════════════
#  DELETE
# ════════════════════════════════════════════════════════════════════════════
def delete_item(kind, name_arg=None):
    path = TOOLS_FILE if kind == 'tool' else EMPLOYEES_FILE
    items = load_json(path)
    key = 'name'
    if not items:
        warn(f"No {kind}s found."); return
    if name_arg:
        item = next((i for i in items if i[key].lower() == name_arg.lower()), None)
    else:
        names = [i[key] for i in items]
        choice = ask_choice(f"Which {kind} to delete?", names)
        item = next(i for i in items if i[key] == choice)
    if not item:
        error(f"{kind} '{name_arg}' not found"); return
    confirm = ask(f"Delete '{item['name']}'? This cannot be undone.", options=["yes","no"])
    if confirm.lower() in ("yes","y"):
        items = [i for i in items if i['id'] != item['id']]
        save_json(path, items)
        success(f"'{item['name']}' deleted.")
    else:
        info("Cancelled.")


# ════════════════════════════════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════════════════════════════════
HELP = f"""
{clr('JANOVUM CLI', Y + W)} {dim('— Build tools and AI employees from the terminal')}

{bold('Commands:')}
  {clr('create tool', G)}              Build a new custom tool
  {clr('create employee', G)}          Build a new AI employee
  {clr('list tools', B)}               Show all your custom tools
  {clr('list employees', B)}           Show all your AI employees
  {clr('run tool', P)} {dim('[name]')}           Run a tool interactively
  {clr('delete tool', RED)} {dim('[name]')}        Delete a tool
  {clr('delete employee', RED)} {dim('[name]')}    Delete an employee

{bold('Examples:')}
  python3 janovum.py create tool
  python3 janovum.py create employee
  python3 janovum.py list employees
  python3 janovum.py run tool "Lead Scorer"
  python3 janovum.py delete tool "Old Bot"
"""

def main():
    args = sys.argv[1:]
    if not args or args[0] in ('-h', '--help', 'help'):
        print(HELP); return

    cmd = args[0].lower()
    sub = args[1].lower() if len(args) > 1 else ''
    name_arg = ' '.join(args[2:]) if len(args) > 2 else None

    if cmd == 'create':
        if sub == 'tool':      create_tool()
        elif sub == 'employee': create_employee()
        else: print(HELP)
    elif cmd == 'list':
        if sub == 'tools':      list_tools()
        elif sub == 'employees': list_employees()
        else: list_tools(); list_employees()
    elif cmd == 'run':
        if sub == 'tool':  run_tool(name_arg)
        else: print(HELP)
    elif cmd == 'delete':
        if sub in ('tool', 'tools'):           delete_item('tool', name_arg)
        elif sub in ('employee', 'employees'): delete_item('employee', name_arg)
        else: print(HELP)
    else:
        print(HELP)

if __name__ == '__main__':
    main()
