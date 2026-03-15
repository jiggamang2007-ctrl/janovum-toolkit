"""
Janovum Platform — AI Receptionist Call Guards
Protects the receptionist from abuse, spam, and overload.

Features:
  - Max 1 concurrent call
  - 5 minute max call duration
  - 30 minute cooldown per phone number (after completed calls only)
  - Silent/spam detection (hang up after 5s of no voice)
  - In-memory tracking of active calls and cooldowns
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Dict, Optional
from datetime import datetime

from loguru import logger


@dataclass
class ActiveCall:
    """Tracks a currently active call."""
    call_id: str
    from_number: str
    started_at: float
    last_voice_at: float  # last time voice activity was detected
    pipeline_task: Optional[object] = None  # reference to PipelineTask for cancellation


@dataclass
class CallRecord:
    """Records a completed call for cooldown tracking."""
    from_number: str
    ended_at: float
    duration_seconds: float
    completed_normally: bool  # False if caller got busy signal


class ReceptionistGuards:
    """
    Call protection system for the AI receptionist.
    All time values in seconds.
    """

    MAX_CONCURRENT_CALLS = 1
    MAX_CALL_DURATION = 300       # 5 minutes
    COOLDOWN_DURATION = 1800      # 30 minutes
    SILENCE_TIMEOUT = 5.0         # seconds of no voice before hangup
    SILENCE_CHECK_INTERVAL = 1.0  # how often to check for silence

    def __init__(self):
        self._active_calls: Dict[str, ActiveCall] = {}  # call_id -> ActiveCall
        self._cooldowns: Dict[str, float] = {}  # phone_number -> cooldown_expires_at
        self._lock = asyncio.Lock()
        logger.info("[guards] Receptionist guards initialized")

    @property
    def active_call_count(self) -> int:
        return len(self._active_calls)

    @property
    def has_active_call(self) -> bool:
        return self.active_call_count > 0

    def _clean_expired_cooldowns(self):
        """Remove expired cooldowns from memory."""
        now = time.time()
        expired = [num for num, expires in self._cooldowns.items() if now >= expires]
        for num in expired:
            del self._cooldowns[num]

    def is_number_on_cooldown(self, phone_number: str) -> bool:
        """Check if a phone number is in the cooldown period."""
        self._clean_expired_cooldowns()
        if phone_number in self._cooldowns:
            remaining = self._cooldowns[phone_number] - time.time()
            if remaining > 0:
                logger.info(f"[guards] Number {phone_number} on cooldown, {remaining:.0f}s remaining")
                return True
        return False

    async def can_accept_call(self, from_number: str) -> tuple[bool, str]:
        """
        Check if a new call can be accepted.
        Returns (can_accept, reason_if_rejected).
        """
        async with self._lock:
            # Check concurrent call limit
            if self.active_call_count >= self.MAX_CONCURRENT_CALLS:
                logger.warning(f"[guards] Rejecting call from {from_number}: max concurrent calls reached")
                return False, "busy"

            # Check cooldown (only applies to numbers that completed a call)
            if self.is_number_on_cooldown(from_number):
                logger.warning(f"[guards] Rejecting call from {from_number}: cooldown active")
                return False, "cooldown"

            return True, "ok"

    async def register_call(self, call_id: str, from_number: str, pipeline_task=None) -> bool:
        """
        Register a new active call. Returns False if call cannot be accepted.
        """
        async with self._lock:
            if self.active_call_count >= self.MAX_CONCURRENT_CALLS:
                return False

            now = time.time()
            self._active_calls[call_id] = ActiveCall(
                call_id=call_id,
                from_number=from_number,
                started_at=now,
                last_voice_at=now,
                pipeline_task=pipeline_task,
            )
            logger.info(f"[guards] Call registered: {call_id} from {from_number}")
            return True

    async def unregister_call(self, call_id: str, completed_normally: bool = True):
        """
        Unregister a call and start cooldown if it completed normally.
        """
        async with self._lock:
            call = self._active_calls.pop(call_id, None)
            if call:
                duration = time.time() - call.started_at
                logger.info(
                    f"[guards] Call ended: {call_id} from {call.from_number}, "
                    f"duration={duration:.1f}s, normal={completed_normally}"
                )
                # Only apply cooldown if the call completed normally (not busy/rejected)
                if completed_normally:
                    self._cooldowns[call.from_number] = time.time() + self.COOLDOWN_DURATION
                    logger.info(
                        f"[guards] Cooldown set for {call.from_number}: "
                        f"{self.COOLDOWN_DURATION}s"
                    )

    def update_voice_activity(self, call_id: str):
        """Update the last voice activity timestamp for a call."""
        if call_id in self._active_calls:
            self._active_calls[call_id].last_voice_at = time.time()

    def get_call_duration(self, call_id: str) -> float:
        """Get the current duration of an active call in seconds."""
        call = self._active_calls.get(call_id)
        if call:
            return time.time() - call.started_at
        return 0.0

    def get_silence_duration(self, call_id: str) -> float:
        """Get how long since last voice activity in seconds."""
        call = self._active_calls.get(call_id)
        if call:
            return time.time() - call.last_voice_at
        return 0.0

    async def start_call_monitor(self, call_id: str, cancel_callback):
        """
        Background task that monitors a call for:
        - Max duration exceeded
        - Silence/spam detection

        cancel_callback: async function to call when call should be terminated.
        """
        logger.info(f"[guards] Starting call monitor for {call_id}")

        while call_id in self._active_calls:
            await asyncio.sleep(self.SILENCE_CHECK_INTERVAL)

            call = self._active_calls.get(call_id)
            if not call:
                break

            # Check max duration
            duration = time.time() - call.started_at
            if duration >= self.MAX_CALL_DURATION:
                logger.warning(
                    f"[guards] Call {call_id} exceeded max duration "
                    f"({duration:.0f}s >= {self.MAX_CALL_DURATION}s), terminating"
                )
                try:
                    await cancel_callback("max_duration")
                except Exception as e:
                    logger.error(f"[guards] Error in cancel callback: {e}")
                break

            # Check silence
            silence = time.time() - call.last_voice_at
            if silence >= self.SILENCE_TIMEOUT:
                logger.warning(
                    f"[guards] Call {call_id} silent for {silence:.1f}s, terminating"
                )
                try:
                    await cancel_callback("silence")
                except Exception as e:
                    logger.error(f"[guards] Error in cancel callback: {e}")
                break

        logger.info(f"[guards] Call monitor stopped for {call_id}")

    def get_status(self) -> dict:
        """Get current guard status for monitoring."""
        self._clean_expired_cooldowns()
        now = time.time()
        active = []
        for call in self._active_calls.values():
            active.append({
                "call_id": call.call_id,
                "from_number": call.from_number,
                "duration_seconds": round(now - call.started_at, 1),
                "silence_seconds": round(now - call.last_voice_at, 1),
            })

        cooldowns = []
        for number, expires_at in self._cooldowns.items():
            remaining = expires_at - now
            if remaining > 0:
                cooldowns.append({
                    "phone_number": number,
                    "remaining_seconds": round(remaining, 0),
                    "expires_at": datetime.fromtimestamp(expires_at).isoformat(),
                })

        return {
            "active_calls": active,
            "active_call_count": len(active),
            "max_concurrent": self.MAX_CONCURRENT_CALLS,
            "cooldowns": cooldowns,
            "max_call_duration": self.MAX_CALL_DURATION,
            "silence_timeout": self.SILENCE_TIMEOUT,
        }


# Singleton instance
_guards: Optional[ReceptionistGuards] = None


def get_guards() -> ReceptionistGuards:
    global _guards
    if _guards is None:
        _guards = ReceptionistGuards()
    return _guards
