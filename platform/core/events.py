"""
Janovum Platform — Event-Driven Trigger System
Agents react to events automatically — no manual prompting needed.
Like CrewAI/BabyAGI triggers but simpler.

Event types:
  - webhook_received: external service sends data
  - email_received: new email arrives
  - schedule_fired: cron/timer triggers
  - file_changed: watched file modified
  - agent_completed: another agent finished its task
  - budget_alert: spending threshold reached
  - keyword_detected: monitored keyword found online
  - custom: user-defined events
"""

import json
import time
import uuid
import threading
from datetime import datetime
from pathlib import Path

PLATFORM_DIR = Path(__file__).parent.parent
EVENTS_LOG = PLATFORM_DIR / "data" / "events.json"


class Event:
    """A single event that can trigger agent actions."""

    def __init__(self, event_type, source, data=None, client_id=None):
        self.id = f"evt_{int(time.time())}_{str(uuid.uuid4())[:6]}"
        self.type = event_type
        self.source = source
        self.data = data or {}
        self.client_id = client_id
        self.timestamp = datetime.now().isoformat()
        self.processed = False
        self.handlers_triggered = []

    def to_dict(self):
        return {
            "id": self.id, "type": self.type, "source": self.source,
            "data": self.data, "client_id": self.client_id,
            "timestamp": self.timestamp, "processed": self.processed,
            "handlers_triggered": self.handlers_triggered
        }


class EventHandler:
    """Defines what happens when an event fires."""

    def __init__(self, name, event_type, callback, filter_fn=None, agent_id=None, client_id=None, enabled=True):
        self.id = f"eh_{str(uuid.uuid4())[:8]}"
        self.name = name
        self.event_type = event_type  # which event type to listen for
        self.callback = callback
        self.filter_fn = filter_fn  # optional filter: only trigger if this returns True
        self.agent_id = agent_id  # optional: only events for this agent
        self.client_id = client_id  # optional: only events for this client
        self.enabled = enabled
        self.trigger_count = 0
        self.last_triggered = None
        self.created_at = datetime.now().isoformat()

    def matches(self, event):
        if not self.enabled:
            return False
        if self.event_type != "*" and self.event_type != event.type:
            return False
        if self.client_id and self.client_id != event.client_id:
            return False
        if self.filter_fn:
            try:
                return self.filter_fn(event)
            except Exception:
                return False
        return True

    def to_dict(self):
        return {
            "id": self.id, "name": self.name, "event_type": self.event_type,
            "agent_id": self.agent_id, "client_id": self.client_id,
            "enabled": self.enabled, "trigger_count": self.trigger_count,
            "last_triggered": self.last_triggered, "created_at": self.created_at
        }


class EventBus:
    """Central event bus — publishes events and triggers handlers."""

    def __init__(self):
        EVENTS_LOG.parent.mkdir(parents=True, exist_ok=True)
        self.handlers = {}  # handler_id -> EventHandler
        self.recent_events = []  # last 500 events
        self._lock = threading.Lock()

    def on(self, event_type, name, callback, filter_fn=None, agent_id=None, client_id=None):
        """Register an event handler."""
        handler = EventHandler(name, event_type, callback, filter_fn, agent_id, client_id)
        with self._lock:
            self.handlers[handler.id] = handler
        return handler

    def off(self, handler_id):
        """Unregister an event handler."""
        with self._lock:
            return self.handlers.pop(handler_id, None) is not None

    def emit(self, event_type, source, data=None, client_id=None):
        """Emit an event — all matching handlers will fire."""
        event = Event(event_type, source, data, client_id)

        with self._lock:
            self.recent_events.append(event)
            if len(self.recent_events) > 500:
                self.recent_events = self.recent_events[-500:]

            matching = [h for h in self.handlers.values() if h.matches(event)]

        for handler in matching:
            try:
                handler.callback(event)
                handler.trigger_count += 1
                handler.last_triggered = datetime.now().isoformat()
                event.handlers_triggered.append(handler.name)
            except Exception as e:
                print(f"[events] Handler '{handler.name}' error: {e}")

        event.processed = True
        return event

    def get_handlers(self, event_type=None):
        handlers = list(self.handlers.values())
        if event_type:
            handlers = [h for h in handlers if h.event_type == event_type]
        return [h.to_dict() for h in handlers]

    def get_recent_events(self, limit=50, event_type=None, client_id=None):
        events = list(self.recent_events)
        if event_type:
            events = [e for e in events if e.type == event_type]
        if client_id:
            events = [e for e in events if e.client_id == client_id]
        return [e.to_dict() for e in events[-limit:]]

    def get_event_types(self):
        """Get all event types that have been emitted."""
        types = set()
        for e in self.recent_events:
            types.add(e.type)
        return list(types)

    def get_stats(self):
        return {
            "total_handlers": len(self.handlers),
            "active_handlers": sum(1 for h in self.handlers.values() if h.enabled),
            "total_events": len(self.recent_events),
            "event_types": self.get_event_types(),
            "top_handlers": sorted(
                [h.to_dict() for h in self.handlers.values()],
                key=lambda h: h["trigger_count"], reverse=True
            )[:10]
        }


_bus = None
def get_event_bus():
    global _bus
    if _bus is None:
        _bus = EventBus()
    return _bus
