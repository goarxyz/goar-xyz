"""Local-only metadata compatibility helpers for the Alpine Private Vibe edition.

The retained upstream agent and TUI expect these interfaces during startup.  This
edition intentionally does not collect platform, session, experiment, account,
or prompt metadata for telemetry transport.
"""

from __future__ import annotations

from vibe.core.telemetry.types import (
    AgentEntrypoint,
    AttachmentKind,
    LaunchContext,
    TelemetryCallType,
    TelemetryRequestMetadata,
    TerminalEmulator,
)
from vibe.core.types import LLMMessage


def build_base_metadata(
    *,
    launch_context: LaunchContext | None,
    session_id: str | None,
    parent_session_id: str | None = None,
    experiments: dict[str, str] | None = None,
    user_plan: str | None = None,
) -> dict[str, object]:
    """Return no reportable metadata in the private edition."""
    del launch_context, session_id, parent_session_id, experiments, user_plan
    return {}


def build_request_metadata(
    *,
    launch_context: LaunchContext | None,
    session_id: str | None,
    parent_session_id: str | None = None,
    call_type: TelemetryCallType,
    message_id: str | None = None,
    user_plan: str | None = None,
) -> TelemetryRequestMetadata:
    """Return only the non-identifying structural value required by callers."""
    del launch_context, session_id, parent_session_id, message_id, user_plan
    return TelemetryRequestMetadata(call_type=call_type)


def build_attachment_counts(
    message: LLMMessage | None, *, supports_images: bool
) -> dict[AttachmentKind, int]:
    """Preserve local UI behavior without retaining attachment analytics."""
    del message, supports_images
    return {}


def build_launch_context(
    *,
    agent_entrypoint: AgentEntrypoint,
    agent_version: str,
    client_name: str,
    client_version: str,
    terminal_emulator: TerminalEmulator | None = None,
) -> LaunchContext:
    """Keep the upstream startup contract; the value is never reported."""
    return LaunchContext(
        agent_entrypoint=agent_entrypoint,
        agent_version=agent_version,
        client_name=client_name,
        client_version=client_version,
        terminal_emulator=terminal_emulator,
    )
