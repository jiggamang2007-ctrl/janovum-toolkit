"""
Janovum Platform — Observability & Tracing
Records every step of every agent run for debugging and replay.
Like LangSmith but built into the platform — no external service needed.

Features:
  - Trace every agent action: API calls, tool use, decisions, errors
  - Span-based tracing (parent/child spans for nested operations)
  - Timeline view of agent runs
  - Performance metrics per agent/tool/model
  - Export traces for analysis
  - Real-time streaming of active traces
"""

import json
import time
import uuid
import threading
from datetime import datetime
from pathlib import Path

PLATFORM_DIR = Path(__file__).parent.parent
TRACES_DIR = PLATFORM_DIR / "data" / "traces"


class SpanStatus:
    OK = "ok"
    ERROR = "error"
    RUNNING = "running"


class Span:
    """A single unit of work in a trace — one API call, tool execution, or decision."""

    def __init__(self, trace_id, name, span_type="generic", parent_id=None, metadata=None):
        self.id = str(uuid.uuid4())[:12]
        self.trace_id = trace_id
        self.parent_id = parent_id
        self.name = name
        self.type = span_type  # llm_call, tool_use, decision, action, error
        self.status = SpanStatus.RUNNING
        self.start_time = time.time()
        self.end_time = None
        self.duration_ms = None
        self.metadata = metadata or {}
        self.input_data = None
        self.output_data = None
        self.error = None
        self.tokens = {"input": 0, "output": 0}
        self.cost = 0.0
        self.model = None
        self.children = []

    def end(self, status=SpanStatus.OK, output=None, error=None):
        self.end_time = time.time()
        self.duration_ms = round((self.end_time - self.start_time) * 1000)
        self.status = status
        if output is not None:
            self.output_data = str(output)[:2000]
        if error:
            self.error = str(error)
            self.status = SpanStatus.ERROR

    def set_input(self, data):
        self.input_data = str(data)[:2000]

    def set_tokens(self, input_tokens, output_tokens, model=None, cost=0.0):
        self.tokens = {"input": input_tokens, "output": output_tokens}
        self.cost = cost
        if model:
            self.model = model

    def to_dict(self):
        return {
            "id": self.id,
            "trace_id": self.trace_id,
            "parent_id": self.parent_id,
            "name": self.name,
            "type": self.type,
            "status": self.status,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "model": self.model,
            "tokens": self.tokens,
            "cost": self.cost,
            "input": self.input_data,
            "output": self.output_data[:500] if self.output_data else None,
            "error": self.error,
            "metadata": self.metadata,
            "children": [c.to_dict() for c in self.children]
        }


class Trace:
    """A complete agent run — contains multiple spans."""

    def __init__(self, agent_id, name, client_id=None, metadata=None):
        self.id = f"trace_{int(time.time())}_{str(uuid.uuid4())[:6]}"
        self.agent_id = agent_id
        self.client_id = client_id
        self.name = name
        self.metadata = metadata or {}
        self.start_time = time.time()
        self.end_time = None
        self.status = SpanStatus.RUNNING
        self.spans = {}  # span_id -> Span
        self.root_spans = []  # top-level span IDs
        self.total_cost = 0.0
        self.total_tokens = {"input": 0, "output": 0}
        self.total_tool_calls = 0
        self.total_llm_calls = 0
        self.error_count = 0

    def start_span(self, name, span_type="generic", parent_id=None, metadata=None):
        span = Span(self.id, name, span_type, parent_id, metadata)
        self.spans[span.id] = span
        if parent_id and parent_id in self.spans:
            self.spans[parent_id].children.append(span)
        else:
            self.root_spans.append(span.id)
        return span

    def end_span(self, span_id, status=SpanStatus.OK, output=None, error=None):
        if span_id in self.spans:
            span = self.spans[span_id]
            span.end(status, output, error)
            self.total_cost += span.cost
            self.total_tokens["input"] += span.tokens["input"]
            self.total_tokens["output"] += span.tokens["output"]
            if span.type == "tool_use":
                self.total_tool_calls += 1
            if span.type == "llm_call":
                self.total_llm_calls += 1
            if span.status == SpanStatus.ERROR:
                self.error_count += 1

    def end(self, status=None):
        self.end_time = time.time()
        if status:
            self.status = status
        elif self.error_count > 0:
            self.status = SpanStatus.ERROR
        else:
            self.status = SpanStatus.OK

    def duration_ms(self):
        end = self.end_time or time.time()
        return round((end - self.start_time) * 1000)

    def to_dict(self):
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "client_id": self.client_id,
            "name": self.name,
            "status": self.status,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms(),
            "total_cost": round(self.total_cost, 6),
            "total_tokens": self.total_tokens,
            "total_tool_calls": self.total_tool_calls,
            "total_llm_calls": self.total_llm_calls,
            "error_count": self.error_count,
            "metadata": self.metadata,
            "spans": [self.spans[sid].to_dict() for sid in self.root_spans if sid in self.spans]
        }


class TracingSystem:
    """Global tracing system — records all agent activity."""

    def __init__(self):
        TRACES_DIR.mkdir(parents=True, exist_ok=True)
        self.active_traces = {}  # trace_id -> Trace
        self.completed_traces = []  # recent completed (in-memory, last 100)
        self._lock = threading.Lock()

    def start_trace(self, agent_id, name, client_id=None, metadata=None):
        with self._lock:
            trace = Trace(agent_id, name, client_id, metadata)
            self.active_traces[trace.id] = trace
            return trace

    def end_trace(self, trace_id, status=None):
        with self._lock:
            if trace_id in self.active_traces:
                trace = self.active_traces.pop(trace_id)
                trace.end(status)
                self.completed_traces.append(trace)
                if len(self.completed_traces) > 200:
                    self.completed_traces = self.completed_traces[-200:]
                self._save_trace(trace)
                return trace
        return None

    def get_trace(self, trace_id):
        if trace_id in self.active_traces:
            return self.active_traces[trace_id]
        for t in reversed(self.completed_traces):
            if t.id == trace_id:
                return t
        return self._load_trace(trace_id)

    def get_active_traces(self):
        return [t.to_dict() for t in self.active_traces.values()]

    def get_recent_traces(self, limit=50, agent_id=None, client_id=None):
        traces = list(self.completed_traces)
        if agent_id:
            traces = [t for t in traces if t.agent_id == agent_id]
        if client_id:
            traces = [t for t in traces if t.client_id == client_id]
        traces = sorted(traces, key=lambda t: t.start_time, reverse=True)[:limit]
        return [t.to_dict() for t in traces]

    def get_stats(self, agent_id=None):
        traces = list(self.completed_traces)
        if agent_id:
            traces = [t for t in traces if t.agent_id == agent_id]
        if not traces:
            return {"total_traces": 0, "total_cost": 0, "avg_duration_ms": 0, "error_rate": 0}
        total = len(traces)
        total_cost = sum(t.total_cost for t in traces)
        avg_dur = sum(t.duration_ms() for t in traces) / total
        errors = sum(1 for t in traces if t.status == SpanStatus.ERROR)
        return {
            "total_traces": total,
            "total_cost": round(total_cost, 4),
            "avg_duration_ms": round(avg_dur),
            "error_rate": round(errors / total * 100, 1),
            "total_llm_calls": sum(t.total_llm_calls for t in traces),
            "total_tool_calls": sum(t.total_tool_calls for t in traces)
        }

    def _save_trace(self, trace):
        try:
            date_dir = TRACES_DIR / datetime.now().strftime("%Y-%m-%d")
            date_dir.mkdir(exist_ok=True)
            path = date_dir / f"{trace.id}.json"
            path.write_text(json.dumps(trace.to_dict(), indent=2))
        except Exception:
            pass

    def _load_trace(self, trace_id):
        try:
            for date_dir in sorted(TRACES_DIR.iterdir(), reverse=True):
                if date_dir.is_dir():
                    path = date_dir / f"{trace_id}.json"
                    if path.exists():
                        data = json.loads(path.read_text())
                        # Return as dict since we can't fully reconstruct
                        return data
        except Exception:
            pass
        return None


# Singleton
_tracer = None
def get_tracer():
    global _tracer
    if _tracer is None:
        _tracer = TracingSystem()
    return _tracer
