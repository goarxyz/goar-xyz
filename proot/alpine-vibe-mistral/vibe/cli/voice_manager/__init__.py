"""Port-only voice interface for Alpine Private Vibe.

Concrete microphone and transcription support is intentionally absent.  The
full Textual UI uses the retained protocol and permanent no-op manager instead.
"""

from vibe.cli.voice_manager.voice_manager_port import (
    RecordingStartError,
    VoiceManagerPort,
)

__all__ = ["RecordingStartError", "VoiceManagerPort"]
