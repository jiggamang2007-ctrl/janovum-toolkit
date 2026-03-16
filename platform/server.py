"""
Janovum Platform — Main Server v8
Flask server with ALL 14 systems + Director Agent + Telegram + Client Management.
Multi-client receptionist management — add clients, spin up receptionists on different ports.

Start with: python server_v8.py
Dashboard at: http://localhost:5050

Systems:
  Phase 1: heartbeat, api_router, cost_tracker, guardrails, agent_registry, auth
  Phase 2: tracing, approval, handoffs, events, voice, sandbox, model_failover, soul
  Phase 3: director (message routing brain), telegram listener
  Phase 4: client manager (multi-client receptionists)
"""

import json
import os
import sys
import time
import threading
from flask import Flask, request, jsonify, send_from_directory, Response
from datetime import datetime

# Setup paths
PLATFORM_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(PLATFORM_DIR)
sys.path.insert(0, PLATFORM_DIR)

from core.config import load_config, save_config, get_api_key, set_api_key, get_model, set_model
from core.engine import test_api_key, quick_ask, call_claude, pick_model, get_model_name, MODELS

app = Flask(__name__)


# ══════════════════════════════════════════
# LAZY IMPORTS — only load systems when needed
# ══════════════════════════════════════════

def _get_heartbeat():
    from core.heartbeat import get_heartbeat
    return get_heartbeat()

def _get_router():
    from core.api_router import get_router
    return get_router()

def _get_costs():
    from core.cost_tracker import get_cost_tracker
    return get_cost_tracker()

def _get_guardrails():
    from core.guardrails import get_guardrails
    return get_guardrails()

def _get_registry():
    from core.agent_registry import get_registry
    return get_registry()

def _get_tracer():
    from core.tracing import get_tracer
    return get_tracer()

def _get_approval():
    from core.approval import get_approval_manager
    return get_approval_manager()

def _get_handoffs():
    from core.handoffs import get_handoff_router
    return get_handoff_router()

def _get_events():
    from core.events import get_event_bus
    return get_event_bus()

def _get_voice():
    from core.voice import get_voice_system
    return get_voice_system()

def _get_sandbox():
    from core.sandbox import get_sandbox
    return get_sandbox()

def _get_failover():
    from core.model_failover import get_model_failover
    return get_model_failover()

def _get_soul():
    from core.soul import get_soul_system
    return get_soul_system()

def _get_auth():
    from core.auth import get_auth
    return get_auth()

def _get_director():
    from core.director import get_director
    return get_director()


# ══════════════════════════════════════════
# CDP CONNECTION POOL — persistent WebSocket
# ══════════════════════════════════════════

_cdp_connections = {}
_cdp_lock = threading.Lock()


def _get_cdp_connection(port):
    import urllib.request
    import websocket

    with _cdp_lock:
        conn = _cdp_connections.get(port)
        if conn and conn.get("ws"):
            try:
                conn["ws"].ping()
                return conn
            except Exception:
                try:
                    conn["ws"].close()
                except Exception:
                    pass
                del _cdp_connections[port]

        try:
            resp = urllib.request.urlopen(f"http://127.0.0.1:{port}/json", timeout=3)
            pages = json.loads(resp.read())
            pages = [p for p in pages if p.get("type") == "page"]
            if not pages:
                return None
            ws_url = pages[0].get("webSocketDebuggerUrl")
            if not ws_url:
                return None
            ws = websocket.create_connection(ws_url, timeout=10)
            conn = {
                "ws": ws,
                "page_url": pages[0].get("url", ""),
                "page_title": pages[0].get("title", ""),
                "page_id": pages[0].get("id", ""),
                "lock": threading.Lock(),
                "cmd_id": 1,
                "created": time.time()
            }
            _cdp_connections[port] = conn
            return conn
        except Exception:
            return None


def _cdp_screenshot(port):
    conn = _get_cdp_connection(port)
    if not conn:
        return None, "No connection"

    with conn["lock"]:
        try:
            ws = conn["ws"]
            cmd_id = conn["cmd_id"]
            conn["cmd_id"] += 1
            ws.send(json.dumps({
                "id": cmd_id,
                "method": "Page.captureScreenshot",
                "params": {"format": "jpeg", "quality": 65}
            }))
            deadline = time.time() + 5
            while time.time() < deadline:
                raw = ws.recv()
                msg = json.loads(raw)
                if msg.get("id") == cmd_id:
                    data = msg.get("result", {}).get("data")
                    if data:
                        try:
                            conn["cmd_id"] += 1
                            ws.send(json.dumps({
                                "id": conn["cmd_id"],
                                "method": "Runtime.evaluate",
                                "params": {"expression": "JSON.stringify({url:location.href,title:document.title})"}
                            }))
                            raw2 = ws.recv()
                            msg2 = json.loads(raw2)
                            if msg2.get("result", {}).get("result", {}).get("value"):
                                info = json.loads(msg2["result"]["result"]["value"])
                                conn["page_url"] = info.get("url", conn["page_url"])
                                conn["page_title"] = info.get("title", conn["page_title"])
                        except Exception:
                            pass
                        return data, None
                    else:
                        return None, "Empty screenshot"
            return None, "Timeout"
        except Exception as e:
            with _cdp_lock:
                if port in _cdp_connections:
                    del _cdp_connections[port]
            return None, str(e)


# ══════════════════════════════════════════
# CORS
# ══════════════════════════════════════════

@app.after_request
def add_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


# ══════════════════════════════════════════
# SERVE HTML / STATIC FILES
# ══════════════════════════════════════════

@app.route("/")
def index():
    return send_from_directory(PARENT_DIR, "Janovum_Landing.html")

@app.route("/toolkit")
def toolkit():
    return send_from_directory(PARENT_DIR, "Janovum_Platform.html")

@app.route("/api/demo-request", methods=["POST"])
def demo_request():
    """Handle demo request from landing page — save appointment + email Jaden."""
    import uuid, smtplib
    from email.mime.text import MIMEText
    data = request.json
    name = data.get("name", "").strip()
    business = data.get("business", "").strip()
    phone = data.get("phone", "").strip()
    email = data.get("email", "").strip()
    date = data.get("date", "")
    time_slot = data.get("time", "")

    if not name or not phone or not date or not time_slot:
        return jsonify({"error": "Please fill out all fields"}), 400

    # Save as appointment
    appts_path = os.path.join(PLATFORM_DIR, "data", "clients", "janovum_appointments.json")
    try:
        with open(appts_path, "r") as f:
            appts = json.load(f)
    except Exception:
        appts = []

    appt = {
        "id": str(uuid.uuid4())[:8],
        "client_id": "janovum",
        "business_name": "Janovum",
        "name": name,
        "phone": phone,
        "date": date,
        "time": time_slot,
        "service": "AI Receptionist Demo",
        "notes": f"Business: {business}. Email: {email}",
        "status": "confirmed",
        "payment_status": "pending",
        "potential_income": 1000,
        "booked_at": datetime.now().isoformat(),
        "booked_by": "Website Form",
    }
    appts.append(appt)
    with open(appts_path, "w") as f:
        json.dump(appts, f, indent=2)

    # Email notification to Jaden
    try:
        smtp_user = "myfriendlyagent12@gmail.com"
        smtp_pass = "pdcvjroclstugncx"
        msg = MIMEText(
            f"New Demo Request!\n\n"
            f"Name: {name}\n"
            f"Business: {business}\n"
            f"Phone: {phone}\n"
            f"Email: {email}\n"
            f"Date: {date}\n"
            f"Time: {time_slot}\n\n"
            f"Booked via website form."
        )
        msg["Subject"] = f"New Janovum Demo Request — {name} ({business})"
        msg["From"] = smtp_user
        msg["To"] = "janovumllc@gmail.com"
        with smtplib.SMTP("smtp.gmail.com", 587) as s:
            s.starttls()
            s.login(smtp_user, smtp_pass)
            s.send_message(msg)
    except Exception as e:
        print(f"Email notification failed: {e}")

    return jsonify({"status": "ok", "id": appt["id"]})

@app.route("/<path:filename>")
def serve_file(filename):
    if filename.startswith("api/"):
        return "Not found", 404
    if filename.endswith((".html", ".css", ".js", ".json", ".png", ".jpg", ".ico", ".wav", ".mp3")):
        return send_from_directory(PARENT_DIR, filename)
    return "Not found", 404


# ══════════════════════════════════════════
# PLATFORM STATUS — everything at a glance
# ══════════════════════════════════════════

@app.route("/api/status")
def platform_status():
    try:
        hb = _get_heartbeat()
        router = _get_router()
        costs = _get_costs()
        registry = _get_registry()
        tracer = _get_tracer()
        approval = _get_approval()
        handoffs = _get_handoffs()
        events = _get_events()
        voice = _get_voice()
        sandbox = _get_sandbox()
        failover = _get_failover()
        soul = _get_soul()

        return jsonify({
            "platform": "Janovum Toolkit v4",
            "timestamp": datetime.now().isoformat(),
            "api_key_set": bool(get_api_key()),
            "systems": {
                "heartbeat": {"running": hb.running, "agents": len(hb.agents)},
                "router": {"capabilities": len(router.get_capabilities())},
                "costs": costs.get_all_costs(),
                "registry": registry.get_dashboard(),
                "tracing": tracer.get_stats(),
                "approval": {"pending": len(approval.get_pending())},
                "handoffs": handoffs.get_stats(),
                "events": events.get_stats(),
                "voice": voice.get_status(),
                "sandbox": sandbox.get_stats(),
                "failover": {"providers": len(failover.get_status())},
                "soul": {"configs": len(soul.list_souls())}
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ══════════════════════════════════════════
# CONFIG & API KEY
# ══════════════════════════════════════════

@app.route("/api/config", methods=["GET"])
def get_config():
    cfg = load_config()
    masked_key = ""
    if cfg.get("api_key"):
        key = cfg["api_key"]
        masked_key = key[:8] + "..." + key[-4:] if len(key) > 12 else "***set***"
    return jsonify({
        "has_key": bool(cfg.get("api_key")),
        "masked_key": masked_key,
        "model": cfg.get("model", "claude-sonnet-4-20250514"),
        "max_monthly_spend": cfg.get("max_monthly_spend_per_client", 300)
    })

@app.route("/api/config", methods=["POST"])
def update_config():
    data = request.json
    cfg = load_config()
    # Legacy fields (Settings tab)
    if "api_key" in data and data["api_key"]:
        cfg["api_key"] = data["api_key"]
    if "model" in data:
        cfg["model"] = data["model"]
    if "max_monthly_spend" in data:
        cfg["max_monthly_spend_per_client"] = data["max_monthly_spend"]
    # Setup Wizard fields — save everything from the wizard
    wizard_fields = [
        "business_name", "business_type", "business_description",
        "business_hours", "business_address", "business_phone",
        "business_email", "owner_email", "owner_phone",
        "language", "personality", "llm_provider",
        "modules_enabled", "module_configs",
    ]
    for field in wizard_fields:
        if field in data:
            cfg[field] = data[field]
    save_config(cfg)
    return jsonify({"status": "ok"})

@app.route("/api/config/full", methods=["GET"])
def get_config_full():
    """Return full config (minus API key) for client banner and UI."""
    cfg = load_config()
    safe = {k: v for k, v in cfg.items() if k != "api_key"}
    return jsonify(safe)


def check_module_enabled(module_name):
    """Check if a module is enabled. Returns None if OK, or error response if disabled."""
    cfg = load_config()
    modules = cfg.get("modules_enabled", {})
    if modules and modules.get(module_name) is False:
        return jsonify({"error": f"Module '{module_name}' is not enabled. Enable it in Setup Wizard.", "module_disabled": True}), 403
    return None

@app.route("/api/test-key", methods=["POST"])
def test_key():
    data = request.json
    key = data.get("api_key", "") or get_api_key()
    if not key:
        return jsonify({"valid": False, "message": "No API key provided."})
    valid, message = test_api_key(key)
    return jsonify({"valid": valid, "message": message})


# ══════════════════════════════════════════
# HEARTBEAT ENDPOINTS
# ══════════════════════════════════════════

@app.route("/api/heartbeat/status")
def heartbeat_status():
    hb = _get_heartbeat()
    return jsonify(hb.get_dashboard_summary())

@app.route("/api/heartbeat/start", methods=["POST"])
def heartbeat_start():
    hb = _get_heartbeat()
    hb.start()
    return jsonify({"status": "started", "running": hb.running})

@app.route("/api/heartbeat/stop", methods=["POST"])
def heartbeat_stop():
    hb = _get_heartbeat()
    hb.stop()
    return jsonify({"status": "stopped", "running": hb.running})

@app.route("/api/heartbeat/register", methods=["POST"])
def heartbeat_register():
    data = request.json
    hb = _get_heartbeat()
    entry = hb.register_agent(
        data["agent_id"],
        data.get("agent_type", "generic"),
        data.get("client_id"),
        data.get("metadata")
    )
    return jsonify(entry.to_dict())

@app.route("/api/heartbeat/ping", methods=["POST"])
def heartbeat_ping():
    data = request.json
    hb = _get_heartbeat()
    hb.report_alive(data["agent_id"])
    return jsonify({"status": "ok"})

@app.route("/api/heartbeat/checklist/<client_id>", methods=["GET"])
def get_heartbeat_checklist(client_id):
    hb = _get_heartbeat()
    content = hb.load_heartbeat_checklist(client_id)
    return jsonify({"client_id": client_id, "checklist": content})

@app.route("/api/heartbeat/checklist/<client_id>", methods=["POST"])
def save_heartbeat_checklist(client_id):
    data = request.json
    hb = _get_heartbeat()
    hb.save_heartbeat_checklist(client_id, data.get("content", ""))
    return jsonify({"status": "saved"})

@app.route("/api/heartbeat/log")
def heartbeat_log():
    hb = _get_heartbeat()
    limit = request.args.get("limit", 50, type=int)
    return jsonify({"log": hb.global_log[-limit:]})


# ══════════════════════════════════════════
# API ROUTER ENDPOINTS
# ══════════════════════════════════════════

@app.route("/api/router/status")
def router_status():
    router = _get_router()
    return jsonify(router.get_stats())

@app.route("/api/router/providers")
def router_providers():
    router = _get_router()
    capability = request.args.get("capability")
    return jsonify(router.get_providers(capability))

@app.route("/api/router/capabilities")
def router_capabilities():
    router = _get_router()
    return jsonify({"capabilities": router.get_capabilities()})

@app.route("/api/router/image", methods=["POST"])
def router_image():
    data = request.json
    try:
        from core.api_router import generate_image
        result = generate_image(data["prompt"], data.get("width", 512), data.get("height", 512))
        if "image_data" in result:
            img_dir = os.path.join(PLATFORM_DIR, "data", "generated")
            os.makedirs(img_dir, exist_ok=True)
            filename = f"img_{int(time.time())}.png"
            filepath = os.path.join(img_dir, filename)
            with open(filepath, "wb") as f:
                f.write(result["image_data"])
            result["image_path"] = filepath
            result["image_url"] = f"/data/generated/{filename}"
            del result["image_data"]
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/router/search", methods=["POST"])
def router_search():
    data = request.json
    try:
        from core.api_router import search_web
        result = search_web(data["query"], data.get("max_results", 10))
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/router/tts", methods=["POST"])
def router_tts():
    data = request.json
    try:
        from core.api_router import text_to_speech
        result = text_to_speech(data["text"], data.get("voice", "en-US-AriaNeural"))
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/router/weather", methods=["POST"])
def router_weather():
    data = request.json
    try:
        from core.api_router import get_weather
        result = get_weather(
            location=data.get("location"),
            latitude=data.get("latitude"),
            longitude=data.get("longitude")
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/router/news", methods=["POST"])
def router_news():
    data = request.json or {}
    try:
        from core.api_router import get_news
        result = get_news(data.get("query"))
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/router/translate", methods=["POST"])
def router_translate():
    data = request.json
    try:
        from core.api_router import translate
        result = translate(data["text"], data.get("source", "en"), data.get("target", "es"))
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ══════════════════════════════════════════
# COST TRACKER ENDPOINTS
# ══════════════════════════════════════════

@app.route("/api/costs")
def costs_overview():
    costs = _get_costs()
    return jsonify(costs.get_all_costs())

@app.route("/api/costs/<client_id>")
def costs_client(client_id):
    costs = _get_costs()
    return jsonify(costs.get_client_costs(client_id))

@app.route("/api/costs/<client_id>/budget", methods=["POST"])
def set_budget(client_id):
    data = request.json
    costs = _get_costs()
    costs.set_budget(client_id, data.get("daily_limit"), data.get("monthly_limit"))
    return jsonify({"status": "ok"})

@app.route("/api/costs/<client_id>/check")
def check_budget(client_id):
    costs = _get_costs()
    allowed, reason = costs.check_budget(client_id)
    return jsonify({"allowed": allowed, "reason": reason})


# ══════════════════════════════════════════
# GUARDRAILS ENDPOINTS
# ══════════════════════════════════════════

@app.route("/api/guardrails/rules")
def guardrails_rules():
    gr = _get_guardrails()
    return jsonify(gr.get_rules())

@app.route("/api/guardrails/validate/input", methods=["POST"])
def guardrails_validate_input():
    data = request.json
    gr = _get_guardrails()
    result = gr.validate_input(data.get("text", ""))
    return jsonify(result.to_dict())

@app.route("/api/guardrails/validate/output", methods=["POST"])
def guardrails_validate_output():
    data = request.json
    gr = _get_guardrails()
    result = gr.validate_output(data.get("text", ""))
    return jsonify(result.to_dict())

@app.route("/api/guardrails/log")
def guardrails_log():
    gr = _get_guardrails()
    return jsonify({"log": gr.get_log()})


# ══════════════════════════════════════════
# AGENT REGISTRY & MARKETPLACE
# ══════════════════════════════════════════

@app.route("/api/registry/dashboard")
def registry_dashboard():
    registry = _get_registry()
    return jsonify(registry.get_dashboard())

@app.route("/api/registry/agents")
def registry_list_agents():
    registry = _get_registry()
    client_id = request.args.get("client_id")
    state = request.args.get("state")
    agent_type = request.args.get("type")
    agents = registry.get_all_agents(client_id, state, agent_type)
    return jsonify({"agents": [a.to_dict() for a in agents]})

@app.route("/api/registry/agents/<agent_id>")
def registry_get_agent(agent_id):
    registry = _get_registry()
    agent = registry.get_agent(agent_id)
    if agent:
        return jsonify(agent.to_dict())
    return jsonify({"error": "Agent not found"}), 404

@app.route("/api/registry/agents", methods=["POST"])
def registry_create_agent():
    data = request.json
    registry = _get_registry()
    agent = registry.create_agent(
        data["name"],
        data.get("type", "custom"),
        data.get("client_id"),
        data.get("skill_name"),
        data.get("config"),
        data.get("from_template")
    )
    hb = _get_heartbeat()
    hb.register_agent(agent.id, agent.type, agent.client_id)
    return jsonify(agent.to_dict())

@app.route("/api/registry/agents/<agent_id>/start", methods=["POST"])
def registry_start_agent(agent_id):
    registry = _get_registry()
    success = registry.start_agent(agent_id)
    return jsonify({"started": success})

@app.route("/api/registry/agents/<agent_id>/stop", methods=["POST"])
def registry_stop_agent(agent_id):
    registry = _get_registry()
    success = registry.stop_agent(agent_id)
    return jsonify({"stopped": success})

@app.route("/api/registry/agents/<agent_id>/pause", methods=["POST"])
def registry_pause_agent(agent_id):
    registry = _get_registry()
    success = registry.pause_agent(agent_id)
    return jsonify({"paused": success})

@app.route("/api/registry/agents/<agent_id>", methods=["DELETE"])
def registry_remove_agent(agent_id):
    registry = _get_registry()
    hb = _get_heartbeat()
    hb.unregister_agent(agent_id)
    success = registry.remove_agent(agent_id)
    return jsonify({"removed": success})

@app.route("/api/registry/agents/<agent_id>/message", methods=["POST"])
def registry_send_message(agent_id):
    data = request.json
    registry = _get_registry()
    msg, error = registry.send_message(data["from_agent_id"], agent_id, data["message"], data.get("type", "text"))
    if error:
        return jsonify({"error": error}), 400
    return jsonify(msg)

@app.route("/api/registry/agents/<agent_id>/messages")
def registry_get_messages(agent_id):
    registry = _get_registry()
    agent = registry.get_agent(agent_id)
    if not agent:
        return jsonify({"error": "Agent not found"}), 404
    unread_only = request.args.get("unread", "true").lower() == "true"
    return jsonify({"messages": agent.get_messages(unread_only)})

@app.route("/api/marketplace")
def marketplace_browse():
    registry = _get_registry()
    tag = request.args.get("tag")
    search = request.args.get("search")
    return jsonify({"templates": registry.get_marketplace(tag, search)})

@app.route("/api/marketplace/deploy", methods=["POST"])
def marketplace_deploy():
    data = request.json
    registry = _get_registry()
    agent, error = registry.deploy_from_marketplace(
        data["template_id"],
        data["client_id"],
        data.get("name"),
        data.get("config")
    )
    if error:
        return jsonify({"error": error}), 400
    hb = _get_heartbeat()
    hb.register_agent(agent.id, agent.type, agent.client_id)
    return jsonify(agent.to_dict())


# ══════════════════════════════════════════
# TRACING ENDPOINTS
# ══════════════════════════════════════════

@app.route("/api/tracing/stats")
def tracing_stats():
    tracer = _get_tracer()
    agent_id = request.args.get("agent_id")
    return jsonify(tracer.get_stats(agent_id))

@app.route("/api/tracing/active")
def tracing_active():
    tracer = _get_tracer()
    traces = tracer.get_active_traces()
    return jsonify({"traces": [t.to_dict() for t in traces]})

@app.route("/api/tracing/recent")
def tracing_recent():
    tracer = _get_tracer()
    limit = request.args.get("limit", 50, type=int)
    agent_id = request.args.get("agent_id")
    client_id = request.args.get("client_id")
    traces = tracer.get_recent_traces(limit, agent_id, client_id)
    return jsonify({"traces": [t.to_dict() for t in traces]})

@app.route("/api/tracing/<trace_id>")
def tracing_get(trace_id):
    tracer = _get_tracer()
    trace = tracer.get_trace(trace_id)
    if trace:
        return jsonify(trace.to_dict())
    return jsonify({"error": "Trace not found"}), 404

@app.route("/api/tracing/start", methods=["POST"])
def tracing_start():
    """Start a new trace for an agent operation."""
    data = request.json or {}
    agent_id = data.get("agent_id", "unknown")
    name = data.get("name", data.get("operation", "unnamed"))
    tracer = _get_tracer()
    trace = tracer.start_trace(
        agent_id,
        name,
        data.get("client_id"),
        data.get("metadata")
    )
    return jsonify({"trace_id": trace.id})

@app.route("/api/tracing/<trace_id>/end", methods=["POST"])
def tracing_end(trace_id):
    data = request.json or {}
    tracer = _get_tracer()
    tracer.end_trace(trace_id, data.get("status"))
    return jsonify({"status": "ended"})


# ══════════════════════════════════════════
# APPROVAL ENDPOINTS (Human-in-the-Loop)
# ══════════════════════════════════════════

@app.route("/api/approval/pending")
def approval_pending():
    mgr = _get_approval()
    agent_id = request.args.get("agent_id")
    client_id = request.args.get("client_id")
    pending = mgr.get_pending(agent_id, client_id)
    return jsonify({"pending": [r.to_dict() for r in pending]})

@app.route("/api/approval/history")
def approval_history():
    mgr = _get_approval()
    limit = request.args.get("limit", 50, type=int)
    history = mgr.get_history(limit)
    return jsonify({"history": [r.to_dict() for r in history]})

@app.route("/api/approval/rules")
def approval_rules():
    mgr = _get_approval()
    return jsonify(mgr.get_rules())

@app.route("/api/approval/request", methods=["POST"])
def approval_request():
    data = request.json
    mgr = _get_approval()
    req, status = mgr.request_approval(
        data["agent_id"],
        data["action"],
        data.get("description", ""),
        data.get("client_id"),
        data.get("metadata"),
        data.get("priority"),
        blocking=False
    )
    return jsonify({"request_id": req.id, "status": status})

@app.route("/api/approval/<request_id>/approve", methods=["POST"])
def approval_approve(request_id):
    data = request.json or {}
    mgr = _get_approval()
    success = mgr.approve(request_id, data.get("decided_by", "dashboard"), data.get("reason"))
    return jsonify({"approved": success})

@app.route("/api/approval/<request_id>/deny", methods=["POST"])
def approval_deny(request_id):
    data = request.json or {}
    mgr = _get_approval()
    success = mgr.deny(request_id, data.get("decided_by", "dashboard"), data.get("reason"))
    return jsonify({"denied": success})

@app.route("/api/approval/rules/add", methods=["POST"])
def approval_add_rule():
    data = request.json
    mgr = _get_approval()
    mgr.add_sensitive_action(data["action"], data.get("priority", "medium"))
    return jsonify({"status": "added"})

@app.route("/api/approval/rules/auto", methods=["POST"])
def approval_auto_approve():
    data = request.json
    mgr = _get_approval()
    mgr.set_auto_approve(data["action"], data.get("conditions"))
    return jsonify({"status": "set"})


# ══════════════════════════════════════════
# HANDOFF ENDPOINTS (Agent Delegation)
# ══════════════════════════════════════════

@app.route("/api/handoffs/stats")
def handoffs_stats():
    router = _get_handoffs()
    return jsonify(router.get_stats())

@app.route("/api/handoffs/pending")
def handoffs_pending():
    router = _get_handoffs()
    agent_type = request.args.get("agent_type")
    pending = router.get_pending(agent_type)
    return jsonify({"pending": [h.to_dict() for h in pending]})

@app.route("/api/handoffs/history")
def handoffs_history():
    router = _get_handoffs()
    limit = request.args.get("limit", 50, type=int)
    agent_id = request.args.get("agent_id")
    history = router.get_history(limit, agent_id)
    return jsonify({"history": [h.to_dict() for h in history]})

@app.route("/api/handoffs/request", methods=["POST"])
def handoffs_request():
    data = request.json
    router = _get_handoffs()
    handoff = router.request_handoff(
        data["from_agent_id"],
        data["task_description"],
        data.get("context"),
        data.get("to_agent_id"),
        data.get("to_agent_type"),
        data.get("priority", "medium"),
        data.get("client_id"),
        blocking=False
    )
    return jsonify(handoff.to_dict())

@app.route("/api/handoffs/<handoff_id>/accept", methods=["POST"])
def handoffs_accept(handoff_id):
    data = request.json
    router = _get_handoffs()
    success = router.accept_handoff(handoff_id, data["agent_id"])
    return jsonify({"accepted": success})

@app.route("/api/handoffs/<handoff_id>/complete", methods=["POST"])
def handoffs_complete(handoff_id):
    data = request.json
    router = _get_handoffs()
    success = router.complete_handoff(handoff_id, data.get("result", ""))
    return jsonify({"completed": success})

@app.route("/api/handoffs/<handoff_id>/fail", methods=["POST"])
def handoffs_fail(handoff_id):
    data = request.json
    router = _get_handoffs()
    success = router.fail_handoff(handoff_id, data.get("error", "Unknown error"))
    return jsonify({"failed": success})


# ══════════════════════════════════════════
# EVENT BUS ENDPOINTS
# ══════════════════════════════════════════

@app.route("/api/events/stats")
def events_stats():
    bus = _get_events()
    return jsonify(bus.get_stats())

@app.route("/api/events/types")
def events_types():
    bus = _get_events()
    return jsonify({"types": bus.get_event_types()})

@app.route("/api/events/recent")
def events_recent():
    bus = _get_events()
    limit = request.args.get("limit", 50, type=int)
    event_type = request.args.get("type")
    client_id = request.args.get("client_id")
    events = bus.get_recent_events(limit, event_type, client_id)
    return jsonify({"events": [e.to_dict() for e in events]})

@app.route("/api/events/handlers")
def events_handlers():
    bus = _get_events()
    event_type = request.args.get("type")
    handlers = bus.get_handlers(event_type)
    return jsonify({"handlers": [h.to_dict() for h in handlers]})

@app.route("/api/events/emit", methods=["POST"])
def events_emit():
    data = request.json
    bus = _get_events()
    event = bus.emit(
        data["event_type"],
        data.get("source", "api"),
        data.get("data"),
        data.get("client_id")
    )
    return jsonify(event.to_dict())


# ══════════════════════════════════════════
# VOICE ENDPOINTS (TTS / STT)
# ══════════════════════════════════════════

@app.route("/api/voice/status")
def voice_status():
    voice = _get_voice()
    return jsonify(voice.get_status())

@app.route("/api/voice/voices")
def voice_list():
    voice = _get_voice()
    return jsonify({"voices": voice.get_voices()})

@app.route("/api/voice/tts", methods=["POST"])
def voice_tts():
    data = request.json
    voice = _get_voice()
    filepath, error = voice.text_to_speech(
        data["text"],
        data.get("voice"),
        data.get("client_id"),
        data.get("filename")
    )
    if error:
        return jsonify({"error": error}), 500
    # Return the file path relative to platform for serving
    rel = os.path.relpath(filepath, PLATFORM_DIR)
    return jsonify({"file": rel, "url": f"/platform/{rel.replace(os.sep, '/')}"})

@app.route("/api/voice/stt", methods=["POST"])
def voice_stt():
    data = request.json
    voice = _get_voice()
    text, error = voice.speech_to_text(data["audio_path"], data.get("language"))
    if error:
        return jsonify({"error": error}), 500
    return jsonify({"text": text})

@app.route("/api/voice/client/<client_id>", methods=["POST"])
def voice_set_client(client_id):
    data = request.json
    voice = _get_voice()
    voice.set_client_voice(client_id, data["voice"])
    return jsonify({"status": "ok"})

@app.route("/api/voice/files")
def voice_files():
    voice = _get_voice()
    client_id = request.args.get("client_id")
    return jsonify({"files": voice.list_audio_files(client_id)})

@app.route("/api/voice/chat", methods=["POST"])
def voice_chat():
    """Voice chat — send text (from speech recognition), get AI response as audio.
    Combines chat + TTS in one call. The browser handles mic → text via Web Speech API."""
    data = request.json
    message = data.get("message", "")
    client_id = data.get("client_id", "platform")
    voice_name = data.get("voice", "en-US-GuyNeural")
    conversation_id = data.get("conversation_id", "voice_default")

    if not message:
        return jsonify({"error": "No message"})

    # Get AI response (reuse chat logic)
    conv_dir = os.path.join(PLATFORM_DIR, "data", "conversations", client_id)
    os.makedirs(conv_dir, exist_ok=True)
    conv_file = os.path.join(conv_dir, f"{conversation_id}.json")

    if os.path.exists(conv_file):
        with open(conv_file) as f:
            history = json.load(f)
    else:
        history = {"messages": [], "created": datetime.now().isoformat()}

    history["messages"].append({"role": "user", "content": message})
    messages = history["messages"][-30:]

    system_prompt = "You are a voice assistant running inside the Janovum toolkit. Keep responses concise and conversational — they will be spoken aloud. Avoid code blocks, markdown, and long paragraphs. Be natural and direct."

    # Try local auth first
    result = None
    creds = _get_claude_code_credentials()
    if creds and not creds["is_expired"]:
        result = _call_claude_with_local_auth(messages, system_prompt)
    if not result or "error" in result:
        try:
            failover = _get_failover()
            result = failover.call(messages, system_prompt)
        except Exception:
            result = call_claude(messages=messages, system_prompt=system_prompt)

    if "error" in result:
        return jsonify({"error": result["error"]})

    response_text = result.get("text", "")
    history["messages"].append({"role": "assistant", "content": response_text})
    history["updated"] = datetime.now().isoformat()
    with open(conv_file, "w") as f:
        json.dump(history, f, indent=2)

    # Generate TTS audio
    import asyncio
    try:
        import edge_tts
        audio_dir = os.path.join(PLATFORM_DIR, "data", "audio")
        os.makedirs(audio_dir, exist_ok=True)
        audio_file = f"voice_{int(time.time())}.mp3"
        audio_path = os.path.join(audio_dir, audio_file)

        async def gen():
            comm = edge_tts.Communicate(response_text, voice_name)
            await comm.save(audio_path)

        asyncio.run(gen())
        audio_url = f"/platform/data/audio/{audio_file}"
    except Exception as e:
        audio_url = None

    return jsonify({
        "response": response_text,
        "audio_url": audio_url,
        "model": result.get("model", ""),
        "provider": result.get("provider", ""),
        "voice": voice_name
    })

@app.route("/api/voice/speak", methods=["POST"])
def voice_speak():
    """Just convert text to speech — no AI, just TTS."""
    data = request.json
    text = data.get("text", "")
    voice_name = data.get("voice", "en-US-GuyNeural")
    if not text:
        return jsonify({"error": "No text"})

    import asyncio
    try:
        import edge_tts
        audio_dir = os.path.join(PLATFORM_DIR, "data", "audio")
        os.makedirs(audio_dir, exist_ok=True)
        audio_file = f"speak_{int(time.time())}.mp3"
        audio_path = os.path.join(audio_dir, audio_file)

        async def gen():
            comm = edge_tts.Communicate(text, voice_name)
            await comm.save(audio_path)

        asyncio.run(gen())
        return jsonify({"audio_url": f"/platform/data/audio/{audio_file}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/voice/speak/sentences", methods=["POST"])
def voice_speak_sentences():
    """Generate TTS for multiple sentences in parallel — returns URLs for each chunk."""
    data = request.json
    text = data.get("text", "")
    voice_name = data.get("voice", "en-US-JennyNeural")
    if not text:
        return jsonify({"error": "No text"})

    import asyncio, re as _re
    # Split into sentences
    sentences = _re.split(r'(?<=[.!?])\s+', text.strip())
    sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 1]
    if not sentences:
        sentences = [text]

    try:
        import edge_tts
        audio_dir = os.path.join(PLATFORM_DIR, "data", "audio")
        os.makedirs(audio_dir, exist_ok=True)

        results = []
        ts = int(time.time() * 1000)

        async def gen_all():
            tasks = []
            for i, sentence in enumerate(sentences):
                fname = f"chunk_{ts}_{i}.mp3"
                fpath = os.path.join(audio_dir, fname)
                async def gen_one(s=sentence, fp=fpath):
                    comm = edge_tts.Communicate(s, voice_name)
                    await comm.save(fp)
                tasks.append(gen_one())
                results.append({"text": sentence, "audio_url": f"/platform/data/audio/{fname}"})
            await asyncio.gather(*tasks)

        asyncio.run(gen_all())
        return jsonify({"chunks": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/platform/<path:filename>")
def serve_platform_file(filename):
    return send_from_directory(PLATFORM_DIR, filename)


# ══════════════════════════════════════════
# SANDBOX ENDPOINTS (Code Execution)
# ══════════════════════════════════════════

@app.route("/api/sandbox/stats")
def sandbox_stats():
    sb = _get_sandbox()
    return jsonify(sb.get_stats())

@app.route("/api/sandbox/python", methods=["POST"])
def sandbox_python():
    data = request.json
    sb = _get_sandbox()
    result = sb.execute_python(
        data["code"],
        data.get("timeout"),
        data.get("env_vars"),
        data.get("working_dir")
    )
    return jsonify(result.to_dict())

@app.route("/api/sandbox/shell", methods=["POST"])
def sandbox_shell():
    data = request.json
    sb = _get_sandbox()
    result = sb.execute_shell(data["command"], data.get("timeout"))
    return jsonify(result.to_dict())

@app.route("/api/sandbox/log")
def sandbox_log():
    sb = _get_sandbox()
    limit = request.args.get("limit", 50, type=int)
    return jsonify({"log": sb.get_log(limit)})


# ══════════════════════════════════════════
# MODEL FAILOVER ENDPOINTS
# ══════════════════════════════════════════

@app.route("/api/failover/status")
def failover_status():
    fo = _get_failover()
    return jsonify({"providers": fo.get_status()})

@app.route("/api/failover/call", methods=["POST"])
def failover_call():
    data = request.json
    fo = _get_failover()
    result = fo.call(
        data["messages"],
        data.get("system_prompt"),
        data.get("max_tokens", 4096),
        data.get("preferred_provider")
    )
    return jsonify(result)


# ══════════════════════════════════════════
# SOUL ENDPOINTS (Agent Personality)
# ══════════════════════════════════════════

@app.route("/api/soul/list")
def soul_list():
    soul = _get_soul()
    return jsonify({"souls": soul.list_souls()})

@app.route("/api/soul/get")
def soul_get():
    soul = _get_soul()
    agent_id = request.args.get("agent_id")
    client_id = request.args.get("client_id")
    return jsonify({
        "soul": soul.get_soul(agent_id, client_id),
        "rules": soul.get_rules(agent_id, client_id)
    })

@app.route("/api/soul/set", methods=["POST"])
def soul_set():
    data = request.json
    soul = _get_soul()
    if "soul" in data:
        soul.set_soul(data["soul"], data.get("agent_id"), data.get("client_id"))
    if "rules" in data:
        soul.set_rules(data["rules"], data.get("agent_id"), data.get("client_id"))
    return jsonify({"status": "ok"})

@app.route("/api/soul/prompt")
def soul_prompt():
    soul = _get_soul()
    agent_id = request.args.get("agent_id")
    client_id = request.args.get("client_id")
    skill = request.args.get("skill", "")
    prompt = soul.build_system_prompt(agent_id, client_id, skill)
    return jsonify({"system_prompt": prompt})


# ══════════════════════════════════════════
# AUTH / OAUTH ENDPOINTS
# ══════════════════════════════════════════

@app.route("/api/auth/status")
def auth_status():
    """Get auth status for a client."""
    auth = _get_auth()
    client_id = request.args.get("client_id", "default")
    return jsonify(auth.get_auth_status(client_id))

@app.route("/api/auth/oauth/config", methods=["GET"])
def auth_oauth_config():
    """Check if OAuth is configured."""
    auth = _get_auth()
    return jsonify({
        "configured": auth.is_oauth_configured(),
        "redirect_uri": auth.oauth_config.get("redirect_uri", ""),
        "has_client_id": bool(auth.oauth_config.get("client_id")),
    })

@app.route("/api/auth/oauth/config", methods=["POST"])
def auth_oauth_set_config():
    """Set OAuth client_id and client_secret."""
    data = request.json
    auth = _get_auth()
    auth.save_oauth_config(data)
    return jsonify({"status": "ok", "configured": auth.is_oauth_configured()})

@app.route("/api/auth/oauth/login", methods=["POST"])
def auth_oauth_login():
    """Start OAuth login — returns the URL to redirect the user to."""
    data = request.json or {}
    client_id = data.get("client_id", "default")
    auth = _get_auth()
    url, state_or_error = auth.get_oauth_url(client_id)
    if url:
        return jsonify({"url": url, "state": state_or_error})
    return jsonify({"error": state_or_error}), 400

@app.route("/auth/callback")
def auth_oauth_callback():
    """OAuth callback — Anthropic redirects here after user approves."""
    code = request.args.get("code")
    state = request.args.get("state")
    error = request.args.get("error")

    if error:
        return f"""<html><body style="background:#0a0a0a;color:#e0e0e0;font-family:sans-serif;text-align:center;padding:80px">
        <h1 style="color:#ff6b35">OAuth Error</h1><p>{error}</p>
        <a href="/" style="color:#f7c948">Back to Dashboard</a></body></html>"""

    if not code or not state:
        return f"""<html><body style="background:#0a0a0a;color:#e0e0e0;font-family:sans-serif;text-align:center;padding:80px">
        <h1 style="color:#ff6b35">Missing Parameters</h1><p>No auth code received.</p>
        <a href="/" style="color:#f7c948">Back to Dashboard</a></body></html>"""

    auth = _get_auth()
    token, err = auth.handle_oauth_callback(code, state)
    if err:
        return f"""<html><body style="background:#0a0a0a;color:#e0e0e0;font-family:sans-serif;text-align:center;padding:80px">
        <h1 style="color:#ff6b35">Login Failed</h1><p>{err}</p>
        <a href="/" style="color:#f7c948">Back to Dashboard</a></body></html>"""

    user = token.user_info.get("name", token.user_info.get("email", "User"))
    return f"""<html><body style="background:#0a0a0a;color:#e0e0e0;font-family:sans-serif;text-align:center;padding:80px">
    <h1 style="color:#2ecc71">Connected!</h1>
    <p>Welcome, <strong style="color:#f7c948">{user}</strong></p>
    <p>Your Claude subscription is now linked to Janovum.</p>
    <script>setTimeout(()=>window.location='/',2000)</script>
    </body></html>"""

@app.route("/api/auth/oauth/disconnect", methods=["POST"])
def auth_oauth_disconnect():
    """Disconnect OAuth for a client."""
    data = request.json or {}
    client_id = data.get("client_id", "default")
    auth = _get_auth()
    auth.disconnect_oauth(client_id)
    return jsonify({"status": "disconnected"})

@app.route("/api/auth/client-key", methods=["POST"])
def auth_set_client_key():
    """Set a client-specific API key."""
    data = request.json
    auth = _get_auth()
    auth.set_client_api_key(data["client_id"], data["api_key"])
    return jsonify({"status": "ok"})


# ══════════════════════════════════════════
# AI QUICK ASK (guardrails + cost tracking + tracing)
# ══════════════════════════════════════════

@app.route("/api/quick-ask", methods=["POST"])
def api_quick_ask():
    data = request.json
    prompt = data.get("prompt", "")
    client_id = data.get("client_id", "platform")

    if not prompt:
        return jsonify({"error": "No prompt provided"})

    # Guardrails check
    gr = _get_guardrails()
    input_check = gr.validate_input(prompt)
    if not input_check.passed:
        return jsonify({"error": input_check.message, "blocked_by": "guardrails"})

    # Budget check
    costs = _get_costs()
    allowed, reason = costs.check_budget(client_id)
    if not allowed:
        return jsonify({"error": reason, "blocked_by": "budget"})

    # Start trace
    tracer = _get_tracer()
    trace = tracer.start_trace("quick-ask", "quick_ask", client_id)

    # Make the call
    result = call_claude(
        messages=[{"role": "user", "content": prompt}],
        system_prompt=data.get("system_prompt")
    )

    if "error" in result:
        tracer.end_trace(trace.id, "error")
        return jsonify({"error": result["error"]})

    # Track cost
    usage = result.get("usage", {})
    model_used = pick_model(prompt)
    costs.record_usage(
        client_id, model_used,
        usage.get("input_tokens", 0),
        usage.get("output_tokens", 0)
    )

    # Guardrails check on output
    output_text = result.get("text", "")
    output_check = gr.validate_output(output_text)
    if not output_check.passed:
        tracer.end_trace(trace.id, "blocked")
        return jsonify({"error": output_check.message, "blocked_by": "guardrails"})

    tracer.end_trace(trace.id, "ok")
    return jsonify({"response": output_text, "model": result.get("model_used", ""), "usage": usage})


# ══════════════════════════════════════════
# CLIENT MANAGEMENT
# ══════════════════════════════════════════

@app.route("/api/clients", methods=["GET"])
def list_clients():
    clients_dir = os.path.join(PLATFORM_DIR, "clients")
    clients = []
    if os.path.exists(clients_dir):
        for f in os.listdir(clients_dir):
            if f.endswith(".json") and not f.endswith("_results.json"):
                with open(os.path.join(clients_dir, f)) as fh:
                    cfg = json.load(fh)
                    clients.append({
                        "id": f.replace(".json", ""),
                        "name": cfg.get("client_name", f),
                        "modules": cfg.get("enabled_modules", [])
                    })
    return jsonify(clients)

@app.route("/api/clients/<client_id>", methods=["GET"])
def get_client(client_id):
    path = os.path.join(PLATFORM_DIR, "clients", f"{client_id}.json")
    if os.path.exists(path):
        with open(path) as f:
            return jsonify(json.load(f))
    return jsonify({"error": "Client not found"}), 404

@app.route("/api/clients/<client_id>", methods=["POST"])
def save_client(client_id):
    data = request.json
    path = os.path.join(PLATFORM_DIR, "clients", f"{client_id}.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    return jsonify({"status": "ok"})


# ══════════════════════════════════════════
# WEBHOOK ENDPOINTS
# ══════════════════════════════════════════

@app.route("/api/webhook/lead", methods=["POST"])
def webhook_lead():
    data = request.json
    client_id = data.get("client_id", "default")
    # Emit event on the bus
    _get_events().emit("webhook_received", "webhook", {"type": "lead", "data": data}, client_id)
    client_config_path = os.path.join(PLATFORM_DIR, "clients", f"{client_id}.json")
    if os.path.exists(client_config_path):
        with open(client_config_path) as f:
            client_config = json.load(f)
    else:
        client_config = {"client_name": client_id, "auto_send_leads": False}
    from modules.lead_responder import handle_webhook
    result = handle_webhook(data, client_config)
    return jsonify(result)

@app.route("/api/webhook/<source>", methods=["POST"])
def receive_webhook(source):
    data = request.json or {}
    # Emit event on the bus
    _get_events().emit("webhook_received", source, data, data.get("client_id"))
    try:
        from modules.webhook_receiver import process_webhook
        result = process_webhook(source, data)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ══════════════════════════════════════════
# AGENT VIEWER / SCREENSHOTS / STATIC
# ══════════════════════════════════════════

SCREENSHOT_DIR = os.path.join(PLATFORM_DIR, "agent_screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

@app.route("/agent-viewer")
def agent_viewer():
    viewer_path = os.path.expanduser("~/OneDrive/Desktop")
    return send_from_directory(viewer_path, "Agent_Viewer.html")

@app.route("/screenshots/<path:filename>")
def serve_screenshot(filename):
    return send_from_directory(SCREENSHOT_DIR, filename)

@app.route("/data/generated/<path:filename>")
def serve_generated(filename):
    gen_dir = os.path.join(PLATFORM_DIR, "data", "generated")
    return send_from_directory(gen_dir, filename)


# ══════════════════════════════════════════
# CDP PROXY (live streaming)
# ══════════════════════════════════════════

@app.route("/api/cdp/<int:port>/json")
def cdp_proxy_json(port):
    import urllib.request
    try:
        resp = urllib.request.urlopen(f"http://127.0.0.1:{port}/json", timeout=3)
        pages = json.loads(resp.read())
        for page in pages:
            if page.get("webSocketDebuggerUrl"):
                page["wsDirect"] = page["webSocketDebuggerUrl"]
        return jsonify(pages)
    except Exception as e:
        return jsonify({"error": str(e)}), 502

@app.route("/api/cdp/<int:port>/screenshot")
def cdp_proxy_screenshot(port):
    data, error = _cdp_screenshot(port)
    if data:
        conn = _cdp_connections.get(port, {})
        return jsonify({
            "data": data,
            "url": conn.get("page_url", ""),
            "title": conn.get("page_title", "")
        })
    status = 502 if "connection" in (error or "").lower() else 404
    return jsonify({"error": error or "Unknown error"}), status

@app.route("/api/cdp/ports")
def cdp_active_ports():
    ports = []
    for port, conn in _cdp_connections.items():
        ports.append({
            "port": port,
            "url": conn.get("page_url", ""),
            "title": conn.get("page_title", ""),
            "age": int(time.time() - conn.get("created", 0))
        })
    return jsonify({"ports": ports})


# ══════════════════════════════════════════
# AGENT LAUNCH/STOP (legacy + new)
# ══════════════════════════════════════════

@app.route("/api/agent/screenshots", methods=["GET"])
def get_agent_screenshots():
    agents = []
    if os.path.exists(SCREENSHOT_DIR):
        for f in os.listdir(SCREENSHOT_DIR):
            if f.endswith("_meta.json"):
                with open(os.path.join(SCREENSHOT_DIR, f)) as fh:
                    agents.append(json.load(fh))
    return jsonify({"agents": agents})

@app.route("/api/agent/launch", methods=["POST"])
def launch_agent():
    data = request.json
    agent_type = data.get("type", "browser")
    target = data.get("target", "")

    registry = _get_registry()
    agent = registry.create_agent(
        name=f"{agent_type} agent",
        agent_type=agent_type,
        client_id=data.get("client_id"),
        config={"target": target}
    )
    registry.start_agent(agent.id)

    hb = _get_heartbeat()
    hb.register_agent(agent.id, agent_type, data.get("client_id"))

    # Emit event
    _get_events().emit("agent_started", "registry", {"agent_id": agent.id, "type": agent_type})

    def run_agent():
        try:
            if agent_type == "reddit":
                from modules.reddit_agent import get_driver, browse_subreddit
                driver = get_driver()
                try:
                    subreddit = target.replace("r/", "").replace("/", "")
                    browse_subreddit(driver, agent.id, subreddit)
                finally:
                    driver.quit()
            else:
                from modules.browser_agent import get_driver
                driver = get_driver()
                try:
                    url = target if target.startswith("http") else f"https://{target}"
                    driver.get(url)
                    time.sleep(3)
                    screenshot_path = os.path.join(SCREENSHOT_DIR, f"{agent.id}_latest.png")
                    driver.save_screenshot(screenshot_path)
                    meta = {
                        "agent_id": agent.id,
                        "timestamp": datetime.now().isoformat(),
                        "step": "browsing",
                        "url": driver.current_url,
                        "title": driver.title,
                        "screenshot": f"{agent.id}_latest.png"
                    }
                    with open(os.path.join(SCREENSHOT_DIR, f"{agent.id}_meta.json"), "w") as f:
                        json.dump(meta, f)
                finally:
                    driver.quit()

            hb.report_alive(agent.id)
            registry.stop_agent(agent.id)
            _get_events().emit("agent_completed", "registry", {"agent_id": agent.id})
        except Exception as e:
            print(f"[agent] Error: {e}")
            registry.get_agent(agent.id).record_error(str(e))

    thread = threading.Thread(target=run_agent, daemon=True)
    thread.start()
    return jsonify({"status": "launched", "agent_id": agent.id})

@app.route("/api/agent/stop", methods=["POST"])
def stop_agent():
    data = request.json
    agent_id = data.get("agent_id", "")
    registry = _get_registry()
    registry.stop_agent(agent_id)
    hb = _get_heartbeat()
    hb.unregister_agent(agent_id)
    meta_path = os.path.join(SCREENSHOT_DIR, f"{agent_id}_meta.json")
    if os.path.exists(meta_path):
        with open(meta_path) as f:
            meta = json.load(f)
        meta["status"] = "stopped"
        with open(meta_path, "w") as f:
            json.dump(meta, f)
    return jsonify({"status": "stopped", "agent_id": agent_id})


# ══════════════════════════════════════════
# MODULE START/STOP
# ══════════════════════════════════════════

@app.route("/api/module/start", methods=["POST"])
def start_module():
    data = request.json
    return jsonify({"status": "started", "module": data.get("module_name", "")})

@app.route("/api/module/stop", methods=["POST"])
def stop_module():
    data = request.json
    return jsonify({"status": "stopped", "module_id": data.get("module_id", "")})


# ══════════════════════════════════════════
# LISTING & ROI
# ══════════════════════════════════════════

@app.route("/api/listing/create", methods=["POST"])
def create_listing():
    data = request.json
    message = data.get("message", "")
    client_id = data.get("client_id", "default")
    if not message:
        return jsonify({"error": "No listing message provided"})
    client_config_path = os.path.join(PLATFORM_DIR, "clients", f"{client_id}.json")
    if os.path.exists(client_config_path):
        with open(client_config_path) as f:
            client_config = json.load(f)
    else:
        client_config = {"client_name": client_id}
    from modules.listing_poster import create_listing as do_create
    result = do_create(message, client_config)
    return jsonify(result, default=str)

@app.route("/api/roi/scan", methods=["POST"])
def roi_scan():
    data = request.json
    client_id = data.get("client_id", "default")
    client_config_path = os.path.join(PLATFORM_DIR, "clients", f"{client_id}.json")
    if os.path.exists(client_config_path):
        with open(client_config_path) as f:
            client_config = json.load(f)
    else:
        return jsonify({"error": f"Client config not found: {client_id}"})
    from modules.roi_scanner import run_scan
    result = run_scan(client_config)
    return jsonify(result, default=str)


# ══════════════════════════════════════════
# CLAUDE CODE LOCAL AUTH (use existing Claude login)
# ══════════════════════════════════════════

def _get_claude_code_credentials():
    """Read Claude Code's stored OAuth credentials from ~/.claude/.credentials.json"""
    creds_path = os.path.expanduser("~/.claude/.credentials.json")
    if not os.path.exists(creds_path):
        return None
    try:
        with open(creds_path) as f:
            data = json.load(f)
        oauth = data.get("claudeAiOauth", {})
        if oauth.get("accessToken"):
            return {
                "access_token": oauth["accessToken"],
                "refresh_token": oauth.get("refreshToken"),
                "expires_at": oauth.get("expiresAt"),
                "subscription": oauth.get("subscriptionType", "unknown"),
                "scopes": oauth.get("scopes", []),
                "rate_limit_tier": oauth.get("rateLimitTier", ""),
                "is_expired": oauth.get("expiresAt", 0) < time.time() * 1000 if oauth.get("expiresAt") else False
            }
    except Exception:
        pass
    return None

def _call_claude_with_local_auth(messages, system_prompt=None, max_tokens=4096):
    """Make Claude API call using locally stored Claude Code OAuth token."""
    creds = _get_claude_code_credentials()
    if not creds or not creds["access_token"]:
        return {"error": "No Claude Code credentials found. Run 'claude' in terminal and log in first."}

    import requests as req
    headers = {
        "Authorization": f"Bearer {creds['access_token']}",
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    # Smart model picking — cheapest first
    from core.engine import pick_model, MODELS
    msg_text = " ".join(m.get("content", "") for m in messages[-3:])
    model_key = pick_model(msg_text)
    model_id = MODELS.get(model_key, "claude-haiku-4-5-20251001")

    body = {
        "model": model_id,
        "max_tokens": max_tokens,
        "messages": messages
    }
    if system_prompt:
        body["system"] = system_prompt

    try:
        resp = req.post("https://api.anthropic.com/v1/messages", headers=headers, json=body, timeout=120)
        if resp.status_code == 200:
            data = resp.json()
            text = ""
            for block in data.get("content", []):
                if block.get("type") == "text":
                    text += block.get("text", "")
            return {
                "text": text,
                "model": data.get("model", ""),
                "usage": data.get("usage", {}),
                "provider": "claude_local_auth",
                "subscription": creds["subscription"]
            }
        else:
            return {"error": f"Claude API returned {resp.status_code}: {resp.text[:200]}"}
    except Exception as e:
        return {"error": str(e)}

@app.route("/api/auth/local")
def auth_local_status():
    """Check if Claude Code is logged in on this machine."""
    creds = _get_claude_code_credentials()
    if creds:
        return jsonify({
            "logged_in": True,
            "subscription": creds["subscription"],
            "scopes": creds["scopes"],
            "rate_limit_tier": creds["rate_limit_tier"],
            "is_expired": creds["is_expired"],
            "method": "claude_code_oauth"
        })
    return jsonify({"logged_in": False, "method": None})

@app.route("/api/auth/local/test", methods=["POST"])
def auth_local_test():
    """Test the local Claude Code auth with a simple call."""
    result = _call_claude_with_local_auth(
        [{"role": "user", "content": "Say 'Janovum connected!' in 5 words or less."}]
    )
    if "error" in result:
        return jsonify({"success": False, "error": result["error"]})
    return jsonify({"success": True, "response": result.get("text", ""), "subscription": result.get("subscription", "")})


# ══════════════════════════════════════════
# CHAT TERMINAL (Interactive AI Conversation)
# ══════════════════════════════════════════

@app.route("/api/chat/send", methods=["POST"])
def chat_send():
    """Send a message in the chat terminal — full AI conversation with tools."""
    data = request.json
    message = data.get("message", "")
    client_id = data.get("client_id", "platform")
    conversation_id = data.get("conversation_id", "default")
    system_prompt = data.get("system_prompt")

    if not message:
        return jsonify({"error": "No message provided"})

    # Guardrails check
    gr = _get_guardrails()
    input_check = gr.validate_input(message)
    if not input_check.passed:
        return jsonify({"error": input_check.message, "blocked_by": "guardrails"})

    # Budget check
    costs = _get_costs()
    allowed, reason = costs.check_budget(client_id)
    if not allowed:
        return jsonify({"error": reason, "blocked_by": "budget"})

    # Load conversation history
    conv_dir = os.path.join(PLATFORM_DIR, "data", "conversations", client_id)
    os.makedirs(conv_dir, exist_ok=True)
    conv_file = os.path.join(conv_dir, f"{conversation_id}.json")

    if os.path.exists(conv_file):
        with open(conv_file) as f:
            history = json.load(f)
    else:
        history = {"messages": [], "created": datetime.now().isoformat()}

    # Add user message to history
    history["messages"].append({"role": "user", "content": message})

    # Build messages for Claude (keep last 50 messages for context)
    messages = history["messages"][-50:]

    # Get soul/system prompt if configured
    if not system_prompt:
        try:
            soul = _get_soul()
            system_prompt = soul.build_system_prompt(client_id=client_id)
        except Exception:
            system_prompt = "You are a helpful AI assistant running inside the Janovum toolkit. You can help with coding, analysis, automation, and more."

    # Start trace
    tracer = _get_tracer()
    trace = tracer.start_trace("chat", "chat_message", client_id)

    # Priority: local Claude Code auth → failover chain → direct API key
    use_local = data.get("use_local_auth", True)
    result = None
    if use_local:
        creds = _get_claude_code_credentials()
        if creds and not creds["is_expired"]:
            result = _call_claude_with_local_auth(messages, system_prompt)
    if not result or "error" in result:
        try:
            failover = _get_failover()
            result = failover.call(messages, system_prompt)
        except Exception:
            result = call_claude(messages=messages, system_prompt=system_prompt)

    if "error" in result:
        tracer.end_trace(trace.id, "error")
        return jsonify({"error": result["error"]})

    response_text = result.get("text", "")

    # Track cost
    usage = result.get("usage", {})
    model_used = result.get("model", result.get("model_used", "unknown"))
    try:
        costs.record_usage(client_id, model_used, usage.get("input_tokens", 0), usage.get("output_tokens", 0))
    except Exception:
        pass

    # Guardrails check on output
    output_check = gr.validate_output(response_text)
    if not output_check.passed:
        tracer.end_trace(trace.id, "blocked")
        return jsonify({"error": output_check.message, "blocked_by": "guardrails"})

    # Add assistant response to history
    history["messages"].append({"role": "assistant", "content": response_text})
    history["updated"] = datetime.now().isoformat()

    # Save conversation
    with open(conv_file, "w") as f:
        json.dump(history, f, indent=2)

    # Emit event
    _get_events().emit("chat_message", "chat", {"client_id": client_id, "conversation_id": conversation_id})

    tracer.end_trace(trace.id, "ok")

    return jsonify({
        "response": response_text,
        "model": model_used,
        "provider": result.get("provider", "anthropic"),
        "usage": usage,
        "conversation_id": conversation_id
    })

@app.route("/api/receptionist/test", methods=["POST"])
def receptionist_test():
    """Test the AI receptionist using free Pollinations API — no API key needed."""
    gate = check_module_enabled("ai_receptionist")
    if gate: return gate
    data = request.json
    message = data.get("message", "")
    history = data.get("history", [])

    if not message:
        return jsonify({"error": "No message"})

    # Build receptionist system prompt from config
    cfg = load_config()
    biz_name = cfg.get("business_name", "the business")
    biz_type = cfg.get("business_type", "business")
    biz_hours = cfg.get("business_hours", "Mon-Fri 9am-5pm")
    biz_phone = cfg.get("business_phone", "")
    biz_email = cfg.get("business_email", "")
    biz_addr = cfg.get("business_address", "")
    personality = cfg.get("personality", "friendly and professional")
    language = cfg.get("language", "English")

    # Get receptionist-specific config
    mod_cfgs = cfg.get("module_configs", {})
    rec_cfg = mod_cfgs.get("ai_receptionist", {})
    services = rec_cfg.get("services_offered", "various services")
    prices = rec_cfg.get("service_prices", "")
    staff = rec_cfg.get("staff_names", "")
    greeting = rec_cfg.get("greeting_style", "")
    after_hours = rec_cfg.get("after_hours_message", "We're closed right now but I can help!")
    special = rec_cfg.get("special_instructions", "")

    # Check if currently within business hours
    current_time = datetime.now()
    current_hour = current_time.hour
    current_day = current_time.strftime("%A")
    hours_context = f"\nCURRENT TIME: {current_time.strftime('%I:%M %p')}, {current_day}"
    # Simple heuristic: if hours contain "9am-5pm" or similar, parse it
    is_open = True  # Default to open
    if biz_hours:
        hours_lower = biz_hours.lower()
        if "closed" in hours_lower and current_day.lower() in hours_lower:
            is_open = False
        elif current_hour < 8 or current_hour >= 20:
            is_open = False  # Most businesses closed before 8am or after 8pm
    hours_context += f"\nBUSINESS IS: {'OPEN' if is_open else 'CLOSED (after hours)'}"
    if not is_open:
        hours_context += f"\nSince the business is closed, use the after-hours behavior: be helpful, take messages, book appointments for the next open day."

    # Get existing appointments for context
    appt_file = os.path.join(PLATFORM_DIR, "data", "appointments.json")
    existing_appts = []
    if os.path.exists(appt_file):
        try:
            with open(appt_file) as f:
                existing_appts = json.load(f)
            # Show only upcoming ones
            existing_appts = [a for a in existing_appts if a.get("status") != "cancelled"][-20:]
        except: pass

    appt_context = ""
    if existing_appts:
        appt_lines = []
        for a in existing_appts[-10:]:
            appt_lines.append(f"  - {a.get('date','?')} {a.get('time','?')}: {a.get('name','?')} for {a.get('service','?')}")
        appt_context = "EXISTING APPOINTMENTS (check for conflicts):\n" + "\n".join(appt_lines)

    system_prompt = f"""You are a real human receptionist who works at {biz_name}, a {biz_type}. You're answering the phone right now.
{hours_context}

TALK LIKE A REAL PERSON. You are NOT a robot. You are NOT an AI assistant. You're just a friendly person at the front desk picking up the phone. Use casual, natural language. Say things like "yeah", "sure thing", "no worries", "let me check", "gotcha". Use contractions (don't, we're, that'll). Don't be overly formal or corporate.

CRITICAL RULES:
- Keep responses SHORT — 1-2 sentences max. Real receptionists don't give speeches.
- NEVER say "Great question!" or "I'd be happy to help!" or any robotic filler phrases.
- NEVER introduce yourself as an AI or virtual assistant. You're just the person at the front desk.
- Sound natural. If someone says "hey" you say "hey, what's up?" not "Hello! Thank you for calling!"
- Match the caller's energy. If they're casual, be casual. If they're formal, be a little more professional.
- Don't over-explain. Answer the question and stop.
- If you don't know something, say "hmm, I'm not sure about that, let me check" or "I'd have to ask the boss about that."

{"Your vibe: " + personality if personality else ""}

BUSINESS INFO (use when asked):
- {biz_name} | {biz_type}
{"- Located at: " + biz_addr if biz_addr else ""}
{"- Phone: " + biz_phone if biz_phone else ""}
{"- Email: " + biz_email if biz_email else ""}
- Hours: {biz_hours}
- Services: {services}
{"- Prices: " + prices if prices else ""}
{"- Staff: " + staff if staff else ""}
{"- " + special if special else ""}

{appt_context}

ACTIONS YOU CAN TAKE:
When you need to perform an action, include an ACTION tag at the END of your response (after what you say to the caller). The caller won't see these tags — they're processed by the system.

1. BOOK AN APPOINTMENT — when caller wants to schedule:
   First collect: their name, phone number, what service, preferred date and time, and optionally which staff member.
   Once you have all info, confirm it back to them, then add:
   [ACTION:BOOK|name=John Smith|phone=305-555-1234|service=Haircut|date=March 15|time=2:00 PM|staff=Tony|notes=first time customer]

2. TAKE A MESSAGE — when caller wants to leave a message for the owner/staff:
   Collect: their name, phone number, and the message.
   [ACTION:MESSAGE|name=Jane Doe|phone=305-555-5678|message=Wants to discuss a partnership opportunity|urgent=no]

3. SEND NOTIFICATION — when something needs immediate owner attention:
   [ACTION:NOTIFY|type=urgent|message=Customer complaint about billing issue from John at 305-555-1234]

IMPORTANT:
- ALWAYS collect name AND phone number before booking or taking a message.
- Confirm the appointment details back to the caller before adding the ACTION tag.
- Only add ONE action tag per response.
- Keep talking naturally — the action tag goes at the very end, after your spoken response.
- If a requested time conflicts with an existing appointment, suggest a different time.

{"Start with something like: " + greeting.replace('{name}', biz_name) if greeting else ""}
{"After hours say: " + after_hours if after_hours else ""}"""

    # Add custom tools to the system prompt
    custom_tools = rec_cfg.get("custom_tools", [])
    if custom_tools:
        tools_prompt = "\n\nCUSTOM TOOLS AVAILABLE:\nYou have access to these lookup tools. When you need data, add a LOOKUP tag at the end of your response:\n"
        for i, tool in enumerate(custom_tools):
            if tool.get("name") and tool.get("when_to_use"):
                tools_prompt += f"\n{i+1}. {tool['name']}: {tool['when_to_use']}\n"
                tools_prompt += f"   To use: [LOOKUP:{tool['name']}|query=what to search for]\n"
        tools_prompt += "\nWhen you get lookup results back, use them naturally in conversation. Don't mention APIs or lookups to the caller — just say the info like you looked it up on your computer."
        system_prompt += tools_prompt

    # Use free LLM APIs — try multiple providers with retry
    try:
        import requests as req_lib
        import time as _time
        messages_for_api = []
        for m in history[-20:]:
            messages_for_api.append({"role": m["role"], "content": m["content"]})
        messages_for_api.append({"role": "user", "content": message})

        full_messages = [{"role": "system", "content": system_prompt}] + messages_for_api

        # Provider chain — try each until one works
        providers = [
            {"name": "pollinations-openai", "url": "https://text.pollinations.ai/openai",
             "body": {"model": "openai", "messages": full_messages, "temperature": 0.7},
             "parse": lambda r: r.json().get("choices", [{}])[0].get("message", {}).get("content", "")},
            {"name": "pollinations-text", "url": "https://text.pollinations.ai/",
             "body": {"model": "mistral", "messages": full_messages},
             "parse": lambda r: r.text if not r.text.startswith("{") else r.json().get("choices", [{}])[0].get("message", {}).get("content", r.text)},
            {"name": "pollinations-llama", "url": "https://text.pollinations.ai/openai",
             "body": {"model": "llama", "messages": full_messages, "temperature": 0.7},
             "parse": lambda r: r.json().get("choices", [{}])[0].get("message", {}).get("content", "")},
        ]

        reply = None
        model_used = None
        cost = "$0.00"

        for provider in providers:
            for attempt in range(3):
                try:
                    resp = req_lib.post(provider["url"], json=provider["body"], timeout=30)
                    if resp.status_code == 200:
                        r = provider["parse"](resp)
                        if r and len(r.strip()) > 2:
                            reply = r.strip()
                            model_used = provider["name"]
                            break
                    elif resp.status_code == 429:
                        _time.sleep(1.5 * (attempt + 1))
                        continue
                    else:
                        break
                except Exception:
                    break
            if reply:
                break

        # Final fallback: use Claude API if key is set
        if not reply:
            api_key = get_api_key()
            if api_key:
                try:
                    import anthropic
                    client = anthropic.Anthropic(api_key=api_key)
                    claude_msgs = []
                    for m in history[-20:]:
                        claude_msgs.append({"role": m["role"], "content": m["content"]})
                    claude_msgs.append({"role": "user", "content": message})
                    resp = client.messages.create(
                        model="claude-sonnet-4-20250514",
                        max_tokens=400,
                        system=system_prompt,
                        messages=claude_msgs
                    )
                    reply = resp.content[0].text
                    model_used = "claude-sonnet"
                    cost = "~$0.003"
                except Exception as e2:
                    return jsonify({"error": f"All providers failed. Claude error: {str(e2)}"})

        if not reply:
            return jsonify({"error": "Free providers busy and no API key set. Add a Claude API key in Settings for reliable responses."})

        # Process any actions in the response
        import re
        actions_performed = []

        # Check for LOOKUP actions first — these need a second AI call with the data
        lookup_match = re.search(r'\[LOOKUP:(.+?)\|query=(.+?)\]', reply)
        if lookup_match and custom_tools:
            tool_name = lookup_match.group(1)
            query = lookup_match.group(2)
            reply = reply[:lookup_match.start()].strip()

            # Find the matching tool config
            tool_cfg = None
            for t in custom_tools:
                if t.get("name") == tool_name:
                    tool_cfg = t
                    break

            if tool_cfg and tool_cfg.get("api_url"):
                # Call the API
                try:
                    api_url = tool_cfg["api_url"].replace("{query}", req_lib.utils.quote(query))
                    headers = {}
                    if tool_cfg.get("api_key"):
                        headers["Authorization"] = f"Bearer {tool_cfg['api_key']}"
                        headers["X-Api-Key"] = tool_cfg["api_key"]
                    api_resp = req_lib.get(api_url, headers=headers, timeout=15)
                    if api_resp.status_code == 200:
                        lookup_data = api_resp.json()
                        # Extract specific field if configured
                        if tool_cfg.get("response_field"):
                            for key in tool_cfg["response_field"].split("."):
                                if isinstance(lookup_data, dict):
                                    lookup_data = lookup_data.get(key, lookup_data)
                                elif isinstance(lookup_data, list) and lookup_data:
                                    lookup_data = lookup_data[0] if key == "0" else lookup_data
                        # Truncate if too long
                        lookup_str = json.dumps(lookup_data) if not isinstance(lookup_data, str) else lookup_data
                        if len(lookup_str) > 1000:
                            lookup_str = lookup_str[:1000] + "..."

                        actions_performed.append({"type": "lookup", "tool": tool_name, "query": query, "result_preview": lookup_str[:200]})

                        # Add the lookup result to the conversation and get a new response
                        messages_for_api.append({"role": "assistant", "content": reply})
                        messages_for_api.append({"role": "user", "content": f"[SYSTEM: Lookup result for '{query}': {lookup_str}. Now tell the caller the answer naturally based on this data. Remember: {tool_cfg.get('when_to_use', '')}]"})
                        full_messages = [{"role": "system", "content": system_prompt}] + messages_for_api

                        # Quick follow-up call to get the natural response with data
                        for provider in providers:
                            try:
                                provider["body"]["messages"] = full_messages
                                resp2 = req_lib.post(provider["url"], json=provider["body"], timeout=30)
                                if resp2.status_code == 200:
                                    reply2 = provider["parse"](resp2)
                                    if reply2 and len(reply2.strip()) > 2:
                                        # Clean any action tags from the follow-up
                                        reply2 = re.sub(r'\[(?:ACTION|LOOKUP):.+?\]', '', reply2).strip()
                                        reply = reply2
                                        break
                            except:
                                continue
                except Exception as e:
                    print(f"[receptionist] Lookup failed for {tool_name}: {e}")
                    reply += " Hmm, let me check on that... I'm having trouble pulling that up right now."

        action_match = re.search(r'\[ACTION:(BOOK|MESSAGE|NOTIFY)\|(.+?)\]', reply)
        if action_match:
            action_type = action_match.group(1)
            params_str = action_match.group(2)
            params = {}
            for pair in params_str.split("|"):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    params[k.strip()] = v.strip()

            # Remove the action tag from the spoken response
            reply = reply[:action_match.start()].strip()

            if action_type == "BOOK":
                appt = {
                    "id": f"appt_{int(time.time())}",
                    "name": params.get("name", "Unknown"),
                    "phone": params.get("phone", ""),
                    "service": params.get("service", ""),
                    "date": params.get("date", ""),
                    "time": params.get("time", ""),
                    "staff": params.get("staff", ""),
                    "notes": params.get("notes", ""),
                    "status": "confirmed",
                    "booked_at": datetime.now().isoformat(),
                    "booked_by": "ai_receptionist"
                }
                # Save appointment
                appt_file = os.path.join(PLATFORM_DIR, "data", "appointments.json")
                os.makedirs(os.path.dirname(appt_file), exist_ok=True)
                appts = []
                if os.path.exists(appt_file):
                    try:
                        with open(appt_file) as f:
                            appts = json.load(f)
                    except: pass
                appts.append(appt)
                with open(appt_file, "w") as f:
                    json.dump(appts, f, indent=2)
                actions_performed.append({"type": "appointment_booked", "details": appt})

                # Notify owner via email if configured
                owner_email = cfg.get("owner_email", "")
                if owner_email:
                    _send_owner_notification(owner_email, biz_name, "New Appointment Booked",
                        f"Name: {appt['name']}\nPhone: {appt['phone']}\nService: {appt['service']}\nDate: {appt['date']} at {appt['time']}\nStaff: {appt['staff']}\nNotes: {appt['notes']}")

            elif action_type == "MESSAGE":
                msg_entry = {
                    "id": f"msg_{int(time.time())}",
                    "name": params.get("name", "Unknown"),
                    "phone": params.get("phone", ""),
                    "message": params.get("message", ""),
                    "urgent": params.get("urgent", "no") == "yes",
                    "received_at": datetime.now().isoformat(),
                    "read": False
                }
                msg_file = os.path.join(PLATFORM_DIR, "data", "messages.json")
                os.makedirs(os.path.dirname(msg_file), exist_ok=True)
                msgs = []
                if os.path.exists(msg_file):
                    try:
                        with open(msg_file) as f:
                            msgs = json.load(f)
                    except: pass
                msgs.append(msg_entry)
                with open(msg_file, "w") as f:
                    json.dump(msgs, f, indent=2)
                actions_performed.append({"type": "message_taken", "details": msg_entry})

                owner_email = cfg.get("owner_email", "")
                if owner_email:
                    _send_owner_notification(owner_email, biz_name, "New Message from Caller",
                        f"From: {msg_entry['name']}\nPhone: {msg_entry['phone']}\nMessage: {msg_entry['message']}\nUrgent: {'YES' if msg_entry['urgent'] else 'No'}")

            elif action_type == "NOTIFY":
                owner_email = cfg.get("owner_email", "")
                if owner_email:
                    _send_owner_notification(owner_email, biz_name,
                        f"{'URGENT: ' if params.get('type') == 'urgent' else ''}{params.get('message', 'Notification from receptionist')}",
                        params.get("message", ""))
                actions_performed.append({"type": "notification_sent", "details": params})

        return jsonify({
            "response": reply,
            "model": model_used,
            "provider": "free" if cost == "$0.00" else "anthropic",
            "cost": cost,
            "actions": actions_performed
        })
    except Exception as e:
        return jsonify({"error": str(e)})


def _send_owner_notification(email, biz_name, subject, body):
    """Send notification to the business owner via Email + Telegram."""
    # 1. Email notification
    try:
        import smtplib
        from email.mime.text import MIMEText
        msg = MIMEText(f"Janovum AI Receptionist for {biz_name}\n\n{body}\n\n---\nThis notification was sent automatically by your AI receptionist.")
        msg["Subject"] = f"[{biz_name}] {subject}"
        msg["From"] = "myfriendlyagent12@gmail.com"
        msg["To"] = email
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login("myfriendlyagent12@gmail.com", "pdcvjroclstugncx")
            server.send_message(msg)
        print(f"[receptionist] Email sent to {email}")
    except Exception as e:
        print(f"[receptionist] Email notification failed: {e}")

    # 2. Telegram notification (instant — shows on phone immediately)
    _send_telegram_notification(biz_name, subject, body)


def _send_telegram_notification(biz_name, subject, body):
    """Send instant Telegram notification to owner's channel."""
    try:
        import requests as req_lib
        token = _get_telegram_token()
        channel = _get_telegram_channel()
        if not token or not channel:
            print("[receptionist] Telegram not configured — skipping notification")
            return

        # Format a clean Telegram message
        telegram_msg = f"📞 *{biz_name} — AI Receptionist*\n\n"
        telegram_msg += f"*{subject}*\n\n"
        telegram_msg += body.replace("_", "\\_")
        telegram_msg += "\n\n⏰ " + datetime.now().strftime("%I:%M %p, %b %d")

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        req_lib.post(url, json={
            "chat_id": channel,
            "text": telegram_msg,
            "parse_mode": "Markdown"
        }, timeout=10)
        print(f"[receptionist] Telegram notification sent")
    except Exception as e:
        print(f"[receptionist] Telegram notification failed: {e}")

# ══════════════════════════════════════════
# RECEPTIONIST — APPOINTMENTS & MESSAGES
# ══════════════════════════════════════════

@app.route("/api/receptionist/appointments", methods=["GET"])
def get_appointments():
    """Get all appointments booked by the receptionist."""
    appt_file = os.path.join(PLATFORM_DIR, "data", "appointments.json")
    if os.path.exists(appt_file):
        with open(appt_file) as f:
            return jsonify(json.load(f))
    return jsonify([])

@app.route("/api/receptionist/appointments/<appt_id>", methods=["DELETE"])
def cancel_appointment(appt_id):
    """Cancel an appointment."""
    appt_file = os.path.join(PLATFORM_DIR, "data", "appointments.json")
    if os.path.exists(appt_file):
        with open(appt_file) as f:
            appts = json.load(f)
        for a in appts:
            if a.get("id") == appt_id:
                a["status"] = "cancelled"
        with open(appt_file, "w") as f:
            json.dump(appts, f, indent=2)
    return jsonify({"status": "cancelled"})

@app.route("/api/receptionist/messages", methods=["GET"])
def get_messages():
    """Get all messages taken by the receptionist."""
    msg_file = os.path.join(PLATFORM_DIR, "data", "messages.json")
    if os.path.exists(msg_file):
        with open(msg_file) as f:
            return jsonify(json.load(f))
    return jsonify([])

@app.route("/api/receptionist/messages/<msg_id>/read", methods=["POST"])
def mark_message_read(msg_id):
    """Mark a message as read."""
    msg_file = os.path.join(PLATFORM_DIR, "data", "messages.json")
    if os.path.exists(msg_file):
        with open(msg_file) as f:
            msgs = json.load(f)
        for m in msgs:
            if m.get("id") == msg_id:
                m["read"] = True
        with open(msg_file, "w") as f:
            json.dump(msgs, f, indent=2)
    return jsonify({"status": "read"})


@app.route("/api/chat/history/<conversation_id>")
def chat_history(conversation_id):
    """Get conversation history."""
    client_id = request.args.get("client_id", "platform")
    conv_file = os.path.join(PLATFORM_DIR, "data", "conversations", client_id, f"{conversation_id}.json")
    if os.path.exists(conv_file):
        with open(conv_file) as f:
            return jsonify(json.load(f))
    return jsonify({"messages": [], "created": datetime.now().isoformat()})

@app.route("/api/chat/conversations")
def chat_conversations():
    """List all conversations for a client."""
    client_id = request.args.get("client_id", "platform")
    conv_dir = os.path.join(PLATFORM_DIR, "data", "conversations", client_id)
    conversations = []
    if os.path.exists(conv_dir):
        for f in sorted(os.listdir(conv_dir), reverse=True):
            if f.endswith(".json"):
                filepath = os.path.join(conv_dir, f)
                try:
                    with open(filepath) as fh:
                        data = json.load(fh)
                    msg_count = len(data.get("messages", []))
                    first_msg = data["messages"][0]["content"][:80] if data.get("messages") else ""
                    conversations.append({
                        "id": f.replace(".json", ""),
                        "messages": msg_count,
                        "preview": first_msg,
                        "created": data.get("created", ""),
                        "updated": data.get("updated", "")
                    })
                except Exception:
                    pass
    return jsonify({"conversations": conversations})

@app.route("/api/chat/conversations/<conversation_id>", methods=["DELETE"])
def chat_delete_conversation(conversation_id):
    """Delete a conversation."""
    client_id = request.args.get("client_id", "platform")
    conv_file = os.path.join(PLATFORM_DIR, "data", "conversations", client_id, f"{conversation_id}.json")
    if os.path.exists(conv_file):
        os.remove(conv_file)
        return jsonify({"status": "deleted"})
    return jsonify({"error": "Not found"}), 404

@app.route("/api/chat/new", methods=["POST"])
def chat_new():
    """Create a new conversation."""
    data = request.json or {}
    client_id = data.get("client_id", "platform")
    conv_id = f"chat_{int(time.time())}"
    conv_dir = os.path.join(PLATFORM_DIR, "data", "conversations", client_id)
    os.makedirs(conv_dir, exist_ok=True)
    conv_file = os.path.join(conv_dir, f"{conv_id}.json")
    history = {"messages": [], "created": datetime.now().isoformat()}
    with open(conv_file, "w") as f:
        json.dump(history, f, indent=2)
    return jsonify({"conversation_id": conv_id})


# ══════════════════════════════════════════
# FILE BROWSER
# ══════════════════════════════════════════

@app.route("/api/files/list")
def files_list():
    """List files in a directory (default: platform root)."""
    rel_path = request.args.get("path", "")
    base = PLATFORM_DIR
    target = os.path.normpath(os.path.join(base, rel_path))
    # Security: don't escape platform dir
    if not target.startswith(base):
        return jsonify({"error": "Access denied"}), 403
    if not os.path.exists(target):
        return jsonify({"error": "Path not found"}), 404

    items = []
    try:
        for entry in sorted(os.listdir(target)):
            full = os.path.join(target, entry)
            is_dir = os.path.isdir(full)
            stat = os.stat(full)
            items.append({
                "name": entry,
                "type": "directory" if is_dir else "file",
                "size": stat.st_size if not is_dir else None,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "path": os.path.relpath(full, base).replace("\\", "/")
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"path": rel_path or ".", "items": items})

@app.route("/api/files/read")
def files_read():
    """Read a file's contents."""
    rel_path = request.args.get("path", "")
    base = PLATFORM_DIR
    target = os.path.normpath(os.path.join(base, rel_path))
    if not target.startswith(base):
        return jsonify({"error": "Access denied"}), 403
    if not os.path.isfile(target):
        return jsonify({"error": "Not a file"}), 404
    try:
        with open(target, "r", encoding="utf-8", errors="replace") as f:
            content = f.read(500000)  # Max 500KB
        return jsonify({"path": rel_path, "content": content, "size": os.path.getsize(target)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/files/write", methods=["POST"])
def files_write():
    """Write/save a file."""
    data = request.json
    rel_path = data.get("path", "")
    content = data.get("content", "")
    base = PLATFORM_DIR
    target = os.path.normpath(os.path.join(base, rel_path))
    if not target.startswith(base):
        return jsonify({"error": "Access denied"}), 403
    try:
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            f.write(content)
        return jsonify({"status": "saved", "path": rel_path})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ══════════════════════════════════════════
# BOT LIBRARY — Pre-built bots with run/stop
# ══════════════════════════════════════════

_bot_threads = {}  # bot_name -> {"thread": Thread, "module": module}
BOTS_DIR = os.path.join(PLATFORM_DIR, "bots")

def _load_bot_module(bot_file):
    """Dynamically load a bot module."""
    import importlib.util
    path = os.path.join(BOTS_DIR, bot_file)
    name = bot_file.replace(".py", "")
    spec = importlib.util.spec_from_file_location(f"bots.{name}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

@app.route("/api/bots")
def bots_list():
    """List all available bots with their status."""
    bots = []
    if os.path.exists(BOTS_DIR):
        for f in sorted(os.listdir(BOTS_DIR)):
            if f.endswith(".py") and not f.startswith("_"):
                try:
                    mod = _load_bot_module(f)
                    info = getattr(mod, "BOT_INFO", {})
                    running = f.replace(".py", "") in _bot_threads and _bot_threads[f.replace(".py", "")]["thread"].is_alive()
                    status = "running" if running else "stopped"
                    try:
                        s = mod.get_status()
                        status = s.get("state", status)
                    except Exception:
                        pass
                    bots.append({
                        "file": f,
                        "id": f.replace(".py", ""),
                        "name": info.get("name", f),
                        "category": info.get("category", "general"),
                        "description": info.get("description", ""),
                        "icon": info.get("icon", ""),
                        "version": info.get("version", "1.0"),
                        "author": info.get("author", "Janovum"),
                        "config_schema": info.get("config_schema", {}),
                        "status": status,
                        "running": running
                    })
                except Exception as e:
                    bots.append({"file": f, "id": f.replace(".py", ""), "name": f, "error": str(e), "status": "error", "running": False})
    return jsonify({"bots": bots})

@app.route("/api/bots/<bot_id>/start", methods=["POST"])
def bots_start(bot_id):
    """Start a bot."""
    data = request.json or {}
    config = data.get("config", {})
    bot_file = f"{bot_id}.py"
    path = os.path.join(BOTS_DIR, bot_file)
    if not os.path.exists(path):
        return jsonify({"error": "Bot not found"}), 404

    # Check if already running
    if bot_id in _bot_threads and _bot_threads[bot_id]["thread"].is_alive():
        return jsonify({"error": "Bot already running"}), 400

    try:
        mod = _load_bot_module(bot_file)
        def run_bot():
            try:
                mod.run(config)
            except Exception as e:
                print(f"[bot:{bot_id}] Error: {e}")
        t = threading.Thread(target=run_bot, daemon=True, name=f"bot-{bot_id}")
        t.start()
        _bot_threads[bot_id] = {"thread": t, "module": mod}

        # Register with heartbeat
        hb = _get_heartbeat()
        hb.register_agent(f"bot_{bot_id}", "bot")
        _get_events().emit("bot_started", "bots", {"bot_id": bot_id})

        return jsonify({"status": "started", "bot_id": bot_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/bots/<bot_id>/stop", methods=["POST"])
def bots_stop(bot_id):
    """Stop a running bot."""
    if bot_id in _bot_threads:
        mod = _bot_threads[bot_id].get("module")
        if mod:
            try:
                mod.stop()
            except Exception:
                pass
        _get_events().emit("bot_stopped", "bots", {"bot_id": bot_id})
        return jsonify({"status": "stopped", "bot_id": bot_id})
    return jsonify({"error": "Bot not running"}), 400

@app.route("/api/bots/<bot_id>/status")
def bots_status(bot_id):
    """Get detailed bot status."""
    bot_file = f"{bot_id}.py"
    if not os.path.exists(os.path.join(BOTS_DIR, bot_file)):
        return jsonify({"error": "Bot not found"}), 404
    try:
        mod = _load_bot_module(bot_file)
        status = mod.get_status()
        running = bot_id in _bot_threads and _bot_threads[bot_id]["thread"].is_alive()
        status["running"] = running
        return jsonify(status)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/bots/<bot_id>/config", methods=["GET"])
def bots_get_config(bot_id):
    """Get saved config for a bot."""
    config_file = os.path.join(PLATFORM_DIR, "data", "bots", bot_id, "config.json")
    if os.path.exists(config_file):
        with open(config_file) as f:
            return jsonify(json.load(f))
    # Return default config from bot info
    bot_file = f"{bot_id}.py"
    if os.path.exists(os.path.join(BOTS_DIR, bot_file)):
        mod = _load_bot_module(bot_file)
        info = getattr(mod, "BOT_INFO", {})
        schema = info.get("config_schema", {})
        defaults = {k: v.get("default", "") for k, v in schema.items() if isinstance(v, dict)}
        return jsonify(defaults)
    return jsonify({}), 404

@app.route("/api/bots/<bot_id>/config", methods=["POST"])
def bots_save_config(bot_id):
    """Save config for a bot."""
    data = request.json
    config_dir = os.path.join(PLATFORM_DIR, "data", "bots", bot_id)
    os.makedirs(config_dir, exist_ok=True)
    with open(os.path.join(config_dir, "config.json"), "w") as f:
        json.dump(data, f, indent=2)
    return jsonify({"status": "saved"})

@app.route("/api/bots/categories")
def bots_categories():
    """Get bot categories."""
    bots_data = bots_list().get_json()
    cats = {}
    for b in bots_data.get("bots", []):
        cat = b.get("category", "general")
        if cat not in cats:
            cats[cat] = {"name": cat, "count": 0, "bots": []}
        cats[cat]["count"] += 1
        cats[cat]["bots"].append(b["id"])
    return jsonify({"categories": list(cats.values())})


# ══════════════════════════════════════════
# DIRECTOR AGENT (Central Message Router)
# ══════════════════════════════════════════

@app.route("/api/director/process", methods=["POST"])
def director_process():
    """Send a message to the Director for routing."""
    data = request.json or {}
    message = data.get("message", "").strip()
    source = data.get("source", "api")
    metadata = data.get("metadata", {})
    if not message:
        return jsonify({"error": "No message provided"}), 400

    director = _get_director()
    result = director.process_message(message, source=source, metadata=metadata)

    # Track in events
    try:
        _get_events().emit("director_message", "director", {
            "message": message[:200],
            "source": source,
            "action": result.get("action"),
            "bot_id": result.get("bot_id")
        })
    except Exception:
        pass

    return jsonify(result)


@app.route("/api/director/status")
def director_status():
    """Get Director status — running bots, recent activity."""
    director = _get_director()
    dashboard = director.get_dashboard()
    return jsonify(dashboard)


@app.route("/api/director/log")
def director_log():
    """Get Director's message log."""
    limit = request.args.get("limit", 50, type=int)
    director = _get_director()
    return jsonify({"log": director.get_log(limit)})


@app.route("/api/director/bots")
def director_bots():
    """List bots the Director knows about (from its routing map)."""
    from core.director import BOT_ROUTING
    bots = []
    director = _get_director()
    for bot_id, info in BOT_ROUTING.items():
        running = bot_id in director.running_bots
        bots.append({
            "id": bot_id,
            "name": bot_id.replace("_", " ").title(),
            "description": info["description"],
            "keywords": info["keywords"],
            "running": running
        })
    return jsonify({"bots": bots})


@app.route("/api/director/send", methods=["POST"])
def director_send_chat():
    """Chat with the Director from the dashboard — same as process but with conversation context."""
    data = request.json or {}
    message = data.get("message", "").strip()
    if not message:
        return jsonify({"error": "No message"}), 400

    director = _get_director()
    result = director.process_message(message, source="dashboard", metadata={"from": "chat_terminal"})
    return jsonify(result)


# ══════════════════════════════════════════
# TELEGRAM INTEGRATION (Start/Stop listener from dashboard)
# ══════════════════════════════════════════

_telegram_thread = None
_telegram_running = False

@app.route("/api/telegram/status")
def telegram_status():
    """Check if Telegram listener is running."""
    global _telegram_thread
    alive = _telegram_thread is not None and _telegram_thread.is_alive()
    return jsonify({
        "running": alive,
        "bot_token_set": bool(os.environ.get("TELEGRAM_BOT_TOKEN") or _get_telegram_token()),
    })


def _get_telegram_token():
    """Read Telegram bot token from telegram_bot/config.py."""
    try:
        config_path = os.path.join(PARENT_DIR, "telegram_bot", "config.py")
        if os.path.exists(config_path):
            with open(config_path, encoding="utf-8") as f:
                content = f.read()
            for line in content.split("\n"):
                if line.strip().startswith("BOT_TOKEN"):
                    # Extract string value
                    val = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if val and val != "YOUR_BOT_TOKEN_HERE":
                        return val
    except Exception:
        pass
    return None


def _get_telegram_channel():
    """Read Telegram channel ID from telegram_bot/config.py."""
    try:
        config_path = os.path.join(PARENT_DIR, "telegram_bot", "config.py")
        if os.path.exists(config_path):
            with open(config_path, encoding="utf-8") as f:
                content = f.read()
            for line in content.split("\n"):
                if line.strip().startswith("CHANNEL_ID"):
                    val = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if val:
                        return val
    except Exception:
        pass
    return None


@app.route("/api/telegram/start", methods=["POST"])
def telegram_start():
    """Start the Telegram listener in a background thread."""
    global _telegram_thread, _telegram_running
    import requests as req

    if _telegram_thread and _telegram_thread.is_alive():
        return jsonify({"error": "Already running"}), 400

    token = _get_telegram_token()
    if not token:
        return jsonify({"error": "No Telegram bot token found in telegram_bot/config.py"}), 400

    channel_id = _get_telegram_channel()
    api_url = f"https://api.telegram.org/bot{token}"
    _telegram_running = True

    def listener_loop():
        global _telegram_running
        offset = None
        print("[telegram] Listener started")

        while _telegram_running:
            try:
                params = {"timeout": 20, "allowed_updates": '["message"]'}
                if offset:
                    params["offset"] = offset
                resp = req.get(f"{api_url}/getUpdates", params=params, timeout=25)
                if resp.status_code != 200:
                    time.sleep(3)
                    continue

                updates = resp.json().get("result", [])
                for update in updates:
                    offset = update["update_id"] + 1
                    msg = update.get("message", {})
                    text = msg.get("text", "").strip()
                    chat_id = msg.get("chat", {}).get("id")
                    user = msg.get("from", {})
                    username = user.get("username", user.get("first_name", "Unknown"))

                    if not text or not chat_id:
                        continue

                    print(f"[telegram] @{username}: {text[:80]}")

                    # Route through Director
                    director = _get_director()
                    result = director.process_message(text, source="telegram", metadata={
                        "chat_id": chat_id,
                        "username": username,
                        "message_id": msg.get("message_id")
                    })

                    # Format reply
                    action = result.get("action", "")
                    response = result.get("response", "No response")
                    bot_id = result.get("bot_id", "")

                    if action == "auto_started":
                        reply = f"🤖 Director → {bot_id.replace('_', ' ').title()}\n\n{response}"
                    elif action in ("started", "stopped"):
                        icon = "▶️" if action == "started" else "⏹"
                        reply = f"{icon} {response}"
                    else:
                        reply = response

                    # Send reply
                    req.post(f"{api_url}/sendMessage", json={
                        "chat_id": chat_id,
                        "text": reply,
                        "reply_to_message_id": msg.get("message_id")
                    }, timeout=10)

                    print(f"  → {action}" + (f" | {bot_id}" if bot_id else ""))

                    # Emit event
                    try:
                        _get_events().emit("telegram_message", "telegram", {
                            "username": username,
                            "text": text[:200],
                            "action": action,
                            "bot_id": bot_id
                        })
                    except Exception:
                        pass

            except Exception as e:
                if _telegram_running:
                    print(f"[telegram] Error: {e}")
                    time.sleep(5)

        print("[telegram] Listener stopped")

    _telegram_thread = threading.Thread(target=listener_loop, daemon=True, name="telegram-listener")
    _telegram_thread.start()
    return jsonify({"status": "started"})


@app.route("/api/telegram/stop", methods=["POST"])
def telegram_stop():
    """Stop the Telegram listener."""
    global _telegram_running
    _telegram_running = False
    return jsonify({"status": "stopped"})


# ══════════════════════════════════════════
# API DOCS (Self-documenting endpoint list)
# ══════════════════════════════════════════

@app.route("/api/docs")
def api_docs():
    """Auto-generated API documentation from all registered routes."""
    docs = {
        "platform": "Janovum AI Agent Toolkit",
        "version": "5.0",
        "base_url": request.host_url.rstrip("/"),
        "total_endpoints": 0,
        "sections": {}
    }

    section_map = {
        "/api/heartbeat": "Heartbeat (Health Monitoring)",
        "/api/router": "API Router (Multi-Provider)",
        "/api/costs": "Cost Tracker (Budget Enforcement)",
        "/api/guardrails": "Guardrails (Safety & Validation)",
        "/api/registry": "Agent Registry (Lifecycle)",
        "/api/marketplace": "Marketplace (Templates)",
        "/api/tracing": "Tracing (Observability)",
        "/api/approval": "Approval (Human-in-the-Loop)",
        "/api/handoffs": "Handoffs (Agent Delegation)",
        "/api/events": "Events (Event Bus)",
        "/api/voice": "Voice (TTS / STT)",
        "/api/sandbox": "Sandbox (Code Execution)",
        "/api/failover": "Model Failover",
        "/api/soul": "Soul (Agent Personality)",
        "/api/auth": "Authentication",
        "/api/chat": "Chat Terminal",
        "/api/files": "File Browser",
        "/api/bots": "Bot Library",
        "/api/director": "Director (Message Routing)",
        "/api/telegram": "Telegram Integration",
        "/api/clients": "Client Management",
        "/api/webhook": "Webhooks",
        "/api/cdp": "Chrome DevTools Proxy",
        "/api/agent": "Agent Viewer",
        "/api/module": "Module Control",
        "/api/listing": "Listings",
        "/api/roi": "ROI Scanner",
        "/api/quick-ask": "Quick Ask (AI)",
        "/api/config": "Configuration",
        "/api/status": "Platform Status",
        "/api/test-key": "API Key Test",
        "/api/docs": "Documentation",
        "/api/analytics": "Analytics",
    }

    for rule in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):
        if rule.rule.startswith("/api/"):
            methods = sorted(rule.methods - {"HEAD", "OPTIONS"})
            if not methods:
                continue

            # Find section
            section_name = "Other"
            for prefix, name in section_map.items():
                if rule.rule.startswith(prefix):
                    section_name = name
                    break

            if section_name not in docs["sections"]:
                docs["sections"][section_name] = []

            # Get docstring
            func = app.view_functions.get(rule.endpoint)
            description = func.__doc__.strip() if func and func.__doc__ else ""

            docs["sections"][section_name].append({
                "path": rule.rule,
                "methods": methods,
                "description": description
            })
            docs["total_endpoints"] += len(methods)

    return jsonify(docs)


# ══════════════════════════════════════════
# ANALYTICS (Platform-wide metrics)
# ══════════════════════════════════════════

@app.route("/api/analytics")
def analytics_overview():
    """Get platform-wide analytics — messages, costs, bots, agents, events."""
    analytics = {
        "timestamp": datetime.now().isoformat(),
        "uptime_seconds": int(time.time() - _server_start_time) if _server_start_time else 0,
    }

    # Director stats
    try:
        d = _get_director()
        dashboard = d.get_dashboard()
        analytics["director"] = {
            "running_bots": dashboard.get("running_count", 0),
            "total_messages": dashboard.get("total_messages", 0),
            "last_action": dashboard.get("last_message", {}).get("action") if dashboard.get("last_message") else None
        }
    except Exception:
        analytics["director"] = {"running_bots": 0, "total_messages": 0}

    # Bot library stats
    try:
        running = sum(1 for b in _bot_threads.values() if b.get("thread") and b["thread"].is_alive())
        total = len([f for f in os.listdir(BOTS_DIR) if f.endswith(".py") and not f.startswith("_")]) if os.path.exists(BOTS_DIR) else 0
        analytics["bots"] = {"running": running, "total": total}
    except Exception:
        analytics["bots"] = {"running": 0, "total": 0}

    # Agent registry stats
    try:
        reg = _get_registry()
        agents = reg.list_agents()
        analytics["agents"] = {
            "total": len(agents),
            "running": sum(1 for a in agents if a.get("status") == "running"),
            "paused": sum(1 for a in agents if a.get("status") == "paused"),
        }
    except Exception:
        analytics["agents"] = {"total": 0, "running": 0, "paused": 0}

    # Cost stats
    try:
        costs = _get_costs()
        analytics["costs"] = {
            "total_spent": costs.total_spent if hasattr(costs, "total_spent") else 0,
            "session_spent": costs.session_spent if hasattr(costs, "session_spent") else 0,
        }
    except Exception:
        analytics["costs"] = {"total_spent": 0, "session_spent": 0}

    # Events stats
    try:
        events = _get_events()
        analytics["events"] = {"total": events.event_count if hasattr(events, "event_count") else 0}
    except Exception:
        analytics["events"] = {"total": 0}

    # Marketplace stats
    try:
        mp_dir = os.path.join(PLATFORM_DIR, "marketplace")
        templates = len([f for f in os.listdir(mp_dir) if f.endswith(".json")]) if os.path.exists(mp_dir) else 0
        analytics["marketplace"] = {"templates": templates}
    except Exception:
        analytics["marketplace"] = {"templates": 0}

    # Telegram
    analytics["telegram"] = {"running": _telegram_thread is not None and _telegram_thread.is_alive()}

    # Souls
    try:
        souls_dir = os.path.join(PLATFORM_DIR, "souls")
        soul_count = len([f for f in os.listdir(souls_dir) if f.endswith(".md")]) if os.path.exists(souls_dir) else 0
        analytics["souls"] = {"total": soul_count}
    except Exception:
        analytics["souls"] = {"total": 0}

    return jsonify(analytics)


@app.route("/api/analytics/health")
def analytics_health():
    """Quick health check for all systems."""
    systems = {}
    checks = {
        "heartbeat": lambda: bool(_get_heartbeat()),
        "api_router": lambda: bool(_get_router()),
        "cost_tracker": lambda: bool(_get_costs()),
        "guardrails": lambda: bool(_get_guardrails()),
        "agent_registry": lambda: bool(_get_registry()),
        "tracing": lambda: bool(_get_tracer()),
        "approval": lambda: bool(_get_approval()),
        "handoffs": lambda: bool(_get_handoffs()),
        "events": lambda: bool(_get_events()),
        "voice": lambda: bool(_get_voice()),
        "sandbox": lambda: bool(_get_sandbox()),
        "model_failover": lambda: bool(_get_failover()),
        "soul": lambda: bool(_get_soul()),
        "director": lambda: bool(_get_director()),
    }
    healthy = 0
    for name, check in checks.items():
        try:
            ok = check()
            systems[name] = "healthy" if ok else "degraded"
            if ok:
                healthy += 1
        except Exception as e:
            systems[name] = f"error: {str(e)[:50]}"

    return jsonify({
        "systems": systems,
        "healthy": healthy,
        "total": len(checks),
        "score": f"{int(healthy / len(checks) * 100)}%"
    })


# ══════════════════════════════════════════
# MARKETPLACE — Browse & Deploy Templates
# ══════════════════════════════════════════

MARKETPLACE_DIR = os.path.join(PLATFORM_DIR, "marketplace")

@app.route("/api/marketplace/templates")
def marketplace_templates():
    """List all marketplace templates."""
    templates = []
    if os.path.exists(MARKETPLACE_DIR):
        for f in sorted(os.listdir(MARKETPLACE_DIR)):
            if f.endswith(".json"):
                try:
                    with open(os.path.join(MARKETPLACE_DIR, f), encoding="utf-8") as fh:
                        data = json.load(fh)
                    templates.append(data)
                except Exception:
                    pass
    return jsonify({"templates": templates, "total": len(templates)})


@app.route("/api/marketplace/templates/<template_id>")
def marketplace_template_detail(template_id):
    """Get a specific template by ID."""
    if os.path.exists(MARKETPLACE_DIR):
        for f in os.listdir(MARKETPLACE_DIR):
            if f.endswith(".json"):
                try:
                    with open(os.path.join(MARKETPLACE_DIR, f), encoding="utf-8") as fh:
                        data = json.load(fh)
                    if data.get("id") == template_id:
                        return jsonify(data)
                except Exception:
                    pass
    return jsonify({"error": "Template not found"}), 404


@app.route("/api/marketplace/categories")
def marketplace_categories():
    """Get marketplace template categories with counts."""
    cats = {}
    if os.path.exists(MARKETPLACE_DIR):
        for f in os.listdir(MARKETPLACE_DIR):
            if f.endswith(".json"):
                try:
                    with open(os.path.join(MARKETPLACE_DIR, f), encoding="utf-8") as fh:
                        data = json.load(fh)
                    cat = data.get("category", "general")
                    cats[cat] = cats.get(cat, 0) + 1
                except Exception:
                    pass
    return jsonify({"categories": [{"name": k, "count": v} for k, v in sorted(cats.items())]})


# ══════════════════════════════════════════
# SOUL MANAGEMENT — Enhanced soul endpoints
# ══════════════════════════════════════════

SOULS_DIR = os.path.join(PLATFORM_DIR, "souls")

@app.route("/api/soul/templates")
def soul_templates():
    """List all available soul/personality templates."""
    souls = []
    if os.path.exists(SOULS_DIR):
        for f in sorted(os.listdir(SOULS_DIR)):
            if f.endswith(".md"):
                try:
                    with open(os.path.join(SOULS_DIR, f), encoding="utf-8") as fh:
                        content = fh.read()
                    name = f.replace(".md", "")
                    # Extract first heading
                    title = name.replace("_", " ").title()
                    for line in content.split("\n"):
                        if line.startswith("# "):
                            title = line[2:].strip()
                            break
                    souls.append({
                        "id": name,
                        "file": f,
                        "title": title,
                        "preview": content[:200]
                    })
                except Exception:
                    pass
    return jsonify({"souls": souls, "total": len(souls)})


# ══════════════════════════════════════════
# CLIENT RECEPTIONIST MANAGEMENT
# ══════════════════════════════════════════

from core.client_manager import (
    list_clients as cm_list_clients,
    get_client as cm_get_client,
    add_client as cm_add_client,
    update_client as cm_update_client,
    delete_client as cm_delete_client,
    start_client as cm_start_client,
    stop_client as cm_stop_client,
    get_client_appointments as cm_get_client_appointments,
    get_all_stats as cm_get_all_stats,
    check_client_health as cm_check_health,
    get_client_logs as cm_get_logs,
    clear_client_logs as cm_clear_logs,
    load_toolkit_config as cm_load_toolkit_config,
    save_toolkit_config as cm_save_toolkit_config,
    update_all_webhooks as cm_update_all_webhooks,
)

@app.route("/api/receptionist/clients", methods=["GET"])
def receptionist_clients():
    """List all receptionist clients with status."""
    return jsonify(cm_get_all_stats())

@app.route("/api/receptionist/clients/add", methods=["POST"])
def receptionist_add_client():
    """Add a new client. Body: {business_name, twilio_phone_number, business_type, services, staff, hours, ...}"""
    data = request.json
    result = cm_add_client(data)
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)

@app.route("/api/receptionist/clients/<client_id>", methods=["GET"])
def receptionist_get_client(client_id):
    """Get full config for a client."""
    config = cm_get_client(client_id)
    if not config:
        return jsonify({"error": "Client not found"}), 404
    return jsonify(config)

@app.route("/api/receptionist/clients/<client_id>", methods=["POST"])
def receptionist_update_client(client_id):
    """Update a client's config."""
    data = request.json
    result = cm_update_client(client_id, data)
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)

@app.route("/api/receptionist/clients/<client_id>", methods=["DELETE"])
def receptionist_delete_client(client_id):
    """Remove a client and stop their receptionist."""
    result = cm_delete_client(client_id)
    return jsonify(result)

@app.route("/api/receptionist/clients/<client_id>/start", methods=["POST"])
def receptionist_start_client(client_id):
    """Start a client's receptionist on their assigned port."""
    result = cm_start_client(client_id)
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)

@app.route("/api/receptionist/clients/<client_id>/stop", methods=["POST"])
def receptionist_stop_client(client_id):
    """Stop a client's receptionist."""
    result = cm_stop_client(client_id)
    return jsonify(result)

@app.route("/api/receptionist/clients/<client_id>/appointments", methods=["GET"])
def receptionist_client_appointments(client_id):
    """Get appointments for a specific client."""
    appts = cm_get_client_appointments(client_id)
    return jsonify({"client_id": client_id, "total": len(appts), "appointments": appts})


@app.route("/api/receptionist/clients/<client_id>/health", methods=["GET"])
def receptionist_client_health(client_id):
    """Health check for a specific client — ping port, response time, uptime."""
    health = cm_check_health(client_id)
    return jsonify(health)


@app.route("/api/receptionist/clients/<client_id>/logs", methods=["GET"])
def receptionist_client_logs(client_id):
    """Get recent stderr/stdout logs for a client."""
    lines = request.args.get("lines", 100, type=int)
    logs = cm_get_logs(client_id, lines=lines)
    return jsonify({"client_id": client_id, "lines": len(logs), "logs": logs})


@app.route("/api/receptionist/clients/<client_id>/logs/clear", methods=["POST"])
def receptionist_clear_logs(client_id):
    """Clear a client's log file."""
    ok = cm_clear_logs(client_id)
    return jsonify({"success": ok})


# ══════════════════════════════════════════
# TOOLKIT CONFIG (domain, Twilio, etc.)
# ══════════════════════════════════════════

@app.route("/api/toolkit/config", methods=["GET"])
def get_toolkit_config():
    """Get toolkit-wide config (domain, webhook settings, etc.)."""
    cfg = cm_load_toolkit_config()
    # Mask the auth token for security
    safe = dict(cfg)
    if safe.get("twilio_auth_token"):
        t = safe["twilio_auth_token"]
        safe["twilio_auth_token_masked"] = t[:4] + "..." + t[-4:] if len(t) > 8 else "***"
        del safe["twilio_auth_token"]
    return jsonify(safe)


@app.route("/api/toolkit/config", methods=["POST"])
def save_toolkit_config():
    """Save toolkit-wide config. Auto-updates Twilio webhooks if domain changed."""
    data = request.json
    cfg = cm_load_toolkit_config()

    old_domain = cfg.get("domain", "")

    # Update allowed fields
    allowed = ["domain", "twilio_account_sid", "twilio_auth_token", "auto_update_webhooks"]
    for key in allowed:
        if key in data:
            cfg[key] = data[key]

    # Mark setup as complete if domain is set
    if cfg.get("domain"):
        cfg["setup_complete"] = True

    cm_save_toolkit_config(cfg)

    # Auto-update ALL running clients' Twilio webhooks if domain changed
    webhook_results = None
    new_domain = cfg.get("domain", "")
    if new_domain and new_domain != old_domain and cfg.get("auto_update_webhooks", True):
        webhook_results = cm_update_all_webhooks(new_domain)

    result = {"success": True, "config": {k: v for k, v in cfg.items() if k != "twilio_auth_token"}}
    if webhook_results:
        result["webhook_update"] = webhook_results
    return jsonify(result)


@app.route("/api/receptionist/wizard/steps", methods=["GET"])
def receptionist_wizard_steps():
    """Return the setup wizard steps for adding a new client."""
    steps = [
        {
            "step": 1,
            "title": "Buy a Twilio Phone Number",
            "description": "Go to Twilio console and buy a local phone number in the client's area code.",
            "instructions": [
                "Log into console.twilio.com",
                "Go to Phone Numbers > Buy a Number",
                "Search by area code (use the client's local area code)",
                "Pick a LOCAL number (not toll-free) — $1.15/mo",
                "Copy the phone number (e.g. +1234567890)",
            ],
            "link": "https://console.twilio.com/us1/develop/phone-numbers/manage/search",
            "field": "twilio_phone_number",
            "field_label": "Twilio Phone Number",
            "field_placeholder": "+1234567890",
            "required": True,
        },
        {
            "step": 2,
            "title": "Business Information",
            "description": "Enter the client's business details.",
            "fields": [
                {"name": "business_name", "label": "Business Name", "placeholder": "Bob's Barbershop", "required": True},
                {"name": "business_type", "label": "Business Type", "placeholder": "Barbershop, Dental Office, Auto Shop, etc.", "required": False},
            ],
        },
        {
            "step": 3,
            "title": "Services Offered",
            "description": "What services does the client offer? (People will book these by phone)",
            "type": "service_list",
            "fields": [
                {"name": "name", "label": "Service Name", "placeholder": "Haircut"},
                {"name": "duration_minutes", "label": "Duration (min)", "placeholder": "30", "type": "number"},
                {"name": "price", "label": "Price", "placeholder": "$25", "required": False},
            ],
        },
        {
            "step": 4,
            "title": "Business Hours",
            "description": "When is the business open?",
            "type": "hours",
        },
        {
            "step": 5,
            "title": "Staff (Optional)",
            "description": "Who works there? Callers might ask for a specific person.",
            "type": "staff_list",
            "fields": [
                {"name": "name", "label": "Name", "placeholder": "Bob"},
                {"name": "role", "label": "Role", "placeholder": "Owner / Barber"},
            ],
        },
        {
            "step": 6,
            "title": "Voice & Personality",
            "description": "How should the AI receptionist sound?",
            "fields": [
                {"name": "greeting", "label": "Greeting", "placeholder": "Hi! Thanks for calling [Business]. How can I help?"},
                {"name": "tone", "label": "Tone", "placeholder": "warm and professional", "options": ["warm and professional", "friendly and casual", "formal and polished", "upbeat and energetic"]},
            ],
        },
        {
            "step": 7,
            "title": "Set Twilio Webhook",
            "description": "Point the Twilio phone number to your server so calls come through.",
            "instructions": [
                "Go to Twilio console > Phone Numbers > Active Numbers",
                "Click the number you just bought",
                "Under 'A call comes in', set the webhook URL",
                "Method: POST",
                "The URL will be shown after setup completes",
            ],
            "link": "https://console.twilio.com/us1/develop/phone-numbers/manage/active",
            "type": "webhook_setup",
        },
        {
            "step": 8,
            "title": "Launch!",
            "description": "Review everything and start the receptionist.",
            "type": "review",
        },
    ]
    return jsonify({"steps": steps, "total_steps": len(steps)})


# Track server start time for uptime
_server_start_time = time.time()


# ══════════════════════════════════════════
# START SERVER
# ══════════════════════════════════════════

if __name__ == "__main__":
    cfg = load_config()
    port = cfg.get("server_port", 5050)

    # Auto-start heartbeat daemon
    try:
        hb = _get_heartbeat()
        hb.start()
        print("[+] Heartbeat daemon started")
    except Exception as e:
        print(f"[!] Heartbeat failed to start: {e}")

    print()
    print("=" * 65)
    print("  JANOVUM PLATFORM SERVER v8 — TOOLKIT + CLIENT MANAGEMENT")
    print("=" * 65)
    print(f"  Dashboard:       http://localhost:{port}")
    print(f"  Agent Viewer:    http://localhost:{port}/agent-viewer")
    print(f"  Platform Status: http://localhost:{port}/api/status")
    print(f"  API Key:         {'SET' if get_api_key() else 'NOT SET'}")
    print(f"  Model:           {get_model()}")
    print()
    print("  PHASE 1: heartbeat, api_router, cost_tracker, guardrails, registry, auth")
    print("  PHASE 2: tracing, approval, handoffs, events, voice, sandbox, failover, soul")
    print("  PHASE 3: director, telegram")
    print("  PHASE 4: client manager (multi-client receptionists)")
    print()
    print("  CLIENT ENDPOINTS:")
    print("    /api/receptionist/clients             — List all clients")
    print("    /api/receptionist/clients/add          — Add new client (wizard)")
    print("    /api/receptionist/clients/<id>/start   — Start receptionist")
    print("    /api/receptionist/clients/<id>/stop    — Stop receptionist")
    print("    /api/receptionist/clients/<id>/health  — Health check")
    print("    /api/receptionist/clients/<id>/logs    — View logs")
    print("    /api/toolkit/config                    — Toolkit config (domain, etc.)")
    print("    /api/receptionist/wizard/steps         — Setup wizard steps")
    print("=" * 65)

    # First-time setup detection
    try:
        tk_cfg = cm_load_toolkit_config()
        if not tk_cfg.get("domain"):
            print()
            print("  [!] FIRST-TIME SETUP: No domain configured!")
            print("  [!] Go to Settings > Server Setup in the dashboard to set your domain.")
            print()
    except Exception:
        pass

    # Auto-start clients that were previously running
    try:
        from core.client_manager import _load_clients_index, start_client
        clients = _load_clients_index()
        auto_started = 0
        for c in clients:
            if c.get("status") == "running":
                result = start_client(c["client_id"])
                if result.get("success"):
                    auto_started += 1
                    print(f"  [+] Auto-started: {c['business_name']} (port {c['port']})")
                else:
                    print(f"  [!] Failed to start: {c['business_name']} — {result.get('error', 'unknown')}")
        if auto_started > 0:
            print(f"  [+] {auto_started} client(s) auto-started")
        print()
    except Exception as e:
        print(f"  [!] Auto-start failed: {e}")

    app.run(host="0.0.0.0", port=port, debug=True)
