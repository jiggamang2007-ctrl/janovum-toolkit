"""
Janovum Platform — Voice Agent System
Text-to-Speech and Speech-to-Text as first-class agent interfaces.
Uses FREE APIs: edge-tts (unlimited TTS), faster-whisper (local STT).

Features:
  - Convert any agent response to speech (edge-tts, 400+ voices)
  - Transcribe audio messages to text (Whisper/faster-whisper)
  - Voice profiles per client (different voices for different brands)
  - Audio file management
"""

import os
import json
import asyncio
import threading
from datetime import datetime
from pathlib import Path

PLATFORM_DIR = Path(__file__).parent.parent
AUDIO_DIR = PLATFORM_DIR / "data" / "audio"

# Available voice profiles (edge-tts voices)
VOICE_PROFILES = {
    "professional_female": "en-US-AriaNeural",
    "professional_male": "en-US-GuyNeural",
    "friendly_female": "en-US-JennyNeural",
    "friendly_male": "en-US-DavisNeural",
    "british_female": "en-GB-SoniaNeural",
    "british_male": "en-GB-RyanNeural",
    "australian_female": "en-AU-NatashaNeural",
    "australian_male": "en-AU-WilliamNeural",
    "spanish_female": "es-ES-ElviraNeural",
    "spanish_male": "es-ES-AlvaroNeural",
    "french_female": "fr-FR-DeniseNeural",
    "french_male": "fr-FR-HenriNeural",
    "german_female": "de-DE-KatjaNeural",
    "german_male": "de-DE-ConradNeural",
}


class VoiceSystem:
    """Manages TTS and STT for the platform."""

    def __init__(self):
        AUDIO_DIR.mkdir(parents=True, exist_ok=True)
        self.client_voices = {}  # client_id -> voice_id
        self.default_voice = "en-US-AriaNeural"
        self._tts_available = None
        self._stt_available = None

    def check_tts(self):
        """Check if edge-tts is installed."""
        if self._tts_available is None:
            try:
                import edge_tts
                self._tts_available = True
            except ImportError:
                self._tts_available = False
        return self._tts_available

    def check_stt(self):
        """Check if faster-whisper or whisper is installed."""
        if self._stt_available is None:
            try:
                import faster_whisper
                self._stt_available = "faster_whisper"
            except ImportError:
                try:
                    import whisper
                    self._stt_available = "whisper"
                except ImportError:
                    self._stt_available = False
        return self._stt_available

    def text_to_speech(self, text, voice=None, client_id=None, filename=None):
        """
        Convert text to speech audio file.
        Returns path to the generated audio file.
        """
        if not self.check_tts():
            return None, "edge-tts not installed. Run: pip install edge-tts"

        import edge_tts

        # Pick voice
        if not voice:
            voice = self.client_voices.get(client_id, self.default_voice)
        if voice in VOICE_PROFILES:
            voice = VOICE_PROFILES[voice]

        # Generate filename
        if not filename:
            timestamp = int(datetime.now().timestamp())
            prefix = client_id or "platform"
            filename = f"{prefix}_tts_{timestamp}.mp3"

        output_path = AUDIO_DIR / filename

        try:
            async def _generate():
                communicate = edge_tts.Communicate(text, voice)
                await communicate.save(str(output_path))

            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        pool.submit(asyncio.run, _generate()).result()
                else:
                    loop.run_until_complete(_generate())
            except RuntimeError:
                asyncio.run(_generate())

            return str(output_path), None
        except Exception as e:
            return None, str(e)

    def speech_to_text(self, audio_path, language=None):
        """
        Transcribe audio file to text.
        Returns (transcription_text, error)
        """
        stt_engine = self.check_stt()

        if not stt_engine:
            return None, "No STT engine installed. Run: pip install faster-whisper"

        try:
            if stt_engine == "faster_whisper":
                from faster_whisper import WhisperModel
                model = WhisperModel("base", device="cpu", compute_type="int8")
                segments, info = model.transcribe(audio_path, language=language)
                text = " ".join(segment.text for segment in segments)
                return text.strip(), None

            elif stt_engine == "whisper":
                import whisper
                model = whisper.load_model("base")
                result = model.transcribe(audio_path, language=language)
                return result["text"].strip(), None

        except Exception as e:
            return None, str(e)

    def set_client_voice(self, client_id, voice):
        """Set the default voice for a client."""
        if voice in VOICE_PROFILES:
            self.client_voices[client_id] = VOICE_PROFILES[voice]
        else:
            self.client_voices[client_id] = voice

    def get_voices(self):
        """Get all available voice profiles."""
        return VOICE_PROFILES

    def get_client_voice(self, client_id):
        return self.client_voices.get(client_id, self.default_voice)

    def list_audio_files(self, client_id=None):
        """List generated audio files."""
        files = []
        if AUDIO_DIR.exists():
            for f in sorted(AUDIO_DIR.iterdir(), reverse=True):
                if f.suffix in (".mp3", ".wav", ".ogg"):
                    if client_id and not f.name.startswith(client_id):
                        continue
                    files.append({
                        "filename": f.name,
                        "path": str(f),
                        "size_kb": round(f.stat().st_size / 1024, 1),
                        "created": datetime.fromtimestamp(f.stat().st_mtime).isoformat()
                    })
        return files[:50]

    def get_status(self):
        return {
            "tts_available": self.check_tts(),
            "stt_available": bool(self.check_stt()),
            "stt_engine": self.check_stt() or "none",
            "default_voice": self.default_voice,
            "voice_profiles": len(VOICE_PROFILES),
            "client_voices": len(self.client_voices),
            "audio_files": len(self.list_audio_files())
        }


_voice = None
def get_voice_system():
    global _voice
    if _voice is None:
        _voice = VoiceSystem()
    return _voice
