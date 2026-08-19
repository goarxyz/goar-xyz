"""Audio-free compatibility managers for the Alpine Private Vibe edition.

Voice recording, microphone transcription, audio playback, and narration are
intentionally unavailable. The upstream Textual UI still receives the same
manager-shaped objects, but they never load an audio backend or access a device.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from vibe.app_server.config import ConfigView
from vibe.cli.narrator_manager.narrator_manager_port import (
    NarratorManagerListener,
    NarratorManagerPort,
    NarratorState,
)
from vibe.cli.turn_summary import TurnSummaryGenerator
from vibe.cli.voice_manager.voice_manager_port import (
    TranscribeState,
    VoiceManagerListener,
    VoiceManagerPort,
)
from vibe.utils.audio import RecordingMode

if TYPE_CHECKING:
    from vibe.cli.telemetry import ClientTelemetry


_PRIVATE_AUDIO_MESSAGE = (
    "Voice, microphone, transcription, and narration are disabled in Alpine Private Vibe."
)


def check_audio_available() -> str:
    """Explain the intentional absence of every audio subsystem."""
    return _PRIVATE_AUDIO_MESSAGE


class LazyVoiceManager:
    """A permanently disabled voice manager with the upstream local interface."""

    def __init__(
        self,
        config_getter: Callable[[], ConfigView],
        factory: Callable[[], VoiceManagerPort] | None = None,
    ) -> None:
        del config_getter, factory
        self._listeners: list[VoiceManagerListener] = []

    @property
    def is_enabled(self) -> bool:
        return False

    @property
    def transcribe_state(self) -> TranscribeState:
        return TranscribeState.IDLE

    @property
    def peak(self) -> float:
        return 0.0

    def apply_enabled(self, enabled: bool) -> None:
        del enabled

    def start_recording(self, mode: RecordingMode = RecordingMode.STREAM) -> None:
        del mode

    async def stop_recording(self) -> None:
        return None

    def cancel_recording(self) -> None:
        return None

    def add_listener(self, listener: VoiceManagerListener) -> None:
        if listener not in self._listeners:
            self._listeners.append(listener)

    def remove_listener(self, listener: VoiceManagerListener) -> None:
        try:
            self._listeners.remove(listener)
        except ValueError:
            pass

    async def close(self) -> None:
        self._listeners.clear()


class LazyNarratorManager:
    """A permanently disabled narrator manager with the upstream local interface."""

    def __init__(
        self,
        config_getter: Callable[[], ConfigView],
        factory: Callable[[], NarratorManagerPort] | None = None,
    ) -> None:
        del config_getter, factory
        self._listeners: list[NarratorManagerListener] = []

    @property
    def state(self) -> NarratorState:
        return NarratorState.IDLE

    @property
    def is_playing(self) -> bool:
        return False

    def on_turn_start(self, user_message: str) -> None:
        del user_message

    def on_user_message(self, message_id: str) -> None:
        del message_id

    def on_assistant_text(self, content: str) -> None:
        del content

    def on_turn_error(self, message: str) -> None:
        del message

    def on_turn_cancel(self) -> None:
        return None

    def on_turn_end(self) -> None:
        return None

    def cancel(self) -> None:
        return None

    def sync(self) -> None:
        return None

    def add_listener(self, listener: NarratorManagerListener) -> None:
        if listener not in self._listeners:
            self._listeners.append(listener)

    def remove_listener(self, listener: NarratorManagerListener) -> None:
        try:
            self._listeners.remove(listener)
        except ValueError:
            pass

    async def close(self) -> None:
        self._listeners.clear()


def create_default_voice_manager(
    config_getter: Callable[[], ConfigView], telemetry_client: ClientTelemetry | None
) -> VoiceManagerPort:
    del telemetry_client
    return LazyVoiceManager(config_getter)


def create_default_narrator_manager(
    config_getter: Callable[[], ConfigView],
    summary_generator: TurnSummaryGenerator,
    telemetry_client: ClientTelemetry | None,
) -> NarratorManagerPort:
    del summary_generator, telemetry_client
    return LazyNarratorManager(config_getter)
